# CHANGELOG

## v3.1.0 - Dynamic Stock + MACD Zero Axis

### Added

- Dynamic Stock Resolver：清單外個股可輸入股號後自動嘗試抓取 `.TW / .TWO` 資料。
- Custom Stock Store：成功識別的自訂個股會保存到 `~/.ai_stock_radar/custom_stocks.json`。
- MACD Zero Axis Watchlist：新增「MACD 即將從 0 軸翻正」觀察名單。
- Dashboard 新增「0軸MACD」頁籤。
- 測試覆蓋：未知股號、使用者自訂名稱、Stock Master 回歸、MACD 0 軸欄位。

### Changed

- 新增持股 / 觀察清單時會先建立個股決策卡，若資料源可識別名稱，會儲存更正確的名稱。
- 個股線圖選單會納入個人持股與指定觀察個股。
- 股市老師總評提醒：0 軸 MACD 是優先觀察，不等於無條件買進。

### Fixed

- 避免清單外個股因 Stock Master 未收錄而無法新增。
- 避免完整版本重整後再次遺失前幾版的自訂個股能力。
