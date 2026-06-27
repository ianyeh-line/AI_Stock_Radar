# Institutional Flow Radar

AI Stock Radar 會優先嘗試 TWSE T86 三大法人資料，將外資、投信、自營商與三大法人合計轉換為籌碼分數。

若官方資料抓取失敗或個股無對應資料，系統會使用 fallback flow model，以量價狀態產生保守籌碼推估，並在 Dashboard 中明確標示。

法人籌碼分數會進入：

- Radar Score
- Evidence Chain
- 今日優先動作
- 每日報告
