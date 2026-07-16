# Official Data Source Architecture

AI Stock Radar v3.4.0 uses a hybrid price-data strategy:

```text
TWSE / TPEx OpenAPI
        ↓
Latest official daily close confirmation
        ↓
Yahoo Finance historical OHLC
        ↓
Indicators / chart / decision cards
```

## Why
Yahoo Finance is useful for historical charting, but the latest Taiwan stock close can sometimes diverge or lag. Official exchange data is preferred for latest daily close confirmation.

## Guardrail
If official confirmation is missing:

- The stock can still be analyzed.
- The recommendation confidence is lowered.
- It cannot receive high-trust actionable status.
