# AI Stock Radar v3.0.1 Regression Hotfix

## Fixed

- Restored expanded Taiwan Stock Master from the v2.x line.
- Fixed user-entered holdings such as `南亞科` / `2408` not resolving correctly.
- Added regression tests for `2313 華通` and `2408 南亞科`.
- Removed runtime cache artifacts from the release package.

## Principle

Full releases must not drop validated capabilities from previous versions. Stock Master resolution is now part of regression testing.
