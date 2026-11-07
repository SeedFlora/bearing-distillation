"""Synthetic checks for the electrical-order front-end and bridge cross-fitting provenance."""
import numpy as np
import pytest
import torch

from cmkd.data.store import WindowIndex
from cmkd.models.frontend import ElectricalOrderFrontEnd, LogOrderSpectrumFrontEnd
from cmkd.train.engine import crossfit_bridges


def _signal(fe, fs=8000, n=4000, phase=0.3):
    t = np.arange(n) / fs
    # fundamental plus two components at fixed electrical orders (as defect sidebands would be)
    return (np.sin(2 * np.pi * fe * t + phase) + 0.05 * np.sin(2 * np.pi * 1.76 * fe * t)
            + 0.03 * np.sin(2 * np.pi * 7.0 * fe * t)).astype(np.float32)


def test_frontend_estimates_supply_frequency_and_maps_speeds_to_the_same_order_grid():
    fr = ElectricalOrderFrontEnd(fs=8000, window=4000)
    x = torch.tensor(np.stack([_signal(60.0), _signal(100.0)]))
    y, fe = fr(x)
    assert torch.allclose(fe, torch.tensor([60.0, 100.0]), atol=0.05)
    assert y.shape == (2, 28 * 64)
    a, b = y[0].numpy(), y[1].numpy()
    core = slice(64, -64)
    corr = np.corrcoef(a[core], b[core])[0, 1]
    assert corr > 0.99, corr


def test_frontend_rejects_wrong_window_length():
    fr = ElectricalOrderFrontEnd(fs=8000, window=4000)
    with pytest.raises(ValueError):
        fr(torch.zeros(2, 3000))


class _FakeStore:
    """Minimal CPU store: each recording is a deterministic signal."""

    def __init__(self, n_rec=6, length=16000, rate=8000):
        rng = np.random.default_rng(0)
        self.cur = torch.tensor(rng.normal(size=(n_rec, length)).astype(np.float32))
        self.current_rate, self.device = rate, "cpu"

    def current(self, idx, sel, win):
        ar = torch.arange(win)
        return self.cur[idx.local_row[sel][:, None], idx.start[sel][:, None] + ar[None, :]]


def _index(bearings, conditions):
    n = len(bearings)
    return WindowIndex(torch.arange(n) % 6, torch.zeros(n, dtype=torch.long), torch.zeros(n, dtype=torch.long),
                       np.arange(n), np.array(bearings, dtype=object), np.array(conditions, dtype=object), np.zeros(n, dtype=int))


def test_crossfit_gives_every_window_an_out_of_group_prediction():
    store = _FakeStore()
    bearings = ["A", "A", "B", "B", "C", "C"]
    idx = _index(bearings, ["c1", "c2"] * 3)
    z = torch.randn(6, 64)
    res = crossfit_bridges(store, idx, z, np.array(bearings, dtype=object), group_kind="bearing", epochs=1, batch=4)
    assert (res["provenance"] >= 0).all()
    for f in res["folds"]:
        assert not set(f["fit_bearings"]) & set(f["held_bearings"])
    assert np.all(np.isfinite(res["residual"]))


def test_crossfit_refuses_bearing_leakage():
    store = _FakeStore()
    bearings = ["A", "A", "B", "B", "C", "C"]
    idx = _index(bearings, ["c1", "c2"] * 3)
    leaky_groups = np.array([0, 1, 0, 1, 0, 1])  # splits each bearing across groups
    with pytest.raises(AssertionError):
        crossfit_bridges(store, idx, torch.randn(6, 64), leaky_groups, group_kind="bearing", epochs=1, batch=4)


def test_log_order_spectrum_matches_across_speeds_and_uses_the_whole_window():
    fe = LogOrderSpectrumFrontEnd(fs=8000, window=4000)
    x = torch.tensor(np.stack([_signal(60.0), _signal(100.0)]))
    y, f = fe(x)
    assert y.shape == (2, 897) and torch.allclose(f, torch.tensor([60.0, 100.0]), atol=0.05)
    # identical order structure -> the same peak bins and levels at both speeds (orders 1, 1.76, 7);
    # the numerical noise floor (~-82 dB) differs between speeds and is not compared
    y = y.numpy()
    for b in (28, 49, 196):
        w = slice(b - 2, b + 3)
        assert b - 2 + int(np.argmax(y[0][w])) == b and b - 2 + int(np.argmax(y[1][w])) == b
        assert abs(y[0][w].max() - y[1][w].max()) < 0.5
    # the second segment ends at the last complete cycle: 50 cycles available at 100 Hz
    o = fe.order
    assert int(torch.floor(torch.tensor(4000 * 100.0 / 8000)).item()) - o.cycles == 22
