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
  --exclude 'data/journal/' \
  --exclude 'output/daily_report.md' \
  --exclude 'output/dashboard_data.json' \
  "$SOURCE_DIR/" "$TARGET/"

# Version Integrity: runtime reports/payloads are generated files. Remove old
# files after upgrade so the app cannot show a stale report from a previous
# release, such as app v3.11.x with report v3.9.0.
rm -f "$TARGET/output/daily_report.md" "$TARGET/output/dashboard_data.json"
mkdir -p "$TARGET/output"
touch "$TARGET/output/.gitkeep"

echo "AI Stock Radar v3.11.2 Version Integrity + Report Sync 已升級到 $TARGET"
