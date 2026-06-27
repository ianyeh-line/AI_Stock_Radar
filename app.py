"""AI Stock Radar Streamlit Dashboard."""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from radar.engine.decision import run_decision_pipeline, save_dashboard_payload
from radar.engine.user_space import (
    add_or_update_holding,
    add_user_watchlist_item,
    load_portfolio,
    load_user_watchlist,
    remove_holding,
    remove_user_watchlist_item,
)
from radar.knowledge.stock_map import resolve_stock_query
from radar.report.markdown import build_markdown_report, save_markdown_report

SECTIONS = [
    "盤前決策總覽",
    "今日可買進名單",
    "法人籌碼 Radar",
    "MACD 觀察名單",
    "指定觀察個股",
    "個人持股分析",
    "個股技術線圖",
    "新聞影響鏈",
]

st.set_page_config(page_title="AI Stock Radar", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; }
    div[role="radiogroup"] { gap: 0.35rem; }
    .price-red { color: #d32f2f; font-weight: 600; font-size: 0.95rem; line-height: 1.2; }
    .price-green { color: #168a35; font-weight: 600; font-size: 0.95rem; line-height: 1.2; }
    .price-gray { color: #555555; font-weight: 600; font-size: 0.95rem; line-height: 1.2; }
    .small-muted { color: #777777; font-size: 0.88rem; }
    .news-link a { text-decoration: none; font-weight: 700; }
    .section-title {font-size: 0.88rem; color: #777; margin-bottom: -0.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


PAYLOAD_PATH = Path("output/dashboard_data.json")
REPORT_PATH = Path("output/daily_report.md")


def run_pipeline() -> dict[str, Any]:
    payload = run_decision_pipeline()
    save_dashboard_payload(payload)
    save_markdown_report(build_markdown_report(payload))
    return payload


def _read_payload_file() -> dict[str, Any]:
    return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))


@st.cache_data(ttl=300)
def load_payload_from_file(file_mtime: float) -> dict[str, Any]:
    # Fast dashboard mode: page load reads the latest generated payload instead
    # of refetching 100 price series + institutional flow on every Streamlit start.
    return _read_payload_file()


def load_payload() -> dict[str, Any]:
    if PAYLOAD_PATH.exists():
        return load_payload_from_file(PAYLOAD_PATH.stat().st_mtime)
    with st.spinner("第一次啟動尚未找到 dashboard_data.json，正在產生今日 Radar..."):
        return run_pipeline()


def refresh_product() -> None:
    with st.spinner("正在重新抓取最新價格、新聞與法人資料，請稍候..."):
        run_pipeline()
    st.cache_data.clear()
    st.rerun()


def set_active_section(section: str) -> None:
    # Defer section switch until next rerun. Streamlit does not allow mutating
    # a widget-backed session_state key after the widget has been rendered.
    st.session_state["pending_section"] = section


def decision_icon(decision: str) -> str:
    return {
        "波段買進": "🟢",
        "波段觀察": "🟡",
        "等待": "⚪",
        "減碼/避開": "🔴",
    }.get(decision, "⚪")


def tw_price_class(change_pct: float) -> str:
    if change_pct > 0:
        return "price-red"
    if change_pct < 0:
        return "price-green"
    return "price-gray"


def price_html(price: float, change_pct: float, prefix: str = "最新可得價") -> str:
    css = tw_price_class(change_pct)
    sign = "+" if change_pct > 0 else ""
    return f'<div class="small-muted">{prefix}</div><div class="{css}">{price:.2f}（{sign}{change_pct:.2f}%）</div>'


def volume_ratio_help(ratio: float) -> str:
    if ratio >= 1.25:
        tone = "明顯放大，突破確認度較高，但需避免爆量長黑。"
    elif ratio >= 1.05:
        tone = "溫和放大，屬於健康量能。"
    elif ratio >= 0.85:
        tone = "接近常態，訊號有效但攻擊力普通。"
    else:
        tone = "低於常態，突破可信度不足。"
    return f"量能比 = 今日成交量 / 20日均量。{ratio:.2f} 代表今日成交量約為 20日均量的 {ratio:.0%}，{tone}"


def compact_volume(value: float) -> str:
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f}億"
    if value >= 10_000:
        return f"{value / 10_000:.0f}萬"
    return f"{value:.0f}"


def chart_period_options() -> dict[str, int]:
    return {
        "1個月": 22,
        "3個月": 66,
        "6個月": 132,
        "1年": 260,
    }


def select_stock(symbol: str, jump_to_chart: bool = True) -> None:
    st.session_state["quick_chart_symbol"] = symbol
    if jump_to_chart:
        set_active_section("個股技術線圖")


def stock_button(symbol: str, label: str, key: str, jump_to_chart: bool = True) -> None:
    if st.button(label, key=key):
        select_stock(symbol, jump_to_chart=jump_to_chart)
        st.rerun()


def stock_options(payload: dict[str, Any]) -> dict[str, str]:
    rows = sorted(payload.get("stock_index", {}).values(), key=lambda item: item["symbol"])
    return {f"{item['symbol']} {item['name']}": item["symbol"] for item in rows}


def resolve_user_stock(query: str, selected_label: str | None, payload: dict[str, Any]) -> Optional[Any]:
    text = (query or "").strip()
    if text:
        return resolve_stock_query(text)
    if selected_label and selected_label != "（不使用）":
        symbol = stock_options(payload).get(selected_label)
        if symbol:
            return resolve_stock_query(symbol)
    return None


def render_score_breakdown(card: dict[str, Any]) -> None:
    breakdown = card["score_breakdown"]
    rows = [
        {"項目": "基礎分", "分數": breakdown["base"]},
        {"項目": "新聞/主線", "分數": breakdown["news_signal"]},
        {"項目": "技術面", "分數": breakdown["technical"]},
        {"項目": "法人籌碼", "分數": breakdown.get("institutional_flow", 0)},
        {"項目": "波段偏好", "分數": breakdown["profile_bonus"]},
        {"項目": "價格資料品質", "分數": breakdown["price_quality"]},
        {"項目": "風險扣分", "分數": -breakdown["risk_penalty"]},
        {"項目": "最終 Radar", "分數": breakdown["final_score"]},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_decision_card_compact(card: dict[str, Any], key_prefix: str) -> None:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        with left:
            st.subheader(f"{decision_icon(card['decision'])} {card['display_name']}｜{card['decision']}｜{card['conviction']}")
            st.write(card["swing_view"])
            st.write(f"**進場條件：** {card['entry_condition']}")
            st.write(f"**減碼條件：** {card['reduce_condition']}")
            st.caption(card.get("volume_ratio_note", ""))
            st.caption("法人籌碼：" + card.get("institutional_summary", "尚無法人資料"))
        with right:
            st.metric("Radar", card["radar_score"])
            st.metric("Confidence", f"{card['confidence']}%")
            st.markdown(price_html(float(card["latest_close"]), float(card["change_pct"]), prefix="最新可得價"), unsafe_allow_html=True)
            stock_button(card["symbol"], "📈 查看線圖", f"{key_prefix}-{card['symbol']}")
        with st.expander("分數拆解與 Evidence Chain"):
            render_score_breakdown(card)
            for evidence in card["evidence"]:
                icon = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
                st.write(f"{icon} **{evidence['label']}**：{evidence['explanation']}")


def render_stock_chart(payload: dict[str, Any], symbol: str, chart_context: str = "main") -> None:
    profile = payload["technical_profiles"].get(symbol)
    if not profile:
        st.warning("找不到此股票技術資料。若剛新增個股，請按『重新產生今日 Radar』。")
        return
    name = payload["stock_index"].get(symbol, {}).get("name", "")
    df = pd.DataFrame(profile["history"])
    if df.empty:
        st.warning("沒有足夠價格資料可顯示。")
        return
    df["date"] = pd.to_datetime(df["date"])

    st.subheader(f"{symbol} {name} 技術線圖")

    period_map = chart_period_options()
    period = st.radio(
        "觀察區間",
        list(period_map.keys()),
        index=1,
        horizontal=True,
        key=f"chart-period-{chart_context}-{symbol}",
    )
    chart_df = df.tail(period_map[period]).copy()
    latest_row = chart_df.iloc[-1]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(price_html(float(profile["latest_close"]), float(profile["change_pct"])), unsafe_allow_html=True)
    c2.metric("開", f"{float(latest_row['open']):.2f}")
    c3.metric("高", f"{float(latest_row['high']):.2f}")
    c4.metric("低", f"{float(latest_row['low']):.2f}")
    c5.metric("量", compact_volume(float(latest_row["volume"])))
    c6.metric("資料日期", profile.get("latest_date", "N/A"))

    ma_cols = st.columns(6)
    ma_cols[0].metric("MA5", f"{profile.get('ma5', 0):.2f}")
    ma_cols[1].metric("MA10", f"{profile.get('ma10', 0):.2f}")
    ma_cols[2].metric("MA20", f"{profile.get('ma20', 0):.2f}")
    ma_cols[3].metric("MACD Hist", f"{profile['macd_hist']:.4f}")
    ma_cols[4].metric("RSI", f"{profile['rsi']:.1f}")
    ma_cols[5].metric("量能比", f"{profile['volume_ratio']:.2f}")
    st.caption(f"價格來源：{profile['price_source']}｜{profile['technical_summary']}｜預設顯示 3 個月，可切換觀察區間。")
    st.caption(volume_ratio_help(float(profile['volume_ratio'])))

    volume_colors = ["#d32f2f" if row.close >= row.open else "#168a35" for row in chart_df.itertuples()]

    price_volume_fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.70, 0.30],
    )
    price_volume_fig.add_trace(
        go.Candlestick(
            x=chart_df["date"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="K線",
            increasing_line_color="#d32f2f",
            increasing_fillcolor="#d32f2f",
            decreasing_line_color="#168a35",
            decreasing_fillcolor="#168a35",
        ),
        row=1,
        col=1,
    )
    for col, label in [("ma5", "MA5"), ("ma10", "MA10"), ("ma20", "MA20")]:
        if col in chart_df:
            price_volume_fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df[col], name=label, mode="lines"), row=1, col=1)

    price_volume_fig.add_trace(go.Bar(x=chart_df["date"], y=chart_df["volume"], name="成交量", marker_color=volume_colors), row=2, col=1)
    for col, label in [("volume_ma5", "MV5"), ("volume_ma20", "MV20")]:
        if col in chart_df:
            price_volume_fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df[col], name=label, mode="lines"), row=2, col=1)

    price_volume_fig.update_layout(
        height=620,
        xaxis_rangeslider_visible=False,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    price_volume_fig.update_yaxes(title_text="價格", row=1, col=1)
    price_volume_fig.update_yaxes(title_text="成交量", row=2, col=1)
    st.plotly_chart(price_volume_fig, use_container_width=True, key=f"price-volume-{chart_context}-{symbol}-{period}")

    indicator_tabs = st.tabs(["MACD", "RSI"])
    with indicator_tabs[0]:
        macd_fig = go.Figure()
        macd_fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["dif"], name="DIF"))
        macd_fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["dea"], name="DEA"))
        hist_colors = ["#d32f2f" if (value or 0) >= 0 else "#168a35" for value in chart_df["macd_hist"]]
        macd_fig.add_trace(go.Bar(x=chart_df["date"], y=chart_df["macd_hist"], name="MACD Histogram", marker_color=hist_colors))
        macd_fig.update_layout(height=260, margin={"l": 10, "r": 10, "t": 30, "b": 10})
        st.plotly_chart(macd_fig, use_container_width=True, key=f"macd-{chart_context}-{symbol}-{period}")
    with indicator_tabs[1]:
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=chart_df["date"], y=chart_df["rsi"], name="RSI"))
        rsi_fig.add_hline(y=70, line_dash="dash", annotation_text="過熱")
        rsi_fig.add_hline(y=30, line_dash="dash", annotation_text="偏弱")
        rsi_fig.update_layout(height=220, margin={"l": 10, "r": 10, "t": 30, "b": 10})
        st.plotly_chart(rsi_fig, use_container_width=True, key=f"rsi-{chart_context}-{symbol}-{period}")

