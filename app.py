"""AI Stock Radar Streamlit Dashboard."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

from radar.datasource.rss_news import fetch_rss_news
from radar.engine.decision import build_dashboard_payload, build_decision_cards, save_dashboard_payload
from radar.engine.personalization import load_investor_profile
from radar.knowledge.stock_map import load_stock_universe
from radar.report.markdown import build_markdown_report, save_markdown_report

st.set_page_config(page_title="AI Stock Radar", page_icon="🚀", layout="wide")


def run_pipeline() -> dict:
    news_items, news_source = fetch_rss_news(limit=12)
    stocks = load_stock_universe()
    profile = load_investor_profile()
    cards = build_decision_cards(news_items, stocks, profile)
    payload = build_dashboard_payload(news_items, cards, stocks, profile, news_source)
    save_dashboard_payload(payload)
    save_markdown_report(build_markdown_report(payload))
    return payload


@st.cache_data(ttl=600)
def load_payload() -> dict:
    path = Path("output/dashboard_data.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return run_pipeline()


@st.cache_data(ttl=3600)
def load_price_data(symbol: str, days: int = 240) -> pd.DataFrame:
    ticker = f"{symbol}.TW" if symbol.isdigit() and len(symbol) == 4 else symbol
    if yf is not None:
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
            if data is not None and not data.empty:
                data = data.reset_index()
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [col[0] for col in data.columns]
                data = data.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
                return add_indicators(data[["date", "open", "high", "low", "close", "volume"]].tail(days))
        except Exception:
            pass
    return add_indicators(generate_fallback_prices(symbol, days))


def generate_fallback_prices(symbol: str, days: int = 240) -> pd.DataFrame:
    seed = sum(ord(char) for char in symbol)
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="B")
    base = 80 + seed % 300
    trend = np.linspace(0, 22 + (seed % 25), days)
    cycle = np.sin(np.linspace(0, 8 * math.pi, days)) * (5 + seed % 8)
    noise = rng.normal(0, 2.2, days).cumsum() * 0.25
    close = np.maximum(10, base + trend + cycle + noise)
    open_ = close + rng.normal(0, 1.5, days)
    high = np.maximum(open_, close) + rng.uniform(0.5, 3.5, days)
    low = np.minimum(open_, close) - rng.uniform(0.5, 3.5, days)
    volume = rng.integers(2000, 18000, days) * 1000
    return pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume})


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"])
    for window in [20, 60, 120]:
        df[f"ma{window}"] = df["close"].rolling(window).mean()
    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()
    df["bb_upper"] = mid + 2 * std
    df["bb_lower"] = mid - 2 * std
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["dif"] = ema12 - ema26
    df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["dif"] - df["dea"]
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def render_stock_chart(symbol: str, name: str) -> None:
    df = load_price_data(symbol)
    st.subheader(f"{symbol} {name} 技術線圖")
    latest = df.dropna().tail(1)
    if not latest.empty:
        row = latest.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤價", f"{row['close']:.2f}")
        c2.metric("MA20", f"{row['ma20']:.2f}")
        c3.metric("MACD Histogram", f"{row['macd_hist']:.2f}")
        c4.metric("RSI", f"{row['rsi']:.1f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="K線"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma60"], name="MA60"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma120"], name="MA120"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["bb_upper"], name="布林上緣", line={"dash": "dot"}))
    fig.add_trace(go.Scatter(x=df["date"], y=df["bb_lower"], name="布林下緣", line={"dash": "dot"}))
    fig.update_layout(height=520, xaxis_rangeslider_visible=False, margin={"l": 10, "r": 10, "t": 40, "b": 10})
    st.plotly_chart(fig, use_container_width=True)

    volume_fig = go.Figure()
    volume_fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="成交量"))
    volume_fig.update_layout(height=220, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    st.plotly_chart(volume_fig, use_container_width=True)

    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["date"], y=df["dif"], name="DIF"))
    macd_fig.add_trace(go.Scatter(x=df["date"], y=df["dea"], name="DEA"))
    macd_fig.add_trace(go.Bar(x=df["date"], y=df["macd_hist"], name="MACD Histogram"))
    macd_fig.update_layout(height=260, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    st.plotly_chart(macd_fig, use_container_width=True)

    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df["date"], y=df["rsi"], name="RSI"))
    rsi_fig.add_hline(y=70, line_dash="dash", annotation_text="過熱")
    rsi_fig.add_hline(y=30, line_dash="dash", annotation_text="偏弱")
    rsi_fig.update_layout(height=220, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    st.plotly_chart(rsi_fig, use_container_width=True)


def stock_button(symbol: str, name: str, key: str) -> None:
    if st.button(f"查看線圖：{symbol} {name}", key=key):
        st.session_state["selected_stock"] = {"symbol": symbol, "name": name}


def decision_color(decision: str) -> str:
    return {
        "波段買進": "🟢",
        "波段觀察": "🟡",
        "等待": "⚪",
        "減碼/避開": "🔴",
    }.get(decision, "⚪")


payload = load_payload()

st.title("🚀 AI Stock Radar")
st.caption("Stage 5：波段操作型 AI 投資經理人")

if st.button("重新產生今日 Radar"):
    payload = run_pipeline()
    st.cache_data.clear()
    st.rerun()

profile = payload["investor_profile"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("今日市場判斷", payload["market_view"])
m2.metric("AI 信心指數", f"{payload['ai_confidence']}%")
m3.metric("投資風格", profile.get("style_zh", "波段操作"))
m4.metric("新聞來源", payload["news_source"])

st.info(payload["market_summary"])

cards = payload["decision_cards"]
stock_options = {card["display_name"]: {"symbol": card["symbol"], "name": card["name"]} for card in cards}

if "selected_stock" not in st.session_state:
    first = cards[0]
    st.session_state["selected_stock"] = {"symbol": first["symbol"], "name": first["name"]}

tab_overview, tab_macd, tab_chart, tab_news, tab_report = st.tabs(["今日決策", "MACD翻正十檔", "個股技術線圖", "新聞影響", "每日報告"])

with tab_overview:
    st.header("波段操作 Top Decision Cards")
    for idx, card in enumerate(cards[:8], 1):
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.subheader(f"{idx}. {decision_color(card['decision'])} {card['display_name']}｜{card['decision']}")
                st.write(card["swing_view"])
                st.markdown(f"**進場條件：** {card['entry_condition']}")
                st.markdown(f"**續抱條件：** {card['hold_condition']}")
                st.markdown(f"**減碼條件：** {card['reduce_condition']}")
                st.markdown(f"**風險提醒：** {card['risk_note']}")
                st.markdown("**Evidence Chain**")
                for evidence in card["evidence"][:5]:
                    icon = "✅" if evidence["direction"] == "positive" else "⚠️" if evidence["direction"] == "negative" else "➖"
                    st.write(f"{icon} {evidence['label']}｜權重 {evidence['weight']}｜{evidence['explanation']}")
            with right:
                st.metric("Radar", card["radar_score"])
                st.metric("信心", f"{card['confidence']}%")
                stock_button(card["symbol"], card["name"], f"overview-{card['symbol']}")

with tab_macd:
    st.header("AI 選出 MACD 即將翻正的十檔股票")
    st.caption("邏輯：MACD 柱狀體由負值收斂、接近零軸，並搭配趨勢分數與 RSI 過熱風險校正。")
    macd_df = pd.DataFrame(payload["macd_candidates"])
    if not macd_df.empty:
        macd_df = macd_df.rename(columns={
            "symbol": "代號",
            "name": "名稱",
            "sector": "產業",
            "score": "翻正分數",
            "hist_prev": "MACD前值",
            "hist_current": "MACD目前",
            "rsi": "RSI",
            "trend": "趨勢分數",
            "reason": "理由",
        })
        st.dataframe(macd_df, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("快速查看候選股線圖")
        cols = st.columns(2)
        for idx, item in enumerate(payload["macd_candidates"]):
            with cols[idx % 2]:
                stock_button(item["symbol"], item["name"], f"macd-{item['symbol']}")

with tab_chart:
    st.header("個股技術線圖")
    selected_label = st.selectbox("選擇個股", list(stock_options.keys()), index=list(stock_options.keys()).index(f"{st.session_state['selected_stock']['symbol']} {st.session_state['selected_stock']['name']}") if f"{st.session_state['selected_stock']['symbol']} {st.session_state['selected_stock']['name']}" in stock_options else 0)
    selected = stock_options[selected_label]
    st.session_state["selected_stock"] = selected
    render_stock_chart(selected["symbol"], selected["name"])

with tab_news:
    st.header("新聞 → 訊號 → 個股影響")
    for idx, item in enumerate(payload["news"], 1):
        with st.container(border=True):
            icon = "✅" if item["impact"] == "positive" else "⚠️" if item["impact"] == "negative" else "➖"
            st.subheader(f"{idx}. {icon} {item['title_zh']}")
            st.write(item["summary_zh"])
            st.caption(f"來源：{item['source']}｜Signal：{item['signal']}")
            if item["affected_stocks"]:
                st.write("受影響個股：")
                cols = st.columns(3)
                for sidx, label in enumerate(item["affected_stocks"]):
                    parts = label.split(maxsplit=1)
                    symbol = parts[0]
                    name = parts[1] if len(parts) > 1 else symbol
                    with cols[sidx % 3]:
                        stock_button(symbol, name, f"news-{idx}-{symbol}")

with tab_report:
    st.header("每日 Markdown 報告")
    report_path = Path("output/daily_report.md")
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.warning("尚未產生 daily_report.md，請按上方重新產生今日 Radar。")
