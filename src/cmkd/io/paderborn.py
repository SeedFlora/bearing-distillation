"""Reader for the Paderborn University (KAt) Bearing DataCenter recordings.

Each ``.mat`` file holds one 4-s recording of one physical bearing under one
operating condition. The MATLAB struct has fields ``Info``, ``X`` (time
vectors, one per sampling raster) and ``Y`` (named channels). A channel's
``XIndex`` points to its time vector, so channels that share an ``XIndex``
were sampled on the same clock of the same dSPACE platform.

All channel look-ups in this module use channel *names*; array positions are
never assumed.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy.io as sio

FILE_RE = re.compile(r"^(N\d{2}_M\d{2}_F\d{2})_(K\d{3}|K[AIB]\d{2})_(\d+)\.mat$")
BEARING_RE = re.compile(r"^(K\d{3}|K[AIB]\d{2})$")

# Nominal operating conditions as encoded in the file names
# (speed rpm, load torque Nm, radial force N).
CONDITIONS: dict[str, tuple[float, float, float]] = {
    "N15_M07_F10": (1500.0, 0.7, 1000.0),
    "N09_M07_F10": (900.0, 0.7, 1000.0),
    "N15_M01_F10": (1500.0, 0.1, 1000.0),
    "N15_M07_F04": (1500.0, 0.7, 400.0),
}

HIGH_RATE_CHANNELS = ("phase_current_1", "phase_current_2", "vibration_1")


def _unwrap(x):
    while isinstance(x, np.ndarray) and x.size == 1 and x.dtype == object:
        x = x.reshape(-1)[0]
    if isinstance(x, np.ndarray) and x.size == 1:
        x = x.reshape(-1)[0]
    if isinstance(x, np.ndarray) and x.dtype.kind in "US":
        return "".join(x.reshape(-1).tolist())
    return x


def parse_filename(name: str) -> tuple[str, str, int]:
    """Return (condition_code, bearing_id, recording_index) from a file name."""
    m = FILE_RE.match(name)
    if not m:
        raise ValueError(f"unexpected Paderborn file name: {name}")
    return m.group(1), m.group(2), int(m.group(3))


@dataclass
class Channel:
    name: str
    data: np.ndarray
    raster: str
    xindex: int


@dataclass
class Recording:
    path: Path
    key: str
    condition: str
    bearing: str
    index: int
    timestamp: datetime | None
    time_limit: str
    measurement_id: int | None
    rasters: dict[int, dict] = field(default_factory=dict)
    channels: dict[str, Channel] = field(default_factory=dict)
    times: dict[int, np.ndarray] = field(default_factory=dict)
    raw_sha256: str | None = None

    def fs(self, channel: str) -> float:
        return self.rasters[self.channels[channel].xindex]["fs"]

    def time(self, channel: str) -> np.ndarray:
        """Stored time vector of the raster that ``channel`` was sampled on."""
        return self.times[self.channels[channel].xindex]


def read_recording(path: str | Path, raw_bytes: bytes | None = None) -> Recording:
    """Load one recording. ``raw_bytes`` may be supplied to avoid a second read."""
    path = Path(path)
    condition, bearing, index = parse_filename(path.name)
    buf = io.BytesIO(raw_bytes) if raw_bytes is not None else path
    raw = sio.loadmat(buf, squeeze_me=False, struct_as_record=True)
    keys = [k for k in raw if not k.startswith("__")]
    if len(keys) != 1:
        raise ValueError(f"{path.name}: expected one top-level variable, found {keys}")
    rec = raw[keys[0]][0, 0]

    timestamp = None
    time_limit = ""
    try:
        general = rec["Description"][0, 0]["General"][0, 0]
        ts = _unwrap(general[1])
        timestamp = datetime.strptime(str(ts), "%d.%m.%Y %H:%M:%S")
        recording = rec["Description"][0, 0]["Recording"][0, 0]
        time_limit = str(_unwrap(recording[1]))
    except Exception:  # metadata is optional for the signal itself
        pass
    measurement_id = None
    try:
        measurement_id = int(_unwrap(rec["Info"][0, 0]["MeasurementID"]))
    except Exception:
        pass

    rasters: dict[int, dict] = {}
    times: dict[int, np.ndarray] = {}
    for i, xch in enumerate(rec["X"].reshape(-1), start=1):
        t = np.asarray(xch["Data"], dtype=np.float64).reshape(-1)
        times[i] = t
        n = t.size
        dt = (t[-1] - t[0]) / (n - 1) if n > 1 else float("nan")
        rasters[i] = {
            "raster": str(_unwrap(xch["Raster"])),
            "n": n,
            "t0": float(t[0]),
            "t1": float(t[-1]),
            "fs": (1.0 / dt) if n > 1 and dt > 0 else float("nan"),
        }

    channels: dict[str, Channel] = {}
    for ych in rec["Y"].reshape(-1):
        name = str(_unwrap(ych["Name"]))
        channels[name] = Channel(
            name=name,
            data=np.asarray(ych["Data"], dtype=np.float64).reshape(-1),
            raster=str(_unwrap(ych["Raster"])),
            xindex=int(_unwrap(ych["XIndex"])),
        )
    return Recording(
        path=path,
        key=keys[0],
        condition=condition,
        bearing=bearing,
        index=index,
        timestamp=timestamp,
        time_limit=time_limit,
        measurement_id=measurement_id,
        rasters=rasters,
        channels=channels,
        times=times,
    )


# ----------------------------------------------------------------------------
# Official per-bearing documents shipped inside each archive
# ----------------------------------------------------------------------------

def _clean(cell) -> str:
    return re.sub(r"\s+", " ", (cell or "").replace("\n", " ")).strip()


def parse_factsheet(pdf_path: str | Path) -> dict:
    """Parse the 'Profile of rolling bearing damage' factsheet (two pages).

    Returns ``{"general": {label: value}, "n_damages": int|None,
    "damages": [{row_label: value}, ...]}`` using PyMuPDF table detection.
    """
    import fitz  # PyMuPDF

    out: dict = {"general": {}, "n_damages": None, "damages": [], "source": str(pdf_path)}
    with fitz.open(pdf_path) as doc:
        # Page 1: general table (label in column 2, value in last column)
        for tab in doc[0].find_tables().tables:
            for row in tab.extract():
                cells = [_clean(c) for c in row]
                if len(cells) >= 5 and cells[2]:
                    unit = cells[3]
                    out["general"][cells[2]] = cells[4] if not unit or unit == "-" else f"{cells[4]} [{unit}]"
        if len(doc) < 2:
            return out
        rows = []
        for tab in doc[1].find_tables().tables:
            rows.extend([[_clean(c) for c in r] for r in tab.extract()])
    damage_cols: list[int] = []
    for cells in rows:
        if "Number of damages" in cells:
            vals = [c for c in cells if c and c != "Number of damages"]
            try:
                out["n_damages"] = int(vals[0])
            except (IndexError, ValueError):
                pass
        if any(c.startswith("Damage 1") for c in cells):
            damage_cols = [i for i, c in enumerate(cells) if re.match(r"^Damage \d$", c)]
    if not damage_cols:
        return out
    n = out["n_damages"] if out["n_damages"] is not None else len(damage_cols)
    damages = [dict() for _ in range(n)]
    for cells in rows:
        label = cells[2] if len(cells) > 2 else ""
        if not label or label in ("Number of damages",) or any(c.startswith("Damage 1") for c in cells):
            continue
        for j in range(n):
            col = damage_cols[j]
            if col < len(cells):
                damages[j][label] = cells[col]
    out["damages"] = damages
    return out


def read_measuring_log(pdf_path: str | Path) -> str:
    import fitz

    with fitz.open(pdf_path) as doc:
        return "\n".join(page.get_text() for page in doc)


def derive_class3(factsheet: dict) -> tuple[str, str]:
    """Map a parsed factsheet to (class3, damage_origin).

    class3: healthy | outer | inner | combined. damage_origin: none |
    artificial | real | mixed. Raises when the factsheet is ambiguous.
    """
    damages = factsheet.get("damages") or []
    n = factsheet.get("n_damages")
    if (n in (0, None)) and not damages:
        return "healthy", "none"
    comps = {d.get("Component", "").upper() for d in damages}
    comps.discard("")
    if comps == {"OR"}:
        cls = "outer"
    elif comps == {"IR"}:
        cls = "inner"
    elif comps == {"IR", "OR"}:
        cls = "combined"
    else:
        raise ValueError(f"unrecognised damage components {comps} in {factsheet.get('source')}")
    modes = {d.get("Mode", "").lower() for d in damages}
    if modes == {"artificial"}:
        origin = "artificial"
    elif "artificial" in modes:
        origin = "mixed"
    else:
        origin = "real"
    return cls, origin
