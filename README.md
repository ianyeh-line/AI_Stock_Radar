# AI Stock Radar v3.6.1

AI 股市老師盤前決策系統。

## 本版重點

v3.6.1 修正 v3.6.0 今日可買名單仍過度模板化的問題，將今日可買、持股總教練、觀察清單統一改用更完整的股市老師分析邏輯。

## Run CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Run Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Upgrade

```bash
bash ~/Desktop/AI_Stock_Radar_v3.6.1_TeacherNarrativeFix_Product_Release/upgrade_to_repo.sh
```
