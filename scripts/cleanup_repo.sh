#!/usr/bin/env bash
set -e
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name ".DS_Store" -delete
rm -f output/daily_report.md output/dashboard_data.json
mkdir -p output
touch output/.gitkeep
