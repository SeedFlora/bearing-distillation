"""Development pilot on development bearings only (protocol Amendment A1).

Usage: .venv/Scripts/python.exe -I scripts/run_pilot.py [--epochs 30]

Writes results/pilot/<pilot>/<fold>/... (metrics.json, predictions.npz) and
checkpoints/pilot/...; completed runs are skipped on restart.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from cmkd.data.store import CLASSES, SignalStore
from cmkd.kd import gates as G
from cmkd.models.frontend import ElectricalOrderFrontEnd
from cmkd.train.engine import TrainCfg, crossfit_bridges, predict, teacher_targets, train_student, train_teacher

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
OUT, CKPT = ROOT / "results/pilot", ROOT / "checkpoints/pilot"
N15 = ["N15_M07_F10", "N15_M01_F10", "N15_M07_F04"]
N09 = ["N09_M07_F10"]
SPEC_A = [("ce8", {"method": "ce"}), ("ce16", {"method": "ce", "rate": 16000}), ("ce_of", {"method": "ce", "of": True}),
          ("feat8", {"method": "feat", "hp": {"lambda": 1.0}}), ("gate8", {"method": "gate", "hp": {"lambda": 1.0}})]
SPEC_B = [("ce8", {"method": "ce"}), ("ce_of", {"method": "ce", "of": True}),
          ("feat8", {"method": "feat", "hp": {"lambda": 1.0}}), ("gate8", {"method": "gate", "hp": {"lambda": 1.0}}),
          ("feat_of", {"method": "feat", "of": True, "hp": {"lambda": 1.0}})]


def jdump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)), encoding="utf-8")


def save_pred(path: Path, idx, res) -> None:
    extra = {"fe": res["fe"]} if "fe" in res else {}
    np.savez_compressed(path, probs=res["probs"], label=idx.label.cpu().numpy(), recording=idx.recording,
                        bearing=idx.bearing.astype(str), condition=idx.condition.astype(str), window_no=idx.window_no, **extra)


def residual_table(tr, r, w) -> dict:
    df = pd.DataFrame({"cls": [CLASSES[i] for i in tr.label.cpu().numpy()], "cond": tr.condition, "r": r, "w": w})
    out = {}
    for key, col in (("by_class", "cls"), ("by_condition", "cond")):
        g = df.groupby(col).agg(r_mean=("r", "mean"), r_median=("r", "median"), w_mean=("w", "mean"),
                                w_min=("w", "min"), w_max=("w", "max"))
        out[key] = {str(k): {c: float(v) for c, v in row.items()} for k, row in g.round(4).iterrows()}
    return out


def run_sanity(stores, dev, cfg) -> None:
    """Pilot-S: learnability check only (same bearings, held-out recordings 15-20). Not generalisation evidence."""
    s8 = stores[0]
    out = OUT / "S_within_bearing"
    rec_no = dict(zip(s8.meta["cache_row"], s8.meta["index"].astype(int)))
    tr_all = s8.windows(dev, None, stride_s=0.25)
    ev_all = s8.windows(dev, None, stride_s=0.5)
    tr = tr_all.subset(np.array([rec_no[r] <= 14 for r in tr_all.recording]))
    ev = ev_all.subset(np.array([rec_no[r] >= 15 for r in ev_all.recording]))
    assert not set(tr.recording) & set(ev.recording)
    teacher, tfwd, tinfo = train_teacher(s8, tr, ev, cfg)
    tres = predict(teacher, tfwd, ev, 512, "cuda")
    tinfo["eval_metrics"] = tres["metrics"]
    jdump(out / "teacher" / "metrics.json", tinfo)
    print(f"[S] teacher eval rec-F1 {tres['metrics']['recording']['macro_f1']:.3f}", flush=True)
    for name, fr in (("ce8", None), ("ce_of", ElectricalOrderFrontEnd(8000, 4000))):
        model, fwd, info = train_student("ce", s8, tr, ev, cfg, None, {}, frontend=fr)
        res = predict(model, fwd, ev, 512, "cuda")
        info["eval_metrics"] = res["metrics"]
        jdump(out / name / "metrics.json", info)
        print(f"[S] {name:<8} eval rec-F1 {res['metrics']['recording']['macro_f1']:.3f}", flush=True)


def run_fold(tag, stores, train_b, eval_b, train_cond, eval_cond, cfg, specs, group_kind, groups=None):
    s8, s16 = stores
    out = OUT / tag
    if any((out / n / "metrics.json").exists() for n, _ in specs):
        # a fold is never partially re-run: students must share the fold's single teacher (review finding)
        print(f"[{tag}] has existing student results; skipped (move the folder to re-run)", flush=True)
        return
    tr = s8.windows(train_b, train_cond, stride_s=0.25)
    ev = s8.windows(eval_b, eval_cond, stride_s=0.5)
    tr16 = s16.windows(train_b, train_cond, stride_s=0.25)
    ev16 = s16.windows(eval_b, eval_cond, stride_s=0.5)
    print(f"[{tag}] train windows {len(tr)} eval windows {len(ev)}", flush=True)

    teacher, tfwd, tinfo = train_teacher(s8, tr, ev, cfg)
    tres = predict(teacher, tfwd, ev, 512, "cuda")
    tinfo["eval_metrics"] = tres["metrics"]
    tinfo["train_bearings_metrics"] = predict(teacher, tfwd, s8.windows(train_b, train_cond, stride_s=0.5), 512, "cuda")["metrics"]
    tinfo["preprocessing_hashes"] = s8.config_hashes
    jdump(out / "teacher" / "metrics.json", tinfo)
    save_pred(out / "teacher" / "predictions.npz", ev, tres)
    (CKPT / tag).mkdir(parents=True, exist_ok=True)
    torch.save(teacher.state_dict(), CKPT / tag / f"teacher_{tinfo['checkpoint_hash']}.pt")
    print(f"[{tag}] teacher eval recording macro-F1 {tres['metrics']['recording']['macro_f1']:.3f}", flush=True)

    targets = teacher_targets(teacher, tfwd, tr, 512, "cuda")
    key = tr.condition if group_kind == "condition" else np.array([groups[b] for b in tr.bearing], dtype=object)
    cf = crossfit_bridges(s8, tr, targets["z"], key, group_kind=group_kind, epochs=15, seed=cfg.seed)
    r = cf["residual"]
    y = tr.label.cpu().numpy()
    w = G.class_normalise(G.residual_gate(r, tau=float(np.median(r)), eps=0.2), y)
    jdump(out / "bridges.json", {"folds": cf["folds"], "group_kind": group_kind, "residual_median": float(np.median(r)),
                                 "table": residual_table(tr, r, w), "teacher_checkpoint": tinfo["checkpoint_hash"]})
    np.savez_compressed(out / "residuals.npz", residual=r, weight=w, provenance=cf["provenance"], recording=tr.recording,
                        window_no=tr.window_no, label=y, condition=tr.condition.astype(str), bearing=tr.bearing.astype(str))

    for name, spec in specs:
        d = out / name
        if (d / "metrics.json").exists():
            print(f"[{tag}] skip {name}", flush=True)
            continue
        st, a, b = (s16, tr16, ev16) if spec.get("rate") == 16000 else (s8, tr, ev)
        fr = ElectricalOrderFrontEnd(8000, 4000) if spec.get("of") else None
        method = spec["method"]
        model, fwd, info = train_student(method, st, a, b, cfg, targets if method != "ce" else None, spec.get("hp", {}),
                                         frontend=fr, weights=w if method == "gate" else None)
        res = predict(model, fwd, b, 512, "cuda")
        info.update(spec=spec, eval_metrics=res["metrics"], teacher_checkpoint=tinfo["checkpoint_hash"])
        if "fe" in res:
            info["fe_hz"] = {"mean": float(res["fe"].mean()), "sd": float(res["fe"].std()), "min": float(res["fe"].min()),
                             "max": float(res["fe"].max())}
        jdump(d / "metrics.json", info)
        save_pred(d / "predictions.npz", b, res)
        torch.save(model.state_dict(), CKPT / tag / f"{name}_{info['checkpoint_hash']}.pt")
        m = res["metrics"]
        print(f"[{tag}] {name:<8} best_epoch {info['best_epoch']:>2} eval rec-F1 {m['recording']['macro_f1']:.3f} "
              f"win-F1 {m['window']['macro_f1']:.3f} ({info['train_seconds']} s)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=30)
    args = ap.parse_args()
    dev = json.loads((ROOT / "manifests/splits/dev_pool.json").read_text())["bearings"]
    idx = pd.read_csv(CACHE / "index.csv")
    rows = idx.loc[idx["bearing"].isin(dev), "cache_row"].to_numpy()
    assert set(idx.loc[idx["cache_row"].isin(rows), "bearing"]) == set(dev)
    t0 = time.time()
    stores = (SignalStore(CACHE, rows, 8000, 32000), SignalStore(CACHE, rows, 16000, None))
    cfg_a = TrainCfg(epochs=args.epochs, patience=8, seed=0)
    if not (OUT / "S_within_bearing" / "ce_of" / "metrics.json").exists():
        run_sanity(stores, dev, TrainCfg(epochs=15, patience=5, seed=0))
    folds = {"P1": (["K001", "KA07", "KI16"], ["K005", "KA16", "KI01"]), "P2": (["K005", "KA16", "KI01"], ["K001", "KA07", "KI16"])}
    for f, (trb, evb) in folds.items():
        run_fold(f"A_{f}", stores, trb, evb, None, None, cfg_a, SPEC_A, "condition")
    cfg_b = TrainCfg(epochs=args.epochs, seed=0, select_best=False, early_stopping=False)
    groups = {b: ("G1" if b in ("K001", "KA07", "KI01") else "G2") for b in dev}
    run_fold("B_N09", stores, dev, dev, N15, N09, cfg_b, SPEC_B, "bearing", groups)
    print(f"pilot finished in {time.time() - t0:.0f} s; GPU: {torch.cuda.get_device_name(0)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
