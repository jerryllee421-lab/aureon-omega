#!/usr/bin/env python3
"""AUREON MT5 adapter: broker intelligence, guarded order preflight and tester control."""
from __future__ import annotations
import argparse, json, logging, math, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "mt5_adapter.json"
REPORTS, LOGS = ROOT / "reports", ROOT / "logs"
REPORTS.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOGS / "mt5_adapter.log", level=logging.INFO,
                    format="%(asctime)sZ %(levelname)s %(message)s")
log = logging.getLogger("aureon.mt5")

def now():
    return datetime.now(timezone.utc).isoformat()

def load_config():
    if not CONFIG.exists():
        raise RuntimeError("Missing config file: " + str(CONFIG))
    return json.loads(CONFIG.read_text(encoding="utf-8-sig"))

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)

def mt5_import():
    try:
        import MetaTrader5 as mt5
        return mt5
    except Exception as exc:
        raise RuntimeError("MetaTrader5 package unavailable. Run the one-click setup again.") from exc

def candidates(cfg):
    out = []
    if cfg.get("terminal_path"):
        out.append(Path(cfg["terminal_path"]))
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "APPDATA"):
        base = os.environ.get(key)
        if base:
            b = Path(base)
            out.extend([b/"MetaTrader 5"/"terminal64.exe", b/"MetaTrader 5"/"terminal.exe",
                        b/"Programs"/"MetaTrader 5"/"terminal64.exe"])
    unique, seen = [], set()
    for p in out:
        if str(p).lower() not in seen:
            seen.add(str(p).lower()); unique.append(p)
    return unique

def terminal_path(cfg, mt5=None):
    for p in candidates(cfg):
        if p.is_file():
            return p
    if mt5:
        ti = mt5.terminal_info()
        if ti and getattr(ti, "path", None):
            for p in (Path(ti.path)/"terminal64.exe", Path(ti.path)/"terminal.exe"):
                if p.is_file():
                    return p
    return None

def connect(mt5, cfg):
    p = terminal_path(cfg)
    ok = mt5.initialize(path=str(p)) if p else mt5.initialize()
    if not ok:
        raise RuntimeError("MT5 initialize failed: " + str(mt5.last_error()) +
                           ". Open MT5 manually and log in to the intended account.")
    log.info("MT5 initialized; terminal=%s", p or "auto")

def mode_name(mt5, ai):
    if not ai: return "UNKNOWN"
    v = getattr(ai, "trade_mode", None)
    if v == mt5.ACCOUNT_TRADE_MODE_DEMO: return "DEMO"
    if v == mt5.ACCOUNT_TRADE_MODE_CONTEST: return "CONTEST"
    if v == mt5.ACCOUNT_TRADE_MODE_REAL: return "REAL"
    return "UNKNOWN"

def plain(x):
    return x._asdict() if x is not None and hasattr(x, "_asdict") else (x if isinstance(x, dict) else {})

