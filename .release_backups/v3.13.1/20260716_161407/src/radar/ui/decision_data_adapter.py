"""Data adapter for AI Stock Radar v3.13.0 Decision-first UX.

The adapter accepts several likely dashboard JSON shapes so the UI can be
installed without forcing a rewrite of the existing data pipeline. It avoids
hard-coded demo stocks: when no rows are available, the page shows a neutral
empty state instead of fake recommendations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .decision_copy_guard import sanitize_user_facing_copy

DEFAULT_MARKET_STATE = "偏多但不追高"
DEFAULT_MARKET_GUIDANCE = "今天只做有價格條件的低接或突破確認，盤中急拉不追。先處理持股風險，再看今日可操作清單。"

CATEGORY_ACTIONABLE = "今日可操作"
CATEGORY_WATCH = "強勢觀察"
CATEGORY_WAIT = "等待條件"
CATEGORY_RISK = "避開/控風險"
CATEGORY_HOLDING = "我的持股"

ROW_COLUMNS = (
    "priority",
    "stock",
    "category",
    "suggestion",
    "trigger",
    "risk_line",
    "reason",
    "data_status",
)

ACTION_WORDS = ("買", "低接", "分批", "加碼", "突破", "可操作", "進場")
WAIT_WORDS = ("等", "觀察", "回檔", "拉回", "盤整", "未觸發")
RISK_WORDS = ("避開", "減碼", "停損", "不追", "轉弱", "控風險", "風險")


class MissingDashboardData(dict):
    """Marker payload used when dashboard_data.json is absent."""


def _first_present(mapping: dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return []


def _stringify(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        text = "、".join(str(item) for item in value if item not in (None, ""))
        return text or fallback
    if isinstance(value, dict):
        preferred = _first_present(value, ("label", "text", "name", "value"), "")
        return str(preferred) if preferred else fallback
    return str(value).strip() or fallback


def _compose_stock_name(item: dict[str, Any]) -> str:
    stock = _first_present(item, ("stock", "股票", "display_name", "label"), "")
    code = _first_present(item, ("code", "symbol", "ticker", "股票代號", "證券代號"), "")
    name = _first_present(item, ("name", "stock_name", "股票名稱", "證券名稱"), "")
    if stock:
        return _stringify(stock)
    if code and name:
        return f"{code} {name}"
    return _stringify(code or name, "未命名標的")


def _infer_category(item: dict[str, Any], category_hint: str | None = None) -> str:
    raw = _stringify(
        _first_present(item, ("category", "分類", "bucket", "group", "status", "decision_type"), category_hint or ""),
        "",
    )
    text = " ".join(
        _stringify(
            _first_present(item, ("suggestion", "今日建議", "action", "recommendation", "next_step", "下一步"), ""),
            "",
        ).split()
    )
    combined = f"{raw} {text}"

    if any(word in combined for word in ("今日可操作", "可買", "可操作", "actionable")):
        return CATEGORY_ACTIONABLE
    if any(word in combined for word in ("持股", "holding", "續抱")):
        return CATEGORY_HOLDING
    if any(word in combined for word in RISK_WORDS):
        return CATEGORY_RISK
    if any(word in combined for word in ("強勢", "watch", "觀察")):
        return CATEGORY_WATCH
    if any(word in combined for word in WAIT_WORDS):
        return CATEGORY_WAIT
    if any(word in combined for word in ACTION_WORDS):
        return CATEGORY_ACTIONABLE
    return raw or CATEGORY_WAIT


def _normalize_data_status(item: dict[str, Any]) -> str:
    explicit = _first_present(item, ("data_status", "資料狀態", "data_quality", "資料品質"), "")
    if explicit:
        return sanitize_user_facing_copy(_stringify(explicit), "資料狀態未標示")

    chip = _first_present(item, ("chip_status", "籌碼狀態", "institutional_status", "三大法人"), "")
    if chip:
        return sanitize_user_facing_copy(_stringify(chip), "籌碼資料狀態未標示")

    has_official_chip = _first_present(item, ("has_official_chip_data", "official_chip", "has_chip_data"), None)
    if has_official_chip is True:
        return "資料完整"
    if has_official_chip is False:
        return "籌碼資料不足"
    return "資料狀態未標示"


def normalize_row(item: dict[str, Any], index: int = 0, category_hint: str | None = None) -> dict[str, Any]:
    category = _infer_category(item, category_hint)
    suggestion = sanitize_user_facing_copy(
        _stringify(_first_present(item, ("suggestion", "今日建議", "action", "recommendation", "next_step", "下一步"), ""), "等待條件"),
        "等待條件",
    )
    trigger = sanitize_user_facing_copy(
        _stringify(_first_present(item, ("trigger", "觸發條件", "entry_condition", "condition", "buy_zone", "entry_zone"), ""), "等價格條件成立"),
        "等價格條件成立",
    )
    risk_line = sanitize_user_facing_copy(
        _stringify(_first_present(item, ("risk_line", "風險線", "stop_loss", "stop", "support", "risk"), ""), "跌破風險線減碼"),
        "跌破風險線減碼",
    )
    reason = sanitize_user_facing_copy(
        _stringify(_first_present(item, ("reason", "理由", "why", "rationale", "summary", "note"), ""), "需等待量價與價格條件確認"),
        "需等待量價與價格條件確認",
    )

    priority = _first_present(item, ("priority", "優先級", "rank", "score_rank"), index + 1)
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        priority = index + 1

    return {
        "priority": priority,
        "stock": _compose_stock_name(item),
        "category": category,
        "suggestion": suggestion,
        "trigger": trigger,
        "risk_line": risk_line,
        "reason": reason,
        "data_status": _normalize_data_status(item),
    }


def _collect_from_path(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _iter_candidate_sections(payload: dict[str, Any]) -> Iterable[tuple[Any, str | None]]:
    paths: tuple[tuple[tuple[str, ...], str | None], ...] = (
        (("decision_rows",), None),
        (("decisions",), None),
        (("recommendations",), None),
        (("stocks",), None),
        (("today", "decision_rows"), None),
        (("today", "recommendations"), None),
        (("today", "actionable"), CATEGORY_ACTIONABLE),
        (("actionable",), CATEGORY_ACTIONABLE),
        (("actionable_stocks",), CATEGORY_ACTIONABLE),
        (("今日可操作",), CATEGORY_ACTIONABLE),
        (("watch",), CATEGORY_WATCH),
        (("watchlist",), CATEGORY_WATCH),
        (("strong_watch",), CATEGORY_WATCH),
        (("強勢觀察",), CATEGORY_WATCH),
        (("wait",), CATEGORY_WAIT),
        (("waiting",), CATEGORY_WAIT),
        (("等待條件",), CATEGORY_WAIT),
        (("risk",), CATEGORY_RISK),
        (("risk_list",), CATEGORY_RISK),
        (("avoid",), CATEGORY_RISK),
        (("避開/控風險",), CATEGORY_RISK),
        (("holdings",), CATEGORY_HOLDING),
        (("my_holdings",), CATEGORY_HOLDING),
        (("我的持股",), CATEGORY_HOLDING),
    )
    for path, hint in paths:
        value = _collect_from_path(payload, path)
        if value is not None:
            yield value, hint


def normalize_decision_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for section, hint in _iter_candidate_sections(payload):
        for item in _as_list(section):
            if not isinstance(item, dict):
                continue
            row = normalize_row(item, len(rows), hint)
            key = (row["stock"], row["suggestion"], row["trigger"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    rows.sort(key=lambda row: (row.get("priority", 999), row.get("stock", "")))
    return rows


def _explicit_count(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = _first_present(payload, (key,), None)
        if isinstance(value, int):
            return value
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            nested = _first_present(value, ("count", "total", "value"), None)
            if isinstance(nested, int):
                return nested
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary:
        for key in keys:
            value = summary.get(key)
            if isinstance(value, int):
                return value
    return None


def derive_summary(rows: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, int]:
    counts = {
        "actionable": sum(1 for row in rows if row["category"] == CATEGORY_ACTIONABLE),
        "watch": sum(1 for row in rows if row["category"] == CATEGORY_WATCH),
        "wait": sum(1 for row in rows if row["category"] == CATEGORY_WAIT),
        "risk": sum(1 for row in rows if row["category"] == CATEGORY_RISK),
    }
    explicit_map = {
        "actionable": ("actionable_count", "today_actionable", "今日可操作"),
        "watch": ("watch_count", "strong_watch", "強勢觀察"),
        "wait": ("wait_count", "waiting_count", "等待條件"),
        "risk": ("risk_count", "avoid_count", "避開/控風險"),
    }
    for name, keys in explicit_map.items():
        explicit = _explicit_count(payload, keys)
        if explicit is not None:
            counts[name] = explicit
    return counts


def split_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "actionable_rows": [row for row in rows if row["category"] == CATEGORY_ACTIONABLE],
        "holding_rows": [row for row in rows if row["category"] == CATEGORY_HOLDING],
        "risk_rows": [row for row in rows if row["category"] == CATEGORY_RISK],
        "watch_rows": [row for row in rows if row["category"] == CATEGORY_WATCH],
        "wait_rows": [row for row in rows if row["category"] == CATEGORY_WAIT],
    }


def load_dashboard_payload(path: str | Path = "output/dashboard_data.json") -> dict[str, Any]:
    dashboard_path = Path(path)
    if not dashboard_path.exists():
        return MissingDashboardData({
            "diagnostics": {
                "price_status": "尚未找到 output/dashboard_data.json",
                "official_chip_status": "尚未提供",
                "generated_at": "尚未產生",
            }
        })
    with dashboard_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("dashboard_data.json 必須是 JSON object")
    return data


def build_dashboard_view(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = payload or {}
    rows = normalize_decision_rows(data)
    summary = derive_summary(rows, data)
    split = split_rows(rows)

    market_state = sanitize_user_facing_copy(
        _stringify(_first_present(data, ("market_state", "market_title", "title", "今日結論"), DEFAULT_MARKET_STATE), DEFAULT_MARKET_STATE),
        DEFAULT_MARKET_STATE,
    )
    market_guidance = sanitize_user_facing_copy(
        _stringify(_first_present(data, ("market_guidance", "subtitle", "guidance", "操作建議"), DEFAULT_MARKET_GUIDANCE), DEFAULT_MARKET_GUIDANCE),
        DEFAULT_MARKET_GUIDANCE,
    )

    diagnostics = data.get("diagnostics") if isinstance(data.get("diagnostics"), dict) else {}
    if not diagnostics:
        diagnostics = {
            "price_status": _stringify(_first_present(data, ("price_status", "價格資料狀態"), "未提供")),
            "official_chip_status": _stringify(_first_present(data, ("official_chip_status", "三大法人資料狀態"), "未提供")),
            "generated_at": _stringify(_first_present(data, ("generated_at", "updated_at", "資料更新時間"), "未提供")),
        }

    return {
        "market_state": market_state,
        "market_guidance": market_guidance,
        "summary": summary,
        "decision_rows": rows,
        "diagnostics": diagnostics,
        **split,
        "has_dashboard_data": not isinstance(data, MissingDashboardData),
    }
