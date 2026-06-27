# AI Stock Radar

AI Stock Radar is a Taiwan-stock decision intelligence product designed to help investors complete a 3-minute morning decision workflow.

## Current Release

**v0.5.0 Product Release**

Focus: Explainable Decision Cards.

This version converts RSS/news signals into stock-level Decision Cards with:

- Radar Score
- Decision: Buy / Watch / Wait / Sell
- Confidence
- Evidence chain
- Action recommendation
- Risk alert

## Run

```bash
PYTHONPATH=src python3 -m radar.cli run
```

Output:

```text
output/daily_report.md
```

## Product Flow

```text
RSS / Fallback News
        ↓
Signal Classification
        ↓
Stock Knowledge Map
        ↓
Decision Engine
        ↓
Decision Cards
        ↓
Markdown Daily Report
```

## Release Principle

Every release must be executable, reviewable, and product-oriented.
