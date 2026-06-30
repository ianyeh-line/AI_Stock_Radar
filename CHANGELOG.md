# CHANGELOG

## v3.4.0 - Official Data Source Upgrade

### Added
- Added `radar.core.official_data` for TWSE / TPEx OpenAPI latest daily close snapshots.
- Added official data confirmation to decision cards.
- Added data source summary to dashboard and daily report.
- Added teacher-style portfolio advice with concrete support, breakout, stop, and trim levels.

### Changed
- Latest displayed price is now labelled 「今日股價」 in portfolio analysis.
- Removed standalone 「資料可信度」 page from top navigation.
- Moved 「每日報告」 before 「持股總教練」.
- Data trust now explicitly distinguishes official-confirmed, Yahoo-only, and fallback data.

### Fixed
- Reduced risk of stale Yahoo-only latest price being treated as fully trusted.
