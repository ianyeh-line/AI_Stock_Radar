"""Cloud user portfolio/watchlist storage via Supabase REST API.

v3.2.0 restores Web Beta persistence: friends can use Email + Access Code
(Beta Access) and store personal watchlist/portfolio in Supabase. When Supabase
is not configured, the app falls back to Streamlit session storage so the page
remains usable.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import requests

DEFAULT_TABLE = "user_profiles"
TIMEOUT_SECONDS = 12


def _streamlit() -> Any | None:
    try:
        import streamlit as st  # type: ignore
        return st
    except Exception:
        return None


def _secret_value(*keys: str) -> str:
    st = _streamlit()
    if st is None:
        return ""
    try:
        value: Any = st.secrets
        for key in keys:
            value = value[key]
        return str(value or "").strip()
    except Exception:
        return ""


def supabase_config() -> dict[str, str]:
    url = _secret_value("supabase", "url").rstrip("/")
    key = (
        _secret_value("supabase", "service_role_key")
        or _secret_value("supabase", "key")
        or _secret_value("supabase", "anon_key")
    )
    table = _secret_value("supabase", "table") or DEFAULT_TABLE
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
        status = "已設定，可保存朋友持股"
    return {"status": status, "url": cfg["url"], "table": cfg["table"]}


def _headers() -> dict[str, str]:
    key = supabase_config()["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    cfg = supabase_config()
    return f"{cfg['url']}/rest/v1/{cfg['table']}"


def _empty(email: str) -> dict[str, Any]:
    return {"user_email": email, "watchlist": [], "portfolio": []}


def load_user_profile(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not email or not is_cloud_store_configured():
        return _empty(email)
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
        return _empty(email)
    return _empty(email)


def save_user_profile(email: str, watchlist: list[dict[str, Any]], portfolio: list[dict[str, Any]]) -> bool:
    email = (email or "").strip().lower()
    if not email or not is_cloud_store_configured():
        return False
    payload = {"user_email": email, "watchlist": watchlist, "portfolio": portfolio}
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
