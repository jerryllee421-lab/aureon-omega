"""Pure decision gate for a local MT5 DEMO adapter; never connects or trades."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Snapshot:
    connected: bool
    terminal_trade_allowed: bool
    account_trade_allowed: bool
    account_mode: str
    server: str
    login: Optional[int]
    symbol: str
    market_open: bool
    daily_loss_pct: float
    open_positions: int
    pending_orders: int

@dataclass(frozen=True)
class Config:
    expected_server: str = "PXBTTrading-1"
    expected_symbol: str = "XAUUSD"
    expected_login: Optional[int] = None
    demo_enabled: bool = False
    kill_switch: bool = True
    max_daily_loss_pct: float = 2.0
    max_open_positions: int = 3
    max_pending_orders: int = 1

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reasons: tuple[str, ...]
    live_trading_allowed: bool = False


def evaluate(snapshot: Snapshot, config: Config = Config()) -> Decision:
    checks = [
        (snapshot.connected, "TERMINAL_DISCONNECTED"),
        (snapshot.terminal_trade_allowed, "TERMINAL_TRADING_DISABLED"),
        (snapshot.account_trade_allowed, "ACCOUNT_TRADING_DISABLED"),
        (snapshot.account_mode.strip().upper() == "DEMO", "ACCOUNT_NOT_VERIFIED_DEMO"),
        (snapshot.server == config.expected_server, "UNEXPECTED_SERVER"),
        (snapshot.symbol == config.expected_symbol, "UNEXPECTED_SYMBOL"),
        (snapshot.market_open, "MARKET_CLOSED"),
        (config.expected_login is not None, "EXPECTED_LOGIN_NOT_CONFIGURED"),
        (snapshot.login == config.expected_login, "ACCOUNT_LOGIN_MISMATCH"),
        (snapshot.daily_loss_pct >= 0, "INVALID_DAILY_LOSS_METRIC"),
        (snapshot.daily_loss_pct < config.max_daily_loss_pct, "DAILY_LOSS_LIMIT_REACHED"),
        (snapshot.open_positions >= 0 and snapshot.pending_orders >= 0, "INVALID_EXPOSURE_METRICS"),
        (snapshot.open_positions < config.max_open_positions, "OPEN_POSITION_LIMIT_REACHED"),
        (snapshot.pending_orders < config.max_pending_orders, "PENDING_ORDER_LIMIT_REACHED"),
        (not config.kill_switch, "KILL_SWITCH_ACTIVE"),
        (config.demo_enabled, "DEMO_EXECUTION_NOT_ENABLED"),
    ]
    reasons = tuple(reason for passed, reason in checks if not passed)
    return Decision(allowed=not reasons, reasons=reasons, live_trading_allowed=False)


def require_allowed(snapshot: Snapshot, config: Config = Config()) -> Decision:
    decision = evaluate(snapshot, config)
    if not decision.allowed:
        raise PermissionError("MT5 DEMO gate blocked: " + ",".join(decision.reasons))
    return decision
