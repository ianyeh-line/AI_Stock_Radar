"""Report generation."""

from __future__ import annotations

import json
from pathlib import Path

from radar.teacher.decision import run_teacher_pipeline
from radar.teacher.decision_loop import save_decision_journal


REPORT_VERSION = "3.10.0"


def save_outputs(payload: dict) -> None:
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / "dashboard_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "daily_report.md").write_text(build_markdown(payload), encoding="utf-8")
    save_decision_journal(payload)


def _price_line(card: dict) -> str:
    t = card.get("tech", {})
    change = t.get("change_pct", 0)
    arrow = "▲" if change > 0 else "▼" if change < 0 else "—"
    return f"今日股價：{t.get('close')}（{arrow} {change}%）"


def _card_teacher_lines(card: dict) -> list[str]:
    narrative = card.get("teacher_narrative") or {}
    t = card.get("tech", {})
    lines = [
        f"### {card['label']}｜{card['setup']}｜Radar {card['score']}｜等級 {card['grade']}",
        f"- {_price_line(card)}｜資料日：{card.get('latest_date')}",
        f"- 老師判斷：{narrative.get('teacher_judgement', card.get('action', ''))}",
        f"- 技術面：{narrative.get('technical', '')}",
        f"- 籌碼面：{narrative.get('chip', '')}",
        f"- 產業 / 消息面：{narrative.get('news', '')}",
        f"- 支撐壓力：{narrative.get('support_resistance', '')}",
        f"- A劇本：{narrative.get('scenario_a', '')}",
        f"- B劇本：{narrative.get('scenario_b', '')}",
        f"- C劇本：{narrative.get('scenario_c', '')}",
        f"- 未持有者：{narrative.get('no_position_strategy', '')}",
        f"- 已持有者：{narrative.get('holding_strategy', '')}",
        f"- 風險提醒：{narrative.get('risk', card.get('risk', ''))}",
        f"- MACD：DIF {t.get('macd', {}).get('macd')}｜DEA {t.get('macd', {}).get('signal')}｜0軸 {t.get('macd', {}).get('zero_axis_status')}",
        "",
    ]
    return lines



def _strength_lines(payload: dict) -> list[str]:
    strength = payload.get("strong_momentum") or {}
    gap = payload.get("strength_gap_analysis") or {}
    lines = ["", "## 今日強勢股雷達", gap.get("summary", "今日強勢股雷達尚未產生落差分析。"), ""]

    def add_rows(title: str, rows: list[dict], empty: str) -> None:
        lines.extend([f"### {title}"])
        if not rows:
            lines.append(empty)
            lines.append("")
            return
        for row in rows[:8]:
            reasons = "；".join(row.get("strength_reasons", [])[:3])
            lines.append(
                f"- {row.get('label')}｜強勢分 {row.get('strength_score')}｜{row.get('strength_category')}｜"
                f"今日股價 {row.get('close')}（{row.get('change_pct')}%）｜量能比 {row.get('volume_ratio')}｜"
                f"老師判斷：{row.get('teacher_view')}｜理由：{reasons}"
            )
        lines.append("")

    coverage = strength.get("data_coverage", {})
    if coverage:
        lines.append(f"全市場掃描：{coverage.get('total_market_rows', 0)} 檔｜候選分析：{coverage.get('classified_rows', coverage.get('candidate_rows', 0))} 檔｜{coverage.get('message', '')}")
        lines.append("")
    add_rows("可追強勢", strength.get("chaseable_list", []), "今日沒有同時符合強勢與合理操作空間的可追名單。")
    add_rows("今日強勢", strength.get("strong_list", []), "今日沒有明確強勢股主線。")
    add_rows("漲停 / 接近漲停觀察", strength.get("limit_watch", []), "今日沒有接近漲停觀察名單。")
    add_rows("已漲不追", strength.get("no_chase_list", []), "今日沒有明顯已漲不追名單。")
    add_rows("明日接力觀察", strength.get("tomorrow_watch", []), "今日沒有明確明日接力名單。")
    rankings = strength.get("ranking_tables", {})
    if rankings.get("top_gainers"):
        lines.extend(["### 全市場漲幅排行 Top 5"])
        for row in rankings.get("top_gainers", [])[:5]:
            lines.append(f"- {row.get('label')}｜{row.get('change_pct')}%｜股價 {row.get('close')}｜成交量 {row.get('volume')}")
        lines.append("")
    return lines


