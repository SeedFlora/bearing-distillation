"""Window- and recording-level metrics with a fixed aggregation rule."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, recall_score

N_CLASSES = 3


def aggregate_recordings(probs: np.ndarray, recording: np.ndarray, label: np.ndarray, condition: np.ndarray,
                         bearing: np.ndarray) -> pd.DataFrame:
    """Mean of window class probabilities per recording; decision = arg-max."""
    df = pd.DataFrame(probs, columns=[f"p{k}" for k in range(probs.shape[1])])
    df["recording"], df["label"], df["condition"], df["bearing"] = recording, label, condition, bearing
    g = df.groupby("recording")
    rec = g[[f"p{k}" for k in range(probs.shape[1])]].mean()
    rec["label"] = g["label"].first()
    rec["condition"] = g["condition"].first()
    rec["bearing"] = g["bearing"].first()
    rec["n_windows"] = g.size()
    rec["pred"] = rec[[f"p{k}" for k in range(probs.shape[1])]].to_numpy().argmax(1)
    return rec.reset_index()


def summarise(y: np.ndarray, pred: np.ndarray) -> dict:
    labels = list(range(N_CLASSES))
    return {
        "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "recall": [float(r) for r in recall_score(y, pred, labels=labels, average=None, zero_division=0)],
        "confusion": confusion_matrix(y, pred, labels=labels).tolist(),
        "n": int(len(y)),
    }


def evaluate(probs: np.ndarray, label: np.ndarray, recording: np.ndarray, condition: np.ndarray, bearing: np.ndarray) -> dict:
    rec = aggregate_recordings(probs, recording, label, condition, bearing)
    out = {"recording": summarise(rec["label"].to_numpy(), rec["pred"].to_numpy()),
           "window": summarise(label, probs.argmax(1))}
    out["recording_by_condition"] = {c: summarise(g["label"].to_numpy(), g["pred"].to_numpy())["macro_f1"]
                                     for c, g in rec.groupby("condition")}
    out["recording_accuracy_by_bearing"] = {b: float((g["pred"] == g["label"]).mean()) for b, g in rec.groupby("bearing")}
    return out
