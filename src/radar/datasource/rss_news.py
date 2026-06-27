"""RSS/live news loader with deterministic fallback."""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from radar.models.domain import NewsItem

RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSM,NVDA,AMD,SMH&region=US&lang=en-US",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
]

KEYWORD_SIGNAL_MAP = [
    ("nvidia", "AI Infrastructure", "positive", ["2330", "2382", "3231", "6669"], ["AI Server", "Semiconductor"]),
    ("ai", "AI Infrastructure", "positive", ["2330", "2382", "3231", "6669"], ["AI Server", "Semiconductor"]),
    ("semiconductor", "Semiconductor Momentum", "positive", ["2330", "2449", "2454"], ["Semiconductor"]),
    ("chip", "Semiconductor Momentum", "positive", ["2330", "2449", "2454"], ["Semiconductor"]),
    ("fed", "Macro Risk", "negative", ["2330", "2382", "3231", "6669"], ["Growth Stocks"]),
    ("rate", "Macro Risk", "negative", ["2330", "2382", "3231", "6669"], ["Growth Stocks"]),
    ("tariff", "Macro Risk", "negative", ["2330", "2382", "3231", "6669"], ["Export Tech"]),
]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _classify(title: str, summary: str) -> tuple[str, str, list[str], list[str]]:
    text = f"{title} {summary}".lower()
    for keyword, signal, sentiment, tickers, industries in KEYWORD_SIGNAL_MAP:
        if keyword in text:
            return signal, sentiment, tickers, industries
    return "Market Noise", "mixed", ["2330", "2382", "3231", "6669", "2449"], ["Market"]


def _load_fallback() -> list[NewsItem]:
    raw = json.loads(Path("data/rss/fallback_news.json").read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw]


def _fetch_feed(url: str, timeout: int = 6) -> list[NewsItem]:
    req = urllib.request.Request(url, headers={"User-Agent": "AIStockRadar/0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content = response.read()

    root = ET.fromstring(content)
    source = root.findtext("./channel/title") or "RSS"
    items: list[NewsItem] = []

    for item in root.findall("./channel/item")[:8]:
        title = _clean_text(item.findtext("title"))
        summary = _clean_text(item.findtext("description"))
        if not title:
            continue
        signal, sentiment, tickers, industries = _classify(title, summary)
        items.append(
            NewsItem(
                source=source,
                title=title,
                summary=summary[:240],
                signal=signal,
                sentiment=sentiment,
                tickers=tickers,
                industries=industries,
            )
        )
    return items


def load_news() -> tuple[str, list[NewsItem]]:
    all_items: list[NewsItem] = []
    for feed in RSS_FEEDS:
        try:
            all_items.extend(_fetch_feed(feed))
        except Exception:
            continue

    if all_items:
        return "RSS Live", all_items[:12]
    return "Fallback", _load_fallback()
