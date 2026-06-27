# Sprint 15 Hotfix - v2.2.2

## Objective

Repair price-context language in entry/add-position guidance.

## Completed

- Added price-context based entry language.
- Removed illogical "stand back above support" language when current price is already above support.
- Added regression test for the 國巨-style scenario.

## Acceptance

If current price is already above support but still below breakout, the product should say:

```text
現價已高於支撐區，但尚未突破壓力；不追高，等待突破或回測支撐區守穩。
```
