#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/Desktop/AI_Stock_Radar"

if [ ! -d "$TARGET" ]; then
  echo "找不到 $TARGET，請確認 AI_Stock_Radar 在桌面。"
  exit 1
fi

rsync -av --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'config/portfolio.json' \
  --exclude 'config/user_watchlist.json' \
  --exclude 'data/cache/' \
  --exclude 'output/daily_report.md' \
  --exclude 'output/dashboard_data.json' \
  "$SOURCE_DIR/" "$TARGET/"

echo "AI Stock Radar v3.8.2 Market Strength Reliability Fix 已升級到 $TARGET"
