# Changelog

## v0.4.0 - RSS Product Release

### Added
- 第一版 RSS 真實新聞來源。
- Fallback news 機制，避免網路或 RSS 失效時無法產生報告。
- Keyword-based Knowledge Layer。
- Decision Engine：將新聞轉換為股票 Radar 排名。
- Markdown Report Generator。
- `.gitignore` 清理 Python 與 macOS 暫存檔。

### Changed
- CLI 顯示版本號、新聞來源、Market View、Top 5 與報告路徑。
- Daily Report 加入 Source News 與 Evidence by Stock。

### Removed
- 不再提交每日產生的 `output/daily_report.md`。
- 不再提交 `__pycache__` 與 `.DS_Store`。
