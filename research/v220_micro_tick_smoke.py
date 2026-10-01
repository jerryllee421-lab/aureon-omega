from __future__ import annotations

import argparse
import csv
import json
import lzma
import math
import os
import struct
import time
import urllib.request
from collections import deque, Counter
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://datafeed.dukascopy.com/datafeed"
REC = struct.Struct(">IIIff")
PRICE_SCALE = 1000.0

# V2.20 ULTIMATE MICRO defaults being replicated.
POINT = 0.01                 # PXBT-style 2-digit XAUUSD point assumption
MAX_SPREAD_POINTS = 80.0
FLOW_WINDOW_MS = 120_000
FLOW_MAX_SAMPLES = 4096
FLOW_MIN_SAMPLES = 80
REFRESH_MS = 500
STRONG_DELTA_PCT = 18.0
FOOTPRINT_BINS = 32
FOOTPRINT_MIN_BIN_SAMPLES = 3
FOOTPRINT_IMBALANCE_RATIO = 2.0
PROFILE_BARS = 120
PROFILE_BINS = 64
VALUE_AREA_PCT = 70.0
MIN_OF_SCORE = 56.0
MIN_OF_EDGE = 7.0
MIN_DIR_DELTA_PCT = 4.0
MIN_MOMENTUM_ATR = 0.035
TP_ATR = 0.24
SL_ATR = 0.20
MIN_TP_SPREAD_MULT = 3.0
MIN_SL_SPREAD_MULT = 2.5
MAX_HOLD_SECONDS = 90
FLOW_FLIP_SCORE = 64.0
BREAK_EVEN_R = 0.35
BREAK_EVEN_LOCK_R = 0.03
TRAIL_START_R = 0.65
TRAIL_ATR = 0.10
RISK_PCT = 0.35
DAILY_LOSS_PCT = 3.0
ENTRY_COOLDOWN_SECONDS = 3
MAX_TRADES_DAY = 1000
ATR_PERIOD = 14
FAST_EMA = 20
SLOW_EMA = 50

@dataclass
class Tick:
    ts_ms: int
    bid: float
    ask: float

@dataclass
class FlowSample:
    ts_ms: int
    price: float
    side: int

@dataclass
class Bar:
    minute: int
    open: float
    high: float
    low: float
    close: float
    ticks: int

@dataclass
class Position:
    bullish: bool
    entry_ts_ms: int
    entry: float
    initial_stop: float
    stop: float
    target: float
    risk_price: float
    entry_equity: float
    entry_spread: float
    score: float
    edge: float
    delta: float
    momentum_atr: float

@dataclass
class Trade:
    entry_time: str
    exit_time: str
    side: str
    entry: float
    exit: float
    initial_stop: float
    target: float
    r: float
    pnl: float
    hold_seconds: float
    exit_reason: str
    entry_spread: float
    score: float
    edge: float
    delta: float
    momentum_atr: float

def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def day_iter(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

def url_for(d: date, hour: int) -> str:
    return f"{BASE}/XAUUSD/{d.year:04d}/{d.month-1:02d}/{d.day:02d}/{hour:02d}h_ticks.bi5"

def fetch_one(d: date, hour: int, cache: Path) -> tuple[str, int]:
    out = cache / f"{d.isoformat()}_{hour:02d}.bi5"
    if out.exists():
        return str(out), out.stat().st_size
    url = url_for(d, hour)
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "AUREON-V220-TICK-BACKTEST/1.0"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            out.write_bytes(data)
            return str(out), len(data)
        except Exception as e:
            last = e
            time.sleep(min(8, 1.5 * (2 ** attempt)))
    raise RuntimeError(f"download failed {url}: {last}")

def download_range(start: date, end: date, cache: Path, workers: int = 2) -> list[Path]:
    jobs = [(d, h) for d in day_iter(start, end) if d.weekday() < 5 for h in range(24)]
    paths: list[Path] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(fetch_one, d, h, cache): (d, h) for d, h in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            d, h = futs[fut]
            try:
                p, size = fut.result()
                if size:
                    paths.append(Path(p))
            except Exception as e:
                print(f"WARN {d} {h:02d}: {e}", flush=True)
            if i % 24 == 0 or i == len(futs):
                print(f"download {i}/{len(futs)} nonempty={len(paths)}", flush=True)
    return sorted(paths)

def decode_file(path: Path):
    name = path.stem
    day_s, hour_s = name.rsplit("_", 1)
    d = date.fromisoformat(day_s)
    hour = int(hour_s)
    raw_c = path.read_bytes()
    if not raw_c:
        return
    try:
        raw = lzma.decompress(raw_c)
    except lzma.LZMAError:
        return
    if len(raw) % REC.size:
        return
    start = datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc)
    base_ms = int(start.timestamp() * 1000)
    for off in range(0, len(raw), REC.size):
        ms, ask_i, bid_i, ask_vol, bid_vol = REC.unpack_from(raw, off)
        if ask_i <= 0 or bid_i <= 0:
            continue
        ask = ask_i / PRICE_SCALE
        bid = bid_i / PRICE_SCALE
        if ask < bid:
            continue
        yield Tick(base_ms + int(ms), bid, ask)

