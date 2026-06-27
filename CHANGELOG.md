# Changelog

## v2.1.0 Phase 5 MVP

### Added

- Data Trust Engine：價格資料、法人資料、樣本數與 fallback 狀態檢查。
- Recommendation Guardrails：A 級推薦必須通過資料、技術風險、法人籌碼與價格位置檢查。
- Lightweight Backtest：以近一年相似技術訊號驗證 20 交易日後勝率、平均報酬與最大回撤。
- Portfolio Coach Phase 5：新增資金政策、核心續抱、可加碼候選、減碼候選、題材集中度。
- Dashboard 新增「資料可信度」與「歷史回測驗證」頁面。
- 每日報告新增 Phase 5 資料可信度、Guardrails 與回測摘要。

### Changed

- A 級今日可買進名單不再只依 Radar Score，會被 Guardrails 自動降級或禁止。
- Teacher Buy List 顯示 Guardrail 狀態與回測勝率。

### Fixed

- 避免資料不足、價格 fallback 或法人明顯偏空時仍給 A 級買進。
