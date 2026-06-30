# AI Stock Radar v3.5.3

AI Stock Radar 是一個「AI 股市老師」盤前決策工具，目標是協助投資人用更少時間完成台股波段決策。

## v3.5.3 重點

本版是 **Data Freshness Rule Update**：

- 價格資料採用最新可得資料，不論來源是 TWSE / TPEx 官方資料或 Yahoo Finance。
- Yahoo Finance 會優先使用最新日線與最新報價資訊，避免官方盤後尚未更新時使用舊資料。
- 若官方資料較新且價格合理，仍採用官方盤後快照確認最新價。
- 盤前接受前一交易日收盤資料；盤中接受當日盤中最新資料；盤後接受當日最新可得資料；假日接受最近交易日資料。
- 只要資料符合目前交易狀態，不因來源是 Yahoo 或官方而降等。
- 只有資料真正過舊、fallback、缺失或樣本不足時才降級推薦。
- 新增持股 / 觀察清單改成表單流程，輸入股號、股數、成本時不會先抓資料，只有按下加入後才抓取與更新。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.5.3_DataFreshness_InputFlow_Hotfix/upgrade_to_repo.sh
```
