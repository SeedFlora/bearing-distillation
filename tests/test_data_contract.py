"""Consequential checks on the frozen splits and the signal cache.

These tests read the real manifests. Tests that need the raw/cached data on
D: are skipped automatically when those files are absent.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "manifests" / "splits"
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
EXTRACTED = Path("D:/bahrain-data/extracted/paderborn")


def _load(name):
    return json.loads((SPLITS / name).read_text(encoding="utf-8"))


def test_split_files_unchanged_since_freeze():
    for line in (SPLITS / "SPLITS_SHA256.txt").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((SPLITS / name).read_bytes()).hexdigest() == digest, f"{name} changed after freezing"


def test_protocol_a_bearing_partitions_are_disjoint_and_complete():
    A = _load("protocol_A.json")
    dev = set(_load("dev_pool.json")["bearings"])
    pop = pd.read_csv(SPLITS / "paderborn_population.csv")
    primary = set(pop.loc[pop["in_primary"], "bearing"])
    cls = dict(zip(pop["bearing"], pop["class3"]))
    tested = []
    for f in A["folds"]:
        te, va, tr = set(f["test"]), set(f["validation"]), set(f["train"])
        assert not (te & va) and not (te & tr) and not (va & tr)
        assert te | va | tr == primary
        assert not (te & dev), "development bearing used as test evidence"
        for part in (te, va, tr):
            assert {cls[b] for b in part} == {"healthy", "inner", "outer"}
        assert set().union(*map(set, f["bridge_folds"])) == tr
        tested += list(te)
    assert len(tested) == len(set(tested)) == len(primary - dev)


def test_protocol_b_target_condition_absent_from_fitting():
    B = _load("protocol_B.json")
    dev = set(_load("dev_pool.json")["bearings"])
    for t in B["targets"]:
        assert t["target_condition"] not in t["source_conditions"]
        assert not (set(t["test_bearings"]) & dev)
        for iv in t["inner_validation"]:
            assert t["target_condition"] not in iv["fit_conditions"]
            assert iv["held_out_source_condition"] not in iv["fit_conditions"]


def test_excluded_bearings_are_not_in_primary_population():
    pop = pd.read_csv(SPLITS / "paderborn_population.csv")
    for b in ("KB23", "KB24", "KB27", "KI04", "KI14"):
        assert not bool(pop.loc[pop["bearing"] == b, "in_primary"].iloc[0])
    assert pop.loc[pop["bearing"] == "KA08", "class3"].iloc[0] == "outer"


@pytest.mark.skipif(not (CACHE / "index.csv").exists(), reason="cache not built")
def test_cache_index_matches_retained_recordings():
    idx = pd.read_csv(CACHE / "index.csv")
    rec = pd.read_csv(ROOT / "manifests/paderborn_recordings.csv")
    kept = set(rec.loc[rec["exclude_reason"].fillna("") == "", "file"])
    assert set(idx["file"]) == kept
    assert idx["cache_row"].tolist() == list(range(len(idx)))
    excluded = set(rec.loc[rec["exclude_reason"].fillna("") != "", "file"])
    assert not (set(idx["file"]) & excluded)


@pytest.mark.skipif(not (CACHE / "index.csv").exists() or not EXTRACTED.exists(), reason="cache or raw data absent")
def test_cached_current_and_vibration_cover_the_same_interval():
    """Cache = decimated first 4.0 s on the sample index (D12); both channels share one index."""
    from cmkd.data.preprocess import NOMINAL_FS, decimate, nominal_span
    from cmkd.io.paderborn import read_recording

    idx = pd.read_csv(CACHE / "index.csv")
    cur = np.load(CACHE / "current_8000.npy", mmap_mode="r")
    vib = np.load(CACHE / "vibration_32000.npy", mmap_mode="r")
    rng = np.random.default_rng(0)
    for row in rng.choice(len(idx), size=3, replace=False):
        r = idx.iloc[row]
        rec = read_recording(EXTRACTED / r.bearing / r.bearing / r.file)
        assert rec.channels["phase_current_1"].xindex == rec.channels["vibration_1"].xindex
        c = decimate(nominal_span(rec.channels["phase_current_1"].data, 4.0, NOMINAL_FS), 8)
        v = decimate(nominal_span(rec.channels["vibration_1"].data, 4.0, NOMINAL_FS), 2)
        n_c, n_v = int(r.valid_current_8000), int(r.valid_vibration_32000)
        assert np.allclose(cur[row, :n_c], c[:n_c].astype(np.float32), atol=1e-5)
        assert np.allclose(vib[row, :n_v], v[:n_v].astype(np.float32), atol=1e-5)


@pytest.mark.skipif(not (CACHE / "index.csv").exists(), reason="cache not built")
def test_cache_keeps_a_constant_supply_frequency_in_recordings_with_faulty_time_stamps():
    """Regression for D12: in a recording whose time vector has thousands of compressed steps,
    every 0.5-s cached window must show the same ~100 Hz fundamental (no time warping)."""
    idx = pd.read_csv(CACHE / "index.csv")
    row = int(idx.index[idx["file"] == "N15_M07_F10_KA03_2.mat"][0])
    cur = np.load(CACHE / "current_8000.npy", mmap_mode="r")
    f = np.fft.rfftfreq(1 << 18, 1 / 8000)
    band = (f > 40) & (f < 400)
    peaks = []
    for s in range(0, 32000 - 4000 + 1, 4000):
        w = np.asarray(cur[row, s:s + 4000], dtype=float)
        m = np.abs(np.fft.rfft((w - w.mean()) * np.hanning(4000), 1 << 18))
        peaks.append(f[band][np.argmax(m[band])])
    assert max(peaks) - min(peaks) < 1.0 and abs(np.mean(peaks) - 100.0) < 1.0, peaks


@pytest.mark.skipif(not (CACHE / "index.csv").exists(), reason="cache not built")
def test_every_paired_window_is_complete_in_both_modalities():
    from cmkd.data.store import SignalStore

    idx = pd.read_csv(CACHE / "index.csv")
    short = (idx["valid_vibration_32000"] < 128000) | (idx["valid_current_8000"] < 32000)
    rows = idx.loc[short & idx["class3"].isin(["healthy", "outer", "inner"]), "cache_row"].to_numpy()
    assert len(rows) > 0
    s = SignalStore(CACHE, rows, 8000, 32000, device="cpu")
    w = s.windows(sorted(set(s.meta["bearing"])), None, stride_s=0.5)
    vlen = dict(zip(s.meta["cache_row"], s.meta["valid_vibration_32000"]))
    clen = dict(zip(s.meta["cache_row"], s.meta["valid_current_8000"]))
    for rec, st in zip(w.recording, w.start.numpy()):
        assert st + 4000 <= clen[rec] and 4 * (st + 4000) <= vlen[rec]
