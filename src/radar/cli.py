"""CLI entry point for AI Stock Radar."""

import argparse

from radar.datasource.mock_news import load_news
from radar.engine.decision import build_daily_decision
from radar.report.markdown import render_report, save_report


def run() -> None:
    news_items = load_news()
    decision = build_daily_decision(news_items)
    report = render_report(decision)
    report_path = save_report(report)

    print("🚀 AI Stock Radar v0.3.0")
    print(f"Market View: {decision.market_view}")
    print(f"AI Confidence: {decision.confidence}%")
    print("Top 5:")
    for card in decision.top_cards:
        print(f"  {card.rank}. {card.stock} | {card.score} | {card.decision} | {card.confidence}%")
    print(f"Report generated: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="radar")
    parser.add_argument("command", nargs="?", default="run", choices=["run"])
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
