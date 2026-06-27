# Release v2.4.0 - User Account + Cloud Portfolio

## Summary

This release turns Web Beta into a user-account capable testing environment.
Friends can log in with Google and save their personal watchlist and portfolio
in Supabase, so they do not need to re-enter holdings every time.

## Added

- Streamlit OIDC / Google Login readiness.
- Supabase REST-backed user profile persistence.
- Cloud portfolio and watchlist storage by user email.
- Guest Mode remains available for anonymous visitors.
- Local Mac mode still stores data under `~/.ai_stock_radar/`.
- Deployment guide and SQL schema for Supabase.

## Notes

- No real secrets are committed.
- Streamlit Cloud Secrets must be configured before Google Login and Supabase storage work.
- Without secrets, the app safely falls back to Guest Mode.
