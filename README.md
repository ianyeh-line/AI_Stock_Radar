# AI Stock Radar

AI Stock Radar 是一個以「每天早上 3 分鐘完成台股 AI 決策」為目標的投資決策產品。

本版本為 **v0.9.0 Stage 5 Product Release**，重點從「通用 Radar」升級為「波段操作型 AI 投資經理人」。

## v0.9.0 新增重點

- 介面全中文。
- 新增投資人偏好：以 **2–8 週波段操作** 為核心。
- 新增個股完整技術線圖：K 線、MA20/60/120、布林通道、成交量、MACD、RSI。
- 新增 **AI 選出 MACD 即將翻正的十檔股票**。
- 新增專業投資經理人風格的個股評價：波段進場條件、續抱條件、減碼條件與風險。
- 所有 Dashboard 主要個股區塊皆提供「查看技術線圖」互動入口。

## 快速執行

在專案根目錄執行：

```bash
PYTHONPATH=src python3 -m radar.cli run
```

會產出：

```text
output/daily_report.md
output/dashboard_data.json
```

## 開啟 Dashboard

第一次使用請先安裝依賴：

```bash
python3 -m pip install -r requirements.txt
```

啟動頁面：

```bash
PYTHONPATH=src python3 -m streamlit run app.py
```

瀏覽器開啟：

```text
http://localhost:8501
```

## 產品定位

AI Stock Radar 不是技術分析展示網站，而是 Decision OS：

```text
市場資料 → 訊號 → 證據 → Radar → 決策 → 行動
```

本版本的決策基準為波段操作，而非當沖或長期存股。

## Release 驗收

本版驗收重點：

1. Dashboard 是否有產品感，而不是工程頁面。
2. 介面是否全中文。
3. 個股是否能點擊查看技術線圖。
4. MACD 即將翻正十檔是否清楚可讀。
5. AI 評價是否像專業投資經理人，而非單純買賣訊號。
