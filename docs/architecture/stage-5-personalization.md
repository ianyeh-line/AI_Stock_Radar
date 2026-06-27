# Stage 5 Architecture - Personalization and Swing Trading

## Overview

Stage 5 introduces an investor profile layer and a swing-trading decision layer.

```text
News
  ↓
Signal Classification
  ↓
Stock Mapping
  ↓
Technical Radar
  ↓
Investor Profile
  ↓
Decision Card
  ↓
Dashboard / Report
```

## Investor Profile

The default profile is a moderate-risk swing trader:

- Holding period: 2–8 weeks.
- Prefer pullback entries.
- Avoid opening chase.
- Prefer MACD turn-positive setups.
- Avoid overheated RSI.

## Technical Radar

Current indicators:

- MA20 / MA60 / MA120.
- Bollinger Band.
- MACD DIF / DEA / Histogram.
- RSI.
- Volume.

## Decision Language

Decision Card output should sound like a professional investment manager:

- Entry condition.
- Hold condition.
- Reduce condition.
- Risk note.
