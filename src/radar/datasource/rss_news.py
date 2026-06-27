"""RSS news datasource using Python standard library only."""

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from radar.models.domain import NewsItem


DEFAULT_SETTINGS = Path("config/settings.example.json")
FALLBACK_NEWS = Path("data/rss/fallback_news.json")


def load_settings() -> dict:
    if DEFAULT_SETTINGS.exists():
        return json.loads(DEFAULT_SETTINGS.read_text(encoding="utf-8"))
    return {"rss_feeds": [], "max_news_items": 12}


def _text(parent: ET.Element, tag: str) -> str:
    found = parent.find(tag)
    return found.text.strip() if found is not None and found.text else ""


def fetch_feed(url: str, timeout: int = 8) -> list[NewsItem]:
    req = urllib.request.Request(url, headers={"User-Agent": "AIStockRadar/0.4"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        return []

    source = _text(channel, "title") or url
    items: list[NewsItem] = []
    for item in channel.findall("item"):
        title = _text(item, "title")
        if not title:
            continue
        items.append(
            NewsItem(
                title=title,
                source=source,
                link=_text(item, "link"),
                summary=_text(item, "description"),
                published=_text(item, "pubDate"),
            )
        )
    return items


def load_fallback_news() -> list[NewsItem]:
    raw_items = json.loads(FALLBACK_NEWS.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw_items]


def fetch_market_news() -> tuple[list[NewsItem], bool]:
    settings = load_settings()
    max_items = int(settings.get("max_news_items", 12))
    all_items: list[NewsItem] = []

    for url in settings.get("rss_feeds", []):
        try:
            all_items.extend(fetch_feed(url))
        except Exception:
            continue

    if not all_items:
        return load_fallback_news()[:max_items], False

    seen = set()
    deduped: list[NewsItem] = []
    for item in all_items:
        key = item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return deduped, True
