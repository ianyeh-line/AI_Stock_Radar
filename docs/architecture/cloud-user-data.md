# Cloud User Data Architecture

AI Stock Radar now supports three storage modes:

```text
Local Mac Mode
  ~/.ai_stock_radar/portfolio.json
  ~/.ai_stock_radar/user_watchlist.json

Web Guest Mode
  Streamlit session_state only

Web Login Mode
  Google Login email
        ↓
  Supabase user_profiles table
        ↓
  watchlist / portfolio JSONB
```

The app never stores personal data in GitHub.

## Why Supabase

- Simple Postgres data model.
- REST API support.
- Free tier is enough for early beta.
- Easy to migrate later to a formal backend.

## Why not browser local storage

Browser local storage is faster to implement, but it does not solve cross-device
usage and is fragile for beta testers. Cloud portfolio storage is the correct
foundation.
