# AI Stock Radar v3.11.1

AI 股市老師決策工具。

v3.11.1 的重點是 **Action Precision + MACD Restore + Chip Quiet Mode**。

本版不新增大量頁面，專注修正三件事：

1. **無數字不建議**：進場、續抱、加碼、減碼、停損、觀察，都必須包含具體價格或區間。
2. **籌碼安靜模式**：若法人 / 籌碼資料未取得，只顯示「未取得」，不再用長篇模板或量能假裝籌碼。
3. **恢復 0 軸轉強雷達**：重新強化 MACD/DIF 從 0 軸下方即將翻正或剛翻正的觀察名單。

## 安裝 / 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.11.1_ActionPrecision_MACDRestore_Product_Release/upgrade_to_repo.sh
```

## 產生決策資料

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
```

## 啟動 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.11.1 Action Precision and MACD Restore"
git push
```
