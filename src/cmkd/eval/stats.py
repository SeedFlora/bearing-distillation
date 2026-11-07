"""Bearing-level bootstrap, paired differences and Holm adjustment.

The physical bearing is the resampling unit. Each method's recording-level
decisions are summarised per bearing as a 3x3 confusion contribution; a
bootstrap replicate resamples bearings with replacement *within class* and sums
their contributions, so every replicate keeps all classes and scores all
methods on the same bearings (paired).
"""
from __future__ import annotations

import numpy as np

N_CLASSES = 3


def bearing_confusions(rec_true: np.ndarray, rec_pred: np.ndarray, rec_bearing: np.ndarray, bearings: list[str]) -> np.ndarray:
    """(n_bearings, 3, 3) confusion counts from recording-level decisions."""
    out = np.zeros((len(bearings), N_CLASSES, N_CLASSES), dtype=np.int64)
    pos = {b: i for i, b in enumerate(bearings)}
    for t, p, b in zip(rec_true, rec_pred, rec_bearing):
        out[pos[b], t, p] += 1
    return out


def macro_f1_from_confusion(cm: np.ndarray) -> np.ndarray:
    """Macro-F1 for one (3,3) matrix or a stack (..., 3, 3); classes absent from truth and prediction score 0."""
    tp = np.diagonal(cm, axis1=-2, axis2=-1).astype(float)
    fp = cm.sum(axis=-2) - tp
    fn = cm.sum(axis=-1) - tp
    den = 2 * tp + fp + fn
    f1 = np.where(den > 0, 2 * tp / np.where(den > 0, den, 1), 0.0)
    return f1.mean(axis=-1)


def bootstrap_indices(bearing_class: np.ndarray, n_boot: int, seed: int = 20261107) -> np.ndarray:
    """(n_boot, n_bearings) indices resampled within class."""
    rng = np.random.default_rng(seed)
    cols = []
    order = []
    for c in np.unique(bearing_class):
        members = np.flatnonzero(bearing_class == c)
        cols.append(rng.choice(members, size=(n_boot, members.size), replace=True))
        order.append(members)
    return np.concatenate(cols, axis=1)


def paired_bootstrap(cm_a: np.ndarray, cm_b: np.ndarray, idx: np.ndarray) -> dict:
    """cm_*: (n_seeds, n_bearings, 3, 3). Statistic = seed-mean macro-F1(a) - seed-mean macro-F1(b)."""
    point_a = macro_f1_from_confusion(cm_a.sum(axis=1)).mean()
    point_b = macro_f1_from_confusion(cm_b.sum(axis=1)).mean()
    boot_a = macro_f1_from_confusion(cm_a[:, idx].sum(axis=2)).mean(axis=0)   # (n_boot,)
    boot_b = macro_f1_from_confusion(cm_b[:, idx].sum(axis=2)).mean(axis=0)
    d = boot_a - boot_b
    p = 2 * min((d <= 0).mean(), (d >= 0).mean())
    return {"a": float(point_a), "b": float(point_b), "diff": float(point_a - point_b),
            "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], "p_boot": float(min(1.0, p))}


def bootstrap_ci(cm: np.ndarray, idx: np.ndarray) -> list[float]:
    boot = macro_f1_from_confusion(cm[:, idx].sum(axis=2)).mean(axis=0)
    return [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj
