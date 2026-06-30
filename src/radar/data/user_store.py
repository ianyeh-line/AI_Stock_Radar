"""Persistent user watchlist and portfolio storage.

Storage priority:
1. Streamlit Beta Access + Supabase cloud profile, when configured.
2. Streamlit session state for Guest Mode, when cloud is not configured.
3. Local files under ~/.ai_stock_radar for the product owner using the app locally.

v3.2.3 change: save_* now returns True/False so the UI can tell the user when
cloud persistence actually failed instead of showing a false success message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from radar.integrations.cloud_user_store import (
    is_cloud_store_configured,
    load_cloud_portfolio,
    load_cloud_watchlist,
    save_cloud_portfolio,
    save_cloud_watchlist,
    last_cloud_error,
)

APP_DIR = Path.home() / ".ai_stock_radar"
PORTFOLIO_PATH = APP_DIR / "portfolio.json"
WATCHLIST_PATH = APP_DIR / "user_watchlist.json"


def _session_state() -> Any | None:
    try:
        import streamlit as st  # type: ignore
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
        if get_script_run_ctx() is None:
            return None
        return st.session_state
    except Exception:
        return None


def _cloud_email() -> str:
    ss = _session_state()
    if ss is None:
        return ""
    return str(ss.get("cloud_user_email") or "").strip().lower()


def _use_cloud() -> bool:
    return bool(_cloud_email() and is_cloud_store_configured())


def _use_session() -> bool:
    ss = _session_state()
    if ss is None or _use_cloud():
        return False
    return bool(ss.get("guest_mode_enabled") or ss.get("beta_access_enabled"))


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _session_list(key: str) -> list[dict]:
    ss = _session_state()
    if ss is None:
        return []
    ss.setdefault(key, [])
    data = ss.get(key)
    return data if isinstance(data, list) else []


def _save_session_list(key: str, items: list[dict]) -> None:
    ss = _session_state()
    if ss is not None:
        ss[key] = items


def _record_save_result(ok: bool, detail: str = "") -> None:
    ss = _session_state()
    if ss is not None:
        ss["last_user_store_save_ok"] = ok
        ss["last_user_store_save_detail"] = detail


def load_watchlist() -> list[dict]:
    if _use_cloud():
        return load_cloud_watchlist(_cloud_email())
    if _use_session():
        return _session_list("guest_watchlist")
    return _read_json(WATCHLIST_PATH, [])


def save_watchlist(items: list[dict]) -> bool:
    if _use_cloud():
        ok = save_cloud_watchlist(_cloud_email(), items)
        if not ok:
            # Preserve the user's changes during this browser session even when
            # Supabase is misconfigured, but report failure clearly.
            _save_session_list("guest_watchlist", items)
            _record_save_result(False, last_cloud_error())
            return False
        _record_save_result(True, "已保存到 Supabase")
        return True
    if _use_session():
        _save_session_list("guest_watchlist", items)
        _record_save_result(True, "已暫存在本次瀏覽 session")
        return True
    _write_json(WATCHLIST_PATH, items)
    _record_save_result(True, str(WATCHLIST_PATH))
    return True


def load_portfolio() -> list[dict]:
    if _use_cloud():
        return load_cloud_portfolio(_cloud_email())
    if _use_session():
        return _session_list("guest_portfolio")
    return _read_json(PORTFOLIO_PATH, [])


def save_portfolio(items: list[dict]) -> bool:
    if _use_cloud():
        ok = save_cloud_portfolio(_cloud_email(), items)
        if not ok:
            _save_session_list("guest_portfolio", items)
            _record_save_result(False, last_cloud_error())
            return False
        _record_save_result(True, "已保存到 Supabase")
        return True
    if _use_session():
        _save_session_list("guest_portfolio", items)
        _record_save_result(True, "已暫存在本次瀏覽 session")
        return True
    _write_json(PORTFOLIO_PATH, items)
    _record_save_result(True, str(PORTFOLIO_PATH))
    return True


def last_save_status() -> dict[str, str | bool]:
    ss = _session_state()
    if ss is None:
        return {"ok": True, "detail": ""}
    return {
        "ok": bool(ss.get("last_user_store_save_ok", True)),
        "detail": str(ss.get("last_user_store_save_detail") or ""),
    }


def storage_status() -> dict[str, str]:
    if _use_cloud():
        return {"mode": "cloud", "label": f"雲端保存：{_cloud_email()}", "detail": "Supabase user_profiles"}
    if _use_session():
        return {"mode": "session", "label": "訪客暫存", "detail": "目前只保存在這次瀏覽 session；設定 Supabase 後可跨次保存。"}
    return {"mode": "local", "label": "本機保存", "detail": str(APP_DIR)}
