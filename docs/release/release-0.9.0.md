# Release v0.9.0 - Stage 5 Product Release

## Release Goal

將 AI Stock Radar 從一般 Dashboard 升級為「波段操作型 AI 投資經理人」。

## New Product Capabilities

1. 個人化投資風格：預設以 2–8 週波段操作為主。
2. 個股技術線圖升級：K 線、MA20/60/120、布林通道、成交量、MACD、RSI。
3. AI 選出 MACD 即將翻正的十檔股票。
4. 投資經理人風格評價：進場、續抱、減碼、風險。
5. Dashboard 全中文。

## Acceptance Criteria

- CLI 可成功產生 `output/daily_report.md` 與 `output/dashboard_data.json`。
- Dashboard 可在 `http://localhost:8501` 開啟。
- 使用者可查看個股完整技術線圖。
- MACD 翻正十檔可被清楚呈現。
- Decision Card 的語氣要像專業投資經理人，而非單純技術訊號。
