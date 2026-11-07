#!/usr/bin/env bash
# Generate the architecture illustration with PaperBanana (llmsresearch/paperbanana, commit 87e01fd).
#
# PaperBanana calls cloud models (a VLM plus an image generator). It needs an API key in the
# environment and may incur charges (the tool's README lists about USD 0.134 per Gemini image,
# and each run renders several refinement iterations). Nothing runs unless a key is present.
#
#   Windows PowerShell (persists for new shells):  setx GOOGLE_API_KEY "<your key>"
#   or for OpenAI:                                  setx OPENAI_API_KEY "<your key>"
#
# Usage: bash scripts/run_paperbanana.sh [iterations]
# Output: paper/figures/paperbanana/out/run_<timestamp>/final_output.png (inspect before use;
#         the vector figure paper/manuscript/figures/fig_architecture.pdf remains the reference).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="D:/bahrain-data/tools/paperbanana"
VENV="D:/bahrain-data/tools/paperbanana-venv"
ITER="${1:-3}"
if [ -z "${GOOGLE_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "No GOOGLE_API_KEY or OPENAI_API_KEY in the environment; PaperBanana was not run." >&2
  exit 2
fi
if [ ! -x "$VENV/Scripts/python.exe" ]; then
  py -3.13 -m venv "$VENV"
  "$VENV/Scripts/python.exe" -m pip install --quiet "$TOOL[google,openai]"
fi
PROVIDER_ARGS=()
if [ -z "${GOOGLE_API_KEY:-}" ]; then PROVIDER_ARGS=(--vlm-provider openai --image-provider openai_imagen); fi
cd "$ROOT"
"$VENV/Scripts/paperbanana.exe" generate \
  --input paper/figures/paperbanana/architecture_method.txt \
  --caption "Training (a) and deployment (b) of the current-only student: a vibration-aware teacher supplies a 64-d bottleneck, bearing-grouped cross-fitted current-only bridges give out-of-group residuals that set fixed per-window gates on feature alignment, and only the student is deployed." \
  --venue ieee --iterations "$ITER" --output-dir paper/figures/paperbanana/out "${PROVIDER_ARGS[@]}"
