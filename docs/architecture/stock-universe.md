# Stock Universe Architecture

AI Stock Radar 使用 `data/universe/taiwan_watchlist.json` 作為預設股票 universe。

## v1.3.0 Design

- 預設 universe：AI 產業鏈相關 100 檔台股。
- 使用者可在 `config/user_watchlist.json` 新增清單外個股。
- 個人持股資料存在 `config/portfolio.json`。
- `config/user_watchlist.json` 與 `config/portfolio.json` 不提交 GitHub。

## Principle

預設清單提供產品啟動時的完整分析範圍；使用者清單提供個人化擴充。
