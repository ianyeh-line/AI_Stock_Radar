"""RSS news ingestion with deterministic Chinese investment summaries."""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

from radar.models.domain import NewsItem

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=NVIDIA+AI+server+Taiwan+semiconductor&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=TSMC+CoWoS+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=semiconductor+SOX+AI+stocks&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=Fed+rates+growth+stocks+semiconductor&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

KEYWORD_SIGNAL_MAP = [
    ("NVIDIA", "AI Infrastructure", "NVIDIA 與 AI GPU 需求仍是 AI 基礎建設的核心訊號。", ["2330 台積電", "2382 廣達", "3231 緯創", "6669 緯穎", "3017 奇鋐"]),
    ("NVDA", "AI Infrastructure", "NVIDIA 與 AI GPU 需求仍是 AI 基礎建設的核心訊號。", ["2330 台積電", "2382 廣達", "3231 緯創", "6669 緯穎", "3017 奇鋐"]),
    ("TSMC", "Semiconductor Momentum", "台積電與先進製程仍是台股半導體主線。", ["2330 台積電", "2449 京元電子", "2454 聯發科"]),
    ("台積電", "Semiconductor Momentum", "台積電與先進製程仍是台股半導體主線。", ["2330 台積電", "2449 京元電子", "2454 聯發科"]),
    ("CoWoS", "AI Infrastructure", "CoWoS 需求支撐先進封裝與 AI Server 供應鏈。", ["2330 台積電", "3017 奇鋐", "2449 京元電子"]),
    ("AI", "AI Infrastructure", "AI 基礎建設仍是市場最重要的成長題材之一。", ["2382 廣達", "3231 緯創", "6669 緯穎", "2308 台達電"]),
    ("server", "AI Infrastructure", "AI 伺服器需求支撐電子供應鏈波段動能。", ["2382 廣達", "3231 緯創", "6669 緯穎", "2317 鴻海"]),
    ("semiconductor", "Semiconductor Momentum", "半導體景氣與估值是台股電子族群的重要方向。", ["2330 台積電", "2454 聯發科", "2449 京元電子", "3661 世芯-KY"]),
    ("Fed", "Macro Risk", "Fed 與利率變數可能壓抑高估值科技股追價意願。", ["6669 緯穎", "3661 世芯-KY", "3017 奇鋐"]),
    ("inflation", "Macro Risk", "通膨與利率變數提高成長股評價壓力。", ["6669 緯穎", "3661 世芯-KY", "3017 奇鋐"]),
]

TRANSLATION_REPLACEMENTS = {
    "NVIDIA": "NVIDIA",
    "NVDA": "NVIDIA",
    "AI server": "AI 伺服器",
    "AI Server": "AI 伺服器",
    "server": "伺服器",
    "Semiconductor": "半導體",
    "semiconductor": "半導體",
    "TSMC": "台積電",
    "CoWoS": "CoWoS",
    "Fed": "Fed",
    "inflation": "通膨",
    "earnings": "財報",
    "chip": "晶片",
    "stocks": "股票",
    "market": "市場",
    "rate": "利率",
    "rates": "利率",
}


def _fallback_news() -> list[NewsItem]:
    raw = json.loads(Path("data/rss/fallback_news.json").read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in raw]


def _translate_title(title: str) -> str:
    translated = title
    for source, target in TRANSLATION_REPLACEMENTS.items():
        translated = translated.replace(source, target)
    return translated


def _clean_google_link(link: str) -> str:
    if not link:
        return ""
    # Google News RSS links are acceptable as source links. Some feeds include url= original.
    try:
        parsed = urlparse(link)
        params = parse_qs(parsed.query)
        if "url" in params and params["url"]:
            return unquote(params["url"][0])
    except Exception:
        return link
    return link


def _classify_news(title: str, source: str, published: str = "", source_url: str = "") -> NewsItem:
    for keyword, signal, summary, stocks in KEYWORD_SIGNAL_MAP:
        if keyword.lower() in title.lower():
            impact = "negative" if signal == "Macro Risk" else "positive"
            industries = ["高估值科技", "AI 概念股"] if impact == "negative" else ["半導體", "AI Server", "資料中心"]
            return NewsItem(
                source=source,
                title=title,
                title_zh=_translate_title(title),
                summary_zh=summary,
                signal=signal,
                impact=impact,
                industries=industries,
                affected_stocks=stocks,
                published=published,
                source_url=source_url,
            )
    return NewsItem(
        source=source,
        title=title,
        title_zh=_translate_title(title),
        summary_zh="此新聞與目前核心 Watchlist 關聯度較低，暫列為市場背景資訊。",
        signal="Market Background",
        impact="neutral",
        industries=["市場背景"],
        affected_stocks=[],
        published=published,
        source_url=source_url,
    )


def fetch_rss_news(limit: int = 12) -> tuple[list[NewsItem], str]:
    items: list[NewsItem] = []
    seen_titles: set[str] = set()

    for feed in RSS_FEEDS:
        try:
            request = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=6) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            channel = root.find("channel")
            if channel is None:
                continue
            for node in channel.findall("item"):
                title = (node.findtext("title") or "Untitled").strip()
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                source = "Google News RSS"
                source_node = node.find("source")
                if source_node is not None and source_node.text:
                    source = source_node.text.strip()
                published = node.findtext("pubDate") or ""
                source_url = _clean_google_link(node.findtext("link") or "")
                items.append(_classify_news(title, source, published, source_url))
                if len(items) >= limit:
                    break
        except Exception:
            continue
        if len(items) >= limit:
            break

    if not items:
        return _fallback_news(), "Fallback News"

    relevant = [item for item in items if item.signal != "Market Background"]
    if len(relevant) >= 3:
        return relevant[:limit], f"RSS Live ({len(relevant[:limit])} items)"
    return items[:limit], f"RSS Live ({len(items[:limit])} items)"
