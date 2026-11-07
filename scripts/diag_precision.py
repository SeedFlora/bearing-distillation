"""Diagnostic (development bearings only): does bfloat16 autocast erase weak current components?

Usage: .venv/Scripts/python.exe -I scripts/diag_precision.py
Same Pilot-S split (same six development bearings, recordings 1-14 fit, 15-20 evaluate),
same CE-only student and budget; only the training precision changes. A second check
measures how much of a window's spectrum survives a bfloat16 round trip.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from cmkd.data.store import SignalStore, standardise
from cmkd.train.engine import TrainCfg, predict, train_student

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")


def main() -> int:
    dev = json.loads((ROOT / "manifests/splits/dev_pool.json").read_text())["bearings"]
    idx = pd.read_csv(CACHE / "index.csv")
    rows = idx.loc[idx["bearing"].isin(dev), "cache_row"].to_numpy()
    s8 = SignalStore(CACHE, rows, 8000, None)
    rec_no = dict(zip(s8.meta["cache_row"], s8.meta["index"].astype(int)))
    tr_all, ev_all = s8.windows(dev, None, stride_s=0.25), s8.windows(dev, None, stride_s=0.5)
    tr = tr_all.subset(np.array([rec_no[r] <= 14 for r in tr_all.recording]))
    ev = ev_all.subset(np.array([rec_no[r] >= 15 for r in ev_all.recording]))

    # 1) spectrum survival under bf16 quantisation of a standardised window
    x = standardise(s8.current(tr, torch.arange(64, device="cuda"), 4000))
    xq = x.to(torch.bfloat16).float()
    err = xq - x
    snr_db = 10 * torch.log10((x ** 2).mean() / (err ** 2).mean()).item()
    X = torch.fft.rfft(x * torch.hann_window(4000, device="cuda"), dim=-1).abs().mean(0)
    f = np.fft.rfftfreq(4000, 1 / 8000)
    k0 = int(np.argmax(X.cpu().numpy()[5:400]) + 5)
    rel = 20 * np.log10(np.median(X.cpu().numpy()[(f > 150) & (f < 2000)]) / X.cpu().numpy()[k0])
    out = {"bf16_quantisation_snr_db": round(snr_db, 1), "fundamental_hz": float(f[k0]),
           "median_150_2000Hz_level_rel_fundamental_db": round(float(rel), 1)}
    print(json.dumps(out), flush=True)

    # 2) identical student, budget and split; only precision differs
    for amp in (True, False):
        cfg = TrainCfg(epochs=30, patience=10, seed=0, amp=amp)
        model, fwd, info = train_student("ce", s8, tr, ev, cfg, None, {})
        res = predict(model, fwd, ev, 512, "cuda")
        h = info["history"]
        out[f"amp_bf16={amp}"] = {"train_loss_first": round(h[0]["train_loss"], 3), "train_loss_last": round(h[-1]["train_loss"], 3),
                                  "epochs_run": len(h), "eval_recording_macro_f1": round(res["metrics"]["recording"]["macro_f1"], 3),
                                  "eval_window_macro_f1": round(res["metrics"]["window"]["macro_f1"], 3)}
        print(f"amp_bf16={amp}: {out[f'amp_bf16={amp}']}", flush=True)
    (ROOT / "results/pilot/diag_precision.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
