"""AUREON Ω V2.17 cTrader Open API DEMO preflight transport.

Zero-order, fail-closed broker preflight. This module authenticates only against the
cTrader DEMO endpoint, verifies the configured Pepperstone DEMO account, resolves
the intended Gold symbol and broker specification, subscribes to one live quote,
then exits. It contains no order-submission message type.
"""
import hashlib
import os
import time

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAAccountAuthReq,
    ProtoOATraderReq,
    ProtoOASymbolsListReq,
    ProtoOASymbolByIdReq,
    ProtoOASubscribeSpotsReq,
)
from twisted.internet import reactor

ENV = os.getenv("CTRADER_ENV", "demo").lower()
CLIENT_ID = os.getenv("CTRADER_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET", "")
TOKEN = os.getenv("CTRADER_ACCESS_TOKEN", "")
ACCOUNT = os.getenv("CTRADER_ACCOUNT_ID", "")
SYMBOL = os.getenv("AUREON_SYMBOL", "XAUUSD").upper()
EXPECTED_BROKER = os.getenv("AUREON_EXPECTED_BROKER", "Pepperstone")
EXEC_ENABLED = os.getenv("AUREON_EXECUTION_ENABLED", "false").lower() == "true"

if ENV != "demo":
    raise SystemExit("HARD BLOCK: AUREON certification preflight accepts DEMO only")
if not SYMBOL.startswith("XAU"):
    raise SystemExit("HARD BLOCK: Gold/XAU symbols only")
if not all((CLIENT_ID, CLIENT_SECRET, TOKEN, ACCOUNT)):
    raise SystemExit("Missing secure cTrader application credentials/access token/account id")
if EXEC_ENABLED:
    raise SystemExit("HARD BLOCK: zero-order preflight requires execution disabled")

client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

state = {
    "account_id": None,
    "account_hash": None,
    "broker": None,
    "trader_ready": False,
    "symbol_id": None,
    "symbol_name": None,
    "symbol_ready": False,
    "spot_ready": False,
    "bid": None,
    "ask": None,
    "spot_age_seconds": None,
    "balance": None,
    "money_digits": None,
    "account_type": None,
    "access_rights": None,
    "digits": None,
    "pip_position": None,
    "min_volume": None,
    "max_volume": None,
    "step_volume": None,
    "lot_size": None,
    "trading_mode": None,
    "measurement_units": None,
}


