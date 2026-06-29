# AI Stock Radar v3.2.0

AI 股市老師：盤前決策、個人持股教練、資料可信度防呆、MACD 0 軸觀察與 Web Beta Access。

## v3.2.0 重點

- 資料可信度 Guardrails：fallback、舊資料、樣本不足時不給 A 級買進。
- 修正 MACD 0 軸判斷：MACD/DIF 已在 0 軸上方時，不會再顯示 0 軸下方偏弱。
- 個股技術圖表升級：K 線、MA、成交量、MACD/DIF、DEA、柱狀體、RSI/KD/BIAS 摘要。
- 恢復 Web Beta Access：朋友用 Email + 自訂存取碼，可在 Supabase 設定後保存個人持股與觀察清單。
- 保留動態新增清單外個股能力。

## 本機執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 安裝 / 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.2.0_DataTrust_BetaAccess_Product_Release/upgrade_to_repo.sh
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.2.0 Data Trust and Beta Access"
git push
```
