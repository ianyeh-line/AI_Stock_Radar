from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
SRC = APP_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from radar.core.indicators import ema_series
from radar.core.report import build_markdown, save_outputs
from radar.data.stock_master import resolve_stock
from radar.data.user_store import load_portfolio, save_portfolio, load_watchlist, save_watchlist, storage_status
from radar.integrations.cloud_user_store import cloud_status, is_cloud_store_configured
from radar.teacher.decision import build_decision_card, run_teacher_pipeline

st.set_page_config(page_title="AI Stock Radar 3.2", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem; }
    .tw-red { color:#DC2626; font-weight:700; }
    .tw-green { color:#16A34A; font-weight:700; }
    .tw-gray { color:#374151; font-weight:700; }
    .small-muted { color:#6B7280; font-size:0.88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

PAYLOAD_PATH = Path("output/dashboard_data.json")
REPORT_PATH = Path("output/daily_report.md")


def is_streamlit_cloud_env() -> bool:
    cwd = str(Path.cwd())
    home = os.environ.get("HOME", "")
    return os.environ.get("STREAMLIT_CLOUD") == "1" or home == "/home/adminuser" or "/mount/src" in cwd


def beta_identity(email: str, code: str) -> str:
    raw = f"{email.strip().lower()}|{code.strip()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"beta_{digest}@ai-stock-radar.local"


def ensure_user_mode_defaults() -> None:
    st.session_state.setdefault("guest_watchlist", [])
    st.session_state.setdefault("guest_portfolio", [])
    if "guest_mode_enabled" not in st.session_state:
        st.session_state["guest_mode_enabled"] = is_streamlit_cloud_env()


def render_beta_access() -> None:
    ensure_user_mode_defaults()
    st.sidebar.header("👤 使用者資料")
    cloud = cloud_status()
    current_email = st.session_state.get("beta_access_email", "")
    current_key = st.session_state.get("cloud_user_email", "")
    if current_key:
        st.sidebar.success(f"目前使用者：{current_email or 'Beta 使用者'}")
        if is_cloud_store_configured():
            st.sidebar.caption("持股與觀察清單會保存到 Supabase。")
        else:
            st.sidebar.warning("Supabase 尚未設定，資料只會暫存在本次瀏覽。")
        if st.sidebar.button("登出 / 切回訪客"):
            for k in ["cloud_user_email", "beta_access_email", "beta_access_enabled"]:
                st.session_state.pop(k, None)
            st.session_state["guest_mode_enabled"] = True
            st.rerun()
        return

    st.sidebar.caption("朋友若要下次保留持股，請使用 Email + 自訂存取碼。")
    email = st.sidebar.text_input("Email", key="beta_email_input", placeholder="friend@example.com")
    code = st.sidebar.text_input("自訂存取碼", type="password", key="beta_code_input", placeholder="自己記得住即可")
    if st.sidebar.button("載入 / 保存我的資料"):
        if not email.strip() or not code.strip():
            st.sidebar.error("請輸入 Email 與存取碼。")
        else:
            st.session_state["cloud_user_email"] = beta_identity(email, code)
            st.session_state["beta_access_email"] = email.strip().lower()
            st.session_state["beta_access_enabled"] = True
            st.session_state["guest_mode_enabled"] = not is_cloud_store_configured()
            st.rerun()
    st.sidebar.caption(f"雲端資料庫狀態：{cloud['status']}")
    if not is_cloud_store_configured():
        st.sidebar.info("未設定 Supabase 時仍可體驗，但重新開瀏覽器後資料不會永久保存。")


def run_pipeline() -> dict:
    payload = run_teacher_pipeline()
    if st.session_state.get("guest_mode_enabled") or st.session_state.get("cloud_user_email"):
        st.session_state["dashboard_payload"] = payload
        st.session_state["report_md"] = build_markdown(payload)
    else:
        save_outputs(payload)
    return payload


def load_payload() -> dict:
    if st.session_state.get("dashboard_payload"):
        return st.session_state["dashboard_payload"]
    if (st.session_state.get("guest_mode_enabled") or st.session_state.get("cloud_user_email")) and not PAYLOAD_PATH.exists():
        return run_pipeline()
    if PAYLOAD_PATH.exists():
        return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    return run_pipeline()


def current_report(payload: dict) -> str:
    if st.session_state.get("report_md"):
        return st.session_state["report_md"]
    if REPORT_PATH.exists():
        return REPORT_PATH.read_text(encoding="utf-8")
    return build_markdown(payload)


def price_class(change: float) -> str:
    if change > 0:
        return "tw-red"
    if change < 0:
        return "tw-green"
    return "tw-gray"


def render_data_trust(card: dict) -> None:
    trust = card.get("data_trust") or {}
    status = trust.get("status", "未知")
    if trust.get("actionable"):
        st.success(f"資料可信度：{status}｜資料日：{card.get('latest_date')}｜來源：{card.get('price_source')}")
    else:
        st.warning(f"資料可信度：{status}｜資料日：{card.get('latest_date')}｜來源：{card.get('price_source')}")
        for warning in trust.get("warnings", []):
            st.caption(f"⚠️ {warning}")


def render_card(card: dict, show_trust: bool = True) -> None:
    t = card["tech"]
    css = price_class(t["change_pct"])
    with st.container(border=True):
        st.subheader(f"{card['label']}｜{card['setup']}｜等級 {card['grade']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Radar", card["score"])
        c2.metric("信心", f"{card['confidence']}%")
        c3.markdown(f"<div class='small-muted'>最新價</div><div class='{css}'>{t['close']:.2f}（{t['change_pct']}%）</div>", unsafe_allow_html=True)
        c4.write(f"資料日：{card['latest_date']}")
        st.write(f"**老師建議：** {card['action']}")
        st.write(f"**風險紀律：** {card['risk']}")
        st.write("**理由：** " + "、".join(card["reasons"][:6]))
        macd = t["macd"]
        st.caption(f"MACD(DIF)：{macd['macd']}｜DEA：{macd['signal']}｜柱狀體：{macd['hist']}｜0軸判斷：{macd.get('zero_axis_status')}")
        if show_trust:
            render_data_trust(card)


def _macd_chart_series(closes: list[float]) -> dict:
    if len(closes) < 35:
        return {"macd": [], "signal": [], "hist": []}
    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    dif = [a - b for a, b in zip(ema12[-len(ema26):], ema26)]
    dea = ema_series(dif, 9)
    hist = [m - s for m, s in zip(dif[-len(dea):], dea)]
    n = min(len(dif), len(dea), len(hist))
    return {"macd": dif[-n:], "signal": dea[-n:], "hist": hist[-n:]}


def render_technical_chart(card: dict, key: str) -> None:
    range_label = st.radio("觀察區間", ["1個月", "3個月", "6個月", "1年"], index=1, horizontal=True, key=f"range-{key}")
    days = {"1個月": 30, "3個月": 90, "6個月": 180, "1年": 252}[range_label]
    rows = card.get("prices", [])[-days:]
    if len(rows) < 20:
        st.warning("價格資料不足，無法繪製完整技術圖。")
        return
    df = pd.DataFrame(rows)
    closes = [float(x) for x in df["close"].tolist()]
    macd_series = _macd_chart_series(closes)
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.52, 0.18, 0.20, 0.10],
        subplot_titles=("K線 / MA", "成交量", "MACD", "RSI / KD / BIAS 摘要"),
    )
    up = "#DC2626"  # Taiwan up red
    down = "#16A34A"  # Taiwan down green
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], increasing_line_color=up, decreasing_line_color=down, name="K線"), row=1, col=1)
    for w, name in [(5, "MA5"), (10, "MA10"), (20, "MA20")]:
        fig.add_trace(go.Scatter(x=df["date"], y=df["close"].rolling(w).mean(), mode="lines", name=name), row=1, col=1)
    colors = [up if c >= o else down for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="成交量"), row=2, col=1)
    if macd_series["macd"]:
        x = df["date"].tolist()[-len(macd_series["macd"]):]
        hist_colors = [up if h >= 0 else down for h in macd_series["hist"]]
        fig.add_trace(go.Bar(x=x, y=macd_series["hist"], marker_color=hist_colors, name="Hist"), row=3, col=1)
        fig.add_trace(go.Scatter(x=x, y=macd_series["macd"], mode="lines", name="MACD/DIF"), row=3, col=1)
        fig.add_trace(go.Scatter(x=x, y=macd_series["signal"], mode="lines", name="DEA"), row=3, col=1)
        fig.add_hline(y=0, line_width=1, line_dash="dash", row=3, col=1)
    tech = card["tech"]
    summary = f"RSI {tech.get('rsi')}｜KD {tech.get('kd', {}).get('k')}/{tech.get('kd', {}).get('d')}｜BIAS20 {tech.get('bias20')}%｜量能比 {tech.get('volume_ratio')}"
    fig.add_trace(go.Scatter(x=[df["date"].iloc[-1]], y=[0], mode="text", text=[summary], textposition="middle center", showlegend=False), row=4, col=1)
    fig.update_layout(height=760, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True, key=f"chart-{key}")


