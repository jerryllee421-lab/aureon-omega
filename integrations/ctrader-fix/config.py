"""AUREON cTrader FIX 4.4 safety/config boundary.

Transport implementation intentionally remains separate from strategy logic.
No credentials are stored in source.
"""
from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class FixConfig:
    environment: str
    host: str
    quote_port: int
    trade_port: int
    sender_comp_id: str
    target_comp_id: str
    password: str
    trading_enabled: bool

    @classmethod
    def from_env(cls) -> "FixConfig":
        cfg = cls(
            environment=os.getenv("AUREON_FIX_ENV", "demo").strip().lower(),
            host=os.getenv("AUREON_FIX_HOST", "").strip(),
            quote_port=int(os.getenv("AUREON_FIX_QUOTE_SSL_PORT", "5211")),
            trade_port=int(os.getenv("AUREON_FIX_TRADE_SSL_PORT", "5212")),
            sender_comp_id=os.getenv("AUREON_FIX_SENDER_COMP_ID", "").strip(),
            target_comp_id=os.getenv("AUREON_FIX_TARGET_COMP_ID", "cServer").strip(),
            password=os.getenv("AUREON_FIX_PASSWORD", ""),
            trading_enabled=os.getenv("AUREON_FIX_TRADING_ENABLED", "false").lower() == "true",
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.environment != "demo":
            raise RuntimeError("AUREON FIX HARD BLOCK: only demo environment is authorized.")
        if self.host != "demo.cfixapi.com":
            raise RuntimeError("AUREON FIX HARD BLOCK: unexpected/non-demo FIX host.")
        if self.quote_port != 5211 or self.trade_port != 5212:
            raise RuntimeError("AUREON FIX HARD BLOCK: SSL demo ports must be 5211/5212.")
        if not self.sender_comp_id or not self.password:
            raise RuntimeError("AUREON FIX BLOCKED: credentials must be supplied via secrets/env.")
        if self.target_comp_id != "cServer":
            raise RuntimeError("AUREON FIX BLOCKED: unexpected TargetCompID.")

    def session(self, kind: str) -> dict:
        kind = kind.upper()
        if kind not in {"QUOTE", "TRADE"}:
            raise ValueError("session kind must be QUOTE or TRADE")
        return {
            "host": self.host,
            "port": self.quote_port if kind == "QUOTE" else self.trade_port,
            "sender_comp_id": self.sender_comp_id,
            "sender_sub_id": kind,
            "target_comp_id": self.target_comp_id,
        }

    def require_order_authority(self) -> None:
        self.validate()
        if not self.trading_enabled:
            raise RuntimeError("AUREON FIX ORDER BLOCKED: demo trading switch is disabled.")
