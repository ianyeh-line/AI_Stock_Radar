"""Markdown report generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _evidence_lines(card: dict[str, Any]) -> str:
    lines: list[str] = []
    for evidence in card.get("evidence", [])[:8]:
        icon = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
        lines.append(f"- {icon} **{evidence['label']}**：{evidence['explanation']}")
    return "\n".join(lines) if lines else "- 目前證據不足。"


def build_markdown_report(payload: dict[str, Any]) -> str:
    pm = payload["pm_brief"]
    teacher = payload.get("teacher_buy_list", {})
    cards = payload["decision_cards"]
    macd = payload["macd_candidates"]
    news = payload["news_items"]
    portfolio = payload.get("portfolio_analysis", [])
    portfolio_coach = payload.get("portfolio_coach", {})
    quality = pm["data_quality"]
    data_trust = payload.get("data_trust", {})
    backtest_summary = payload.get("backtest_summary", {})
    recommended_rows = []
    for item in pm.get("recommended_stocks", []):
        recommended_rows.append(
            f"- **{item['display_name']}**｜{item['decision']}｜Radar {item['radar_score']}｜突破 {item['breakout_price']:.2f} 或拉回 {item['pullback_low']:.2f}～{item['pullback_high']:.2f} 再處理。"
        )
    recommended_block = "\n".join(recommended_rows) if recommended_rows else "目前沒有高信念推薦個股，以觀察與資金控管為主。"

    def _teacher_lines(items: list[dict[str, Any]], limit: int = 8) -> str:
        if not items:
            return "目前沒有符合條件的標的。"
        rows: list[str] = []
        for item in items[:limit]:
            reasons = "；".join(item.get("reasons", [])[:2])
            rows.append(
                f"- **{item['display_name']}**｜等級 {item['grade']}｜{item['action_type']}｜Radar {item['radar_score']}｜"
                f"買進區間 {item['suggested_entry_zone']}｜突破 {item['breakout_trigger']:.2f}｜"
                f"失效 {item['invalidation_price']:.2f}｜第一停利 {item['first_profit_take']:.2f}｜第二停利 {item['second_profit_take']:.2f}｜Guardrail {item.get('guardrail_status', '未檢查')}｜回測勝率 {item.get('backtest_win_rate', 'N/A')}%｜{reasons}"
            )
        return "\n".join(rows)

    ready_block = _teacher_lines(teacher.get("ready_to_buy", []), 6)
    seen: set[str] = set()
    b_items: list[dict[str, Any]] = []
    for item in teacher.get("wait_breakout", []) + teacher.get("pullback_watch", []):
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        b_items.append(item)
    candidate_block = _teacher_lines(b_items, 8)
    observe_lines = []
    for item in teacher.get("observe_only", [])[:5]:
        observe_lines.append(f"- C｜{item['display_name']}｜Radar {item['radar_score']}｜{item['recommendation']}")
    for item in teacher.get("avoid_or_reduce", [])[:5]:
        observe_lines.append(f"- D｜{item['display_name']}｜Radar {item['radar_score']}｜{item['recommendation']}")
    observe_block = "\n".join(observe_lines) if observe_lines else "目前沒有 C/D 名單。"

    report = f"""# AI Stock Radar Daily Report

Version: v{payload['version']}  
Generated At: {payload['generated_at']}


## 今日可買進名單（股市老師盤前版）

**結論：** {teacher.get('headline', '今日尚無可買進名單。')}  
{teacher.get('summary', '')}

### A｜今日可買進 / 可行動

{ready_block}

### B｜等待突破或拉回確認

{candidate_block}

### C / D｜只觀察與避免

{observe_block}

## 投資經理人早會

**市場判斷：** {payload['market_view']}  
**AI 信心指數：** {payload['ai_confidence']}%  
**新聞來源：** {payload['news_source']}

### 今日主策略

{pm['headline']}

{pm['strategy']}

### 主策略推薦個股

{recommended_block}

### 資金配置建議

{pm['capital_allocation']}

