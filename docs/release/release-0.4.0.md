# Release Notes - v0.4.0

## Summary

v0.4.0 是 AI Stock Radar 第一個接入真實 RSS 新聞來源的 Product Release。

## Delivered

- RSS News Datasource
- Fallback News
- Knowledge Mapping
- Decision Engine
- Markdown Daily Report
- Clean Git Ignore Rules

## Acceptance

Run:

```bash
PYTHONPATH=src python3 -m radar.cli run
```

Expected:

- Terminal shows AI Stock Radar v0.4.0
- Terminal shows RSS Live or Fallback
- `output/daily_report.md` is generated
