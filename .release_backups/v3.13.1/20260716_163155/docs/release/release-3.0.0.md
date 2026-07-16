# Release v3.0.0

## Goal

Rebuild AI Stock Radar into a simplified stock teacher product.

## Main changes

- New product-first dashboard
- Stock teacher daily decision workflow
- Buy / wait / avoid lists
- Portfolio coach
- Persistent local user data
- Streamlit Cloud compatibility

## Validation

Run:

```bash
PYTHONPATH=src python3 -m radar.cli run
```

Then:

```bash
PYTHONPATH=src python3 -m streamlit run app.py
```
