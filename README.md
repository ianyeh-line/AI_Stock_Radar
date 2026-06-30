# AI Stock Radar v3.4.0

AI 股市老師盤前決策系統。

本版重點：**Data Source Upgrade**。價格資料改為「TWSE / TPEx 官方盤後資料優先確認最新價，Yahoo Finance 保留為歷史線圖與 fallback」。

## 本版新增

- TWSE OpenAPI 上市個股盤後收盤資料整合。
- TPEx OpenAPI 上櫃個股盤後收盤資料整合。
- Yahoo Finance 繼續提供歷史 OHLC 線圖與技術指標計算。
- 若官方資料取得失敗，系統會清楚標示 Yahoo Only / fallback，不會默默當成高可信推薦。
- 個人持股分析欄位由「今日最新可得價」改為「今日股價」。
- 持股總教練建議加長，加入老師式續抱、加碼、減碼、失效條件與組合曝險說明。
- 移除獨立「資料可信度」功能頁；資料可信度改回到每張決策卡與每日報告中呈現。
- 「每日報告」頁籤移到「持股總教練」前面。

## 本機執行

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Web Beta

Streamlit Cloud 部署仍使用：

```text
app.py
requirements.txt
.streamlit/config.toml
```

Supabase 仍可保存朋友的 Email + 自訂存取碼對應的觀察清單與個人持股。

## 資料來源定位

- TWSE / TPEx：最新官方盤後收盤資料確認。
- Yahoo Finance：歷史日線、技術線圖、fallback。
- 若官方資料缺失，AI Stock Radar 會降低推薦可信度。
