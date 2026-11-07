"""Unpack the three KAIST varying-load zips into separate folders (path-traversal safe).

Usage:
  .venv/Scripts/python.exe -I scripts/extract_kaist.py --raw D:/bahrain-data/raw/kaist --out D:/bahrain-data/extracted/kaist
"""
import argparse
import sys
import zipfile
from pathlib import Path

ZIPS = {"current,temp.zip": "current_temp", "vibration.zip": "vibration", "acoustic.zip": "acoustic"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    for zname, sub in ZIPS.items():
        dst = (args.out / sub).resolve()
        dst.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.raw / zname) as zf:
            for info in zf.infolist():
                target = (dst / info.filename).resolve()
                if not str(target).startswith(str(dst)):
                    raise SystemExit(f"unsafe path in {zname}: {info.filename}")
            zf.extractall(dst)
        print(sub, sum(1 for p in dst.rglob("*") if p.is_file()), "files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