def find_card(payload: dict[str, Any], symbol: str) -> Optional[dict[str, Any]]:
    for card in payload.get("decision_cards", []):
        if card["symbol"] == symbol:
            return card
    return None


def teacher_item_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    teacher = payload.get("teacher_buy_list", {})
    items: list[dict[str, Any]] = []
    for key in ["ready_to_buy", "wait_breakout", "pullback_watch", "observe_only", "avoid_or_reduce"]:
        items.extend(teacher.get(key, []))
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        result.setdefault(str(item.get("symbol")), item)
    return result


def render_compact_decision_card(card: dict[str, Any], key_prefix: str) -> None:
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.subheader(f"{decision_icon(card['decision'])} {card['display_name']}｜{card['decision']}｜Radar {card['radar_score']}")
            st.write(card.get("swing_view", ""))
            st.write(f"**進場：** {card.get('entry_condition', '')}")
            st.write(f"**減碼：** {card.get('reduce_condition', '')}")
            st.caption(card.get("volume_ratio_note", ""))
        with right:
            st.metric("Confidence", f"{card['confidence']}%")
            st.markdown(price_html(float(card["latest_close"]), float(card["change_pct"])), unsafe_allow_html=True)
            stock_button(card["symbol"], "📈 查看線圖", f"compact-{key_prefix}-{card['symbol']}")


