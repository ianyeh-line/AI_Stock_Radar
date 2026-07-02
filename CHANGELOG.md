# CHANGELOG

## v3.9.0 - Decision Quality Gate

### Added

- 新增 Recommendation Quality Gate。
- 今日可買推薦前先檢查價格位置、量能、RSI、資料有效性與突破可執行性。
- 每張決策卡新增品質檢查資訊。
- 今日可買與持股總教練共用 Teacher Narrative Engine。
- 新增 regression tests，涵蓋：
  - 現價高於拉回區時不可再建議低位分批。
  - 已修正資料來源文字不可再出現在推薦理由。
  - 今日可買需具備完整老師分析面向。

### Changed

- 今日可買的語氣從簡化理由升級為股市老師分析。
- 資料來源資訊退到頁尾與折疊區。
- 若資料不足，明確說明限制，不硬補籌碼或消息判斷。
- 若已突破，老師語句改成站穩與量能確認，不再寫「若突破」。

### Fixed

- 修正高於買點仍建議分批買進的邏輯。
- 修正突破價不可執行時仍當作今日條件的問題。
- 移除「Yahoo 較新 / 官方尚未同步 / 信心略降」等違反 Data Freshness Rule 的文字。