def safe_hash(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def norm_symbol(value):
    return "".join(ch for ch in str(value).upper() if ch.isalnum())


def stop_fail(reason):
    print(f"PREFLIGHT_FAIL reason={reason}")
    if reactor.running:
        reactor.stop()


def send(msg):
    d = client.send(msg)
    d.addErrback(lambda failure: stop_fail("SEND_ERROR_" + failure.type.__name__))
    return d


def maybe_finish():
    if not (state["trader_ready"] and state["symbol_ready"] and state["spot_ready"]):
        return

    if state["bid"] is None or state["ask"] is None:
        stop_fail("QUOTE_INCOMPLETE")
        return

    if state["spot_age_seconds"] is None or state["spot_age_seconds"] > 3.0:
        stop_fail("STALE_SPOT")
        return

    spread = state["ask"] - state["bid"]
    print(
        "PREFLIGHT_PASS "
        f"environment=demo isLive=false broker={state['broker']} "
        f"accountHash={state['account_hash']} symbol={state['symbol_name']} "
        f"symbolId={state['symbol_id']} digits={state['digits']} "
        f"pipPosition={state['pip_position']} minVolume={state['min_volume']} "
        f"maxVolume={state['max_volume']} stepVolume={state['step_volume']} "
        f"lotSize={state['lot_size']} tradingMode={state['trading_mode']} "
        f"measurementUnits={state['measurement_units']} balance={state['balance']:.8f} "
        f"moneyDigits={state['money_digits']} accountType={state['account_type']} "
        f"accessRights={state['access_rights']} bid={state['bid']:.8f} "
        f"ask={state['ask']:.8f} spreadPrice={spread:.8f} "
        f"marketDataAgeSeconds={state['spot_age_seconds']:.3f} execution_enabled=false"
    )
    reactor.stop()


def connected(_client):
    print("STATE BOOT")
    print("STATE AUTHENTICATING endpoint=DEMO")
    req = ProtoOAApplicationAuthReq()
    req.clientId = CLIENT_ID
    req.clientSecret = CLIENT_SECRET
    send(req)


def received(_client, message):
    obj = Protobuf.extract(message)
    name = type(obj).__name__

    if name == "ProtoOAApplicationAuthRes":
        print("STATE APPLICATION_AUTHENTICATED")
        req = ProtoOAGetAccountListByAccessTokenReq()
        req.accessToken = TOKEN
        send(req)
        return

    if name == "ProtoOAGetAccountListByAccessTokenRes":
        accounts = list(obj.ctidTraderAccount)
        selected = next(
            (
                a
                for a in accounts
                if str(a.ctidTraderAccountId) == ACCOUNT
            ),
            None,
        )
        if selected is None:
            stop_fail("REQUESTED_ACCOUNT_NOT_AUTHORIZED")
            return
        if getattr(selected, "isLive", False):
            stop_fail("LIVE_ACCOUNT")
            return

        broker = getattr(selected, "brokerTitleShort", "") or ""
        if EXPECTED_BROKER.lower() not in broker.lower():
            stop_fail("BROKER_MISMATCH")
            return

        state["account_id"] = int(selected.ctidTraderAccountId)
        state["account_hash"] = safe_hash(selected.ctidTraderAccountId)
        state["broker"] = broker

        print(
            "STATE ACCOUNT_DISCOVERED "
            f"accountHash={state['account_hash']} isLive=false broker={broker}"
        )

        req = ProtoOAAccountAuthReq()
        req.ctidTraderAccountId = state["account_id"]
        req.accessToken = TOKEN
        send(req)
        return

    if name == "ProtoOAAccountAuthRes":
        print("STATE ACCOUNT_AUTHENTICATED")

        trader_req = ProtoOATraderReq()
        trader_req.ctidTraderAccountId = state["account_id"]
        send(trader_req)

        symbols_req = ProtoOASymbolsListReq()
        symbols_req.ctidTraderAccountId = state["account_id"]
        symbols_req.includeArchivedSymbols = False
        send(symbols_req)
        return

    if name == "ProtoOATraderRes":
        trader = obj.trader
        access_rights = int(getattr(trader, "accessRights", 3))
        if access_rights != 0:
            stop_fail("ACCOUNT_NOT_FULL_ACCESS")
            return

        broker_name = getattr(trader, "brokerName", "") or ""
        if broker_name and EXPECTED_BROKER.lower() not in broker_name.lower():
            stop_fail("TRADER_BROKER_MISMATCH")
            return

        money_digits = int(getattr(trader, "moneyDigits", 0))
        raw_balance = int(getattr(trader, "balance", 0))
        divisor = 10 ** money_digits if money_digits >= 0 else 1
        balance = raw_balance / divisor

        state["balance"] = balance
        state["money_digits"] = money_digits
        state["account_type"] = int(getattr(trader, "accountType", -1))
        state["access_rights"] = access_rights
        state["trader_ready"] = True

        print(
            "STATE ACCOUNT_VERIFIED "
            f"accountHash={state['account_hash']} accessRights=FULL_ACCESS "
            f"accountType={state['account_type']} balance={balance:.8f} "
            f"moneyDigits={money_digits}"
        )
        maybe_finish()
        return

    if name == "ProtoOASymbolsListRes":
        expected = norm_symbol(SYMBOL)
        matches = [
            s
            for s in obj.symbol
            if norm_symbol(getattr(s, "symbolName", "")) == expected
        ]
        if len(matches) != 1:
            stop_fail("XAU_SYMBOL_NOT_UNIQUE_OR_NOT_FOUND")
            return

        selected = matches[0]
        state["symbol_id"] = int(selected.symbolId)
        state["symbol_name"] = selected.symbolName

        req = ProtoOASymbolByIdReq()
        req.ctidTraderAccountId = state["account_id"]
        req.symbolId.append(state["symbol_id"])
        send(req)
        return

    if name == "ProtoOASymbolByIdRes":
        symbols = list(obj.symbol)
        selected = next(
            (s for s in symbols if int(s.symbolId) == state["symbol_id"]),
            None,
        )
        if selected is None:
            stop_fail("SYMBOL_SPEC_NOT_FOUND")
            return

        trading_mode = int(getattr(selected, "tradingMode", 3))
        if trading_mode != 0:
            stop_fail("SYMBOL_TRADING_DISABLED")
            return

        state["digits"] = int(selected.digits)
        state["pip_position"] = int(selected.pipPosition)
        state["min_volume"] = int(getattr(selected, "minVolume", 0))
        state["max_volume"] = int(getattr(selected, "maxVolume", 0))
        state["step_volume"] = int(getattr(selected, "stepVolume", 0))
        state["lot_size"] = int(getattr(selected, "lotSize", 0))
        state["trading_mode"] = trading_mode
        state["measurement_units"] = getattr(selected, "measurementUnits", "") or ""
        state["symbol_ready"] = True

        if (
            state["min_volume"] <= 0
            or state["max_volume"] <= 0
            or state["step_volume"] <= 0
            or state["max_volume"] < state["min_volume"]
        ):
            stop_fail("INVALID_BROKER_VOLUME_SPEC")
            return

        print(
            "STATE SYMBOL_RESOLVED "
            f"symbol={state['symbol_name']} symbolId={state['symbol_id']} "
            f"digits={state['digits']} pipPosition={state['pip_position']} "
            f"minVolume={state['min_volume']} maxVolume={state['max_volume']} "
            f"stepVolume={state['step_volume']} lotSize={state['lot_size']} "
            f"tradingMode=ENABLED measurementUnits={state['measurement_units']}"
        )

        req = ProtoOASubscribeSpotsReq()
        req.ctidTraderAccountId = state["account_id"]
        req.symbolId.append(state["symbol_id"])
        req.subscribeToSpotTimestamp = True
        send(req)
        return

    if name == "ProtoOASubscribeSpotsRes":
        print("STATE MARKET_DATA_SUBSCRIBED")
        return

    if name == "ProtoOASpotEvent":
        if int(obj.symbolId) != state["symbol_id"]:
            return
        if not (obj.HasField("bid") and obj.HasField("ask")):
            return

        bid = int(obj.bid) / 100000.0
        ask = int(obj.ask) / 100000.0
        ts = int(getattr(obj, "timestamp", 0))
        if ts <= 0:
            stop_fail("SPOT_TIMESTAMP_MISSING")
            return

        spot_seconds = ts / 1000.0 if ts > 10_000_000_000 else float(ts)
        age = max(0.0, time.time() - spot_seconds)

        state["bid"] = bid
        state["ask"] = ask
        state["spot_age_seconds"] = age
        state["spot_ready"] = True

        print(
            "STATE MARKET_DATA_VERIFIED "
            f"symbol={state['symbol_name']} bid={bid:.8f} ask={ask:.8f} "
            f"ageSeconds={age:.3f}"
        )
        maybe_finish()
        return

    if name == "ProtoOAErrorRes":
        code = getattr(obj, "errorCode", "UNKNOWN")
        description = getattr(obj, "description", "") or ""
        stop_fail(f"OPENAPI_ERROR_{code}_{description[:80]}")
        return


client.setConnectedCallback(connected)
client.setMessageReceivedCallback(received)
client.setDisconnectedCallback(
    lambda _client, reason: print("STATE DISCONNECTED reason=" + str(reason).splitlines()[0][:120])
)
client.startService()

reactor.callLater(30, lambda: stop_fail("TIMEOUT") if reactor.running else None)
reactor.run()
