# Official Data Source Upgrade

v3.4.0 的目標是降低只依賴 Yahoo Finance 造成的價格失真風險。

## 資料優先順序

1. TWSE OpenAPI：上市股票最新日收盤資料。
2. TPEx OpenAPI：上櫃股票最新日收盤資料。
3. Yahoo Finance：歷史線圖與技術指標資料。
4. Fallback：僅在外部資料源失敗時讓產品可執行，不給 A 級推薦。

## 設計原則

- 官方資料負責「最新收盤校正」。
- Yahoo 負責「歷史 K 線與技術指標」。
- 若官方資料與 Yahoo 最新價差異過大，系統不直接信任推薦，會提示人工確認。

## 注意

TWSE / TPEx OpenAPI 是官方公開資料來源，但不是逐筆即時報價。AI Stock Radar 仍定位為盤前 / 盤後決策輔助工具，不是即時交易終端。
