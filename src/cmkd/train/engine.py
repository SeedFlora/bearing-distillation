"""Teacher training, target extraction, grouped bridge cross-fitting and students.

Rules enforced here:
* targets and residuals are computed in eval mode under no_grad and stored
  as plain tensors aligned with one training-window index;
* a window's bridge prediction always comes from a bridge whose fitting set
  excludes that window's group (checked by assertion and recorded);
* gates and masks never carry gradients; cross-entropy acts on every window;
* validation windows are used only for checkpoint selection, test windows
  only for the final prediction.
"""
from __future__ import annotations

import copy
import hashlib
import io
import math
import time
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F

from cmkd.data.store import SignalStore, WindowIndex, standardise
from cmkd.eval.metrics import evaluate
from cmkd.kd import gates as G
from cmkd.kd.losses import objective
from cmkd.models import Bridge, Student, Teacher
from cmkd.models.frontend import ElectricalOrderFrontEnd


@dataclass
class TrainCfg:
    epochs: int = 40
    batch: int = 256
    lr: float = 1e-3
    weight_decay: float = 1e-2
    patience: int = 8
    win_s: float = 0.5
    seed: int = 0
    early_stopping: bool = True
    amp: bool = True
    select_best: bool = True   # False: keep the last epoch; validation is then logged only


def set_seed(seed: int) -> None:
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def state_hash(model: torch.nn.Module) -> str:
    buf = io.BytesIO()
    torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, buf)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:16]


class InputPipe:
    """Builds standardised model inputs; the optional order front-end acts on raw current."""

    def __init__(self, store: SignalStore, win_s: float, frontend: ElectricalOrderFrontEnd | None = None):
        self.store, self.win = store, int(win_s * store.current_rate)
        self.frontend = frontend.to(store.device) if frontend is not None else None

    @torch.no_grad()
    def current(self, idx: WindowIndex, sel: torch.Tensor):
        x = self.store.current(idx, sel, self.win)
        fe = None
        if self.frontend is not None:
            x, fe = self.frontend(x)
        return standardise(x)[:, None, :], fe

    @torch.no_grad()
    def vibration(self, idx: WindowIndex, sel: torch.Tensor):
        return standardise(self.store.vibration(idx, sel, self.win))[:, None, :]


def _batches(n: int, batch: int, device):
    for b in range(0, n, batch):
        yield torch.arange(b, min(b + batch, n), device=device)


@torch.no_grad()
def run_forward(fn, n: int, batch: int, device, amp: bool = True) -> list[torch.Tensor]:
    outs = None
    for sel in _batches(n, batch, device):
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=(amp and device == "cuda")):
            res = fn(sel)
        res = [r.float() for r in res]
        outs = [[r] for r in res] if outs is None else [o + [r] for o, r in zip(outs, res)]
    return [torch.cat(o) for o in outs]


def _metrics(probs: torch.Tensor, idx: WindowIndex) -> dict:
    return evaluate(probs.cpu().numpy(), idx.label.cpu().numpy(), idx.recording, idx.condition, idx.bearing)


