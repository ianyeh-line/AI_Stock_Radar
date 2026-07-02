# CHANGELOG

## v3.8.3 - Teacher Logic and Momentum Fix

### Fixed

- 強勢股雷達資料來源抓不到時，新增 endpoint 診斷，不再無原因空白。
- 官方資料解析不足時，新增 Yahoo Quote fallback，並明確標示不是純官方全市場資料。
- 強勢股頁面顯示官方解析數、Yahoo 補充數、候選分析數。
- 新增欄位解析防呆，支援更多 TWSE / TPEx 中文欄位名稱。

### Changed

- 強勢股雷達從「有沒有資料」改成「資料來源是否真正抓取與解析成功」。
