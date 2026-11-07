"""Training objectives. Ground-truth cross-entropy is kept on every sample."""
from __future__ import annotations

import torch
import torch.nn.functional as F


def logit_kd(student_logits, teacher_logits, temperature: float) -> torch.Tensor:
    """Hinton-style KD: T^2 * KL(softmax(t/T) || softmax(s/T)), batch mean."""
    t = temperature
    return F.kl_div(F.log_softmax(student_logits / t, dim=1), F.softmax(teacher_logits.detach() / t, dim=1),
                    reduction="batchmean") * (t * t)


def feature_alignment(student_proj, teacher_z, weights=None, mask=None, delta: float = 1.0) -> torch.Tensor:
    """Per-sample Huber alignment of L2-normalised features, summed over dimensions (~ 1 - cos).

    ``weights`` (N,) and ``mask`` (N, D) are fixed tensors without gradients.
    Masked dimensions are excluded and the kept ones rescaled to D (SAAMask-style variant).
    """
    s = F.normalize(student_proj, dim=1)
    t = F.normalize(teacher_z.detach(), dim=1)
    per_dim = F.huber_loss(s, t, reduction="none", delta=delta)
    # Sum over dimensions: for unit vectors in the quadratic Huber regime this equals 1 - cos,
    # so lambda is on the scale of the cross-entropy (a mean over 64 dimensions made the term ~64x
    # weaker; review finding, Amendment A5). Masked dimensions are excluded and the kept
    # dimensions are rescaled to the full dimensionality, keeping masked and unmasked runs comparable.
    d = per_dim.shape[1]
    if mask is not None:
        per_sample = (per_dim * mask).sum(1) * (d / mask.sum(1).clamp_min(1.0))
    else:
        per_sample = per_dim.sum(1)
    if weights is not None:
        if weights.requires_grad:
            raise ValueError("gate weights must be detached")
        per_sample = per_sample * weights
    return per_sample.mean()


def objective(student_logits, y, student_proj=None, teacher_z=None, teacher_logits=None, *, lam: float = 0.0,
              weights=None, mask=None, kd_weight: float = 0.0, temperature: float = 4.0) -> dict:
    ce = F.cross_entropy(student_logits, y)
    out = {"ce": ce, "total": ce}
    if lam > 0:
        fa = feature_alignment(student_proj, teacher_z, weights=weights, mask=mask)
        out["feature"] = fa
        out["total"] = out["total"] + lam * fa
    if kd_weight > 0:
        kd = logit_kd(student_logits, teacher_logits, temperature)
        out["logit_kd"] = kd
        out["total"] = out["total"] + kd_weight * kd
    return out
