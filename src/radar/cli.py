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
    print("🚀 AI Stock Radar v3.5.4")
    print(f"交易狀態：{payload['trading_status']['session']}")
    print(f"市場結論：{payload['market_view']}")
    source = payload.get("data_source_summary", {})
    print(f"資料基準日：預期 {source.get('expected_latest_date', '未知')} / 實際 {source.get('price_date_min', '未知')}~{source.get('price_date_max', '未知')}")
    print(f"資料狀態：{source.get('truth_status', '未知')}")
    print(f"資料來源：官方採用 {source.get('official_confirmed', 0)} / Yahoo採用 {source.get('yahoo_selected', source.get('yahoo_newer_than_official', 0) + source.get('yahoo_only', 0))} / Fallback {source.get('fallback', 0)}")
    print("今日可買進：")
    for idx, card in enumerate(payload["buy_list"][:5], start=1):
        print(f"  {idx}. {card['label']} | {card['grade']} | {card['setup']} | {card['score']} | {card['action']}")
    print("Report generated: output/daily_report.md")
    print("Dashboard data generated: output/dashboard_data.json")


if __name__ == "__main__":
    main()