def fit(model, params, step_loss, n_train: int, val_fn, cfg: TrainCfg, device, on_epoch_start=None) -> dict:
    opt = torch.optim.AdamW(params, lr=cfg.lr, weight_decay=cfg.weight_decay)
    steps = cfg.epochs * math.ceil(n_train / cfg.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=cfg.lr, total_steps=steps, pct_start=0.1, anneal_strategy="cos")
    gen = torch.Generator(device=device).manual_seed(cfg.seed)
    best, best_state, best_epoch, bad, history = -1.0, None, -1, 0, []
    t0 = time.time()
    for epoch in range(cfg.epochs):
        if on_epoch_start is not None:
            on_epoch_start(epoch)
        model.train()
        perm = torch.randperm(n_train, generator=gen, device=device)
        tot, nb = 0.0, 0
        for b in range(0, n_train, cfg.batch):
            sel = perm[b:b + cfg.batch]
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=cfg.amp and device == "cuda"):
                loss = step_loss(sel)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            tot += float(loss.detach())
            nb += 1
        score, _ = val_fn()
        history.append({"epoch": epoch, "train_loss": tot / max(nb, 1), "val_recording_macro_f1": score,
                        "elapsed_s": round(time.time() - t0, 1)})
        if score > best:
            best, best_epoch, bad = score, epoch, 0
            if cfg.select_best:
                best_state = copy.deepcopy(model.state_dict())
        else:
            bad += 1
            if cfg.select_best and cfg.early_stopping and bad >= cfg.patience:
                break
    if cfg.select_best and best_state is not None:
        model.load_state_dict(best_state)
    return {"history": history, "best_epoch": best_epoch, "best_val_recording_macro_f1": best,
            "train_seconds": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------- teacher
def train_teacher(store: SignalStore, tr: WindowIndex, va: WindowIndex, cfg: TrainCfg, multimodal: bool = True):
    set_seed(cfg.seed)
    dev = store.device
    model = Teacher(store.current_rate, store.vibration_rate if multimodal else None).to(dev)
    pipe = InputPipe(store, cfg.win_s)

    def fwd(idx, sel):
        xc, _ = pipe.current(idx, sel)
        xv = pipe.vibration(idx, sel) if multimodal else None
        return model(xc, xv)

    def step_loss(sel):
        logits, _ = fwd(tr, sel)
        return F.cross_entropy(logits, tr.label[sel])

    def val_fn():
        model.eval()
        logits, _ = run_forward(lambda s: fwd(va, s), len(va), cfg.batch * 2, dev, amp=cfg.amp)
        m = _metrics(torch.softmax(logits, 1), va)
        return m["recording"]["macro_f1"], m

    info = fit(model, model.parameters(), step_loss, len(tr), val_fn, cfg, dev)
    model.eval()
    info["checkpoint_hash"] = state_hash(model)
    info["val_metrics"] = val_fn()[1]
    return model, fwd, info


@torch.no_grad()
def teacher_targets(model, fwd, idx: WindowIndex, batch: int, device, amp: bool = True) -> dict:
    """Eval-mode, no-grad targets for exactly the windows of ``idx`` (same order)."""
    model.eval()
    logits, z = run_forward(lambda s: fwd(idx, s), len(idx), batch, device, amp=amp)
    return {"logits": logits, "z": z, "p_true": torch.softmax(logits, 1).gather(1, idx.label[:, None]).squeeze(1)}


# ----------------------------------------------------------------------------- bridges
def crossfit_bridges(store: SignalStore, tr: WindowIndex, z_teacher: torch.Tensor, group_of_window: np.ndarray,
                     group_kind: str, epochs: int = 15, batch: int = 256, lr: float = 1e-3, seed: int = 0,
                     widths=(16, 32, 64), win_s: float = 0.5, frontend=None) -> dict:
    """Out-of-group bridge predictions for every training window.

    ``group_of_window`` assigns each training window to a cross-fitting group;
    ``group_kind`` states what the groups are ("bearing" for the proposal,
    "condition" for the condition-aware variant, "random" for the non-grouped
    control) and selects the disjointness check that must hold.
    """
    if group_kind not in ("bearing", "condition", "random"):
        raise ValueError(group_kind)
    dev = store.device
    target = F.normalize(z_teacher.float(), dim=1)
    z_b = torch.zeros_like(target)
    provenance = np.full(len(tr), -1, dtype=np.int64)
    groups = sorted(set(group_of_window.tolist()))
    pipe = InputPipe(store, win_s, frontend)
    fitted = []
    for gi, g in enumerate(groups):
        held = group_of_window == g
        fit_idx = torch.as_tensor(np.flatnonzero(~held), device=dev)
        held_idx = torch.as_tensor(np.flatnonzero(held), device=dev)
        if group_kind == "bearing":
            leak = set(tr.bearing[held]) & set(tr.bearing[~held])
            assert not leak, f"bearing(s) {leak} in both the fitting set and the held-out group"
        elif group_kind == "condition":
            leak = set(tr.condition[held]) & set(tr.condition[~held])
            assert not leak, f"condition(s) {leak} in both the fitting set and the held-out group"
        assert not (set(tr.recording[held].tolist()) & set(tr.recording[~held].tolist())) or group_kind == "random", \
            "a recording is split across fitting and held-out windows"
        set_seed(seed + 101 * gi)
        net = (Bridge(store.current_rate, widths=widths) if frontend is None
               else Bridge(None, widths=widths, stem_stride=frontend.stem_stride)).to(dev)
        opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-2)
        n = len(fit_idx)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=epochs * math.ceil(n / batch), pct_start=0.1)
        gen = torch.Generator(device=dev).manual_seed(seed + gi)
        for _ in range(epochs):
            net.train()
            perm = fit_idx[torch.randperm(n, generator=gen, device=dev)]
            for b in range(0, n, batch):
                sel = perm[b:b + batch]
                xc, _ = pipe.current(tr, sel)
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev == "cuda"):
                    pred = net(xc)
                loss = F.mse_loss(pred.float(), target[sel])
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
                sched.step()
        net.eval()
        with torch.no_grad():
            for b in range(0, len(held_idx), batch * 2):
                sel = held_idx[b:b + batch * 2]
                xc, _ = pipe.current(tr, sel)
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=dev == "cuda"):
                    z_b[sel] = net(xc).float()
        provenance[held] = gi
        fitted.append({"group": str(g), "fit_windows": int(n), "held_windows": int(held.sum()),
                       "fit_bearings": sorted(set(tr.bearing[~held])), "held_bearings": sorted(set(tr.bearing[held]))})
    assert (provenance >= 0).all(), "a training window received no out-of-group prediction"
    r = G.residuals(target.cpu().numpy(), z_b.cpu().numpy())
    return {"z_bridge": z_b, "residual": r, "provenance": provenance, "folds": fitted, "group_kind": group_kind}


