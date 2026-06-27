# AI Stock Radar

AI Stock Radar 是一個以「每天早上 3 分鐘完成台股波段決策」為目標的 AI 投資決策產品。

## v1.0.0 重點

本版從 Stage 5 升級為 **Investment Manager Release**：產品不只列出分數，而是以專業投資經理人的方式輸出早會結論、部位建議、分數拆解、失效條件與風險控管。

## 核心能力

- 中文 Dashboard
- 中文新聞摘要
- 投資經理人早會摘要
- Top Decision Cards
- Radar Score 分數拆解
- Evidence Chain
- 波段操作建議
- MACD 即將翻正十檔
- 個股技術線圖
- 新聞 → 訊號 → 個股影響
- Markdown 每日報告

## 執行 CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

產出：

```text
output/daily_report.md
output/dashboard_data.json
```

## 開啟 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

打開：

```text
http://localhost:8501
```

## 產品定位

AI Stock Radar 不是股價預測工具，而是投資決策輔助系統。每個建議都必須說明：

1. 為什麼現在值得看？
2. 分數怎麼來？
3. 何時進場？
4. 何時續抱？
5. 何時減碼或放棄？

## 注意事項

目前仍屬 Beta / MVP 階段。輸出內容僅供研究與決策輔助，不構成投資建議。
