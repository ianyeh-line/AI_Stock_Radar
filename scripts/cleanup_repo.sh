#!/usr/bin/env bash
set -euo pipefail

find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name ".DS_Store" -delete

git rm -r --cached --ignore-unmatch \
  src/radar/__pycache__ \
  src/radar/datasource/__pycache__ \
  src/radar/engine/__pycache__ \
  src/radar/knowledge/__pycache__ \
  src/radar/models/__pycache__ \
  src/radar/report/__pycache__ \
  output/daily_report.md \
  output/dashboard_data.json >/dev/null 2>&1 || true

echo "Runtime files cleaned."
