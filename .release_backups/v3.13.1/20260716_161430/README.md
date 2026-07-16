# AI Stock Radar v3.13.1

AI 股市老師：台股盤前 / 盤中 / 盤後決策輔助系統。

## v3.13.1 重點

- 以 v3.12.0 完整程式碼為基底重新交付，保留 CLI、股市老師、今日強勢、我的持股、個股研究、每日報告、設定、Supabase 設定頁、技術圖與測試。
- 修正「今天怎麼做」錯誤文案，改成使用者可執行的三個任務。
- 主畫面按鈕改為「更新今日資料」。
- Hero 與 KPI 改為決策導向文案，不再把版本說明、資料工程說明塞進主畫面。
- 新增「今日優先清單」，先看股票層級決策，再展開個股卡片。
- 保留資料來源、更新狀態與系統資訊於頁尾收合區。

## 安裝

```bash
bash ~/Desktop/AI_Stock_Radar_v3.13.1_DecisionFirstSafePatch_Product_Release/upgrade_to_repo.sh
```

或指定 repo：

```bash
bash ~/Desktop/AI_Stock_Radar_v3.13.1_DecisionFirstSafePatch_Product_Release/upgrade_to_repo.sh ~/Desktop/AI_Stock_Radar
```

## 驗收

```bash
cd ~/Desktop/AI_Stock_Radar
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 scripts/validate_decision_first_safepatch.py
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.13.1 Decision-first SafePatch"
git push
```
