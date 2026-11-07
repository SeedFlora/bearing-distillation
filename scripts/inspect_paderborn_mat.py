"""Print the internal structure of one or more Paderborn .mat recordings.

Usage: py -3.13 -I scripts/inspect_paderborn_mat.py <file.mat> [<file.mat> ...]

Read-only inspection used during the data audit. It prints every channel's
name, unit, raster (sample interval group), length and basic statistics so
that channel identities are checked by name, not by array position.
"""
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio


def _s(x):
    """Unwrap MATLAB cell/char arrays into a Python string."""
    while isinstance(x, np.ndarray) and x.size == 1:
        x = x.reshape(-1)[0]
    if isinstance(x, np.ndarray) and x.dtype.kind in "US":
        return "".join(x.reshape(-1).tolist())
    return str(x)


def describe(path: Path) -> None:
    raw = sio.loadmat(path, squeeze_me=False, struct_as_record=True)
    keys = [k for k in raw if not k.startswith("__")]
    print(f"== {path.name}  header={raw.get('__header__', b'')[:60]!r}")
    print(f"   top-level keys: {keys}")
    rec = raw[keys[0]][0, 0]
    print(f"   struct fields: {rec.dtype.names}")
    for field in rec.dtype.names:
        arr = rec[field]
        if field in ("X", "Y"):
            entries = arr.reshape(-1)
            print(f"   [{field}] {len(entries)} channels; subfields={entries.dtype.names}")
            for ch in entries:
                name = _s(ch["Name"])
                unit = _s(ch["Unit"]) if "Unit" in ch.dtype.names else "?"
                raster = _s(ch["Raster"]) if "Raster" in ch.dtype.names else "?"
                data = np.asarray(ch["Data"]).reshape(-1)
                print(
                    f"      {name:<24} unit={unit:<6} raster={raster:<10} n={data.size:>7} "
                    f"dtype={data.dtype} mean={data.mean():+.4g} std={data.std():.4g} "
                    f"min={data.min():+.4g} max={data.max():+.4g}"
                )
        else:
            flat = arr.reshape(-1)
            print(f"   [{field}] shape={arr.shape} dtype={arr.dtype} sample={str(flat[:1])[:300]}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        describe(Path(p))
