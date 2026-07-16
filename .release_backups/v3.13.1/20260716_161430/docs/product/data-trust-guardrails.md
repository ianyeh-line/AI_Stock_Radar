# Data Trust Guardrails

A stock cannot receive A-grade actionable buy status when:

- Price source is fallback instead of Yahoo Finance.
- Latest price date is older than seven days.
- Daily sample count is below 60 bars.

When any of these happens, the card is downgraded to observation-only.
