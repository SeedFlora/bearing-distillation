#!/usr/bin/env bash
# Compile the IJCDS manuscript and enforce the page budget.
# IJCDS (For Authors, verified 2026-11-07): 10-15 pages INCLUDING references and appendices,
# counted on the official template output (US Letter). Over 15 pages fails the build; below 10 warns.
# Usage: bash scripts/build_paper.sh
set -euo pipefail
# regenerate tables and figures from the result files first; each figure script fails on a layout defect
# (element outside the canvas, label overflowing its box, colliding text), so a clipped figure stops the build
"$(dirname "$0")/../.venv/Scripts/python.exe" -I "$(dirname "$0")/make_tables.py"
"$(dirname "$0")/../.venv/Scripts/python.exe" -I "$(dirname "$0")/figures/fig_architecture.py"
"$(dirname "$0")/../.venv/Scripts/python.exe" -I "$(dirname "$0")/figures/fig_conditions.py"
cd "$(dirname "$0")/../paper/manuscript"
rm -f main.bbl main.aux main.blg main.fdb_latexmk main.fls
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > build.log 2>&1 || { tail -40 build.log; exit 1; }
grep -E "LaTeX Warning: (Citation|Reference).*undefined" main.log | sort -u || true
n_over=$(grep -c "Overfull" main.log || true)   # grep -c exits 1 on zero matches
echo "overfull boxes: ${n_over}"
ROOT="$(cd ../.. && pwd)"
"$ROOT/.venv/Scripts/python.exe" -I "$ROOT/scripts/check_pages.py" main.pdf
"$ROOT/.venv/Scripts/python.exe" -I "$ROOT/scripts/check_abstract.py" sections/00_abstract.tex
# open author decisions: \pending{...}, \pendinginline{...} and \todoauthor{...} markers per file (fixed strings, so "depending" is not counted)
grep -c -F -e '\pending' -e '\todoauthor' sections/*.tex | grep -v ':0$' || echo 'no pending or TO CONFIRM markers'
