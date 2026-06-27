"""RSS datasource for AI Stock Radar.

The datasource tries live public RSS feeds first. If the feeds are unavailable or
too generic, it blends in curated baseline news so the product can still produce
a usable Decision OS view.
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from radar.i18n.zh import localize_news_summary, localize_news_title, signal_zh, sentiment_zh, source_zh
from radar.knowledge.stock_map import SIGNAL_KEYWORDS
from radar.models.domain import NewsItem

RSS_FEEDS: list[tuple[str, str]] = [
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Technology", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),
]

FALLBACK_PATH = Path("data/rss/fallback_news.json")


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return " ".join(value.split())


def _classify(title: str, summary: str) -> tuple[str, str, list[str], list[str]]:
    text = f"{title} {summary}".lower()
    matched_signals: list[str] = []
    matched_tickers: list[str] = []
    sentiment = "neutral"

    for signal, keywords, signal_sentiment, tickers in SIGNAL_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            matched_signals.append(signal)
            matched_tickers.extend(tickers)
            if signal_sentiment == "negative":
                sentiment = "negative"
            elif sentiment != "negative":
                sentiment = signal_sentiment

    if not matched_signals:
        matched_signals = ["Market News"]

    industries = sorted({signal for signal in matched_signals if signal != "Market News"})
    if not industries:
        industries = ["Broad Market"]

    return matched_signals[0], sentiment, sorted(set(matched_tickers)), industries


def _build_news_item(source: str, title: str, summary: str, url: str = "") -> NewsItem:
    signal, sentiment, tickers, industries = _classify(title, summary)
    title_zh = localize_news_title(title, signal, sentiment, tickers)
    summary_zh = localize_news_summary(summary, signal, sentiment, tickers)
    return NewsItem(
        source=source_zh(source),
        title=title,
        summary=summary[:280],
        signal=signal,
        sentiment=sentiment,
        tickers=tickers,
        industries=industries,
        url=url,
        title_zh=title_zh,
        summary_zh=summary_zh,
        signal_zh=signal_zh(signal),
        sentiment_zh=sentiment_zh(sentiment),
    )


def _parse_feed(source: str, xml_text: str, limit: int = 8) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")[:limit]
    news_items: list[NewsItem] = []

    for item in items:
        title = _clean_text(item.findtext("title", ""))
        summary = _clean_text(item.findtext("description", ""))
        link = _clean_text(item.findtext("link", ""))
        if not title:
            continue
        news_items.append(_build_news_item(source, title, summary, link))
    return news_items


def _fetch_feed(source: str, url: str) -> list[NewsItem]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Stock-Radar/0.8"})
    with urllib.request.urlopen(request, timeout=4) as response:  # noqa: S310 - public RSS only
        xml_text = response.read().decode("utf-8", errors="ignore")
    return _parse_feed(source, xml_text)


def _load_fallback() -> list[NewsItem]:
    data = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
    items: list[NewsItem] = []
    for item in data:
        signal = item["signal"]
        sentiment = item["sentiment"]
        tickers = item["tickers"]
        items.append(
            NewsItem(
                source=source_zh(item["source"]),
                title=item["title"],
                summary=item["summary"],
                signal=signal,
                sentiment=sentiment,
                tickers=tickers,
                industries=item["industries"],
                url=item.get("url", ""),
                title_zh=item.get("title_zh") or localize_news_title(item["title"], signal, sentiment, tickers),
                summary_zh=item.get("summary_zh") or localize_news_summary(item["summary"], signal, sentiment, tickers),
                signal_zh=signal_zh(signal),
                sentiment_zh=sentiment_zh(sentiment),
            )
        )
    return items


def _meaningful_count(items: list[NewsItem]) -> int:
    return sum(1 for item in items if item.signal != "Market News" and item.tickers)


def load_news() -> tuple[str, list[NewsItem]]:
    live_items: list[NewsItem] = []
    for source, url in RSS_FEEDS:
        try:
            live_items.extend(_fetch_feed(source, url))
        except Exception:
            continue

    if _meaningful_count(live_items) >= 4:
        return "即時 RSS 新聞", live_items[:18]

    fallback_items = _load_fallback()
    if live_items:
        blended = live_items[:8] + fallback_items
        return "即時 RSS + 精選基準新聞", blended[:18]

    return "精選基準新聞", fallback_items
