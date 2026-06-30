# CHANGELOG

## v3.2.4 - UX State and MACD Chart Hotfix

### Fixed

- 修正 Streamlit 線上版在按下「測試 Supabase 連線」後跳回首頁的問題。
- 修正按下「重新產生今日決策資料」後跳回首頁的問題。
- 修正技術線圖切換到 1 個月後 MACD/DIF/DEA 消失的問題。

### Changed

- 將原本 Streamlit tabs 改成可保存狀態的水平功能切換列。
- MACD 圖表改為使用完整歷史價格計算，再截取顯示區間。
