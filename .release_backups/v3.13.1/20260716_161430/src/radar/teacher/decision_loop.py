"""Daily decision loop for AI Stock Radar.

v3.10.0 shifts the product from a one-shot recommendation page into a
repeatable teacher workflow:

    盤前計畫 -> 盤中觀察 -> 盤後檢討 -> 明日準備

The module intentionally avoids pretending it has complete history when a
journal is not yet available. It still gives a useful first-run baseline and
starts saving future decisions for day-over-day review.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

JOURNAL_DIR = Path("data/journal")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _card_snapshot(card: dict) -> dict:
    tech = card.get("tech") or {}
    narrative = card.get("teacher_narrative") or {}
    return {
        "symbol": card.get("symbol"),
        "name": card.get("name"),
        "label": card.get("label"),
        "grade": card.get("grade"),
        "setup": card.get("setup"),
        "score": card.get("score"),
        "decision": card.get("decision"),
        "action": card.get("action"),
        "close": tech.get("close"),
        "change_pct": tech.get("change_pct"),
        "support_low": tech.get("support_low"),
        "support_high": tech.get("support_high"),
        "breakout": tech.get("breakout"),
        "stop": tech.get("stop"),
        "volume_ratio": tech.get("volume_ratio"),
        "rsi": tech.get("rsi"),
        "teacher_judgement": narrative.get("teacher_judgement", card.get("action", "")),
        "risk": narrative.get("risk", card.get("risk", "")),
    }


def _journal_payload(payload: dict) -> dict:
    strength = payload.get("strong_momentum") or {}
    return {
        "version": payload.get("version"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "trading_status": payload.get("trading_status", {}),
        "market_view": payload.get("market_view", ""),
        "buy_list": [_card_snapshot(c) for c in payload.get("buy_list", [])[:10]],
        "wait_list": [_card_snapshot(c) for c in payload.get("wait_list", [])[:10]],
        "avoid_list": [_card_snapshot(c) for c in payload.get("avoid_list", [])[:10]],
        "portfolio": [
            {
                "stock": row.get("stock"),
                "shares": row.get("shares"),
                "cost": row.get("cost"),
                "pnl": row.get("pnl"),
                "pnl_pct": row.get("pnl_pct"),
                "card": _card_snapshot(row.get("card", {})),
            }
            for row in (payload.get("portfolio_coach") or {}).get("rows", [])
        ],
        "strong_list": strength.get("strong_list", [])[:20],
        "chaseable_list": strength.get("chaseable_list", [])[:20],
        "no_chase_list": strength.get("no_chase_list", [])[:20],
        "tomorrow_watch": strength.get("tomorrow_watch", [])[:20],
    }


def save_decision_journal(payload: dict) -> Path | None:
    """Persist a compact daily decision journal.

    The journal is runtime data. It is ignored by git and used only to make the
    next execution able to review prior recommendations. Failure to save should
    never break report generation.
    """
    try:
        status = payload.get("trading_status", {})
        day = status.get("date") or datetime.now().date().isoformat()
        session = str(status.get("session") or "session").replace("/", "-")
        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        path = JOURNAL_DIR / f"{day}-{session}.json"
        path.write_text(json.dumps(_journal_payload(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


def _load_previous_journal(current_date: str) -> dict | None:
    if not JOURNAL_DIR.exists():
        return None
    candidates = []
    for path in JOURNAL_DIR.glob("*.json"):
        if path.name.startswith(current_date):
            continue
        candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates[:5]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def _session_mode(status: dict) -> dict:
    session = status.get("session", "")
    if session in {"盤前", "盤前集合競價"}:
        return {
            "mode": "盤前計畫",
            "headline": "今天先確認可買名單、不能追的強勢股，以及持股是否需要調整。",
            "primary_question": "今天開盤後要先看哪些標的與價位？",
        }
    if session == "盤中":
        return {
            "mode": "盤中觀察",
            "headline": "盤中重點不是追所有上漲股，而是確認哪些強勢仍有合理進場空間。",
            "primary_question": "目前強勢股哪些可以追，哪些只適合觀察？",
        }
    if session in {"收盤後整理", "盤後"}:
        return {
            "mode": "盤後檢討與明日準備",
            "headline": "市場已收盤，重點轉為檢討今日推薦、整理明日接力與調整持股策略。",
            "primary_question": "今天哪些判斷需要修正，明天要準備哪些劇本？",
        }
    return {
        "mode": "非交易日準備",
        "headline": "非交易日不做盤中判斷，重點是整理下個交易日觀察名單與持股策略。",
        "primary_question": "下個交易日要先觀察哪些族群與價位？",
    }


def _format_price(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "--"


def _build_pre_market_plan(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for card in payload.get("buy_list", [])[:5]:
        tech = card.get("tech") or {}
        narrative = card.get("teacher_narrative") or {}
        rows.append({
            "label": card.get("label"),
            "type": card.get("setup"),
            "price": tech.get("close"),
            "action": narrative.get("no_position_strategy") or card.get("action"),
            "hold_action": narrative.get("holding_strategy"),
            "watch_price": f"拉回 {_format_price(tech.get('support_low'))}～{_format_price(tech.get('support_high'))}｜突破 {_format_price(tech.get('breakout'))}｜失效 {_format_price(tech.get('stop'))}",
            "teacher_view": narrative.get("teacher_judgement", ""),
        })
    return rows


def _build_strength_loop(payload: dict) -> dict:
    strength = payload.get("strong_momentum") or {}
    buy_symbols = {c.get("symbol") for c in payload.get("buy_list", [])}
    strong_rows = strength.get("strong_list", [])[:12]
    chaseable = strength.get("chaseable_list", [])[:8]
    no_chase = strength.get("no_chase_list", [])[:8]
    tomorrow = strength.get("tomorrow_watch", [])[:8]
    missed = []
    for row in strong_rows:
        if row.get("symbol") in buy_symbols:
            continue
        missed.append({
            "label": row.get("label"),
            "change_pct": row.get("change_pct"),
            "volume_ratio": row.get("volume_ratio"),
            "reason": row.get("teacher_view") or "強勢但未通過今日可買條件，列入觀察而非直接追價。",
            "next_step": row.get("tomorrow_plan") or "明日觀察是否回測不破、量能是否延續。",
        })
    return {
        "chaseable": chaseable,
        "no_chase": no_chase,
        "tomorrow_watch": tomorrow,
        "missed_strength": missed[:8],
    }


def _build_recommendation_review(payload: dict, previous: dict | None) -> dict:
    current_cards = {c.get("symbol"): c for c in payload.get("all_cards", [])}
    if not previous:
        return {
            "has_previous": False,
            "summary": "尚無前次決策紀錄；本次將建立基準，下一次執行後即可檢討推薦表現。",
            "rows": [],
        }
    rows = []
    for prev in previous.get("buy_list", [])[:8]:
        symbol = prev.get("symbol")
        current = current_cards.get(symbol)
        if not current:
            rows.append({
                "label": prev.get("label"),
                "previous_close": prev.get("close"),
                "current_close": None,
                "change_since": None,
                "review": "目前股票池未取得最新卡片，暫不做績效判斷。",
            })
            continue
        prev_close = _safe_float(prev.get("close"))
        cur_close = _safe_float((current.get("tech") or {}).get("close"))
        change_since = ((cur_close / prev_close - 1) * 100) if prev_close else 0.0
        if change_since >= 2:
            review = "推薦後表現轉強；若仍未跌破失效價，持股以續抱為主，空手不追高。"
        elif change_since <= -2:
            review = "推薦後表現不如預期；檢查是否跌破失效價，若量價轉弱要降級觀察。"
        else:
            review = "推薦後表現接近持平；等待突破或回測確認，不急著放大部位。"
        rows.append({
            "label": prev.get("label"),
            "previous_close": round(prev_close, 2),
            "current_close": round(cur_close, 2),
            "change_since": round(change_since, 2),
            "review": review,
        })
    summary = "已讀取前次決策紀錄，老師會檢查推薦後表現，而不是只產生新的名單。"
    return {"has_previous": True, "summary": summary, "rows": rows}


def _build_portfolio_strategy_updates(payload: dict) -> list[dict]:
    rows = []
    for row in (payload.get("portfolio_coach") or {}).get("rows", []):
        card = row.get("card") or {}
        narrative = card.get("teacher_narrative") or {}
        tech = card.get("tech") or {}
        score = _safe_float(card.get("score"))
        change = _safe_float(tech.get("change_pct"))
        if score >= 78 and change >= 0:
            status = "策略維持偏多"
        elif score >= 65:
            status = "策略維持觀察"
        else:
            status = "策略降級檢討"
        rows.append({
            "stock": row.get("stock"),
            "status": status,
            "today_price": tech.get("close"),
            "pnl_pct": row.get("pnl_pct"),
            "action": narrative.get("holding_strategy") or row.get("advice"),
            "risk_line": f"失效價 {_format_price(tech.get('stop'))}",
        })
    return rows


def _build_tomorrow_preparation(payload: dict) -> dict:
    strength = payload.get("strong_momentum") or {}
    wait_list = payload.get("wait_list", [])[:5]
    rows = []
    for row in strength.get("tomorrow_watch", [])[:6]:
        rows.append({
            "label": row.get("label"),
            "source": "今日強勢接力",
            "plan": row.get("tomorrow_plan") or "明日觀察是否延續量能、是否回測不破。",
        })
    for card in wait_list:
        tech = card.get("tech") or {}
        narrative = card.get("teacher_narrative") or {}
        rows.append({
            "label": card.get("label"),
            "source": "等待突破/拉回",
            "plan": narrative.get("no_position_strategy") or f"觀察突破 {_format_price(tech.get('breakout'))} 或回測 {_format_price(tech.get('support_low'))}～{_format_price(tech.get('support_high'))}。",
        })
    return {
        "summary": "明日準備不是追今天最強，而是把今日強勢、等待突破與持股風險轉成可執行條件。",
        "rows": rows[:10],
    }


def build_decision_loop(payload: dict) -> dict:
    status = payload.get("trading_status") or {}
    session = _session_mode(status)
    previous = _load_previous_journal(status.get("date", ""))
    review = _build_recommendation_review(payload, previous)
    return {
        "session_mode": session,
        "pre_market_plan": _build_pre_market_plan(payload),
        "recommendation_review": review,
        "strength_loop": _build_strength_loop(payload),
        "portfolio_strategy_updates": _build_portfolio_strategy_updates(payload),
        "tomorrow_preparation": _build_tomorrow_preparation(payload),
        "journal": {
            "has_previous": bool(previous),
            "previous_date": (previous or {}).get("trading_status", {}).get("date", ""),
            "current_date": status.get("date", ""),
        },
    }
