# Release v1.7.1

Fast Dashboard Hotfix.

## Why

v1.7.0 Dashboard opened slowly because Streamlit regenerated the full data pipeline on page load.

## What changed

- Page load reads `output/dashboard_data.json`.
- Manual refresh button triggers full fresh data pipeline.
- Institutional flow scoring now respects total institutional net flow direction.
- Teacher Buy List A-grade names must be near executable pullback or breakout prices.
