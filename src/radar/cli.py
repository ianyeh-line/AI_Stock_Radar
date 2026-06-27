"""Command line entry point for AI Stock Radar."""

import argparse

from radar.datasource.rss_news import load_news
from radar.engine.decision import build_decision
from radar.report.markdown import render_markdown, save_dashboard_snapshot, save_report


def run() -> None:
    news_source, news_items = load_news()
    decision = build_decision(news_source, news_items)
    report = render_markdown(decision)
    report_path = save_report(report)
    snapshot_path = save_dashboard_snapshot(decision)

    print(f"🚀 AI Stock Radar v{decision.version}")
    print(f"新聞來源：{decision.news_source}（{decision.news_count} 則）")
    print(f"今日盤勢：{decision.market_view}")
    print(f"AI 信心：{decision.ai_confidence}%")
    print("Top 5 決策卡：")
    for idx, card in enumerate(decision.cards[:5], start=1):
        print(
            f"  {idx}. {card.ticker} {card.name} | "
            f"Radar {card.radar_score} | 新聞 {card.news_score} | 技術 {card.technical_score} | "
            f"{card.decision} | {card.confidence}% | {card.reason}"
        )
    print(f"報告已產生：{report_path}")
    print(f"Dashboard 資料已產生：{snapshot_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="radar")
    parser.add_argument("command", nargs="?", default="run", choices=["run"])
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