def render_decision_overview(payload: dict[str, Any]) -> None:
    cards = payload["decision_cards"]
    pm = payload["pm_brief"]
    quality = pm["data_quality"]
    teacher = payload.get("teacher_buy_list", {})

    st.header("盤前決策總覽")
    st.caption("整合原本的投資經理人早會、今日決策卡與每日報告；先給結論，再給買點與證據。")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("今日市場判斷", payload["market_view"])
    m2.metric("AI 信心指數", f"{payload['ai_confidence']}%")
    m3.metric("新聞數", quality["news_items"])
    m4.metric("真實日線", quality["price_live_count"])
    m5.metric("價格最新日", quality.get("price_latest_date_max", "N/A"))
    m6.metric("持股檔數", quality.get("portfolio_count", 0))

    st.info(pm["headline"])
    st.subheader("今日主策略與推薦個股")
    st.write(pm["strategy"])
    if pm.get("recommended_stocks"):
        rec_cols = st.columns(min(3, max(1, len(pm["recommended_stocks"]))))
        for idx, item in enumerate(pm["recommended_stocks"][:6]):
            with rec_cols[idx % len(rec_cols)]:
                with st.container(border=True):
                    st.markdown(f"**{item['display_name']}**")
                    st.write(f"{item['decision']}｜Radar {item['radar_score']}｜Confidence {item['confidence']}%")
                    st.caption(item["reason"])
                    stock_button(item["symbol"], "📈 查看線圖", f"overview-rec-{item['symbol']}-{idx}")

    st.subheader("資金配置與今日動作")
    st.write(pm["capital_allocation"])
    c1, c2 = st.columns(2)
    with c1:
        st.write("**今日優先動作**")
        for item in pm["top_actions"]:
            st.success(item)
    with c2:
        st.write("**今日避免動作**")
        for item in pm["avoid_actions"]:
            st.warning(item)

    st.subheader("今日可買進名單摘要")
    st.write(teacher.get("headline", "今日尚無可買進名單。"))
    ready = teacher.get("ready_to_buy", [])
    if ready:
        for item in ready[:3]:
            render_teacher_stock_card(item, "overview-ready")
    else:
        st.info("今日沒有 A 級直接可行動標的，請看 B 級等待突破/拉回名單。")

    st.subheader("Top Decision Cards")
    for idx, card in enumerate(cards[:5], 1):
        with st.expander(f"{idx}. {card['display_name']}｜{card['decision']}｜Radar {card['radar_score']}｜Confidence {card['confidence']}%", expanded=idx <= 2):
            render_compact_decision_card(card, f"overview-{idx}")
            render_score_breakdown(card)
            for evidence in card.get("evidence", [])[:6]:
                icon = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
                st.write(f"{icon} **{evidence['label']}**：{evidence['explanation']}")

    st.subheader("資料品質與限制")
    dq = pd.DataFrame(
        [
            {"項目": "資料產生時間", "值": payload.get("generated_at", "N/A")},
            {"項目": "新聞來源", "值": quality["news_source"]},
            {"項目": "價格資料最新日", "值": f"{quality.get('price_latest_date_min', 'N/A')} ～ {quality.get('price_latest_date_max', 'N/A')}"},
            {"項目": "真實價格日線", "值": quality["price_live_count"]},
            {"項目": "Fallback 價格", "值": quality["price_fallback_count"]},
            {"項目": "價格頻率", "值": quality.get("price_frequency", "日線資料")},
            {"項目": "新聞頻率", "值": quality.get("news_frequency", "RSS 更新")},
            {"項目": "決策維度", "值": quality.get("decision_scope", "日線技術、新聞影響、AI 產業鏈、個人觀察與持股")},
        ]
    )
    st.dataframe(dq, use_container_width=True, hide_index=True)
    st.caption(quality["limitation"])

    with st.expander("每日 Markdown 報告預覽", expanded=False):
        report_path = REPORT_PATH
        if report_path.exists():
            st.markdown(report_path.read_text(encoding="utf-8"))
        else:
            st.warning("尚未產生 daily_report.md。請按重新抓取最新資料。")