def broker_report(mt5, cfg):
    ti, ai = mt5.terminal_info(), mt5.account_info()
    symbols = {}
    aliases = cfg.get("symbols", {}).get("XAUUSD", ["XAUUSD", "GOLD", "XAUUSD."])
    for name in aliases:
        info = mt5.symbol_info(name)
        if not info: continue
        tick = mt5.symbol_info_tick(name)
        symbols[name] = {
            "name": info.name, "description": getattr(info,"description",None),
            "visible": getattr(info,"visible",None), "digits": getattr(info,"digits",None),
            "point": getattr(info,"point",None), "contract_size": getattr(info,"trade_contract_size",None),
            "tick_size": getattr(info,"trade_tick_size",None), "tick_value": getattr(info,"trade_tick_value",None),
            "tick_value_profit": getattr(info,"trade_tick_value_profit",None),
            "tick_value_loss": getattr(info,"trade_tick_value_loss",None),
            "volume_min": getattr(info,"volume_min",None), "volume_max": getattr(info,"volume_max",None),
            "volume_step": getattr(info,"volume_step",None), "stops_level_points": getattr(info,"trade_stops_level",None),
            "freeze_level_points": getattr(info,"trade_freeze_level",None), "trade_mode": getattr(info,"trade_mode",None),
            "filling_mode": getattr(info,"filling_mode",None), "spread_points": getattr(info,"spread",None),
            "bid": getattr(tick,"bid",None) if tick else None, "ask": getattr(tick,"ask",None) if tick else None,
            "tick_time_epoch": getattr(tick,"time",None) if tick else None,
            "market_data_status": "AVAILABLE" if tick and tick.bid > 0 and tick.ask >= tick.bid else "UNAVAILABLE"
        }
    report = {
        "schema_version": 1, "timestamp_utc": now(), "connected": bool(ti and ai),
        "terminal": {k:getattr(ti,k,None) for k in ("path","data_path","company","name","build","connected","trade_allowed","tradeapi_disabled")} if ti else {},
        "account": {
            "login_present": bool(getattr(ai,"login",0)) if ai else False,
            "server": getattr(ai,"server",None) if ai else None, "company": getattr(ai,"company",None) if ai else None,
            "currency": getattr(ai,"currency",None) if ai else None, "leverage": getattr(ai,"leverage",None) if ai else None,
            "trade_mode": mode_name(mt5,ai), "balance": getattr(ai,"balance",None) if ai else None,
            "equity": getattr(ai,"equity",None) if ai else None, "free_margin": getattr(ai,"margin_free",None) if ai else None,
            "margin_level": getattr(ai,"margin_level",None) if ai else None, "trade_allowed": getattr(ai,"trade_allowed",None) if ai else None,
            "trade_expert": getattr(ai,"trade_expert",None) if ai else None
        },
        "symbols": symbols,
        "safety": {"live_orders_enabled": cfg["execution"]["allow_live_orders"],
                   "demo_orders_enabled": cfg["execution"]["allow_demo_orders"],
                   "unknown_values_fail_closed": True, "probe_sent_orders": False}
    }
    save(REPORTS/"broker_intelligence.json", report)
    return report

def doctor(args):
    cfg = load_config()
    result = {"timestamp_utc":now(),"project_root":str(ROOT),"config_found":CONFIG.exists(),
              "python":sys.version,"terminal_candidates":[str(p) for p in candidates(cfg)],
              "terminal_found":any(p.is_file() for p in candidates(cfg)),
              "demo_orders_enabled":cfg["execution"]["allow_demo_orders"],
              "live_orders_enabled":cfg["execution"]["allow_live_orders"],"broker_probe":"NOT_RUN","issues":[]}
    try:
        mt5 = mt5_import()
        result["mt5_python_version"] = getattr(mt5,"__version__","installed")
        try:
            connect(mt5,cfg); report=broker_report(mt5,cfg)
            result["broker_probe"]="CONNECTED" if report["connected"] else "PARTIAL"
            result["broker_server"]=report["account"]["server"]
            result["account_mode"]=report["account"]["trade_mode"]
            result["symbols_found"]=list(report["symbols"])
        except Exception as e: result["issues"].append(str(e))
        finally:
            try: mt5.shutdown()
            except Exception: pass
    except Exception as e: result["issues"].append(str(e))
    save(REPORTS/"mt5_doctor.json",result); print(json.dumps(result,indent=2))
    return 0

def connected(fn):
    def run(args):
        cfg=load_config(); mt5=mt5_import()
        try:
            connect(mt5,cfg); return fn(args,mt5,cfg)
        except Exception as e:
            log.exception("command failed"); print("BLOCKED:",e,file=sys.stderr); return 2
        finally:
            try: mt5.shutdown()
            except Exception: pass
    return run

@connected
def status(args,mt5,cfg):
    r=broker_report(mt5,cfg); print(json.dumps(r,indent=2)); return 0 if r["connected"] else 2

