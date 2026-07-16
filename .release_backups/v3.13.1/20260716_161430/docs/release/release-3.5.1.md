# Release v3.5.1 - Data Source Reliability Hotfix

## Goal

修正 v3.5.0 線上版在官方資料、Yahoo 資料與快取 payload 之間造成的資料可信度與畫面失真問題。

## Fixed

- App 與 payload 版本不一致時自動重算，避免線上版顯示舊版本號。
- 官方快照價格若與 Yahoo 最新價差異過大，不再覆蓋 Yahoo 歷史日線。
- 個股線圖會清理異常日期與非數字價格，避免 K 線 / MACD 失效。
- 持股總教練在資料可信度不足時只給觀察與風險控管建議，不再給加碼暗示。
- 今日股價顏色維持台股邏輯：漲紅、跌綠、平盤灰。

## Validation

- CLI runs successfully.
- Test suite passes: 19 passed.
