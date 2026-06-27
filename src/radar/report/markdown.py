"""Markdown report renderer for AI Stock Radar."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from radar.models.domain import DailyDecision


def render_markdown(decision: DailyDecision) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = f"""# AI Stock Radar 每日決策報告

產生時間：{generated_at}  
版本：v{decision.version}  
新聞來源：{decision.news_source}（{decision.news_count} 則）

## 今日總覽

| 項目 | 結果 |
|---|---|
| 今日盤勢 | {decision.market_view} |
| AI 信心 | {decision.ai_confidence}% |
| 產品階段 | Stage 4：Decision OS v1 |

## 今日行動建議

{decision.today_action}

## Top Decision Cards

| 排名 | 個股 | Radar | 新聞 | 技術 | 風險 | 決策 | 信心 | 理由 |
|---:|---|---:|---:|---:|---:|---|---:|---|
"""

    for idx, card in enumerate(decision.cards, start=1):
        report += (
            f"| {idx} | {card.ticker} {card.name} | {card.radar_score} | "
            f"{card.news_score} | {card.technical_score} | {card.risk_score} | "
            f"{card.decision} | {card.confidence}% | {card.reason} |\n"
        )

    report += "\n## 決策卡明細\n\n"

    for card in decision.cards:
        tech = card.technical
        report += f"""### {card.ticker} {card.name}

- **Radar Score：** {card.radar_score}
- **新聞分數：** {card.news_score}
- **技術分數：** {card.technical_score}
- **風險分數：** {card.risk_score}
- **決策：** {card.decision}
- **信心：** {card.confidence}%
- **理由：** {card.reason}
- **行動：** {card.action}
- **進出場條件：** {card.position_rule}
- **風險提醒：** {card.risk_note}

#### 技術線圖快照

- 價格：{tech.price}
- MA5：{tech.ma5}
- MA20：{tech.ma20}
- MA60：{tech.ma60}
- RSI14：{tech.rsi14}
- 趨勢：{tech.trend}
- 資料來源：{tech.data_source}

#### Evidence Chain

"""
        if not card.evidence:
            report += "- 今日沒有足夠直接證據。\n\n"
        for ev in card.evidence:
            icon = "✅" if ev.tone == "positive" else "⚠️" if ev.tone == "negative" else "➖"
            sign = "+" if ev.score > 0 else ""
            report += f"- {icon} **{ev.category}｜{ev.signal_zh}** ({sign}{ev.score})｜{ev.source}｜{ev.reason}\n"
        report += "\n"

    report += "## 新聞影響鏈\n\n"
    report += "| 新聞中文摘要 | 訊號 | 情緒 | 受影響個股 |\n|---|---|---|---|\n"
    for item in decision.news_items[:15]:
        stocks = "、".join(item.tickers) if item.tickers else "大盤"
        sentiment = getattr(item, "sentiment_zh", "") or item.sentiment
        report += f"| {item.title_zh[:120]} | {item.signal_zh} | {sentiment} | {stocks} |\n"

    report += "\n## 風險提醒\n\n"
    for risk in decision.risk_alerts:
        report += f"- ⚠️ {risk}\n"

    return report


def save_report(content: str) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "daily_report.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def save_dashboard_snapshot(decision: DailyDecision) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    snapshot_path = output_dir / "dashboard_data.json"
    snapshot_path.write_text(
        json.dumps(asdict(decision), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return snapshot_path