class Engine:
    def __init__(self):
        self.flow = deque(maxlen=FLOW_MAX_SAMPLES)
        self.last_flow_price = 0.0
        self.last_flow_side = 0
        self.completed_bars = deque(maxlen=PROFILE_BARS + 50)
        self.current_bar: Bar | None = None
        self.prev_bar_close: float | None = None
        self.atr: float | None = None
        self.atr_seed = []
        self.fast_ema: float | None = None
        self.slow_ema: float | None = None
        self.last_eval_ms = -10**18
        self.last_entry_ms = -10**18
        self.position: Position | None = None
        self.trades: list[Trade] = []
        self.equity = 10000.0
        self.day_key = None
        self.day_start_equity = self.equity
        self.trades_today = 0
        self.profile_cache_minute = None
        self.profile_cache = None
        self.candidate_evals = 0
        self.signal_count = 0
        self.tick_count = 0
        self.spread_rejects = 0
        self.flow_rejects = 0

    def _roll_bar(self, tick: Tick):
        mid = (tick.bid + tick.ask) * 0.5
        minute = tick.ts_ms // 60000
        if self.current_bar is None:
            self.current_bar = Bar(minute, mid, mid, mid, mid, 1)
            return
        if minute == self.current_bar.minute:
            b = self.current_bar
            b.high = max(b.high, mid)
            b.low = min(b.low, mid)
            b.close = mid
            b.ticks += 1
            return
        # Close the previous bar, even across gaps; only real bars are stored.
        self._close_bar(self.current_bar)
        self.current_bar = Bar(minute, mid, mid, mid, mid, 1)
        self.profile_cache_minute = None

    def _close_bar(self, bar: Bar):
        self.completed_bars.append(bar)
        close = bar.close
        a_fast = 2.0 / (FAST_EMA + 1.0)
        a_slow = 2.0 / (SLOW_EMA + 1.0)
        self.fast_ema = close if self.fast_ema is None else a_fast * close + (1.0 - a_fast) * self.fast_ema
        self.slow_ema = close if self.slow_ema is None else a_slow * close + (1.0 - a_slow) * self.slow_ema

        if self.prev_bar_close is not None:
            tr = max(bar.high - bar.low, abs(bar.high - self.prev_bar_close), abs(bar.low - self.prev_bar_close))
            if self.atr is None:
                self.atr_seed.append(tr)
                if len(self.atr_seed) >= ATR_PERIOD:
                    self.atr = sum(self.atr_seed[-ATR_PERIOD:]) / ATR_PERIOD
            else:
                self.atr = ((ATR_PERIOD - 1.0) * self.atr + tr) / ATR_PERIOD
        self.prev_bar_close = close

    def _current_emas(self, mid: float):
        if self.fast_ema is None or self.slow_ema is None:
            return None, None
        af = 2.0 / (FAST_EMA + 1.0)
        as_ = 2.0 / (SLOW_EMA + 1.0)
        return af * mid + (1-af) * self.fast_ema, as_ * mid + (1-as_) * self.slow_ema

    def _capture_flow(self, tick: Tick):
        price = (tick.bid + tick.ask) * 0.5
        side = 0
        if self.last_flow_price > 0:
            if price > self.last_flow_price:
                side = 1
            elif price < self.last_flow_price:
                side = -1
            else:
                side = self.last_flow_side
        self.flow.append(FlowSample(tick.ts_ms, price, side))
        self.last_flow_price = price
        if side:
            self.last_flow_side = side
        cutoff = tick.ts_ms - FLOW_WINDOW_MS
        while self.flow and self.flow[0].ts_ms < cutoff:
            self.flow.popleft()

    def _profile(self):
        if self.current_bar is None:
            return None
        minute = self.current_bar.minute
        if self.profile_cache_minute == minute:
            return self.profile_cache
        bars = list(self.completed_bars)[-PROFILE_BARS:]
        if len(bars) < 10:
            self.profile_cache_minute = minute
            self.profile_cache = None
            return None
        lo = min(b.low for b in bars)
        hi = max(b.high for b in bars)
        if not hi > lo:
            return None
        width = (hi - lo) / PROFILE_BINS
        if width <= 0:
            return None
        hist = [0.0] * PROFILE_BINS
        total = 0.0
        for b in bars:
            b0 = max(0, min(PROFILE_BINS-1, int(math.floor((b.low-lo)/width))))
            b1 = max(0, min(PROFILE_BINS-1, int(math.floor((b.high-lo)/width))))
            if b1 < b0:
                b0, b1 = b1, b0
            n = max(1, b1-b0+1)
            each = max(1, b.ticks) / n
            for j in range(b0, b1+1):
                hist[j] += each
            total += max(1, b.ticks)
        poc_idx = max(range(PROFILE_BINS), key=lambda j: hist[j])
        target = total * (VALUE_AREA_PCT / 100.0)
        accum = hist[poc_idx]
        left = right = poc_idx
        while accum < target and (left > 0 or right < PROFILE_BINS-1):
            lv = hist[left-1] if left > 0 else -1.0
            rv = hist[right+1] if right < PROFILE_BINS-1 else -1.0
            if rv > lv and right < PROFILE_BINS-1:
                right += 1
                accum += hist[right]
            elif left > 0:
                left -= 1
                accum += hist[left]
            else:
                right += 1
                accum += hist[right]
        poc = lo + (poc_idx + 0.5) * width
        val = lo + left * width
        vah = lo + (right + 1.0) * width
        self.profile_cache_minute = minute
        self.profile_cache = (poc, vah, val)
        return self.profile_cache

    def _scores(self):
        samples = list(self.flow)
        n = len(samples)
        if n < FLOW_MIN_SAMPLES:
            return None
        first = samples[0].price
        last = samples[-1].price
        minp = min(s.price for s in samples)
        maxp = max(s.price for s in samples)
        buy = sum(1.0 for s in samples if s.side > 0)
        sell = sum(1.0 for s in samples if s.side < 0)
        total = buy + sell
        delta = 100.0 * (buy - sell) / total if total > 0 else 0.0
        price_change_pts = (last - first) / POINT

        # Footprint for both directions in one pass.
        bbuy = [0.0] * FOOTPRINT_BINS
        bsell = [0.0] * FOOTPRINT_BINS
        bcount = [0] * FOOTPRINT_BINS
        width = (maxp-minp) / FOOTPRINT_BINS if maxp >= minp else POINT
        if width < POINT:
            width = POINT
        for s in samples:
            if s.side == 0:
                continue
            b = int(math.floor((s.price-minp)/width)) if width > 0 else 0
            b = max(0, min(FOOTPRINT_BINS-1, b))
            if s.side > 0:
                bbuy[b] += 1.0
            else:
                bsell[b] += 1.0
            bcount[b] += 1

        buy_best = sell_best = 1.0
        have = False
        for j in range(FOOTPRINT_BINS):
            if bcount[j] < FOOTPRINT_MIN_BIN_SAMPLES:
                continue
            have = True
            buy_best = max(buy_best, (bbuy[j] + 1e-9) / (bsell[j] + 1e-9))
            sell_best = max(sell_best, (bsell[j] + 1e-9) / (bbuy[j] + 1e-9))

        profile = self._profile()
        possible = 30.0 + (20.0 if have else 0.0) + (20.0 if profile else 0.0)
        reliability = possible
        if reliability < 40.0:
            return None

        def side_score(bullish: bool):
            dir_delta = delta if bullish else -delta
            delta_norm = clamp01(0.5 + dir_delta / (2.0 * STRONG_DELTA_PCT))
            earned = 30.0 * delta_norm
            fp_ratio = buy_best if bullish else sell_best
            if have:
                fp_norm = clamp01((fp_ratio - 1.0) / max(0.01, FOOTPRINT_IMBALANCE_RATIO - 1.0))
                earned += 20.0 * fp_norm
            profile_signal = 0.0
            if profile:
                poc, vah, val = profile
                px = last
                norm = 0.5
                if bullish:
                    if px >= poc:
                        norm = 1.0
                    elif px <= val:
                        norm = 0.0
                    elif poc > val:
                        norm = (px-val)/(poc-val)
                else:
                    if px <= poc:
                        norm = 1.0
                    elif px >= vah:
                        norm = 0.0
                    elif vah > poc:
                        norm = (vah-px)/(vah-poc)
                profile_signal = clamp01(norm)
                earned += 20.0 * profile_signal
            return 100.0 * earned / possible, fp_ratio, profile_signal

        bs, bfp, bps = side_score(True)
        ss, sfp, sps = side_score(False)
        return {
            "samples": n,
            "delta": delta,
            "price_change_pts": price_change_pts,
            "buy_score": bs,
            "sell_score": ss,
            "buy_fp": bfp,
            "sell_fp": sfp,
            "reliability": reliability,
        }

    def _signal(self, tick: Tick):
        if self.atr is None or self.atr <= 0:
            return None
        if tick.ts_ms - self.last_eval_ms < REFRESH_MS:
            return None
        self.last_eval_ms = tick.ts_ms
        self.candidate_evals += 1

        if len(self.flow) < FLOW_MIN_SAMPLES:
            return None

        # Cheap mandatory gates before footprint/profile calculation.
        first = self.flow[0].price
        last = self.flow[-1].price
        price_change = last - first
        momentum_atr = abs(price_change) / self.atr
        if momentum_atr < MIN_MOMENTUM_ATR or price_change == 0:
            return None

        buy = sum(1 for s in self.flow if s.side > 0)
        sell = sum(1 for s in self.flow if s.side < 0)
        total = buy + sell
        delta = 100.0 * (buy-sell)/total if total else 0.0
        bullish_hint = price_change > 0
        if (delta if bullish_hint else -delta) < MIN_DIR_DELTA_PCT:
            return None

        mid = (tick.bid + tick.ask) * 0.5
        ef, es = self._current_emas(mid)
        if ef is None or es is None:
            return None
        if bullish_hint and ef < es:
            return None
        if (not bullish_hint) and ef > es:
            return None

        spread = tick.ask - tick.bid
        if spread / POINT > MAX_SPREAD_POINTS:
            self.spread_rejects += 1
            return None
        tp_dist = max(self.atr * TP_ATR, spread * MIN_TP_SPREAD_MULT)
        # Mirrors V2.20's strict <= comparison: ATR target must exceed 3x spread.
        if tp_dist <= spread * MIN_TP_SPREAD_MULT:
            self.spread_rejects += 1
            return None

        snap = self._scores()
        if not snap:
            self.flow_rejects += 1
            return None
        bullish = snap["buy_score"] >= snap["sell_score"]
        chosen = snap["buy_score"] if bullish else snap["sell_score"]
        edge = abs(snap["buy_score"] - snap["sell_score"])
        dir_delta = snap["delta"] if bullish else -snap["delta"]
        if chosen < MIN_OF_SCORE or edge < MIN_OF_EDGE or dir_delta < MIN_DIR_DELTA_PCT:
            self.flow_rejects += 1
            return None
        if bullish and snap["price_change_pts"] <= 0:
            return None
        if (not bullish) and snap["price_change_pts"] >= 0:
            return None
        # Re-check EMA against selected side, as MQL does after side selection.
        if bullish and ef < es:
            return None
        if (not bullish) and ef > es:
            return None
        self.signal_count += 1
        return bullish, chosen, edge, snap["delta"], momentum_atr

    def _open(self, tick: Tick, sig):
        bullish, score, edge, delta, momentum_atr = sig
        spread = tick.ask - tick.bid
        entry = tick.ask if bullish else tick.bid
        sl_dist = max(self.atr * SL_ATR, spread * MIN_SL_SPREAD_MULT)
        tp_dist = max(self.atr * TP_ATR, spread * MIN_TP_SPREAD_MULT)
        stop = entry - sl_dist if bullish else entry + sl_dist
        target = entry + tp_dist if bullish else entry - tp_dist
        self.position = Position(
            bullish=bullish, entry_ts_ms=tick.ts_ms, entry=entry,
            initial_stop=stop, stop=stop, target=target, risk_price=abs(entry-stop),
            entry_equity=self.equity, entry_spread=spread, score=score, edge=edge,
            delta=delta, momentum_atr=momentum_atr
        )
        self.last_entry_ms = tick.ts_ms
        self.trades_today += 1

    def _close(self, tick: Tick, exit_px: float, reason: str):
        p = self.position
        if p is None:
            return
        r = (exit_px-p.entry)/p.risk_price if p.bullish else (p.entry-exit_px)/p.risk_price
        risk_money = p.entry_equity * (RISK_PCT/100.0)
        pnl = risk_money * r
        self.equity += pnl
        self.trades.append(Trade(
            entry_time=datetime.fromtimestamp(p.entry_ts_ms/1000, tz=timezone.utc).isoformat(),
            exit_time=datetime.fromtimestamp(tick.ts_ms/1000, tz=timezone.utc).isoformat(),
            side="BUY" if p.bullish else "SELL",
            entry=p.entry, exit=exit_px, initial_stop=p.initial_stop, target=p.target,
            r=r, pnl=pnl, hold_seconds=(tick.ts_ms-p.entry_ts_ms)/1000.0,
            exit_reason=reason, entry_spread=p.entry_spread, score=p.score, edge=p.edge,
            delta=p.delta, momentum_atr=p.momentum_atr
        ))
        self.position = None

    def _manage(self, tick: Tick):
        p = self.position
        if p is None:
            return
        # Broker SL/TP semantics first.
        if p.bullish:
            if tick.bid <= p.stop:
                return self._close(tick, p.stop, "SL")
            if tick.bid >= p.target:
                return self._close(tick, p.target, "TP")
            mark = tick.bid
            rr = (mark-p.entry)/p.risk_price
        else:
            if tick.ask >= p.stop:
                return self._close(tick, p.stop, "SL")
            if tick.ask <= p.target:
                return self._close(tick, p.target, "TP")
            mark = tick.ask
            rr = (p.entry-mark)/p.risk_price

        if (tick.ts_ms-p.entry_ts_ms) >= MAX_HOLD_SECONDS*1000:
            return self._close(tick, mark, "TIME")

        if rr < BREAK_EVEN_R and tick.ts_ms-self.last_eval_ms >= REFRESH_MS:
            # MQL recomputes an opposite order-flow snapshot inside position management.
            snap = self._scores()
            if snap:
                opposite = snap["sell_score"] if p.bullish else snap["buy_score"]
                if opposite >= FLOW_FLIP_SCORE:
                    return self._close(tick, mark, "FLOW_FLIP")

        if rr >= BREAK_EVEN_R:
            new_stop = p.entry + p.risk_price*BREAK_EVEN_LOCK_R if p.bullish else p.entry - p.risk_price*BREAK_EVEN_LOCK_R
            if p.bullish:
                p.stop = max(p.stop, new_stop)
            else:
                p.stop = min(p.stop, new_stop)

        if rr >= TRAIL_START_R and self.atr and self.atr > 0:
            trail = mark - self.atr*TRAIL_ATR if p.bullish else mark + self.atr*TRAIL_ATR
            floor_stop = p.entry + p.risk_price*BREAK_EVEN_LOCK_R if p.bullish else p.entry - p.risk_price*BREAK_EVEN_LOCK_R
            if p.bullish:
                trail = max(trail, floor_stop)
                p.stop = max(p.stop, trail)
            else:
                trail = min(trail, floor_stop)
                p.stop = min(p.stop, trail)

    def on_tick(self, tick: Tick):
        self.tick_count += 1
        self._roll_bar(tick)
        self._capture_flow(tick)

        d = datetime.fromtimestamp(tick.ts_ms/1000, tz=timezone.utc).date()
        if d != self.day_key:
            self.day_key = d
            self.day_start_equity = self.equity
            self.trades_today = 0

        self._manage(tick)
        if self.position is not None:
            return
        if self.trades_today >= MAX_TRADES_DAY:
            return
        if (self.day_start_equity - self.equity) / self.day_start_equity * 100.0 >= DAILY_LOSS_PCT:
            return
        if tick.ts_ms - self.last_entry_ms < ENTRY_COOLDOWN_SECONDS*1000:
            return
        sig = self._signal(tick)
        if sig:
            self._open(tick, sig)

    def finish(self, last_tick: Tick | None):
        if self.position and last_tick:
            px = last_tick.bid if self.position.bullish else last_tick.ask
            self._close(last_tick, px, "END")
        return self.summary()

    def summary(self):
        rs = [t.r for t in self.trades]
        pnls = [t.pnl for t in self.trades]
        wins = [r for r in rs if r > 0]
        losses = [-r for r in rs if r < 0]
        pf = sum(wins)/sum(losses) if losses else (999.0 if wins else 0.0)
        eq = 10000.0
        peak = eq
        max_dd_pct = 0.0
        for p in pnls:
            eq += p
            peak = max(peak, eq)
            dd = (peak-eq)/peak*100.0 if peak else 0.0
            max_dd_pct = max(max_dd_pct, dd)
        days = len({t.entry_time[:10] for t in self.trades})
        holds = [t.hold_seconds for t in self.trades]
        reasons = Counter(t.exit_reason for t in self.trades)
        sides = Counter(t.side for t in self.trades)
        return {
            "engine": "V2.20_ULTIMATE_MICRO_TICK_REPLICATION",
            "data": "Dukascopy XAUUSD bid/ask ticks",
            "important_limitation": "Research replication, not native MT5 Strategy Tester. DOM/GEX/true-trade-volume unavailable; point normalized to 0.01 to match 2-digit XAUUSD broker semantics.",
            "starting_equity": 10000.0,
            "ending_equity": self.equity,
            "net_profit": self.equity-10000.0,
            "trades": len(rs),
            "trading_days_with_entries": days,
            "trades_per_entry_day": len(rs)/days if days else 0.0,
            "win_rate_pct": 100.0*len(wins)/len(rs) if rs else 0.0,
            "profit_factor_r": pf,
            "expectancy_r": sum(rs)/len(rs) if rs else 0.0,
            "net_r": sum(rs),
            "max_drawdown_pct": max_dd_pct,
            "avg_hold_seconds": sum(holds)/len(holds) if holds else 0.0,
            "median_hold_seconds": sorted(holds)[len(holds)//2] if holds else 0.0,
            "buy_trades": sides.get("BUY", 0),
            "sell_trades": sides.get("SELL", 0),
            "exit_reasons": dict(reasons),
            "ticks_processed": self.tick_count,
            "candidate_evaluations": self.candidate_evals,
            "signals": self.signal_count,
            "spread_rejects": self.spread_rejects,
            "flow_rejects": self.flow_rejects,
        }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-08-10")
    ap.add_argument("--end", default="2026-08-14")
    ap.add_argument("--cache", default=".cache/v220_ticks")
    ap.add_argument("--out", default="research_results/v220_micro_tick")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end before start")

    cache = Path(args.cache)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = download_range(start, end, cache, args.workers)
    print(f"downloaded non-empty hourly files: {len(paths)}", flush=True)

    eng = Engine()
    last_tick = None
    for i, path in enumerate(paths, 1):
        for tick in decode_file(path) or ():
            last_tick = tick
            eng.on_tick(tick)
        if i % 12 == 0 or i == len(paths):
            print(f"processed {i}/{len(paths)} hours ticks={eng.tick_count:,} trades={len(eng.trades)} equity={eng.equity:.2f}", flush=True)

    summary = eng.finish(last_tick)
    summary["requested_start"] = start.isoformat()
    summary["requested_end"] = end.isoformat()
    summary["hour_files"] = len(paths)

    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out / "trades.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(Trade.__annotations__.keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for t in eng.trades:
            w.writerow(asdict(t))
    print("AUREON_V220_RESULT=" + json.dumps(summary, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