### 今日優先動作
"""
    for item in pm["top_actions"]:
        report += f"- {item}\n"
    report += "\n### 今日避免動作\n"
    for item in pm["avoid_actions"]:
        report += f"- {item}\n"
    report += "\n### 風險控管\n"
    for item in pm["risk_controls"]:
        report += f"- {item}\n"

    report += f"""
## Phase 5 資料可信度與推薦防呆

- 參考價格日期：{data_trust.get('reference_price_date', 'N/A')}
- 價格資料正常：{data_trust.get('price_normal_count', 0)} 檔
- 價格日期落後：{data_trust.get('price_stale_count', 0)} 檔
- Fallback 價格：{data_trust.get('price_fallback_count', 0)} 檔
- 通過 A 級 Guardrail：{data_trust.get('guardrail_passed_count', 0)} 檔
- 降級觀察：{data_trust.get('guardrail_downgraded_count', 0)} 檔
- 禁止買進：{data_trust.get('guardrail_blocked_count', 0)} 檔

政策：{data_trust.get('policy', '')}

## Phase 4 輕量歷史驗證

- 方法：{backtest_summary.get('method', 'N/A')}
- 驗證股票數：{backtest_summary.get('validated_symbols', 0)} / {backtest_summary.get('total_symbols', 0)}
- 平均勝率：{backtest_summary.get('avg_win_rate', 'N/A')}%
- 平均 20 日報酬：{backtest_summary.get('avg_return', 'N/A')}%
- 平均最大回撤：{backtest_summary.get('avg_max_drawdown', 'N/A')}%
- 限制：{backtest_summary.get('limitations', '')}

"""

    report += "\n## Top Decision Cards\n\n"
    for idx, card in enumerate(cards[:10], 1):
        breakdown = card["score_breakdown"]
        report += f"""### {idx}. {card['display_name']}｜{card['decision']}｜{card['conviction']}

- Radar Score: **{card['radar_score']}**
- Confidence: **{card['confidence']}%**
- Latest Close: **{card['latest_close']}** ({card['change_pct']}%)
- Price Source: {card['price_source']}
- Position: {card['position_guidance']}
- 突破追蹤價：**{card.get('breakout_price')}**
- 拉回區間：**{card.get('pullback_low')}～{card.get('pullback_high')}**
- 減碼價：**{card.get('reduce_price')}**
- 停損/失效價：**{card.get('stop_loss_price')}**

#### 分數拆解

| 項目 | 分數 |
|---|---:|
| 基礎分 | {breakdown['base']} |
| 新聞/主線 | {breakdown['news_signal']} |
| 技術面 | {breakdown['technical']} |
| 法人籌碼 | {breakdown.get('institutional_flow', 0)} |
| 波段偏好 | {breakdown['profile_bonus']} |
| 價格資料品質 | {breakdown['price_quality']} |
| 風險扣分 | -{breakdown['risk_penalty']} |
| 最終 Radar | {breakdown['final_score']} |

#### 投資經理人觀點

{card['swing_view']}

- 進場條件：{card['entry_condition']}
- 續抱條件：{card['hold_condition']}
- 減碼條件：{card['reduce_condition']}
- 失效條件：{card['invalidation_condition']}
- 風險提醒：{card['risk_note']}
- 量能比說明：{card.get('volume_ratio_note', '')}
- 法人籌碼：{card.get('institutional_summary', '')}
- Data Trust：{payload.get('data_trust', {}).get('guardrails_by_symbol', {}).get(card['symbol'], {}).get('status', '未檢查')}
- 歷史驗證：樣本 {payload.get('backtest_summary', {}).get('per_symbol', {}).get(card['symbol'], {}).get('sample_count', 0)}，勝率 {payload.get('backtest_summary', {}).get('per_symbol', {}).get(card['symbol'], {}).get('win_rate', 'N/A')}%，平均報酬 {payload.get('backtest_summary', {}).get('per_symbol', {}).get(card['symbol'], {}).get('avg_return', 'N/A')}%

#### Evidence Chain

{_evidence_lines(card)}

"""

    report += """
## 法人籌碼 Radar

