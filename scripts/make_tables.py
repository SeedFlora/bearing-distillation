"""Write the results tables of the manuscript from the analysis outputs (no number is typed by hand).

Inputs : results/analysis/protocol_A.json, protocol_B.json, supplement.json, results/deploy/benchmark_*.json
Outputs: paper/manuscript/tables/tab_protocol_a.tex, tab_contrasts.tex, tab_protocol_b.tex, tab_deploy.tex
Usage  : .venv/Scripts/python.exe -I scripts/make_tables.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AN, DEP, OUT = ROOT / "results/analysis", ROOT / "results/deploy", ROOT / "paper/manuscript/tables"
OUT.mkdir(parents=True, exist_ok=True)
A = json.loads((AN / "protocol_A.json").read_text(encoding="utf-8"))
B = json.loads((AN / "protocol_B.json").read_text(encoding="utf-8"))
S = json.loads((AN / "supplement.json").read_text(encoding="utf-8"))

f3 = lambda x: f"{x:.3f}"
sg = lambda x: ("$+$" if x > 0 else "$-$" if x < 0 else "") + f"{abs(x):.3f}"
ci = lambda lo, hi: f"[{lo:.3f}, {hi:.3f}]".replace("-", "$-$")
pv = lambda p: "$<$0.001" if p < 0.001 else f"{p:.3f}"

NAMES = {"ce": "CE only", "logit_kd": "Logit KD", "feat": "Feature KD, ungated", "conf_gate": "CPFD-style confidence gate",
         "saamask": "SAAMask-style adaptation", "gate": "Out-of-group residual gate", "shuffled_gate": "Shuffled residual gate",
         "insample_gate": "In-sample residual gate", "ungrouped_gate": "Gate, non-grouped cross-fitting",
         "gate_noclassnorm": "Gate, no class normalisation", "gate_largebridge": "Gate, larger bridge",
         "feat_curteacher": "Feature KD, current-only teacher", "bridge_head": "Bridge + linear head",
         "ce_ord": "CE only", "feat_ord": "Feature KD, ungated", "gate_ord": "Out-of-group residual gate"}


def protocol_a():
    rows = {r["method"]: r for r in A["table"]}
    vs = A["vs_ce"]
    t = S["A_teacher_vs"]["ce"]
    lines = [r"\begin{table*}[t]", r"\centering",
             r"\caption{Protocol A, unseen bearings: recording-level macro-F1 on the 21 test bearings pooled over three outer folds "
             r"(mean of three student seeds; seed SD; 95\% bearing bootstrap interval) and the paired difference from the CE-only student. "
             r"Window: window-level macro-F1 (mean over folds and seeds). The teacher is a reference that sees vibration and is not deployable; "
             r"its $\Delta$ is a post hoc comparison.}",
             r"\label{tab:protocolA}", r"\footnotesize\setlength{\tabcolsep}{6pt}",
             r"\begin{tabular}{lcccccc}", r"\toprule",
             r"Method & Macro-F1 & Seed SD & 95\% CI & Window & $\Delta$ vs CE & 95\% CI of $\Delta$\\", r"\midrule",
             r"\multicolumn{7}{l}{\textit{Current and vibration (reference, not deployable)}}\\",
             rf"\quad Multimodal teacher & {f3(S['A_teacher_pooled_macro_f1_check'])} & -- & "
             rf"{ci(*S['A_teacher_ci95'])} & -- & {sg(t['diff'])} & {ci(*t['ci95'])}\\"]
    groups = [("Current only, log spectrum", ["ce", "logit_kd", "feat", "conf_gate", "saamask", "gate", "shuffled_gate", "insample_gate",
                                               "ungrouped_gate", "gate_noclassnorm", "gate_largebridge", "feat_curteacher", "bridge_head"]),
              ("Current only, log order spectrum", ["ce_ord", "feat_ord", "gate_ord"])]
    for gname, ms in groups:
        lines.append(r"\multicolumn{7}{l}{\textit{" + gname + r"}}\\")
        for m in ms:
            r = rows[m]
            d = vs.get(m)
            dd = (sg(d["diff"]), ci(*d["ci95"])) if d else ("--", "--")
            lines.append(rf"\quad {NAMES[m]} & {f3(r['rec_macro_f1'])} & {f3(r['seed_sd'])} & {ci(r['ci_lo'], r['ci_hi'])} & "
                         rf"{f3(r['win_macro_f1'])} & {dd[0]} & {dd[1]}\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (OUT / "tab_protocol_a.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def contrasts():
    fam = A["primary_family_gate_vs"]
    mde = S["A_mde_gate_vs"]
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{Predeclared Holm family, Protocol A: out-of-group residual gate minus each comparator (recording-level macro-F1, "
             r"paired over 21 test bearings). MDE: difference detectable with 80\% power at $\alpha=0.05$ (post hoc).}",
             r"\label{tab:contrasts}", r"\footnotesize\setlength{\tabcolsep}{3.5pt}",
             r"\begin{tabular}{lccccc}", r"\toprule", r"Comparator & $\Delta$ & 95\% CI & $p$ & $p_{\mathrm{Holm}}$ & MDE\\", r"\midrule"]
    for k, lab in (("ce", "CE only"), ("feat", "Feature KD"), ("saamask", "SAAMask-style"), ("shuffled_gate", "Shuffled gate"),
                   ("insample_gate", "In-sample gate")):
        r = fam[k]
        lines.append(rf"{lab} & {sg(r['diff'])} & {ci(*r['ci95'])} & {pv(r['p_boot'])} & {pv(r['p_holm'])} & {f3(mde[k]['mde80_alpha05'])}\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (OUT / "tab_contrasts.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def protocol_b():
    units = [("N15_M07_F10", "Baseline"), ("N15_M01_F10", "0.1 Nm"), ("N15_M07_F04", "400 N"), ("N09_M07_F10", "900 rpm")]
    tab = {u: {r["method"]: r for r in B[u]["table"]} for u, _ in units}
    lines = [r"\begin{table*}[t]", r"\centering",
             r"\caption{Protocol B, unseen operating setting: recording-level macro-F1 on the 21 non-development bearings under the "
             r"held-out setting (mean of three seeds), and paired differences with 95\% bearing bootstrap intervals (unadjusted). "
             r"Codes as in Table~\ref{tab:conditions}.}",
             r"\label{tab:protocolB}", r"\footnotesize\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.15}",
             r"\begin{tabular}{l" + "c" * len(units) + "}", r"\toprule",
             "Held-out setting & " + " & ".join(f"{lab} ({u.replace('_', chr(92) + '_')})" for u, lab in units) + r"\\", r"\midrule",
             "Multimodal teacher & " + " & ".join(f3(B["teacher"][u]) for u, _ in units) + r"\\", r"\midrule",
             r"\multicolumn{" + str(len(units) + 1) + r"}{l}{\textit{Current, log spectrum}}\\"]
    for m in ("ce", "feat", "saamask", "gate", "shuffled_gate", "insample_gate"):
        lines.append(f"\\quad {NAMES[m]} & " + " & ".join(f3(tab[u][m]["rec_macro_f1"]) for u, _ in units) + r"\\")
    lines.append(r"\multicolumn{" + str(len(units) + 1) + r"}{l}{\textit{Current, log order spectrum}}\\")
    for m in ("ce_ord", "feat_ord", "gate_ord"):
        lines.append(f"\\quad {NAMES[m]} & " + " & ".join(f3(tab[u][m]["rec_macro_f1"]) for u, _ in units) + r"\\")
    lines.append(r"\midrule")
    for lab, get in (("Gate $-$ CE", lambda u: B[u]["vs_ce"]["gate"]), ("Gate $-$ in-sample", lambda u: B[u]["gate_vs"]["insample_gate"]),
                     ("Order CE $-$ CE", lambda u: B[u]["vs_ce"]["ce_ord"])):
        lines.append(lab + " & " + " & ".join(sg(get(u)["diff"]) + " " + ci(*get(u)["ci95"]) for u, _ in units) + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (OUT / "tab_protocol_b.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def deploy():
    hz = json.loads((DEP / "benchmark_A_fold0_gate_s0.json").read_text(encoding="utf-8"))
    od = json.loads((DEP / "benchmark_A_fold0_ce_ord_s0.json").read_text(encoding="utf-8"))
    lines = [r"\begin{table}[t]", r"\centering",
             r"\caption{Exported student on the laptop CPU (Intel Core \mbox{i7-12700H}, ONNX Runtime, batch 1, median of 2,000 runs after "
             r"100 warm-up runs): file size, inference latency, front-end time, fold-0 test macro-F1 and agreement of recording "
             r"decisions with the GPU evaluation pipeline of the same checkpoint (log spectrum: residual-gate student; order spectrum: "
             r"cross-entropy-only student; both fold 0, seed 0). Acquisition of the 0.5-s window is excluded.}",
             r"\label{tab:deploy}", r"\footnotesize\setlength{\tabcolsep}{2.4pt}",
             r"\begin{tabular}{llcccccc}", r"\toprule",
             r"Front-end & Model & kB & 1 thr. & 4 thr. & Front-end & F1 & Agree\\",
             r" & & & (ms) & (ms) & (ms) & & (\%)\\", r"\midrule"]
    ref = {"hz": hz["evaluation_pipeline"]["fold0_test_recording_macro_f1"], "ord": od["evaluation_pipeline"]["fold0_test_recording_macro_f1"]}
    for name, d, key in (("Log spec.", hz, "hz"), ("Order", od, "ord")):
        pre = d["preprocessing_cpu_threads1"]["median_ms"]
        lines.append(rf"{name} & GPU ref. & -- & -- & -- & -- & {f3(ref[key])} & --\\")
        for prec in ("fp32", "int8"):
            r = d[prec]
            lines.append(rf" & {prec.upper()} & {d['file_bytes'][prec] / 1000:.1f} & {r['cpu_threads1']['median_ms']:.3f} & "
                         rf"{r['cpu_threads4']['median_ms']:.3f} & {pre:.3f} & {f3(r['fold0_test_recording_macro_f1'])} & "
                         rf"{100 * r['recording_decision_agreement_vs_evaluation']:.1f}\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (OUT / "tab_deploy.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    protocol_a()
    contrasts()
    protocol_b()
    deploy()
    print("tables written to", OUT)
