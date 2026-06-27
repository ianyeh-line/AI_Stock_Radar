#!/usr/bin/env bash
set -euo pipefail

RELEASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-$HOME/Desktop/AI_Stock_Radar}"
USER_DATA_DIR="$HOME/.ai_stock_radar"

if [ ! -d "$TARGET_DIR" ]; then
  echo "找不到目標專案資料夾：$TARGET_DIR" >&2
  echo "請確認 AI_Stock_Radar 位於 Desktop，或用參數指定路徑。" >&2
  exit 1
fi

mkdir -p "$USER_DATA_DIR"

# Migrate existing local personal data before copying release files.
if [ ! -f "$USER_DATA_DIR/portfolio.json" ] && [ -f "$TARGET_DIR/config/portfolio.json" ]; then
  cp "$TARGET_DIR/config/portfolio.json" "$USER_DATA_DIR/portfolio.json"
  echo "已備份/遷移個人持股到 $USER_DATA_DIR/portfolio.json"
fi

if [ ! -f "$USER_DATA_DIR/user_watchlist.json" ] && [ -f "$TARGET_DIR/config/user_watchlist.json" ]; then
  cp "$TARGET_DIR/config/user_watchlist.json" "$USER_DATA_DIR/user_watchlist.json"
  echo "已備份/遷移觀察清單到 $USER_DATA_DIR/user_watchlist.json"
fi

rsync -av --delete \
  --exclude '.git/' \
  --exclude 'config/portfolio.json' \
  --exclude 'config/user_watchlist.json' \
  --exclude 'config/settings.json' \
  --exclude 'output/daily_report.md' \
  --exclude 'output/dashboard_data.json' \
  "$RELEASE_DIR/" "$TARGET_DIR/"

echo "v2.2.3 已部署到 $TARGET_DIR"
echo "個人持股與觀察清單保存於：$USER_DATA_DIR"
