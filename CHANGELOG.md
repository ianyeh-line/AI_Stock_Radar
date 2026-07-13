# CHANGELOG

## v3.11.1 - Action Precision + MACD Restore + Chip Quiet Mode

### Added

- 新增 `macd_zero_action`，讓 0 軸轉強雷達每檔都提供具體價格條件。
- 新增測試覆蓋：無數字不建議、籌碼安靜模式、MACD 0 軸建議必須有價格。

### Changed

- 老師建議改為「具體價格 / 區間」優先，不再使用泛用的「等回測支撐」語句。
- 法人 / 籌碼資料未取得時，僅顯示「法人籌碼：未取得，不列入本次判斷。」
- 個股研究頁的 MACD 區塊改名為「0軸轉強雷達」，專注於 DIF 接近或剛站上 0 軸。
- MACD 觀察卡顯示 DIF、DEA、柱狀體、RSI、量能比與小型 MACD 圖。

### Fixed

- 移除籌碼無資料時的長篇說明。
- 移除沒有具體價位的下一步建議。

### Verified

- CLI 可執行。
- 測試通過。
- Release package 不包含 `__pycache__`、runtime output 或 journal runtime 檔案。
