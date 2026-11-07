"""Build memory-mapped signal caches for every retained Paderborn recording.

Usage:
  .venv/Scripts/python.exe -I scripts/build_cache.py --extracted D:/bahrain-data/extracted/paderborn \
      --out D:/bahrain-data/cache/paderborn --current-rates 8000 16000 --vibration-rate 32000

For each (channel, rate) a float32 memmap of shape (n_recordings, span*rate) is
written, zero-padded beyond each recording's valid length. One shared
index.csv lists the row order, labels, conditions and valid lengths; one
meta.json per (channel, rate) stores the preprocessing configuration and its
hash. Splits are applied later by the dataset class, never here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from cmkd.data.preprocess import NOMINAL_FS, config_hash, decimate, nominal_span, preprocessing_config
from cmkd.io.paderborn import read_recording

ROOT = Path(__file__).resolve().parents[1]
SPAN = 4.0
CHANNELS = {"current": "phase_current_1", "vibration": "vibration_1"}


def process(args: tuple[str, list[tuple[str, int]]]) -> dict:
    path, targets = args
    rec = read_recording(path)
    out = {}
    for key, rate in targets:
        ch = CHANNELS[key]
        x = nominal_span(rec.channels[ch].data, SPAN, NOMINAL_FS)
        y = decimate(x, int(NOMINAL_FS // rate)).astype(np.float32)
        out[(key, rate)] = y
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extracted", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--current-rates", type=int, nargs="+", default=[8000, 16000])
    ap.add_argument("--vibration-rate", type=int, default=32000)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    rec = pd.read_csv(ROOT / "manifests/paderborn_recordings.csv")
    rec = rec[rec["exclude_reason"].fillna("") == ""].sort_values(["bearing", "condition", "index"]).reset_index(drop=True)
    pop = pd.read_csv(ROOT / "manifests/splits/paderborn_population.csv")[["bearing", "class3", "damage_origin", "in_primary"]]
    rec = rec.drop(columns=["class3", "damage_origin"]).merge(pop, on="bearing", how="left")
    targets = [("current", r) for r in args.current_rates] + [("vibration", args.vibration_rate)]
    args.out.mkdir(parents=True, exist_ok=True)

    mm, metas = {}, {}
    for key, rate in targets:
        L = int(SPAN * rate)
        cfg = preprocessing_config(rate if key == "current" else args.current_rates[0],
                                   rate if key == "vibration" else args.vibration_rate, SPAN)
        cfg_ch = {**cfg, "channel_key": key, "channel": CHANNELS[key], "rate": rate, "length": L, "dtype": "float32",
                  "index_rows": len(rec)}
        h = config_hash(cfg_ch)
        name = f"{key}_{rate}"
        mm[(key, rate)] = np.lib.format.open_memmap(args.out / f"{name}.npy", mode="w+", dtype=np.float32, shape=(len(rec), L))
        metas[(key, rate)] = {"file": f"{name}.npy", "config": cfg_ch, "config_hash": h}

    jobs = [(str(args.extracted / r.bearing / r.bearing / r.file), targets) for r in rec.itertuples()]
    valid = {t: np.zeros(len(rec), dtype=np.int64) for t in targets}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(process, jobs, chunksize=4)):
            for t, y in res.items():
                n = min(y.size, mm[t].shape[1])
                mm[t][i, :n] = y[:n]
                valid[t][i] = n
            if i % 250 == 0:
                print(f"  {i}/{len(rec)}", flush=True)
    for t in targets:
        mm[t].flush()
        rec[f"valid_{t[0]}_{t[1]}"] = valid[t]
    rec["cache_row"] = np.arange(len(rec))
    keep_cols = ["cache_row", "file", "bearing", "class3", "damage_origin", "in_primary", "condition", "index",
                 "timestamp", "file_sha256"] + [f"valid_{t[0]}_{t[1]}" for t in targets]
    rec[keep_cols].to_csv(args.out / "index.csv", index=False)
    index_hash = hashlib.sha256((args.out / "index.csv").read_bytes()).hexdigest()[:16]
    for t, meta in metas.items():
        meta["index_sha256_16"] = index_hash
        (args.out / f"{meta['file'].replace('.npy', '')}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({f"{k[0]}_{k[1]}": v["config_hash"] for k, v in metas.items()}, indent=1))
    print("rows", len(rec), "short recordings:", {f"{t[0]}_{t[1]}": int((valid[t] < mm[t].shape[1]).sum()) for t in targets})
    return 0


if __name__ == "__main__":
    sys.exit(main())
