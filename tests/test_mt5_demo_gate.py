import unittest

from execution.mt5_demo_gate import Config, Snapshot, evaluate, require_allowed


def valid_snapshot(**changes):
    values = dict(connected=True, terminal_trade_allowed=True, account_trade_allowed=True,
                  account_mode="DEMO", server="PXBTTrading-1", login=123456,
                  symbol="XAUUSD", market_open=True, daily_loss_pct=0.2,
                  open_positions=0, pending_orders=0)
    values.update(changes)
    return Snapshot(**values)


class DemoGateTests(unittest.TestCase):
    def test_default_configuration_blocks(self):
        decision = evaluate(valid_snapshot())
        self.assertFalse(decision.allowed)
        self.assertIn("EXPECTED_LOGIN_NOT_CONFIGURED", decision.reasons)
        self.assertIn("KILL_SWITCH_ACTIVE", decision.reasons)
        self.assertIn("DEMO_EXECUTION_NOT_ENABLED", decision.reasons)
        self.assertFalse(decision.live_trading_allowed)

    def test_explicit_demo_configuration_passes(self):
        config = Config(expected_login=123456, demo_enabled=True, kill_switch=False)
        decision = evaluate(valid_snapshot(), config)
        self.assertTrue(decision.allowed, decision.reasons)
        self.assertFalse(decision.live_trading_allowed)

    def test_unknown_or_real_account_is_blocked(self):
        config = Config(expected_login=123456, demo_enabled=True, kill_switch=False)
        for mode in ("REAL", "CONTEST", "", "UNKNOWN"):
            with self.subTest(mode=mode):
                self.assertIn("ACCOUNT_NOT_VERIFIED_DEMO", evaluate(valid_snapshot(account_mode=mode), config).reasons)

    def test_market_closed_exposure_and_daily_loss_block(self):
        config = Config(expected_login=123456, demo_enabled=True, kill_switch=False)
        decision = evaluate(valid_snapshot(market_open=False, open_positions=3, pending_orders=1, daily_loss_pct=2.0), config)
        for reason in ("MARKET_CLOSED", "OPEN_POSITION_LIMIT_REACHED", "PENDING_ORDER_LIMIT_REACHED", "DAILY_LOSS_LIMIT_REACHED"):
            self.assertIn(reason, decision.reasons)

    def test_identity_mismatch_blocks(self):
        config = Config(expected_login=123456, demo_enabled=True, kill_switch=False)
        decision = evaluate(valid_snapshot(server="OtherServer", symbol="XAUUSD.a", login=999), config)
        for reason in ("UNEXPECTED_SERVER", "UNEXPECTED_SYMBOL", "ACCOUNT_LOGIN_MISMATCH"):
            self.assertIn(reason, decision.reasons)

    def test_guard_raises_on_block(self):
        with self.assertRaises(PermissionError):
            require_allowed(valid_snapshot())


if __name__ == "__main__":
    unittest.main()
