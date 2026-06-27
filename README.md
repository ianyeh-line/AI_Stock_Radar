# AI Stock Radar

AI Stock Radar 是一個以「每天早上 3 分鐘完成台股 AI 決策」為目標的投資決策產品。

本版是 **v0.8.0 Stage 4 Product Release**，重點是把產品從「Dashboard」升級為第一版 **Decision OS**：

```text
中文新聞
  ↓
市場訊號
  ↓
Knowledge Map
  ↓
新聞證據鏈
  ↓
技術面 Radar
  ↓
風險控管
  ↓
Decision Card
  ↓
中文 Dashboard + 每日報告
```

## 本版重點

- 介面全面中文化。
- 新聞在產品頁面以中文呈現。
- 新增個股技術線圖頁面。
- 所有提到個股的位置都提供「線圖」按鈕，可切換到個股技術線圖。
- 新增 Technical Radar：價格、20 日均線、60 日均線、RSI、技術分數。
- Decision Card 分數拆解為：新聞分數、技術分數、風險分數。
- CLI 與 Streamlit Dashboard 均可執行。

## 執行 CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

成功後會產生：

```text
output/daily_report.md
output/dashboard_data.json
```

## 啟動 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

瀏覽器打開：

```text
http://localhost:8501
```

## 驗收重點

1. 頁面是否全中文。
2. 新聞是否以中文決策語言呈現。
3. 點擊任一個股的「線圖」按鈕後，是否可在「個股技術線圖」頁看到該股線圖。
4. Decision Card 是否顯示新聞分數、技術分數、風險分數。
5. 是否能在 3 分鐘內知道今日應該買進、觀察、等待或賣出哪些股票。

## Git Commit

驗收成功後：

```bash
git add .
git commit -m "Release v0.8.0 Stage 4 Decision OS"
git push
```

## 免責聲明

AI Stock Radar 是投資決策支援工具，不是投資建議或保證獲利系統。所有輸出僅供研究與決策輔助使用。
