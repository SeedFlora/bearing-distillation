"""Protocol B figure: Hz-axis versus electrical-order students per held-out setting (presentation only).

Reads results/analysis/protocol_B.json (written by scripts/analyze_main.py); draws no new statistic.
Colour encodes the front-end (validated categorical pair #2a78d6 / #eb6834, light mode), marker shape
encodes the training method, so identity never depends on colour alone (prints in greyscale).
Usage: .venv/Scripts/python.exe -I scripts/figures/fig_conditions.py
Output: paper/manuscript/figures/fig_conditions.pdf
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
B = json.loads((ROOT / "results/analysis/protocol_B.json").read_text(encoding="utf-8"))
UNITS = [("N15_M07_F10", "baseline"), ("N15_M01_F10", "0.1 Nm"), ("N15_M07_F04", "400 N"), ("N09_M07_F10", "900 rpm")]
HZ, ORD, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#8a8984"
SERIES = [("ce", HZ, "o", -0.30), ("feat", HZ, "s", -0.19), ("gate", HZ, "^", -0.08),
          ("ce_ord", ORD, "o", 0.08), ("feat_ord", ORD, "s", 0.19), ("gate_ord", ORD, "^", 0.30)]

plt.rcParams.update({"font.family": "serif", "font.size": 7, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
                     "ytick.major.width": 0.6, "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
fig, ax = plt.subplots(figsize=(3.45, 2.55))
for j, (u, _) in enumerate(UNITS):
    rows = {r["method"]: r for r in B[u]["table"]}
    for m, col, mk, dx in SERIES:
        r = rows[m]
        ax.errorbar(j + dx, r["rec_macro_f1"], yerr=[[r["rec_macro_f1"] - r["ci_lo"]], [r["ci_hi"] - r["rec_macro_f1"]]],
                    fmt=mk, color=col, ms=4.2, mew=0.6, mec="white", lw=0.9, capsize=0, zorder=3)
    ax.hlines(B["teacher"][u], j - 0.42, j + 0.42, color=MUTED, lw=1.0, ls=(0, (3, 1.5)), zorder=2)
ax.set_xticks(range(len(UNITS)), [f"{lab}\n{u}" for u, lab in UNITS], fontsize=6.3)
ax.set_xlim(-0.55, len(UNITS) - 0.45)
ax.set_ylim(0, 1.04)
ax.set_ylabel("Recording-level macro-F1", color=INK)
ax.grid(axis="y", color="#e4e3df", lw=0.5, zorder=0)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
handles = [Line2D([], [], color=HZ, marker="o", ls="", ms=4.5, label="Log spectrum (Hz axis)"),
           Line2D([], [], color=ORD, marker="o", ls="", ms=4.5, label="Log order spectrum"),
           Line2D([], [], color=MUTED, ls=(0, (3, 1.5)), lw=1.0, label="Multimodal teacher"),
           Line2D([], [], color=INK, marker="o", ls="", ms=4, label="CE only"),
           Line2D([], [], color=INK, marker="s", ls="", ms=4, label="Feature KD"),
           Line2D([], [], color=INK, marker="^", ls="", ms=4, label="Residual gate")]
ax.legend(handles=handles, ncol=2, fontsize=6.2, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0),
          handletextpad=0.4, columnspacing=1.0, borderaxespad=0.2)
fig.tight_layout(pad=0.3)
# layout check (fails the script): legend, axis labels and tick labels must lie inside the canvas, and the
# legend must not overlap the plotting area
fig.canvas.draw()
_r = fig.canvas.get_renderer()
_W, _H = fig.bbox.width, fig.bbox.height
_items = [("legend", ax.get_legend()), ("y label", ax.yaxis.label)] + \
         [(f"tick {t.get_text()!r}", t) for t in ax.get_xticklabels() + ax.get_yticklabels() if t.get_text()]
_bad = []
for _name, _a in _items:
    _bb = _a.get_window_extent(_r)
    if _bb.x0 < 1 or _bb.y0 < 1 or _bb.x1 > _W - 1 or _bb.y1 > _H - 1:
        _bad.append(f"{_name} outside canvas: x[{_bb.x0:.1f}, {_bb.x1:.1f}] y[{_bb.y0:.1f}, {_bb.y1:.1f}] canvas {_W:.0f}x{_H:.0f}")
if ax.get_legend().get_window_extent(_r).overlaps(ax.get_window_extent(_r).shrunk(0.999, 0.999)):
    _bad.append("legend overlaps the plotting area")
_xt = [t.get_window_extent(_r) for t in ax.get_xticklabels() if t.get_text()]
_bad += [f"x tick labels {i} and {i + 1} collide" for i in range(len(_xt) - 1) if _xt[i].x1 + 2 > _xt[i + 1].x0]
if _bad:
    raise SystemExit("layout check failed:\n  " + "\n  ".join(_bad))
print(f"layout check passed: legend, y label and {len(_items) - 2} tick labels inside the canvas; no tick-label collision")
out = ROOT / "paper/manuscript/figures/fig_conditions.pdf"
fig.savefig(out)
fig.savefig(out.with_suffix(".png"), dpi=220)
print("written", out)
