# Changelog

## v2.2.3 - User Data Persistence Hotfix

### Fixed

- 修正版本更新時個人持股與指定觀察清單可能被覆蓋的問題。
- 個人資料從 repo-local `config/*.json` 移到 durable storage：`~/.ai_stock_radar/`。
- 第一次執行會自動遷移舊版 `config/portfolio.json` 與 `config/user_watchlist.json`。
- 新增安全升級腳本 `upgrade_to_repo.sh`，更新版本時會備份並保留個人資料。

### Added

- Dashboard 側邊欄顯示個人資料保存位置。
- README 新增安全升級流程。
- Release Notes 新增個人資料保護說明。

### Product Impact

- 使用者更新 AI Stock Radar 版本後，不需要重新輸入個人持股與觀察清單。
- 後續 Release 可更放心覆蓋產品檔案，個人資料與產品程式分離。

## v2.2.2 - Action Logic Hotfix

### Fixed

- 修正進場/加碼語句的價格情境判斷。
- 若現價已經高於支撐觀察區，系統不再提示「需重新站回支撐價」。
- 針對「低於支撐 / 位於支撐區 / 高於支撐但未突破 / 已突破 / 明顯高於突破價」建立不同文字邏輯。

## v2.2.1 - Refresh Hotfix

### Fixed

- Fixed Dashboard refresh hanging after adding portfolio/watchlist stocks.
- Added cache-first Yahoo Finance daily price loading.
- Added concurrent technical profile loading for the 100-stock universe.

## v2.2.0 - Data Integrity + AI Teacher Upgrade

### Fixed

- Fixed stale MACD latest-price risk by auto-resolving Yahoo Finance .TW / .TWO suffixes and selecting the freshest valid price series.
- MACD recommendation list excludes fallback and date-lagging price profiles.
- Fixed personal portfolio analysis visibility by rendering holdings from local config plus current payload.
