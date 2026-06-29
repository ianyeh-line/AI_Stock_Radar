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


def build_markdown(payload: dict) -> str:
    status = payload["trading_status"]
    lines = [
        "# AI Stock Radar 3.0 股市老師盤前決策",
        "",
        f"日期：{status['date']}（星期{status['weekday']}）",
        f"交易狀態：{status['session']}",
        f"市場結論：{payload['market_view']}",
        "",
        f"> {payload['teacher_summary']}",
        "",
        "## 今日可買進名單",
    ]
    if not payload["buy_list"]:
        lines.append("今日沒有 A 級可買進名單。")
    for c in payload["buy_list"]:
        t = c["tech"]
        lines += [
            f"### {c['label']}｜{c['setup']}｜分數 {c['score']}｜信心 {c['confidence']}%",
            f"- 最新價：{t['close']}（{t['change_pct']}%）｜資料日：{c['latest_date']}｜來源：{c['price_source']}",
            f"- 建議：{c['action']}",
            f"- 失效：{c['risk']}",
            f"- 理由：{'、'.join(c['reasons'][:5])}",
            "",
        ]
    lines += ["## 等待突破 / 拉回名單"]
    for c in payload["wait_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 避免名單"]
    for c in payload["avoid_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 持股總教練", payload["portfolio_coach"]["summary"]]
    return "\n".join(lines)


def run_and_save() -> dict:
    payload = run_teacher_pipeline()
    save_outputs(payload)
    return payload
