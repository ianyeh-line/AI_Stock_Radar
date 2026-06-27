# CHANGELOG

## v0.9.0 - Stage 5 Product Release

### Added

- 新增 Stage 5：個人化與波段操作決策層。
- 新增 `config/investor_profile.json`，定義使用者投資風格為波段操作。
- 新增 MACD 翻正候選股排序引擎。
- 新增更完整的個股技術線圖：K 線、MA20、MA60、MA120、布林通道、成交量、MACD、RSI。
- 新增 Dashboard 個股互動選擇與線圖檢視。
- 新增投資經理人風格分析：進場條件、續抱條件、減碼條件、風險控管。
- 新增 `output/dashboard_data.json`，提供 Dashboard 與後續 API 使用。

### Changed

- Dashboard 全面中文化。
- Decision Card 從一般建議升級為波段操作建議。
- Radar Score 調整為更重視趨勢、風險報酬比與技術確認。
- MACD、RSI、MA 結構納入個股評價文字。

### Fixed

- 避免分數過度飽和造成全部 Buy。
- 避免重複 Evidence 顯示。
- 強化 `.gitignore`，避免 `__pycache__` 與每日輸出進入 Git。

## v0.8.0 - Stage 4 Product Release

- 新增中文 Dashboard。
- 新增 Decision OS v1。
- 新增技術線圖入口。

## v0.7.0 - Dashboard UX Release

- 新增 Dashboard 首頁。
- 新增 Top Decision Cards。
- 新增 Evidence Chain。

## v0.6.0 - Dashboard Release

- 新增 Streamlit Dashboard。

## v0.5.0 - Explainable Decision Cards

- 新增可解釋決策卡。

## v0.4.0 - RSS Live News

- 新增 RSS 真實新聞來源。
