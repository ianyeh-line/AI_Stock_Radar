# Release v3.2.4 - UX State and MACD Chart Hotfix

## Goal

Fix Web Beta persistence issues where a user could add portfolio/watchlist items in the UI, but the data was not actually saved to Supabase and disappeared after page refresh.

## Changes

- Added visible Supabase connection and permission diagnostics.
- Added explicit save success/failure feedback for portfolio and watchlist writes.
- Prevented false success messages when Supabase write fails.
- Added support for common Streamlit Secrets key names: `service_role_key`, `secret_key`, `sb_secret_key`, `key`.
- Detects public / publishable Supabase keys and warns users to use service_role / secret key.
- Keeps failed cloud writes in the current browser session so the user does not immediately lose data.
- Added a Dashboard Supabase test button.

## Validation

- CLI smoke run verified.
- Python compile check verified.

## Notes

For cloud persistence, Streamlit Secrets must include:

```toml
[supabase]
url = "https://your-project.supabase.co"
service_role_key = "your service_role or secret key"
table = "user_profiles"
```

Do not use the anon / publishable key for this Beta persistence flow when RLS is enabled.
