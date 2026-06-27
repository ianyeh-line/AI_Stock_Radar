# Changelog

## v2.2.2 - Action Logic Hotfix

### Fixed

- 修正進場/加碼語句的價格情境判斷。
- 若現價已經高於支撐觀察區，系統不再提示「需重新站回支撐價」。
- 針對「低於支撐 / 位於支撐區 / 高於支撐但未突破 / 已突破 / 明顯高於突破價」建立不同文字邏輯。
- 修正減碼/避開標的的解除條件，改為「放量突破壓力且 MACD 改善」，避免把低於現價的支撐價誤寫成重新站回條件。

### Added

- 新增測試：現價 1015、高於支撐 890～915、壓力 1160 時，不得產生「重新站回 915」這類不合理語句。

### Product Impact

- 個股建議更像股市老師的價格語境：現價在哪裡，就給出對應操作計畫。
- 避免使用者看到已經站上的價位卻被要求「重新站回」，降低誤解與錯誤決策風險。

## v2.2.1 - Refresh Hotfix

### Fixed

- Fixed Dashboard refresh hanging after adding portfolio/watchlist stocks.
- Added cache-first Yahoo Finance daily price loading.
- Added concurrent technical profile loading for the 100-stock universe.
- Reduced Yahoo network timeout and safely falls back to cached data before synthetic fallback.

## v2.2.0 - Data Integrity + AI Teacher Upgrade

### Fixed

- Fixed stale MACD latest-price risk by auto-resolving Yahoo Finance .TW / .TWO suffixes and selecting the freshest valid price series.
- MACD recommendation list excludes fallback and date-lagging price profiles.
- Fixed personal portfolio analysis visibility by rendering holdings from local config plus current payload.

### Added

- AI 股市老師總評：market posture, scenario playbook, data warning, focus list and teacher rules.
