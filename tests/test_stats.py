"""Synthetic checks for the bearing-level statistics (no experimental data)."""
import numpy as np
from sklearn.metrics import f1_score

from cmkd.eval.stats import (bearing_confusions, bootstrap_indices, holm, macro_f1_from_confusion,
                             paired_bootstrap)


def test_macro_f1_matches_sklearn():
    rng = np.random.default_rng(0)
    y, p = rng.integers(0, 3, 300), rng.integers(0, 3, 300)
    cm = np.zeros((3, 3), int)
    np.add.at(cm, (y, p), 1)
    assert np.isclose(macro_f1_from_confusion(cm), f1_score(y, p, labels=[0, 1, 2], average="macro"))


def test_bootstrap_keeps_classes_and_pairs_methods():
    bearings = [f"b{i}" for i in range(9)]
    cls = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
    idx = bootstrap_indices(cls, 2000, seed=1)
    assert idx.shape == (2000, 9)
    assert set(np.unique(cls[idx[:, :3]])) == {0} and set(np.unique(cls[idx[:, 6:]])) == {2}
    # method a perfect, method b always predicts class 0 -> a clearly better
    rec_true = np.repeat(cls, 10)
    rec_b = np.repeat(bearings, 10)
    cm_a = bearing_confusions(rec_true, rec_true, rec_b, bearings)[None]
    cm_b = bearing_confusions(rec_true, np.zeros_like(rec_true), rec_b, bearings)[None]
    r = paired_bootstrap(cm_a, cm_b, idx)
    assert r["diff"] > 0.5 and r["ci95"][0] > 0 and r["p_boot"] < 0.01
    same = paired_bootstrap(cm_a, cm_a, idx)
    assert same["diff"] == 0 and same["ci95"] == [0.0, 0.0]


def test_holm_is_monotone_and_bounded():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.5})
    assert adj["a"] == 0.04 and adj["c"] == 0.09 and adj["b"] == 0.09 and adj["d"] == 0.5
