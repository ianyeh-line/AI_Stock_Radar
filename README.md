# AI Stock Radar v3.6.0

AI 股市老師盤前決策系統。

## 本版重點

- 今日可買名單升級為股市老師完整分析卡。
- 首頁與每日報告先給決策，再把資料來源說明放到頁尾。
- 資料來源只作為頁尾資訊，不寫入推薦理由，也不影響最新有效資料的評等。
- 老師建議會依照現價是否已突破關鍵價動態改寫。
- 今日可買與持股總教練共用同一套 Teacher Narrative Engine。
- MACD 觀察卡改放 MACD 小型線圖，不再放大段資料狀態。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```
