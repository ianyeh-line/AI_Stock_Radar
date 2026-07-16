"""Cloud user portfolio/watchlist storage via Supabase REST API.

v3.2.4 hardens the Web Beta persistence layer:
- Make save failures visible instead of silently showing success.
- Support common Streamlit Secrets key names.
- Add connection diagnostics for Streamlit Cloud setup.
- Use a server-side Supabase service_role / secret key only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

import requests

DEFAULT_TABLE = "user_profiles"
TIMEOUT_SECONDS = 12

_LAST_ERROR = ""
_LAST_RESPONSE = ""


def _set_error(message: str, detail: str = "") -> None:
    global _LAST_ERROR, _LAST_RESPONSE
    _LAST_ERROR = message
    _LAST_RESPONSE = detail[:1000] if detail else ""
    st = _streamlit()
    if st is not None:
        try:
            st.session_state["cloud_store_last_error"] = _LAST_ERROR
            st.session_state["cloud_store_last_response"] = _LAST_RESPONSE
        except Exception:
            pass


def last_cloud_error() -> str:
    st = _streamlit()
    if st is not None:
        try:
            return str(st.session_state.get("cloud_store_last_error") or _LAST_ERROR)
        except Exception:
            pass
    return _LAST_ERROR


def last_cloud_response() -> str:
    st = _streamlit()
    if st is not None:
        try:
            return str(st.session_state.get("cloud_store_last_response") or _LAST_RESPONSE)
        except Exception:
            pass
    return _LAST_RESPONSE


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



def _normalize_supabase_url(raw_url: str) -> str:
    """Normalize common Supabase URL inputs for REST API calls.

    Streamlit Secrets should ideally contain only:
        https://<project-ref>.supabase.co

    In practice, new users often paste the Data API endpoint, for example:
        https://<project-ref>.supabase.co/rest/v1

    If we do not normalize this, the app builds invalid URLs such as
    /rest/v1/rest/v1/user_profiles and Supabase returns PGRST125.
    """
    raw_url = (raw_url or "").strip().strip('"').strip("'").rstrip("/")
    if not raw_url:
        return ""
    parsed = urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return raw_url.rstrip("/")


def _normalize_table_name(raw_table: str) -> str:
    """Normalize table name entered in Streamlit Secrets.

    Supabase UI labels the table as public.user_profiles. PostgREST endpoint
    should use only user_profiles. This function also handles users pasting a
    REST path such as /rest/v1/user_profiles.
    """
    value = (raw_table or DEFAULT_TABLE).strip().strip('"').strip("'").strip("/")
    if not value:
        return DEFAULT_TABLE
    if "/" in value:
        value = value.split("/")[-1]
    if "." in value:
        value = value.split(".")[-1]
    return value or DEFAULT_TABLE

def supabase_config() -> dict[str, str]:
    raw_url = (
        _secret_value("supabase", "url")
        or _secret_value("connections", "supabase", "url")
    )
    url = _normalize_supabase_url(raw_url)

    # Prefer server-side keys. Keep anon_key as a detected value only so we can
    # show a clear warning; it should not be used for persistence when RLS is on.
    key = (
        _secret_value("supabase", "service_role_key")
        or _secret_value("supabase", "secret_key")
        or _secret_value("supabase", "sb_secret_key")
        or _secret_value("supabase", "key")
        or _secret_value("supabase", "anon_key")
    )
    raw_table = _secret_value("supabase", "table") or DEFAULT_TABLE
    table = _normalize_table_name(raw_table)
    return {
        "url": url,
        "key": key,
        "table": table,
        "raw_url": str(raw_url or ""),
        "raw_table": str(raw_table or ""),
    }


def _looks_like_public_key(key: str) -> bool:
    if not key:
        return False
    # Supabase legacy anon/service keys are JWTs and hard to distinguish without
    # decoding. However users often paste publishable keys in the new API Keys UI.
    lowered = key.lower()
    return lowered.startswith("sb_publishable_") or lowered.startswith("supabase_publishable_")


def is_cloud_store_configured() -> bool:
    cfg = supabase_config()
    return bool(cfg["url"] and cfg["key"] and not _looks_like_public_key(cfg["key"]))


def cloud_status() -> dict[str, str]:
    cfg = supabase_config()
    key = cfg["key"]
    if not cfg["url"]:
        status = "未設定 Supabase URL"
    elif not key:
        status = "未設定 Supabase Key"
    elif _looks_like_public_key(key):
        status = "偵測到 publishable / public key；請改用 service_role 或 secret key"
    else:
        status = "已設定，可保存朋友持股"
    masked = ""
    if key:
        masked = f"{key[:8]}...{key[-6:]}" if len(key) > 18 else "已設定"
    warning_parts = []
    if cfg.get("raw_url") and cfg.get("raw_url") != cfg["url"]:
        warning_parts.append("URL 已自動修正為專案根網址")
    if cfg.get("raw_table") and cfg.get("raw_table") != cfg["table"]:
        warning_parts.append("資料表名稱已自動修正為 user_profiles")
    return {
        "status": status,
        "url": cfg["url"],
        "table": cfg["table"],
        "key_preview": masked,
        "warning": "；".join(warning_parts),
    }


def _headers(prefer: str | None = None) -> dict[str, str]:
    key = supabase_config()["key"]
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _base_url() -> str:
    cfg = supabase_config()
    return f"{cfg['url']}/rest/v1/{cfg['table']}"


def _empty(email: str) -> dict[str, Any]:
    return {"user_email": email, "watchlist": [], "portfolio": []}


@dataclass
class CloudCheck:
    ok: bool
    message: str
    detail: str = ""


def check_cloud_connection() -> CloudCheck:
    cfg = supabase_config()
    if not cfg["url"]:
        return CloudCheck(False, "未設定 Supabase URL")
    if not cfg["key"]:
        return CloudCheck(False, "未設定 Supabase Key")
    if _looks_like_public_key(cfg["key"]):
        return CloudCheck(False, "目前填的是 public / publishable key。請改用 service_role 或 secret key。")

    url = f"{_base_url()}?select=user_email&limit=1"
    try:
        response = requests.get(url, headers=_headers(), timeout=TIMEOUT_SECONDS)
        if response.status_code in (200, 206):
            _set_error("")
            return CloudCheck(True, "Supabase 連線成功")
        detail = response.text[:500]
        if response.status_code in (401, 403):
            return CloudCheck(False, "Supabase 權限不足：請確認 Streamlit Secrets 使用 service_role / secret key，不要用 anon key。", detail)
        if "PGRST125" in detail or "Invalid path" in detail:
            return CloudCheck(
                False,
                "Supabase URL / table 設定格式錯誤：URL 應只填 https://xxxx.supabase.co，table 應只填 user_profiles，不要填 public.user_profiles 或 /rest/v1/user_profiles。",
                detail,
            )
        if response.status_code == 404:
            return CloudCheck(False, "找不到 user_profiles 資料表：請確認 SQL schema 已建立，table 名稱為 user_profiles。", detail)
        return CloudCheck(False, f"Supabase 回應異常：HTTP {response.status_code}", detail)
    except Exception as exc:
        return CloudCheck(False, f"Supabase 連線失敗：{exc}")


def load_user_profile(email: str) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not email:
        _set_error("未提供使用者識別碼")
        return _empty(email)
    if not is_cloud_store_configured():
        _set_error("Supabase 尚未完整設定")
        return _empty(email)
    url = f"{_base_url()}?user_email=eq.{quote(email)}&select=user_email,watchlist,portfolio&limit=1"
    try:
        response = requests.get(url, headers=_headers(), timeout=TIMEOUT_SECONDS)
        if response.status_code not in (200, 206):
            _set_error(f"讀取 Supabase 失敗：HTTP {response.status_code}", response.text)
            return _empty(email)
        rows = response.json()
        _set_error("")
        if rows:
            row = rows[0]
            return {
                "user_email": email,
                "watchlist": row.get("watchlist") or [],
                "portfolio": row.get("portfolio") or [],
            }
    except Exception as exc:
        _set_error(f"讀取 Supabase 失敗：{exc}")
        return _empty(email)
    return _empty(email)


def save_user_profile(email: str, watchlist: list[dict[str, Any]], portfolio: list[dict[str, Any]]) -> bool:
    email = (email or "").strip().lower()
    if not email:
        _set_error("未提供使用者識別碼，無法保存")
        return False
    if not is_cloud_store_configured():
        _set_error("Supabase 尚未完整設定，無法保存到雲端")
        return False

    payload = {"user_email": email, "watchlist": watchlist, "portfolio": portfolio}
    url = f"{_base_url()}?on_conflict=user_email"
    headers = _headers("resolution=merge-duplicates,return=representation")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False), timeout=TIMEOUT_SECONDS)
        if response.status_code in (200, 201, 204):
            _set_error("")
            return True
        # If the upsert path fails because of policy/shape, expose the actual
        # Supabase message. This is much better than pretending success.
        if response.status_code in (401, 403):
            _set_error("寫入 Supabase 權限不足：請使用 service_role / secret key，且放在 Streamlit Secrets。", response.text)
        elif response.status_code == 404:
            _set_error("寫入 Supabase 失敗：找不到 user_profiles 資料表。", response.text)
        else:
            _set_error(f"寫入 Supabase 失敗：HTTP {response.status_code}", response.text)
        return False
    except Exception as exc:
        _set_error(f"寫入 Supabase 失敗：{exc}")
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
