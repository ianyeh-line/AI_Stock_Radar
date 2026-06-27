"""Cloud user portfolio/watchlist storage via Supabase REST API.

This module intentionally uses only `requests` so the app remains simple on
Streamlit Community Cloud. Secrets must be configured in Streamlit Cloud, never
committed to GitHub.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import requests

TABLE_NAME = "user_profiles"
TIMEOUT_SECONDS = 12


def _streamlit() -> Any | None:
    try:
        import streamlit as st  # type: ignore

        return st
    except Exception:
        return None


def _secret_value(*paths: str) -> str:
    st = _streamlit()
    if st is None:
        return ""
    try:
        value: Any = st.secrets
        for path in paths:
            value = value[path]
        return str(value or "").strip()
    except Exception:
        return ""


def supabase_config() -> dict[str, str]:
    """Return Supabase REST config from Streamlit secrets.

    Supported secrets format:

    [supabase]
    url = "https://xxxx.supabase.co"
    service_role_key = "..."

    `anon_key` is also accepted for development, but service_role_key is
    recommended for this beta because all DB writes happen server-side in
    Streamlit Cloud.
    """
    url = _secret_value("supabase", "url").rstrip("/")
    key = (
        _secret_value("supabase", "service_role_key")
        or _secret_value("supabase", "key")
        or _secret_value("supabase", "anon_key")
    )
    table = _secret_value("supabase", "table") or TABLE_NAME
    return {"url": url, "key": key, "table": table}


def is_cloud_store_configured() -> bool:
    cfg = supabase_config()
    return bool(cfg["url"] and cfg["key"])


def cloud_status() -> dict[str, str]:
    cfg = supabase_config()
    if not cfg["url"]:
        status = "未設定 Supabase URL"
    elif not cfg["key"]:
        status = "未設定 Supabase Key"
    else:
        status = "已設定"
    return {"status": status, "url": cfg["url"], "table": cfg["table"]}


def _headers() -> dict[str, str]:
    cfg = supabase_config()
    key = cfg["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    cfg = supabase_config()
    return f"{cfg['url']}/rest/v1/{cfg['table']}"


def _empty_profile(email: str) -> dict[str, Any]:
    return {"user_email": email, "watchlist": [], "portfolio": []}


def load_user_profile(email: str) -> dict[str, Any]:
    """Load a user's profile from Supabase.

    Returns an empty profile when cloud storage is not configured or when the
    user has no row yet. Network errors are swallowed so the Dashboard can stay
    usable in Guest Mode.
    """
    email = (email or "").strip().lower()
    if not email or not is_cloud_store_configured():
        return _empty_profile(email)
    url = f"{_base_url()}?user_email=eq.{quote(email)}&select=user_email,watchlist,portfolio"
    try:
        response = requests.get(url, headers=_headers(), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        rows = response.json()
        if rows:
            row = rows[0]
            return {
                "user_email": email,
                "watchlist": row.get("watchlist") or [],
                "portfolio": row.get("portfolio") or [],
            }
    except Exception:
        return _empty_profile(email)
    return _empty_profile(email)


def save_user_profile(email: str, watchlist: list[dict[str, Any]], portfolio: list[dict[str, Any]]) -> bool:
    """Upsert a user's full profile to Supabase."""
    email = (email or "").strip().lower()
    if not email or not is_cloud_store_configured():
        return False
    payload = {
        "user_email": email,
        "watchlist": watchlist,
        "portfolio": portfolio,
        "updated_at": "now()",
    }
    # Supabase/PostgREST cannot interpret "now()" inside JSON as SQL, so use a
    # separate PATCH-friendly string timestamp only when DB column has default.
    payload.pop("updated_at", None)
    url = f"{_base_url()}?on_conflict=user_email"
    headers = _headers() | {"Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except Exception:
        return False


def load_cloud_watchlist(email: str) -> list[dict[str, Any]]:
    data = load_user_profile(email).get("watchlist") or []
    return data if isinstance(data, list) else []


def load_cloud_portfolio(email: str) -> list[dict[str, Any]]:
    data = load_user_profile(email).get("portfolio") or []
    return data if isinstance(data, list) else []


def save_cloud_watchlist(email: str, watchlist: list[dict[str, Any]]) -> bool:
    profile = load_user_profile(email)
    return save_user_profile(email, watchlist, profile.get("portfolio") or [])


def save_cloud_portfolio(email: str, portfolio: list[dict[str, Any]]) -> bool:
    profile = load_user_profile(email)
    return save_user_profile(email, profile.get("watchlist") or [], portfolio)