def render_teacher_stock_card(item: dict[str, Any], key_prefix: str) -> None:
    grade_icon = {"A": "🟢", "B": "🟡", "C": "⚪", "D": "🔴"}.get(item.get("grade"), "⚪")
    with st.container(border=True):
        left, right = st.columns([3, 1])
        with left:
            st.subheader(f"{grade_icon} {item['display_name']}｜等級 {item['grade']}｜{item['action_type']}")
            st.success(item["recommendation"] if item.get("grade") in {"A", "B"} else item["recommendation"])
            st.write(f"**股市老師觀點：** {item['manager_note']}")
            level_rows = pd.DataFrame(
                [
                    {"項目": "建議買進區間", "數字/條件": item["suggested_entry_zone"]},
                    {"項目": "突破確認價", "數字/條件": f"{item['breakout_trigger']:.2f}"},
                    {"項目": "停損 / 失效價", "數字/條件": f"{item['invalidation_price']:.2f}"},
                    {"項目": "風險減碼價", "數字/條件": f"{item['risk_reduce_price']:.2f}"},
                    {"項目": "第一停利/減碼", "數字/條件": f"{item['first_profit_take']:.2f}"},
                    {"項目": "第二停利/減碼", "數字/條件": f"{item['second_profit_take']:.2f}"},
                ]
            )
            st.dataframe(level_rows, use_container_width=True, hide_index=True)
            st.write(f"**進場條件：** {item['entry_condition']}")
            st.write(f"**不追高原則：** {item['do_not_chase_reason']}")
            with st.expander("為什麼可以列入這個等級"):
                for reason in item.get("reasons", []):
                    st.write(f"- {reason}")
                st.caption(item.get("volume_condition", ""))
        with right:
            st.metric("Radar", item["radar_score"])
            st.metric("Confidence", f"{item['confidence']}%")
            st.markdown(price_html(float(item["latest_close"]), float(item["change_pct"])), unsafe_allow_html=True)
            stock_button(item["symbol"], "📈 查看線圖", f"{key_prefix}-{item['symbol']}-{item['rank']}")


