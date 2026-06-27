# AI Stock Radar

AI Stock Radar 是一個協助台股投資人縮短盤前決策時間的 AI 股市老師工具。

目前定位：**每天早上 3 分鐘，直接看到今日可買、等待、避開與持股管理建議。**

## v2.3.2 Streamlit Import Path Hotfix

修正 Streamlit Cloud 上 `ModuleNotFoundError: No module named radar` / `radar.engine.decision` 的部署問題。

本版修正 Streamlit Cloud 部署時的 `packages.txt` apt 安裝錯誤，讓 Web Beta 可以正常完成 dependency installation。

### 本版新增

- Streamlit Cloud Web Beta 支援
- 網站 Demo / Guest 模式
- 訪客觀察清單與持股資料只存在同一次瀏覽 Session，不寫入共享伺服器檔案
- 本機模式仍保留 `~/.ai_stock_radar/` 的個人持股與觀察清單
- 新增 `.streamlit/config.toml`
- 移除不需要的 `packages.txt`，避免 Streamlit Cloud 把註解文字當作 apt 套件安裝。
- 新增 `data/demo/dashboard_data.json`，讓雲端第一次開頁更快
- 新增 Streamlit Cloud 部署文件

## 本機執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

開啟 Dashboard：

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

瀏覽器開啟：

```text
http://localhost:8501
```

## 部署到 Streamlit Cloud

請參考：

```text
docs/deploy/streamlit-cloud.md
```

部署後，朋友只需要打開網址，不需要安裝 Python、VS Code 或下載檔案。

## 使用模式

### 本機模式

適合 Ian 自己使用。

個人資料保存在：

```text
~/.ai_stock_radar/
├── portfolio.json
└── user_watchlist.json
```

### 網站 Demo 模式

適合分享給朋友測試。

- 每位訪客的觀察清單與持股資料只存在該次瀏覽 Session
- 不保證永久保存
- 不會寫入共享伺服器檔案
- 避免朋友之間看到彼此的持股資料

## 升級方式

解壓縮後，建議使用安全升級腳本：

```bash
bash ~/Desktop/AI_Stock_Radar_v2.3.0_WebBeta_Product_Release/upgrade_to_repo.sh
```

如果你的 Repository 不在桌面，可以指定路徑：

```bash
bash ~/Desktop/AI_Stock_Radar_v2.3.0_WebBeta_Product_Release/upgrade_to_repo.sh ~/Desktop/AI_Stock_Radar
```

## 注意

本工具不是逐筆即時交易終端，也不是投資保證。它使用抓取當下可取得的日線價格、RSS 新聞、法人資料與技術指標，產生波段操作輔助建議。
