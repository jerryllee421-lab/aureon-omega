from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_set(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith(';') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(repo_root: Path) -> dict[str, object]:
    root = Path(repo_root)
    ea = root / 'ea/baseline/FVG_Scalper_V2_12_Research.mq5'
    preset = root / 'ea/baseline/presets/FVG_V2_12_R943K.set'
    r943k_path = root / 'research/baselines/fvg_v212_r943k.json'
    r1_path = root / 'research/baselines/fvg_v212_r1_253b_historical.json'

    preset_values = parse_set(preset)
    r943k = json.loads(r943k_path.read_text(encoding='utf-8'))
    r1 = json.loads(r1_path.read_text(encoding='utf-8'))

    return {
        'schema': 'aureon.v212.control_manifest.v1',
        'control': r943k['id'],
        'baseline_role': r943k['role'],
        'native_model': r943k['tester']['model'],
        'preset': preset_values,
        'ea_sha256': sha256_file(ea),
        'preset_sha256': sha256_file(preset),
        'r943k_sha256': sha256_file(r943k_path),
        'r1_253b_sha256': sha256_file(r1_path),
        'benchmark': {
            'r943k': r943k['result'],
            'r1_253b': {
                **r1.get('tester_evidence', {}),
                **r1.get('contextual_results_from_research_record', {}),
            },
        },
        'native_reproduction_status': 'PENDING',
        'live_ready': bool(r943k.get('policy', {}).get('live_ready', False)),
        'real_money_execution': 'LOCKED',
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', default='.')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    manifest = build_manifest(Path(args.repo_root))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
