# CHANGELOG

## v3.10.0 - Daily Decision Loop

### Added

- 新增 Daily Decision Loop：盤前計畫、盤中觀察、盤後檢討、明日準備。
- 新增決策紀錄 journal：每次產生 payload 後保存 compact snapshot。
- 新增前次推薦檢討：比較前次推薦與本次價格變化。
- 新增 AI 沒選到強勢股的原因。
- 新增明日準備清單。
- 新增持股策略是否改變。
- 新增 Streamlit「決策閉環」功能頁。
- 新增 tests，確認 daily decision loop 與 journal ignore 規則。

### Changed

- Dashboard 預設首頁改為「決策閉環」。
- 每日報告順序改為先顯示股市老師今日結論，再顯示決策閉環。
- CLI 版本更新至 v3.10.0。

### Preserved

- v3.9.0 Decision Quality Gate。
- 今日可買與持股總教練共用老師敘事。
- Data Freshness Rule。
- Beta Access / Supabase 架構。
- 強勢股雷達與可追 / 已漲不追 / 明日接力分類。
