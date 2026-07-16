# Release v3.13.1 - Decision-first SafePatch

## Goal

修復 v3.13.0 交付時功能遺失的問題，重新以 v3.12.0 完整功能為基底，只做必要的決策首頁與文案修正。

## Changes

- 保留 v3.12.0 完整 app、src、tests、docs 與 CLI。
- 修正 `teacher_summary`，不再輸出版本 / UI / 資料工程說明。
- 「今天怎麼做」改成三個可執行任務。
- 新增「今日優先清單」表格。
- KPI 卡片加入行動提示。
- 主按鈕改為「更新今日資料」。
- 側欄移除 Supabase 連線測試，測試功能保留在設定頁。
- 新增 SafePatch 驗證腳本與測試。

## Verification

- `py_compile` 通過。
- `scripts/validate_decision_first_safepatch.py` 通過。
- `pytest` 通過：47 passed。
- 未包含 `__pycache__`。
- 未包含 `output/daily_report.md`。
- 未包含 `output/dashboard_data.json`。
