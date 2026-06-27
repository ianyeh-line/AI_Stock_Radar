"""Command line entry point for AI Stock Radar."""

import argparse

from radar.datasource.rss_news import load_news
from radar.engine.decision import build_decision
from radar.report.markdown import render_markdown, save_report


def run() -> None:
    news_source, news_items = load_news()
    decision = build_decision(news_source, news_items)
    report = render_markdown(decision)
    report_path = save_report(report)

    print(f"🚀 AI Stock Radar v{decision.version}")
    print(f"News Source: {decision.news_source} ({decision.news_count} items)")
    print(f"Market View: {decision.market_view}")
    print(f"AI Confidence: {decision.ai_confidence}%")
    print("Top 5 Decision Cards:")
    for idx, card in enumerate(decision.cards, start=1):
        print(
            f"  {idx}. {card.ticker} {card.name} | "
            f"{card.radar_score} | {card.decision} | {card.confidence}% | {card.reason}"
        )
    print(f"Report generated: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="radar")
    parser.add_argument("command", nargs="?", default="run", choices=["run"])
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
