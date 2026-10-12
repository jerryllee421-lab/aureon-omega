import pandas as pd
import numpy as np

from research.fvg_v212_edge_recovery import Params, Zone, find_newest_fvg, prepare, rejection_ok


def frame(rows):
    base = pd.DataFrame(rows)
    base['time'] = pd.date_range('2026-01-01', periods=len(base), freq='min', tz='UTC')
    for c in ('open','high','low','close'):
        base[f'bid_{c}'] = base[f'mid_{c}'] - 0.05
        base[f'ask_{c}'] = base[f'mid_{c}'] + 0.05
    base['spread_open'] = base.ask_open - base.bid_open
    base['spread_close'] = base.ask_close - base.bid_close
    return base


def bullish_rows():
    return [
        {'mid_open':100.0,'mid_high':100.2,'mid_low':99.8,'mid_close':100.0},
        {'mid_open':100.0,'mid_high':100.9,'mid_low':99.9,'mid_close':100.8},
        {'mid_open':100.5,'mid_high':101.0,'mid_low':100.5,'mid_close':100.9},
        {'mid_open':100.7,'mid_high':100.9,'mid_low':100.6,'mid_close':100.85},
    ]


def bearish_rows():
    return [
        {'mid_open':100.6,'mid_high':100.8,'mid_low':100.5,'mid_close':100.6},
        {'mid_open':100.6,'mid_high':100.7,'mid_low':99.7,'mid_close':99.8},
        {'mid_open':100.0,'mid_high':100.1,'mid_low':99.6,'mid_close':99.7},
        {'mid_open':99.9,'mid_high':100.0,'mid_low':99.7,'mid_close':99.8},
    ]


def test_bullish_fvg_uses_closed_three_bar_pattern():
    x = frame(bullish_rows()); x['atr'] = 1.0
    z = find_newest_fvg(x, decision_i=3, p=Params())
    assert z is not None and z.bullish
    assert z.low == 100.2 and z.high == 100.5


def test_bearish_fvg_uses_closed_three_bar_pattern():
    x = frame(bearish_rows()); x['atr'] = 1.0
    z = find_newest_fvg(x, decision_i=3, p=Params())
    assert z is not None and not z.bullish
    assert z.low == 100.1 and z.high == 100.5


def test_fvg_rejects_gap_below_minimum_atr():
    rows = bullish_rows(); rows[2]['mid_low'] = 100.3
    x = frame(rows); x['atr'] = 1.0
    assert find_newest_fvg(x, 3, Params(min_fvg_atr=0.15)) is None


def test_fvg_rejects_weak_displacement_body():
    rows = bullish_rows(); rows[1].update(mid_open=100.0, mid_close=100.2, mid_high=100.9, mid_low=99.9)
    x = frame(rows); x['atr'] = 1.0
    assert find_newest_fvg(x, 3, Params(min_body_atr=0.5)) is None


def test_rejection_uses_previous_closed_bar_only():
    rows = bullish_rows()
    rows[2].update(mid_low=100.0, mid_high=101.0, mid_close=100.8)
    x = frame(rows); x['atr'] = 1.0
    ok, strength = rejection_ok(x, decision_i=3, bullish=True)
    assert ok is True
    assert strength >= 0.55


def test_causal_decision_ignores_current_bar_future_ohlc():
    a = frame(bullish_rows()); a['atr'] = 1.0
    b = a.copy()
    b.loc[3, ['mid_open','mid_high','mid_low','mid_close','bid_open','bid_high','bid_low','bid_close','ask_open','ask_high','ask_low','ask_close']] = [50,500,1,400,49.95,499.95,.95,399.95,50.05,500.05,1.05,400.05]
    za = find_newest_fvg(a, 3, Params())
    zb = find_newest_fvg(b, 3, Params())
    ra = rejection_ok(a, 3, True)
    rb = rejection_ok(b, 3, True)
    assert za == zb
    assert ra == rb


def test_prepare_shifts_atr_so_decision_bar_cannot_see_itself():
    x = frame(bullish_rows() * 6)
    p = Params(atr_period=3)
    a = prepare(x, p)
    y = x.copy(); y.loc[10, ['mid_high','mid_low','mid_close']] = [999.0, 1.0, 500.0]
    b = prepare(y, p)
    assert a.loc[10, 'atr'] == b.loc[10, 'atr']


def test_zone_identity_stable_for_same_event_and_changes_for_new_event():
    from research.fvg_v212_edge_recovery import zone_identity
    t = pd.Timestamp('2026-01-01T00:02:00Z')
    a = zone_identity(True, t, 100.2, 100.5)
    b = zone_identity(True, t, 100.2, 100.5)
    c = zone_identity(True, t + pd.Timedelta(minutes=1), 100.2, 100.5)
    assert a == b
    assert a != c


