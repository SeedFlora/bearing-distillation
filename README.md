# Current-only bearing diagnosis with cross-modal distillation (research code)

Working title: *When Does Vibration-Aware Distillation Help Current-Only Bearing Fault
Diagnosis? A Bearing-Grouped Study on Unseen Bearings and Operating Conditions* (target: IJCDS;
the earlier title "Transferability-Aware ..." was dropped in protocol Amendment A4).

This repository contains the experimental code, frozen data splits, saved predictions,
analysis outputs and ONNX exports. Protocol A holds out physical bearings. Protocol B
also holds out an operating condition. See [the experimental protocol](reports/protocol.md)
and [the run registry](results/main/RUN_REGISTRY.md).

## Layout

| Path | Content |
|---|---|
| `src/cmkd/io/` | Readers for Paderborn `.mat` and KAIST `.mat`/`.tdms` (channels resolved by name) |
| `src/cmkd/data/` | Uniform resampling, decimation, per-window standardisation, window indexing |
| `scripts/` | Download, audit, split generation, training, analysis and deployment |
| `configs/data/` | Label decisions applied on top of official factsheets |
| `manifests/` | Download provenance, audited recordings/bearings, frozen splits |
| `reports/` | Data audits and experimental protocol |
| `results/` | Saved predictions, metrics and analysis outputs |
| `tests/` | Preprocessing and data-contract tests |

Raw data live outside the repository (`D:\bahrain-data\`, decision D01) and are
never redistributed. Dataset licences: Paderborn CC BY-NC 4.0; KAIST CC BY 4.0.

## Reproduce what exists so far (Windows, Git Bash)

```bash
# 1. environment (reuses a CUDA build of torch from the base Python 3.13)
py -3.13 -m venv --system-site-packages .venv
.venv/Scripts/python.exe -m pip install nptdms tabulate
.venv/Scripts/python.exe -m pip install --no-deps -e .

# 2. data (resumable; records size, SHA-256 and Last-Modified)
bash scripts/download.sh manifests/download_lists/paderborn.tsv D:/bahrain-data/raw/paderborn manifests/provenance/paderborn_downloads.tsv
bash scripts/download.sh manifests/download_lists/kaist_varying_load_v6.tsv D:/bahrain-data/raw/kaist manifests/provenance/kaist_downloads.tsv

# 3. audit (extracts archives with WinRAR UnRAR.exe; parses factsheets and every recording)
.venv/Scripts/python.exe -I scripts/audit_paderborn.py --raw D:/bahrain-data/raw/paderborn --extracted D:/bahrain-data/extracted/paderborn
.venv/Scripts/python.exe -I scripts/extract_kaist.py --raw D:/bahrain-data/raw/kaist --out D:/bahrain-data/extracted/kaist
.venv/Scripts/python.exe -I scripts/audit_kaist.py --root D:/bahrain-data/extracted/kaist

# 4. frozen splits (metadata only; refuses unverified label overrides)
.venv/Scripts/python.exe -I scripts/make_splits.py --seed 20261107

# 5. development-only spectra and caches
.venv/Scripts/python.exe -I scripts/dev_spectra.py --extracted D:/bahrain-data/extracted/paderborn
.venv/Scripts/python.exe -I scripts/build_cache.py --extracted D:/bahrain-data/extracted/paderborn --out D:/bahrain-data/cache/paderborn/v2

# 6. tests and re-analysis from the saved predictions
.venv/Scripts/python.exe -I -m pytest -q tests/
.venv/Scripts/python.exe -I scripts/analyze_main.py --boot 10000 --out results/reproduced
```
