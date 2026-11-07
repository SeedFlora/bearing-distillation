"""Frequency-content inspection on DEVELOPMENT bearings only.

Usage:
  .venv/Scripts/python.exe -I scripts/dev_spectra.py --extracted D:/bahrain-data/extracted/paderborn

Reads manifests/splits/dev_pool.json and refuses to touch any other bearing.
Each recording is uniformly resampled on its own time vector (64 kHz), then a
Welch PSD (Hann, 16384-sample segments, 50% overlap) is computed for
phase_current_1 and vibration_1. Outputs:
  reports/figures/dev_spectra.pdf / .png   class-mean log-PSD per channel
  reports/dev_spectra_summary.json         cumulative power below candidate cut-offs
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import welch

from cmkd.data.preprocess import NOMINAL_FS, nominal_span
from cmkd.io.paderborn import read_recording

ROOT = Path(__file__).resolve().parents[1]
NPERSEG = 16384


def psd_one(args: tuple[str, str]) -> dict:
    path, cls = args
    rec = read_recording(path)
    out = {"file": Path(path).name, "class3": cls, "condition": rec.condition, "bearing": rec.bearing}
    for ch in ("phase_current_1", "vibration_1"):
        x = nominal_span(rec.channels[ch].data, 4.0, NOMINAL_FS)
        f, p = welch(x - x.mean(), fs=NOMINAL_FS, window="hann", nperseg=NPERSEG, noverlap=NPERSEG // 2)
        out[ch] = p.astype(np.float64)
        out["f"] = f
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extracted", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    dev = json.loads((ROOT / "manifests/splits/dev_pool.json").read_text())["bearings"]
    rec = pd.read_csv(ROOT / "manifests/paderborn_recordings.csv")
    rec = rec[rec["bearing"].isin(dev) & (rec["exclude_reason"].fillna("") == "")]
    assert set(rec["bearing"]) <= set(dev), "non-development bearing reached the spectral inspection"
    jobs = [(str(args.extracted / r.bearing / r.bearing / r.file), r.class3) for r in rec.itertuples()]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        res = list(ex.map(psd_one, jobs, chunksize=4))
    f = res[0]["f"]
    summary = {"bearings": dev, "n_recordings": len(res), "nperseg": NPERSEG, "channels": {}}

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.6), sharex=True)
    styles = {"healthy": ("k", "-"), "outer": ("0.45", "--"), "inner": ("0.65", ":")}
    for ax, ch in zip(axes, ("phase_current_1", "vibration_1")):
        P = np.stack([r[ch] for r in res])
        cls = np.array([r["class3"] for r in res])
        summary["channels"][ch] = {}
        for c in ("healthy", "outer", "inner"):
            m = 10 * np.log10(P[cls == c].mean(axis=0) + 1e-20)
            col, ls = styles[c]
            ax.plot(f / 1000, m, color=col, ls=ls, lw=1.0, label=f"{c} (n={int((cls == c).sum())})")
        tot = P.sum(axis=1, keepdims=True)
        cum = np.cumsum(P, axis=1) / tot
        for cut in (2000, 4000, 8000, 16000):
            j = np.searchsorted(f, cut)
            frac = cum[:, j]
            summary["channels"][ch][f"power_fraction_below_{cut}Hz"] = {
                "median": float(np.median(frac)), "min": float(frac.min())}
        for cut in (4, 8):
            ax.axvline(cut, color="0.3", lw=0.6, ls="-.")
        ax.set_ylabel(f"{ch}\nPSD (dB re unit$^2$/Hz)")
        ax.grid(alpha=0.3, lw=0.4)
        ax.legend(fontsize=7, loc="upper right")
    axes[-1].set_xlabel("Frequency (kHz)")
    axes[-1].set_xlim(0, 32)
    fig.suptitle("Development bearings only: class-mean Welch PSD (vertical lines: 4 and 8 kHz)", fontsize=9)
    fig.tight_layout()
    (ROOT / "reports/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(ROOT / "reports/figures/dev_spectra.pdf")
    fig.savefig(ROOT / "reports/figures/dev_spectra.png", dpi=110)
    # low-frequency zoom for current sidebands
    fig2, ax2 = plt.subplots(1, 1, figsize=(7.0, 3.0))
    P = np.stack([r["phase_current_1"] for r in res])
    cls = np.array([r["class3"] for r in res])
    cond = np.array([r["condition"] for r in res])
    for c in ("healthy", "outer", "inner"):
        sel = (cls == c) & (cond == "N15_M07_F10")
        ax2.plot(f, 10 * np.log10(P[sel].mean(axis=0) + 1e-20), color=styles[c][0], ls=styles[c][1], lw=0.9, label=c)
    ax2.set_xlim(0, 1000)
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("phase_current_1 PSD (dB)")
    ax2.set_title("Development bearings, N15_M07_F10: current spectrum 0-1 kHz", fontsize=9)
    ax2.legend(fontsize=7)
    ax2.grid(alpha=0.3, lw=0.4)
    fig2.tight_layout()
    fig2.savefig(ROOT / "reports/figures/dev_current_lowfreq.png", dpi=110)
    peak = f[np.argmax(P.mean(axis=0)[f > 10]) + np.sum(f <= 10)]
    summary["current_dominant_peak_hz"] = float(peak)
    (ROOT / "reports/dev_spectra_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
