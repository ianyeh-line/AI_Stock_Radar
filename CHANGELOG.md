# Changelog

## v2.3.0 - Web Beta Ready

### Added

- 新增 Streamlit Cloud Web Beta 支援。
- 新增網站 Demo / Guest 模式，讓朋友可以直接用網址測試。
- 新增 Session-only watchlist / portfolio，避免雲端共用伺服器檔案造成使用者資料混用。
- 新增 `.streamlit/config.toml`。
- 新增 `packages.txt`。
- 新增 `data/demo/dashboard_data.json` 與 `data/demo/daily_report.md`，雲端第一次開頁可先載入 Demo payload。
- 新增 `docs/deploy/streamlit-cloud.md` 部署文件。

### Changed

- Dashboard 在雲端環境會優先使用 Guest Demo Mode。
- 本機使用仍保留 `~/.ai_stock_radar/` 個人持久資料。
- Dashboard 報告預覽支援 Session report，不再強制讀取共享 output 檔案。
- 版本號更新為 `2.3.0`。

### Fixed

- 避免公開網站上不同測試者共用同一份持股與觀察清單。
- 避免 Web Beta 第一次開頁一定要立刻重跑完整資料管線。
