# AI Stock Radar v3.0.2 Stock Master Regression Hotfix

## Purpose

Fix another Stock Master regression found during personal portfolio testing.

## Fixed

- `4952` now resolves to `4952 凌通`.
- `凌通` now resolves to `4952 凌通`.
- `4952 凌通` now resolves to `4952 凌通`.
- Unknown numeric inputs with user-provided Chinese names now preserve the submitted name instead of always showing `自訂個股`.
- Added regression tests for 2313 華通, 2408 南亞科, and 4952 凌通.

## Product Impact

Personal portfolio and watchlist input should no longer reject 4952 凌通 or display it as unknown.
