# Release 3.5.0 - Data Source Truthfulness

## Goal

讓 AI Stock Radar 在官方資料未更新、Yahoo 資料較新、資料過舊或 fallback 時，能清楚標示資料狀態並限制強推薦。

## Key Changes

- 新增預期最新交易日判斷。
- TWSE / TPEx 官方資料與 Yahoo Finance 進行日期比較。
- 採用較新的可得資料作為當日判斷基準。
- 官方資料落後於 Yahoo 時，不再覆蓋 Yahoo。
- 官方資料無日期時，不再假設為今日。
- 資料不足時降級為觀察。

## Validation

- CLI 可執行。
- 測試通過：19 passed。
