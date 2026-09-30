"""AUREON Ω V2.17 cTrader Open API DEMO transport.

Fail-closed Linux adapter. It deliberately does not invent/approximate V2.17 signals:
strategy parity must be ported and tested before order submission is enabled.
"""
import os, sys
from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAAccountAuthReq, ProtoOASymbolsListReq
)
from twisted.internet import reactor

ENV=os.getenv("CTRADER_ENV","demo").lower()
CLIENT_ID=os.getenv("CTRADER_CLIENT_ID","")
CLIENT_SECRET=os.getenv("CTRADER_CLIENT_SECRET","")
TOKEN=os.getenv("CTRADER_ACCESS_TOKEN","")
ACCOUNT=os.getenv("CTRADER_ACCOUNT_ID","")
SYMBOL=os.getenv("AUREON_SYMBOL","XAUUSD").upper()
EXEC_ENABLED=os.getenv("AUREON_EXECUTION_ENABLED","false").lower()=="true"

if ENV!="demo":
    raise SystemExit("HARD BLOCK: AUREON certification executor accepts DEMO only")
if not SYMBOL.startswith("XAU"):
    raise SystemExit("HARD BLOCK: Gold/XAU symbols only")
if not all((CLIENT_ID,CLIENT_SECRET,TOKEN)):
    raise SystemExit("Missing cTrader application credentials/access token")
if EXEC_ENABLED:
    raise SystemExit("HARD BLOCK: order submission remains disabled until Open API strategy-parity certification passes")

client=Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

def send(msg):
    d=client.send(msg)
    d.addErrback(lambda f: print("SEND_ERROR", f))
    return d

def connected(_client):
    print("CONNECTED DEMO transport")
    r=ProtoOAApplicationAuthReq(); r.clientId=CLIENT_ID; r.clientSecret=CLIENT_SECRET; send(r)

def received(_client, message):
    obj=Protobuf.extract(message)
    name=type(obj).__name__
    print("EVENT", name)
    if name=="ProtoOAApplicationAuthRes":
        r=ProtoOAGetAccountListByAccessTokenReq(); r.accessToken=TOKEN; send(r)
    elif name=="ProtoOAGetAccountListByAccessTokenRes":
        accounts=list(obj.ctidTraderAccount)
        demo=[a for a in accounts if not getattr(a,"isLive",False)]
        if not demo: raise SystemExit("HARD BLOCK: token has no DEMO account")
        selected=None
        if ACCOUNT:
            selected=next((a for a in demo if str(a.ctidTraderAccountId)==ACCOUNT),None)
            if selected is None: raise SystemExit("HARD BLOCK: requested account is not authorized DEMO")
        else:
            selected=demo[0]
        globals()["ACCOUNT"]=str(selected.ctidTraderAccountId)
        r=ProtoOAAccountAuthReq(); r.ctidTraderAccountId=selected.ctidTraderAccountId; r.accessToken=TOKEN; send(r)
    elif name=="ProtoOAAccountAuthRes":
        r=ProtoOASymbolsListReq(); r.ctidTraderAccountId=int(ACCOUNT); r.includeArchivedSymbols=False; send(r)
    elif name=="ProtoOASymbolsListRes":
        matches=[s for s in obj.symbol if SYMBOL in getattr(s,"symbolName","").upper()]
        if not matches:
            print("PREFLIGHT_FAIL: XAU symbol not found")
            reactor.stop(); return
        print("PREFLIGHT_PASS account=%s symbol=%s execution_enabled=false" % (ACCOUNT, matches[0].symbolName))
        print("NEXT_GATE: strategy semantic parity + reconciliation tests; no order sent")
        reactor.stop()

client.setConnectedCallback(connected)
client.setMessageReceivedCallback(received)
client.setDisconnectedCallback(lambda _c,reason: print("DISCONNECTED",reason))
client.startService()
reactor.run()
