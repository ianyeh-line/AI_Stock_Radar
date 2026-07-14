# AI Stock Radar v3.12.0

AI 股市老師：台股盤前 / 盤中 / 盤後決策輔助系統。

## v3.12.0 重點

- Responsive Decision UX：電腦與手機都以「先看決策」為核心。
- 主畫面減少文字，資料來源與系統資訊預設收合到頁尾。
- 今日可操作、今日強勢、我的持股、個股研究、每日報告、設定六大頁面重新整理。
- 個股卡片改為「下一步優先」，完整股市老師分析與技術圖預設收合。
- 每日報告改為摘要優先，個股完整分析預設收合。

## 安裝

```bash
bash ~/Desktop/AI_Stock_Radar_v3.12.0_ResponsiveDecisionUX_Product_Release/upgrade_to_repo.sh
```

## 驗收

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.12.0 Responsive Decision UX"
git push
```
