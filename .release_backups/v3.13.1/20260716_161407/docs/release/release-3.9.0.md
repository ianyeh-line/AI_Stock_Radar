# Release v3.9.0 - Decision Quality Gate

## Goal

讓 AI Stock Radar 的推薦更可執行、更可信、更像股市老師，而不是只顯示制式條件摘要。

## Delivered

- Recommendation Quality Gate
- Teacher Narrative Engine 強化
- 今日可買與持股總教練共用老師語句邏輯
- 資料來源資訊退到頁尾
- Regression tests

## Acceptance Criteria

- 高於拉回買點的股票，不可仍建議在低位分批。
- 已突破的股票，不可寫「若突破」。
- 沒有籌碼資料時，不可假裝有籌碼加分。
- 資料來源不應成為推薦理由。
- 今日可買必須包含技術、籌碼限制、產業消息、支撐壓力、A/B/C 劇本、未持有者與已持有者策略。
