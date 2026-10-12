import pandas as pd
import pytest

from research.fvg_v212_edge_recovery import Params, Trade, metrics, run


def t(r, attempt=1):
    return Trade(
        zone_id='z', attempt_no=attempt, time_since_prior_attempt_bars=None,
        fvg_age_bars=1, fvg_width_atr=.3, fill_depth=.5, rejection_strength=.8,
        direction='LONG', entry_time=pd.Timestamp('2026-01-01T00:00Z'),
        exit_time=pd.Timestamp('2026-01-01T00:01Z'), entry_i=0, exit_i=1,
        bullish=True, entry=100.0, initial_stop=99.0, target=130.0, exit=100.0+r,
        realized_r=r, mfe_r=max(r,0), mae_r=max(-r,0), exit_reason='FIXTURE',
        hold_bars=1, entry_spread=.1,
    )


def test_metrics_exact_fixed_r_summary_and_attempt_groups():
    m = metrics([t(1,1), t(-1,1), t(2,2), t(-.5,2)])
    assert m['trades'] == 4
    assert m['win_rate'] == .5
    assert m['profit_factor'] == 2.0
    assert m['expectancy_r'] == pytest.approx(.375)
    assert m['net_r'] == pytest.approx(1.5)
    assert m['average_win_r'] == pytest.approx(1.5)
    assert m['average_loss_r'] == pytest.approx(-.75)
    assert m['max_drawdown_r'] == pytest.approx(1.0)
    assert m['max_loss_streak'] == 1
    assert m['attempt_breakdown']['1']['trades'] == 2
    assert m['attempt_breakdown']['1']['expectancy_r'] == pytest.approx(0.0)
    assert m['attempt_breakdown']['2']['profit_factor'] == pytest.approx(4.0)


def synthetic_bullish_entry_frame():
    rows = [
        [100.0,100.0,99.8,99.9],
        [99.9,100.8,99.8,100.7],
        [100.2,100.7,100.2,100.6],
        [100.10,100.30,100.00,100.20],
        [100.20,100.30,100.10,100.20],
    ]
    x = pd.DataFrame(rows, columns=['mid_open','mid_high','mid_low','mid_close'])
    x['time'] = pd.date_range('2026-01-01', periods=len(x), freq='min', tz='UTC')
    for c in ('open','high','low','close'):
        x[f'bid_{c}'] = x[f'mid_{c}'] - .05
        x[f'ask_{c}'] = x[f'mid_{c}'] + .05
    x['spread_open'] = .10; x['spread_close'] = .10
    x['atr'] = 1.0; x['atr_close'] = 1.0
    return x


def test_run_long_entry_uses_ask_and_spread_is_not_subtracted_twice():
    x = synthetic_bullish_entry_frame()
    trades, report = run(x, Params(require_rejection=True, one_trade_per_fvg=True))
    assert trades
    tr = trades[0]
    assert tr.entry == pytest.approx(x.loc[3,'ask_open'])
    assert tr.entry_spread == pytest.approx(.10)
    expected = (tr.exit - tr.entry) / (tr.entry - tr.initial_stop)
    assert tr.realized_r == pytest.approx(expected)
    assert report['fidelity'] == 'M1_BAR_APPROX_CAUSAL_NEXT_BAR_ENTRY'
    assert report['compounding'] is False


def test_trade_frame_has_required_attempt_telemetry():
    from research.fvg_v212_edge_recovery import trades_frame
    df = trades_frame([t(1,2)])
    required = {'zone_id','attempt_no','time_since_prior_attempt_bars','fvg_age_bars','fvg_width_atr','fill_depth','rejection_strength','direction','entry_time','exit_time','realized_r','mfe_r','mae_r','exit_reason','entry_spread'}
    assert required.issubset(df.columns)
