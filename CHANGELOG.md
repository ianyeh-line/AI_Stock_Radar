# CHANGELOG

## v3.3.0 - Data Trust, Cloud Load UX, MACD Zero-Axis Unification

### Added

- 線上版登入後自動載入雲端持股與觀察清單。
- 個人持股分析新增今日最新可得價與台股漲紅跌綠顯示。
- 新增 TWSE / TPEx 資料源規劃文件。

### Changed

- 「MACD觀察」與「0軸MACD」整合成單一 MACD 0 軸觀察。
- MACD 觀察只列出 DIF 從 0 軸下方即將翻正或剛翻正的個股。
- 資料不新、fallback、樣本不足的個股不列入 MACD 觀察推薦。
- 技術圖表加入 MACD 0 軸狀態說明。

### Fixed

- 修正線上版輸入 Email + 存取碼後，需再按重新產生資料才看到持股的問題。
- 修正持股分析未顯示最新價與漲跌顏色的問題。