def _decision_loop_lines(payload: dict) -> list[str]:
    loop = payload.get("decision_loop") or {}
    session = loop.get("session_mode") or {}
    lines = [
        "",
        "## 決策閉環：盤前計畫 → 盤中觀察 → 盤後檢討 → 明日準備",
        f"**目前模式：{session.get('mode', '未判斷')}**",
        session.get("headline", ""),
        "",
        "### 今日作戰計畫",
    ]
    plan = loop.get("pre_market_plan") or []
    if not plan:
        lines.append("目前沒有通過品質閘門的 A 級作戰標的；先以等待突破、強勢接力與持股管理為主。")
    for row in plan[:5]:
        lines.append(f"- {row.get('label')}｜{row.get('type')}｜{row.get('watch_price')}｜{row.get('action')}")

    review = loop.get("recommendation_review") or {}
    lines += ["", "### 前次推薦檢討"]
    lines.append(review.get("summary", "尚無檢討資料。"))
    for row in review.get("rows", [])[:8]:
        lines.append(
            f"- {row.get('label')}｜前次 {row.get('previous_close')} → 本次 {row.get('current_close')}｜"
            f"變化 {row.get('change_since')}%｜{row.get('review')}"
        )

    strength_loop = loop.get("strength_loop") or {}
    lines += ["", "### AI 沒選到強勢股的原因"]
    missed = strength_loop.get("missed_strength") or []
    if not missed:
        lines.append("目前沒有明確『強勢但未列入可買』的落差，或強勢資料尚不足。")
    for row in missed[:8]:
        lines.append(f"- {row.get('label')}｜漲跌 {row.get('change_pct')}%｜{row.get('reason')}｜下一步：{row.get('next_step')}")

    tomorrow = loop.get("tomorrow_preparation") or {}
    lines += ["", "### 明日準備"]
    lines.append(tomorrow.get("summary", ""))
    for row in tomorrow.get("rows", [])[:10]:
        lines.append(f"- {row.get('label')}｜{row.get('source')}｜{row.get('plan')}")
    lines.append("")
    return lines

def _data_source_footer(payload: dict) -> list[str]:
    summary = payload.get("data_source_summary") or {}
    return [
        "---",
        "## 資料來源與更新說明",
        f"- 預期資料基準日：{summary.get('expected_latest_date', '未知')}",
        f"- 實際價格資料日期範圍：{summary.get('price_date_min', '未知')}～{summary.get('price_date_max', '未知')}",
        f"- 資料狀態：{summary.get('truth_status', '未知')}",
        f"- 官方採用：{summary.get('official_confirmed', 0)} 檔",
        f"- Yahoo 採用：{summary.get('yahoo_selected', summary.get('yahoo_newer_than_official', 0) + summary.get('yahoo_only', 0))} 檔",
        f"- Fallback：{summary.get('fallback', 0)} 檔",
        f"- 說明：{summary.get('description', '依目前交易狀態採用最新可得資料。')}",
        "",
    ]


def build_markdown(payload: dict) -> str:
    status = payload["trading_status"]
    lines = [
        f"# AI Stock Radar {REPORT_VERSION} 股市老師每日報告",
        "",
        f"日期：{status['date']}（星期{status['weekday']}）｜交易狀態：{status['session']}｜台灣時間：{status.get('time', '--:--')}",
        "",
        "## 股市老師今日結論",
        payload.get("market_view", ""),
    ]
    lines += _decision_loop_lines(payload)
    lines += ["", "## 今日可買進名單"]
    if not payload.get("buy_list"):
        lines.append("今日沒有 A 級可買進名單；老師不硬湊推薦，先等價格、量能與結構條件更完整。")
    for c in payload.get("buy_list", [])[:8]:
        lines.extend(_card_teacher_lines(c))

    lines += _strength_lines(payload)

    lines += ["", "## 等待突破 / 拉回觀察"]
    if not payload.get("wait_list"):
        lines.append("今日沒有明確等待突破名單。")
    for c in payload.get("wait_list", [])[:8]:
        narrative = c.get("teacher_narrative") or {}
        lines += [
            f"- {c['label']}｜{c['setup']}｜Radar {c['score']}：{narrative.get('teacher_judgement', c.get('action', ''))}",
        ]

    lines += ["", "## 避免名單"]
    if not payload.get("avoid_list"):
        lines.append("今日沒有明確避免名單。")
    for c in payload.get("avoid_list", [])[:8]:
        narrative = c.get("teacher_narrative") or {}
        lines.append(f"- {c['label']}｜Radar {c['score']}：{narrative.get('teacher_judgement', c.get('action', ''))}")

    lines += ["", "## MACD 0軸觀察"]
    macd_zero_items = payload.get("macd_zero_axis_list", [])[:10]
    if not macd_zero_items:
        lines.append("目前沒有符合『DIF 從 0 軸下方即將或剛翻正』且資料有效的名單；沒有訊號時不硬湊。")
    for c in macd_zero_items:
        t = c["tech"]
        lines.append(f"- {c['label']}：{t['macd'].get('zero_axis_status')}｜DIF {t['macd']['macd']}｜DEA {t['macd']['signal']}｜今日股價 {t['close']}｜{c.get('teacher_narrative', {}).get('teacher_judgement', c['action'])}")

    lines += ["", "## 持股總教練"]
    lines.append(payload.get("portfolio_coach", {}).get("summary", "尚未建立持股。"))
    for row in payload.get("portfolio_coach", {}).get("rows", [])[:10]:
        card = row.get("card", {})
        tech = card.get("tech", {})
        lines.append(f"- {row['stock']}：Radar {card.get('score')}｜今日股價 {tech.get('close')}（{tech.get('change_pct')}%）｜損益 {row['pnl']}（{row['pnl_pct']}%）｜{row['advice']}")

    lines += _data_source_footer(payload)
    return "\n".join(lines)


def run_and_save() -> dict:
    payload = run_teacher_pipeline()
    save_outputs(payload)
    return payload
