#!/usr/bin/env python3
"""AUREON XAUUSD VWAP+EMA tick replay proxy.

Uses third-party Dukascopy bid/ask ticks. This is not MT5 Strategy Tester and
cannot reproduce broker-server time, broker points, contract value, commissions,
or MT5 indicator semantics exactly. All PnL is reported in gold price units per
one unit of exposure; no currency conversion is implied.
"""
from __future__ import annotations
import argparse, io, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ARCHIVE_SHA256 = "d354c8769bd4d6f6c5a57a7da87843acdddec4f03815137b339c6ed5786069b0"

def load_ticks(path: Path) -> pd.DataFrame:
    frames = []
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"ZIP integrity failure: {bad}")
        for name in sorted(n for n in z.namelist() if n.lower().endswith(".parquet")):
            raw = z.read(name)
            table = pq.read_table(io.BytesIO(raw))
            if not {"time", "bid", "ask"}.issubset(table.column_names):
                raise RuntimeError(f"Missing time/bid/ask columns in {name}")
            if table.num_rows == 0:
                continue
            df = table.select(["time", "bid", "ask"]).to_pandas()
            t = pd.to_datetime(df["time"], utc=True, errors="coerce")
            if t.isna().any():
                vals = pd.to_numeric(df["time"], errors="coerce")
                med = vals.dropna().median()
                unit = "ms" if med > 10**11 else ("us" if med > 10**14 else "s")
                t = pd.to_datetime(vals, unit=unit, utc=True, errors="coerce")
            df["time"] = t
            df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
            df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
            df = df.dropna(subset=["time","bid","ask"])
            df = df[(df.bid > 0) & (df.ask >= df.bid)]
            frames.append(df)
    if not frames:
        raise RuntimeError("No valid tick rows")
    ticks = pd.concat(frames, ignore_index=True).sort_values("time", kind="stable").reset_index(drop=True)
    ticks["spread"] = ticks.ask - ticks.bid
    ticks["minute"] = ticks.time.dt.floor("min")
    return ticks

