"""The manuscript figures must pass their own layout checks (nothing outside the canvas, no label overflow,
no text collision). Added after Figure 1 was found clipped at its right edge (2026-11-07)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["scripts/figures/fig_architecture.py", "scripts/figures/fig_conditions.py"])
def test_figure_passes_layout_check(script):
    if script.endswith("fig_conditions.py") and not (ROOT / "results/analysis/protocol_B.json").exists():
        pytest.skip("Protocol B analysis output not available")
    r = subprocess.run([sys.executable, "-I", str(ROOT / script)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "layout check passed" in r.stdout
