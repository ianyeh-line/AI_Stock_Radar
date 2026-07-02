# AI Stock Radar v3.9.0

## Decision Quality Gate

這版目標不是新增更多頁面，而是讓 AI Stock Radar 的推薦更可靠、更像股市老師。

v3.9.0 新增推薦前置檢查：每一檔股票要進入「今日可買」前，必須先通過價格可執行性、資料有效性、量能與過熱風險檢查。

## 本版重點

- 今日可買不再只看分數，必須通過 Decision Quality Gate。
- 若現價已高於拉回買點且尚未有效突破，不再列 A 級可買。
- 若已突破，老師語句會改成「已突破，觀察是否站穩」，不再寫「若突破」。
- 今日可買與持股總教練共用股市老師敘事邏輯。
- 資料來源退到頁尾，不再干擾主要決策。
- 推薦理由避免資料來源口號，聚焦技術、量能、價格位置、籌碼資料限制、產業消息與操作劇本。
- 新增 regression tests，防止舊錯誤再次回歸。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.9.0_DecisionQualityGate/upgrade_to_repo.sh
```

## 驗收重點

- 今日可買名單的老師建議是否像持股總教練一樣完整。
- 若股價已高於買進區，不應再建議在較低買進區分批。
- 若股價已突破，不應再寫「若突破」。
- 資料來源說明應在頁尾或折疊區，不應出現在推薦理由。
- 強勢股雷達仍應區分可追、已漲不追、明日接力。
