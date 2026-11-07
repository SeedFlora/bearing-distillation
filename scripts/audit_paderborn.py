"""Audit the complete Paderborn Bearing DataCenter download.

Usage:
  .venv/Scripts/python.exe -I scripts/audit_paderborn.py \
      --raw D:/bahrain-data/raw/paderborn --extracted D:/bahrain-data/extracted/paderborn \
      --provenance manifests/provenance/paderborn_downloads.tsv --workers 12

Outputs (all derived; raw files are never modified):
  manifests/paderborn_recordings.csv   one row per .mat recording
  manifests/paderborn_bearings.csv     one row per physical bearing
  manifests/paderborn_factsheets.json  parsed official factsheets (all rows)
  manifests/paderborn_logs/<id>.txt    full text of each measuring log
  reports/data_audit_paderborn.md      generated audit summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from cmkd.io.paderborn import (
    CONDITIONS,
    HIGH_RATE_CHANNELS,
    derive_class3,
    parse_factsheet,
    read_measuring_log,
    read_recording,
)

UNRAR = r"C:\Program Files\WinRAR\UnRAR.exe"
ROOT = Path(__file__).resolve().parents[1]


def extract_archive(rar: Path, dest_root: Path) -> Path:
    code = rar.stem
    dest = dest_root / code
    inner = dest / code
    if inner.is_dir() and len(list(inner.glob("*.mat"))) >= 80:
        return inner
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([UNRAR, "x", "-o+", "-idq", str(rar), str(dest) + "\\"], check=True)
    return inner


def rec_time_vector(path: Path, raw: bytes, xindex: int) -> np.ndarray:
    import io

    import scipy.io as sio

    m = sio.loadmat(io.BytesIO(raw), squeeze_me=False, struct_as_record=True)
    k = [k for k in m if not k.startswith("__")][0]
    return np.asarray(m[k][0, 0]["X"].reshape(-1)[xindex - 1]["Data"], dtype=np.float64).reshape(-1)


def audit_one(path_str: str) -> dict:
    path = Path(path_str)
    raw = path.read_bytes()
    row: dict = {"file": path.name, "file_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    try:
        rec = read_recording(path, raw_bytes=raw)
    except Exception as exc:  # recorded, never silently dropped
        row["parse_error"] = f"{type(exc).__name__}: {exc}"
        return row
    row.update(
        bearing=rec.bearing,
        condition=rec.condition,
        index=rec.index,
        key=rec.key,
        key_matches_name=(rec.key == path.stem),
        timestamp=rec.timestamp.isoformat() if rec.timestamp else None,
        measurement_id=rec.measurement_id,
        time_limit=rec.time_limit,
        channel_names="|".join(sorted(rec.channels)),
        parse_error="",
    )
    missing = [c for c in HIGH_RATE_CHANNELS if c not in rec.channels]
    row["missing_high_rate"] = "|".join(missing)
    if missing:
        return row
    c1, c2, v = (rec.channels[c] for c in HIGH_RATE_CHANNELS)
    row.update(
        xindex_current1=c1.xindex,
        xindex_current2=c2.xindex,
        xindex_vibration=v.xindex,
        raster_current1=c1.raster,
        raster_vibration=v.raster,
        shared_clock=(c1.xindex == c2.xindex == v.xindex),
        fs_current=rec.fs("phase_current_1"),
        fs_vibration=rec.fs("vibration_1"),
        n_current1=c1.data.size,
        n_current2=c2.data.size,
        n_vibration=v.data.size,
        n_time_vector=rec.rasters[c1.xindex]["n"],
        t0=rec.rasters[c1.xindex]["t0"],
        t1=rec.rasters[c1.xindex]["t1"],
    )
    row["duration_s"] = (row["n_current1"] - 1) / row["fs_current"] if row["fs_current"] else None
    # Time-vector regularity: nominal step is 1/64000 s; time stamps jitter
    # between ~0.985 and ~1.013 nominal steps. Steps outside [0.9, 1.1]
    # indicate inserted/irregular samples that require resampling.
    tvec = rec_time_vector(path, raw, c1.xindex)
    steps = np.diff(tvec) * 64000.0
    row["irregular_steps"] = int(((steps < 0.9) | (steps > 1.1)).sum())
    row["min_step_rel"] = float(steps.min())
    row["max_step_rel"] = float(steps.max())
    row["uniform_64k_samples"] = int(np.floor((tvec[-1] - tvec[0]) * 64000.0)) + 1
    hi = np.stack([c1.data, c2.data, v.data]) if c1.data.size == c2.data.size == v.data.size else None
    row["nonfinite_high_rate"] = int(sum(int((~np.isfinite(ch.data)).sum()) for ch in (c1, c2, v)))
    row["content_hash"] = hashlib.sha1(hi.tobytes()).hexdigest() if hi is not None else ""
    for name, ch in (("pc1", c1), ("pc2", c2), ("vib", v)):
        row[f"{name}_mean"] = float(np.mean(ch.data))
        row[f"{name}_std"] = float(np.std(ch.data))
        row[f"{name}_absmax"] = float(np.max(np.abs(ch.data)))
    for name in ("speed", "torque", "force", "temp_2_bearing_module"):
        if name in rec.channels:
            d = rec.channels[name].data
            row[f"{name}_mean"] = float(np.mean(d))
            row[f"{name}_std"] = float(np.std(d))
            row[f"{name}_n"] = int(d.size)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--extracted", type=Path, required=True)
    ap.add_argument("--provenance", type=Path, default=ROOT / "manifests/provenance/paderborn_downloads.tsv")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    prov = pd.read_csv(args.provenance, sep="\t", dtype=str).set_index("filename")
    rars = sorted(args.raw.glob("*.rar"))
    print(f"{len(rars)} archives found")

    # 1) extraction + official per-bearing documents -----------------------
    bearings, factsheets = [], {}
    logs_dir = ROOT / "manifests/paderborn_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    mat_files: list[str] = []
    for rar in rars:
        inner = extract_archive(rar, args.extracted)
        code = rar.stem
        mats = sorted(inner.glob("*.mat"))
        mat_files += [str(m) for m in mats]
        fs_pdf = inner / f"{code}.pdf"
        log_pdf = inner / f"measuring_log_{code}.pdf"
        fsheet = parse_factsheet(fs_pdf) if fs_pdf.exists() else {"general": {}, "damages": [], "n_damages": None}
        factsheets[code] = fsheet
        log_text = read_measuring_log(log_pdf) if log_pdf.exists() else ""
        (logs_dir / f"{code}.txt").write_text(log_text, encoding="utf-8")
        try:
            cls, origin = derive_class3(fsheet)
        except ValueError as exc:
            cls, origin = "UNRESOLVED", str(exc)
        g = fsheet["general"]
        dmg = fsheet["damages"]
        remarks = log_text.split("remarks:", 1)[1].split("name:", 1)[0].strip() if "remarks:" in log_text else ""
        bearings.append(
            {
                "bearing": code,
                "archive": rar.name,
                "archive_bytes": int(prov.loc[rar.name, "bytes"]) if rar.name in prov.index else None,
                "archive_sha256": prov.loc[rar.name, "sha256_local"] if rar.name in prov.index else None,
                "n_mat_files": len(mats),
                "class3": cls,
                "damage_origin": origin,
                "n_damages": fsheet.get("n_damages"),
                "components": "|".join(d.get("Component", "") for d in dmg),
                "modes": "|".join(d.get("Mode", "") for d in dmg),
                "symptoms": "|".join(d.get("Symptom", "") for d in dmg),
                "methods": "|".join(d.get("Damage method", "") for d in dmg),
                "extent_levels": "|".join(d.get("Extent of damage", "") for d in dmg),
                "combination": "|".join(d.get("Damage combination", "") for d in dmg),
                "arrangement": "|".join(d.get("Arrangement of the respective damages", "") for d in dmg),
                "length_mm": "|".join(d.get("Length", "") for d in dmg),
                "width_mm": "|".join(d.get("Width", "") for d in dmg),
                "depth_mm": "|".join(d.get("Depth", "") for d in dmg),
                "manufacturer": g.get("Manufacturer"),
                "sample_number": g.get("Sample number"),
                "installation_site": g.get("Installation site"),
                "lifetime": g.get("Lifetime"),
                "load_cycles": g.get("Number of load cycles"),
                "pitch_circle_diameter": g.get("Pitch circle diameter"),
                "log_remarks": remarks.replace("\n", " ")[:600],
                "factsheet_pdf_sha256": hashlib.sha256(fs_pdf.read_bytes()).hexdigest() if fs_pdf.exists() else None,
                "log_pdf_sha256": hashlib.sha256(log_pdf.read_bytes()).hexdigest() if log_pdf.exists() else None,
            }
        )
        print(f"  {code}: {cls:<9} {origin:<10} mats={len(mats)} manuf={g.get('Manufacturer')}")
    bdf = pd.DataFrame(bearings)
    (ROOT / "manifests/paderborn_factsheets.json").write_text(json.dumps(factsheets, indent=1, ensure_ascii=False), encoding="utf-8")

    # 2) every recording -----------------------------------------------------
    print(f"auditing {len(mat_files)} recordings with {args.workers} workers ...")
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rows = list(ex.map(audit_one, mat_files, chunksize=8))
    rdf = pd.DataFrame(rows)
    from cmkd.io.paderborn import parse_filename

    for i, r in rdf[rdf["bearing"].isna()].iterrows():
        cond, b, idx = parse_filename(r["file"])
        rdf.loc[i, ["bearing", "condition", "index"]] = [b, cond, idx]
    rdf = rdf.merge(bdf[["bearing", "class3", "damage_origin", "manufacturer", "archive", "archive_sha256"]], on="bearing", how="left")
    nominal = rdf["condition"].map(CONDITIONS)
    rdf["rpm_nominal"] = nominal.map(lambda t: t[0] if isinstance(t, tuple) else np.nan)
    rdf["torque_nominal"] = nominal.map(lambda t: t[1] if isinstance(t, tuple) else np.nan)
    rdf["force_nominal"] = nominal.map(lambda t: t[2] if isinstance(t, tuple) else np.nan)
    rdf["speed_dev_rel"] = (rdf["speed_mean"] - rdf["rpm_nominal"]) / rdf["rpm_nominal"]
    rdf["torque_dev_abs"] = rdf["torque_mean"] - rdf["torque_nominal"]
    rdf["force_dev_rel"] = (rdf["force_mean"] - rdf["force_nominal"]) / rdf["force_nominal"]
    rdf["content_hash"] = rdf["content_hash"].fillna("").astype(str)
    dup_counts = rdf.loc[rdf["content_hash"] != "", "content_hash"].value_counts()
    rdf["content_duplicates"] = rdf["content_hash"].map(dup_counts).fillna(0).astype(int)
    # Exclusion policy (recorded, never silent):
    #  * unreadable file -> excluded
    #  * identical signal content -> keep the lowest recording index, exclude later copies
    rdf = rdf.sort_values(["bearing", "condition", "index"]).reset_index(drop=True)
    rdf["exclude_reason"] = ""
    rdf.loc[rdf["parse_error"].fillna("") != "", "exclude_reason"] = "unreadable_file"
    first_of = {}
    for i, r in rdf.iterrows():
        h = r["content_hash"]
        if not h:
            continue
        if h in first_of:
            rdf.at[i, "exclude_reason"] = f"duplicate_content_of:{first_of[h]}"
        else:
            first_of[h] = r["file"]
    rdf["dataset"] = "paderborn_kat_bearing_datacenter"
    rdf["units"] = "not stored in files (see measuring log/paper)"
    rdf = rdf.sort_values(["bearing", "condition", "index"]).reset_index(drop=True)
    rdf.to_csv(ROOT / "manifests/paderborn_recordings.csv", index=False)

    # per-bearing campaign dates
    ts = pd.to_datetime(rdf["timestamp"], errors="coerce")
    span = ts.groupby(rdf["bearing"]).agg(["min", "max"]).rename(columns={"min": "first_recording", "max": "last_recording"})
    bdf = bdf.merge(span, left_on="bearing", right_index=True, how="left")
    bdf.to_csv(ROOT / "manifests/paderborn_bearings.csv", index=False)

    write_report(bdf, rdf)
    print("done")
    return 0


def _md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False) if len(df) else "_none_"


def write_report(bdf: pd.DataFrame, rdf: pd.DataFrame) -> None:
    lines = ["# Paderborn data audit (generated by scripts/audit_paderborn.py)", ""]
    lines += [f"Archives: {len(bdf)}; recordings parsed: {len(rdf)}; parse errors: {int((rdf['parse_error'].fillna('') != '').sum())}.", ""]
    lines += ["## Bearings and official factsheet labels", ""]
    cols = ["bearing", "class3", "damage_origin", "components", "modes", "methods", "extent_levels", "combination", "manufacturer", "lifetime", "n_mat_files", "first_recording", "last_recording"]
    lines += [_md(bdf[cols]), ""]
    lines += ["## Counts: class x condition (recordings) and class x bearings", ""]
    ct = pd.crosstab(rdf["class3"], rdf["condition"], margins=True)
    lines += [ct.to_markdown(), ""]
    lines += [pd.crosstab(bdf["class3"], bdf["damage_origin"], margins=True).to_markdown(), ""]
    lines += ["## Manufacturer by class (possible confound)", "", pd.crosstab(bdf["manufacturer"], bdf["class3"]).to_markdown(), ""]
    lines += ["## Recording campaigns (dates) by class (possible confound)", ""]
    camp = rdf.assign(month=pd.to_datetime(rdf["timestamp"]).dt.strftime("%Y-%m")).pivot_table(index="month", columns="class3", values="file", aggfunc="count", fill_value=0)
    lines += [camp.to_markdown(), ""]
    lines += ["## Signal contract checks", ""]
    readable = rdf[rdf["parse_error"].fillna("") == ""]
    chk = {
        "all readable recordings: current/vibration share one time vector (XIndex)": bool(readable["shared_clock"].astype(bool).all()),
        "recordings with irregular time steps (outside 0.9-1.1 nominal)": int((readable["irregular_steps"] > 0).sum()),
        "excluded recordings": dict(Counter(rdf["exclude_reason"].map(lambda s: s.split(":")[0] if s else "kept"))),
        "fs_current values (Hz)": sorted(set(np.round(rdf["fs_current"].dropna(), 3))),
        "fs_vibration values (Hz)": sorted(set(np.round(rdf["fs_vibration"].dropna(), 3))),
        "n_current1 values": dict(Counter(rdf["n_current1"].dropna().astype(int))),
        "n_vibration values": dict(Counter(rdf["n_vibration"].dropna().astype(int))),
        "non-finite samples (total)": int(rdf["nonfinite_high_rate"].fillna(0).sum()),
        "file name != internal key (readable files)": int((~readable["key_matches_name"].astype(bool)).sum()),
        "recordings with missing high-rate channel": int((rdf["missing_high_rate"].fillna("") != "").sum()),
        "time_limit values": dict(Counter(rdf["time_limit"].fillna(""))),
    }
    for k, v in chk.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines += ["## Irregular time steps by class (inserted samples; resampling required)", ""]
    irr = readable.assign(irregular=readable["irregular_steps"] > 0).pivot_table(index="class3", columns="irregular", values="file", aggfunc="count", fill_value=0)
    lines += [irr.to_markdown(), ""]
    lines += ["## Duplicate signal content (identical current+vibration arrays)", ""]
    dups = rdf[rdf["content_duplicates"] > 1][["file", "bearing", "condition", "index", "content_hash"]]
    lines += [_md(dups), ""]
    lines += ["## Recordings with non-standard length", ""]
    odd = rdf[(rdf["n_current1"] != 256001) | (rdf["n_vibration"] != 256001)][["file", "n_current1", "n_current2", "n_vibration", "duration_s"]]
    lines += [_md(odd), ""]
    lines += ["## Operating-condition verification from measured speed/torque/force", ""]
    agg = rdf.groupby("condition")[["speed_mean", "torque_mean", "force_mean", "temp_2_bearing_module_mean"]].describe().T
    lines += [agg.round(3).to_markdown(), ""]
    flag = rdf[(rdf["speed_dev_rel"].abs() > 0.03) | (rdf["torque_dev_abs"].abs() > 0.25) | (rdf["force_dev_rel"].abs() > 0.25)]
    lines += [f"Recordings outside tolerance (speed 3%, torque 0.25 Nm, force 25%): {len(flag)}", ""]
    lines += [_md(flag[["file", "speed_mean", "torque_mean", "force_mean"]].round(3).head(60)), ""]
    lines += ["## Measuring-log remarks (verbatim, per bearing)", ""]
    for _, b in bdf.iterrows():
        if b["log_remarks"]:
            lines.append(f"- **{b['bearing']}**: {b['log_remarks']}")
    (ROOT / "reports/data_audit_paderborn.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