def make_bars(ticks: pd.DataFrame) -> pd.DataFrame:
    # Broker M1 candles in this proxy use bid OHLC; tick count is volume proxy.
    g = ticks.groupby("minute", sort=True)
    bars = g.agg(open=("bid","first"), high=("bid","max"), low=("bid","min"),
                 close=("bid","last"), tick_volume=("bid","size"),
                 ask_close=("ask","last"), spread_median=("spread","median"),
                 spread_p95=("spread", lambda x: x.quantile(.95))).sort_index()
    bars["mid_close"] = (bars.close + bars.ask_close) / 2
    bars["ema9"] = bars.close.ewm(span=9, adjust=False, min_periods=9).mean()
    bars["ema21"] = bars.close.ewm(span=21, adjust=False, min_periods=21).mean()
    bars["ema50"] = bars.close.ewm(span=50, adjust=False, min_periods=50).mean()
    bars["ema200"] = bars.close.ewm(span=200, adjust=False, min_periods=200).mean()
    prev = bars.close.shift(1)
    tr = pd.concat([(bars.high-bars.low), (bars.high-prev).abs(), (bars.low-prev).abs()], axis=1).max(axis=1)
    # Wilder-like ATR smoothing.
    bars["atr14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    # UTC-day session reset is a proxy until broker server session settings are known.
    typical = (bars.high + bars.low + bars.close) / 3
    day = bars.index.strftime("%Y-%m-%d")
    pv = typical * bars.tick_volume
    bars["vwap"] = pv.groupby(day).cumsum() / bars.tick_volume.groupby(day).cumsum()

    # M5 indicators only become available after their 5-minute candle has closed.
    m5 = bars.resample("5min", label="left", closed="left").agg(
        open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"))
    m5["ema21"] = m5.close.ewm(span=21, adjust=False, min_periods=21).mean()
    m5["ema50"] = m5.close.ewm(span=50, adjust=False, min_periods=50).mean()
    # Shift availability to the next 5-minute boundary, then forward-fill onto M1.
    m5.index = m5.index + pd.Timedelta(minutes=5)
    bars["m5_ema21"] = m5.ema21.reindex(bars.index, method="ffill")
    bars["m5_ema50"] = m5.ema50.reindex(bars.index, method="ffill")

    c1, c2 = bars.close, bars.close.shift(1)
    e21, e21p = bars.ema21, bars.ema21.shift(1)
    vw = bars.vwap
    bullish_reclaim = ((c2 <= e21p) & (c1 > e21)) | ((c2 <= vw.shift(1)) & (c1 > vw) & (c1 > e21))
    bearish_reject = ((c2 >= e21p) & (c1 < e21)) | ((c2 >= vw.shift(1)) & (c1 < vw) & (c1 < e21))
    bars["long_signal"] = (bars.ema9 > bars.ema21) & (bars.ema21 >= bars.ema50) & (c1 > vw) & (bars.m5_ema21 > bars.m5_ema50) & bullish_reclaim
    bars["short_signal"] = (bars.ema9 < bars.ema21) & (bars.ema21 <= bars.ema50) & (c1 < vw) & (bars.m5_ema21 < bars.m5_ema50) & bearish_reject
    return bars

def run_scenario(ticks: pd.DataFrame, bars: pd.DataFrame, spread_cap: float,
                 slippage_side: float, commission_round_turn: float) -> tuple[dict, list]:
    # Each bar's signal is known at bar end; order fills on the first subsequent tick.
    signal_map = {ts: (1 if bool(r.long_signal) else -1 if bool(r.short_signal) else 0)
                  for ts, r in bars.iterrows()}
    bar_by_minute = {ts: r for ts, r in bars.iterrows()}
    trades, position = [], None
    pending = 0
    current_minute = None
    rejected_spread = 0
    for row in ticks.itertuples(index=False):
        ts, bid, ask, spread, minute = row.time, float(row.bid), float(row.ask), float(row.spread), row.minute
        if current_minute is None:
            current_minute = minute
        elif minute != current_minute:
            # Previous candle is now closed; its decision is eligible only on this tick.
            pending = signal_map.get(current_minute, 0)
            current_minute = minute

        if position is not None:
            side = position["side"]
            exit_price = None
            reason = None
            mark = bid if side == 1 else ask
            if side == 1:
                if mark <= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif mark >= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            else:
                if mark >= position["sl"]:
                    exit_price, reason = position["sl"], "SL"
                elif mark <= position["tp"]:
                    exit_price, reason = position["tp"], "TP"
            if exit_price is not None:
                exit_price += (-slippage_side if side == 1 else slippage_side)
                gross = (exit_price - position["entry"]) * side
                net = gross - commission_round_turn
                trades.append({**position, "exit_time": ts.isoformat(), "exit_price": exit_price,
                               "exit_reason": reason, "gross_price_units": gross,
                               "net_price_units": net, "net_R": net / position["risk_distance"]})
                position = None

        if position is None and pending:
            if spread > spread_cap:
                rejected_spread += 1
                pending = 0
                continue
            side = pending
            entry = (ask if side == 1 else bid) + (slippage_side if side == 1 else -slippage_side)
            bar = bar_by_minute.get(current_minute)
            if bar is not None and pd.notna(bar.atr14) and bar.atr14 > 0:
                risk = float(bar.atr14) * 1.5
                position = {"side": side, "entry_time": ts.isoformat(), "entry": entry,
                            "sl": entry - side*risk, "tp": entry + side*risk*1.5,
                            "risk_distance": risk, "entry_spread": spread,
                            "signal_bar_utc": current_minute.isoformat()}
            pending = 0

    # Force-close at final observed quote to avoid hiding open risk at sample end.
    if position is not None:
        last = ticks.iloc[-1]
        side = position["side"]
        px = float(last.bid if side == 1 else last.ask) + (-slippage_side if side == 1 else slippage_side)
        gross = (px-position["entry"])*side
        net = gross-commission_round_turn
        trades.append({**position, "exit_time": last.time.isoformat(), "exit_price": px,
                       "exit_reason":"END_OF_DATA", "gross_price_units":gross,
                       "net_price_units":net, "net_R":net/position["risk_distance"]})
    df = pd.DataFrame(trades)
    wins = int((df.net_price_units > 0).sum()) if len(df) else 0
    gross_profit = float(df.loc[df.net_price_units > 0, "net_price_units"].sum()) if len(df) else 0.0
    gross_loss = float(-df.loc[df.net_price_units < 0, "net_price_units"].sum()) if len(df) else 0.0
    eq = df.net_R.cumsum() if len(df) else pd.Series(dtype=float)
    dd = float((eq - eq.cummax().clip(lower=0)).min()) if len(eq) else 0.0
    report = {
        "spread_cap_price_units": spread_cap, "slippage_per_side_price_units": slippage_side,
        "commission_round_turn_price_units": commission_round_turn,
        "trades": int(len(df)), "wins": wins, "win_rate_pct": round(100*wins/len(df), 2) if len(df) else None,
        "net_price_units": round(float(df.net_price_units.sum()), 6) if len(df) else 0.0,
        "net_R": round(float(df.net_R.sum()), 6) if len(df) else 0.0,
        "profit_factor": round(gross_profit/gross_loss, 6) if gross_loss > 0 else (None if gross_profit == 0 else "infinite"),
        "max_drawdown_R": round(dd, 6), "spread_rejected_entry_opportunities": int(rejected_spread),
        "note": "Third-party tick replay proxy; not MT5 Strategy Tester; UTC session VWAP; costs are assumptions; no currency PnL conversion."
    }
    return report, trades

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--out", default="test-results")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    ticks = load_ticks(Path(args.archive))
    bars = make_bars(ticks)
    scenarios = []
    all_trades = []
    # Explicit spread/cost grid in gold price units. No broker-point conversion assumed.
    for cap, slip, comm in [(0.60,0.00,0.00),(0.70,0.00,0.00),(0.85,0.00,0.00),
                            (0.70,0.01,0.00),(0.70,0.02,0.00),(0.70,0.01,0.02)]:
        report, trades = run_scenario(ticks, bars, cap, slip, comm)
        scenarios.append(report)
        for t in trades:
            all_trades.append({"scenario_spread_cap":cap,"slippage_side":slip,"commission_round_turn":comm,**t})
    metrics = {
        "test_type":"AUREON VWAP+EMA tick-level research proxy; NOT MT5 Strategy Tester",
        "archive_sha256_expected":ARCHIVE_SHA256,
        "source":"Dukascopy third-party XAUUSD bid/ask tick archive; not PXBTTrading-1 native feed",
        "tick_rows":int(len(ticks)), "first_tick_utc":ticks.time.iloc[0].isoformat(),
        "last_tick_utc":ticks.time.iloc[-1].isoformat(),
        "unique_minutes":int(ticks.minute.nunique()),
        "spread_price_units":{"median":float(ticks.spread.median()),"p95":float(ticks.spread.quantile(.95)),
                              "p99":float(ticks.spread.quantile(.99)),"max":float(ticks.spread.max())},
        "bar_count":int(len(bars)), "signal_bars":int((bars.long_signal|bars.short_signal).sum()),
        "scenarios":scenarios,
        "limitations":["UTC day is a proxy for broker session reset","broker point size and contract value unknown",
                       "EMA/ATR calculations approximate MT5 indicator behavior","no margin, financing, partial fills or latency model",
                       "one short sample is not evidence of durable edge","open position at sample end is force-closed"],
        "promotion_gate":"FAIL / NOT EVALUATED: require longer out-of-sample data, broker-native MT5 real-tick test, cost calibration and DEMO reconciliation."
    }
    (out/"vwap-ema-tick-replay-report.json").write_text(json.dumps(metrics,indent=2)+"\n")
    pd.DataFrame(all_trades).to_csv(out/"vwap-ema-tick-replay-trades.csv",index=False)
    print(json.dumps(metrics,indent=2))
if __name__ == "__main__":
    main()
