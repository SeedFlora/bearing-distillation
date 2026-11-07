"""Development-only comparison of student input representations (protocol Amendment A2).

Usage: .venv/Scripts/python.exe -I scripts/diag_representation.py
CE-only student, 30 epochs, seed 0, identical splits; only the fixed per-window
representation changes. Pilot-S/A select; Pilot-B is descriptive.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from cmkd.data.store import SignalStore
from cmkd.models.frontend import ElectricalOrderFrontEnd, LogOrderSpectrumFrontEnd, LogSpectrumFrontEnd
from cmkd.train.engine import TrainCfg, predict, train_student

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
REPS = {"wave_hz": lambda: None, "wave_order": lambda: ElectricalOrderFrontEnd(8000, 4000),
        "logspec_hz": lambda: LogSpectrumFrontEnd(8000, 4000), "logspec_order": lambda: LogOrderSpectrumFrontEnd(8000, 4000)}


def main() -> int:
    dev = json.loads((ROOT / "manifests/splits/dev_pool.json").read_text())["bearings"]
    idx = pd.read_csv(CACHE / "index.csv")
    s8 = SignalStore(CACHE, idx.loc[idx["bearing"].isin(dev), "cache_row"].to_numpy(), 8000, None)
    rec_no = dict(zip(s8.meta["cache_row"], s8.meta["index"].astype(int)))
    tr_all, ev_all = s8.windows(dev, None, stride_s=0.25), s8.windows(dev, None, stride_s=0.5)
    splits = {
        "S": (tr_all.subset(np.array([rec_no[r] <= 14 for r in tr_all.recording])),
              ev_all.subset(np.array([rec_no[r] >= 15 for r in ev_all.recording])), True),
        "A_P1": (s8.windows(["K001", "KA07", "KI16"], None, stride_s=0.25), s8.windows(["K005", "KA16", "KI01"], None), True),
        "A_P2": (s8.windows(["K005", "KA16", "KI01"], None, stride_s=0.25), s8.windows(["K001", "KA07", "KI16"], None), True),
        "B_N09": (s8.windows(dev, ["N15_M07_F10", "N15_M01_F10", "N15_M07_F04"], stride_s=0.25),
                  s8.windows(dev, ["N09_M07_F10"]), False),
    }
    rows = []
    for split, (tr, ev, select_best) in splits.items():
        for rep, make in REPS.items():
            cfg = TrainCfg(epochs=30, patience=10, seed=0, select_best=select_best, early_stopping=select_best)
            model, fwd, info = train_student("ce", s8, tr, ev, cfg, None, {}, frontend=make())
            res = predict(model, fwd, ev, 512, "cuda")
            h = info["history"]
            rows.append({"split": split, "representation": rep, "eval_rec_macro_f1": round(res["metrics"]["recording"]["macro_f1"], 3),
                         "eval_win_macro_f1": round(res["metrics"]["window"]["macro_f1"], 3),
                         "train_loss_last": round(h[-1]["train_loss"], 3), "epochs": len(h)})
            print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results/pilot/diag_representation.csv", index=False)
    sel = df[df["split"].isin(["S", "A_P1", "A_P2"])].copy()
    sel["type"] = np.where(sel["representation"].str.startswith("wave"), "waveform", "logspec")
    choice = sel.groupby("type")["eval_rec_macro_f1"].mean().round(3).to_dict()
    winner = "logspec" if choice.get("logspec", 0) - choice.get("waveform", 0) > 0.02 else "waveform"
    out = {"selection_means": choice, "chosen_type": winner}
    (ROOT / "results/pilot/diag_representation_choice.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out), flush=True)
    print(df.pivot(index="representation", columns="split", values="eval_rec_macro_f1").to_string(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
