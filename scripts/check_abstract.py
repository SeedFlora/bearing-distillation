"""Count the words of the IJCDS abstract (limit 200, For Authors page, verified 2026-11-07).

Usage: .venv/Scripts/python.exe -I scripts/check_abstract.py paper/manuscript/sections/00_abstract.tex
Exit code 4 when the abstract exceeds 200 words. Numbers and hyphenated compounds count as one word each.
"""
import re
import sys

LIMIT = 200


def main() -> int:
    tex = open(sys.argv[1], encoding="utf-8").read()
    body = tex.split(r"\textbf{Abstract:}", 1)[1].split(r"\textbf{Keywords:}", 1)[0]   # keywords are not abstract words
    body = re.sub(r"\$([^$]*)\$", lambda m: m.group(1).replace("\\", ""), body)      # inline math -> its text
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", body)                           # drop commands
    body = body.replace("~", " ").replace("{", " ").replace("}", " ").replace("\\%", "%")
    words = [w for w in body.split() if re.search(r"[A-Za-z0-9]", w)]
    print(f"abstract words: {len(words)} (limit {LIMIT})")
    return 4 if len(words) > LIMIT else 0


if __name__ == "__main__":
    sys.exit(main())