def add_watchlist_ui() -> None:
    st.subheader("新增指定觀察個股")
    text = st.text_input("輸入股號或名稱", placeholder="例如：2313、華通；清單外可輸入股號或『股號 股票名稱』", key="watch_input")
    if st.button("加入觀察清單"):
        try:
            stock = resolve_stock(text)
            card = build_decision_card(stock)
            items = load_watchlist()
            if not any(i.get("symbol") == card["symbol"] for i in items):
                items.append({"symbol": card["symbol"], "name": card["name"]})
                save_watchlist(items)
            st.success(f"已加入 {card['label']}")
            st.session_state.pop("dashboard_payload", None)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def add_portfolio_ui() -> None:
    st.subheader("新增個人持股")
    text = st.text_input("股號或名稱", placeholder="例如：3037、欣興；清單外可輸入股號或『股號 股票名稱』", key="portfolio_symbol")
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
            st.session_state.pop("dashboard_payload", None)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


ensure_user_mode_defaults()
render_beta_access()

st.title("🚀 AI Stock Radar 3.2｜AI 股市老師")
st.caption("本版重點：資料可信度防呆、MACD 0軸判斷修正、Beta Access 持股保存、個股技術圖表升級。")

if st.button("重新產生今日決策資料"):
    with st.spinner("股市老師重新抓取與分析中..."):
        payload = run_pipeline()
    st.success("已完成更新")
