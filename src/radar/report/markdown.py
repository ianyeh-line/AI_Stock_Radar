"""Markdown report generator."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


def _decision_icon(decision: str) -> str:
    return {
        "波段買進": "🟢",
        "波段觀察": "🟡",
        "等待": "⚪",
        "減碼/避開": "🔴",
    }.get(decision, "⚪")


def build_markdown_report(payload: dict[str, Any]) -> str:
    today = date.today().isoformat()
    cards = payload["decision_cards"]
    macd_candidates = payload["macd_candidates"]
    news = payload["news"]

    report = f"""# AI Stock Radar 每日決策報告

日期：{today}  
版本：v{payload["version"]} Stage 5  
新聞來源：{payload["news_source"]}

## 今日總結

**市場判斷：{payload["market_view"]}**  
**AI 信心指數：{payload["ai_confidence"]}%**

{payload["market_summary"]}

## 波段操作 Top 5

| 排名 | 個股 | Radar | 決策 | 信心 | 投資經理人評語 |
|---:|---|---:|---|---:|---|
"""
    for idx, card in enumerate(cards[:5], 1):
        icon = _decision_icon(card["decision"])
        report += f"| {idx} | {card['display_name']} | {card['radar_score']} | {icon} {card['decision']} | {card['confidence']}% | {card['swing_view']} |\n"

    report += """
## AI 選出 MACD 即將翻正十檔

| 排名 | 個股 | 分數 | MACD 前值 | MACD 目前 | RSI | 理由 |
|---:|---|---:|---:|---:|---:|---|
"""
    for idx, item in enumerate(macd_candidates, 1):
        report += f"| {idx} | {item['symbol']} {item['name']} | {item['score']} | {item['hist_prev']} | {item['hist_current']} | {item['rsi']} | {item['reason']} |\n"

    report += """
## 個股 Decision Cards

"""
    for card in cards[:10]:
        icon = _decision_icon(card["decision"])
        report += f"""### {icon} {card['display_name']}

- Radar Score：{card['radar_score']}
- 決策：{card['decision']}
- 信心：{card['confidence']}%
- 波段評價：{card['swing_view']}
- 進場條件：{card['entry_condition']}
- 續抱條件：{card['hold_condition']}
- 減碼條件：{card['reduce_condition']}
- 風險提醒：{card['risk_note']}

Evidence：
"""
        for evidence in card["evidence"][:5]:
            direction = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
            report += f"- {direction} {evidence['label']}：{evidence['explanation']}\n"
        report += "\n"

    report += """
## 今日重要新聞與影響

"""
    for item in news[:8]:
        icon = "✅" if item["impact"] == "positive" else "⚠️" if item["impact"] == "negative" else "➖"
        affected = "、".join(item["affected_stocks"]) if item["affected_stocks"] else "暫無明確個股"
        report += f"""### {icon} {item['title_zh']}

- 來源：{item['source']}
- Signal：{item['signal']}
- 摘要：{item['summary_zh']}
- 受影響個股：{affected}

"""

    return report


def save_markdown_report(content: str) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "daily_report.md"
    path.write_text(content, encoding="utf-8")
    return path
