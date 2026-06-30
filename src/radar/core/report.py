"""Report generation."""

from __future__ import annotations

import json
from pathlib import Path

from radar.teacher.decision import run_teacher_pipeline


def save_outputs(payload: dict) -> None:
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / "dashboard_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "daily_report.md").write_text(build_markdown(payload), encoding="utf-8")


def _data_source_lines(payload: dict) -> list[str]:
    summary = payload.get("data_source_summary") or {}
    return [
        "## 資料來源與可信度",
        f"- 官方盤後確認：{summary.get('official_confirmed', 0)} 檔",
        f"- Yahoo Only：{summary.get('yahoo_only', 0)} 檔",
        f"- Fallback：{summary.get('fallback', 0)} 檔",
        f"- 說明：{summary.get('description', 'TWSE / TPEx 官方資料優先；Yahoo 作為歷史線圖與 fallback。')}",
        "",
    ]


def build_markdown(payload: dict) -> str:
    status = payload["trading_status"]
    lines = [
        "# AI Stock Radar 3.4.0 股市老師盤前決策",
        "",
        f"日期：{status['date']}（星期{status['weekday']}）",
        f"交易狀態：{status['session']}｜台灣時間：{status.get('time', '--:--')}",
        f"市場結論：{payload['market_view']}",
        "",
        f"> {payload['teacher_summary']}",
        "",
    ]
    lines += _data_source_lines(payload)
    lines += ["## 今日可買進名單"]
    if not payload["buy_list"]:
        lines.append("今日沒有 A 級可買進名單。")
    for c in payload["buy_list"]:
        t = c["tech"]
        trust = c.get("data_trust", {})
        lines += [
            f"### {c['label']}｜{c['setup']}｜分數 {c['score']}｜信心 {c['confidence']}%",
            f"- 今日股價：{t['close']}（{t['change_pct']}%）｜資料日：{c['latest_date']}｜來源：{c['price_source']}",
            f"- 官方確認：{'是' if c.get('official_confirmed') else '否'}｜官方來源：{trust.get('official_source', '未取得')}",
            f"- 0軸 MACD：{t['macd'].get('zero_axis_status')}｜MACD(DIF)：{t['macd'].get('macd')}｜DEA：{t['macd'].get('signal')}",
            f"- 資料可信度：{trust.get('status', '未知')}｜來源：{c.get('price_source')}｜資料日：{c.get('latest_date')}",
            f"- 建議：{c['action']}",
            f"- 失效：{c['risk']}",
            f"- 理由：{'、'.join(c['reasons'][:5])}",
            "",
        ]
    lines += [
        "## MACD 0 軸觀察名單",
        "> 本版僅列出 DIF 從 0 軸下方即將翻正或剛翻正，且資料可信的個股。",
    ]
    macd_zero_items = payload.get("macd_zero_axis_list", [])[:10]
    if not macd_zero_items:
        lines.append("目前沒有符合『即將或剛從 0 軸轉強』且資料可信的名單；沒有訊號時不硬湊推薦。")
    for c in macd_zero_items:
        t = c["tech"]
        lines.append(f"- {c['label']}：{t['macd'].get('zero_axis_status')}｜MACD(DIF) {t['macd']['macd']}｜DEA {t['macd']['signal']}｜今日股價 {t['close']}｜{c['decision']}")
    lines += ["", "## 等待突破 / 拉回名單"]
    for c in payload["wait_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 避免名單"]
    for c in payload["avoid_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 持股總教練", payload["portfolio_coach"]["summary"]]
    for row in payload.get("portfolio_coach", {}).get("rows", [])[:10]:
        card = row.get("card", {})
        tech = card.get("tech", {})
        lines.append(f"- {row['stock']}：今日股價 {tech.get('close')}（{tech.get('change_pct')}%）｜損益 {row['pnl']}（{row['pnl_pct']}%）｜{row['advice']}")
    return "\n".join(lines)


def run_and_save() -> dict:
    payload = run_teacher_pipeline()
    save_outputs(payload)
    return payload
