# AI Stock Radar v3.5.1

AI Stock Radar 是一個「AI 股市老師」盤前 / 盤中 / 盤後決策輔助工具，目標是協助投資人在 3 分鐘內完成台股波段操作判斷。

## v3.5.1 重點

本版是 **Data Source Reliability Hotfix**，直接修正 v3.5.0 線上版問題：

- 修正版本號不一致：App 與 payload 版本不一致時會自動重算，不再沿用舊版快取。
- 修正官方快照價格異常造成持股估值與線圖失真的問題。
- 官方資料若與 Yahoo 最新價格差異超過合理範圍，會改採 Yahoo 並清楚標示。
- 個股線圖會先清理異常日期與非數字價格，再繪製 K 線 / MACD，避免圖表失效。
- 持股總教練若資料可信度不足，會改為「僅能觀察」，不再同時出現加碼與觀察矛盾語句。
- 今日股價顯示維持台股邏輯：漲紅、跌綠、平盤灰色。

## 本機執行

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.5.1_DataSourceReliability_Hotfix/upgrade_to_repo.sh
```

## Commit

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.5.1 Data Source Reliability Hotfix"
git push
```

## 投資提醒

本產品是投資決策輔助工具，不是保證獲利工具。所有推薦都應搭配個人風險承受度、資金控管與交易紀律。
