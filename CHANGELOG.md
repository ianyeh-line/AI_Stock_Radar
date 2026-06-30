# CHANGELOG

## v3.5.3 - Data Freshness Rule Update

### Changed

- 正式套用 Data Freshness Rule v1：以目前交易狀態下最新有效資料為準。
- 移除「來源差異過大」作為降級原因；不再因 Yahoo / 官方差異而自動降等。
- 盤前接受前一交易日資料；盤中接受當日盤中資料；盤後接受當日最新可得資料；非交易日接受最近交易日資料。
- Yahoo 或官方只要是最新有效資料，都可作為操作評分基準。

## v3.5.3 - Data Freshness Rule Update

### Fixed

- 價格來源改為最新可得資料優先，不論來自 TWSE / TPEx 或 Yahoo。
- Yahoo 日線會合併最新報價 meta，降低官方資料未更新造成的舊資料問題。
- 新增持股與觀察清單改為 form，避免輸入股號、股數、成本時觸發資料抓取。
- 更新版本號與 Release 文件。

## v3.5.1 - Data Source Reliability Hotfix

- 修正官方資料異常造成線圖與持股估值失真。
