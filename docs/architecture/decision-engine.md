# Decision Engine

The Decision Engine converts news signals into explainable stock-level decision cards.

Pipeline:

```text
RSS News
  -> Signal Classification
  -> Stock Mapping
  -> Evidence Deduplication
  -> Radar Score
  -> Decision
  -> Confidence
  -> Report / Dashboard
```

Radar Score is intentionally bounded and conservative. A score of 100 should be rare and should require multiple independent positive evidence sources with limited risk.
