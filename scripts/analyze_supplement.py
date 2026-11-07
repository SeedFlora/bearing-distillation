"""Supplementary analyses added AFTER the pre-registered analysis was inspected (Amendment A6; descriptive).

None of these numbers was used to choose a model, a setting or a hypothesis. They support interpretation:
1. Teacher reference vs CE-only student on Protocol A test bearings, paired bearing bootstrap (the teacher
   is evaluated on recordings with its own current+vibration input; it is a reference, not a deployable model).
2. Minimum detectable effect (80% power) of the primary contrasts, from the bootstrap SE of each paired
   difference, at alpha = 0.05 and at the Holm-first alpha = 0.01.
3. Holm adjustment over the 20 gate contrasts of Protocol B (gate vs CE, feature KD, SAAMask-style,
   shuffled and in-sample gate; four held-out settings), as a sensitivity check of the unadjusted intervals.
4. Class-wise recall (pre-declared secondary endpoint, protocol section 9.1), pooled over folds, seed-mean.

Usage: .venv/Scripts/python.exe -I scripts/analyze_supplement.py
Output: results/analysis/supplement.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import norm

from cmkd.data.store import SignalStore
from cmkd.eval.stats import bearing_confusions, bootstrap_ci, bootstrap_indices, holm, macro_f1_from_confusion, paired_bootstrap
from cmkd.models.nets import Teacher
from cmkd.train.engine import InputPipe, run_forward

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_main import collect, complete_seeds, confusions  # noqa: E402

CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
SPL, RES, CKPT, OUT = ROOT / "manifests/splits", ROOT / "results/main", ROOT / "checkpoints/main", ROOT / "results/analysis"
N_BOOT = 10000


def teacher_recordings_A() -> pd.DataFrame:
    """Recording-level decisions of the three frozen Protocol A teachers on their test windows."""
    pop = pd.read_csv(SPL / "paderborn_population.csv")
    prim = sorted(pop.loc[pop["in_primary"], "bearing"])
    index = pd.read_csv(CACHE / "index.csv")
    rows = index.loc[index["bearing"].isin(prim + ["KI04", "KI14"]), "cache_row"].to_numpy()
    store = SignalStore(CACHE, rows, 8000, 32000)
    parts = []
    for f in json.loads((SPL / "protocol_A.json").read_text())["folds"]:
        k = f["fold"]
        te = store.windows(f["test"], None, stride_s=0.5)
        h = json.loads((RES / "A" / f"fold{k}" / "teacher" / "metrics.json").read_text())["checkpoint_hash"]
        t = Teacher(8000, 32000).to("cuda")
        t.load_state_dict(torch.load(CKPT / f"A_fold{k}_teacher_{h}.pt", map_location="cuda", weights_only=True))
        t.eval()
        pipe = InputPipe(store, 0.5)
        with torch.no_grad():
            logits, _ = run_forward(lambda s: t(pipe.current(te, s)[0], pipe.vibration(te, s)), len(te), 512, "cuda")
        p = torch.softmax(logits, 1).cpu().numpy()
        df = pd.DataFrame(p, columns=["p0", "p1", "p2"]).assign(recording=te.recording, label=te.label.cpu().numpy(),
                                                                 bearing=te.bearing.astype(str), unit=f"fold{k}")
        g = df.groupby("recording")
        rec = g[["p0", "p1", "p2"]].mean()
        rec["label"], rec["bearing"], rec["unit"] = g["label"].first(), g["bearing"].first(), g["unit"].first()
        rec["pred"] = rec[["p0", "p1", "p2"]].to_numpy().argmax(1)
        parts.append(rec.reset_index())
    return pd.concat(parts, ignore_index=True)


def recall(cm: np.ndarray) -> list[float]:
    cm = cm.sum(axis=tuple(range(cm.ndim - 2))) if cm.ndim > 2 else cm
    return [float(cm[c, c] / cm[c].sum()) for c in range(3)]


def mde(fam: dict, cms: dict, idx: np.ndarray, ref: str = "gate") -> dict:
    out = {}
    for other in fam:
        a = macro_f1_from_confusion(cms[ref][:, idx].sum(axis=2)).mean(axis=0)
        b = macro_f1_from_confusion(cms[other][:, idx].sum(axis=2)).mean(axis=0)
        se = float(np.std(a - b, ddof=1))
        out[other] = {"bootstrap_se": se, "mde80_alpha05": float((norm.ppf(0.975) + norm.ppf(0.8)) * se),
                      "mde80_alpha01": float((norm.ppf(0.995) + norm.ppf(0.8)) * se)}
    return out


def main() -> int:
    res = {"note": __doc__.split("Usage:")[0].strip()}
    # ---------------- Protocol A
    data, _ = collect("A")
    data = complete_seeds(data, 3)
    any_df = next(iter(data["ce"].values()))
    bdf = any_df.groupby("bearing")["label"].first()
    bearings, bclass = list(bdf.index), bdf.to_numpy()
    idx = bootstrap_indices(bclass, N_BOOT)
    cms = confusions(data, bearings)
    trec = teacher_recordings_A()
    cm_t = bearing_confusions(trec["label"].to_numpy(), trec["pred"].to_numpy(), trec["bearing"].to_numpy(), bearings)[None]
    res["A_teacher_vs"] = {m: paired_bootstrap(cm_t, cms[m], idx) for m in ("ce", "feat", "gate", "ce_ord", "feat_ord")}
    res["A_teacher_pooled_macro_f1_check"] = float(macro_f1_from_confusion(cm_t.sum(axis=(0, 1))))
    res["A_teacher_ci95"] = bootstrap_ci(cm_t, idx)
    fam = ["ce", "feat", "saamask", "shuffled_gate", "insample_gate"]
    res["A_mde_gate_vs"] = mde(fam, cms, idx)
    res["A_mde_feat_vs_ce"] = mde(["ce"], cms, idx, ref="feat")["ce"]
    res["A_recall"] = {m: recall(cms[m]) for m in ("ce", "logit_kd", "feat", "gate", "saamask", "ce_ord", "feat_ord", "gate_ord")}
    res["A_recall"]["teacher"] = recall(cm_t)
    res["A_confusion_seed_mean"] = {m: (cms[m].sum(axis=1).mean(axis=0)).round(1).tolist() for m in ("ce", "feat", "gate", "ce_ord")}
    res["A_confusion_seed_mean"]["teacher"] = cm_t.sum(axis=(0, 1)).tolist()
    # ---------------- Protocol B
    b = json.loads((OUT / "protocol_B.json").read_text())
    pvals, rows = {}, {}
    for u in [k for k in b if k != "teacher"]:
        for o in ("ce", "feat", "saamask", "shuffled_gate", "insample_gate"):
            r = b[u]["vs_ce"]["gate"] if o == "ce" else b[u]["gate_vs"][o]
            pvals[f"{u}|{o}"] = r["p_boot"]
            rows[f"{u}|{o}"] = {"diff": r["diff"], "ci95": r["ci95"], "p_boot": r["p_boot"]}
    adj = holm(pvals)
    for k in rows:
        rows[k]["p_holm20"] = adj[k]
    res["B_gate_contrasts_holm20"] = rows
    rb = {}
    for u in [k for k in b if k != "teacher"]:
        d, _ = collect("B", unit_filter=lambda n, uu=u: n == uu)
        d = complete_seeds(d, 1)
        bd = next(iter(d["ce"].values())).groupby("bearing")["label"].first()
        c = confusions(d, list(bd.index))
        rb[u] = {m: recall(c[m]) for m in ("ce", "feat", "gate", "ce_ord", "feat_ord", "gate_ord")}
    res["B_recall"] = rb
    (OUT / "supplement.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    t = res["A_teacher_vs"]
    print("teacher pooled F1 (check vs 0.576):", round(res["A_teacher_pooled_macro_f1_check"], 4))
    for m, r in t.items():
        print(f"teacher - {m:9s} {r['diff']:+.3f} [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] p {r['p_boot']:.4f}")
    for m, r in res["A_mde_gate_vs"].items():
        print(f"MDE gate vs {m:14s} SE {r['bootstrap_se']:.4f} MDE80 a.05 {r['mde80_alpha05']:.3f} a.01 {r['mde80_alpha01']:.3f}")
    print("MDE feat vs ce", {k: round(v, 3) for k, v in res["A_mde_feat_vs_ce"].items()})
    for m, r in res["A_recall"].items():
        print(f"recall A {m:9s} healthy {r[0]:.3f} outer {r[1]:.3f} inner {r[2]:.3f}")
    for k, r in rows.items():
        if r["p_holm20"] < 0.05:
            print(f"B Holm20 survives: {k:30s} {r['diff']:+.3f} p_holm {r['p_holm20']:.4f}")
    for u, d in rb.items():
        print(u, {m: [round(x, 2) for x in v] for m, v in d.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
