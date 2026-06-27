# AI Stock Radar

AI Stock Radar 是一套協助投資人縮短台股盤前決策時間的本機工具。

## v1.7.1 Fast Dashboard Hotfix

本版重點：

- Dashboard 預設讀取 `output/dashboard_data.json`，不再一開頁面就重新抓 100 檔價格與法人資料。
- 只有按下「重新抓取最新資料」時，才會重新執行完整資料管線。
- 修正法人籌碼判斷：三大法人合計為賣超時，不會因單一法人買超就標示為明顯偏多。
- 股市老師買進名單加入「可操作性」判斷，避免把距離拉回區或突破價過遠的標的列為 A 級今日可買。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```
