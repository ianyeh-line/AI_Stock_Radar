#!/usr/bin/env bash
set -e
find . -name '__pycache__' -type d -prune -exec rm -rf {} +
find . -name '*.pyc' -delete
find . -name '.DS_Store' -delete
rm -rf .pytest_cache
rm -f output/daily_report.md output/dashboard_data.json
mkdir -p output data/cache
touch output/.gitkeep data/cache/.gitkeep
