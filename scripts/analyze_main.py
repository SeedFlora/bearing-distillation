"""Analyse recorded predictions of the main experiments (written before any result was inspected).

Usage: .venv/Scripts/python.exe -I scripts/analyze_main.py [--boot 10000]
Inputs : results/main/{A,B}/.../predictions_*.npz, metrics.json, residuals, prep targets
Outputs: results/analysis/*.json|*.md|*.tex and paper/manuscript/figures/fig_*.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from cmkd.eval.stats import bearing_confusions, bootstrap_ci, bootstrap_indices, holm, macro_f1_from_confusion, paired_bootstrap

ROOT = Path(__file__).resolve().parents[1]
RES, OUT, FIG = ROOT / "results/main", ROOT / "results/analysis", ROOT / "paper/manuscript/figures"
SKIP = {"teacher", "teacher_current_only", "prep"}
FAMILY = ["ce", "feat", "saamask", "shuffled_gate", "insample_gate"]
LABEL = {"ce": "CE only", "logit_kd": "Logit KD", "feat": "Feature KD (ungated)", "conf_gate": "CPFD-style confidence gate",
         "saamask": "SAAMask-style adaptation", "shuffled_gate": "Shuffled gate", "insample_gate": "In-sample residual gate",
         "gate": "Out-of-group gate (proposed)", "ungrouped_gate": "Non-grouped cross-fitting gate",
         "gate_noclassnorm": "Gate, no class normalisation", "gate_largebridge": "Gate, larger bridge",
         "feat_curteacher": "Feature KD, current-only teacher", "ce_ord": "CE only, order variant",
         "feat_ord": "Feature KD, order variant", "gate_ord": "Gate, order variant", "bridge_head": "Bridge + head (control)"}


def recordings(npz: Path) -> pd.DataFrame:
    a = np.load(npz, allow_pickle=False)
    df = pd.DataFrame(a["probs"], columns=["p0", "p1", "p2"])
    df["recording"], df["label"], df["bearing"], df["condition"] = a["recording"], a["label"], a["bearing"], a["condition"]
    g = df.groupby("recording")
    rec = g[["p0", "p1", "p2"]].mean()
    rec["label"], rec["bearing"], rec["condition"] = g["label"].first(), g["bearing"].first(), g["condition"].first()
    rec["pred"] = rec[["p0", "p1", "p2"]].to_numpy().argmax(1)
    return rec.reset_index()


def window_macro_f1(npz: Path) -> float:
    a = np.load(npz)
    cm = np.zeros((3, 3), int)
    np.add.at(cm, (a["label"], a["probs"].argmax(1)), 1)
    return float(macro_f1_from_confusion(cm))


def collect(protocol: str, unit_filter=None) -> dict:
    """{method: {seed: DataFrame of recordings pooled over units}} plus window F1."""
    out, win = {}, {}
    for unit in sorted((RES / protocol).glob("*")):
        if not unit.is_dir() or (unit_filter and not unit_filter(unit.name)):
            continue
        for mdir in sorted(p for p in unit.iterdir() if p.is_dir() and p.name not in SKIP):
            for sdir in sorted(mdir.glob("seed*")):
                f = sdir / "predictions_test.npz"
                if f.exists():
                    sd = int(sdir.name[4:])
                    out.setdefault(mdir.name, {}).setdefault(sd, []).append(recordings(f).assign(unit=unit.name))
                    win.setdefault(mdir.name, {}).setdefault(sd, []).append(window_macro_f1(f))
    return {m: {s: pd.concat(v, ignore_index=True) for s, v in d.items()} for m, d in out.items()}, win


def complete_seeds(data: dict, n_units: int) -> dict:
    return {m: {s: df for s, df in d.items() if df["unit"].nunique() == n_units} for m, d in data.items()}


def confusions(data: dict, bearings: list[str]) -> dict:
    return {m: np.stack([bearing_confusions(df["label"].to_numpy(), df["pred"].to_numpy(), df["bearing"].to_numpy(), bearings)
                         for s, df in sorted(d.items())]) for m, d in data.items() if d}


def summarise(cms: dict, idx: np.ndarray, win: dict) -> pd.DataFrame:
    rows = []
    for m, cm in cms.items():
        per_seed = macro_f1_from_confusion(cm.sum(axis=1))
        lo, hi = bootstrap_ci(cm, idx)
        rows.append({"method": m, "label": LABEL.get(m, m), "n_seeds": cm.shape[0], "rec_macro_f1": per_seed.mean(),
                     "seed_sd": per_seed.std(ddof=1) if cm.shape[0] > 1 else np.nan, "ci_lo": lo, "ci_hi": hi,
                     "win_macro_f1": float(np.mean(win.get(m, {}).get(0, [np.nan])))})
    return pd.DataFrame(rows).sort_values("rec_macro_f1", ascending=False)


def protocol_a(n_boot: int) -> dict:
    data, win = collect("A")
    data = complete_seeds(data, 3)
    if "ce" not in data or not data["ce"]:
        return {"status": "incomplete"}
    any_df = next(iter(data["ce"].values()))
    bdf = any_df.groupby("bearing")["label"].first()
    bearings, bclass = list(bdf.index), bdf.to_numpy()
    idx = bootstrap_indices(bclass, n_boot)
    cms = confusions(data, bearings)
    win_mean = {m: {0: [np.mean([np.mean(v) for v in d.values()])]} for m, d in win.items()}
    table = summarise(cms, idx, win_mean)
    res = {"n_test_bearings": len(bearings), "bearings": bearings, "table": table.to_dict(orient="records")}
    fam = {}
    if "gate" in cms:
        for other in FAMILY:
            if other in cms and cms[other].shape[0] == cms["gate"].shape[0]:
                fam[other] = paired_bootstrap(cms["gate"], cms[other], idx)
        adj = holm({k: v["p_boot"] for k, v in fam.items()})
        for k in fam:
            fam[k]["p_holm"] = adj[k]
    res["primary_family_gate_vs"] = fam
    res["vs_ce"] = {m: paired_bootstrap(cms[m], cms["ce"], idx) for m in cms if m != "ce" and cms[m].shape[0] == cms["ce"].shape[0]}
    if "ce_ord" in cms:
        res["order_vs_time"] = {"ce_ord_vs_ce": paired_bootstrap(cms["ce_ord"], cms["ce"], idx)}
        if "gate_ord" in cms and "gate" in cms:
            res["order_vs_time"]["gate_ord_vs_gate"] = paired_bootstrap(cms["gate_ord"], cms["gate"], idx)
    # per-condition (pooled over folds, seed-mean)
    pc = {}
    for m, d in data.items():
        pc[m] = {}
        for c in sorted(any_df["condition"].unique()):
            vals = []
            for df in d.values():
                g = df[df["condition"] == c]
                cm = bearing_confusions(g["label"].to_numpy(), g["pred"].to_numpy(), g["bearing"].to_numpy(), bearings).sum(0)
                vals.append(macro_f1_from_confusion(cm))
            pc[m][c] = float(np.mean(vals))
    res["per_condition"] = pc
    res["teacher"] = teacher_reference("A")
    res["campaign"] = campaign_diagnostic(data)
    res["ki04_ki14"] = external_shares()
    res["residuals"] = residual_diagnostics()
    return res


def teacher_reference(protocol: str) -> dict:
    cms = []
    for f in sorted((RES / protocol).glob("*/teacher/metrics.json")):
        cms.append(np.array(json.loads(f.read_text())["test_metrics"]["recording"]["confusion"]))
    if not cms:
        return {}
    tot = np.sum(cms, axis=0)
    return {"pooled_recording_macro_f1": float(macro_f1_from_confusion(tot)), "confusion": tot.tolist(), "units": len(cms)}


def campaign_diagnostic(data: dict) -> dict:
    pop = pd.read_csv(ROOT / "manifests/splits/paderborn_population.csv").set_index("bearing")
    out = {}
    for m in ("ce", "feat", "saamask", "gate", "ce_ord", "gate_ord"):
        if m not in data:
            continue
        df = pd.concat(data[m].values())
        df["year"] = df["bearing"].map(pop["campaign_year"])
        df["err"] = df["pred"] != df["label"]
        g = {}
        for name, sub in (("healthy_2015", df[df["label"] == 0]), ("damaged_2015", df[(df["label"] > 0) & (df["year"] == 2015)]),
                          ("damaged_2014", df[(df["label"] > 0) & (df["year"] == 2014)])):
            g[name] = {"error_rate": float(sub["err"].mean()) if len(sub) else None,
                       "predicted_healthy_share": float((sub["pred"] == 0).mean()) if len(sub) else None,
                       "bearings": int(sub["bearing"].nunique()), "recordings_x_seeds": int(len(sub))}
        out[m] = g
    return out


def external_shares() -> dict:
    out = {}
    for f in sorted((RES / "A").glob("*/*/seed*/predictions_ext.npz")):
        m = f.parent.parent.name
        rec = recordings(f)
        out.setdefault(m, []).append(rec["pred"].to_numpy())
    return {m: {k: float(np.mean(np.concatenate(v) == i)) for i, k in enumerate(("healthy", "outer", "inner"))} for m, v in out.items()}


def residual_diagnostics() -> dict:
    out = {}
    for unit in sorted((RES / "A").glob("fold*")):
        f, t = unit / "residuals_hz.npz", unit / "prep" / "targets.npz"
        if not (f.exists() and t.exists()):
            continue
        a, z = np.load(f), np.load(t)["z"].astype(float)
        zn = z / np.linalg.norm(z, axis=1, keepdims=True)
        r = a["residual"]
        sse = r.sum() * zn.shape[1]
        sst = ((zn - zn.mean(0)) ** 2).sum()
        df = pd.DataFrame({"r": r, "b": a["bearing"], "c": a["label"], "cond": a["condition"]})
        between = df.groupby("b")["r"].transform("mean").var(ddof=0)
        out[unit.name] = {"out_of_group_r2": float(1 - sse / sst), "between_bearing_share": float(between / df["r"].var(ddof=0)),
                          "median_by_class": df.groupby("c")["r"].median().round(4).to_dict(),
                          "median_by_condition": df.groupby("cond")["r"].median().round(4).to_dict()}
    return out


def protocol_b(n_boot: int) -> dict:
    res = {}
    for unit in sorted((RES / "B").glob("*")):
        if not unit.is_dir():
            continue
        data, win = collect("B", unit_filter=lambda n, u=unit.name: n == u)
        data = complete_seeds(data, 1)
        if "ce" not in data or not data["ce"]:
            continue
        any_df = next(iter(data["ce"].values()))
        bdf = any_df.groupby("bearing")["label"].first()
        bearings, bclass = list(bdf.index), bdf.to_numpy()
        idx = bootstrap_indices(bclass, n_boot)
        cms = confusions(data, bearings)
        win_mean = {m: {0: [np.mean([np.mean(v) for v in d.values()])]} for m, d in win.items()}
        r = {"table": summarise(cms, idx, win_mean).to_dict(orient="records"),
             "vs_ce": {m: paired_bootstrap(cms[m], cms["ce"], idx) for m in cms if m != "ce"}}
        if "gate" in cms:
            r["gate_vs"] = {o: paired_bootstrap(cms["gate"], cms[o], idx) for o in ("feat", "saamask", "shuffled_gate", "insample_gate")
                            if o in cms}
        if "ce_ord" in cms:
            r["ce_ord_vs_ce"] = paired_bootstrap(cms["ce_ord"], cms["ce"], idx)
        res[unit.name] = r
    res["teacher"] = {u.name: json.loads((u / "teacher" / "metrics.json").read_text())["test_metrics"]["recording"]["macro_f1"]
                      for u in sorted((RES / "B").glob("*")) if (u / "teacher" / "metrics.json").exists()}
    return res


def figures(a: dict, b: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "serif", "font.size": 7.5})
    if a.get("table"):
        t = pd.DataFrame(a["table"]).sort_values("rec_macro_f1")
        fig, ax = plt.subplots(figsize=(3.45, 0.22 * len(t) + 0.8))
        y = np.arange(len(t))
        ax.errorbar(t["rec_macro_f1"], y, xerr=[t["rec_macro_f1"] - t["ci_lo"], t["ci_hi"] - t["rec_macro_f1"]], fmt="o",
                    color="black", ms=3, lw=0.8, capsize=1.5)
        ce = t.loc[t["method"] == "ce", "rec_macro_f1"]
        if len(ce):
            ax.axvline(float(ce.iloc[0]), color="0.5", ls="--", lw=0.7)
        if a.get("teacher"):
            ax.axvline(a["teacher"]["pooled_recording_macro_f1"], color="0.3", ls=":", lw=0.8)
        ax.set_yticks(y, t["label"])
        ax.set_xlabel("Recording-level macro-F1 (21 unseen bearings; 95% bearing bootstrap)")
        ax.grid(axis="x", alpha=0.3, lw=0.4)
        fig.tight_layout()
        fig.savefig(FIG / "fig_protocol_a.pdf")
        plt.close(fig)
    units = [u for u in b if u != "teacher"]
    if units:
        methods = ["ce", "ce_ord", "feat", "gate", "gate_ord", "insample_gate", "saamask"]
        fig, ax = plt.subplots(figsize=(3.45, 2.3))
        for j, u in enumerate(units):
            t = pd.DataFrame(b[u]["table"]).set_index("method")
            for k, m in enumerate([m for m in methods if m in t.index]):
                x = j + (k - 3) * 0.1
                ax.errorbar(x, t.loc[m, "rec_macro_f1"], yerr=[[t.loc[m, "rec_macro_f1"] - t.loc[m, "ci_lo"]],
                                                                [t.loc[m, "ci_hi"] - t.loc[m, "rec_macro_f1"]]],
                            fmt="os^dvP*"[k], color=str(0.15 * k), ms=3, lw=0.6, capsize=1, label=LABEL[m] if j == 0 else None)
        ax.set_xticks(range(len(units)), units, fontsize=6.5)
        ax.set_ylabel("Recording-level macro-F1")
        ax.legend(fontsize=5.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False)
        ax.grid(axis="y", alpha=0.3, lw=0.4)
        fig.tight_layout()
        fig.savefig(FIG / "fig_protocol_b.pdf")
        plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--results", type=Path, default=None, help="override results/main (tests)")
    ap.add_argument("--out", type=Path, default=None, help="override results/analysis and figure folder (tests)")
    args = ap.parse_args()
    global RES, OUT, FIG
    if args.results:
        RES = args.results
    if args.out:
        OUT = FIG = args.out
    OUT.mkdir(parents=True, exist_ok=True)
    a = protocol_a(args.boot)
    b = protocol_b(args.boot)
    (OUT / "protocol_A.json").write_text(json.dumps(a, indent=1, default=float), encoding="utf-8")
    (OUT / "protocol_B.json").write_text(json.dumps(b, indent=1, default=float), encoding="utf-8")
    if a.get("table"):
        pd.DataFrame(a["table"]).round(3).to_markdown(OUT / "protocol_A_table.md", index=False)
    figures(a, b)
    print("analysis written to", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
