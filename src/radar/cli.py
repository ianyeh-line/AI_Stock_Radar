"""Command line entry point for AI Stock Radar."""

from __future__ import annotations

import argparse

from radar.engine.decision import run_decision_pipeline, save_dashboard_payload
from radar.report.markdown import build_markdown_report, save_markdown_report


def run() -> None:
    payload = run_decision_pipeline()
    dashboard_path = save_dashboard_payload(payload)
    report_path = save_markdown_report(build_markdown_report(payload))
    quality = payload["pm_brief"]["data_quality"]

    print(f"🚀 AI Stock Radar v{payload['version']}")
    print(f"News Source: {payload['news_source']}")
    print(f"Price Source: Yahoo Finance {quality['price_live_count']} / Fallback {quality['price_fallback_count']}")
    print(f"Data Frequency: {quality.get('price_frequency')} / {quality.get('news_frequency')}")
    print(f"Price Latest Date: {quality.get('price_latest_date_min')} ~ {quality.get('price_latest_date_max')}")
    print(f"Market View: {payload['market_view']}")
    print(f"AI Confidence: {payload['ai_confidence']}%")
    print(f"User Watchlist: {quality.get('user_watchlist_count', 0)} / Portfolio: {quality.get('portfolio_count', 0)}")
    print(f"Institutional Flow: TWSE {quality.get('institutional_official_count', 0)} / Fallback {quality.get('institutional_fallback_count', 0)}")
    teacher = payload.get("teacher_buy_list", {})
    print("今日可買進名單:")
    ready = teacher.get("ready_to_buy", [])
    if ready:
        for idx, item in enumerate(ready[:5], 1):
            print(
                f"  {idx}. {item['display_name']} | 等級 {item['grade']} | {item['action_type']} | "
                f"買進區間 {item['suggested_entry_zone']} | 突破 {item['breakout_trigger']} | "
                f"失效 {item['invalidation_price']} | 停利 {item['first_profit_take']}/{item['second_profit_take']}"
            )
    else:
        print("  今日無 A 級直接可行動標的，以下列出 B 級條件候選:")
        seen = set()
        b_items = []
        for item in teacher.get("wait_breakout", []) + teacher.get("pullback_watch", []):
            if item["symbol"] in seen:
                continue
            seen.add(item["symbol"])
            b_items.append(item)
        for idx, item in enumerate(b_items[:5], 1):
            print(
                f"  B {idx}. {item['display_name']} | {item['action_type']} | "
                f"買進區間 {item['suggested_entry_zone']} | 突破 {item['breakout_trigger']} | "
                f"失效 {item['invalidation_price']}"
            )

    print("Top 5 Decision Cards:")
    for idx, card in enumerate(payload["decision_cards"][:5], 1):
        print(
            f"  {idx}. {card['display_name']} | {card['radar_score']} | "
            f"{card['decision']} | {card['confidence']}% | Close {card['latest_close']} ({card['change_pct']}%) | "
            f"突破 {card.get('breakout_price')} / 拉回 {card.get('pullback_low')}~{card.get('pullback_high')} / 減碼 {card.get('reduce_price')} / 法人 {card.get('institutional_summary', '')}"
        )
    print("MACD 觀察名單 Top 3:")
    for idx, item in enumerate(payload["macd_candidates"][:3], 1):
        print(
            f"  {idx}. {item['display_name']} | {item.get('macd_status', '')} | "
            f"{item['score']} | Hist {item['hist_current']} | RSI {item['rsi']}"
        )
    print(f"Report generated: {report_path}")
    print(f"Dashboard data generated: {dashboard_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="radar", description="AI Stock Radar CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Generate today's radar report and dashboard data")
    args = parser.parse_args()
    if args.command in (None, "run"):
        run()


if __name__ == "__main__":
    main()
