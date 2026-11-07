"""Page-budget check for the IJCDS manuscript (10-15 pages including references; template output).

Usage: .venv/Scripts/python.exe -I scripts/check_pages.py paper/manuscript/main.pdf
Exit code 3 when the PDF exceeds 15 pages.
"""
import re
import sys

import fitz

MAX_PAGES, MIN_PAGES = 15, 10
HEADS = ["INTRODUCTION", "RELATED WORK", "DATA AND EXPERIMENTAL PROTOCOL", "METHOD", "RESULTS", "DISCUSSION",
         "CONCLUSION", "Author Contributions", "Data Availability", "AI Use Statement", "References"]


def main() -> int:
    d = fitz.open(sys.argv[1])
    n = len(d)
    print(f"pages {n} (IJCDS budget {MIN_PAGES}-{MAX_PAGES} incl. references) size_pt {d[0].rect.width:.0f}x{d[0].rect.height:.0f}")
    where = {}
    for i, page in enumerate(d):
        text = page.get_text()
        for h in HEADS:
            if h not in where and re.search(r"(^|\n)\s*(\d+\.\s*)?" + re.escape(h) + r"\s*(\n|$)", text, re.I):
                where[h] = i + 1
    print("section start pages: " + ", ".join(f"{h} p{p}" for h, p in where.items()))
    if n > MAX_PAGES:
        print(f"OVER PAGE BUDGET: {n} > {MAX_PAGES} pages; cut before submission.")
        return 3
    if n < MIN_PAGES:
        print(f"note: {n} < {MIN_PAGES} pages (acceptable only while sections are pending).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
