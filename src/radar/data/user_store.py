"""Local user data persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".ai_stock_radar"
PORTFOLIO_PATH = APP_DIR / "portfolio.json"
WATCHLIST_PATH = APP_DIR / "user_watchlist.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_watchlist() -> list[dict]:
    return _read_json(WATCHLIST_PATH, [])


def save_watchlist(items: list[dict]) -> None:
    _write_json(WATCHLIST_PATH, items)


def load_portfolio() -> list[dict]:
    return _read_json(PORTFOLIO_PATH, [])


def save_portfolio(items: list[dict]) -> None:
    _write_json(PORTFOLIO_PATH, items)
