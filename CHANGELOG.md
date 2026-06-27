# CHANGELOG

## v0.5.0

### Added

- Added Explainable Decision Cards.
- Added evidence scoring by stock.
- Added stock-level reason, confidence, and action.
- Added Decision Card rendering in `output/daily_report.md`.
- Added news count and source visibility.

### Changed

- Upgraded report from simple ranking to decision-first output.
- Improved CLI output to show top-level decision reasons.
- Refined scoring logic to avoid unexplained Buy/Sell outputs.

### Fixed

- Reduced black-box scoring behavior.
- Improved product value by making each stock decision explainable.
