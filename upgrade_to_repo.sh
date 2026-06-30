#!/usr/bin/env bash
set -e
RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/Desktop/AI_Stock_Radar"
if [ ! -d "$TARGET" ]; then
  echo "找不到 $TARGET"
  exit 1
fi
rsync -av --delete \
  --exclude '.git/' \
  --exclude 'output/daily_report.md' \
  --exclude 'output/dashboard_data.json' \
  --exclude 'config/portfolio.json' \
  --exclude 'config/user_watchlist.json' \
  "$RELEASE_DIR/" "$TARGET/"
echo "AI Stock Radar v3.5.1 Data Source Reliability Hotfix 已升級到 $TARGET"
