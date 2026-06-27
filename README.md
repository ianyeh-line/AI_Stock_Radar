# AI Stock Radar

AI Stock Radar 是一個以「每天早上 3 分鐘完成台股 AI 決策」為目標的投資決策產品。

## v0.4.0 新增

- 接入第一版 RSS 真實新聞來源。
- 建立 News -> Knowledge -> Decision -> Report 的可執行流程。
- 加入 `.gitignore`，避免 `__pycache__`、`.DS_Store`、每日報告輸出被提交。
- 產出 `output/daily_report.md` 作為每日驗收報告。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## 預期輸出

```text
🚀 AI Stock Radar v0.4.0
News Source: RSS Live
Market View: 🟢 偏多
AI Confidence: xx%
Report generated: output/daily_report.md
```

若 RSS 暫時無法連線，系統會自動使用 fallback news，確保產品仍可執行。
