"""Training/deployment architecture diagram (vector, grayscale-safe).

Usage: .venv/Scripts/python.exe -I scripts/figures/fig_architecture.py
Writes paper/manuscript/figures/fig_architecture.pdf and a PNG preview.
The diagram is a schematic of the implemented method; it contains no data.

Layout check (fails the script): after drawing, every box, text and arrow must lie inside the canvas with a
margin, and every box label must fit inside its box. The first version clipped the student box at the right
edge (box edge at x = 1.003 of the canvas), which this check now catches.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/manuscript/figures"
plt.rcParams.update({"font.family": "serif", "font.size": 7.2, "mathtext.fontset": "dejavuserif"})
BOXES = []      # (patch, label) pairs for the containment check
PAD = 0.008     # FancyBboxPatch pad, in axes units (drawn outside the nominal box)


def box(ax, x, y, w, h, text, fill="white", dashed=False, bold=False, fs=7.2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={PAD},rounding_size=0.012", lw=0.8,
                       ec="black", fc=fill, ls=(0, (3, 2)) if dashed else "-")
    ax.add_patch(p)
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                fontweight="bold" if bold else "normal", linespacing=1.25)
    BOXES.append((p, t))
    return (x, y, w, h)


def arrow(ax, p, q, dashed=False, text=None, toff=(0, 0.012)):
    a = FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=7, lw=0.8, color="black",
                        ls=(0, (3, 2)) if dashed else "-", shrinkA=1, shrinkB=1)
    ax.add_patch(a)
    if text:
        ax.text((p[0] + q[0]) / 2 + toff[0], (p[1] + q[1]) / 2 + toff[1], text, ha="center", va="bottom", fontsize=6.3,
                style="italic")


def check_layout(fig, ax, margin_px=2.0, inner_px=2.0) -> None:
    """Raise if any artist leaves the canvas or any box label overflows its box (pixel units at save dpi)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    problems = []
    for art in list(ax.patches) + list(ax.texts) + list(ax.lines):
        bb = art.get_window_extent(r)
        if bb.x0 < margin_px or bb.y0 < margin_px or bb.x1 > W - margin_px or bb.y1 > H - margin_px:
            label = art.get_text()[:40] if hasattr(art, "get_text") else type(art).__name__
            problems.append(f"outside canvas: {label!r} extent x[{bb.x0:.1f}, {bb.x1:.1f}] y[{bb.y0:.1f}, {bb.y1:.1f}] "
                            f"canvas {W:.0f}x{H:.0f}")
    for p, t in BOXES:
        pb, tb = p.get_window_extent(r), t.get_window_extent(r)
        if tb.x0 < pb.x0 + inner_px or tb.x1 > pb.x1 - inner_px or tb.y0 < pb.y0 + inner_px or tb.y1 > pb.y1 - inner_px:
            problems.append(f"label overflows its box: {t.get_text()[:40]!r} text x[{tb.x0:.1f}, {tb.x1:.1f}] "
                            f"box x[{pb.x0:.1f}, {pb.x1:.1f}] text y[{tb.y0:.1f}, {tb.y1:.1f}] box y[{pb.y0:.1f}, {pb.y1:.1f}]")
    # collisions: no text may touch another text, a drawn line, an arrow, or a box other than its own
    from matplotlib.path import Path as MPath
    from matplotlib.transforms import Bbox

    def grown(bb, d):
        return Bbox.from_extents(bb.x0 - d, bb.y0 - d, bb.x1 + d, bb.y1 + d)

    texts = list(ax.texts)
    labels = {id(t) for _, t in BOXES}
    own_box = {id(t): p for p, t in BOXES}
    tbs = {id(t): t.get_window_extent(r) for t in texts}
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if grown(tbs[id(a)], 1.0).overlaps(tbs[id(b)]):
                problems.append(f"texts collide: {a.get_text()[:30]!r} / {b.get_text()[:30]!r}")
    for t in texts:
        tb = grown(tbs[id(t)], 1.0)
        for ln in ax.lines:
            xy = ln.get_transform().transform(ln.get_xydata())
            for k in range(len(xy) - 1):
                if MPath(xy[k:k + 2]).intersects_bbox(tb, filled=True):
                    problems.append(f"text touches a line: {t.get_text()[:40]!r}")
                    break
        for p in ax.patches:
            if p is own_box.get(id(t)):
                continue
            if id(t) in labels and isinstance(p, FancyBboxPatch):
                continue          # box labels are checked against their own box above; boxes do not overlap each other
            if tb.overlaps(p.get_window_extent(r)):
                problems.append(f"text touches a {type(p).__name__}: {t.get_text()[:40]!r}")
    if problems:
        raise SystemExit("layout check failed:\n  " + "\n  ".join(problems))
    print(f"layout check passed: {len(ax.patches)} patches, {len(ax.texts)} texts, {len(ax.lines)} lines inside the canvas; "
          f"{len(BOXES)} box labels fit")


