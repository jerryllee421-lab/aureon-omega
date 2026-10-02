from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EngineSpec:
    sl_atr: float
    rr: float
    hold: int


SPECS = {
    "FVG": EngineSpec(1.20, 1.70, 20),
    "SWEEP": EngineSpec(1.35, 1.80, 25),
    "EMA": EngineSpec(1.15, 1.55, 18),
    "MOM": EngineSpec(1.25, 1.60, 12),
    "BRK": EngineSpec(1.45, 1.75, 20),
    "EXH": EngineSpec(1.80, 2.20, 30),
}


def load_m1(root: Path) -> pd.DataFrame:
    files = sorted((root / "XAUUSD" / "M1").rglob("*.parquet"))
    if not files:
        raise SystemExit("No XAUUSD M1 parquet files found")
    df = pd.concat((pd.read_parquet(p) for p in files), ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    h, l, c = x["bid_high"], x["bid_low"], x["bid_close"]
    prev = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    x["atr"] = wilder(tr, 14)

    d = c.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    au = wilder(up, 14)
    ad = wilder(dn, 14)
    rs = au / ad.replace(0, np.nan)
    x["rsi"] = 100.0 - 100.0 / (1.0 + rs)

    upmove = h.diff()
    downmove = -l.diff()
    plus_dm = pd.Series(np.where((upmove > downmove) & (upmove > 0), upmove, 0.0), index=x.index)
    minus_dm = pd.Series(np.where((downmove > upmove) & (downmove > 0), downmove, 0.0), index=x.index)
    atrw = wilder(tr, 14)
    pdi = 100.0 * wilder(plus_dm, 14) / atrw.replace(0, np.nan)
    mdi = 100.0 * wilder(minus_dm, 14) / atrw.replace(0, np.nan)
    dx = 100.0 * (pdi-mdi).abs() / (pdi+mdi).replace(0, np.nan)
    x["adx"] = wilder(dx, 14)

    for n in (9, 21, 55):
        x[f"ema{n}"] = c.ewm(span=n, adjust=False, min_periods=n).mean()

    # At entry bar j these exactly represent MQL5 shifts 2..N+1.
    x["prior12_lo"] = l.shift(2).rolling(12).min()
    x["prior12_hi"] = h.shift(2).rolling(12).max()
    x["prior20_lo"] = l.shift(2).rolling(20).min()
    x["prior20_hi"] = h.shift(2).rolling(20).max()
    x["spread_open"] = x["ask_open"] - x["bid_open"]
    return x


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def candidate(engine, direction, score, entry, atr, entry_idx, intrabar):
    s = SPECS[engine]
    return {
        "engine": engine,
        "direction": int(direction),
        "score": float(score),
        "entry": float(entry),
        "atr": float(atr),
        "entry_idx": int(entry_idx),
        "intrabar": bool(intrabar),
        "sl_atr": s.sl_atr,
        "rr": s.rr,
        "hold_limit_min": s.hold,
    }


def generate(df: pd.DataFrame) -> list[dict]:
    a = {c: df[c].to_numpy() for c in df.columns if c != "time"}
    n = len(df)
    out: list[dict] = []

    for j in range(60, n):
        atr = a["atr"][j-1]
        rsi = a["rsi"][j-1]
        adx = a["adx"][j-1]
        e9 = a["ema9"][j-1]
        e21 = a["ema21"][j-1]
        e55 = a["ema55"][j-1]
        e9prev = a["ema9"][j-2]
        if not all(np.isfinite(v) for v in (atr,rsi,adx,e9,e21,e55,e9prev)) or atr <= 0:
            continue

        o1,h1,l1,c1 = (a["bid_open"][j-1],a["bid_high"][j-1],a["bid_low"][j-1],a["bid_close"][j-1])
        ask_o,ask_h,ask_l = a["ask_open"][j],a["ask_high"][j],a["ask_low"][j]
        bid_o,bid_h,bid_l = a["bid_open"][j],a["bid_high"][j],a["bid_low"][j]
        spr = max(0.0, a["spread_open"][j])

        # FVG retest: previous gap/displacement, current bar must touch gap.
        h3,l3 = a["bid_high"][j-3],a["bid_low"][j-3]
        o2,c2 = a["bid_open"][j-2],a["bid_close"][j-2]
        atr2 = a["atr"][j-2]
        if np.isfinite(atr2) and atr2 > 0 and abs(c2-o2) >= 0.70*atr2:
            if l1 > h3 and c2 > o2:
                gap = l1-h3
                if gap >= 0.10*atr and ask_l <= l1+0.08*atr and ask_h >= h3-0.08*atr:
                    score = 68 + clamp(gap/atr*20,0,12) + (4 if rsi>50 else 0) + (3 if adx>18 else 0)
                    entry = clamp(ask_o, h3+spr, l1+spr)
                    out.append(candidate("FVG",1,score,entry,atr,j,True))
            if a["bid_high"][j-1] < l3 and c2 < o2:
                gap = l3-a["bid_high"][j-1]
                if gap >= 0.10*atr and bid_h >= a["bid_high"][j-1]-0.08*atr and bid_l <= l3+0.08*atr:
                    score = 68 + clamp(gap/atr*20,0,12) + (4 if rsi<50 else 0) + (3 if adx>18 else 0)
                    entry = clamp(bid_o, a["bid_high"][j-1], l3)
                    out.append(candidate("FVG",-1,score,entry,atr,j,True))

        # Liquidity sweep / reclaim.
        p12lo,p12hi = a["prior12_lo"][j],a["prior12_hi"][j]
        if np.isfinite(p12lo) and l1 < p12lo and c1 > p12lo:
            score = 70 + (8 if rsi<42 else 0) + (4 if adx<28 else 0) + (5 if (p12lo-l1)/atr>0.15 else 0)
            out.append(candidate("SWEEP",1,score,ask_o,atr,j,False))
        if np.isfinite(p12hi) and h1 > p12hi and c1 < p12hi:
            score = 70 + (8 if rsi>58 else 0) + (4 if adx<28 else 0) + (5 if (h1-p12hi)/atr>0.15 else 0)
            out.append(candidate("SWEEP",-1,score,bid_o,atr,j,False))

        # EMA velocity pullback + current-bar breakout trigger.
        if e9>e21>e55 and e9>e9prev and l1<=e9+0.18*atr and c1>e9 and ask_h>h1:
            score = 67 + (7 if adx>=18 else 0) + (6 if 52<=rsi<=72 else 0) + clamp((e9-e9prev)/atr*25,0,8)
            entry = ask_o if ask_o>h1 else h1+spr
            out.append(candidate("EMA",1,score,entry,atr,j,True))
        if e9<e21<e55 and e9<e9prev and h1>=e9-0.18*atr and c1<e9 and bid_l<l1:
            score = 67 + (7 if adx>=18 else 0) + (6 if 28<=rsi<=48 else 0) + clamp((e9prev-e9)/atr*25,0,8)
            entry = bid_o if bid_o<l1 else l1
            out.append(candidate("EMA",-1,score,entry,atr,j,True))

        # Momentum burst.
        body = abs(c1-o1)
        ratio = body/atr
        if c1>o1 and ratio>=0.70 and adx>=17 and rsi>=55 and ask_h>h1:
            score = 69 + clamp((ratio-0.70)*18,0,12) + (5 if adx>=25 else 0)
            entry = ask_o if ask_o>h1 else h1+spr
            out.append(candidate("MOM",1,score,entry,atr,j,True))
        if c1<o1 and ratio>=0.70 and adx>=17 and rsi<=45 and bid_l<l1:
            score = 69 + clamp((ratio-0.70)*18,0,12) + (5 if adx>=25 else 0)
            entry = bid_o if bid_o<l1 else l1
            out.append(candidate("MOM",-1,score,entry,atr,j,True))

        # Micro breakout.
        p20lo,p20hi = a["prior20_lo"][j],a["prior20_hi"][j]
        if np.isfinite(p20hi) and ask_h>p20hi+0.04*atr and e9>e21>e55 and adx>=18:
            score = 66 + (5 if rsi>=55 else 0) + (5 if adx>=25 else 0)
            entry = max(ask_o, p20hi+0.04*atr)
            out.append(candidate("BRK",1,score,entry,atr,j,True))
        if np.isfinite(p20lo) and bid_l<p20lo-0.04*atr and e9<e21<e55 and adx>=18:
            score = 66 + (5 if rsi<=45 else 0) + (5 if adx>=25 else 0)
            entry = min(bid_o, p20lo-0.04*atr)
            out.append(candidate("BRK",-1,score,entry,atr,j,True))

        # Exhaustion reversal.
        if np.isfinite(p20lo):
            ext = (e21-c1)/atr
            if l1<p20lo and c1>p20lo and rsi<=28 and adx<=30 and ext>=1.60:
                score = 75 + clamp((ext-1.60)*8,0,10) + (5 if rsi<=24 else 0)
                out.append(candidate("EXH",1,score,ask_o,atr,j,False))
        if np.isfinite(p20hi):
            ext = (c1-e21)/atr
            if h1>p20hi and c1<p20hi and rsi>=72 and adx<=30 and ext>=1.60:
                score = 75 + clamp((ext-1.60)*8,0,10) + (5 if rsi>=76 else 0)
                out.append(candidate("EXH",-1,score,bid_o,atr,j,False))

    return out


def simulate(df: pd.DataFrame, c: dict) -> dict:
    a = {k: df[k].to_numpy() for k in ("bid_low","bid_high","bid_close","ask_low","ask_high","ask_close","atr")}
    j = c["entry_idx"]
    side = c["direction"]
    entry = c["entry"]
    risk = c["sl_atr"] * c["atr"]
    sl = entry - side*risk
    tp = entry + side*c["rr"]*risk
    start = j+1 if c["intrabar"] else j
    last = min(len(df)-1, j+c["hold_limit_min"])
    exit_price = None
    exit_idx = last
    reason = "TIME"

    for k in range(start, last+1):
        if side > 0:
            stop_hit = a["bid_low"][k] <= sl
            tp_hit = a["bid_high"][k] >= tp
        else:
            stop_hit = a["ask_high"][k] >= sl
            tp_hit = a["ask_low"][k] <= tp

        # Conservative stop-first ordering if both levels occur in one M1 bar.
        if stop_hit:
            exit_price, exit_idx, reason = sl, k, "SL"
            break
        if tp_hit:
            exit_price, exit_idx, reason = tp, k, "TP"
            break

        if side > 0:
            favorable = a["bid_high"][k]-entry
            close_ref = a["bid_close"][k]
        else:
            favorable = entry-a["ask_low"][k]
            close_ref = a["ask_close"][k]
        mfe_r = favorable/risk

        if mfe_r >= 0.60:
            x = entry + side*0.05*risk
            sl = max(sl,x) if side>0 else min(sl,x)
        if mfe_r >= 1.00:
            x = entry + side*0.25*risk
            sl = max(sl,x) if side>0 else min(sl,x)
        if mfe_r >= 1.50 and np.isfinite(a["atr"][k]) and a["atr"][k] > 0:
            x = close_ref - side*0.60*a["atr"][k]
            sl = max(sl,x) if side>0 else min(sl,x)

    if exit_price is None:
        exit_price = a["bid_close"][last] if side>0 else a["ask_close"][last]

    r = side*(exit_price-entry)/risk
    row = dict(c)
    row.update({
        "exit_idx": int(exit_idx),
        "exit": float(exit_price),
        "r": float(r),
        "reason": reason,
        "entry_time": df["time"].iloc[j],
        "exit_time": df["time"].iloc[exit_idx],
        "hold_min": float((df["time"].iloc[exit_idx]-df["time"].iloc[j]).total_seconds()/60.0),
    })
    return row


def metrics(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades":0,"profit_factor":0.0,"expectancy_r":0.0,"net_r":0.0,"win_rate":0.0,"max_drawdown_r":0.0,"avg_hold_min":0.0}
    r = t["r"].to_numpy(float)
    gp = float(r[r>0].sum())
    gl = float(-r[r<0].sum())
    pf = gp/gl if gl>0 else (999.0 if gp>0 else 0.0)
    curve = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0,curve])
    dd = peak[1:]-curve
    return {
        "trades": int(len(t)),
        "profit_factor": float(pf),
        "expectancy_r": float(r.mean()),
        "net_r": float(r.sum()),
        "win_rate": float((r>0).mean()),
        "max_drawdown_r": float(dd.max() if len(dd) else 0.0),
        "avg_hold_min": float(t["hold_min"].mean()),
        "median_hold_min": float(t["hold_min"].median()),
    }


