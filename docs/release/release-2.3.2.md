# Release v2.3.2 - Streamlit Import Path Hotfix

## Purpose

Fix Streamlit Cloud deployment failure caused by the cloud runtime not loading the local `src/` package path by default.

## Fixed

- Added explicit `src/` path bootstrap in `app.py` before importing `radar.*` modules.
- Kept `packages.txt` removed; Linux apt packages are not required for this app.
- Updated product version to `2.3.2`.

## Validation

- CLI can generate `output/dashboard_data.json` and `output/daily_report.md`.
- App package imports can resolve `radar.engine.decision` without manually setting `PYTHONPATH`.
