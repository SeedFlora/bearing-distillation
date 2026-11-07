"""Generate the frozen Paderborn split manifests from metadata only.

Usage:
  .venv/Scripts/python.exe -I scripts/make_splits.py --seed 20261107 [--allow-pending]

Inputs : manifests/paderborn_bearings.csv, manifests/paderborn_recordings.csv,
         configs/data/paderborn_labels.yaml
Outputs: manifests/splits/paderborn_population.csv
         manifests/splits/dev_pool.json
         manifests/splits/protocol_A.json      (outer folds, validation, bridge folds)
         manifests/splits/protocol_B.json      (held-out conditions)
         manifests/splits/protocol_C.json      (optional joint design, declared only)
         manifests/splits/SPLITS_SHA256.txt    (hashes used to detect any change)

No signal, prediction or result is read. Assignment uses a seeded shuffle within
strata (class x damage origin) and round-robin placement that balances class
counts across folds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manifests" / "splits"
CONDITIONS = ["N15_M07_F10", "N09_M07_F10", "N15_M01_F10", "N15_M07_F04"]
DEV_QUOTA = {("healthy", "none"): 2, ("outer", "artificial"): 1, ("outer", "real"): 1,
             ("inner", "artificial"): 1, ("inner", "real"): 1}
VAL_QUOTA = DEV_QUOTA | {("healthy", "none"): 1}


def load_population(allow_pending: bool) -> pd.DataFrame:
    b = pd.read_csv(ROOT / "manifests/paderborn_bearings.csv")
    cfg = yaml.safe_load((ROOT / "configs/data/paderborn_labels.yaml").read_text(encoding="utf-8"))
    for bid, ov in (cfg.get("overrides") or {}).items():
        if ov.get("status") != "verified" and not allow_pending:
            raise SystemExit(f"label override for {bid} is not verified; rerun with --allow-pending only for a dry run")
        b.loc[b["bearing"] == bid, ["class3", "damage_origin"]] = [ov["class3"], ov["damage_origin"]]
        b.loc[b["bearing"] == bid, "label_source"] = f"override:{ov.get('status')}"
    b["label_source"] = b.get("label_source", pd.Series(index=b.index, dtype=object)).fillna("factsheet")
    excl = set((cfg["primary_population"]["exclude_bearings"] or {}).keys())
    keep = b["class3"].isin(cfg["primary_population"]["classes"]) & ~b["bearing"].isin(excl)
    b["in_primary"] = keep
    b["campaign_year"] = pd.to_datetime(b["first_recording"]).dt.year
    return b


def stratified_pick(df: pd.DataFrame, quota: dict, rng: np.random.Generator) -> list[str]:
    chosen = []
    for (cls, origin), k in quota.items():
        pool = sorted(df[(df["class3"] == cls) & (df["damage_origin"] == origin)]["bearing"])
        if len(pool) < k:
            raise SystemExit(f"stratum {cls}/{origin} has {len(pool)} bearings, quota {k}")
        chosen += list(rng.choice(pool, size=k, replace=False))
    return sorted(chosen)


def stratified_folds(df: pd.DataFrame, k: int, rng: np.random.Generator) -> list[list[str]]:
    folds: list[list[str]] = [[] for _ in range(k)]
    per_class = defaultdict(lambda: [0] * k)
    for (cls, origin), grp in sorted(df.groupby(["class3", "damage_origin"])):
        ids = list(grp["bearing"])
        rng.shuffle(ids)
        for bid in ids:
            counts = per_class[cls]
            sizes = [len(f) for f in folds]
            j = min(range(k), key=lambda i: (counts[i], sizes[i], i))
            folds[j].append(bid)
            counts[j] += 1
    return [sorted(f) for f in folds]


def composition(df: pd.DataFrame, ids: list[str]) -> dict:
    sub = df[df["bearing"].isin(ids)]
    return {
        "n": len(sub),
        "class": dict(Counter(sub["class3"])),
        "origin": dict(Counter(sub["class3"] + ":" + sub["damage_origin"])),
        "campaign_year": {str(k): v for k, v in Counter(sub["campaign_year"]).items()},
        "manufacturer": dict(Counter(sub["manufacturer"])),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=20261107)
    ap.add_argument("--allow-pending", action="store_true", help="dry run with unverified overrides (not frozen)")
    ap.add_argument("--outer-folds", type=int, default=3)
    ap.add_argument("--bridge-folds", type=int, default=3)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    b = load_population(args.allow_pending)
    P = b[b["in_primary"]].copy()

    dev = stratified_pick(P, DEV_QUOTA, rng)
    T = P[~P["bearing"].isin(dev)]
    outer = stratified_folds(T, args.outer_folds, rng)

    protoA = {"seed": args.seed, "description": "unseen physical bearings; all conditions of a bearing follow its assignment",
              "dev_pool_never_tested": dev, "folds": []}
    for k, test in enumerate(outer):
        source = P[~P["bearing"].isin(test)]
        val = stratified_pick(source, VAL_QUOTA, rng)
        train = source[~source["bearing"].isin(val)]
        bridge = stratified_folds(train, args.bridge_folds, rng)
        protoA["folds"].append({
            "fold": k, "test": test, "validation": val, "train": sorted(train["bearing"]),
            "bridge_folds": bridge,
            "composition": {"test": composition(P, test), "validation": composition(P, val),
                            "train": composition(P, list(train["bearing"]))},
        })
        for part in ("test", "validation", "train"):
            assert all(cnt > 0 for cnt in Counter(P[P["bearing"].isin(protoA["folds"][-1][part])]["class3"]).values())
        assert not (set(test) & set(val)) and not (set(test) & set(train["bearing"])) and not (set(val) & set(train["bearing"]))
        for g in bridge:
            assert set(Counter(P[P["bearing"].isin(g)]["class3"])) == {"healthy", "inner", "outer"}, "bridge fold misses a class"

    protoB = {"seed": args.seed, "description": "held-out operating condition; test = non-development bearings under the target condition "
              "(previously observed bearings under a new condition)", "targets": []}
    for c in CONDITIONS:
        src = [x for x in CONDITIONS if x != c]
        protoB["targets"].append({
            "target_condition": c, "source_conditions": src,
            "train_bearings": sorted(P["bearing"]), "test_bearings": sorted(T["bearing"]),
            "inner_validation": [{"held_out_source_condition": v, "fit_conditions": [x for x in src if x != v]} for v in src],
            "bridge_folds": stratified_folds(P, args.bridge_folds, rng),
        })

    protoC = {"status": "declared, optional; run only after Protocols A and B and recorded before inspection",
              "design": "for outer fold k and target condition c: fit on fold-k train bearings under conditions != c; "
                        "validate on fold-k validation bearings under conditions != c; test on fold-k test bearings under c",
              "uses": "protocol_A folds x CONDITIONS"}

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["bearing", "class3", "damage_origin", "label_source", "in_primary", "manufacturer", "campaign_year", "first_recording"]
    b[cols].assign(dev_pool=b["bearing"].isin(dev)).to_csv(OUT / "paderborn_population.csv", index=False)
    status = "DRY_RUN_pending_label_verification" if args.allow_pending else "frozen"
    files = {
        "dev_pool.json": {"seed": args.seed, "bearings": dev, "composition": composition(P, dev),
                          "use": "development pilot and coarse preprocessing/architecture choices only; never test evidence"},
        "protocol_A.json": protoA, "protocol_B.json": protoB, "protocol_C.json": protoC,
    }
    for name, obj in files.items():
        obj = {"status": status, **obj} if isinstance(obj, dict) else obj
        (OUT / name).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    digest = "\n".join(f"{hashlib.sha256((OUT / n).read_bytes()).hexdigest()}  {n}" for n in sorted(list(files) + ["paderborn_population.csv"]))
    (OUT / "SPLITS_SHA256.txt").write_text(digest + "\n", encoding="utf-8")
    print(json.dumps({"dev": dev, "outer": outer, "val": [f["validation"] for f in protoA["folds"]],
                      "status": "DRY RUN (pending labels)" if args.allow_pending else "frozen"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
