#!/usr/bin/env python3
"""
AUREON Ω — IG DEMO one-trade canary executor.

Safety properties:
- DEMO endpoint is hard-coded. There is no live endpoint option.
- XAU/Spot Gold only.
- Execution defaults OFF; --execute must be provided.
- Minimum broker-permitted deal size is used for the canary.
- Existing Gold exposure vetoes a new order.
- Persistent state hard-stops after one accepted canary submission.
- Strategy signal is the validated V7-style M5 exhaustion/liquidity reversal gate.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://demo-api.ig.com/gateway/deal"
STATE_PATH = Path("ig-api/state/one_trade_canary.json")
EVIDENCE_PATH = Path("ig-api/evidence/one_trade_canary.json")
RUNTIME_PATH = Path("ig-api/runtime")
CANARY_REFERENCE = "AUREON_IG_CANARY_001"
SEARCH_TERM = "Spot Gold"


class IGError(RuntimeError):
    pass


class IG:
    def __init__(self, api_key: str, identifier: str, password: str):
        self.api_key = api_key
        self.identifier = identifier
        self.password = password
        self.cst = ""
        self.security_token = ""
        self.active_account = ""

    def _request(
        self,
        method: str,
        path: str,
        *,
        version: int = 1,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        url = BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {
            "X-IG-API-KEY": self.api_key,
            "Accept": "application/json; charset=UTF-8",
            "Content-Type": "application/json; charset=UTF-8",
            "Version": str(version),
        }
        if authenticated:
            if not self.cst or not self.security_token:
                raise IGError("Authenticated request attempted before login")
            headers["CST"] = self.cst
            headers["X-SECURITY-TOKEN"] = self.security_token

        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if raw else {}
                rh = {k.lower(): v for k, v in resp.headers.items()}
                return body, rh
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
            except Exception:
                detail = {"raw": raw[:1000]}
            raise IGError(f"IG HTTP {exc.code} {method} {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise IGError(f"IG network error {method} {path}: {exc}") from exc

    def login(self) -> dict[str, Any]:
        body, headers = self._request(
            "POST",
            "/session",
            version=2,
            payload={
                "identifier": self.identifier,
                "password": self.password,
                "encryptedPassword": False,
            },
            authenticated=False,
        )
        self.cst = headers.get("cst", "")
        self.security_token = headers.get("x-security-token", "")
        self.active_account = str(body.get("currentAccountId") or body.get("accountId") or "")
        if not self.cst or not self.security_token:
            raise IGError("Login succeeded without CST/X-SECURITY-TOKEN response headers")
        return body

    def accounts(self) -> dict[str, Any]:
        body, _ = self._request("GET", "/accounts", version=1)
        return body

    def search_markets(self, term: str) -> dict[str, Any]:
        body, _ = self._request("GET", "/markets", version=1, params={"searchTerm": term})
        return body

    def market(self, epic: str) -> dict[str, Any]:
        body, _ = self._request("GET", f"/markets/{urllib.parse.quote(epic)}", version=2)
        return body

    def prices_m5(self, epic: str, points: int = 120) -> dict[str, Any]:
        body, _ = self._request(
            "GET",
            f"/prices/{urllib.parse.quote(epic)}/MINUTE_5/{points}",
            version=2,
        )
        return body

    def positions(self) -> dict[str, Any]:
        body, _ = self._request("GET", "/positions", version=2)
        return body

    def create_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        body, _ = self._request("POST", "/positions/otc", version=2, payload=payload)
        return body

    def confirm(self, deal_reference: str) -> dict[str, Any]:
        # Confirm is REST fallback; docs note the confirmation is short-lived.
        for attempt in range(8):
            try:
                body, _ = self._request(
                    "GET",
                    f"/confirms/{urllib.parse.quote(deal_reference)}",
                    version=1,
                )
                return body
            except IGError:
                if attempt == 7:
                    raise
                time.sleep(0.75)
        raise IGError("Confirmation unavailable")


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "schema_version": 1,
            "canary_id": CANARY_REFERENCE,
            "completed": False,
            "deal_reference": None,
            "deal_id": None,
            "updated_at": None,
        }
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def safe_summary(obj: Any) -> Any:
    if isinstance(obj, dict):
        hidden = {"password", "apiKey", "cst", "securityToken", "oauthToken"}
        return {k: ("***" if k in hidden else safe_summary(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [safe_summary(v) for v in obj]
    return obj


def midpoint(price_obj: dict[str, Any], key: str) -> float:
    p = price_obj[key]
    bid = p.get("bid")
    ask = p.get("ask")
    if bid is None or ask is None:
        raise IGError(f"Historical price missing bid/ask for {key}")
    return (float(bid) + float(ask)) / 2.0


def wilder(values: list[float], period: int) -> list[float]:
    out = [math.nan] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = (prev * (period - 1) + values[i]) / period
        out[i] = prev
    return out


def ema(values: list[float], period: int) -> list[float]:
    out = [math.nan] * len(values)
    if not values:
        return out
    alpha = 2.0 / (period + 1.0)
    prev = values[0]
    out[0] = prev
    for i in range(1, len(values)):
        prev = alpha * values[i] + (1.0 - alpha) * prev
        out[i] = prev
    return out


def indicators(candles: list[dict[str, float]]) -> dict[str, list[float]]:
    h = [x["high"] for x in candles]
    l = [x["low"] for x in candles]
    c = [x["close"] for x in candles]

    tr = []
    for i in range(len(c)):
        if i == 0:
            tr.append(h[i] - l[i])
        else:
            tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    atr = wilder(tr, 14)

    gains, losses = [0.0], [0.0]
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag, al = wilder(gains, 14), wilder(losses, 14)
    rsi = [math.nan] * len(c)
    for i in range(len(c)):
        if math.isnan(ag[i]) or math.isnan(al[i]):
            continue
        if al[i] == 0:
            rsi[i] = 100.0
        else:
            rs = ag[i] / al[i]
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)

    plus_dm, minus_dm = [0.0], [0.0]
    for i in range(1, len(c)):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    sm_plus, sm_minus = wilder(plus_dm, 14), wilder(minus_dm, 14)
    dx = [math.nan] * len(c)
    for i in range(len(c)):
        if math.isnan(atr[i]) or atr[i] <= 0 or math.isnan(sm_plus[i]) or math.isnan(sm_minus[i]):
            continue
        pdi = 100.0 * sm_plus[i] / atr[i]
        mdi = 100.0 * sm_minus[i] / atr[i]
        den = pdi + mdi
        dx[i] = 0.0 if den == 0 else 100.0 * abs(pdi - mdi) / den

    # Wilder smoothing cannot consume NaN prefix directly.
    valid_dx = [0.0 if math.isnan(x) else x for x in dx]
    adx = wilder(valid_dx, 14)
    return {"atr": atr, "rsi": rsi, "adx": adx, "ema21": ema(c, 21)}


def v7_signal(prices: dict[str, Any]) -> dict[str, Any]:
    raw = prices.get("prices") or []
    candles = []
    for p in raw:
        try:
            candles.append(
                {
                    "open": midpoint(p, "openPrice"),
                    "high": midpoint(p, "highPrice"),
                    "low": midpoint(p, "lowPrice"),
                    "close": midpoint(p, "closePrice"),
                    "time": p.get("snapshotTimeUTC") or p.get("snapshotTime"),
                }
            )
        except Exception:
            continue

    if len(candles) < 80:
        return {"qualified": False, "reason": "INSUFFICIENT_M5_HISTORY", "bars": len(candles)}

    # Treat the newest returned interval conservatively as potentially incomplete.
    idx = len(candles) - 2
    ind = indicators(candles)
    atr = ind["atr"][idx]
    rsi = ind["rsi"][idx]
    adx = ind["adx"][idx]
    ema21 = ind["ema21"][idx]
    if any(math.isnan(x) for x in (atr, rsi, adx, ema21)) or atr <= 0:
        return {"qualified": False, "reason": "INDICATOR_NOT_READY"}

    atr_hist = [x for x in ind["atr"][max(0, idx - 49): idx + 1] if not math.isnan(x)]
    if len(atr_hist) < 30:
        return {"qualified": False, "reason": "ATR_REGIME_NOT_READY"}
    atr_med = statistics.median(atr_hist)
    vol_ratio = atr / atr_med if atr_med > 0 else math.nan

    prior = candles[idx - 20:idx]
    prior_low = min(x["low"] for x in prior)
    prior_high = max(x["high"] for x in prior)
    bar = candles[idx]

    hour = datetime.now(timezone.utc).hour
    session_ok = 7 <= hour < 12
    vol_ok = 0.80 <= vol_ratio < 1.80

    long_ext = (ema21 - bar["close"]) / atr
    short_ext = (bar["close"] - ema21) / atr
    long_ok = (
        session_ok and vol_ok and
        bar["low"] < prior_low and bar["close"] > prior_low and
        rsi <= 30.0 and adx <= 30.0 and long_ext >= 2.0
    )
    short_ok = (
        session_ok and vol_ok and
        bar["high"] > prior_high and bar["close"] < prior_high and
        rsi >= 70.0 and adx <= 30.0 and short_ext >= 2.0
    )

    direction = "BUY" if long_ok else "SELL" if short_ok else None
    return {
        "qualified": bool(direction),
        "direction": direction,
        "reason": "QUALIFIED" if direction else "NO_V7_SETUP",
        "bar_time": bar["time"],
        "atr": atr,
        "rsi": rsi,
        "adx": adx,
        "ema21": ema21,
        "vol_ratio": vol_ratio,
        "long_extension_atr": long_ext,
        "short_extension_atr": short_ext,
        "prior20_low": prior_low,
        "prior20_high": prior_high,
        "session_utc_ok": session_ok,
    }


def choose_gold_market(search: dict[str, Any]) -> dict[str, Any]:
    markets = search.get("markets") or []
    if not markets:
        raise IGError("IG returned no markets for Spot Gold")

    def score(m: dict[str, Any]) -> tuple[int, int]:
        name = str(m.get("instrumentName") or m.get("name") or "").lower()
        epic = str(m.get("epic") or "").lower()
        s = 0
        if "spot gold" in name:
            s += 100
        if "gold" in name:
            s += 50
        if "gold" in epic:
            s += 10
        if str(m.get("expiry") or "") in ("-", "DFB"):
            s += 20
        if str(m.get("marketStatus") or "") == "TRADEABLE":
            s += 5
        return (s, -len(name))

    selected = sorted(markets, key=score, reverse=True)[0]
    if "gold" not in str(selected.get("instrumentName") or selected.get("name") or "").lower():
        raise IGError(f"Gold market discovery ambiguous: {selected}")
    return selected


def rule_distance(rule: dict[str, Any], reference_price: float) -> float:
    value = float(rule.get("value", 0.0) or 0.0)
    unit = str(rule.get("unit") or "POINTS").upper()
    if unit == "PERCENTAGE":
        return reference_price * value / 100.0
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Arm a real IG DEMO canary order")
    args = ap.parse_args()

    api_key = os.environ.get("IG_DEMO_API_KEY", "").strip()
    identifier = os.environ.get("IG_DEMO_IDENTIFIER", "").strip()
    password = os.environ.get("IG_DEMO_PASSWORD", "").strip()
    if not all((api_key, identifier, password)):
        raise SystemExit("Missing IG_DEMO_API_KEY / IG_DEMO_IDENTIFIER / IG_DEMO_PASSWORD")

    RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    state = load_state()
    if state.get("completed"):
        print(json.dumps({"status": "HALT", "reason": "ONE_TRADE_CANARY_ALREADY_COMPLETED", "state": state}, indent=2))
        return 0

    ig = IG(api_key, identifier, password)
    login = ig.login()

    accounts = ig.accounts()
    if not accounts.get("accounts"):
        raise IGError("No IG accounts returned after authentication")

    gold_search = ig.search_markets(SEARCH_TERM)
    selected = choose_gold_market(gold_search)
    epic = str(selected["epic"])

    details = ig.market(epic)
    instrument = details.get("instrument") or {}
    snapshot = details.get("snapshot") or {}
    rules = details.get("dealingRules") or {}

    name = str(instrument.get("name") or selected.get("instrumentName") or "")
    if "gold" not in name.lower():
        raise IGError(f"Fail-closed: discovered market is not Gold: {name}")
    if str(snapshot.get("marketStatus") or selected.get("marketStatus") or "") != "TRADEABLE":
        print(json.dumps({"status": "WAIT", "reason": "GOLD_MARKET_NOT_TRADEABLE", "epic": epic, "name": name}, indent=2))
        return 0

    positions = ig.positions()
    for p in positions.get("positions") or []:
        market = p.get("market") or {}
        if str(market.get("epic") or "") == epic:
            print(json.dumps({"status": "HALT", "reason": "EXISTING_GOLD_EXPOSURE", "epic": epic}, indent=2))
            return 0

    prices = ig.prices_m5(epic, 120)
    signal = v7_signal(prices)

    preflight = {
        "environment": "DEMO_ONLY",
        "base_url": BASE_URL,
        "active_account": ig.active_account or login.get("currentAccountId"),
        "gold": {
            "name": name,
            "epic": epic,
            "expiry": instrument.get("expiry") or selected.get("expiry") or "-",
            "currency": next((x.get("code") for x in instrument.get("currencies", []) if x.get("isDefault")), None),
            "market_status": snapshot.get("marketStatus") or selected.get("marketStatus"),
            "min_deal_size": (rules.get("minDealSize") or {}).get("value"),
            "market_order_preference": rules.get("marketOrderPreference"),
        },
        "signal": signal,
        "execute_requested": args.execute,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_json(RUNTIME_PATH / "preflight.json", preflight)
    print(json.dumps(preflight, indent=2, default=str))

    if not signal.get("qualified"):
        print("AUREON_IG_STATUS=NO_SIGNAL")
        return 0

    if not args.execute:
        print("AUREON_IG_STATUS=QUALIFIED_DRY_RUN")
        return 0

    market_pref = str(rules.get("marketOrderPreference") or "")
    if market_pref == "NOT_AVAILABLE":
        raise IGError("Gold market orders are not available for this account/instrument")

    min_size_rule = rules.get("minDealSize") or {}
    if str(min_size_rule.get("unit") or "POINTS").upper() != "POINTS":
        raise IGError(f"Unsupported minDealSize unit for canary: {min_size_rule}")
    size = float(min_size_rule.get("value") or 0.0)
    if size <= 0:
        raise IGError("Could not determine broker minimum Gold deal size")

    bid = float(snapshot.get("bid"))
    offer = float(snapshot.get("offer"))
    reference = offer if signal["direction"] == "BUY" else bid
    min_stop = rule_distance(rules.get("minNormalStopOrLimitDistance") or {}, reference)
    stop_distance = max(float(signal["atr"]) * 2.5, min_stop * 1.10)
    limit_distance = stop_distance * 4.0

    currency = next((x.get("code") for x in instrument.get("currencies", []) if x.get("isDefault")), None)
    if not currency:
        currencies = instrument.get("currencies") or []
        currency = currencies[0].get("code") if currencies else None
    if not currency:
        raise IGError("Unable to determine Gold dealing currency")

    payload = {
        "currencyCode": str(currency),
        "dealReference": CANARY_REFERENCE,
        "direction": signal["direction"],
        "epic": epic,
        "expiry": str(instrument.get("expiry") or selected.get("expiry") or "-"),
        "forceOpen": True,
        "guaranteedStop": False,
        "limitDistance": round(limit_distance, 6),
        "orderType": "MARKET",
        "size": size,
        "stopDistance": round(stop_distance, 6),
        "timeInForce": "FILL_OR_KILL",
        "trailingStop": False,
    }

    intent = {
        "type": "TradeIntent",
        "canary_id": CANARY_REFERENCE,
        "environment": "DEMO_ONLY",
        "strategy": "V7_M5_EXHAUSTION_LIQUIDITY_REVERSAL",
        "epic": epic,
        "direction": signal["direction"],
        "size": size,
        "stop_distance": payload["stopDistance"],
        "limit_distance": payload["limitDistance"],
        "signal": signal,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(RUNTIME_PATH / "trade_intent.json", intent)

    order = ig.create_position(payload)
    deal_reference = str(order.get("dealReference") or "")
    if not deal_reference:
        raise IGError(f"Order acknowledgement missing dealReference: {safe_summary(order)}")

    confirmation = ig.confirm(deal_reference)
    deal_status = str(confirmation.get("dealStatus") or "").upper()
    status = str(confirmation.get("status") or "").upper()
    accepted = deal_status == "ACCEPTED" and status not in {"REJECTED", "DELETED"}

    evidence = {
        "canary_id": CANARY_REFERENCE,
        "environment": "DEMO_ONLY",
        "intent": intent,
        "ack": safe_summary(order),
        "confirmation": safe_summary(confirmation),
        "accepted": accepted,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(EVIDENCE_PATH, evidence)
    save_json(RUNTIME_PATH / "execution_evidence.json", evidence)

    if not accepted:
        raise IGError(f"Canary was not accepted: {safe_summary(confirmation)}")

    state.update(
        {
            "schema_version": 1,
            "canary_id": CANARY_REFERENCE,
            "completed": True,
            "deal_reference": deal_reference,
            "deal_id": confirmation.get("dealId"),
            "epic": epic,
            "direction": signal["direction"],
            "size": size,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_json(STATE_PATH, state)
    print(json.dumps({"status": "ONE_TRADE_CANARY_ACCEPTED", "state": state}, indent=2))
    print("AUREON_IG_STATUS=ONE_TRADE_CANARY_ACCEPTED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IGError as exc:
        RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
        err = {"status": "ERROR", "message": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
        save_json(RUNTIME_PATH / "error.json", err)
        print(json.dumps(err, indent=2), file=sys.stderr)
        raise SystemExit(2)
