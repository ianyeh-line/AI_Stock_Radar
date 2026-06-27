"""Stock universe and theme mapping."""

from __future__ import annotations

import json
from pathlib import Path

from radar.models.domain import StockProfile


def load_stock_universe(path: str | Path = "data/universe/taiwan_watchlist.json") -> list[StockProfile]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [StockProfile(**item) for item in raw]


def stock_lookup() -> dict[str, StockProfile]:
    return {stock.symbol: stock for stock in load_stock_universe()}


def normalize_stock_name(text: str) -> str:
    return text.split()[0].strip()
