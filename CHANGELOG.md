# CHANGELOG

## v1.0.0 - Investment Manager Release

### Added

- 新增投資經理人早會頁面。
- 新增今日資金配置建議。
- 新增 Top Actions 與 Avoid Actions。
- 新增 Decision Card 分數拆解。
- 新增 Thesis / Invalidation 條件。
- 新增 Data Quality Check，讓使用者知道資料可信度與限制。
- 新增更完整的 Markdown 報告章節。

### Changed

- 將產品主軸從「顯示 Radar」升級為「投資經理人式波段決策」。
- Radar Score 不再只是分數，改為由訊號、技術、風險與個人化偏好組成。
- Dashboard 首頁改成以「今天要怎麼做」為核心。

### Fixed

- 強化 Evidence 去重，避免同一訊號重複出現。
- 強化分數上限與風險懲罰，降低過度樂觀評分。
- 改善 CLI 輸出，使其更接近早會摘要。