# ----------------------------------------------------------------------------- students
def make_student(store: SignalStore, frontend=None):
    if frontend is None:
        return Student(store.current_rate)
    return Student(None, stem_stride=frontend.stem_stride)


def train_student(method: str, store: SignalStore, tr: WindowIndex, va: WindowIndex, cfg: TrainCfg, targets: dict | None,
                  hp: dict, frontend: ElectricalOrderFrontEnd | None = None, weights: np.ndarray | None = None):
    """method in: ce, logit_kd, feat, gate (weights given), saamask, insample_gate."""
    set_seed(cfg.seed)
    dev = store.device
    model = make_student(store, frontend).to(dev)
    pipe = InputPipe(store, cfg.win_s, frontend)
    lam = hp.get("lambda", 0.0) if method not in ("ce", "logit_kd") else 0.0
    kd_w = hp.get("kd_weight", 0.0) if method == "logit_kd" else 0.0
    temp = hp.get("temperature", 4.0)
    zt = targets["z"] if targets is not None else None
    tl = targets["logits"] if targets is not None else None
    state = {"w": torch.as_tensor(weights, dtype=torch.float32, device=dev) if weights is not None else None, "mask": None}
    warmup = max(1, int(round(0.1 * cfg.epochs)))
    diag = {}

    def build_after_warmup(epoch):
        if method not in ("saamask", "insample_gate") or epoch != warmup:
            return
        model.eval()
        with torch.no_grad():
            def f(s):
                xc, _ = pipe.current(tr, s)
                _, feat = model(xc)
                return (model.proj(feat),)
            (proj,) = run_forward(f, len(tr), cfg.batch * 2, dev, amp=cfg.amp)
        s_n, t_n = F.normalize(proj, dim=1), F.normalize(zt.float(), dim=1)
        sq = ((s_n - t_n) ** 2).cpu().numpy()
        if method == "saamask":
            state["mask"] = torch.as_tensor(G.saamask_topk_mask(sq, ratio=0.2), device=dev)
            diag["mask_built_epoch"] = epoch
        else:
            r = sq.mean(1)
            w = G.class_normalise(G.residual_gate(r, tau=hp["tau_scale"] * float(np.median(r)), eps=hp["eps"]),
                                  tr.label.cpu().numpy())
            state["w"] = torch.as_tensor(w, dtype=torch.float32, device=dev)
            diag["insample_residual_median"] = float(np.median(r))

    def step_loss(sel):
        xc, _ = pipe.current(tr, sel)
        logits, feat = model(xc)
        proj = model.proj(feat) if lam > 0 else None
        out = objective(logits.float(), tr.label[sel], proj.float() if proj is not None else None,
                        zt[sel] if lam > 0 else None, tl[sel] if kd_w > 0 else None, lam=lam,
                        weights=state["w"][sel] if (lam > 0 and state["w"] is not None) else None,
                        mask=state["mask"][sel] if (lam > 0 and state["mask"] is not None) else None,
                        kd_weight=kd_w, temperature=temp)
        return out["total"]

    def fwd_eval(idx, s):
        xc, fe = pipe.current(idx, s)
        logits, _ = model(xc)
        return (logits,) if fe is None else (logits, fe)

    def val_fn():
        model.eval()
        outs = run_forward(lambda s: fwd_eval(va, s), len(va), cfg.batch * 2, dev, amp=cfg.amp)
        m = _metrics(torch.softmax(outs[0], 1), va)
        return m["recording"]["macro_f1"], m

    info = fit(model, [p for n, p in model.named_parameters()], step_loss, len(tr), val_fn, cfg, dev,
               on_epoch_start=build_after_warmup)
    model.eval()
    info.update(diag)
    info["checkpoint_hash"] = state_hash(model)
    return model, (lambda idx, s: fwd_eval(idx, s)), info


@torch.no_grad()
def predict(model, fwd, idx: WindowIndex, batch: int, device, amp: bool = True) -> dict:
    model.eval()
    outs = run_forward(lambda s: fwd(idx, s), len(idx), batch, device, amp=amp)
    probs = torch.softmax(outs[0], 1)
    res = {"probs": probs.cpu().numpy(), "metrics": _metrics(probs, idx)}
    if len(outs) > 1:
        # a per-window vector is the supply-frequency estimate; a matrix (teacher bottleneck) is z
        res["fe" if outs[1].ndim == 1 else "z"] = outs[1].cpu().numpy()
    return res