def test_reentry_control_allows_repeat_zero_cooldown():
    from research.fvg_v212_edge_recovery import reentry_allowed
    z = Zone(True, 100, 101, 3, pd.Timestamp('2026-01-01T00:03Z'), traded=True, attempts=1, last_entry_i=10)
    assert reentry_allowed(z, 11, Params(one_trade_per_fvg=False, cooldown_bars=0))


def test_reentry_one_trade_rejects_second_attempt():
    from research.fvg_v212_edge_recovery import reentry_allowed
    z = Zone(True, 100, 101, 3, pd.Timestamp('2026-01-01T00:03Z'), traded=True, attempts=1, last_entry_i=10)
    assert not reentry_allowed(z, 11, Params(one_trade_per_fvg=True))


def test_reentry_one_bar_cooldown_rejects_immediate_next_bar():
    from research.fvg_v212_edge_recovery import reentry_allowed
    z = Zone(True, 100, 101, 3, pd.Timestamp('2026-01-01T00:03Z'), traded=True, attempts=1, last_entry_i=10)
    assert not reentry_allowed(z, 11, Params(cooldown_bars=1))
    assert reentry_allowed(z, 12, Params(cooldown_bars=1))


def test_reentry_max3_rejects_attempt4():
    from research.fvg_v212_edge_recovery import reentry_allowed
    z = Zone(True, 100, 101, 3, pd.Timestamp('2026-01-01T00:03Z'), traded=True, attempts=3, last_entry_i=10)
    assert not reentry_allowed(z, 12, Params(max_attempts_per_fvg=3))


def test_a01_policy_table_changes_only_recycling_controls():
    from dataclasses import asdict
    from research.fvg_v212_edge_recovery import A01_POLICIES
    assert set(A01_POLICIES) == {'A01_CONTROL','A01_ONE_TRADE','A01_COOLDOWN_1BAR','A01_MAX3'}
    base = asdict(A01_POLICIES['A01_CONTROL'])
    mutable = {'one_trade_per_fvg','cooldown_bars','max_attempts_per_fvg'}
    for name, p in A01_POLICIES.items():
        d = asdict(p)
        assert {k:v for k,v in d.items() if k not in mutable} == {k:v for k,v in base.items() if k not in mutable}


def test_lock1_moves_stop_to_plus_point1r():
    from research.fvg_v212_edge_recovery import next_stop_after_closed_bar
    pos = {'entry':100.0,'risk':1.0,'stop':99.0}
    assert next_stop_after_closed_bar(pos, 100.5, 1.0, True, Params()) == 100.1


def test_lock2_moves_stop_to_plus_point35r():
    from research.fvg_v212_edge_recovery import next_stop_after_closed_bar
    pos = {'entry':100.0,'risk':1.0,'stop':99.0}
    assert next_stop_after_closed_bar(pos, 101.0, 1.0, True, Params()) == 100.35


def test_trail_activates_at_1point5r_and_never_below_lock2():
    from research.fvg_v212_edge_recovery import next_stop_after_closed_bar
    pos = {'entry':100.0,'risk':1.0,'stop':99.0}
    assert next_stop_after_closed_bar(pos, 101.5, 0.5, True, Params()) == 101.45


def test_stop_never_loosens_long_or_short():
    from research.fvg_v212_edge_recovery import next_stop_after_closed_bar
    long_pos = {'entry':100.0,'risk':1.0,'stop':100.6}
    short_pos = {'entry':100.0,'risk':1.0,'stop':99.4}
    assert next_stop_after_closed_bar(long_pos, 100.2, 1.0, True, Params()) == 100.6
    assert next_stop_after_closed_bar(short_pos, 99.8, 1.0, False, Params()) == 99.4


def test_bar_exit_resolves_stop_before_target_when_both_touch():
    from research.fvg_v212_edge_recovery import resolve_bar_exit
    pos = {'entry':100.0,'risk':1.0,'stop':99.0,'target':101.0}
    result = resolve_bar_exit(pos, bid_low=98.9, bid_high=101.1, ask_low=99.0, ask_high=101.2, bullish=True)
    assert result == (99.0, 'SL')


def test_stop_update_is_not_retroactive_to_same_bar():
    from research.fvg_v212_edge_recovery import resolve_bar_exit, next_stop_after_closed_bar
    pos = {'entry':100.0,'risk':1.0,'stop':99.0,'target':130.0}
    new_stop = next_stop_after_closed_bar(pos, 100.5, 1.0, True, Params())
    result = resolve_bar_exit(pos, bid_low=100.0, bid_high=100.6, ask_low=100.1, ask_high=100.7, bullish=True)
    assert result is None
    assert new_stop == 100.1
