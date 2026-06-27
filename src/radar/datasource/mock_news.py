"""Mock news data source for product validation."""

import json
from pathlib import Path

from radar.models.domain import NewsItem


DEFAULT_NEWS_PATH = Path("data/mock/news.json")


def load_news(path: Path = DEFAULT_NEWS_PATH) -> list[NewsItem]:
    raw_items = json.loads(path.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw_items]
