from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    from research.fvg_v212_edge_recovery import A01_POLICIES, FIDELITY, LIMITATIONS, Trade, metrics, run, trades_frame
except ModuleNotFoundError:  # CLI execution via python research/run_v212_a01.py
    from fvg_v212_edge_recovery import A01_POLICIES, FIDELITY, LIMITATIONS, Trade, metrics, run, trades_frame


def _sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def _hash_json(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def load_data(path: Path) -> pd.DataFrame:
    p=Path(path)
    files=[p] if p.is_file() else sorted(p.rglob('*.parquet'))
    if not files:
        raise FileNotFoundError(f'No parquet data under {p}')
    frames=[pd.read_parquet(f) for f in files]
    x=pd.concat(frames,ignore_index=True)
    x['time']=pd.to_datetime(x['time'],utc=True)
    return x.sort_values('time').drop_duplicates('time').reset_index(drop=True)


def _frame_metrics(g: pd.DataFrame) -> dict[str, Any]:
    if g.empty:
        return {'trades':0,'profit_factor':0.0,'expectancy_r':0.0,'net_r':0.0}
    rs=pd.to_numeric(g['realized_r'],errors='coerce').dropna()
    gp=float(rs[rs>0].sum()); gl=float(-rs[rs<0].sum())
    return {
        'trades':int(len(rs)),
        'profit_factor':float(gp/gl) if gl>0 else (999.0 if gp>0 else 0.0),
        'expectancy_r':float(rs.mean()) if len(rs) else 0.0,
        'net_r':float(rs.sum()),
    }


def _breakdowns(name: str, tf: pd.DataFrame):
    attempt=[]; year=[]; direction=[]; exits=[]
    if tf.empty:
        return attempt,year,direction,exits
    for key,g in tf.groupby('attempt_no',dropna=False):
        attempt.append({'variant':name,'attempt_no':int(key),**_frame_metrics(g)})
    tf=tf.copy(); tf['entry_time']=pd.to_datetime(tf['entry_time'],utc=True)
    tf['year']=tf['entry_time'].dt.year
    for key,g in tf.groupby('year'):
        year.append({'variant':name,'year':int(key),**_frame_metrics(g)})
    for key,g in tf.groupby('direction'):
        direction.append({'variant':name,'direction':str(key),**_frame_metrics(g)})
    for key,g in tf.groupby('exit_reason'):
        exits.append({'variant':name,'exit_reason':str(key),**_frame_metrics(g)})
    return attempt,year,direction,exits


def _policy_thresholds(policy: dict[str, Any] | None) -> dict[str,float]:
    if policy is None:
        return {'min_trades':100,'min_profit_factor':1.20,'min_expectancy_r':0.05}
    if 'promotion' in policy:
        policy=policy['promotion']
    return {
        'min_trades':int(policy.get('min_trades',100)),
        'min_profit_factor':float(policy.get('min_profit_factor',1.20)),
        'min_expectancy_r':float(policy.get('min_expectancy_r',0.05)),
    }


def run_a01_frame(
    df: pd.DataFrame,
    manifest: dict[str, Any],
    out: Path,
    *,
    source_commit: str='unknown',
    policy: dict[str, Any] | None=None,
) -> dict[str, Any]:
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    thresholds=_policy_thresholds(policy)
    variants: dict[str,Any]={}
    comparisons=[]; attempts=[]; years=[]; directions=[]; exits=[]

    for name,p in A01_POLICIES.items():
        trades,report=run(df,p)
        tf=trades_frame(trades)
        tf.to_csv(out/f'trades_{name}.csv',index=False)
        diagnostic=(
            report['trades']>=thresholds['min_trades'] and
            report['profit_factor']>=thresholds['min_profit_factor'] and
            report['expectancy_r']>=thresholds['min_expectancy_r']
        )
        item={
            'params':asdict(p),
            'metrics':report,
            'diagnostic_policy_pass':bool(diagnostic),
            'promotion_status':'RESEARCH_ONLY',
        }
        variants[name]=item
        comparisons.append({
            'variant':name,
            **{k:report[k] for k in ('trades','wins','losses','win_rate','profit_factor','expectancy_r','net_r','average_win_r','average_loss_r','max_drawdown_r','max_loss_streak')},
            'diagnostic_policy_pass':bool(diagnostic),
        })
        a,y,d,e=_breakdowns(name,tf)
        attempts.extend(a); years.extend(y); directions.extend(d); exits.extend(e)

    pd.DataFrame(comparisons).to_csv(out/'comparison.csv',index=False)
    pd.DataFrame(attempts).to_csv(out/'attempt_breakdown.csv',index=False)
    pd.DataFrame(years).to_csv(out/'year_breakdown.csv',index=False)
    pd.DataFrame(directions).to_csv(out/'direction_breakdown.csv',index=False)
    pd.DataFrame(exits).to_csv(out/'exit_breakdown.csv',index=False)

    sim_path=Path(__file__).with_name('fvg_v212_edge_recovery.py')
    provenance={
        'dataset_sha256':manifest.get('dataset_sha256'),
        'mirror_commit':manifest.get('mirror_commit'),
        'source_commit':source_commit,
        'simulator_sha256':_sha256_file(sim_path) if sim_path.exists() else None,
        'configuration_sha256':_hash_json({k:asdict(v) for k,v in A01_POLICIES.items()}),
        'manifest':manifest,
    }
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2,default=str),encoding='utf-8')

    # Diagnostic rank only. It never changes promotion state.
    ranked=sorted(
        comparisons,
        key=lambda r:(r['expectancy_r']*4 + math.log1p(max(0,min(r['profit_factor'],5))) - .02*r['max_drawdown_r'], r['trades']),
        reverse=True,
    )
    period={
        'first':pd.Timestamp(df['time'].min()).isoformat() if len(df) else None,
        'last':pd.Timestamp(df['time'].max()).isoformat() if len(df) else None,
    }
    result={
        'schema':'aureon.v212.a01.v1',
        'campaign':'FVG_V2_12_MECHANISM_ATTRIBUTION',
        'experiment':'A01_REENTRY',
        'fidelity':FIDELITY,
        'limitations':LIMITATIONS,
        'compounding':False,
        'data_role':'historical_diagnostic',
        'period':period,
        'variants':variants,
        'diagnostic_ranking':[r['variant'] for r in ranked],
        'policy_thresholds':thresholds,
        'native_parity_status':'PENDING',
        'external_holdout_status':'PENDING',
        'promotion_status':'RESEARCH_ONLY',
        'provenance':provenance,
    }
    (out/'attribution.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    return result


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',required=True)
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--out',default='research_results/v212_a01')
    ap.add_argument('--policy',default='research/evolution/policy.yml')
    ap.add_argument('--source-commit',default=os.getenv('GITHUB_SHA','unknown'))
    args=ap.parse_args()
    df=load_data(Path(args.data))
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    policy=None
    if Path(args.policy).is_file():
        policy=yaml.safe_load(Path(args.policy).read_text(encoding='utf-8'))
    result=run_a01_frame(df,manifest,Path(args.out),source_commit=args.source_commit,policy=policy)
    print(json.dumps({
        'experiment':result['experiment'],
        'period':result['period'],
        'ranking':result['diagnostic_ranking'],
        'native_parity_status':result['native_parity_status'],
        'promotion_status':result['promotion_status'],
    },indent=2))


if __name__=='__main__':
    main()
