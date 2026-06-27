# Release v1.4.0 - PM Precision Action Upgrade

## Goal

將 AI Stock Radar 從「方向判斷」提升為「具體操作計畫」。

## Delivered

- 今日主策略給出推薦個股。
- 今日優先動作加入突破價、拉回區間與減碼價。
- 今日決策卡加入完整操作價位表。
- 進場、續抱、減碼、失效條件皆提供具體數字。
- 量能比新增解釋，讓使用者知道 1.07 等數字代表什麼。
- Data Quality Check 明確標示資料即時性與決策維度。

## Acceptance

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

Dashboard 應能看到：主策略推薦個股、具體價位、量能比說明與資料限制。
