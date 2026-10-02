from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def stats(r: np.ndarray) -> dict:
    if r.size == 0:
        return {"trades":0,"pf":0.0,"exp_r":0.0,"net_r":0.0,"win_rate":0.0}
    gp = float(r[r>0].sum())
    gl = float(-r[r<0].sum())
    pf = gp/gl if gl>0 else (999.0 if gp>0 else 0.0)
    return {
        "trades": int(r.size),
        "pf": float(pf),
        "exp_r": float(r.mean()),
        "net_r": float(r.sum()),
        "win_rate": float((r>0).mean()),
    }


def hour_mask(hours: np.ndarray, start: int, length: int) -> np.ndarray:
    if length >= 24:
        return np.ones(hours.shape, dtype=bool)
    return ((hours - start) % 24) < length


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out", default="v8_subset_results")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df = df.sort_values("entry_time").reset_index(drop=True)

    n = len(df)
    cut1 = int(n * 0.60)
    cut2 = int(n * 0.80)

    engine = df["engine"].astype(str).to_numpy()
    direction = df["direction"].to_numpy(int)
    score = df["score"].to_numpy(float)
    hour = df["utc_hour"].to_numpy(int)
    r = df["r"].to_numpy(float)

    split_masks = {
        "train": np.arange(n) < cut1,
        "validation": (np.arange(n) >= cut1) & (np.arange(n) < cut2),
        "test": np.arange(n) >= cut2,
    }

    engines = sorted(df["engine"].unique().tolist())
    thresholds = [66,70,72,75,78,80,82,85,88]
    windows = [(0,24)]
    for length in (2,3,4,5,6,8,12):
        for start in range(24):
            windows.append((start,length))

    rows = []
    for eng in engines:
        em = engine == eng
        for d in (-1,1):
            dm = direction == d
            base = em & dm
            for th in thresholds:
                sm = score >= th
                prefix = base & sm
                if prefix.sum() < 100:
                    continue
                for start,length in windows:
                    hm = hour_mask(hour,start,length)
                    filt = prefix & hm

                    tm = filt & split_masks["train"]
                    if tm.sum() < 100:
                        continue
                    train = stats(r[tm])
                    if train["pf"] < 1.05 or train["exp_r"] <= 0:
                        continue

                    vm = filt & split_masks["validation"]
                    validation = stats(r[vm])

                    xm = filt & split_masks["test"]
                    test = stats(r[xm])

                    rows.append({
                        "engine": eng,
                        "direction": int(d),
                        "score_threshold": int(th),
                        "utc_start": int(start),
                        "utc_length": int(length),
                        **{f"train_{k}":v for k,v in train.items()},
                        **{f"val_{k}":v for k,v in validation.items()},
                        **{f"test_{k}":v for k,v in test.items()},
                    })

    cand = pd.DataFrame(rows)
    if cand.empty:
        cand = pd.DataFrame(columns=[
            "engine","direction","score_threshold","utc_start","utc_length",
            "train_trades","train_pf","train_exp_r","train_net_r","train_win_rate",
            "val_trades","val_pf","val_exp_r","val_net_r","val_win_rate",
            "test_trades","test_pf","test_exp_r","test_net_r","test_win_rate"
        ])

    cand.to_csv(out/"v8_subset_train_positive.csv", index=False)

    validated = cand[
        (cand["val_trades"] >= 30) &
        (cand["val_pf"] >= 1.0) &
        (cand["val_exp_r"] > 0)
    ].copy() if not cand.empty else cand.copy()
    validated.to_csv(out/"v8_subset_validated.csv", index=False)

    survivors = validated[
        (validated["test_trades"] >= 30) &
        (validated["test_pf"] >= 1.0) &
        (validated["test_exp_r"] > 0)
    ].copy() if not validated.empty else validated.copy()

    if not survivors.empty:
        survivors["robust_pf"] = survivors[["train_pf","val_pf","test_pf"]].min(axis=1)
        survivors["robust_exp_r"] = survivors[["train_exp_r","val_exp_r","test_exp_r"]].min(axis=1)
        survivors = survivors.sort_values(["robust_exp_r","robust_pf"], ascending=False)
    survivors.to_csv(out/"v8_subset_survivors.csv", index=False)

    # Near-miss leaderboard: favor validation/test even when no full survivor exists.
    if not cand.empty:
        near = cand.copy()
        near["forward_pf_min"] = near[["val_pf","test_pf"]].min(axis=1)
        near["forward_exp_min"] = near[["val_exp_r","test_exp_r"]].min(axis=1)
        near = near.sort_values(["forward_exp_min","forward_pf_min","test_trades"], ascending=False).head(100)
    else:
        near = cand.copy()
    near.to_csv(out/"v8_subset_near_misses.csv", index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "AUREON V8.3 CHRONOLOGICAL SUBSET MINER",
        "source_trades": str(args.trades),
        "rows": int(n),
        "split": {
            "train_rows": int(cut1),
            "validation_rows": int(cut2-cut1),
            "test_rows": int(n-cut2),
            "method": "chronological 60/20/20 by trade sequence",
        },
        "search": {
            "engines": engines,
            "directions": [-1,1],
            "score_thresholds": thresholds,
            "utc_windows": "all contiguous 2,3,4,5,6,8,12 hour windows plus 24h",
            "train_gate": ">=100 trades, PF>=1.05, expectancy>0",
            "validation_gate": ">=30 trades, PF>=1.0, expectancy>0",
            "test_gate": ">=30 trades, PF>=1.0, expectancy>0",
        },
        "train_positive_candidates": int(len(cand)),
        "validated_candidates": int(len(validated)),
        "test_survivors": int(len(survivors)),
        "best_survivor": survivors.iloc[0].to_dict() if len(survivors) else None,
        "warning": (
            "Subset mining reuses V8.2 fixed-exit M1-bar results. "
            "It can identify robust engine/direction/session/score slices but does not repair a weak signal or exit model."
        ),
    }
    (out/"v8_subset_report.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
