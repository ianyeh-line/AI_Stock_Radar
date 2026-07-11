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
    print("🚀 AI Stock Radar v3.10.0")
    print(f"交易狀態：{payload['trading_status']['session']}")
    print(f"市場結論：{payload['market_view']}")
    source = payload.get("data_source_summary", {})
    print(f"資料基準日：預期 {source.get('expected_latest_date', '未知')} / 實際 {source.get('price_date_min', '未知')}~{source.get('price_date_max', '未知')}")
    print(f"資料狀態：{source.get('truth_status', '未知')}")
    print(f"資料來源：官方採用 {source.get('official_confirmed', 0)} / Yahoo採用 {source.get('yahoo_selected', source.get('yahoo_newer_than_official', 0) + source.get('yahoo_only', 0))} / Fallback {source.get('fallback', 0)}")
    print("今日可買進：")
    for idx, card in enumerate(payload["buy_list"][:5], start=1):
        print(f"  {idx}. {card['label']} | {card['grade']} | {card['setup']} | {card['score']} | {card['action']}")
    strength = payload.get("strong_momentum", {})
    coverage = strength.get("data_coverage", {})
    print(f"強勢股資料：{coverage.get('mode', 'unknown')} / 全市場 {coverage.get('total_market_rows', 0)} 檔 / 候選 {coverage.get('classified_rows', coverage.get('candidate_rows', 0))} 檔")
    print("可追強勢股：")
    for idx, row in enumerate(strength.get("chaseable_list", [])[:5], start=1):
        print(f"  {idx}. {row['label']} | 強勢分 {row['strength_score']} | {row['strength_category']} | 漲跌 {row['change_pct']}% | 量能比 {row['volume_ratio']}")
    print("今日強勢股：")
    for idx, row in enumerate(strength.get("strong_list", [])[:5], start=1):
        print(f"  {idx}. {row['label']} | 強勢分 {row['strength_score']} | {row['strength_category']} | 漲跌 {row['change_pct']}% | 量能比 {row['volume_ratio']}")
    print("強勢落差分析：" + payload.get("strength_gap_analysis", {}).get("summary", ""))
    print("Report generated: output/daily_report.md")
    print("Dashboard data generated: output/dashboard_data.json")


if __name__ == "__main__":
    main()