@connected
def symbols(args,mt5,cfg):
    rows=[]
    for s in mt5.symbols_get() or []:
        if args.filter.lower() in s.name.lower() or args.filter.lower() in (getattr(s,"description","") or "").lower():
            rows.append({k:getattr(s,k,None) for k in ("name","description","visible","digits","point","trade_contract_size","trade_tick_size","trade_tick_value","volume_min","volume_max","volume_step","trade_mode","spread")})
    save(REPORTS/"broker_symbols.json",{"timestamp_utc":now(),"count":len(rows),"symbols":rows})
    print(json.dumps({"count":len(rows),"saved_to":str(REPORTS/"broker_symbols.json"),"symbols":rows[:args.limit]},indent=2)); return 0

@connected
def quote(args,mt5,cfg):
    s=mt5.symbol_info(args.symbol)
    if not s: print("SYMBOL_NOT_FOUND:",args.symbol); return 3
    if not s.visible and not mt5.symbol_select(args.symbol,True): print("SYMBOL_SELECT_FAILED"); return 4
    t=mt5.symbol_info_tick(args.symbol)
    if not t or t.bid<=0 or t.ask<t.bid: print("QUOTE_UNAVAILABLE"); return 5
    age=max(0,datetime.now(timezone.utc).timestamp()-t.time)
    r={"timestamp_utc":now(),"symbol":args.symbol,"bid":t.bid,"ask":t.ask,"spread_price":t.ask-t.bid,
       "spread_points":(t.ask-t.bid)/s.point if s.point else None,"quote_age_seconds":age,
       "quote_fresh":age<=cfg["quote_max_age_seconds"],"digits":s.digits,"point":s.point,
       "tick_size":s.trade_tick_size,"tick_value":s.trade_tick_value,"volume_min":s.volume_min,
       "volume_max":s.volume_max,"volume_step":s.volume_step}
    save(REPORTS/"latest_quote.json",r); print(json.dumps(r,indent=2)); return 0 if r["quote_fresh"] else 6

@connected
def positions(args,mt5,cfg):
    p,o=mt5.positions_get(),mt5.orders_get()
    r={"timestamp_utc":now(),"positions":[plain(x) for x in (p or [])],"pending_orders":[plain(x) for x in (o or [])],
       "positions_error":str(mt5.last_error()) if p is None else None,"orders_error":str(mt5.last_error()) if o is None else None}
    save(REPORTS/"open_exposure.json",r); print(json.dumps(r,indent=2)); return 0 if p is not None and o is not None else 3

