"""Main experiments under the frozen protocol (v1.0 = draft v0.1 + Amendments A1-A3).

Usage:
  .venv/Scripts/python.exe -I scripts/run_main.py --protocol A --folds 0 1 2 --seeds 0 1 2
  .venv/Scripts/python.exe -I scripts/run_main.py --protocol B --seeds 0 1 2

Every completed run writes results/main/<protocol>/<unit>/<method>/seed<k>/metrics.json and is
skipped on restart. Test bearings are touched only by the final predict() call of each run.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from cmkd.data.store import SignalStore
from cmkd.kd import gates as G
from cmkd.models import Bridge, count_parameters
from cmkd.models.frontend import LogOrderSpectrumFrontEnd, LogSpectrumFrontEnd
from cmkd.train.engine import (InputPipe, TrainCfg, crossfit_bridges, predict, set_seed, state_hash, teacher_targets,
                               train_student, train_teacher)

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
SPL = ROOT / "manifests/splits"
OUT = ROOT / "results/main"
CKPT = ROOT / "checkpoints" / "main"
CKPT.mkdir(parents=True, exist_ok=True)
EXT = ["KI04", "KI14"]
CONDS = ["N15_M07_F10", "N09_M07_F10", "N15_M01_F10", "N15_M07_F04"]
EPOCHS = 40
FE = {"hz": lambda: LogSpectrumFrontEnd(8000, 4000), "ord": lambda: LogOrderSpectrumFrontEnd(8000, 4000)}
GATE_GRID = [{"lambda": l, "tau_scale": t, "eps": e} for l in (0.5, 1.0) for t in (1.0, 2.0) for e in (0.05, 0.2)]
DEFAULT_HP = {"lambda": 1.0, "tau_scale": 1.0, "eps": 0.2, "temperature": 4.0, "kd_weight": 1.0}


def jdump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)), encoding="utf-8")


def save_pred(path: Path, idx, res) -> None:
    extra = {"fe": res["fe"]} if "fe" in res else {}
    np.savez_compressed(path, probs=res["probs"], label=idx.label.cpu().numpy(), recording=idx.recording,
                        bearing=idx.bearing.astype(str), condition=idx.condition.astype(str), window_no=idx.window_no, **extra)


def gate_weights(r, y, tau_scale, eps, classnorm=True):
    w = G.residual_gate(r, tau=tau_scale * float(np.median(r)), eps=eps)
    return G.class_normalise(w, y) if classnorm else w


class Unit:
    """One outer fold (Protocol A) or one held-out setting (Protocol B)."""

    def __init__(self, protocol, name, store, tr, va, te, ext, select_best, bridge_groups):
        self.protocol, self.name, self.store = protocol, name, store
        self.tr, self.va, self.te, self.ext = tr, va, te, ext
        self.select_best, self.bridge_groups = select_best, bridge_groups
        self.dir = OUT / protocol / name
        self.cfg = lambda seed: TrainCfg(epochs=EPOCHS, patience=10, seed=seed, select_best=select_best,
                                         early_stopping=select_best)

    def done(self, method, seed):
        return (self.dir / method / f"seed{seed}" / "metrics.json").exists()

    def record(self, method, seed, model, fwd, info, hp, extra=None):
        d = self.dir / method / f"seed{seed}"
        d.mkdir(parents=True, exist_ok=True)
        res_te = predict(model, fwd, self.te, 512, "cuda")
        out = {"method": method, "seed": seed, "hp": hp, "train": {k: v for k, v in info.items() if k != "history"},
               "history": info.get("history"), "test_metrics": res_te["metrics"],
               "n_parameters_deployed": count_parameters(model) - (sum(p.numel() for p in model.proj.parameters())
                                                                    if getattr(model, "proj", None) is not None else 0)}
        if self.select_best:
            out["val_metrics"] = predict(model, fwd, self.va, 512, "cuda")["metrics"]
        save_pred(d / "predictions_test.npz", self.te, res_te)
        if self.ext is not None and len(self.ext):
            res_ext = predict(model, fwd, self.ext, 512, "cuda")
            out["ext_metrics"] = res_ext["metrics"]
            save_pred(d / "predictions_ext.npz", self.ext, res_ext)
        if extra:
            out.update(extra)
        jdump(d / "metrics.json", out)
        torch.save(model.state_dict(), CKPT / f"{self.protocol}_{self.name}_{method}_s{seed}.pt")
        print(f"  [{self.protocol}/{self.name}] {method:<18} s{seed} test rec-F1 {res_te['metrics']['recording']['macro_f1']:.3f}"
              + (f" val {out['val_metrics']['recording']['macro_f1']:.3f}" if self.select_best else ""), flush=True)
        return out


def _save_targets(path: Path, tg: dict, tr) -> None:
    np.savez_compressed(path, z=tg["z"].cpu().numpy(), logits=tg["logits"].cpu().numpy(), p_true=tg["p_true"].cpu().numpy(),
                        recording=tr.recording, window_no=tr.window_no)


def _load_targets(path: Path, tr) -> dict:
    a = np.load(path)
    assert np.array_equal(a["recording"], tr.recording) and np.array_equal(a["window_no"], tr.window_no), \
        "cached targets do not match the training-window order"
    return {k: torch.as_tensor(a[k], device="cuda") for k in ("z", "logits", "p_true")}


def prepare(unit: Unit, need_controls: bool):
    """Teacher(s), targets and cross-fitted residuals for one unit (seed 0), cached so that every student
    of the unit, including students trained after a restart, uses the same teacher targets and gates."""
    s, tr = unit.store, unit.tr
    pdir = unit.dir / "prep"
    done = pdir / "prep_done.json"
    if done.exists():
        meta = json.loads(done.read_text())
        res = {"targets": _load_targets(pdir / "targets.npz", tr), "y": tr.label.cpu().numpy(), "teacher_hash": meta["teacher_hash"]}
        for rep in ("hz", "ord"):
            res[f"r_{rep}"] = np.load(unit.dir / f"residuals_{rep}.npz")["residual"]
        if need_controls:
            c = np.load(pdir / "controls.npz")
            res["r_rand"], res["r_large"] = c["r_rand"], c["r_large"]
            res["targets_cur"] = _load_targets(pdir / "targets_current_only.npz", tr)
        print(f"  [{unit.protocol}/{unit.name}] reloaded cached teacher targets {meta['teacher_hash']} and residuals", flush=True)
        return res
    pdir.mkdir(parents=True, exist_ok=True)
    res = _prepare_fresh(unit, need_controls)
    _save_targets(pdir / "targets.npz", res["targets"], tr)
    if need_controls:
        np.savez_compressed(pdir / "controls.npz", r_rand=res["r_rand"], r_large=res["r_large"])
        _save_targets(pdir / "targets_current_only.npz", res["targets_cur"], tr)
    jdump(done, {"teacher_hash": res["teacher_hash"], "controls": need_controls})
    return res


def _prepare_fresh(unit: Unit, need_controls: bool):
    s, tr = unit.store, unit.tr
    va_for_teacher = unit.va
    teacher, tfwd, tinfo = train_teacher(s, tr, va_for_teacher, unit.cfg(0), multimodal=True)
    tinfo["test_metrics"] = predict(teacher, tfwd, unit.te, 512, "cuda")["metrics"]
    tinfo["preprocessing_hashes"] = s.config_hashes
    jdump(unit.dir / "teacher" / "metrics.json", tinfo)
    torch.save(teacher.state_dict(), CKPT / f"{unit.protocol}_{unit.name}_teacher_{tinfo['checkpoint_hash']}.pt")
    print(f"  [{unit.protocol}/{unit.name}] teacher {tinfo['checkpoint_hash']} test rec-F1 "
          f"{tinfo['test_metrics']['recording']['macro_f1']:.3f}", flush=True)
    tg = teacher_targets(teacher, tfwd, tr, 512, "cuda")
    y = tr.label.cpu().numpy()
    gkey = np.array([unit.bridge_groups[b] for b in tr.bearing], dtype=object)
    res = {"targets": tg, "y": y, "teacher_hash": tinfo["checkpoint_hash"]}
    for rep in ("hz", "ord"):
        cf = crossfit_bridges(s, tr, tg["z"], gkey, group_kind="bearing", epochs=15, seed=0, frontend=FE[rep]())
        res[f"r_{rep}"] = cf["residual"]
        jdump(unit.dir / f"bridges_{rep}.json", {"folds": cf["folds"], "median_residual": float(np.median(cf["residual"])),
                                                  "teacher_checkpoint": tinfo["checkpoint_hash"]})
        np.savez_compressed(unit.dir / f"residuals_{rep}.npz", residual=cf["residual"], provenance=cf["provenance"],
                            recording=tr.recording, window_no=tr.window_no, label=y, condition=tr.condition.astype(str),
                            bearing=tr.bearing.astype(str))
    if need_controls:
        rng = np.random.default_rng(12345)
        rand_key = rng.integers(0, 3, size=len(tr)).astype(object)
        res["r_rand"] = crossfit_bridges(s, tr, tg["z"], rand_key, group_kind="random", epochs=15, seed=0, frontend=FE["hz"]())["residual"]
        res["r_large"] = crossfit_bridges(s, tr, tg["z"], gkey, group_kind="bearing", epochs=15, seed=0, widths=(32, 64, 128),
                                          frontend=FE["hz"]())["residual"]
        tc, tcfwd, tcinfo = train_teacher(s, tr, unit.va, unit.cfg(0), multimodal=False)
        jdump(unit.dir / "teacher_current_only" / "metrics.json", tcinfo)
        res["targets_cur"] = teacher_targets(tc, tcfwd, tr, 512, "cuda")
        np.savez_compressed(unit.dir / "residuals_controls.npz", r_rand=res["r_rand"], r_large=res["r_large"])
    return res


def run_one(unit, method, seed, hp, prep, rep="hz", weights=None, targets=None, base="gate"):
    model, fwd, info = train_student(base, unit.store, unit.tr, unit.va, unit.cfg(seed),
                                     targets if targets is not None else (prep["targets"] if base != "ce" else None),
                                     hp, frontend=FE[rep](), weights=weights)
    return model, fwd, info


def protocol_a(fold: dict, store: SignalStore, seeds):
    k = fold["fold"]
    s = store
    tr = s.windows(fold["train"], None, stride_s=0.25)
    va = s.windows(fold["validation"], None, stride_s=0.5)
    te = s.windows(fold["test"], None, stride_s=0.5)
    ext = s.windows(EXT, None, stride_s=0.5, label_as={b: "inner" for b in EXT})  # sensitivity reference label
    groups = {b: f"g{i}" for i, g in enumerate(fold["bridge_folds"]) for b in g}
    unit = Unit("A", f"fold{k}", s, tr, va, te, ext, True, groups)
    assert not set(fold["test"]) & (set(fold["train"]) | set(fold["validation"]))
    print(f"[A fold{k}] train {len(tr)} val {len(va)} test {len(te)} windows", flush=True)
    prep = prepare(unit, need_controls=True)
    y, cond = prep["y"], tr.condition
    p_true = prep["targets"]["p_true"].cpu().numpy()
    sel_path = unit.dir / "selection.json"
    selection = json.loads(sel_path.read_text()) if sel_path.exists() else {}

    def tune(method, grid, make):
        """Seed-0 selection on validation bearings; returns the chosen hp."""
        if method in selection:
            return selection[method]["chosen"]
        trials = []
        for hp in grid:
            model, fwd, info = make(hp, 0)
            vm = predict(model, fwd, va, 512, "cuda")["metrics"]["recording"]["macro_f1"]
            trials.append({"hp": hp, "val_recording_macro_f1": vm})
            if vm >= max(t["val_recording_macro_f1"] for t in trials):
                best_model = (model, fwd, info, hp)
        chosen = best_model[3]
        unit.record(method, 0, best_model[0], best_model[1], best_model[2], chosen, {"selection_trials": trials})
        selection[method] = {"chosen": chosen, "trials": trials}
        jdump(sel_path, selection)
        return chosen

    w_conf = G.confidence_gate(p_true, y)
    specs = {
        "ce": ([{}], lambda hp, sd: run_one(unit, "ce", sd, hp, prep, base="ce")),
        "logit_kd": ([{"temperature": t, "kd_weight": w} for t in (2.0, 4.0) for w in (0.5, 1.0)],
                     lambda hp, sd: run_one(unit, "logit_kd", sd, hp, prep, base="logit_kd")),
        "feat": ([{"lambda": l} for l in (0.5, 1.0)], lambda hp, sd: run_one(unit, "feat", sd, hp, prep, base="feat")),
        "conf_gate": ([{"lambda": l} for l in (0.5, 1.0)], lambda hp, sd: run_one(unit, "conf_gate", sd, hp, prep, weights=w_conf)),
        "saamask": ([{"lambda": l} for l in (0.5, 1.0)], lambda hp, sd: run_one(unit, "saamask", sd, hp, prep, base="saamask")),
        "gate": (GATE_GRID, lambda hp, sd: run_one(unit, "gate", sd, hp, prep,
                                                    weights=gate_weights(prep["r_hz"], y, hp["tau_scale"], hp["eps"]))),
        "ce_ord": ([{}], lambda hp, sd: run_one(unit, "ce_ord", sd, hp, prep, rep="ord", base="ce")),
        "feat_ord": ([{"lambda": l} for l in (0.5, 1.0)], lambda hp, sd: run_one(unit, "feat_ord", sd, hp, prep, rep="ord", base="feat")),
        "gate_ord": (GATE_GRID, lambda hp, sd: run_one(unit, "gate_ord", sd, hp, prep, rep="ord",
                                                        weights=gate_weights(prep["r_ord"], y, hp["tau_scale"], hp["eps"]))),
        "feat_curteacher": ([{"lambda": l} for l in (0.5, 1.0)],
                            lambda hp, sd: run_one(unit, "feat_curteacher", sd, hp, prep, base="feat", targets=prep["targets_cur"])),
    }
    chosen = {m: tune(m, grid, make) for m, (grid, make) in specs.items()}
    g = chosen["gate"]
    group_cc = np.array([f"{a}|{b}" for a, b in zip(y, cond)], dtype=object)
    matched = {
        "shuffled_gate": lambda sd: run_one(unit, "shuffled_gate", sd, g, prep, weights=G.shuffle_within_groups(
            gate_weights(prep["r_hz"], y, g["tau_scale"], g["eps"]), group_cc, seed=1000 + sd)),
        "insample_gate": lambda sd: run_one(unit, "insample_gate", sd, g, prep, base="insample_gate"),
        "ungrouped_gate": lambda sd: run_one(unit, "ungrouped_gate", sd, g, prep,
                                             weights=gate_weights(prep["r_rand"], y, g["tau_scale"], g["eps"])),
        "gate_noclassnorm": lambda sd: run_one(unit, "gate_noclassnorm", sd, g, prep,
                                               weights=gate_weights(prep["r_hz"], y, g["tau_scale"], g["eps"], classnorm=False)),
        "gate_largebridge": lambda sd: run_one(unit, "gate_largebridge", sd, g, prep,
                                               weights=gate_weights(prep["r_large"], y, g["tau_scale"], g["eps"])),
    }
    for sd in seeds:
        for m, (grid, make) in specs.items():
            if sd == 0 or unit.done(m, sd):
                continue
            model, fwd, info = make(chosen[m], sd)
            unit.record(m, sd, model, fwd, info, chosen[m])
        for m, make in matched.items():
            if unit.done(m, sd):
                continue
            model, fwd, info = make(sd)
            unit.record(m, sd, model, fwd, info, g, {"matched_to": "gate"})
        if not unit.done("bridge_head", sd):
            bridge_head(unit, prep, sd)


def bridge_head(unit: Unit, prep: dict, seed: int):
    """Auxiliary-model control: one bridge on all training windows + linear head (reported separately)."""
    s, tr, va = unit.store, unit.tr, unit.va
    dev = s.device
    fe = FE["hz"]()
    pipe = InputPipe(s, 0.5, fe)
    set_seed(seed)
    net = Bridge(None, stem_stride=fe.stem_stride).to(dev)
    target = F.normalize(prep["targets"]["z"].float(), dim=1)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-2)
    gen = torch.Generator(device=dev).manual_seed(seed)
    for _ in range(15):
        perm = torch.randperm(len(tr), generator=gen, device=dev)
        for b in range(0, len(tr), 256):
            sel = perm[b:b + 256]
            xc, _ = pipe.current(tr, sel)
            loss = F.mse_loss(net(xc), target[sel])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    net.eval()

    class Head(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.bridge, self.lin, self.proj = net, torch.nn.Linear(64, 3), None

        def forward(self, x):
            with torch.no_grad():
                z = self.bridge(x)
            return self.lin(z), z

    model = Head().to(dev)
    opt = torch.optim.AdamW(model.lin.parameters(), lr=1e-2)
    best, best_state, hist = -1, None, []
    for ep in range(20):
        model.lin.train()
        perm = torch.randperm(len(tr), generator=gen, device=dev)
        for b in range(0, len(tr), 256):
            sel = perm[b:b + 256]
            xc, _ = pipe.current(tr, sel)
            loss = F.cross_entropy(model(xc)[0], tr.label[sel])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()

        def fwd(idx, sl):
            xc, _ = pipe.current(idx, sl)
            return (model(xc)[0],)
        vm = predict(model, fwd, va, 512, "cuda")["metrics"]["recording"]["macro_f1"]
        hist.append(vm)
        if vm > best:
            best, best_state = vm, {k: v.clone() for k, v in model.lin.state_dict().items()}
    model.lin.load_state_dict(best_state)
    info = {"best_val_recording_macro_f1": best, "history": [{"epoch": i, "val_recording_macro_f1": v} for i, v in enumerate(hist)],
            "checkpoint_hash": state_hash(model)}
    unit.record("bridge_head", seed, model, fwd, info, {"bridge_widths": [16, 32, 64]},
                {"n_parameters_bridge_plus_head": count_parameters(net) + 64 * 3 + 3})


def protocol_b(target: str, store: SignalStore, prim: list[str], test_bearings: list[str], groups_list, dev_bearings, seeds):
    src = [c for c in CONDS if c != target]
    tr = store.windows(prim, src, stride_s=0.25)
    log_only = store.windows(dev_bearings, src, stride_s=0.5)   # fit curve only; never the target setting
    te = store.windows(test_bearings, [target], stride_s=0.5)
    assert set(tr.condition) == set(src) and set(te.condition) == {target} and target not in set(log_only.condition)
    groups = {b: f"g{i}" for i, g in enumerate(groups_list) for b in g}
    unit = Unit("B", target, store, tr, log_only, te, None, False, groups)
    print(f"[B {target}] train {len(tr)} test {len(te)} windows (last epoch kept)", flush=True)
    prep = prepare(unit, need_controls=False)
    y = prep["y"]
    hp = DEFAULT_HP
    methods = {
        "ce": lambda sd: run_one(unit, "ce", sd, hp, prep, base="ce"),
        "feat": lambda sd: run_one(unit, "feat", sd, hp, prep, base="feat"),
        "saamask": lambda sd: run_one(unit, "saamask", sd, hp, prep, base="saamask"),
        "gate": lambda sd: run_one(unit, "gate", sd, hp, prep, weights=gate_weights(prep["r_hz"], y, hp["tau_scale"], hp["eps"])),
        # Amendment A4 (P1): in-sample student-residual gate with the same defaults, so the primary
        # contrast "out-of-group vs in-sample residual" also exists under held-out settings
        "insample_gate": lambda sd: run_one(unit, "insample_gate", sd, hp, prep, base="insample_gate"),
        "shuffled_gate": lambda sd: run_one(unit, "shuffled_gate", sd, hp, prep, weights=G.shuffle_within_groups(
            gate_weights(prep["r_hz"], y, hp["tau_scale"], hp["eps"]),
            np.array([f"{a}|{b}" for a, b in zip(y, tr.condition)], dtype=object), seed=1000 + sd)),
        "ce_ord": lambda sd: run_one(unit, "ce_ord", sd, hp, prep, rep="ord", base="ce"),
        "feat_ord": lambda sd: run_one(unit, "feat_ord", sd, hp, prep, rep="ord", base="feat"),
        "gate_ord": lambda sd: run_one(unit, "gate_ord", sd, hp, prep, rep="ord",
                                       weights=gate_weights(prep["r_ord"], y, hp["tau_scale"], hp["eps"])),
    }
    for sd in seeds:
        for m, make in methods.items():
            if unit.done(m, sd):
                continue
            model, fwd, info = make(sd)
            unit.record(m, sd, model, fwd, info, hp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", choices=["A", "B"], required=True)
    ap.add_argument("--folds", type=int, nargs="*", default=[0, 1, 2])
    ap.add_argument("--targets", nargs="*", default=CONDS)
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2])
    args = ap.parse_args()
    pop = pd.read_csv(SPL / "paderborn_population.csv")
    prim = sorted(pop.loc[pop["in_primary"], "bearing"])
    idx = pd.read_csv(CACHE / "index.csv")
    rows = idx.loc[idx["bearing"].isin(prim + EXT), "cache_row"].to_numpy()
    store = SignalStore(CACHE, rows, 8000, 32000)
    t0 = time.time()
    if args.protocol == "A":
        A = json.loads((SPL / "protocol_A.json").read_text())
        assert A["status"] == "frozen"
        for f in A["folds"]:
            if f["fold"] in args.folds:
                protocol_a(f, store, args.seeds)
    else:
        B = json.loads((SPL / "protocol_B.json").read_text())
        dev = json.loads((SPL / "dev_pool.json").read_text())["bearings"]
        for t in B["targets"]:
            if t["target_condition"] in args.targets:
                protocol_b(t["target_condition"], store, prim, t["test_bearings"], t["bridge_folds"], dev, args.seeds)
    print(f"done in {time.time() - t0:.0f} s on {torch.cuda.get_device_name(0)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
