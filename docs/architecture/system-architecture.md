# System Architecture

## Architecture Principle

AI Stock Radar uses a modular, maintainable architecture. Each engine owns one responsibility and can be tested independently.

## High-Level Architecture

```text
External Data Sources
  -> Ingestion Layer
  -> Normalization Layer
  -> Analysis Engines
  -> Scoring Engine
  -> Decision Engine
  -> Report Generator
```

## Modules

### Ingestion Layer

Responsible for collecting market data, news, and financial information from external sources.

### Normalization Layer

Converts heterogeneous external data into internal data models.

### Analysis Engines

Includes:

- News Engine
- Macro Engine
- Technical Engine
- Fundamental Engine
- Institutional Flow Engine

### Scoring Engine

Calculates the explainable Radar Score.

Initial weights:

| Dimension | Weight |
|---|---:|
| News Impact | 25% |
| Technical Trend | 30% |
| Fundamentals | 20% |
| Institutional Flow | 15% |
| Momentum | 10% |

### Decision Engine

Maps scores and risk conditions into daily actions:

- Buy
- Watch
- Hold
- Reduce
- Avoid

### Report Generator

Produces daily 3-minute decision reports.
