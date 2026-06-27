# Release Notes - v0.6.0

## Summary

v0.6.0 is the first release with an actual visible product page. It introduces a Streamlit dashboard available at `http://localhost:8501`.

## Validation

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

## Acceptance Criteria

- CLI runs successfully.
- Dashboard opens locally.
- Top 5 cards have differentiated scores.
- Evidence is not duplicated.
- `__pycache__` is not committed.
