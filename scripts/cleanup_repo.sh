#!/usr/bin/env bash
set -e
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
find . -name '.DS_Store' -delete
rm -f output/daily_report.md output/dashboard_data.json
