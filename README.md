# AI Stock Radar v3.8.0

AI 股市老師盤前 / 盤後決策系統。

## 本版重點：全市場強勢股雷達 v2

v3.8.0 修正 v3.7.0 的核心問題：上一版只是把既有 AI 股票池做強勢分類，沒有真正建立全市場漲幅、成交量、成交值與接近漲停掃描。

本版改為：

1. 先掃描 TWSE / TPEx 全市場快照。
2. 建立全市場漲幅排行、成交量排行、成交值排行、接近漲停名單。
3. 從強勢股中補技術分析，判斷哪些「可追」、哪些「已漲不追」、哪些適合「明日接力觀察」。
4. 今日可買與今日強勢分開顯示。

## Run CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Run Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Upgrade

```bash
bash ~/Desktop/AI_Stock_Radar_v3.8.0_MarketStrength_Product_Release/upgrade_to_repo.sh
```