else:
    payload = load_payload()

status = payload["trading_status"]
st.caption(f"日期：{status['date']}｜星期{status['weekday']}｜交易狀態：{status['session']}｜版本：{payload.get('version')}")
st.info(payload["teacher_summary"])
store = storage_status()
st.caption(f"使用者資料：{store['label']}｜{store['detail']}")

k1, k2, k3, k4 = st.columns(4)
k1.metric("市場結論", payload["market_view"])
k2.metric("今日可買", len(payload["buy_list"]))
k3.metric("等待突破", len(payload["wait_list"]))
k4.metric("避免名單", len(payload["avoid_list"]))

tabs = st.tabs(["今日可買", "等待/避免", "持股總教練", "觀察清單", "MACD觀察", "0軸MACD", "資料可信度", "個股線圖", "每日報告"])

with tabs[0]:
    st.header("今日可買進名單")
    if not payload["buy_list"]:
        st.warning("今日沒有 A 級可買進名單。資料不足或買點不佳時，股市老師不硬給買進。")
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
                render_data_trust(row["card"])
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
    st.header("MACD 觀察名單：柱狀體翻正")
    for card in payload["macd_list"][:10]:
        t = card["tech"]
        st.write(f"**{card['label']}**｜{t['macd']['status']}｜Hist {t['macd']['hist']}｜MACD(DIF) {t['macd']['macd']}｜最新價 {t['close']}｜RSI {t['rsi']}")

with tabs[5]:
    st.header("MACD 即將從 0 軸翻正")
    st.caption("重點看 MACD/DIF 線與 0 軸的位置。若 MACD 已在 0 軸上方，不會再被錯誤標示為 0 軸下方偏弱。")
    zero_items = payload.get("macd_zero_axis_list", [])[:10]
    if not zero_items:
        st.info("目前沒有符合『即將或剛從 0 軸轉強』的名單；沒有訊號時不硬湊推薦。")
    for card in zero_items:
        t = card["tech"]
        st.write(f"**{card['label']}**｜{t['macd'].get('zero_axis_status')}｜MACD(DIF) {t['macd']['macd']}｜DEA {t['macd']['signal']}｜最新價 {t['close']}｜{card['decision']}｜{card['action']}")

with tabs[6]:
    st.header("資料可信度")
    st.caption("本版不做回測，優先防止舊資料、fallback 或樣本不足時仍給買進建議。")
    all_cards = payload.get("all_cards", [])
    bad = [c for c in all_cards if not (c.get("data_trust") or {}).get("actionable")]
    good = [c for c in all_cards if (c.get("data_trust") or {}).get("actionable")]
    st.metric("可作為操作參考", len(good))
    st.metric("資料不足僅觀察", len(bad))
    for card in bad[:20]:
        with st.container(border=True):
            st.write(f"**{card['label']}**｜{card['latest_date']}｜{card['price_source']}｜{card['data_trust']['status']}")
            for warning in card["data_trust"].get("warnings", []):
                st.caption(f"⚠️ {warning}")

with tabs[7]:
    st.header("個股技術線圖")
    dynamic_cards = payload["all_cards"][:30] + payload.get("watchlist_analysis", []) + [row.get("card") for row in payload.get("portfolio_coach", {}).get("rows", []) if row.get("card")]
    choices = {card["label"]: card for card in dynamic_cards}
    selected = st.selectbox("選擇個股", list(choices.keys()))
    render_technical_chart(choices[selected], key=choices[selected]["symbol"])

with tabs[8]:
    st.markdown(current_report(payload))
