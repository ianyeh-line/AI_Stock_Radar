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
