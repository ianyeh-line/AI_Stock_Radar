# CHANGELOG

## v2.4.0 - User Account + Cloud Portfolio

### Added

- Streamlit OIDC / Google Login readiness.
- Supabase REST-backed cloud user profile storage.
- Cloud persistence for personal watchlist and portfolio.
- Guest Mode remains available when login/secrets are not configured.
- Cloud account panel in sidebar.
- Supabase schema and deployment guide.
- Streamlit secrets example.

### Changed

- Web users can now move from temporary Guest Mode to persistent Login Mode.
- User-specific generated payloads stay in session and are not written to shared server output.
- Version updated to `2.4.0`.

### Security

- No secrets are committed.
- Personal data is stored outside GitHub.
- Supabase key must be configured through Streamlit Secrets only.

## v2.3.2 - Streamlit Import Path Hotfix

- Fixed Streamlit Cloud import path for `src/radar` package.

## v2.3.1 - Streamlit Deploy Hotfix

- Removed invalid `packages.txt` to fix Cloud apt dependency installation.

## v2.3.0 - Web Beta Ready

- Added Streamlit Cloud deployment readiness and Guest Mode.
