import json
from pathlib import Path

from research.v212_control_manifest import build_manifest, parse_set

PRESET = '''InpOneTradePerFVG=false\nInpCooldownSeconds=0\nInpRequireRejection=true\nInpMinFVG_ATR=0.15\nInpMinBody_ATR=0.5\nInpUseProfitLock=true\nInpUseATRTrail=true\nInpTrail_ATR=0.1\n'''


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / 'ea/baseline/presets').mkdir(parents=True)
    (tmp_path / 'research/baselines').mkdir(parents=True)
    (tmp_path / 'ea/baseline/FVG_Scalper_V2_12_Research.mq5').write_text('// frozen ea\n', encoding='utf-8')
    (tmp_path / 'ea/baseline/presets/FVG_V2_12_R943K.set').write_text(PRESET, encoding='utf-8')
    (tmp_path / 'research/baselines/fvg_v212_r943k.json').write_text(json.dumps({
        'id':'FVG_V2_12_R943K','role':'FROZEN_CONTROL',
        'tester':{'model':'Every tick based on real ticks'},
        'result':{'profit_factor':2.58,'trades':1135},
        'policy':{'live_ready':False}
    }), encoding='utf-8')
    (tmp_path / 'research/baselines/fvg_v212_r1_253b_historical.json').write_text(json.dumps({
        'id':'FVG_V2_12_R1_253B_HISTORICAL_BENCHMARK','tester_evidence':{'profit_factor':2.48},
        'contextual_results_from_research_record':{'trades':18368}
    }), encoding='utf-8')
    return tmp_path


def test_parse_set_preserves_canonical_values(tmp_path):
    p = tmp_path / 'x.set'; p.write_text(PRESET, encoding='utf-8')
    s = parse_set(p)
    assert s['InpOneTradePerFVG'] == 'false'
    assert s['InpCooldownSeconds'] == '0'
    assert s['InpRequireRejection'] == 'true'
    assert s['InpMinFVG_ATR'] == '0.15'
    assert s['InpMinBody_ATR'] == '0.5'
    assert s['InpUseProfitLock'] == 'true'
    assert s['InpUseATRTrail'] == 'true'
    assert s['InpTrail_ATR'] == '0.1'


def test_build_manifest_records_frozen_identity_and_safety(tmp_path):
    root = make_repo(tmp_path)
    m = build_manifest(root)
    assert m['control'] == 'FVG_V2_12_R943K'
    assert m['baseline_role'] == 'FROZEN_CONTROL'
    assert m['native_model'] == 'Every tick based on real ticks'
    assert m['live_ready'] is False
    assert m['native_reproduction_status'] == 'PENDING'
    assert m['real_money_execution'] == 'LOCKED'
    assert m['benchmark']['r943k']['profit_factor'] == 2.58
    assert m['benchmark']['r1_253b']['profit_factor'] == 2.48
    for key in ('ea_sha256','preset_sha256','r943k_sha256','r1_253b_sha256'):
        assert len(m[key]) == 64
