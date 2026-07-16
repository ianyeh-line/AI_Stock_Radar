#!/usr/bin/env bash
set -euo pipefail

RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_REPO="${1:-${AI_STOCK_RADAR_REPO:-$HOME/Desktop/AI_Stock_Radar}}"
VERSION="v3.13.1"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$TARGET_REPO/.release_backups/$VERSION/$STAMP"

if [ ! -d "$TARGET_REPO" ]; then
  echo "Target repo not found: $TARGET_REPO"
  echo "Usage: bash upgrade_to_repo.sh /path/to/AI_Stock_Radar"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.release_backups' \
    --exclude 'data/cache/' \
    --exclude 'data/journal/' \
    --exclude 'output/daily_report.md' \
    --exclude 'output/dashboard_data.json' \
    "$TARGET_REPO/" "$BACKUP_DIR/"

  rsync -a --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.release_backups' \
    --exclude 'config/portfolio.json' \
    --exclude 'config/user_watchlist.json' \
    --exclude 'data/cache/' \
    --exclude 'data/journal/' \
    --exclude 'output/daily_report.md' \
    --exclude 'output/dashboard_data.json' \
    "$RELEASE_DIR/" "$TARGET_REPO/"
else
  echo "rsync not found; using cp fallback without delete cleanup"
  cp -R "$TARGET_REPO/." "$BACKUP_DIR/"
  cp -R "$RELEASE_DIR/." "$TARGET_REPO/"
fi

rm -f "$TARGET_REPO/output/daily_report.md" "$TARGET_REPO/output/dashboard_data.json"
mkdir -p "$TARGET_REPO/output"
touch "$TARGET_REPO/output/.gitkeep"

cd "$TARGET_REPO"
PYTHONPATH=src python3 -m py_compile app.py scripts/validate_decision_first_safepatch.py
PYTHONPATH=src python3 scripts/validate_decision_first_safepatch.py

if python3 -c "import pytest" >/dev/null 2>&1; then
  PYTHONPATH=src python3 -m pytest -q
else
  echo "pytest not installed; skipped full test suite"
fi

echo "Installed AI Stock Radar $VERSION Decision-first SafePatch into: $TARGET_REPO"
echo "Backup directory: $BACKUP_DIR"
echo "Run: PYTHONPATH=src python3 -m streamlit run app.py"
