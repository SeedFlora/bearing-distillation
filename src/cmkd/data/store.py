"""GPU-resident signal store and window indexing over the memmap cache.

Only the cache rows named by the caller are loaded. Windows are gathered on the
device by index; nothing is materialised per window in host RAM.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

CLASSES = ("healthy", "outer", "inner")
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}


@dataclass
class WindowIndex:
    local_row: torch.Tensor      # (N,) row inside the store
    start: torch.Tensor          # (N,) start sample at the current rate
    label: torch.Tensor          # (N,)
    recording: np.ndarray        # (N,) cache_row of the recording (global id)
    bearing: np.ndarray          # (N,)
    condition: np.ndarray        # (N,)
    window_no: np.ndarray        # (N,)

    def __len__(self):
        return int(self.local_row.shape[0])

    def subset(self, mask: np.ndarray) -> "WindowIndex":
        m = torch.as_tensor(mask, device=self.local_row.device)
        return WindowIndex(self.local_row[m], self.start[m], self.label[m], self.recording[mask], self.bearing[mask],
                           self.condition[mask], self.window_no[mask])


class SignalStore:
    def __init__(self, cache_dir: str | Path, cache_rows: np.ndarray, current_rate: int, vibration_rate: int | None,
                 device: str = "cuda"):
        cache_dir = Path(cache_dir)
        self.index = pd.read_csv(cache_dir / "index.csv")
        cache_rows = np.asarray(sorted(set(int(r) for r in cache_rows)), dtype=np.int64)
        self.meta = self.index.set_index("cache_row").loc[cache_rows].reset_index()
        self.local_of = {int(r): i for i, r in enumerate(cache_rows)}
        self.current_rate, self.vibration_rate, self.device = current_rate, vibration_rate, device
        cur = np.load(cache_dir / f"current_{current_rate}.npy", mmap_mode="r")
        self.cur = torch.from_numpy(np.ascontiguousarray(cur[cache_rows])).to(device)
        self.valid_cur = self.meta[f"valid_current_{current_rate}"].to_numpy()
        self.vib = None
        if vibration_rate:
            vib = np.load(cache_dir / f"vibration_{vibration_rate}.npy", mmap_mode="r")
            self.vib = torch.from_numpy(np.ascontiguousarray(vib[cache_rows])).to(device)
            self.ratio = vibration_rate // current_rate
        self.config_hashes = {}
        for name in [f"current_{current_rate}"] + ([f"vibration_{vibration_rate}"] if vibration_rate else []):
            import json
            self.config_hashes[name] = json.loads((cache_dir / f"{name}.meta.json").read_text())["config_hash"]

    def windows(self, bearings, conditions=None, win_s: float = 0.5, stride_s: float = 0.5,
                label_as: dict | None = None) -> WindowIndex:
        """``label_as`` maps bearing -> reference class for external analyses (e.g. KI04/KI14 -> inner)."""
        win, stride = int(win_s * self.current_rate), int(stride_s * self.current_rate)
        label_as = label_as or {}
        m = self.meta[self.meta["bearing"].isin(list(bearings))]
        if conditions is not None:
            m = m[m["condition"].isin(list(conditions))]
        lr, st, lab, rec, br, cond, wn = [], [], [], [], [], [], []
        for r in m.itertuples():
            valid = int(getattr(r, f"valid_current_{self.current_rate}"))
            if self.vib is not None:   # a window must be complete in both modalities (no zero padding)
                valid = min(valid, int(getattr(r, f"valid_vibration_{self.vibration_rate}")) // self.ratio)
            starts = np.arange(0, valid - win + 1, stride) if valid >= win else np.zeros(0, dtype=int)
            k = len(starts)
            lr.append(np.full(k, self.local_of[int(r.cache_row)]))
            st.append(starts)
            lab.append(np.full(k, CLASS_TO_ID[label_as.get(r.bearing, r.class3)]))
            rec.append(np.full(k, int(r.cache_row)))
            br.append(np.full(k, r.bearing, dtype=object))
            cond.append(np.full(k, r.condition, dtype=object))
            wn.append(np.arange(k))
        cat = lambda a, dt=None: np.concatenate(a) if a else np.zeros(0, dtype=dt)
        dev = self.device
        return WindowIndex(torch.as_tensor(cat(lr, np.int64), device=dev), torch.as_tensor(cat(st, np.int64), device=dev),
                           torch.as_tensor(cat(lab, np.int64), device=dev), cat(rec, np.int64), cat(br, object),
                           cat(cond, object), cat(wn, np.int64))

    def current(self, idx: WindowIndex, sel: torch.Tensor, win: int) -> torch.Tensor:
        ar = torch.arange(win, device=self.device)
        return self.cur[idx.local_row[sel][:, None], idx.start[sel][:, None] + ar[None, :]]

    def vibration(self, idx: WindowIndex, sel: torch.Tensor, win: int) -> torch.Tensor:
        wv = win * self.ratio
        ar = torch.arange(wv, device=self.device)
        return self.vib[idx.local_row[sel][:, None], (idx.start[sel] * self.ratio)[:, None] + ar[None, :]]


def standardise(x: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """Fixed per-window transform (zero mean, unit variance) along the last axis."""
    return (x - x.mean(-1, keepdim=True)) / (x.std(-1, keepdim=True) + eps)
