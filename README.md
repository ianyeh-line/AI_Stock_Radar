# AI Stock Radar

AI Stock Radar 是一個協助台股投資人縮短盤前決策時間的本機工具。

目前定位：**AI 股市老師盤前決策系統**。

## v2.2.3 重點

### User Data Persistence Hotfix

本版修正版本更新時可能覆蓋個人資料的問題。

個人資料包含：

- 個人持股：`portfolio.json`
- 個人觀察清單：`user_watchlist.json`

從 v2.2.3 起，系統會把個人資料保存到 Mac 使用者資料夾：

```text
~/.ai_stock_radar/
├── portfolio.json
└── user_watchlist.json
```

這樣之後更新 Release 時，即使覆蓋 `Desktop/AI_Stock_Radar`，個人持股與觀察清單也不需要重新輸入。

### 自動遷移

如果你之前已有：

```text
config/portfolio.json
config/user_watchlist.json
```

v2.2.3 第一次執行時會自動搬移到：

```text
~/.ai_stock_radar/
```

## 建議升級方式

解壓縮後，不要用 Finder 手動全部取代。請用本版附的安全升級腳本：

```bash
bash ~/Desktop/AI_Stock_Radar_v2.2.3_UserDataPersistence_Hotfix/upgrade_to_repo.sh
```

如果你的 Repository 不在桌面，可以指定路徑：

```bash
bash ~/Desktop/AI_Stock_Radar_v2.2.3_UserDataPersistence_Hotfix/upgrade_to_repo.sh ~/Desktop/AI_Stock_Radar
```

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## 開啟 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

瀏覽器開啟：

```text
http://localhost:8501
```

## 注意

本工具不是逐筆即時交易終端，也不是投資保證。它使用抓取當下可取得的日線價格、RSS 新聞與法人資料，產生波段操作輔助建議。
