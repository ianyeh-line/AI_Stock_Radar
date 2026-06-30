# AI Stock Radar v3.2.4

本版修正線上版操作體驗與技術線圖問題。

## 修正內容

- 測試 Supabase 連線後，停留在「Supabase設定」頁，不再跳回首頁。
- 重新產生今日決策資料後，停留在使用者原本所在功能頁。
- 個股技術線圖切到「1個月」時，MACD/DIF/DEA 仍會顯示。
- MACD 以完整歷史資料計算，再依使用者選擇的區間顯示，避免短區間樣本不足。

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.2.4_UXState_MACDChart_Hotfix/upgrade_to_repo.sh
```

## 執行

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```
