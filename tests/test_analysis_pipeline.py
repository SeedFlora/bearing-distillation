"""End-to-end run of scripts/analyze_main.py on a synthetic results tree (random predictions, no real data)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONDS = ["N15_M07_F10", "N09_M07_F10", "N15_M01_F10", "N15_M07_F04"]
BEARINGS = {0: ["K002", "K006", "KA03", "KA08", "KA22", "KI05", "KI18"], 1: ["K003", "KA04", "KA06", "KA09", "KI03", "KI07", "KI17"],
            2: ["K004", "KA01", "KA05", "KA15", "KA30", "KI08", "KI21"]}
CLS = lambda b: 0 if b.startswith("K0") else (1 if b.startswith("KA") else 2)


def _preds(rng, bearings, conds, rec0):
    rows, rec = [], rec0
    for b in bearings:
        for c in conds:
            for _ in range(3):
                for w in range(8):
                    rows.append((rec, CLS(b), b, c, w))
                rec += 1
    rec_a, lab, br, co, wn = map(np.array, zip(*rows))
    probs = rng.dirichlet([1, 1, 1], size=len(rows))
    return dict(probs=probs, label=lab, recording=rec_a, bearing=br.astype(str), condition=co.astype(str), window_no=wn), rec


def test_analysis_runs_on_synthetic_tree(tmp_path):
    rng = np.random.default_rng(0)
    res = tmp_path / "main"
    methods = ["ce", "feat", "gate", "saamask", "shuffled_gate", "insample_gate", "ce_ord", "gate_ord"]
    rec0 = 0
    for k, bs in BEARINGS.items():
        u = res / "A" / f"fold{k}"
        for m in methods:
            for sd in range(3):
                d = u / m / f"seed{sd}"
                d.mkdir(parents=True)
                p, _ = _preds(rng, bs, CONDS, rec0)
                np.savez_compressed(d / "predictions_test.npz", **p)
                np.savez_compressed(d / "predictions_ext.npz", **_preds(rng, ["KI04"], CONDS, 10**6)[0])
        (u / "teacher").mkdir(parents=True)
        (u / "teacher" / "metrics.json").write_text(json.dumps({"test_metrics": {"recording": {"confusion": np.eye(3, dtype=int).tolist(), "macro_f1": 1.0}}}))
        (u / "prep").mkdir()
        n = 50
        np.savez_compressed(u / "prep" / "targets.npz", z=rng.normal(size=(n, 64)))
        np.savez_compressed(u / "residuals_hz.npz", residual=rng.random(n) * 0.02, bearing=np.array(["A", "B"] * 25),
                            label=rng.integers(0, 3, n), condition=np.array(CONDS * 12 + CONDS[:2]))
        rec0 += 10**4
    ub = res / "B" / "N09_M07_F10"
    for m in ["ce", "ce_ord", "gate"]:
        for sd in range(3):
            d = ub / m / f"seed{sd}"
            d.mkdir(parents=True)
            np.savez_compressed(d / "predictions_test.npz", **_preds(rng, sum(BEARINGS.values(), []), ["N09_M07_F10"], 0)[0])
    (ub / "teacher").mkdir()
    (ub / "teacher" / "metrics.json").write_text(json.dumps({"test_metrics": {"recording": {"macro_f1": 0.5}}}))
    out = tmp_path / "analysis"
    r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/analyze_main.py"), "--boot", "200", "--results", str(res),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    a = json.loads((out / "protocol_A.json").read_text())
    assert a["n_test_bearings"] == 21 and set(a["primary_family_gate_vs"]) == set(["ce", "feat", "saamask", "shuffled_gate", "insample_gate"])
    assert all("p_holm" in v for v in a["primary_family_gate_vs"].values())
    b = json.loads((out / "protocol_B.json").read_text())
    assert "N09_M07_F10" in b and "ce_ord_vs_ce" in b["N09_M07_F10"]
    assert (out / "fig_protocol_a.pdf").exists() and (out / "fig_protocol_b.pdf").exists()
