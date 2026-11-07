"""Window indexing over cached recordings (no window is materialised in RAM)."""
from __future__ import annotations

import numpy as np


def window_starts(valid_len: int, win: int, stride: int) -> np.ndarray:
    """Start offsets of complete windows inside ``[0, valid_len)``."""
    if win <= 0 or stride <= 0:
        raise ValueError("window and stride must be positive")
    if valid_len < win:
        return np.zeros(0, dtype=np.int64)
    return np.arange(0, valid_len - win + 1, stride, dtype=np.int64)


def build_index(rows: np.ndarray, valid_lens: np.ndarray, win: int, stride: int) -> np.ndarray:
    """Return an (M, 3) int64 array of (cache_row, start, window_number).

    Windows never cross recording boundaries. Evaluation uses ``stride == win``
    (non-overlapping windows); any training overlap is explicit in ``stride``.
    """
    out = []
    for r, L in zip(rows, valid_lens):
        s = window_starts(int(L), win, stride)
        if s.size:
            out.append(np.stack([np.full(s.size, r, dtype=np.int64), s, np.arange(s.size, dtype=np.int64)], axis=1))
    return np.concatenate(out, axis=0) if out else np.zeros((0, 3), dtype=np.int64)
