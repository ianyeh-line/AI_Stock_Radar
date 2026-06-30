# AI Stock Radar v3.3.0

本版聚焦三件事：

1. 線上版用戶輸入 Email + 自訂存取碼後，直接載入雲端持股與觀察清單，不需要再按「重新產生今日決策資料」。
2. 個人持股分析加入今日最新可得股價，並使用台股慣例：漲紅、跌綠。
3. MACD 觀察整合為「0 軸 MACD 轉強」：只看 DIF 從 0 軸下方即將翻正或剛翻正，資料不可信時不推薦。

## 執行

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.3.0_DataTrust_MACDUnified_Product_Release/upgrade_to_repo.sh
```

## 驗收重點

- 線上版輸入同一組 Email + 自訂存取碼後，持股與觀察清單應直接載入。
- 個人持股分析應顯示今日最新可得價與漲跌顏色。
- MACD 觀察頁只應顯示「即將從 0 軸翻正」或「剛從 0 軸翻正」且資料可信的股票。
- 個股技術線圖在 1 個月 / 3 個月 / 6 個月 / 1 年區間都應顯示 MACD/DIF/DEA。
