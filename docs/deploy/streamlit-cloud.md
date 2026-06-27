# Streamlit Cloud Deploy Guide

## 目標

把 AI Stock Radar 部署成一個朋友可以直接打開的網址。

## 準備

GitHub Repository 必須包含：

```text
app.py
requirements.txt
.streamlit/config.toml
packages.txt
src/
data/demo/dashboard_data.json
```

## Streamlit Cloud 設定

在 Streamlit Community Cloud 建立 App 時：

```text
Repository: ianyeh-line/AI_Stock_Radar
Branch: main
Main file path: app.py
```

## 分享方式

部署成功後，會得到類似：

```text
https://your-app-name.streamlit.app
```

朋友只要打開網址即可使用。

## 使用模式

### 雲端：Guest Demo Mode

- 觀察清單與持股只保留在當次瀏覽 session。
- 不寫入共享伺服器檔案。
- 避免不同朋友看到彼此持股資料。

### 本機：Persistent Mode

- Ian 本機仍會使用 `~/.ai_stock_radar/` 保存個人持股與觀察清單。

## 版本更新

每次更新產品後：

```bash
git add .
git commit -m "Release vx.x.x"
git push
```

Streamlit Cloud 會依 GitHub main branch 更新。

## 注意

Web Beta 不是商業化產品，也不是投資保證。它是協助投資人縮短研究時間的盤前決策輔助工具。
