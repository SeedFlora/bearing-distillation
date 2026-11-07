"""Amendment A4, diagnostic 5 (descriptive; never used for any choice).

Question: is a test window's bridge residual associated with the current-only student's error on that
window? A4 allows the residual to be called a "proxy for transfer difficulty" only if this association
is positive.

Fixed before computing (2026-11-07, after the main runs, before this script was first executed):
- Residual: r = mean_d (l2n(z_T) - l2n(b(x)))^2 on Protocol A test windows, with z_T from the fold's frozen
  multimodal teacher and b from the auxiliary-control bridge of the same fold (fitted on all training
  bearings, seed 0, log-spectrum input), i.e. the bridge that never saw the test bearings.
- Reference student: CE-only (negative transfer is defined against it); secondary: ungated feature KD
  and the proposed gate. Error = per-window cross-entropy -log p(true), averaged over seeds 0-2;
  0/1 error is reported as well.
- Association: Spearman rho pooled over all test windows of the 21 test bearings, decomposed into a
  between-bearing rho (bearing means, n = 21) and the mean within-bearing rho; 95% percentile intervals
  from 10,000 bearing bootstrap replicates resampled within class (as for the primary endpoint).

Usage: .venv/Scripts/python.exe -I scripts/diag_residual_error.py
Output: results/analysis/diag5_residual_vs_error.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import rankdata

from cmkd.data.store import SignalStore
from cmkd.eval.stats import bootstrap_indices
from cmkd.kd.gates import residuals
from cmkd.models import Bridge
from cmkd.models.frontend import LogSpectrumFrontEnd
from cmkd.models.nets import Teacher
from cmkd.train.engine import InputPipe, run_forward

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
SPL, RES, CKPT = ROOT / "manifests/splits", ROOT / "results/main/A", ROOT / "checkpoints/main"
OUT = ROOT / "results/analysis/diag5_residual_vs_error.json"
EXT = ["KI04", "KI14"]
STUDENTS = ["ce", "feat", "gate"]
N_BOOT = 10000


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def fold_windows(store: SignalStore, fold: dict):
    te = store.windows(fold["test"], None, stride_s=0.5)
    k = fold["fold"]
    t_hash = json.loads((RES / f"fold{k}" / "teacher" / "metrics.json").read_text())["checkpoint_hash"]
    teacher = Teacher(store.current_rate, store.vibration_rate).to("cuda")
    teacher.load_state_dict(torch.load(CKPT / f"A_fold{k}_teacher_{t_hash}.pt", map_location="cuda", weights_only=True))
    teacher.eval()
    raw = InputPipe(store, 0.5)
    _, z_t = run_forward(lambda s: teacher(raw.current(te, s)[0], raw.vibration(te, s)), len(te), 512, "cuda")

    fe = LogSpectrumFrontEnd(8000, 4000)
    bridge = Bridge(None, stem_stride=fe.stem_stride).to("cuda")
    sd = torch.load(CKPT / f"A_fold{k}_bridge_head_s0.pt", map_location="cuda", weights_only=True)
    bridge.load_state_dict({n[len("bridge."):]: v for n, v in sd.items() if n.startswith("bridge.")})
    bridge.eval()
    pipe = InputPipe(store, 0.5, fe)
    (z_b,) = run_forward(lambda s: (bridge(pipe.current(te, s)[0]),), len(te), 512, "cuda")
    r = residuals(z_t.cpu().numpy(), z_b.cpu().numpy())

    df = pd.DataFrame({"fold": k, "bearing": te.bearing.astype(str), "label": te.label.cpu().numpy(), "r": r,
                       "recording": te.recording, "window_no": te.window_no})
    for m in STUDENTS:
        loss, err = [], []
        for seed in (0, 1, 2):
            a = np.load(RES / f"fold{k}" / m / f"seed{seed}" / "predictions_test.npz")
            assert np.array_equal(a["recording"], te.recording) and np.array_equal(a["window_no"], te.window_no), \
                f"window order differs for {m} seed {seed}"
            p = a["probs"][np.arange(len(te)), a["label"]]
            loss.append(-np.log(np.clip(p, 1e-12, 1.0)))
            err.append((a["probs"].argmax(1) != a["label"]).astype(float))
        df[f"loss_{m}"], df[f"err_{m}"] = np.mean(loss, 0), np.mean(err, 0)
    meta = {"fold": k, "teacher_checkpoint": t_hash, "bridge_checkpoint": f"A_fold{k}_bridge_head_s0.pt", "n_windows": len(te)}
    return df, meta


def association(df: pd.DataFrame, col: str, idx: np.ndarray, bearings: list[str]) -> dict:
    arr = {b: (g["r"].to_numpy(), g[col].to_numpy()) for b, g in df.groupby("bearing")}
    within = {b: spearman(*arr[b]) for b in bearings}
    w_vec = np.array([within[b] for b in bearings])
    m_r = np.array([arr[b][0].mean() for b in bearings])
    m_e = np.array([arr[b][1].mean() for b in bearings])

    def stats(sel: np.ndarray) -> tuple[float, float, float]:
        x = np.concatenate([arr[bearings[i]][0] for i in sel])
        y = np.concatenate([arr[bearings[i]][1] for i in sel])
        return spearman(x, y), spearman(m_r[sel], m_e[sel]), float(np.nanmean(w_vec[sel]))

    point = stats(np.arange(len(bearings)))
    boot = np.array([stats(row) for row in idx])
    ci = lambda j: [float(np.nanpercentile(boot[:, j], 2.5)), float(np.nanpercentile(boot[:, j], 97.5))]
    return {"pooled_rho": point[0], "pooled_ci95": ci(0), "between_bearing_rho": point[1], "between_ci95": ci(1),
            "mean_within_bearing_rho": point[2], "within_ci95": ci(2),
            "within_rho_by_bearing": {b: round(v, 4) for b, v in within.items()}}


def main() -> int:
    pop = pd.read_csv(SPL / "paderborn_population.csv")
    prim = sorted(pop.loc[pop["in_primary"], "bearing"])
    index = pd.read_csv(CACHE / "index.csv")
    rows = index.loc[index["bearing"].isin(prim + EXT), "cache_row"].to_numpy()   # same rows as run_main.py
    store = SignalStore(CACHE, rows, 8000, 32000)
    folds = json.loads((SPL / "protocol_A.json").read_text())["folds"]
    parts, metas = [], []
    with torch.no_grad():
        for f in folds:
            d, m = fold_windows(store, f)
            parts.append(d)
            metas.append(m)
            print(f"fold {m['fold']}: {m['n_windows']} test windows, median residual {np.median(d['r']):.4f}", flush=True)
    df = pd.concat(parts, ignore_index=True)
    bclass = df.groupby("bearing")["label"].first()
    bearings = list(bclass.index)
    idx = bootstrap_indices(bclass.to_numpy(), N_BOOT)
    out = {"definition": __doc__.split("Usage:")[0].strip(), "folds": metas, "n_bearings": len(bearings),
           "n_windows": int(len(df)), "median_residual_by_class": df.groupby("label")["r"].median().round(4).to_dict(),
           "residual_between_bearing_share": float(df.groupby("bearing")["r"].transform("mean").var(ddof=0) / df["r"].var(ddof=0)),
           "association": {}}
    for m in STUDENTS:
        for kind in ("loss", "err"):
            col = f"{kind}_{m}"
            out["association"][col] = association(df, col, idx, bearings)
            a = out["association"][col]
            print(f"{col:10s} pooled {a['pooled_rho']:+.3f} {np.round(a['pooled_ci95'], 3)}  between {a['between_bearing_rho']:+.3f} "
                  f"{np.round(a['between_ci95'], 3)}  within {a['mean_within_bearing_rho']:+.3f} {np.round(a['within_ci95'], 3)}", flush=True)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
