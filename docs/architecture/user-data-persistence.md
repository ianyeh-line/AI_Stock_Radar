# User Data Persistence

## Decision

Personal user data is not part of release artifacts.

Starting v2.2.3, AI Stock Radar stores user-owned data in:

```text
~/.ai_stock_radar/
├── portfolio.json
└── user_watchlist.json
```

## Rationale

Release folders are overwritten frequently. If user records live inside the release folder, manual upgrade may delete personal holdings and watchlists.

## Migration

On first read, the application checks:

```text
config/portfolio.json
config/user_watchlist.json
```

If persistent files do not exist yet, legacy files are copied to `~/.ai_stock_radar/`.

## Deployment

Use `install_update.sh` to copy release files while preserving local personal data.
