"""Deterministic signal preprocessing shared by every model.

Paderborn recordings are nominally sampled at 64 kHz, but the stored time
vector shows that many recordings contain inserted samples with irregular
time steps. Every recording is therefore first interpolated onto a uniform
64-kHz grid *using its own time vector* (current and vibration share that
vector, so pairing is preserved), truncated to a fixed analysis span, and
then low-pass filtered and decimated with a polyphase FIR filter.

The configuration dictionary returned by :func:`preprocessing_config` is
hashed; caches and teacher targets store that hash so that stale artefacts
are detected.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
from scipy.signal import firwin, resample_poly

NOMINAL_FS = 64000.0
PREPROCESSING_VERSION = "2.0"


def uniform_resample(t: np.ndarray, x: np.ndarray, fs: float = NOMINAL_FS, max_duration: float | None = None) -> np.ndarray:
    """Linearly interpolate ``x(t)`` onto ``t0 + k / fs``.

    ``t`` must be strictly increasing. The grid covers ``[t0, t0 + span]``
    where ``span`` is the recorded span, optionally capped at ``max_duration``
    (the grid then has ``floor(span * fs)`` samples, i.e. exactly
    ``max_duration * fs`` samples for a capped recording).
    """
    t = np.asarray(t, dtype=np.float64).reshape(-1)
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if t.size != x.size:
        raise ValueError(f"time/sample length mismatch: {t.size} vs {x.size}")
    if np.any(np.diff(t) <= 0):
        raise ValueError("time vector is not strictly increasing")
    span = t[-1] - t[0]
    if max_duration is not None:
        span = min(span, max_duration)
    n = int(np.floor(span * fs + 1e-6))
    grid = t[0] + np.arange(n, dtype=np.float64) / fs
    return np.interp(grid, t, x)


def nominal_span(x: np.ndarray, duration: float = 4.0, fs: float = NOMINAL_FS) -> np.ndarray:
    """First ``duration`` seconds on the sample index at the nominal rate (decision D12).

    The stored Paderborn time vectors contain faulty time stamps: on blocks with
    irregular steps the supply frequency estimated from the sample index stays at
    100 Hz while the time vector would imply 181-316 Hz. Samples are therefore
    taken as uniformly spaced at 64 kHz and the time vector is not used.
    """
    return np.asarray(x, dtype=np.float64).reshape(-1)[: int(round(duration * fs))]


def anti_alias_fir(factor: int) -> np.ndarray:
    """Kaiser FIR with cut-off at 0.8 x the output Nyquist (guard band above it)."""
    return firwin(2 * 20 * factor + 1, 0.8 / factor, window=("kaiser", 8.0))


def decimate(x: np.ndarray, factor: int) -> np.ndarray:
    """Anti-alias FIR low-pass and integer decimation (polyphase)."""
    if factor == 1:
        return np.asarray(x, dtype=np.float64)
    return resample_poly(x, up=1, down=int(factor), window=anti_alias_fir(int(factor)), padtype="line")


def preprocessing_config(target_fs_current: float, target_fs_vibration: float, analysis_span_s: float = 4.0) -> dict:
    for fs in (target_fs_current, target_fs_vibration):
        if NOMINAL_FS % fs != 0:
            raise ValueError(f"target rate {fs} must divide {NOMINAL_FS}")
    return {
        "version": PREPROCESSING_VERSION,
        "nominal_fs": NOMINAL_FS,
        "time_base": "sample index at the nominal 64 kHz; stored time vectors not used (D12)",
        "analysis_span_s": analysis_span_s,
        "fs_current": float(target_fs_current),
        "fs_vibration": float(target_fs_vibration),
        "decimation": "resample_poly with firwin(41*down taps, cut-off 0.8 x output Nyquist, kaiser 8), padtype=line",
        "current_channel": "phase_current_1",
        "vibration_channel": "vibration_1",
    }


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def standardise_window(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Fixed per-window transform: zero mean, unit variance.

    Removes the absolute amplitude (dominated by load torque) and retains the
    relative waveform shape, including modulation depth. Applied identically
    at training and inference; no statistics are fitted on data.
    """
    x = np.asarray(x, dtype=np.float32)
    mu = x.mean(axis=-1, keepdims=True)
    sd = x.std(axis=-1, keepdims=True)
    return (x - mu) / (sd + eps)
