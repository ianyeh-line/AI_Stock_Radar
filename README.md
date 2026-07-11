# AI Stock Radar v3.10.0

## Daily Decision Loop

這版目標不是新增更多頁籤，而是把 AI Stock Radar 從「產生一次建議」升級成每天可循環使用的股市老師流程：

```text
盤前計畫 → 盤中觀察 → 盤後檢討 → 明日準備
```

## 本版重點

- 新增「決策閉環」首頁。
- 依交易狀態切換老師任務：盤前、盤中、盤後、非交易日。
- 新增前次推薦檢討：若本機已有前次 journal，會比較前次推薦與本次股價。
- 新增 AI 沒選到強勢股的原因。
- 新增明日接力與等待突破準備清單。
- 新增持股策略是否改變。
- 每次 CLI / Dashboard 產生資料時會建立 runtime decision journal。
- `data/journal/` 已加入 `.gitignore`，不會提交個人決策歷史。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.10.0_DailyDecisionLoop/upgrade_to_repo.sh
```

## 驗收重點

- 首頁第一個功能應為「決策閉環」。
- 盤前 / 盤中 / 盤後 / 非交易日應顯示不同老師任務。
- 每日報告應新增「決策閉環」段落。
- 第一次執行若沒有前次紀錄，應說明會建立基準。
- 第二次以後應可讀取 `data/journal/` 做推薦檢討。
- 今日可買、強勢股、持股建議仍保留 v3.9.0 Decision Quality Gate。