def order(args):
    cfg=load_config(); ex=cfg["execution"]; mode=args.mode.upper()
    if mode=="DEMO" and (not ex["allow_demo_orders"] or not args.confirm_demo):
        print("SAFETY_BLOCK: enable allow_demo_orders in config and pass --confirm-demo."); return 10
    if mode=="LIVE":
        if not ex["allow_live_orders"] or not args.confirm_live:
            print("SAFETY_BLOCK: live orders are disabled; config and --confirm-live required."); return 11
        if input('Type exactly "I ACCEPT LIVE TRADING RISK": ').strip()!="I ACCEPT LIVE TRADING RISK":
            print("CANCELLED"); return 12
    mt5=mt5_import()
    try:
        connect(mt5,cfg); ai,ti=mt5.account_info(),mt5.terminal_info()
        actual=mode_name(mt5,ai)
        if mode!=actual: print("SAFETY_BLOCK: requested",mode,"but broker reports",actual); return 13
        if not ai or not ti or not ti.connected or not ai.trade_allowed or not ai.trade_expert or ti.tradeapi_disabled:
            print("SAFETY_BLOCK: account/terminal trading permission unavailable"); return 14
        s=mt5.symbol_info(args.symbol)
        if not s: print("SAFETY_BLOCK: symbol unknown"); return 15
        if not s.visible and not mt5.symbol_select(args.symbol,True): print("SAFETY_BLOCK: cannot select symbol"); return 16
        t=mt5.symbol_info_tick(args.symbol)
        if not t or t.bid<=0 or t.ask<t.bid: print("SAFETY_BLOCK: invalid quote"); return 17
        age=datetime.now(timezone.utc).timestamp()-t.time
        if age<0 or age>cfg["quote_max_age_seconds"]: print("SAFETY_BLOCK: stale quote"); return 18
        spread=(t.ask-t.bid)/s.point if s.point else 1e99
        if spread>ex["max_spread_points"]: print("SAFETY_BLOCK: spread exceeds cap:",spread); return 19
        v=args.volume
        if v<=0 or v>ex["max_volume_lots"] or v<s.volume_min or v>s.volume_max:
            print("SAFETY_BLOCK: volume outside configured or broker limits"); return 20
        step=float(s.volume_step or 0)
        if step and abs(round(v/step)*step-v)>1e-8: print("SAFETY_BLOCK: volume step mismatch"); return 21
        side=args.side.upper(); entry=t.ask if side=="BUY" else t.bid
        if side=="BUY" and not args.sl<entry<args.tp: print("SAFETY_BLOCK: BUY requires SL < ask < TP"); return 22
        if side=="SELL" and not args.tp<entry<args.sl: print("SAFETY_BLOCK: SELL requires TP < bid < SL"); return 23
        dist=float(s.trade_stops_level or 0)*float(s.point or 0)
        if dist and (abs(entry-args.sl)<dist or abs(args.tp-entry)<dist): print("SAFETY_BLOCK: SL/TP inside broker stop distance"); return 24
        tick_size=float(s.trade_tick_size or 0); tick_value=float(s.trade_tick_value_loss or s.trade_tick_value or 0)
        risk=abs(entry-args.sl)/tick_size*tick_value*v/float(ai.equity)*100 if tick_size>0 and tick_value>0 and ai.equity>0 else None
        if risk is None or risk>ex["max_risk_percent"]: print("SAFETY_BLOCK: risk cannot be verified or exceeds cap:",risk); return 25
        typ=mt5.ORDER_TYPE_BUY if side=="BUY" else mt5.ORDER_TYPE_SELL
        req={"action":mt5.TRADE_ACTION_DEAL,"symbol":args.symbol,"volume":v,"type":typ,"price":entry,
             "sl":args.sl,"tp":args.tp,"deviation":ex["deviation_points"],"magic":ex["magic"],
             "comment":"AUREON guarded adapter","type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.ORDER_FILLING_RETURN}
        chk=mt5.order_check(req); ch=plain(chk)
        save(REPORTS/"last_order_check.json",{"timestamp_utc":now(),"mode":mode,"request":req,"check":ch})
        if chk is None or getattr(chk,"retcode",None)!=0:
            print("SAFETY_BLOCK: order_check not successful; no order sent."); print(json.dumps(ch,indent=2)); return 26
        print(json.dumps({"preflight_passed":True,"mode":mode,"symbol":args.symbol,"side":side,"volume":v,"estimated_risk_percent":risk,"request":req},indent=2))
        if not args.send: print("DRY RUN: no order sent. Add --send only after reviewing."); return 0
        phrase=f"SEND {mode} {side} {args.symbol} {v}"
        if input(f'Type exactly "{phrase}": ').strip()!=phrase: print("CANCELLED"); return 27
        res=mt5.order_send(req); rr=plain(res)
        save(REPORTS/"last_order_result.json",{"timestamp_utc":now(),"mode":mode,"request":req,"result":rr})
        print(json.dumps(rr,indent=2))
        return 0 if res and res.retcode in (mt5.TRADE_RETCODE_DONE,mt5.TRADE_RETCODE_PLACED,getattr(mt5,"TRADE_RETCODE_DONE_PARTIAL",-1)) else 28
    finally:
        try: mt5.shutdown()
        except Exception: pass

def tester(args):
    cfg=load_config(); term=terminal_path(cfg)
    if not term: print("BLOCKED: MT5 terminal not found; set terminal_path in config."); return 2
    start=datetime.strptime(args.start,"%Y-%m-%d"); end=datetime.strptime(args.end,"%Y-%m-%d")
    if end<=start: print("BLOCKED: end date must be after start date."); return 3
    model={"generated":0,"every_tick":1,"ohlc_1m":2,"open_prices":3,"real_ticks":4}[args.model]
    ini=ROOT/"runtime"/"mt5"/"strategy_tester.ini"; ini.parent.mkdir(parents=True,exist_ok=True)
    report=REPORTS/("tester_"+datetime.now().strftime("%Y%m%d_%H%M%S"))
    lines=["[Tester]",f"Expert={args.expert}",f"Symbol={args.symbol}",f"Period={args.period}",f"Model={model}",
           f"FromDate={args.start.replace('-','.')}",f"ToDate={args.end.replace('-','.')}",
           f"ForwardMode={1 if args.forward else 0}",f"Deposit={args.deposit:.2f}",f"Currency={args.currency}",
           f"Leverage={args.leverage}","Optimization=0",f"Report={report}","ReplaceReport=1","ShutdownTerminal=1","Visual=0"]
    ini.write_text("\\n".join(lines)+"\\n",encoding="utf-8")
    r={"timestamp_utc":now(),"terminal":str(term),"ini":str(ini),"expert":args.expert,"symbol":args.symbol,
       "period":args.period,"model":args.model,"start":args.start,"end":args.end,"report_prefix":str(report),"launched":False}
    save(REPORTS/"strategy_tester_last.json",r); print(json.dumps(r,indent=2))
    if not args.run: print("CONFIG ONLY. Review the INI; add --run --confirm to launch."); return 0
    if not args.confirm: print("BLOCKED: --confirm required to launch tester."); return 4
    proc=subprocess.Popen([str(term),f"/config:{ini}"],cwd=str(term.parent))
    r["launched"]=True; r["process_id"]=proc.pid; r["launched_at_utc"]=now()
    save(REPORTS/"strategy_tester_last.json",r); print("TESTER_LAUNCHED pid=",proc.pid); return 0

def main():
    p=argparse.ArgumentParser(description="AUREON MT5 broker intelligence, guarded execution and tester control")
    sp=p.add_subparsers(dest="cmd",required=True)
    x=sp.add_parser("doctor"); x.set_defaults(fn=doctor)
    x=sp.add_parser("status"); x.set_defaults(fn=status)
    x=sp.add_parser("symbols"); x.add_argument("--filter",default=""); x.add_argument("--limit",type=int,default=100); x.set_defaults(fn=symbols)
    x=sp.add_parser("quote"); x.add_argument("--symbol",default="XAUUSD"); x.set_defaults(fn=quote)
    x=sp.add_parser("positions"); x.set_defaults(fn=positions)
    x=sp.add_parser("order"); x.add_argument("--mode",choices=["DEMO","LIVE"],required=True); x.add_argument("--symbol",required=True)
    x.add_argument("--side",choices=["BUY","SELL"],required=True); x.add_argument("--volume",type=float,required=True)
    x.add_argument("--sl",type=float,required=True); x.add_argument("--tp",type=float,required=True)
    x.add_argument("--confirm-demo",action="store_true"); x.add_argument("--confirm-live",action="store_true")
    x.add_argument("--send",action="store_true"); x.set_defaults(fn=order)
    x=sp.add_parser("tester"); x.add_argument("--expert",required=True); x.add_argument("--symbol",default="XAUUSD")
    x.add_argument("--period",default="M1"); x.add_argument("--start",required=True); x.add_argument("--end",required=True)
    x.add_argument("--model",choices=["generated","every_tick","ohlc_1m","open_prices","real_ticks"],default="real_ticks")
    x.add_argument("--deposit",type=float,default=10000); x.add_argument("--currency",default="USD")
    x.add_argument("--leverage",default="1:100"); x.add_argument("--forward",action="store_true")
    x.add_argument("--run",action="store_true"); x.add_argument("--confirm",action="store_true"); x.set_defaults(fn=tester)
    a=p.parse_args()
    try: return int(a.fn(a) or 0)
    except KeyboardInterrupt: return 130
    except Exception as e:
        log.exception("fatal"); print("ERROR:",e,file=sys.stderr); return 1

if __name__=="__main__":
    raise SystemExit(main())
