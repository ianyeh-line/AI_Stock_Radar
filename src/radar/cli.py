"""CLI entry point."""

from __future__ import annotations

import argparse

from radar.core.report import run_and_save


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="run")
    args = parser.parse_args()
    if args.command != "run":
        raise SystemExit("Usage: python -m radar.cli run")
    payload = run_and_save()
    print("🚀 AI Stock Radar v3.2.4")
    print(f"交易狀態：{payload['trading_status']['session']}")
    print(f"市場結論：{payload['market_view']}")
    print("今日可買進：")
    for idx, card in enumerate(payload["buy_list"][:5], start=1):
        print(f"  {idx}. {card['label']} | {card['grade']} | {card['setup']} | {card['score']} | {card['action']}")
    print("Report generated: output/daily_report.md")
    print("Dashboard data generated: output/dashboard_data.json")


if __name__ == "__main__":
    main()
