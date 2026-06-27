"""Command line interface for AI Stock Radar."""

import argparse

from radar import __version__
from radar.datasource.rss_news import fetch_market_news
from radar.engine.decision import build_decision
from radar.report.markdown import build_markdown, save_report


def run() -> None:
    news_items, live_news = fetch_market_news()
    decision = build_decision(news_items, live_news=live_news)
    report = build_markdown(decision)
    report_path = save_report(report)

    print(f"🚀 AI Stock Radar v{__version__}")
    print(f"News Source: {'RSS Live' if live_news else 'Fallback'}")
    print(f"Market View: {decision.market_view}")
    print(f"AI Confidence: {decision.confidence}%")
    print("Top 5:")
    for index, stock in enumerate(decision.top_stocks, start=1):
        print(f"  {index}. {stock.symbol} {stock.name} | {stock.score} | {stock.decision} | {stock.confidence}%")
    print(f"Report generated: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Stock Radar CLI")
    parser.add_argument("command", nargs="?", default="run", choices=["run"])
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
