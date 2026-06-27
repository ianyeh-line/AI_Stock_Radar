# Decision Engine Architecture

## Flow

```text
NewsItem
  ↓
Signal
  ↓
Evidence
  ↓
Stock Knowledge Map
  ↓
Radar Score
  ↓
Decision Card
```

## Core Concept

A Radar Score is not enough. Each decision must include:

- Evidence
- Confidence
- Action
- Risk

## Current Status

v0.5.0 uses rule-based scoring for product validation. Future versions will add better data sources and technical indicators.
