# Changelog

## v0.8.0 - Stage 4 Decision OS

### Added

- 新增全中文 Dashboard 介面。
- 新增中文新聞呈現層，RSS 新聞會轉為中文決策語言。
- 新增 Technical Radar：價格、20 日均線、60 日均線、RSI、技術分數。
- 新增個股技術線圖頁面。
- 新增所有個股提及處的「線圖」按鈕，可快速切換查看技術線圖。
- 新增 Decision Card 分數拆解：新聞分數、技術分數、風險分數。
- 新增 Stage 4 Decision OS 架構文件。

### Changed

- Dashboard tab 全面中文化：今日總覽、新聞影響鏈、個股技術線圖、風險控管、每日報告。
- Daily Report 改為中文格式。
- CLI 輸出改為中文。
- Decision Engine 從純新聞分數升級為 News + Technical + Risk 整合。

### Fixed

- 避免 Decision Card 只因單一新聞主線而過度高分。
- 新聞與 Evidence 顯示改為中文，降低閱讀成本。
- Dashboard 不再只是一張表，而是可互動的決策頁。
