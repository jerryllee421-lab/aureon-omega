from __future__ import annotations

"""Non-trading MT5 broker truth probe.

Connects to the installed MT5 terminal through MetaTrader5's Python bridge,
discovers the broker server from the locally installed terminal catalogue when
possible, enumerates broker symbols, resolves the most plausible tradable
Gold/XAU symbol and writes a sanitized execution-specification fingerprint.

It never sends an order and never writes credentials to artifacts/logs.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def score_symbol(name: str) -> int:
    s=name.upper()
    if s=="XAUUSD": return 1000
    if s.startswith("XAUUSD"): return 950
    if "XAUUSD" in s: return 900
    if "XAU" in s and "USD" in s: return 850
    if "GOLD" in s and "USD" in s: return 800
    if "XAU" in s: return 700
    if "GOLD" in s: return 650
    return -1


def as_float(x):
    try: return float(x)
    except Exception: return 0.0


def utc_iso(ts):
    try:
        return datetime.fromtimestamp(int(ts),tz=timezone.utc).isoformat()
    except Exception:
        return None


def info_payload(info, tick=None):
    fields=[
        "name","path","description","currency_base","currency_profit","currency_margin",
        "digits","point","trade_tick_size","trade_tick_value","trade_tick_value_profit",
        "trade_tick_value_loss","trade_contract_size","volume_min","volume_max","volume_step",
        "volume_limit","trade_mode","trade_calc_mode","trade_stops_level","trade_freeze_level",
        "filling_mode","order_mode","expiration_mode","order_gtc_mode","spread","spread_float",
        "visible","select",
    ]
    out={k:getattr(info,k,None) for k in fields}
    if tick is not None:
        out["tick"]={
            "time":utc_iso(getattr(tick,"time",0)),
            "bid":as_float(getattr(tick,"bid",0)),
            "ask":as_float(getattr(tick,"ask",0)),
            "last":as_float(getattr(tick,"last",0)),
            "volume":as_float(getattr(tick,"volume",0)),
        }
        p=as_float(out.get("point"))
        if p>0 and out["tick"]["ask"]>0 and out["tick"]["bid"]>0:
            out["observed_spread_points"]=(out["tick"]["ask"]-out["tick"]["bid"])/p
    return out


def history_sample(mt5, symbol: str):
    specs=[
        ("M1",mt5.TIMEFRAME_M1),("M5",mt5.TIMEFRAME_M5),("M15",mt5.TIMEFRAME_M15),
        ("H1",mt5.TIMEFRAME_H1),("H4",mt5.TIMEFRAME_H4),
    ]
    out={}
    for label,tf in specs:
        rates=None
        for _ in range(8):
            rates=mt5.copy_rates_from_pos(symbol,tf,0,5000)
            if rates is not None and len(rates):
                break
            time.sleep(1)
        if rates is None or not len(rates):
            out[label]={"bars":0,"first":None,"last":None}
        else:
            out[label]={
                "bars":int(len(rates)),
                "first":utc_iso(rates[0]["time"]),
                "last":utc_iso(rates[-1]["time"]),
            }
    return out


def discover_server_candidates(terminal: Path, configured: str):
    """Return only server names advertised locally by the installed terminal.

    We do not brute-force arbitrary network endpoints. The configured server is
    tried first, followed by .srv catalogue entries shipped/created by MT5.
    """
    out=[]
    seen=set()

    def add(x):
        x=(x or "").strip()
        if not x or x.lower() in seen:
            return
        seen.add(x.lower())
        out.append(x)

    add(configured)

    roots=[terminal.parent]
    for env_name in ("APPDATA","PROGRAMDATA","LOCALAPPDATA"):
        raw=os.environ.get(env_name)
        if raw:
            p=Path(raw)
            roots += [p/"MetaQuotes",p/"MetaTrader 5"]

    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*.srv"):
                add(p.stem)
        except Exception:
            pass

    # Prefer broker-specific catalogue entries after the configured value.
    broker=[x for x in out[1:] if any(k in x.upper() for k in ("PXBT","PRIMEXBT"))]
    other=[x for x in out[1:] if x not in broker]
    return out[:1]+broker+other


def authenticate(mt5, terminal: Path, login: int, password: str, configured_server: str, out_dir: Path):
    diagnostics={
        "configured_server":configured_server,
        "initialize_without_credentials":None,
        "server_candidates":[],
        "attempts":[],
    }

    # First start the broker terminal itself without forcing credentials. This
    # lets the installed broker catalogue load before explicit login attempts.
    init_ok=mt5.initialize(path=str(terminal),timeout=120000,portable=True)
    diagnostics["initialize_without_credentials"]=bool(init_ok)
    if not init_ok:
        diagnostics["initialize_error"]=list(mt5.last_error())

    candidates=discover_server_candidates(terminal,configured_server)
    diagnostics["server_candidates"]=candidates

    # First try the terminal's current/default server if initialization worked.
    if init_ok:
        ok=mt5.login(login,password=password,timeout=45000)
        err=list(mt5.last_error())
        diagnostics["attempts"].append({"server":"TERMINAL_DEFAULT","ok":bool(ok),"error":err})
        if ok:
            ai=mt5.account_info()
            server=getattr(ai,"server",None) if ai else None
            diagnostics["resolved_server"]=server or "TERMINAL_DEFAULT"
            (out_dir/"auth_diagnostics.json").write_text(json.dumps(diagnostics,indent=2,default=str))
            return diagnostics["resolved_server"]

    for server in candidates:
        if not init_ok:
            # A failed no-credential initialization can still recover when the
            # correct broker server/account is supplied directly.
            ok=mt5.initialize(
                path=str(terminal),login=login,password=password,server=server,
                timeout=120000,portable=True,
            )
        else:
            ok=mt5.login(login,password=password,server=server,timeout=45000)

        err=list(mt5.last_error())
        diagnostics["attempts"].append({"server":server,"ok":bool(ok),"error":err})
        if ok:
            ai=mt5.account_info()
            resolved=getattr(ai,"server",None) if ai else None
            diagnostics["resolved_server"]=resolved or server
            (out_dir/"auth_diagnostics.json").write_text(json.dumps(diagnostics,indent=2,default=str))
            return diagnostics["resolved_server"]

    (out_dir/"auth_diagnostics.json").write_text(json.dumps(diagnostics,indent=2,default=str))
    return None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terminal",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)

    login_raw=os.environ.get("MT5_DEMO_LOGIN","").strip()
    password=os.environ.get("MT5_DEMO_PASSWORD","").strip()
    configured_server=os.environ.get("MT5_DEMO_SERVER","").strip()
    if not login_raw or not password:
        raise SystemExit("MT5 demo credentials are required")
    try:
        login=int(login_raw)
    except ValueError:
        raise SystemExit("MT5 demo login is not numeric")

    try:
        import MetaTrader5 as mt5
    except Exception as e:
        raise SystemExit(f"MetaTrader5 Python package unavailable: {e}")

    resolved_server=authenticate(mt5,args.terminal,login,password,configured_server,args.out)
    if not resolved_server:
        err=mt5.last_error()
        mt5.shutdown()
        raise SystemExit(
            "MT5 authorization failed for the configured/local broker server catalogue. "
            f"Last bridge error: {err}. See auth_diagnostics.json."
        )

    try:
        symbols=mt5.symbols_get()
        if symbols is None:
            raise SystemExit(f"symbols_get failed: {mt5.last_error()}")

        candidates=[]
        for s in symbols:
            sc=score_symbol(s.name)
            if sc<0:
                continue
            mt5.symbol_select(s.name,True)
            info=mt5.symbol_info(s.name) or s
            tick=mt5.symbol_info_tick(s.name)
            row=info_payload(info,tick)
            row["score"]=sc
            candidates.append(row)
            print(
                "ASTRA_BROKER_CANDIDATE "
                f"symbol={s.name} score={sc} trade_mode={getattr(info,'trade_mode',None)} "
                f"point={getattr(info,'point',None)} volume_min={getattr(info,'volume_min',None)}"
            )

        if not candidates:
            print("ASTRA_BROKER_PROBE_FAIL no XAU/GOLD symbols returned by broker")
            raise SystemExit(2)

        def rank(x):
            tick=x.get("tick") or {}
            enabled=1 if int(x.get("trade_mode") or 0)!=0 else 0
            has_tick=1 if as_float(tick.get("bid"))>0 and as_float(tick.get("ask"))>0 else 0
            return (int(x["score"]),enabled,has_tick)

        candidates.sort(key=rank,reverse=True)
        selected=candidates[0]
        symbol=selected["name"]
        if not mt5.symbol_select(symbol,True):
            raise SystemExit(f"Could not select discovered symbol {symbol}: {mt5.last_error()}")

        selected["history_sample"]=history_sample(mt5,symbol)
        terminal=mt5.terminal_info()
        account=mt5.account_info()
        payload={
            "server":resolved_server,
            "selected_symbol":symbol,
            "selected":selected,
            "candidate_count":len(candidates),
            "candidates":candidates,
            "terminal":{
                "connected":bool(getattr(terminal,"connected",False)) if terminal else False,
                "trade_allowed":bool(getattr(terminal,"trade_allowed",False)) if terminal else False,
                "tradeapi_disabled":bool(getattr(terminal,"tradeapi_disabled",False)) if terminal else None,
            },
            "account":{
                "server":getattr(account,"server",None) if account else None,
                "currency":getattr(account,"currency",None) if account else None,
                "leverage":getattr(account,"leverage",None) if account else None,
                "trade_mode":getattr(account,"trade_mode",None) if account else None,
            },
            "orders_sent":0,
            "live_trading_enabled_by_workflow":False,
        }
        (args.out/"broker_truth.json").write_text(json.dumps(payload,indent=2,default=str))
        (args.out/"selected-symbol.txt").write_text(symbol+"\n")
        (args.out/"resolved-server.txt").write_text(str(resolved_server)+"\n")
        print(f"ASTRA_BROKER_SELECTED symbol={symbol} score={selected['score']}")
        print(
            "ASTRA_BROKER_PROBE_OK "
            f"symbol={symbol} digits={selected.get('digits')} point={selected.get('point')} "
            f"tick_size={selected.get('trade_tick_size')} contract={selected.get('trade_contract_size')} "
            f"vol_min={selected.get('volume_min')} vol_step={selected.get('volume_step')} "
            f"stops={selected.get('trade_stops_level')} freeze={selected.get('trade_freeze_level')} "
            f"filling={selected.get('filling_mode')} order_mode={selected.get('order_mode')} "
            f"expiration_mode={selected.get('expiration_mode')} spread_points={selected.get('observed_spread_points')}"
        )
    finally:
        mt5.shutdown()


if __name__=="__main__":
    main()
