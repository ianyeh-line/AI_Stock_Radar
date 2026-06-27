# Release Notes - v0.3.0

## Goal
交付第一個可驗收的產品化版本，讓使用者執行後可以直接看到 Radar Top 5、Evidence、Action 與 Risk。

## Acceptance Criteria
- 執行 `PYTHONPATH=src python3 -m radar.cli run` 成功。
- Terminal 顯示 Market View、AI Confidence 與 Top 5。
- 產生 `output/daily_report.md`。
- 報告包含 Today's Radar、Radar Top 5、Evidence by Stock、Market Signals、Today's Action、Risk Alert。
