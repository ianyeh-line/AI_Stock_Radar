# Release v3.2.3 - Supabase Secrets Hotfix

## Purpose

Fix Web Beta cloud persistence setup when Streamlit Secrets contains common Supabase values copied from the UI.

## Key Fixes

- Normalize Project URL copied as Data API endpoint.
- Normalize table copied as `public.user_profiles`.
- Improve diagnostics for PGRST125 invalid path errors.
- Keep all user portfolio/watchlist persistence behavior from v3.2.2.

## Validation

- CLI smoke test passes.
- Regression tests pass.