def main() -> None:
    # 7.4-pt box text keeps every sub- and superscript at about 5.2 pt in print (mathtext scripts are 70%);
    # no maths is nested two script levels deep
    FS, FSL = 7.4, 7.0               # box text, free labels
    fig = plt.figure(figsize=(7.1, 4.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    grey = "0.90"
    # columns (nominal box x-ranges; the rounded pad adds 0.008 on each side)
    XI, WI = 0.012, 0.150            # inputs        0.012-0.162
    XT, WT = 0.196, 0.214            # teacher       0.196-0.410
    XB, WB = 0.448, 0.258            # bridges/gate  0.448-0.706
    XS, WS = 0.744, 0.236            # student       0.744-0.980
    cT, cB, cS = XT + WT / 2, XB + WB / 2, XS + WS / 2

    ax.text(0.012, 0.985, "(a) Training in the laboratory (source bearings only)", fontsize=8.5, fontweight="bold", va="top")
    # inputs
    box(ax, XI, 0.705, WI, 0.125, "Phase current\n$\\mathtt{phase\\_current\\_1}$\n0.5 s at 8 kHz", fs=FS)
    box(ax, XI, 0.52, WI, 0.125, "Vibration\n$\\mathtt{vibration\\_1}$\nsame 0.5 s at 32 kHz", fill=grey, dashed=True, fs=FS)
    # teacher
    box(ax, XT, 0.52, WT, 0.31,
        "Teacher (frozen after\ntraining): current and\nvibration branches\n(1D residual CNNs)\n$\\downarrow$ fusion\n"
        "bottleneck $z^{T}\\in\\mathbb{R}^{64}$\n$\\downarrow$ linear classifier", fill=grey, dashed=True, fs=FS)
    arrow(ax, (XI + WI + PAD, 0.7675), (XT - PAD, 0.7675))
    arrow(ax, (XI + WI + PAD, 0.5825), (XT - PAD, 0.5825), dashed=True)
    # bridges + gate
    box(ax, XB, 0.665, WB, 0.165,
        "Current-only bridges $g_1, g_2, g_3$\ncross-fitted over bearing groups\n($g_k$ never sees group $k$)\n"
        "$r_i=\\Vert\\bar z^{T}_i-\\bar z^{B}_i\\Vert^2/d$ (out of group)",
        fill=grey, dashed=True, fs=FS)
    box(ax, XB, 0.52, WB, 0.11,
        "Fixed gate, no gradient:\n$w_i=\\epsilon+(1-\\epsilon)\\,\\exp(-r_i/\\tau)$\nclass-normalised", fill=grey, dashed=True, fs=FS)
    arrow(ax, (XT + WT + PAD, 0.7675), (XB - PAD, 0.7675), dashed=True)
    ax.text((XT + WT + XB) / 2, 0.781, "$z^{T}_i$", ha="center", va="bottom", fontsize=FS)
    arrow(ax, (cB, 0.665 - PAD), (cB, 0.63 + PAD), dashed=True)
    # student
    box(ax, XS, 0.52, WS, 0.31,
        "Student (current only)\nfixed front-end: log spectrum\n(Hz axis), or order spectrum\n"
        "(orders 0–32, $f_e$ from window)\n$\\downarrow$\n"
        "depthwise-separable 1D CNN\n$\\downarrow$ feature $f$\nclassifier + projection $P$", fs=FS)
    arrow(ax, (XB + WB + PAD, 0.575), (XS - PAD, 0.575), dashed=True)
    ax.text((XB + WB + XS) / 2, 0.589, "$w_i$", ha="center", va="bottom", fontsize=FS)
    # current bus above the boxes: input -> bridges and student
    ax.plot([XI + WI / 2, XI + WI / 2, cS], [0.83 + PAD, 0.905, 0.905], color="black", lw=0.8)
    arrow(ax, (cB, 0.905), (cB, 0.83 + PAD), dashed=True)
    arrow(ax, (cS, 0.905), (cS, 0.83 + PAD))
    ax.text(0.33, 0.914, "same current window", ha="center", va="bottom", fontsize=FSL, style="italic")
    # teacher bottleneck -> student alignment target, routed below the gate
    ax.plot([cT, cT, cS], [0.52 - PAD, 0.459, 0.459], color="black", lw=0.8, ls=(0, (3, 2)))
    arrow(ax, (cS, 0.459), (cS, 0.52 - PAD), dashed=True)
    ax.text((cT + cS) / 2, 0.465, "cached target $z^{T}_i$ (eval mode, no gradient)", ha="center", va="bottom", fontsize=FSL,
            style="italic")
    ax.text(0.50, 0.398, "$\\mathcal{L}=\\mathrm{CE}(s(x_i),y_i)\\;+\\;\\lambda\\,w_i\\,\\mathrm{Huber}(\\,\\overline{Pf(x_i)},\\bar z^{T}_i)$"
            "      (cross-entropy on every window)", ha="center", fontsize=8.0)

    ax.plot([0.012, 0.988], [0.365, 0.365], color="0.4", lw=0.6)
    ax.text(0.012, 0.352, "(b) Deployment at the machine", fontsize=8.5, fontweight="bold", va="top")
    box(ax, 0.035, 0.11, 0.165, 0.15, "Phase current\nwindow, 0.5 s\nat 8 kHz", fs=7.6)
    box(ax, 0.265, 0.11, 0.26, 0.15, "Student only:\nfixed spectral front-end +\ndepthwise-separable 1D CNN\n+ classifier ($P$ removed)", fs=7.6)
    box(ax, 0.59, 0.11, 0.185, 0.15, "Recording decision:\nmean class probability\nover 8 windows (4 s)", fs=7.6)
    box(ax, 0.835, 0.11, 0.135, 0.15, "Healthy /\nouter race /\ninner race", bold=True, fs=7.6)
    arrow(ax, (0.200 + PAD, 0.185), (0.265 - PAD, 0.185))
    arrow(ax, (0.525 + PAD, 0.185), (0.59 - PAD, 0.185))
    arrow(ax, (0.775 + PAD, 0.185), (0.835 - PAD, 0.185))
    ax.text(0.5, 0.03, "Dashed, grey components (vibration, teacher, bridges, gate) are used only during training and are "
            "not deployed.", ha="center", fontsize=FSL, style="italic")
    check_layout(fig, ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_architecture.pdf")
    fig.savefig(OUT / "fig_architecture_preview.png", dpi=170)
    print("written", OUT / "fig_architecture.pdf")


if __name__ == "__main__":
    main()
