# Release v2.2.1 Refresh Hotfix

## Goal

Fix Dashboard refresh timeout/hanging after users add watchlist or portfolio positions.

## Changes

- Cache-first Yahoo Finance daily price loading.
- Concurrent technical profile loading across the AI stock universe.
- Shorter network timeout and stale-cache fallback before synthetic fallback.
- Dashboard refresh success/error state.
- Version updated to 2.2.1.

## Acceptance

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

Then add a portfolio holding and press refresh. The page should complete refresh instead of staying stuck.