| Stock | 法人觀點 | 籌碼分 | 外資 | 投信 | 自營商 | 合計 | 來源 | 資料日 |
|---|---|---:|---:|---:|---:|---:|---|---|
"""
    for symbol, flow in payload.get("institutional_flows", {}).items():
        report += f"| {symbol} {flow.get('name', '')} | {flow.get('flow_bias')} | {flow.get('flow_score')} | {flow.get('foreign_net')} | {flow.get('investment_trust_net')} | {flow.get('dealer_net')} | {flow.get('total_net')} | {flow.get('source')} | {flow.get('latest_date')} |\n"

    report += "## MACD 觀察名單\n\n"
    report += "| Rank | Stock | 狀態 | Score | MACD 前值 | MACD 現值 | RSI | Trend | Reason |\n|---:|---|---|---:|---:|---:|---:|---:|---|\n"
    for idx, item in enumerate(macd, 1):
        report += f"| {idx} | {item['display_name']} | {item.get('macd_status', '')} | {item['score']} | {item['hist_prev']} | {item['hist_current']} | {item['rsi']} | {item['trend']} | {item['reason']} |\n"

    report += "\n## 個人持股總教練\n\n"
    if portfolio_coach:
        report += f"**總評：** {portfolio_coach.get('headline', '')}\n\n"
        report += f"**組合風格：** {portfolio_coach.get('portfolio_style', '')}\n\n"
        report += f"**資金政策：** {portfolio_coach.get('capital_policy', '')}\n\n"
        report += f"**總市值：** {portfolio_coach.get('total_market_value', 0)}｜**總損益：** {portfolio_coach.get('total_pnl', 0)}｜**總損益%：** {portfolio_coach.get('total_pnl_pct', 0)}%｜**風險：** {portfolio_coach.get('risk_level', 'N/A')}\n\n"
        report += "### 老師建議動作\n"
        for action in portfolio_coach.get('teacher_actions', []):
            report += f"- {action}\n"
        report += "\n### 組合調整計畫\n"
        for action in portfolio_coach.get('rebalance_plan', []):
            report += f"- {action}\n"
        report += "\n### 組合風險提醒\n"
        for risk in portfolio_coach.get('risk_alerts', []):
            report += f"- {risk}\n"
    report += "\n## 個人持股分析\n\n"
    if not portfolio:
        report += "目前尚未輸入個人持股。\n"
    else:
        report += "| Stock | 股數 | 成本 | 最新價 | 損益% | Decision | AI 建議 |\n|---|---:|---:|---:|---:|---|---|\n"
        for row in portfolio:
            report += f"| {row['display_name']} | {row['shares']} | {row['avg_cost']} | {row['latest_close']} | {row['pnl_pct']}% | {row['decision']} | {row['action']} |\n"

    report += "\n## 新聞影響鏈\n\n"
    for item in news:
        icon = "✅" if item["impact"] == "positive" else "⚠️" if item["impact"] == "negative" else "➖"
        stocks = "、".join(item.get("affected_stocks", [])) or "無明確對應"
        source_url = item.get("source_url") or ""
        title = f"[{item['title_zh']}]({source_url})" if source_url else item["title_zh"]
        report += f"### {icon} {title}\n\n- 來源：{item['source']}\n- Signal：{item['signal']}\n- 投資摘要：{item['summary_zh']}\n- 影響個股：{stocks}\n\n"

    report += f"""## Data Quality Check

- News Source: {quality['news_source']}
- News Items: {quality['news_items']}
- Positive Signals: {quality['positive_signals']}
- Negative Signals: {quality['negative_signals']}
- Real Price Count: {quality['price_live_count']}
- Fallback Price Count: {quality['price_fallback_count']}
- Institutional Official Count: {quality.get('institutional_official_count', 0)}
- Institutional Fallback Count: {quality.get('institutional_fallback_count', 0)}
- Institutional Frequency: {quality.get('institutional_frequency', '')}
- Price Frequency: {quality.get('price_frequency')}
- News Frequency: {quality.get('news_frequency')}
- Decision Scope: {quality.get('decision_scope')}
- User Watchlist Count: {quality.get('user_watchlist_count', 0)}
- Portfolio Count: {quality.get('portfolio_count', 0)}
- Limitation: {quality['limitation']}
"""
    return report


def save_markdown_report(content: str, path: str | Path = "output/daily_report.md") -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
