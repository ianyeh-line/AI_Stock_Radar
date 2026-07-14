# Release v3.12.0 - Responsive Decision UX

## Goal

讓 AI Stock Radar 的頁面更像使用者每天會打開的決策工具，而不是開發者後台。

## Changes

- 重新整理主視覺與首頁結構。
- 手機與桌面都採卡片式閱讀。
- 資料來源與診斷資訊預設收合到頁尾。
- 今日可買、持股、強勢股、MACD 觀察都改為摘要優先。
- 每日報告個股分析預設收合。

## Verification

- CLI runs.
- Existing regression tests pass.
- Version integrity remains centralized through `src/radar/version.py`.
