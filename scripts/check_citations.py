"""Check that every \\cite key in the manuscript exists in the verified bibliography.

Usage: .venv/Scripts/python.exe -I scripts/check_citations.py [--merge]
With --merge, writes paper/manuscript/references.bib = control entry + verified entries.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIED = ROOT / "paper/references_verified.bib"
MS = ROOT / "paper/manuscript"
CONTROL = '@IEEEtranBSTCTL{IEEEexample:BSTcontrol,\n  CTLuse_forced_etal = "no",\n  CTLuse_alt_spacing = "no"\n}\n\n'
CITE = re.compile(r"\\cite\{([^}]+)\}")
KEY = re.compile(r"^@\w+\{([^,]+),", re.M)


def main() -> int:
    bib = VERIFIED.read_text(encoding="utf-8")
    keys = set(KEY.findall(bib))
    tex = "".join(p.read_text(encoding="utf-8") for p in sorted((MS / "sections").glob("*.tex")))
    cited = {k.strip() for grp in CITE.findall(tex) for k in grp.split(",")}
    missing = sorted(cited - keys)
    print(f"verified entries: {len(keys)}; cited keys: {len(cited)}; missing: {missing}")
    if "--merge" in sys.argv:
        (MS / "references.bib").write_text(CONTROL + bib, encoding="utf-8")
        print("merged into paper/manuscript/references.bib")
    for k in sys.argv[1:]:
        if not k.startswith("--"):
            m = re.search(r"@\w+\{" + re.escape(k) + r",.*?\n\}", bib, re.S)
            print(m.group(0) if m else f"{k}: not in verified bib")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
