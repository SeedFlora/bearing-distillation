"""Checks for networks, gates and losses (synthetic tensors only)."""
import inspect

import numpy as np
import pytest
import torch

from cmkd.kd.gates import (class_normalise, confidence_gate, residual_gate, residuals, saamask_topk_mask,
                           shuffle_within_groups)
from cmkd.kd.losses import feature_alignment, objective
from cmkd.models import Bridge, Student, Teacher, count_parameters


@pytest.mark.parametrize("fs", [8000, 16000])
def test_shapes_and_student_input_contract(fs):
    xc = torch.randn(4, 1, int(0.5 * fs))
    xv = torch.randn(4, 1, 16000)
    t = Teacher(fs, 32000).eval()
    logits, z = t(xc, xv)
    assert logits.shape == (4, 3) and z.shape == (4, 64)
    s = Student(fs)
    sl, f = s(xc)
    assert sl.shape == (4, 3) and s.proj(f).shape == (4, 64)
    # the deployable student accepts exactly one tensor: the current window
    assert list(inspect.signature(s.forward).parameters) == ["x_current"]
    b = Bridge(fs)
    zb = b(xc)
    assert torch.allclose(zb.norm(dim=1), torch.ones(4), atol=1e-5)
    with pytest.raises(ValueError):
        t(xc)  # multimodal teacher refuses to run without vibration
    assert count_parameters(s) < count_parameters(t)


def test_current_only_teacher_control_runs_without_vibration():
    t = Teacher(8000, None).eval()
    logits, z = t(torch.randn(2, 1, 4000))
    assert logits.shape == (2, 3)


def test_gate_bounds_detached_and_class_means():
    rng = np.random.default_rng(0)
    zt, zb = rng.normal(size=(300, 64)), rng.normal(size=(300, 64))
    r = residuals(zt, zb)
    w = residual_gate(r, tau=np.median(r), eps=0.1)
    assert np.all(w > 0.1) and np.all(w <= 1.0)
    y = rng.integers(0, 3, size=300)
    wn = class_normalise(w, y)
    for c in range(3):
        assert abs(wn[y == c].mean() - 1.0) < 1e-9
    with pytest.raises(ValueError):
        residual_gate(r, tau=0.0, eps=0.1)
    with pytest.raises(ValueError):
        residual_gate(r, tau=1.0, eps=1.0)
    with pytest.raises(FloatingPointError):
        residuals(np.full((2, 4), np.nan), np.ones((2, 4)))
    wt = torch.tensor(wn, requires_grad=True)
    with pytest.raises(ValueError):
        feature_alignment(torch.randn(300, 64), torch.randn(300, 64), weights=wt)


def test_shuffle_preserves_group_multisets():
    rng = np.random.default_rng(1)
    w = rng.random(200)
    g = rng.integers(0, 6, size=200)
    s = shuffle_within_groups(w, g, seed=3)
    for k in np.unique(g):
        assert np.allclose(np.sort(w[g == k]), np.sort(s[g == k]))
    assert not np.allclose(w, s)


def test_saamask_masks_top_twenty_percent():
    err = np.arange(10, dtype=float)[None, :].repeat(3, axis=0)
    m = saamask_topk_mask(err, ratio=0.2)
    assert m.shape == (3, 10) and np.all(m[:, -2:] == 0) and np.all(m[:, :-2] == 1)


def test_confidence_gate_and_objective_keep_ce_on_all_samples():
    y = torch.tensor([0, 1, 2, 0])
    logits = torch.randn(4, 3, requires_grad=True)
    w = torch.zeros(4)  # even with every gate at zero, CE still trains every sample
    out = objective(logits, y, torch.randn(4, 64), torch.randn(4, 64), lam=1.0, weights=w)
    assert torch.allclose(out["total"], out["ce"])
    out["total"].backward()
    assert logits.grad.abs().sum() > 0
    cg = confidence_gate(np.array([0.9, 0.2, 0.5, 0.7]), np.array([0, 1, 2, 0]))
    assert np.isclose(cg[[0, 3]].mean(), 1.0)
