"""RSS news ingestion with robust fallback."""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from radar.models.domain import NewsItem

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=NVIDIA+AI+server+Taiwan+semiconductor&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=TSMC+CoWoS+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=semiconductor+SOX+AI+stocks&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

KEYWORD_SIGNAL_MAP = [
    ("NVIDIA", "AI Infrastructure", "NVIDIA AI GPU 需求維持強勁", ["2330 台積電", "2382 廣達", "3231 緯創", "6669 緯穎", "3017 奇鋐"]),
    ("TSMC", "Semiconductor Momentum", "台積電與先進製程仍是台股核心主線", ["2330 台積電", "2449 京元電子", "2454 聯發科"]),
    ("CoWoS", "AI Infrastructure", "CoWoS 需求支撐先進封裝供應鏈", ["2330 台積電", "3017 奇鋐"]),
    ("AI", "AI Infrastructure", "AI 基礎建設是市場主要成長題材", ["2382 廣達", "3231 緯創", "6669 緯穎"]),
    ("Fed", "Macro Risk", "Fed 變數可能壓抑高估值科技股", ["6669 緯穎", "3017 奇鋐", "3661 世芯-KY"]),
]


def _fallback_news() -> list[NewsItem]:
    raw = json.loads(Path("data/rss/fallback_news.json").read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw]


def _translate_title(title: str) -> str:
    replacements = {
        "NVIDIA": "NVIDIA",
        "AI server": "AI 伺服器",
        "AI Server": "AI 伺服器",
        "semiconductor": "半導體",
        "Semiconductor": "半導體",
        "TSMC": "台積電",
        "CoWoS": "CoWoS",
        "Fed": "Fed",
    }
    translated = title
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _classify_news(title: str, source: str) -> NewsItem:
    for keyword, signal, summary, stocks in KEYWORD_SIGNAL_MAP:
        if keyword.lower() in title.lower():
            impact = "negative" if signal == "Macro Risk" else "positive"
            industries = ["高估值科技", "AI 概念股"] if impact == "negative" else ["半導體", "AI Server"]
            return NewsItem(
                source=source,
                title=title,
                title_zh=_translate_title(title),
                summary_zh=summary,
                signal=signal,
                impact=impact,
                industries=industries,
                affected_stocks=stocks,
            )
    return NewsItem(
        source=source,
        title=title,
        title_zh=_translate_title(title),
        summary_zh="此新聞與目前核心 Watchlist 關聯度較低，暫列為背景資訊。",
        signal="Market Background",
        impact="neutral",
        industries=["市場背景"],
        affected_stocks=[],
    )


def fetch_rss_news(limit: int = 12) -> tuple[list[NewsItem], str]:
    items: list[NewsItem] = []

    for feed in RSS_FEEDS:
        try:
            with urllib.request.urlopen(feed, timeout=5) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item")[:limit]:
                title = item.findtext("title") or "Untitled"
                source = "Google News RSS"
                source_node = item.find("source")
                if source_node is not None and source_node.text:
                    source = source_node.text
                items.append(_classify_news(title, source))
                if len(items) >= limit:
                    break
        except Exception:
            continue
        if len(items) >= limit:
            break

    if not items:
        return _fallback_news(), "Fallback"

    # Keep only relevant or informative items, but preserve enough context.
    relevant = [item for item in items if item.signal != "Market Background"]
    if len(relevant) >= 3:
        return relevant[:limit], f"RSS Live ({len(relevant[:limit])} items)"
    return items[:limit], f"RSS Live ({len(items[:limit])} items)"
