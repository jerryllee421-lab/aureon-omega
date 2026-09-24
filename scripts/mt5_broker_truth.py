from __future__ import annotations

"""Non-trading MT5 broker truth probe with persistent diagnostics."""

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
    try: return datetime.fromtimestamp(int(ts),tz=timezone.utc).isoformat()
    except Exception: return None


def info_payload(info, tick=None):
    fields=["name","path","description","currency_base","currency_profit","currency_margin",
            "digits","point","trade_tick_size","trade_tick_value","trade_tick_value_profit",
            "trade_tick_value_loss","trade_contract_size","volume_min","volume_max","volume_step",
            "volume_limit","trade_mode","trade_calc_mode","trade_stops_level","trade_freeze_level",
            "filling_mode","order_mode","expiration_mode","order_gtc_mode","spread","spread_float",
            "visible","select"]
    out={k:getattr(info,k,None) for k in fields}
    if tick is not None:
        out["tick"]={"time":utc_iso(getattr(tick,"time",0)),"bid":as_float(getattr(tick,"bid",0)),
                     "ask":as_float(getattr(tick,"ask",0)),"last":as_float(getattr(tick,"last",0)),
                     "volume":as_float(getattr(tick,"volume",0))}
        p=as_float(out.get("point"))
        if p>0 and out["tick"]["ask"]>0 and out["tick"]["bid"]>0:
            out["observed_spread_points"]=(out["tick"]["ask"]-out["tick"]["bid"])/p
    return out


def history_sample(mt5, symbol: str):
    specs=[("M1",mt5.TIMEFRAME_M1),("M5",mt5.TIMEFRAME_M5),("M15",mt5.TIMEFRAME_M15),
           ("H1",mt5.TIMEFRAME_H1),("H4",mt5.TIMEFRAME_H4)]
    out={}
    for label,tf in specs:
        rates=None
        for _ in range(8):
            rates=mt5.copy_rates_from_pos(symbol,tf,0,5000)
            if rates is not None and len(rates): break
            time.sleep(1)
        out[label]=({"bars":0,"first":None,"last":None} if rates is None or not len(rates) else
                    {"bars":int(len(rates)),"first":utc_iso(rates[0]["time"]),"last":utc_iso(rates[-1]["time"])})
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terminal",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)

    login=os.environ.get("MT5_DEMO_LOGIN","").strip()
    password=os.environ.get("MT5_DEMO_PASSWORD","").strip()
    server=os.environ.get("MT5_DEMO_SERVER","PXBTTrading-1").strip() or "PXBTTrading-1"
    diag={"server":server,"terminal":str(args.terminal),"orders_sent":0,
          "live_trading_enabled_by_workflow":False,"stages":[]}

    def fail(message, code=2, mt5=None):
        diag["failure"]=message
        if mt5 is not None:
            try: diag["mt5_last_error"]=list(mt5.last_error())
            except Exception: pass
        (args.out/"probe_failure.json").write_text(json.dumps(diag,indent=2,default=str))
        print("ASTRA_BROKER_PROBE_FAIL "+message)
        raise SystemExit(code)

    if not login or not password: fail("MT5 demo credentials are required")
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        fail(f"MetaTrader5 Python package unavailable: {e}")

    attempts=[
        {"portable":True,"login":int(login),"password":password,"server":server},
        {"portable":True},
        {"login":int(login),"password":password,"server":server},
        {},
    ]
    ok=False
    for i,kw in enumerate(attempts,1):
        try:
            ok=mt5.initialize(path=str(args.terminal),timeout=120000,**kw)
        except Exception as e:
            diag["stages"].append({"initialize_attempt":i,"kwargs":sorted(kw),"exception":repr(e)})
            ok=False
        if ok:
            diag["stages"].append({"initialize_attempt":i,"kwargs":sorted(kw),"success":True})
            break
        diag["stages"].append({"initialize_attempt":i,"kwargs":sorted(kw),"success":False,
                               "last_error":list(mt5.last_error())})
        try: mt5.shutdown()
        except Exception: pass
    if not ok: fail("all MT5 initialize/attach attempts failed",3,mt5)

    try:
        ti=mt5.terminal_info(); ai=mt5.account_info()
        diag["terminal_info"]={"connected":bool(getattr(ti,"connected",False)) if ti else False,
                               "trade_allowed":bool(getattr(ti,"trade_allowed",False)) if ti else False,
                               "tradeapi_disabled":bool(getattr(ti,"tradeapi_disabled",False)) if ti else None}
        diag["account_connected"]=bool(ai)
        symbols=mt5.symbols_get()
        if symbols is None: fail("symbols_get failed",4,mt5)
        diag["symbol_count"]=len(symbols)
        candidates=[]
        for s in symbols:
            sc=score_symbol(s.name)
            if sc<0: continue
            mt5.symbol_select(s.name,True)
            info=mt5.symbol_info(s.name) or s
            tick=mt5.symbol_info_tick(s.name)
            row=info_payload(info,tick); row["score"]=sc; candidates.append(row)
            print(f"ASTRA_BROKER_CANDIDATE symbol={s.name} score={sc} trade_mode={getattr(info,'trade_mode',None)} point={getattr(info,'point',None)} volume_min={getattr(info,'volume_min',None)}")
        if not candidates: fail("no XAU/GOLD symbols returned by broker",5,mt5)

        def rank(x):
            tick=x.get("tick") or {}; enabled=1 if int(x.get("trade_mode") or 0)!=0 else 0
            has_tick=1 if as_float(tick.get("bid"))>0 and as_float(tick.get("ask"))>0 else 0
            return (int(x["score"]),enabled,has_tick)
        candidates.sort(key=rank,reverse=True)
        selected=candidates[0]; symbol=selected["name"]
        if not mt5.symbol_select(symbol,True): fail(f"could not select discovered symbol {symbol}",6,mt5)
        selected["history_sample"]=history_sample(mt5,symbol)
        payload={"server":server,"selected_symbol":symbol,"selected":selected,
                 "candidate_count":len(candidates),"candidates":candidates,
                 "terminal":diag.get("terminal_info",{}),"orders_sent":0,"live_trading_enabled_by_workflow":False}
        (args.out/"broker_truth.json").write_text(json.dumps(payload,indent=2,default=str))
        (args.out/"selected-symbol.txt").write_text(symbol+"\n")
        print(f"ASTRA_BROKER_SELECTED symbol={symbol} score={selected['score']}")
        print(f"ASTRA_BROKER_PROBE_OK symbol={symbol} digits={selected.get('digits')} point={selected.get('point')} tick_size={selected.get('trade_tick_size')} contract={selected.get('trade_contract_size')} vol_min={selected.get('volume_min')} vol_step={selected.get('volume_step')} stops={selected.get('trade_stops_level')} freeze={selected.get('trade_freeze_level')} filling={selected.get('filling_mode')} order_mode={selected.get('order_mode')} expiration_mode={selected.get('expiration_mode')} spread_points={selected.get('observed_spread_points')}")
    finally:
        mt5.shutdown()


if __name__=="__main__": main()
