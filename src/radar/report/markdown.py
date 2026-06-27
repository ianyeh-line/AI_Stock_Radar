"""Markdown report renderer."""

from datetime import date
from pathlib import Path

from radar.models.domain import DailyDecision


def render_report(decision: DailyDecision) -> str:
    today = date.today().isoformat()
    lines: list[str] = [
        "# AI Stock Radar Daily Report",
        "",
        f"Date: {today}",
        "",
        "## Today's Radar",
        "",
        f"- Market View: {decision.market_view}",
        f"- AI Confidence: {decision.confidence}%",
        f"- Key Message: {decision.key_message}",
        "",
        "## Radar Top 5",
        "",
        "| Rank | Stock | Score | Decision | Confidence | Action |",
        "|---:|---|---:|---|---:|---|",
    ]

    for card in decision.top_cards:
        lines.append(
            f"| {card.rank} | {card.stock} | {card.score} | {card.decision} | {card.confidence}% | {card.action} |"
        )

    lines.extend(["", "## Evidence by Stock", ""])
    for card in decision.top_cards:
        lines.extend([f"### {card.rank}. {card.stock}", ""])
        for evidence in card.evidence:
            lines.append(f"- {evidence}")
        lines.extend([f"- Risk: {card.risk}", ""])

    lines.extend(["## Market Signals", ""])
    for item in decision.news_items:
        icon = "✅" if item.impact == "positive" else "⚠️" if item.impact == "negative" else "ℹ️"
        lines.extend(
            [
                f"### {icon} {item.title}",
                "",
                f"- Source: {item.source}",
                f"- Signal: {item.signal}",
                f"- Impact: {item.impact}",
                f"- So What: {item.summary}",
                f"- Affected Stocks: {'、'.join(item.affected_stocks)}",
                "",
            ]
        )

    lines.extend(["## Today's Action", ""])
    for action in decision.actions:
        lines.append(f"- {action}")

    lines.extend(["", "## Risk Alert", ""])
    for risk in decision.risks:
        lines.append(f"- {risk}")

    lines.append("")
    return "\n".join(lines)


def save_report(content: str, path: Path = Path("output/daily_report.md")) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
