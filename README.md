# AI Stock Radar v3.11.2

**Version Integrity + Report Sync Hotfix**

這版目標只有一件事：確保 App、CLI、Dashboard payload、每日報告全部使用同一個版本來源，避免線上頁面出現「上方是新版、每日報告卻是舊版」的情況。

## 本版修正

- 新增 `src/radar/version.py` 作為唯一版本來源。
- `app.py`、`cli.py`、每日報告、payload 全部共用同一版本。
- 舊版 `output/dashboard_data.json` 不再被新版 App 使用。
- 舊版 `output/daily_report.md` 不再被新版 App 顯示。
- 升級腳本會自動清除舊 runtime output。
- 新增版本一致性 regression tests。

## 安裝

```bash
bash ~/Desktop/AI_Stock_Radar_v3.11.2_VersionIntegrity_ReportSync_Hotfix/upgrade_to_repo.sh
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
git commit -m "Release v3.11.2 Version Integrity and Report Sync"
git push
```

## 驗收重點

- App 標題版本應為 `3.11.2`。
- 每日報告標題版本也應為 `3.11.2`。
- 若安裝前本機或線上曾產生舊版 report，升級後不應再顯示舊版內容。
- 若 `dashboard_data.json` 是舊版本，App 應自動重新產生。
