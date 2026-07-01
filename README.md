# AI Stock Radar v3.8.2

## Market Strength Reliability Fix

這版修正強勢股雷達資料連接器：不再只是顯示「未取得全市場強勢資料」，而是清楚列出 TWSE / TPEx / Yahoo 每個資料來源的抓取與解析狀態。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.8.2_MarketStrengthReliability_Fix/upgrade_to_repo.sh
```

## 驗收

- 打開「強勢股雷達」。
- 若有資料，應看到市場掃描筆數、官方解析筆數、Yahoo 補充筆數。
- 若沒有資料，打開「資料抓取診斷」確認每個 endpoint 的錯誤或欄位解析狀態。
