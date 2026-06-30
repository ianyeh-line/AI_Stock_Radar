# CHANGELOG

## v3.2.3 - Supabase Secrets Hotfix

### Fixed
- 修正 Streamlit Secrets 常見誤填造成的 Supabase `PGRST125 Invalid path specified in request URL` 問題。
- 自動把 `https://xxxx.supabase.co/rest/v1` 修正成 `https://xxxx.supabase.co`。
- 自動把 `public.user_profiles` 修正成 `user_profiles`。
- Supabase 連線測試會明確提示 URL 與 table 的正確格式。

### Added
- Regression tests for Supabase URL and table name normalization.

### Notes
- Streamlit Secrets 建議格式：

```toml
[supabase]
url = "https://你的專案.supabase.co"
service_role_key = "你的 service_role 或 secret key"
table = "user_profiles"
```
