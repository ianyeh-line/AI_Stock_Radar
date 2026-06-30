# AI Stock Radar v3.5.0

AI Stock Radar 是一個「AI 股市老師」盤前 / 盤中 / 盤後決策輔助工具，目標是協助投資人在 3 分鐘內完成台股波段操作判斷。

## v3.5.0 重點

本版主軸是 **Data Source Truthfulness**：

- TWSE / TPEx 官方資料與 Yahoo Finance 比較日期。
- 採用較新的可得資料作為今日判斷基準。
- 若官方資料尚未更新，但 Yahoo 日期較新，會採用 Yahoo 並清楚標示。
- 若資料早於預期最新交易日、fallback 或樣本不足，系統會降級推薦，不給 A 級買進。
- 首頁、決策卡、每日報告都會顯示資料基準日與來源選擇原因。

## 本機執行

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.5.0_DataSourceTruthfulness_Product_Release/upgrade_to_repo.sh
```

## Commit

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.5.0 Data Source Truthfulness"
git push
```

## 投資提醒

本產品是投資決策輔助工具，不是保證獲利工具。所有推薦都應搭配個人風險承受度、資金控管與交易紀律。
