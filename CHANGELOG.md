# CHANGELOG

## v3.6.1 - Teacher Narrative Fix

### Fixed

- 今日可買名單升級為可見的股市老師完整分析，不再把關鍵分析藏在摘要或模板理由中。
- 移除「Yahoo 較新 / 官方尚未同步 / 信心略降」等違反 Data Freshness Rule 的語句。
- 今日可買、持股總教練與觀察清單共用同一套 Teacher Narrative Engine。
- 持股總教練不再顯示不必要的資料可信度口號。
- MACD 觀察卡保留 MACD 小圖，不再顯示資料來源大段說明。

### Verification

- CLI 可執行。
- Tests passed: 23.

## v3.6.0 - Teacher Narrative UX Release

- 首頁資料來源說明移至頁尾。
- 每日報告改成先給操作結論。
- 今日可買新增股市老師敘事雛形。
