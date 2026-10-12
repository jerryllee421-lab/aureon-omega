import json
from pathlib import Path

import pandas as pd

from research.run_v212_a01 import run_a01_frame


def sample_frame():
    rows=[]
    for block in range(8):
        off=block*.05
        rows += [
            [100.0+off,100.0+off,99.8+off,99.9+off],
            [99.9+off,100.8+off,99.8+off,100.7+off],
            [100.2+off,100.7+off,100.2+off,100.6+off],
            [100.10+off,100.35+off,100.00+off,100.25+off],
            [100.20+off,100.35+off,100.10+off,100.20+off],
        ]
    x=pd.DataFrame(rows,columns=['mid_open','mid_high','mid_low','mid_close'])
    x['time']=pd.date_range('2025-01-01',periods=len(x),freq='min',tz='UTC')
    for c in ('open','high','low','close'):
        x[f'bid_{c}']=x[f'mid_{c}']-.05
        x[f'ask_{c}']=x[f'mid_{c}']+.05
    x['spread_open']=.10; x['spread_close']=.10
    x['atr']=1.0; x['atr_close']=1.0
    return x


def test_a01_report_contains_exact_four_variants_and_provenance(tmp_path):
    manifest={'dataset_sha256':'abc123','mirror_commit':'922f83a60cc574e7395fb27397077288055a1ef6','actual_first':'2025-01-01','actual_last':'2025-12-31'}
    result=run_a01_frame(sample_frame(), manifest, tmp_path, source_commit='deadbeef')
    assert set(result['variants']) == {'A01_CONTROL','A01_ONE_TRADE','A01_COOLDOWN_1BAR','A01_MAX3'}
    assert result['fidelity'] == 'M1_BAR_APPROX_CAUSAL_NEXT_BAR_ENTRY'
    assert result['native_parity_status'] == 'PENDING'
    assert result['promotion_status'] == 'RESEARCH_ONLY'
    assert result['provenance']['dataset_sha256'] == 'abc123'
    assert result['provenance']['source_commit'] == 'deadbeef'
    assert result['data_role'] == 'historical_diagnostic'
    assert result.get('untouched_holdout_pass') is not True
    for name in result['variants']:
        assert (tmp_path/f'trades_{name}.csv').exists()
    for name in ('comparison.csv','attempt_breakdown.csv','year_breakdown.csv','direction_breakdown.csv','exit_breakdown.csv','attribution.json','provenance.json'):
        assert (tmp_path/name).exists()


def test_a01_variants_differ_only_in_declared_recycling_controls(tmp_path):
    manifest={'dataset_sha256':'abc','mirror_commit':'pin'}
    result=run_a01_frame(sample_frame(), manifest, tmp_path, source_commit='sha')
    base=result['variants']['A01_CONTROL']['params']
    mutable={'one_trade_per_fvg','cooldown_bars','max_attempts_per_fvg'}
    for item in result['variants'].values():
        assert {k:v for k,v in item['params'].items() if k not in mutable} == {k:v for k,v in base.items() if k not in mutable}


def test_policy_classifier_cannot_promote_without_native_and_external_holdout(tmp_path):
    manifest={'dataset_sha256':'abc','mirror_commit':'pin'}
    result=run_a01_frame(sample_frame(), manifest, tmp_path, source_commit='sha', policy={'min_trades':1,'min_profit_factor':0.0,'min_expectancy_r':-99.0})
    assert result['promotion_status'] == 'RESEARCH_ONLY'
    assert result['native_parity_status'] == 'PENDING'
    assert result['external_holdout_status'] == 'PENDING'
