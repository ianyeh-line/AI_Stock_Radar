# Release Notes - v0.7.0

## Summary

v0.7.0 upgrades AI Stock Radar from a simple Streamlit prototype into a product-style decision dashboard.

## User value

The investor can now see:

- Market view
- AI confidence
- Buy candidates
- Decision cards
- Evidence chain
- Risk alerts
- News impact chain

## Acceptance

Run:

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

Open `http://localhost:8501` and verify the dashboard has Radar, Market Signals, Risk and Daily Report tabs.
