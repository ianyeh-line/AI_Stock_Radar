# Dashboard Architecture

The dashboard is intentionally built as a thin product layer over the decision pipeline.

```text
RSS / Curated Baseline
        ↓
NewsItem
        ↓
Knowledge Map
        ↓
Decision Engine
        ↓
Decision Cards
        ↓
Streamlit Dashboard + Markdown Report
```

The page does not own decision logic. It renders `DailyDecision` from the engine.
