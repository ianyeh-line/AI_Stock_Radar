# Release v2.2.3 User Data Persistence Hotfix

## Purpose

Prevent personal portfolio and watchlist records from being lost during release upgrades.

## Changes

- Moved durable user data storage to `~/.ai_stock_radar/`.
- Migrates legacy `config/portfolio.json` and `config/user_watchlist.json` on first run.
- Added `upgrade_to_repo.sh` to update product files safely.
- Dashboard sidebar now shows where personal records are saved.

## Validation

- CLI runs successfully.
- User data load/save functions support persistent home-directory storage.
- Legacy config files remain compatible.
