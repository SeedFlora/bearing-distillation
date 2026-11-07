"""Fixed (detached) per-sample gates for the feature-alignment term.

All gates are computed once, before student optimisation, as plain NumPy
arrays indexed by training-window id. They never receive gradients.
"""
from __future__ import annotations

import numpy as np


def l2n(z: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    return z / (np.linalg.norm(z, axis=-1, keepdims=True) + eps)


def residuals(z_teacher: np.ndarray, z_pred: np.ndarray) -> np.ndarray:
    """r_i = mean squared distance between normalised teacher and prediction."""
    r = np.mean((l2n(z_teacher) - l2n(z_pred)) ** 2, axis=-1)
    if not np.all(np.isfinite(r)):
        raise FloatingPointError("non-finite residual")
    return r


def residual_gate(r: np.ndarray, tau: float, eps: float) -> np.ndarray:
    """w_raw = eps + (1 - eps) * exp(-r / tau), with 0 < eps < 1 and tau > 0."""
    if not (0.0 < eps < 1.0):
        raise ValueError("epsilon must lie in (0, 1)")
    if not tau > 0:
        raise ValueError("tau must be positive")
    w = eps + (1.0 - eps) * np.exp(-np.asarray(r, dtype=np.float64) / tau)
    if not np.all(np.isfinite(w)):
        raise FloatingPointError("non-finite gate")
    return w


def class_normalise(w: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Divide each weight by the mean training weight of its class (class means become 1)."""
    w = np.asarray(w, dtype=np.float64).copy()
    for c in np.unique(y):
        m = w[y == c].mean()
        if not m > 0:
            raise FloatingPointError(f"class {c} has non-positive mean weight")
        w[y == c] /= m
    return w


def shuffle_within_groups(w: np.ndarray, groups: np.ndarray, seed: int) -> np.ndarray:
    """Permute weights inside each group (e.g. class x source condition).

    Preserves the multiset of weights in every group, hence the class means and
    the average loss scale, while breaking the sample-to-weight assignment.
    """
    rng = np.random.default_rng(seed)
    out = np.asarray(w, dtype=np.float64).copy()
    for g in np.unique(groups):
        idx = np.flatnonzero(groups == g)
        out[idx] = out[rng.permutation(idx)]
    return out


def confidence_gate(p_true: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Teacher-confidence baseline: teacher probability of the true class, class-normalised."""
    return class_normalise(np.clip(np.asarray(p_true, dtype=np.float64), 1e-6, 1.0), y)


def saamask_topk_mask(sq_err: np.ndarray, ratio: float = 0.2) -> np.ndarray:
    """SAAMask-style mask: zero the top ``ratio`` dimensions of each sample's squared error.

    Following Jo and Um (IEEE Access, 2026), Eqs. (3)-(5): a binary N x D mask
    built once after warm-up; K = round(ratio * D).
    """
    sq_err = np.asarray(sq_err)
    n, d = sq_err.shape
    k = int(round(ratio * d))
    mask = np.ones((n, d), dtype=np.float32)
    if k > 0:
        top = np.argpartition(-sq_err, kth=k - 1, axis=1)[:, :k]
        np.put_along_axis(mask, top, 0.0, axis=1)
    return mask
