"""Markdown report generator."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


def _decision_icon(decision: str) -> str:
    return {
        "波段買進": "🟢",
        "波段觀察": "🟡",
        "等待": "⚪",
        "減碼/避開": "🔴",
    }.get(decision, "⚪")


def build_markdown_report(payload: dict[str, Any]) -> str:
    today = date.today().isoformat()
    cards = payload["decision_cards"]
    macd_candidates = payload["macd_candidates"]
    news = payload["news"]
    brief = payload["pm_brief"]
    quality = brief["data_quality"]

    report = f"""# AI Stock Radar 每日投資經理人報告

日期：{today}  
版本：v{payload["version"]} Investment Manager Release  
新聞來源：{payload["news_source"]}

## 一、投資經理人早會結論

**{brief["headline"]}**

### 今日主策略

{brief["strategy"]}

### 資金配置建議

{brief["capital_allocation"]}

### 今日優先動作

"""
    for item in brief["top_actions"]:
        report += f"- {item}\n"

    report += """
### 今日避免動作

"""
    for item in brief["avoid_actions"]:
        report += f"- {item}\n"

    report += f"""
## 二、今日總結

**市場判斷：{payload["market_view"]}**  
**AI 信心指數：{payload["ai_confidence"]}%**

{payload["market_summary"]}

## 三、波段操作 Top 5

| 排名 | 個股 | Radar | 決策 | 信心 | 信念 | 部位建議 |
|---:|---|---:|---|---:|---|---|
"""
    for idx, card in enumerate(cards[:5], 1):
        icon = _decision_icon(card["decision"])
        report += f"| {idx} | {card['display_name']} | {card['radar_score']} | {icon} {card['decision']} | {card['confidence']}% | {card['conviction']} | {card['position_guidance']} |\n"

    report += """
## 四、AI 選出 MACD 即將翻正十檔

| 排名 | 個股 | 分數 | MACD 前值 | MACD 目前 | RSI | 理由 |
|---:|---|---:|---:|---:|---:|---|
"""
    for idx, item in enumerate(macd_candidates, 1):
        report += f"| {idx} | {item['symbol']} {item['name']} | {item['score']} | {item['hist_prev']} | {item['hist_current']} | {item['rsi']} | {item['reason']} |\n"

    report += """
## 五、個股 Decision Cards

"""
    for card in cards[:10]:
        icon = _decision_icon(card["decision"])
        breakdown = card["score_breakdown"]
        report += f"""### {icon} {card['display_name']}｜{card['decision']}｜{card['conviction']}

- Radar Score：{card['radar_score']}
- 信心：{card['confidence']}%
- 波段評價：{card['swing_view']}
- 部位建議：{card['position_guidance']}
- 進場條件：{card['entry_condition']}
- 續抱條件：{card['hold_condition']}
- 減碼條件：{card['reduce_condition']}
- 失效條件：{card['invalidation_condition']}
- 風險提醒：{card['risk_note']}

分數拆解：

| 項目 | 分數 |
|---|---:|
| 基礎分 | {breakdown['base']} |
| 新聞/主線 | {breakdown['news_signal']} |
| 技術面 | {breakdown['technical']} |
| 波段偏好 | {breakdown['profile_bonus']} |
| 風險扣分 | -{breakdown['risk_penalty']} |
| 最終 Radar | {breakdown['final_score']} |

Evidence：
"""
        for evidence in card["evidence"][:6]:
            direction = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
            report += f"- {direction} {evidence['label']}：{evidence['explanation']}\n"
        report += "\n"

    report += """
## 六、今日重要新聞與影響

"""
    for item in news[:8]:
        icon = "✅" if item["impact"] == "positive" else "⚠️" if item["impact"] == "negative" else "➖"
        affected = "、".join(item["affected_stocks"]) if item["affected_stocks"] else "暫無明確個股"
        report += f"""### {icon} {item['title_zh']}

- 來源：{item['source']}
- Signal：{item['signal']}
- 摘要：{item['summary_zh']}
- 受影響個股：{affected}

"""

    report += f"""
## 七、資料品質與限制

- 新聞來源：{quality['news_source']}
- 新聞數量：{quality['news_items']}
- 正向訊號：{quality['positive_signals']}
- 負向訊號：{quality['negative_signals']}
- 信心指數：{quality['confidence']}%
- 限制：{quality['limitation']}

## 八、風險控管

"""
    for item in brief["risk_controls"]:
        report += f"- {item}\n"

    return report


def save_markdown_report(content: str) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "daily_report.md"
    path.write_text(content, encoding="utf-8")
    return path
