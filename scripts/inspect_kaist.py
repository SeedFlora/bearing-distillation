"""Inspect KAIST varying-load files (vibration .mat and current/temperature .tdms).

Usage:
  .venv/Scripts/python.exe -I scripts/inspect_kaist.py <vibration.mat> <current_temp.tdms>

Prints variable names, column layout, time-stamp properties (start, end, step,
monotonicity), implied sampling rate and duration, and the TDMS metadata
(properties of file, groups and channels) needed to judge cross-sensor pairing.
"""
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio


def time_summary(t: np.ndarray, label: str) -> None:
    t = np.asarray(t, dtype=np.float64).reshape(-1)
    d = np.diff(t)
    fs = 1.0 / np.median(d) if d.size and np.median(d) > 0 else float("nan")
    print(
        f"   {label}: n={t.size} start={t[0]:.9g} end={t[-1]:.9g} "
        f"median_step={np.median(d):.9g} min_step={d.min():.3g} max_step={d.max():.3g} "
        f"monotonic={bool(np.all(d > 0))} implied_fs={fs:.6g} Hz duration={t[-1]-t[0]:.6g}"
    )


def inspect_mat(path: Path) -> None:
    raw = sio.loadmat(path)
    print(f"== {path.name} header={raw['__header__'][:80]!r}")
    for k, v in raw.items():
        if k.startswith("__"):
            continue
        print(f"   var {k!r}: type={type(v).__name__} shape={getattr(v, 'shape', None)} dtype={getattr(v, 'dtype', None)}")
        if isinstance(v, np.ndarray) and v.dtype.names:
            print(f"      fields={v.dtype.names}")
        elif isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] <= 8 and v.dtype.kind == "f":
            print(f"      first rows:\n{v[:3]}")
            time_summary(v[:, 0], "column0 (assumed Time Stamp)")
            for j in range(1, v.shape[1]):
                c = v[:, j]
                print(f"      col{j}: mean={c.mean():+.4g} std={c.std():.4g} min={c.min():+.4g} max={c.max():+.4g}")


def inspect_tdms(path: Path) -> None:
    from nptdms import TdmsFile

    with TdmsFile.open(path) as f:
        print(f"== {path.name}")
        print(f"   file properties: {dict(f.properties)}")
        for g in f.groups():
            print(f"   group {g.name!r} properties={dict(g.properties)}")
            for ch in g.channels():
                props = dict(ch.properties)
                data = ch[:]
                desc = f"n={len(data)} dtype={data.dtype}"
                if data.dtype.kind == "f":
                    desc += f" mean={np.mean(data):+.4g} std={np.std(data):.4g} min={np.min(data):+.4g} max={np.max(data):+.4g}"
                elif data.dtype.kind in "M" or "datetime" in str(data.dtype):
                    desc += f" first={data[0]} last={data[-1]}"
                print(f"      channel {ch.name!r}: {desc}")
                print(f"         props={props}")
                if ch.name.lower().startswith("time") and data.dtype.kind == "f":
                    time_summary(data, "time channel")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.suffix.lower() == ".mat":
            inspect_mat(p)
        elif p.suffix.lower() == ".tdms":
            inspect_tdms(p)
