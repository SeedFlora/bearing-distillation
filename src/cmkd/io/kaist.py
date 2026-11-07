"""Readers for the KAIST rotating-machine dataset (varying-load record, Mendeley v6).

Vibration ``.mat`` files were exported by Simcenter Test.Lab: struct ``Signal``
with ``x_values`` (start, increment, count), ``y_values.values`` (N x 4, unit g)
and ``function_record`` (channel names, creation time). Current and
temperature ``.tdms`` files were logged by NI FlexLogger on a cDAQ chassis
with absolute waveform start times. The two modalities come from different
acquisition systems; pairing must therefore be justified from metadata, not
assumed from matching file names.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy.io as sio

NAME_RE = re.compile(r"^(\d)Nm_([A-Za-z]+)_?(\w+)?$")
CONDITION_ALIASES = {"Unbalalnce": "Unbalance"}  # spelling in some 2Nm vibration files


def parse_stem(stem: str) -> dict:
    m = NAME_RE.match(stem)
    if not m:
        raise ValueError(f"unexpected KAIST file name: {stem}")
    load, cond, sev = m.group(1), m.group(2), m.group(3)
    cond = CONDITION_ALIASES.get(cond, cond)
    return {"load_nm": int(load), "condition": cond, "severity": sev or ""}


def canonical_stem(stem: str) -> str:
    p = parse_stem(stem)
    return f"{p['load_nm']}Nm_{p['condition']}" + (f"_{p['severity']}" if p["severity"] else "")


def _s(x) -> str:
    while isinstance(x, np.ndarray) and x.dtype == object and x.size == 1:
        x = x.reshape(-1)[0]
    if isinstance(x, np.ndarray) and x.dtype.kind in "US":
        return "".join(x.reshape(-1).tolist())
    return str(x)


def read_vibration(path: str | Path, load_values: bool = True) -> dict:
    raw = sio.loadmat(path)
    sig = raw["Signal"][0, 0]
    xv = sig["x_values"][0, 0]
    inc = float(np.asarray(xv["increment"]).reshape(-1)[0])
    out = {
        "start_value": float(np.asarray(xv["start_value"]).reshape(-1)[0]),
        "increment": inc,
        "fs": 1.0 / inc,
        "n": int(np.asarray(xv["number_of_values"]).reshape(-1)[0]),
        "unit": _s(sig["y_values"][0, 0]["quantity"][0, 0]["label"]),
        "exporter": _s(sig["y_values"][0, 0]["quantity"][0, 0]["info"]),
    }
    fr = sig["function_record"][0, 0]
    names = [_s(c) for c in fr["name"].reshape(-1)]
    ctimes = [_s(c) for c in fr["creation_time"].reshape(-1)]
    out["channel_names"] = names
    out["creation_time"] = ctimes[0] if ctimes else ""
    out["creation_times_identical"] = len(set(ctimes)) == 1
    if load_values:
        out["values"] = np.asarray(sig["y_values"][0, 0]["values"], dtype=np.float64)
    return out


def read_current_temp(path: str | Path, load_values: bool = True) -> dict:
    from nptdms import TdmsFile

    f = TdmsFile.read(path) if load_values else TdmsFile.read_metadata(path)
    props = dict(f.properties)
    out = {
        "internal_name": str(props.get("name", "")),
        "date_created": str(props.get("Date Created", "")),
        "run_number": props.get("RunNumber"),
        "product": f"{props.get('ProductName', '')} {props.get('ProductVersion', '')}".strip(),
        "channels": {},
    }
    for g in f.groups():
        for ch in g.channels():
            p = dict(ch.properties)
            entry = {
                "group": g.name,
                "unit": str(p.get("unit_string", "")),
                "type": str(p.get("DAC~Channel~Type", "")),
                "device": str(p.get("DAC~Device~Name", "")),
                "chassis": str(p.get("DAC~Chassis~Name", "")),
                "wf_increment": p.get("wf_increment"),
                "wf_start_time": str(p.get("wf_start_time", "")),
            }
            if load_values:
                data = ch[:]
                entry["n"] = int(len(data))
                entry["values"] = np.asarray(data, dtype=np.float64) if len(data) else np.zeros(0)
            out["channels"][ch.name] = entry
    return out


def parse_internal_name(name: str) -> dict:
    """Parse FlexLogger log names such as 'LogFile_0Nm_Inner_1mm'."""
    m = re.match(r"^LogFile_(\d)Nm_([A-Za-z]+)(?:_(\w+))?$", name)
    if not m:
        return {"load_nm": None, "condition": None, "severity": None}
    return {"load_nm": int(m.group(1)), "condition": m.group(2), "severity": m.group(3) or ""}


def to_datetime(s: str) -> datetime | None:
    s = (s or "").replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None
