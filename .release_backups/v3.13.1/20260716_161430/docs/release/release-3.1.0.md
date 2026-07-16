# Release v3.1.0 - Dynamic Stock + MACD Zero Axis

## Goal

解決清單外個股無法新增的問題，並新增更有波段意義的 MACD 0 軸轉強觀察名單。

## Highlights

- 清單外股號自動嘗試 `.TW / .TWO` 日線資料。
- 自訂個股資料保存於使用者本機資料夾。
- MACD 區分「柱狀體翻正」與「MACD 線從 0 軸翻正」。
- Dashboard 新增 0 軸 MACD 頁籤。

## Acceptance

1. 輸入清單外股號不應直接報錯。
2. 若 Yahoo Finance 有資料，應能產生持股分析。
3. MACD 0 軸名單應與原 MACD 觀察名單分開。
4. v3.0.2 的 2313 / 2408 / 4952 修正仍應保留。
