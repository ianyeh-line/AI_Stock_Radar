# AI Stock Radar

AI Stock Radar 是一個以「每天早上 3 分鐘完成台股 AI 決策」為目標的投資決策產品。

## v0.3.0 Product Release

本版完成第一個可驗收的產品化 Daily Radar：

- Mock News Data
- Decision Engine
- Radar Top 5
- Evidence by Stock
- Today's Action
- Risk Alert
- Markdown Daily Report

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

或：

```bash
./scripts/run.sh
```

## 產出

```text
output/daily_report.md
```

## 目前限制

v0.3.0 使用 mock data，尚未接入即時新聞、市場價格與法人資料。
