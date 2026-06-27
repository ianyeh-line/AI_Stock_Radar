"""Markdown report renderer for Decision Cards."""

from datetime import date
from pathlib import Path

from radar.models.domain import DailyDecision, Evidence


def _tone_icon(evidence: Evidence) -> str:
    if evidence.tone == "positive":
        return "🟢"
    if evidence.tone == "negative":
        return "🔴"
    return "🟡"


def render_markdown(decision: DailyDecision) -> str:
    today = date.today().isoformat()
    lines: list[str] = []

    lines.append("# AI Stock Radar Daily Report")
    lines.append("")
    lines.append(f"Date: {today}")
    lines.append(f"Version: v{decision.version}")
    lines.append("")
    lines.append("## Today's Radar")
    lines.append("")
    lines.append(f"- Market View: **{decision.market_view}**")
    lines.append(f"- AI Confidence: **{decision.ai_confidence}%**")
    lines.append(f"- News Source: **{decision.news_source}**")
    lines.append(f"- News Analyzed: **{decision.news_count}**")
    lines.append("")
    lines.append("## Today's Action")
    lines.append("")
    lines.append(decision.today_action)
    lines.append("")
    lines.append("## Radar Top 5")
    lines.append("")
    lines.append("| Rank | Stock | Radar Score | Decision | Confidence | Key Reason |")
    lines.append("|---:|---|---:|---|---:|---|")
    for idx, card in enumerate(decision.cards, start=1):
        lines.append(
            f"| {idx} | {card.ticker} {card.name} | {card.radar_score} | {card.decision} | {card.confidence}% | {card.reason} |"
        )
    lines.append("")
    lines.append("## Decision Cards")
    lines.append("")

    for card in decision.cards:
        lines.append("---")
        lines.append("")
        lines.append(f"### {card.ticker} {card.name}")
        lines.append("")
        lines.append(f"**Radar Score:** {card.radar_score}  ")
        lines.append(f"**Decision:** {card.decision}  ")
        lines.append(f"**Confidence:** {card.confidence}%")
        lines.append("")
        lines.append("#### Why")
        lines.append("")
        lines.append(card.reason)
        lines.append("")
        lines.append("#### Evidence")
        lines.append("")
        for item in card.evidence:
            icon = _tone_icon(item)
            sign = "+" if item.score > 0 else ""
            lines.append(f"- {icon} **{item.label} ({sign}{item.score})**: {item.reason} _[{item.source}]_")
        lines.append("")
        lines.append("#### Action")
        lines.append("")
        lines.append(card.action)
        lines.append("")

    lines.append("## Risk Alert")
    lines.append("")
    for risk in decision.risk_alerts:
        lines.append(f"- ⚠️ {risk}")
    lines.append("")
    lines.append("## Product Note")
    lines.append("")
    lines.append("v0.5.0 focuses on Explainable Decision Cards. Scores are rule-based and intended for workflow validation, not investment advice.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "daily_report.md"
    path.write_text(content, encoding="utf-8")
    return path
