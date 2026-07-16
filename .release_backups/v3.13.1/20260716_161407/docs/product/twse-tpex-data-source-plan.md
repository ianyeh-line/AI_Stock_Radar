# TWSE / TPEx Data Source Plan

## Why

目前 AI Stock Radar 主要依賴 Yahoo Finance 取得日線資料。Yahoo Finance 方便、穩定度尚可，但不是台股官方資料源。為提升資料可信度，下一階段應逐步導入 TWSE / TPEx 官方開放資料。

## Proposed Sources

### TWSE

- 上市股票盤後資料
- 加權指數與市場統計
- 三大法人買賣超
- 上市個股基本資料

### TPEx

- 上櫃股票盤後資料
- 上櫃三大法人資料
- 上櫃個股基本資料

## Strategy

1. TWSE / TPEx 作為官方資料可信度來源。
2. Yahoo Finance 保留為技術線圖與跨市場 fallback。
3. 若官方資料與 Yahoo 價格差異過大，降低推薦信心。
4. 若官方資料尚未公布，明確標示資料狀態，不給 A 級買進。

## Implementation Priority

1. Stock Master：上市 / 上櫃判斷。
2. Daily Close：官方盤後收盤價。
3. Institutional Flow：三大法人買賣超。
4. Data Trust：官方資料日期檢查。
5. UI：顯示資料來源與最新資料日。
