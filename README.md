# AI Stock Radar v3.5.2

AI Stock Radar 是一個「AI 股市老師」盤前決策工具，目標是協助投資人用更少時間完成台股波段決策。

## v3.5.2 重點

本版是 **Data Freshness and Input Flow Hotfix**：

- 價格資料採用最新可得資料，不論來源是 TWSE / TPEx 官方資料或 Yahoo Finance。
- Yahoo Finance 會優先使用最新日線與最新報價資訊，避免官方盤後尚未更新時使用舊資料。
- 若官方資料較新且價格合理，仍採用官方盤後快照確認最新價。
- 若資料過舊、fallback 或樣本不足，降級推薦，不給強買進。
- 新增持股 / 觀察清單改成表單流程，輸入股號、股數、成本時不會先抓資料，只有按下加入後才抓取與更新。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.5.2_DataFreshness_InputFlow_Hotfix/upgrade_to_repo.sh
```
