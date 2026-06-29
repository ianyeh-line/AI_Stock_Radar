from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from radar.core.report import run_and_save
from radar.data.stock_master import resolve_stock, ai_universe
from radar.data.user_store import load_portfolio, save_portfolio, load_watchlist, save_watchlist
from radar.teacher.decision import build_decision_card, run_teacher_pipeline

st.set_page_config(page_title="AI Stock Radar 3.1", page_icon="🚀", layout="wide")


def load_payload():
    path = Path("output/dashboard_data.json")
    if path.exists():
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    return run_and_save()


def price_color(change):
    if change > 0:
        return "#DC2626"  # Taiwan up red
    if change < 0:
        return "#16A34A"  # Taiwan down green
    return "#374151"


def render_card(card):
    t = card["tech"]
    color = price_color(t["change_pct"])
    with st.container(border=True):
        st.subheader(f"{card['label']}｜{card['setup']}｜等級 {card['grade']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Radar", card["score"])
        c2.metric("信心", f"{card['confidence']}%")
        c3.markdown(f"<div style='font-size:1rem;color:{color};font-weight:600'>最新價 {t['close']:.2f}（{t['change_pct']}%）</div>", unsafe_allow_html=True)
        c4.write(f"資料日：{card['latest_date']}")
        st.write(f"**老師建議：** {card['action']}")
        st.write(f"**風險紀律：** {card['risk']}")
        st.write("**理由：** " + "、".join(card["reasons"][:6]))


def render_chart(card, key):
    rows = card.get("prices", [])[-90:]
    if not rows:
        st.warning("沒有價格資料")
        return
    df = pd.DataFrame(rows)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    up_color = "#DC2626"
    down_color = "#16A34A"
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], increasing_line_color=up_color, decreasing_line_color=down_color, name="K線"), row=1, col=1)
    for w, name in [(5, "MA5"), (10, "MA10"), (20, "MA20")]:
        fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(w).mean(), mode="lines", name=name), row=1, col=1)
    colors = [up_color if c >= o else down_color for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="成交量"), row=2, col=1)
    fig.update_layout(height=560, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True, key=key)


def add_watchlist_ui():
    st.subheader("新增指定觀察個股")
    text = st.text_input("輸入股號或名稱", placeholder="例如：2313、華通，清單外請輸入股號或「股號 股票名稱」", key="watch_input")
    if st.button("加入觀察清單"):
        try:
            stock = resolve_stock(text)
            card = build_decision_card(stock)
            items = load_watchlist()
            if not any(i.get("symbol") == card["symbol"] for i in items):
                items.append({"symbol": card["symbol"], "name": card["name"]})
                save_watchlist(items)
            st.success(f"已加入 {card['label']}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def add_portfolio_ui():
    st.subheader("新增個人持股")
    text = st.text_input("股號或名稱", placeholder="例如：2327、國巨，清單外請輸入股號或「股號 股票名稱」", key="portfolio_symbol")
    col1, col2 = st.columns(2)
    shares = col1.number_input("股數", min_value=0.0, step=100.0, value=0.0)
    cost = col2.number_input("成本", min_value=0.0, step=1.0, value=0.0)
    if st.button("加入 / 更新持股"):
        try:
            stock = resolve_stock(text)
            card = build_decision_card(stock)
            items = [i for i in load_portfolio() if i.get("symbol") != card["symbol"]]
            items.append({"symbol": card["symbol"], "name": card["name"], "shares": shares, "cost": cost})
            save_portfolio(items)
            st.success(f"已儲存 {card['label']}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


st.title("🚀 AI Stock Radar 3.1｜股市老師盤前決策")

if st.button("重新產生今日決策資料"):
    with st.spinner("股市老師重新抓取與分析中..."):
        payload = run_and_save()
    st.success("已完成更新")
else:
    payload = load_payload()

status = payload["trading_status"]
st.caption(f"日期：{status['date']}｜星期{status['weekday']}｜交易狀態：{status['session']}｜版本：{payload.get('version')}")
st.info(payload["teacher_summary"])

k1, k2, k3, k4 = st.columns(4)
k1.metric("市場結論", payload["market_view"])
k2.metric("今日可買", len(payload["buy_list"]))
k3.metric("等待突破", len(payload["wait_list"]))
k4.metric("避免名單", len(payload["avoid_list"]))

tabs = st.tabs(["今日可買", "等待/避免", "持股總教練", "觀察清單", "MACD觀察", "0軸MACD", "個股線圖", "每日報告"])

with tabs[0]:
    st.header("今日可買進名單")
    if not payload["buy_list"]:
        st.warning("今日沒有 A 級可買進名單。股市老師建議等待更好的買點。")
    for card in payload["buy_list"][:8]:
        render_card(card)

with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("等待突破 / 拉回")
        for card in payload["wait_list"][:8]:
            render_card(card)
    with c2:
        st.subheader("今日避免")
        for card in payload["avoid_list"][:8]:
            render_card(card)

with tabs[2]:
    st.header("個人持股分析｜股市老師總教練")
    add_portfolio_ui()
    coach = run_teacher_pipeline()["portfolio_coach"]
    st.write(coach["summary"])
    if coach["rows"]:
        st.metric("總損益", f"{coach['total_pnl']:.0f}", f"{coach['total_pnl_pct']}%")
        for row in coach["rows"]:
            with st.container(border=True):
                st.subheader(row["stock"])
                st.write(f"股數：{row['shares']}｜成本：{row['cost']}｜市值：{row['value']}｜損益：{row['pnl']}（{row['pnl_pct']}%）")
                st.write("**老師建議：** " + row["advice"])
                st.write("**個股動作：** " + row["card"]["action"])
    else:
        st.info("尚未輸入持股。")

with tabs[3]:
    st.header("指定觀察個股")
    add_watchlist_ui()
    items = load_watchlist()
    if not items:
        st.info("尚未加入觀察清單。")
    for item in items:
        try:
            card = build_decision_card(resolve_stock(item.get("symbol") or item.get("name")))
            render_card(card)
        except Exception as exc:
            st.error(str(exc))

with tabs[4]:
    st.header("MACD 觀察名單")
    for card in payload["macd_list"][:10]:
        t = card["tech"]
        st.write(f"**{card['label']}**｜{t['macd']['status']}｜Hist {t['macd']['hist']}｜最新價 {t['close']}｜RSI {t['rsi']}")

with tabs[5]:
    st.header("MACD 即將從 0 軸翻正")
    st.caption("這個名單優先找 MACD 線接近或剛站上 0 軸的股票；這比單純柱狀體翻正更適合波段觀察。")
    for card in payload.get("macd_zero_axis_list", [])[:10]:
        t = card["tech"]
        st.write(f"**{card['label']}**｜{t['macd'].get('zero_axis_status')}｜MACD {t['macd']['macd']}｜最新價 {t['close']}｜{card['decision']}｜{card['action']}")

with tabs[6]:
    st.header("個股技術線圖")
    dynamic_cards = payload["all_cards"][:30] + payload.get("watchlist_analysis", []) + [row.get("card") for row in payload.get("portfolio_coach", {}).get("rows", []) if row.get("card")]
    choices = {card["label"]: card for card in dynamic_cards}
    selected = st.selectbox("選擇個股", list(choices.keys()))
    render_chart(choices[selected], key=f"chart-{choices[selected]['symbol']}")

with tabs[7]:
    path = Path("output/daily_report.md")
    if path.exists():
        st.markdown(path.read_text(encoding="utf-8"))
    else:
        st.info("尚未產生日報。")
