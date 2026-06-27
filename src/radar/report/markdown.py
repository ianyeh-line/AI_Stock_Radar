"""Markdown report generator."""

from datetime import datetime
from pathlib import Path

from radar.models.domain import DailyDecision


def build_markdown(decision: DailyDecision) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []
    lines.append("# AI Stock Radar Daily Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append("## Today's Radar")
    lines.append("")
    lines.append(f"- Market View: {decision.market_view}")
    lines.append(f"- AI Confidence: {decision.confidence}%")
    lines.append(f"- Action: {decision.action}")
    lines.append("")
    lines.append("## Radar Top 5")
    lines.append("")
    lines.append("| Rank | Stock | Radar Score | Decision | Confidence |")
    lines.append("|---:|---|---:|---|---:|")
    for index, stock in enumerate(decision.top_stocks, start=1):
        lines.append(f"| {index} | {stock.symbol} {stock.name} | {stock.score} | {stock.decision} | {stock.confidence}% |")
    lines.append("")
    lines.append("## Evidence by Stock")
    lines.append("")
    for stock in decision.top_stocks:
        lines.append(f"### {stock.symbol} {stock.name}")
        lines.append("")
        lines.append("Evidence:")
        for evidence in stock.evidence:
            lines.append(f"- {evidence}")
        if stock.risks:
            lines.append("")
            lines.append("Risks:")
            for risk in stock.risks:
                lines.append(f"- {risk}")
        lines.append("")
    lines.append("## Market Signals")
    lines.append("")
    for signal in decision.market_signals:
        lines.append(f"- {signal}")
    lines.append("")
    lines.append("## Risk Alert")
    lines.append("")
    for risk in decision.risks:
        lines.append(f"- {risk}")
    lines.append("")
    lines.append("## Source News")
    lines.append("")
    for item in decision.news_items[:10]:
        suffix = f" ({item.source})" if item.source else ""
        lines.append(f"- {item.title}{suffix}")
    lines.append("")
    return "\n".join(lines)


def save_report(content: str) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "daily_report.md"
    path.write_text(content, encoding="utf-8")
    return path
