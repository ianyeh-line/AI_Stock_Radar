"""Command line entry point for AI Stock Radar."""

from __future__ import annotations

import argparse

from radar.datasource.rss_news import fetch_rss_news
from radar.engine.decision import build_dashboard_payload, build_decision_cards, save_dashboard_payload
from radar.engine.personalization import load_investor_profile
from radar.knowledge.stock_map import load_stock_universe
from radar.report.markdown import build_markdown_report, save_markdown_report


def run() -> None:
    news_items, news_source = fetch_rss_news(limit=12)
    stocks = load_stock_universe()
    profile = load_investor_profile()
    cards = build_decision_cards(news_items, stocks, profile)
    payload = build_dashboard_payload(news_items, cards, stocks, profile, news_source)
    dashboard_path = save_dashboard_payload(payload)
    report = build_markdown_report(payload)
    report_path = save_markdown_report(report)

    print("🚀 AI Stock Radar v0.9.0")
    print(f"投資風格：{profile.get('style_zh', '波段操作')}")
    print(f"新聞來源：{news_source}")
    print(f"市場判斷：{payload['market_view']}")
    print(f"AI 信心指數：{payload['ai_confidence']}%")
    print("波段操作 Top 5:")
    for idx, card in enumerate(payload["decision_cards"][:5], 1):
        print(f"  {idx}. {card['display_name']} | {card['radar_score']} | {card['decision']} | {card['confidence']}%")
    print("MACD 即將翻正 Top 10:")
    for idx, item in enumerate(payload["macd_candidates"][:10], 1):
        print(f"  {idx}. {item['symbol']} {item['name']} | {item['score']} | hist {item['hist_prev']} → {item['hist_current']}")
    print(f"Report generated: {report_path}")
    print(f"Dashboard data generated: {dashboard_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Stock Radar CLI")
    parser.add_argument("command", nargs="?", default="run", choices=["run"])
    args = parser.parse_args()
    if args.command == "run":
        run()


if __name__ == "__main__":
    main()