def select_portfolio(t: pd.DataFrame, max_positions=3, min_score=66.0) -> pd.DataFrame:
    if t.empty:
        return t.copy()
    x = t[t["score"]>=min_score].sort_values(["entry_idx","score"],ascending=[True,False])
    selected = []
    active_exits = []
    for _, row in x.iterrows():
        j = int(row.entry_idx)
        active_exits = [e for e in active_exits if e >= j]
        if len(active_exits) >= max_positions:
            continue
        selected.append(row)
        active_exits.append(int(row.exit_idx))
    return pd.DataFrame(selected).reset_index(drop=True) if selected else x.iloc[0:0].copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="research_data")
    ap.add_argument("--out", default="v8_cloud_results")
    ap.add_argument("--min-score", type=float, default=66.0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = prepare(load_m1(Path(args.root)))
    print(f"Loaded {len(df):,} M1 bid/ask bars: {df.time.iloc[0]} -> {df.time.iloc[-1]}", flush=True)

    raw = generate(df)
    print(f"Generated {len(raw):,} raw engine candidates", flush=True)

    trades = pd.DataFrame(simulate(df,c) for c in raw)
    if trades.empty:
        raise SystemExit("No V8 trades generated")

    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)
    trades["utc_hour"] = trades["entry_time"].dt.hour
    trades["month"] = trades["entry_time"].dt.to_period("M").astype(str)
    trades.to_csv(out/"v8_all_engine_trades.csv", index=False)

    portfolio = select_portfolio(trades, max_positions=3, min_score=args.min_score)
    portfolio.to_csv(out/"v8_portfolio_trades.csv", index=False)

    engine_rows = []
    for eng in SPECS:
        z = trades[(trades.engine==eng) & (trades.score>=args.min_score)]
        engine_rows.append({"engine":eng, **asdict(SPECS[eng]), **metrics(z)})
    engdf = pd.DataFrame(engine_rows).sort_values("expectancy_r",ascending=False)
    engdf.to_csv(out/"v8_engine_summary.csv",index=False)

    hourly = []
    for h,z in trades[trades.score>=args.min_score].groupby("utc_hour"):
        hourly.append({"utc_hour":int(h),**metrics(z)})
    pd.DataFrame(hourly).to_csv(out/"v8_hour_summary.csv",index=False)

    monthly = []
    for m,z in portfolio.groupby("month"):
        monthly.append({"month":m,**metrics(z)})
    pd.DataFrame(monthly).to_csv(out/"v8_month_summary.csv",index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "AUREON OMEGA V8.2 SUPERFAST CLOUD RAW-EDGE AUDIT",
        "data_source": "DUKASCOPY_EXTERNAL via pinned GitHub mirror; M1 bid/ask OHLC",
        "period": {"first":df.time.iloc[0].isoformat(),"last":df.time.iloc[-1].isoformat(),"bars":int(len(df))},
        "execution_model": {
            "resolution":"M1 bar-path approximation",
            "spread":"explicit bid/ask OHLC",
            "same_bar_collision":"stop-first",
            "intrabar_trigger_entries":"first-touch approximation; exits begin next bar",
            "portfolio_max_positions":3,
            "risk_note":"R-multiple research; no cash compounding or commissions",
        },
        "threshold": args.min_score,
        "all_qualified": metrics(trades[trades.score>=args.min_score]),
        "portfolio": metrics(portfolio),
        "engines": engine_rows,
        "warning": (
            "This is a cloud research approximation, not MT5 real-tick parity. "
            "It is intended to identify frequency, direction/session asymmetry and raw engine edge. "
            "Any promoted configuration still requires MT5 real-tick and forward-demo validation."
        ),
    }
    (out/"v8_cloud_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"portfolio":report["portfolio"],"engines":engine_rows},indent=2),flush=True)


if __name__ == "__main__":
    main()
