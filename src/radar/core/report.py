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
        "# AI Stock Radar 3.2.4 股市老師盤前決策",
        "",
        f"日期：{status['date']}（星期{status['weekday']}）",
        f"交易狀態：{status['session']}｜台灣時間：{status.get('time', '--:--')}",
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
            f"- 0軸 MACD：{t['macd'].get('zero_axis_status')}｜MACD(DIF)：{t['macd'].get('macd')}｜DEA：{t['macd'].get('signal')}",
            f"- 資料可信度：{c.get('data_trust', {}).get('status', '未知')}｜來源：{c.get('price_source')}｜資料日：{c.get('latest_date')}",
            f"- 建議：{c['action']}",
            f"- 失效：{c['risk']}",
            f"- 理由：{'、'.join(c['reasons'][:5])}",
            "",
        ]
    lines += [
        "## MACD 即將從 0 軸翻正觀察名單",
        "> 以 MACD(DIF) 與 0 軸位置判斷；若 DIF 已在 0 軸上方，不會標示為 0 軸下方偏弱。",
    ]
    macd_zero_items = payload.get("macd_zero_axis_list", [])[:10]
    if not macd_zero_items:
        lines.append("目前沒有符合『即將或剛從 0 軸轉強』的名單；沒有訊號時不硬湊推薦。")
    for c in macd_zero_items:
        t = c["tech"]
        lines.append(f"- {c['label']}：{t['macd'].get('zero_axis_status')}｜MACD(DIF) {t['macd']['macd']}｜DEA {t['macd']['signal']}｜最新價 {t['close']}｜{c['decision']}")
    lines += ["", "## 等待突破 / 拉回名單"]
    for c in payload["wait_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 避免名單"]
    for c in payload["avoid_list"][:5]:
        lines.append(f"- {c['label']}：{c['action']}")
    lines += ["", "## 資料可信度"]
    bad = [c for c in payload.get("all_cards", []) if not (c.get("data_trust") or {}).get("actionable")]
    good_count = len(payload.get("all_cards", [])) - len(bad)
    lines.append(f"- 可作為操作參考：{good_count} 檔")
    lines.append(f"- 資料不足僅觀察：{len(bad)} 檔")
    for c in bad[:8]:
        warnings = "、".join((c.get("data_trust") or {}).get("warnings", [])[:2])
        lines.append(f"- {c['label']}：{warnings}")
    lines += ["", "## 持股總教練", payload["portfolio_coach"]["summary"]]
    return "\n".join(lines)


def run_and_save() -> dict:
    payload = run_teacher_pipeline()
    save_outputs(payload)
    return payload
