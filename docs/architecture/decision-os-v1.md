# Decision OS v1

AI Stock Radar v1.0.0 採用 Investment Manager Layer。

## Pipeline

```text
News
  -> Signal
  -> Evidence
  -> Technical Confirmation
  -> Risk Adjustment
  -> Radar Score
  -> Decision Card
  -> PM Brief
  -> Report / Dashboard
```

## Design Principles

1. Score must be explainable.
2. Every Buy must have invalidation criteria.
3. Every Sell / Avoid must have a reason.
4. Dashboard must answer: What should I do today?
5. Decision confidence is not price prediction.

## Score Components

- Base Score
- News / Signal Score
- Technical Score
- Risk Penalty
- Profile Bonus

## Next Architecture Improvement

The next major version should connect real price data directly into the Decision Engine so technical scores are derived from live historical prices rather than static profile fields.
