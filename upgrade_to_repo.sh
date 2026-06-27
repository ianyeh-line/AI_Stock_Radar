#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${1:-$HOME/Desktop/AI_Stock_Radar}"
BACKUP_DIR="$TARGET_DIR/backups/user_data_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$TARGET_DIR" ]; then
  echo "Target repository not found: $TARGET_DIR"
  echo "Usage: bash upgrade_to_repo.sh /path/to/AI_Stock_Radar"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

# Back up legacy repo-local personal data before updating.
if [ -f "$TARGET_DIR/config/portfolio.json" ]; then
  cp "$TARGET_DIR/config/portfolio.json" "$BACKUP_DIR/portfolio.json"
fi
if [ -f "$TARGET_DIR/config/user_watchlist.json" ]; then
  cp "$TARGET_DIR/config/user_watchlist.json" "$BACKUP_DIR/user_watchlist.json"
fi

# Also back up durable user data if already migrated.
if [ -f "$HOME/.ai_stock_radar/portfolio.json" ]; then
  cp "$HOME/.ai_stock_radar/portfolio.json" "$BACKUP_DIR/home_portfolio.json"
fi
if [ -f "$HOME/.ai_stock_radar/user_watchlist.json" ]; then
  cp "$HOME/.ai_stock_radar/user_watchlist.json" "$BACKUP_DIR/home_user_watchlist.json"
fi

# Copy product files while preserving Git history and local personal data.
rsync -av --delete \
  --exclude '.git/' \
  --exclude 'backups/' \
  --exclude 'config/portfolio.json' \
  --exclude 'config/user_watchlist.json' \
  --exclude 'output/daily_report.md' \
  --exclude 'output/dashboard_data.json' \
  --exclude 'data/cache/' \
  "$SOURCE_DIR/" "$TARGET_DIR/"

# Restore repo-local files if they existed. v2.2.4 will migrate them to ~/.ai_stock_radar on next run.
if [ -f "$BACKUP_DIR/portfolio.json" ]; then
  mkdir -p "$TARGET_DIR/config"
  cp "$BACKUP_DIR/portfolio.json" "$TARGET_DIR/config/portfolio.json"
fi
if [ -f "$BACKUP_DIR/user_watchlist.json" ]; then
  mkdir -p "$TARGET_DIR/config"
  cp "$BACKUP_DIR/user_watchlist.json" "$TARGET_DIR/config/user_watchlist.json"
fi

cd "$TARGET_DIR"
bash scripts/cleanup_repo.sh >/dev/null 2>&1 || true

echo "Upgrade complete: v2.3.2 Streamlit Import Path Hotfix"
echo "Repository: $TARGET_DIR"
echo "User data backup: $BACKUP_DIR"
echo "Next: PYTHONPATH=src python3 -m radar.cli run"
