# CHANGELOG

## v3.2.1 - Trading Status + Supabase Setup Hotfix

### Fixed
- 修正 Streamlit Cloud 使用 UTC 導致台灣盤後誤判為盤中的問題。
- 市場結論改為可換行卡片，不再被 metric 元件截斷。
- 持股總教練頁不再重跑完整 pipeline，改善頁面反應。

### Added
- 新增 Supabase 設定助手頁籤。
- 新增 `docs/deploy/supabase-beginner-guide.md`。
- 新增 `docs/deploy/supabase-schema.sql`。
- 新增 `.streamlit/secrets.example.toml`。
- 新增台灣交易狀態 regression tests。

## v3.2.2 - Cloud Persistence Hotfix

### Fixed
- Fixed false success messaging when online portfolio/watchlist data was not saved to Supabase.
- Added Supabase connection and permission diagnostics.
- Added warning when a public/publishable Supabase key is used instead of service_role/secret key.
- Added explicit UI feedback for cloud save failures.

### Improved
- Cloud save failures are preserved in session for the current browser, preventing immediate data loss during setup.
