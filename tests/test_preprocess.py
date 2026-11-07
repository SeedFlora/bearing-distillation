"""Correctness checks for the deterministic preprocessing (synthetic signals only)."""
import numpy as np
import pytest

from cmkd.data.preprocess import config_hash, decimate, preprocessing_config, standardise_window, uniform_resample
from cmkd.data.windows import build_index, window_starts


def test_uniform_resample_recovers_sine_with_inserted_samples():
    fs = 64000.0
    t = np.arange(0, 0.05, 1 / fs)
    # insert irregular samples (as observed in some Paderborn recordings)
    extra = t[100:2000:7] + 0.274 / fs
    t_irr = np.sort(np.concatenate([t, extra]))
    f0 = 523.0
    x_irr = np.sin(2 * np.pi * f0 * t_irr)
    y = uniform_resample(t_irr, x_irr, fs=fs)
    grid = t_irr[0] + np.arange(y.size) / fs
    assert np.max(np.abs(y - np.sin(2 * np.pi * f0 * grid))) < 1e-3
    # naive use of the irregular sample sequence would be time-warped
    assert y.size == int(np.floor((t_irr[-1] - t_irr[0]) * fs + 1e-6))


def test_uniform_resample_caps_duration_and_rejects_bad_time():
    t = np.arange(0, 5.0, 1 / 1000.0)
    y = uniform_resample(t, np.zeros_like(t), fs=1000.0, max_duration=4.0)
    assert y.size == 4000
    with pytest.raises(ValueError):
        uniform_resample(np.array([0.0, 0.0, 1.0]), np.zeros(3), fs=10.0)


def test_decimation_suppresses_alias():
    fs = 64000.0
    t = np.arange(0, 0.5, 1 / fs)
    low = np.sin(2 * np.pi * 300 * t)
    high = np.sin(2 * np.pi * 12000 * t)  # above the 4-kHz Nyquist of 8 kHz output
    y_low = decimate(low, 8)
    y_mix = decimate(low + high, 8)
    core = slice(200, -200)
    assert np.max(np.abs(y_mix[core] - y_low[core])) < 1e-2


def test_config_hash_changes_with_rate():
    a = config_hash(preprocessing_config(8000, 16000))
    b = config_hash(preprocessing_config(16000, 16000))
    assert a != b and len(a) == 16
    with pytest.raises(ValueError):
        preprocessing_config(7000, 16000)


def test_standardise_window_removes_scale_only():
    x = np.random.default_rng(0).normal(size=(2, 4000))
    z1, z2 = standardise_window(x), standardise_window(10 * x + 3)
    assert np.allclose(z1, z2, atol=1e-4)
    assert np.allclose(z1.mean(-1), 0, atol=1e-5) and np.allclose(z1.std(-1), 1, atol=1e-3)


def test_windows_never_cross_recordings_and_eval_is_nonoverlapping():
    assert window_starts(4000, 4000, 4000).tolist() == [0]
    assert window_starts(3999, 4000, 4000).size == 0
    idx = build_index(np.array([0, 1]), np.array([32000, 31240]), win=4000, stride=4000)
    assert (idx[idx[:, 0] == 0][:, 1] + 4000 <= 32000).all()
    assert (idx[idx[:, 0] == 1][:, 1] + 4000 <= 31240).all()
    assert idx[idx[:, 0] == 0].shape[0] == 8 and idx[idx[:, 0] == 1].shape[0] == 7
    starts = idx[idx[:, 0] == 0][:, 1]
    assert np.all(np.diff(starts) == 4000)
