# CHANGELOG

## v3.5.2 - Data Freshness and Input Flow Hotfix

### Fixed

- 價格來源改為最新可得資料優先，不論來自 TWSE / TPEx 或 Yahoo。
- Yahoo 日線會合併最新報價 meta，降低官方資料未更新造成的舊資料問題。
- 新增持股與觀察清單改為 form，避免輸入股號、股數、成本時觸發資料抓取。
- 更新版本號與 Release 文件。

## v3.5.1 - Data Source Reliability Hotfix

- 修正官方資料異常造成線圖與持股估值失真。