def render_institutional_flow(payload: dict[str, Any]) -> None:
    st.header("法人籌碼 Radar")
    st.caption("資料來源優先使用 TWSE T86 三大法人；若當日尚未公布、個股非上市或抓取失敗，會明確標示 fallback。")
    flows = payload.get("institutional_flows", {})
    cards = {card["symbol"]: card for card in payload.get("decision_cards", [])}
    rows: list[dict[str, Any]] = []
    for symbol, flow in flows.items():
        card = cards.get(symbol, {})
        rows.append(
            {
                "股票": f"{symbol} {flow.get('name', '')}",
                "法人觀點": flow.get("flow_bias"),
                "籌碼分": flow.get("flow_score"),
                "外資淨買賣(股)": flow.get("foreign_net"),
                "投信淨買賣(股)": flow.get("investment_trust_net"),
                "自營商淨買賣(股)": flow.get("dealer_net"),
                "三大法人合計(股)": flow.get("total_net"),
                "Radar": card.get("radar_score"),
                "Decision": card.get("decision"),
                "來源": flow.get("source"),
                "資料日": flow.get("latest_date"),
                "摘要": flow.get("summary"),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("目前沒有法人籌碼資料。")
        return
    st.dataframe(df.sort_values(["籌碼分", "Radar"], ascending=False), use_container_width=True, hide_index=True)

    st.subheader("籌碼偏多 Top 10")
    top = df.sort_values("籌碼分", ascending=False).head(10)
    cols = st.columns(2)
    for idx, row in enumerate(top.to_dict("records")):
        symbol = str(row["股票"]).split()[0]
        with cols[idx % 2]:
            with st.container(border=True):
                st.subheader(f"{row['股票']}｜{row['法人觀點']}｜籌碼分 {row['籌碼分']}")
                st.write(row["摘要"])
                st.write(f"Radar {row.get('Radar')}｜Decision {row.get('Decision')}｜來源 {row.get('來源')}｜資料日 {row.get('資料日')}")
                stock_button(symbol, "📈 查看線圖", f"flow-chart-{symbol}-{idx}")


def render_teacher_buy_list(payload: dict[str, Any]) -> None:
    teacher = payload.get("teacher_buy_list", {})
    st.header("今日可買進名單")
    st.caption("定位：股市老師盤前名單。先給答案，再給買點、停損與理由。這是決策輔助，不是保證獲利。")
    st.info(teacher.get("headline", "今日尚無可買進名單。"))
    st.write(teacher.get("summary", ""))

    ready = teacher.get("ready_to_buy", [])
    wait_breakout = teacher.get("wait_breakout", [])
    pullback_watch = teacher.get("pullback_watch", [])
    observe = teacher.get("observe_only", [])
    avoid = teacher.get("avoid_or_reduce", [])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("A｜今日可行動", len(ready))
    m2.metric("B｜等突破/拉回", len(wait_breakout) + len(pullback_watch))
    m3.metric("C｜只觀察", len(observe))
    m4.metric("D｜避免/減碼", len(avoid))

    with st.expander("A/B/C/D 等級定義", expanded=False):
        for grade, text in teacher.get("grading_rule", {}).items():
            st.write(f"**{grade}：** {text}")

    st.subheader("A｜今日可買進 / 可行動")
    if ready:
        for item in ready:
            render_teacher_stock_card(item, "teacher-ready")
    else:
        st.warning("今日沒有 A 級直接可行動標的。")

    st.subheader("B｜等待突破或拉回確認")
    candidate_keys: set[str] = set()
    b_items = []
    for item in wait_breakout + pullback_watch:
        if item["symbol"] in candidate_keys:
            continue
        candidate_keys.add(item["symbol"])
        b_items.append(item)
    if b_items:
        for item in b_items[:8]:
            render_teacher_stock_card(item, "teacher-b")
    else:
        st.info("目前沒有 B 級候選。")

    st.subheader("C / D｜只觀察與避免名單")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**C｜只觀察**")
        for item in observe[:6]:
            st.write(f"- {item['display_name']}｜Radar {item['radar_score']}｜{item['recommendation']}")
    with c2:
        st.write("**D｜避免 / 反彈減碼**")
        for item in avoid[:6]:
            st.write(f"- {item['display_name']}｜Radar {item['radar_score']}｜{item['recommendation']}")

    if teacher.get("portfolio_actions"):
        st.subheader("持股同步檢查")
        st.dataframe(pd.DataFrame(teacher["portfolio_actions"]), use_container_width=True, hide_index=True)


def render_add_watchlist_form(payload: dict[str, Any], location: str) -> None:
    options = stock_options(payload)
    labels = ["（不使用）"] + list(options.keys())
    with st.form(f"watchlist-form-{location}", clear_on_submit=False):
        selected_label = st.selectbox("從目前股票清單選擇", labels, key=f"watch-select-{location}")
        query = st.text_input("或輸入股號 / 股票名稱", placeholder="例如：2330、台積電、台泥", key=f"watch-query-{location}")
        submitted = st.form_submit_button("加入觀察並重新分析")
    if submitted:
        stock = resolve_user_stock(query, selected_label, payload)
        if stock:
            add_user_watchlist_item(stock.symbol, stock.name)
            st.success(f"已加入觀察：{stock.display_name}")
            refresh_product()
        else:
            st.error("找不到個股。請輸入 4 碼股號，或使用目前支援的股票名稱。")


def render_add_portfolio_form(payload: dict[str, Any], location: str) -> None:
    options = stock_options(payload)
    labels = ["（不使用）"] + list(options.keys())
    with st.form(f"portfolio-form-{location}", clear_on_submit=False):
        selected_label = st.selectbox("從目前股票清單選擇", labels, key=f"portfolio-select-{location}")
        query = st.text_input("或輸入持股股號 / 股票名稱", placeholder="例如：2330、台積電、台泥", key=f"portfolio-query-{location}")
        shares = st.number_input("股數", min_value=0.0, value=0.0, step=100.0, key=f"portfolio-shares-{location}")
        avg_cost = st.number_input("平均成本", min_value=0.0, value=0.0, step=1.0, key=f"portfolio-cost-{location}")
        note = st.text_input("備註", placeholder="例如：核心持股 / 試單", key=f"portfolio-note-{location}")
        submitted = st.form_submit_button("加入/更新持股並重新分析")
    if submitted:
        stock = resolve_user_stock(query, selected_label, payload)
        if stock and shares > 0 and avg_cost > 0:
            add_user_watchlist_item(stock.symbol, stock.name)
            add_or_update_holding(stock.symbol, stock.name, shares, avg_cost, note)
            st.success(f"已更新持股：{stock.display_name}")
            refresh_product()
        else:
            st.error("請輸入有效股號/名稱、股數與成本。")


def render_sidebar_workspace(payload: dict[str, Any]) -> None:
    st.sidebar.header("個人工作區")
    st.sidebar.caption("可用股號或股票名稱新增觀察與持股。")

    with st.sidebar.expander("新增指定觀察個股", expanded=True):
        render_add_watchlist_form(payload, "sidebar")

    watchlist = load_user_watchlist()
    if watchlist:
        st.sidebar.subheader("目前觀察清單")
        for item in watchlist:
            cols = st.sidebar.columns([3, 1])
            cols[0].write(f"{item.get('symbol')} {item.get('name')}")
            if cols[1].button("移除", key=f"remove-watch-{item.get('symbol')}"):
                remove_user_watchlist_item(str(item.get("symbol")))
                refresh_product()

    st.sidebar.divider()
    with st.sidebar.expander("新增/更新持股", expanded=False):
        render_add_portfolio_form(payload, "sidebar")

    st.sidebar.divider()
    st.sidebar.subheader("資料即時性")
    q = payload["pm_brief"]["data_quality"]
    st.sidebar.write(f"價格：{q.get('price_frequency')}")
    st.sidebar.write(f"新聞：{q.get('news_frequency')}")
    st.sidebar.caption(q.get("limitation", ""))


payload = load_payload()
if "quick_chart_symbol" not in st.session_state:
    cards = payload.get("decision_cards", [])
    st.session_state["quick_chart_symbol"] = cards[0]["symbol"] if cards else "2330"
if "active_section" not in st.session_state:
    st.session_state["active_section"] = SECTIONS[0]
if "active_section_choice" not in st.session_state:
    st.session_state["active_section_choice"] = st.session_state["active_section"]
pending_section = st.session_state.pop("pending_section", None)
if pending_section in SECTIONS:
    st.session_state["active_section"] = pending_section
    st.session_state["active_section_choice"] = pending_section

render_sidebar_workspace(payload)

st.title("🚀 AI Stock Radar")
st.caption(f"v{payload['version']}｜投資經理人波段決策平台｜台股漲紅跌綠｜法人籌碼 Radar｜個人持股總教練｜Fast Dashboard Hotfix")

header_cols = st.columns([1, 4])
with header_cols[0]:
    if st.button("重新抓取最新資料"):
        refresh_product()
with header_cols[1]:
    payload_time = payload.get("generated_at", "N/A")
    st.markdown(f'<div class="section-title">功能列表｜目前載入資料：{payload_time}</div>', unsafe_allow_html=True)

selected_section = st.radio(
    "功能列表",
    SECTIONS,
    horizontal=True,
    key="active_section_choice",
    label_visibility="collapsed",
)
st.session_state["active_section"] = selected_section

cards = payload["decision_cards"]
stock_index = payload["stock_index"]
pm = payload["pm_brief"]
quality = pm["data_quality"]

if selected_section == "盤前決策總覽":
    st.header("盤前決策總覽")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("今日市場判斷", payload["market_view"])
    m2.metric("AI 信心指數", f"{payload['ai_confidence']}%")
    m3.metric("新聞數", quality["news_items"])
    m4.metric("最新價格數", quality["price_live_count"])
    m5.metric("個人觀察", quality.get("user_watchlist_count", 0))
    m6.metric("持股檔數", quality.get("portfolio_count", 0))

    st.info(pm["headline"])
    st.subheader("今日主策略")
    st.write(pm["strategy"])
    if pm.get("recommended_stocks"):
        st.subheader("主策略推薦個股")
        rec_cols = st.columns(min(3, max(1, len(pm["recommended_stocks"]))))
        for idx, item in enumerate(pm["recommended_stocks"][:6]):
            with rec_cols[idx % len(rec_cols)]:
                with st.container(border=True):
                    st.markdown(f"**{item['display_name']}**")
                    st.write(f"{item['decision']}｜Radar {item['radar_score']}｜Confidence {item['confidence']}%")
                    st.caption(item["reason"])
                    stock_button(item["symbol"], "📈 查看線圖", f"overview-rec-{item['symbol']}-{idx}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("今日優先動作")
        for item in pm["top_actions"]:
            st.success(item)
    with c2:
        st.subheader("今日避免動作")
        for item in pm["avoid_actions"]:
            st.warning(item)

    st.subheader("今日 Top 決策卡")
    for idx, card in enumerate(cards[:5], 1):
        render_decision_card_compact(card, f"overview-card-{idx}")

    with st.expander("每日報告預覽", expanded=False):
        report_path = REPORT_PATH
        if report_path.exists():
            st.markdown(report_path.read_text(encoding="utf-8"))
        else:
            st.warning("尚未產生 daily_report.md。請按重新產生今日 Radar。")

    with st.expander("資料品質與即時性說明", expanded=False):
        dq = pd.DataFrame(
            [
                {"項目": "新聞來源", "值": quality["news_source"]},
                {"項目": "新聞數", "值": quality["news_items"]},
                {"項目": "正向訊號", "值": quality["positive_signals"]},
                {"項目": "負向訊號", "值": quality["negative_signals"]},
                {"項目": "最新價格資料", "值": quality["price_live_count"]},
                {"項目": "Fallback 價格", "值": quality["price_fallback_count"]},
                {"項目": "三大法人正式資料", "值": quality.get("institutional_official_count", 0)},
                {"項目": "法人 fallback", "值": quality.get("institutional_fallback_count", 0)},
                {"項目": "價格頻率", "值": quality.get("price_frequency", "日線資料")},
                {"項目": "新聞頻率", "值": quality.get("news_frequency", "RSS 更新")},
                {"項目": "決策維度", "值": quality.get("decision_scope", "日線技術、新聞影響、AI 產業鏈、個人觀察與持股")},
            ]
        )
        st.dataframe(dq, use_container_width=True, hide_index=True)
        st.caption(quality["limitation"])

elif selected_section == "盤前決策總覽":
    render_decision_overview(payload)

elif selected_section == "今日可買進名單":
    render_teacher_buy_list(payload)

elif selected_section == "投資經理人早會":
    st.header("投資經理人早會")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("今日市場判斷", payload["market_view"])
    m2.metric("AI 信心指數", f"{payload['ai_confidence']}%")
    m3.metric("新聞數", quality["news_items"])
    m4.metric("價格日線", quality["price_live_count"])
    m5.metric("個人觀察", quality.get("user_watchlist_count", 0))
    m6.metric("持股檔數", quality.get("portfolio_count", 0))

    st.info(pm["headline"])
    st.subheader("今日主策略")
    st.write(pm["strategy"])
    if pm.get("recommended_stocks"):
        st.subheader("主策略推薦個股")
        rec_cols = st.columns(min(3, len(pm["recommended_stocks"])))
        for idx, item in enumerate(pm["recommended_stocks"][:5]):
            with rec_cols[idx % len(rec_cols)]:
                with st.container(border=True):
                    st.markdown(f"**{item['display_name']}**")
                    st.write(f"{item['decision']}｜Radar {item['radar_score']}｜Confidence {item['confidence']}%")
                    st.caption(item["reason"])
                    stock_button(item["symbol"], "📈 查看線圖", f"pm-rec-{item['symbol']}-{idx}")
    st.subheader("資金配置建議")
    st.write(pm["capital_allocation"])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("今日優先動作")
        for item in pm["top_actions"]:
            st.success(item)
    with c2:
        st.subheader("今日避免動作")
        for item in pm["avoid_actions"]:
            st.warning(item)
    st.subheader("資料品質檢查")
    st.caption("v1.6.0 內建 AI 產業鏈 100 檔預設清單，指定觀察與持股分析皆可直接選用；清單外股票仍可用股號新增。")
    dq = pd.DataFrame(
        [
            {"項目": "新聞來源", "值": quality["news_source"]},
            {"項目": "新聞數", "值": quality["news_items"]},
            {"項目": "正向訊號", "值": quality["positive_signals"]},
            {"項目": "負向訊號", "值": quality["negative_signals"]},
            {"項目": "真實價格日線", "值": quality["price_live_count"]},
            {"項目": "Fallback 價格", "值": quality["price_fallback_count"]},
            {"項目": "價格頻率", "值": quality.get("price_frequency", "日線資料")},
            {"項目": "新聞頻率", "值": quality.get("news_frequency", "RSS 更新")},
            {"項目": "決策維度", "值": quality.get("decision_scope", "日線技術、新聞影響、AI 產業鏈、個人觀察與持股")},
        ]
    )
    st.dataframe(dq, use_container_width=True, hide_index=True)
    st.caption(quality["limitation"])

elif selected_section == "今日決策卡":
    st.header("今日波段決策卡")
    for idx, card in enumerate(cards[:10], 1):
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.subheader(f"{idx}. {decision_icon(card['decision'])} {card['display_name']}｜{card['decision']}｜{card['conviction']}")
                st.write(card["swing_view"])
                st.write(f"**部位建議：** {card['position_guidance']}")
                levels = pd.DataFrame([
                    {"項目": "突破追蹤價", "數字": card.get("breakout_price")},
                    {"項目": "拉回區間下緣", "數字": card.get("pullback_low")},
                    {"項目": "拉回區間上緣", "數字": card.get("pullback_high")},
                    {"項目": "減碼價", "數字": card.get("reduce_price")},
                    {"項目": "停損/失效價", "數字": card.get("stop_loss_price")},
                ])
                st.dataframe(levels, use_container_width=True, hide_index=True)
                st.write(f"**進場條件：** {card['entry_condition']}")
                st.write(f"**續抱條件：** {card['hold_condition']}")
                st.write(f"**減碼條件：** {card['reduce_condition']}")
                st.write(f"**失效條件：** {card['invalidation_condition']}")
                st.caption(card.get("volume_ratio_note", ""))
            with right:
                st.metric("Radar", card["radar_score"])
                st.metric("Confidence", f"{card['confidence']}%")
                st.markdown(price_html(float(card["latest_close"]), float(card["change_pct"])), unsafe_allow_html=True)
                stock_button(card["symbol"], "📈 查看線圖", f"card-chart-{card['symbol']}-{idx}")
            with st.expander("分數拆解與 Evidence Chain"):
                render_score_breakdown(card)
                for evidence in card["evidence"]:
                    icon = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
                    st.write(f"{icon} **{evidence['label']}**：{evidence['explanation']}")

elif selected_section == "法人籌碼 Radar":
    render_institutional_flow(payload)

elif selected_section == "MACD 觀察名單":
    st.header("AI 選出 MACD 觀察名單")
    st.caption("已區分：即將翻正、剛翻正、已翻正延續。不是所有名單都代表已翻正。")
    rows = []
    for item in payload["macd_candidates"]:
        rows.append(
            {
                "股票": item["display_name"],
                "狀態": item.get("macd_status", ""),
                "分數": item["score"],
                "最新價": item["latest_close"],
                "資料日期": item.get("latest_date", "N/A"),
                "價格來源": item.get("price_source", "N/A"),
                "MACD前值": item["hist_prev"],
                "MACD現值": item["hist_current"],
                "RSI": item["rsi"],
                "趨勢分": item["trend"],
                "原因": item["reason"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("快速查看線圖")
    cols = st.columns(5)
    for idx, item in enumerate(payload["macd_candidates"][:10], 1):
        with cols[(idx - 1) % 5]:
            stock_button(item["symbol"], f"{idx}. {item['display_name']}", f"macd-chart-{item['symbol']}-{idx}")

elif selected_section == "指定觀察個股":
    st.header("指定觀察個股")
    st.write("內建 AI 產業鏈 100 檔預設清單；也可用 4 碼股號或股票名稱新增清單外個股。加入後會立刻重新抓取資料並納入 Radar 分析。")
    render_add_watchlist_form(payload, "main")
    watchlist = load_user_watchlist()
    if not watchlist:
        st.info("目前尚未加入個人觀察股。")
    else:
        st.subheader("個人觀察清單分析")
        rows = []
        for item in watchlist:
            symbol = str(item.get("symbol"))
            card = find_card(payload, symbol)
            teacher_item = teacher_item_map(payload).get(symbol)
            rows.append(
                {
                    "股票": f"{symbol} {item.get('name')}",
                    "等級": teacher_item.get("grade") if teacher_item else "需重新產生",
                    "買點類型": teacher_item.get("action_type") if teacher_item else "需重新產生",
                    "Radar": card["radar_score"] if card else "需重新產生",
                    "Decision": card["decision"] if card else "需重新產生",
                    "Confidence": f"{card['confidence']}%" if card else "需重新產生",
                    "最新價": card["latest_close"] if card else "需重新產生",
                    "進場區間": teacher_item.get("suggested_entry_zone") if teacher_item else "需重新產生",
                    "突破價": teacher_item.get("breakout_trigger") if teacher_item else "需重新產生",
                    "失效價": teacher_item.get("invalidation_price") if teacher_item else "需重新產生",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        for idx, item in enumerate(watchlist):
            symbol = str(item.get("symbol"))
            card = find_card(payload, symbol)
            teacher_item = teacher_item_map(payload).get(symbol)
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.subheader(f"{symbol} {item.get('name')}")
                    if teacher_item:
                        st.write(f"**等級/買點：** {teacher_item['grade']}｜{teacher_item['action_type']}")
                        st.write(f"**建議：** {teacher_item['recommendation']}")
                        st.write(f"**買進區間：** {teacher_item['suggested_entry_zone']}｜**突破：** {teacher_item['breakout_trigger']:.2f}｜**失效：** {teacher_item['invalidation_price']:.2f}")
                    if card:
                        st.write(f"**AI觀點：** {card['swing_view']}")
                        st.write(f"**進場條件：** {card['entry_condition']}")
                        st.write(f"**減碼條件：** {card['reduce_condition']}")
                    else:
                        st.warning("此股票尚未納入目前分析 payload，請按重新抓取最新資料。")
                with c2:
                    if card:
                        st.metric("Radar", card["radar_score"])
                        st.markdown(price_html(float(card["latest_close"]), float(card["change_pct"])), unsafe_allow_html=True)
                    stock_button(symbol, "📈 查看線圖", f"watch-chart-{idx}")
                    if st.button("移除觀察", key=f"watch-remove-main-{idx}"):
                        remove_user_watchlist_item(symbol)
                        refresh_product()

elif selected_section == "個人持股分析":
    st.header("個人持股分析")
    st.write("可用股號或股票名稱新增持股。加入後會立刻納入 Radar，並以成本、最新價、技術位置、今日策略與失效條件產生波段管理建議。")
    render_add_portfolio_form(payload, "main")
    rows = payload.get("portfolio_analysis", [])
    if not rows:
        st.info("目前尚未輸入個人持股。")
    else:
        table_rows = []
        for row in rows:
            table_rows.append(
                {
                    "股票": row["display_name"],
                    "股數": row["shares"],
                    "成本": row["avg_cost"],
                    "最新價": row["latest_close"],
                    "未實現損益": row["pnl"],
                    "損益%": row["pnl_pct"],
                    "Decision": row["decision"],
                    "Radar": row["radar_score"],
                    "突破價": row.get("breakout_price"),
                    "減碼價": row.get("reduce_price"),
                    "失效價": row.get("stop_loss_price"),
                    "AI建議": row["action"],
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        total_value = sum(float(row["market_value"]) for row in rows)
        total_cost = sum(float(row["cost_value"]) for row in rows)
        total_pnl = total_value - total_cost
        total_pct = 0 if total_cost == 0 else total_pnl / total_cost * 100
        st.markdown(price_html(total_pnl, total_pct, prefix="整體未實現損益"), unsafe_allow_html=True)

        coach = payload.get("portfolio_coach", {})
        if coach:
            st.subheader("股市老師持股總教練")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("持股市值", f"{coach.get('total_market_value', 0):,.0f}")
            c2.metric("總損益", f"{coach.get('total_pnl', 0):,.0f}")
            c3.metric("總損益%", f"{coach.get('total_pnl_pct', 0):.2f}%")
            c4.metric("組合風險", coach.get("risk_level", "N/A"))
            st.info(coach.get("headline", ""))
            st.write(coach.get("summary", ""))
            pc1, pc2 = st.columns(2)
            with pc1:
                st.write("**老師建議動作**")
                for action in coach.get("teacher_actions", []):
                    st.success(action)
                st.write("**調整計畫**")
                for action in coach.get("rebalance_plan", []):
                    st.write(f"- {action}")
            with pc2:
                st.write("**組合風險提醒**")
                for item in coach.get("risk_alerts", []):
                    st.warning(item)
                concentration = coach.get("concentration", [])
                if concentration:
                    st.write("**持股集中度**")
                    st.dataframe(pd.DataFrame(concentration), use_container_width=True, hide_index=True)

        st.subheader("持股逐檔管理建議")
        for idx, row in enumerate(rows):
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.subheader(f"{row['display_name']}｜{row['decision']}｜Radar {row['radar_score']}")
                    st.write(f"**損益：** {row['pnl']:.0f}（{row['pnl_pct']:.2f}%）｜成本 {row['avg_cost']:.2f}｜最新 {row['latest_close']:.2f}")
                    st.write(f"**AI建議：** {row['action']}")
                    st.write(f"**進場/加碼：** {row.get('entry_condition', '')}")
                    st.write(f"**減碼：** {row.get('reduce_condition', '')}")
                    st.write(f"**失效：** {row.get('invalidation_condition', '')}")
                    st.caption(f"價格來源：{row.get('price_source', 'N/A')}｜資料日期：{row.get('latest_date', 'N/A')}")
                with right:
                    stock_button(row["symbol"], "📈 查看線圖", f"portfolio-chart-{idx}")
                    if st.button("移除持股", key=f"portfolio-remove-{idx}"):
                        remove_holding(row["symbol"])
                        refresh_product()

elif selected_section == "個股技術線圖":
    st.header("個股技術線圖")
    options = stock_options(payload)
    labels = list(options.keys())
    current_symbol = st.session_state["quick_chart_symbol"]
    current_label = next((label for label, symbol in options.items() if symbol == current_symbol), labels[0])
    selected_label = st.selectbox("選擇個股", labels, index=labels.index(current_label), key="chart-select")
    selected_symbol = options[selected_label]
    st.session_state["quick_chart_symbol"] = selected_symbol
    render_stock_chart(payload, selected_symbol, chart_context="selected")

elif selected_section == "新聞影響鏈":
    st.header("新聞影響鏈")
    for idx, item in enumerate(payload["news_items"], 1):
        with st.container(border=True):
            icon = "✅" if item["impact"] == "positive" else "⚠️" if item["impact"] == "negative" else "➖"
            title = html.escape(item["title_zh"])
            url = item.get("source_url") or ""
            if url:
                st.markdown(f'<div class="news-link"><a href="{html.escape(url)}" target="_blank">{idx}. {icon} {title}</a></div>', unsafe_allow_html=True)
            else:
                st.subheader(f"{idx}. {icon} {item['title_zh']}")
            st.caption(f"來源：{item['source']}｜發布：{item.get('published', '')}｜Signal：{item['signal']}")
            st.write(item["summary_zh"])
            st.write("**影響個股：**")
            cols = st.columns(4)
            for stock_idx, stock_name in enumerate(item.get("affected_stocks", [])):
                symbol = stock_name.split()[0]
                with cols[stock_idx % 4]:
                    stock_button(symbol, stock_name, f"news-{idx}-{symbol}-{stock_idx}")

elif selected_section == "每日報告":
    st.header("每日 Markdown 報告")
    report_path = REPORT_PATH
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.warning("尚未產生 daily_report.md。請按重新產生今日 Radar。")
