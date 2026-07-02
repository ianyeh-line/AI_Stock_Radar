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
from radar.data.user_store import load_portfolio, save_portfolio, load_watchlist, save_watchlist, storage_status, last_save_status
from radar.integrations.cloud_user_store import cloud_status, is_cloud_store_configured, check_cloud_connection, last_cloud_error, last_cloud_response
from radar.teacher.decision import build_decision_card, run_teacher_pipeline

APP_VERSION = "3.9.0"

st.set_page_config(page_title=f"AI Stock Radar {APP_VERSION}", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem; }
    .tw-red { color:#DC2626; font-weight:700; }
    .tw-green { color:#16A34A; font-weight:700; }
    .tw-gray { color:#374151; font-weight:700; }
    .small-muted { color:#6B7280; font-size:0.88rem; }
    .market-card { border:1px solid #E5E7EB; border-radius:14px; padding:16px 18px; background:#FFFFFF; min-height:92px; }
    .market-title { color:#6B7280; font-size:0.9rem; margin-bottom:6px; }
    .market-view { font-size:1.35rem; font-weight:750; line-height:1.45; white-space:normal; overflow-wrap:anywhere; }
    .setup-box { border:1px solid #F59E0B; border-radius:12px; padding:12px; background:#FFFBEB; font-size:0.92rem; }
    .teacher-section { border-left:4px solid #2563EB; padding:8px 12px; margin:8px 0; background:#F8FAFC; border-radius:8px; }
    .teacher-label { color:#1F2937; font-weight:750; margin-bottom:4px; }
    .footer-note { color:#6B7280; font-size:0.88rem; }
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
            # v3.3.0: Login should immediately load the user's cloud portfolio/watchlist
            # into the decision engine. Do not wait for the user to press
            # 「重新產生今日決策資料」.
            st.session_state.pop("dashboard_payload", None)
            st.session_state.pop("report_md", None)
            st.session_state["force_pipeline_reload"] = True
            st.session_state["active_page"] = "持股總教練"
            st.rerun()
    st.sidebar.caption(f"雲端資料庫狀態：{cloud['status']}")
    if is_cloud_store_configured():
        if st.sidebar.button("測試 Supabase 連線"):
            check = check_cloud_connection()
            if check.ok:
                st.sidebar.success(check.message)
            else:
                st.sidebar.error(check.message)
                if check.detail:
                    st.sidebar.caption(check.detail[:300])
    else:
        st.sidebar.info("未設定 Supabase 時仍可體驗，但重新開瀏覽器後資料不會永久保存。請依 docs/deploy/supabase-beginner-guide.md 完成設定。")


def _payload_is_current(payload: dict | None) -> bool:
    return bool(payload and payload.get("version") == APP_VERSION)


def run_pipeline() -> dict:
    payload = run_teacher_pipeline()
    if st.session_state.get("guest_mode_enabled") or st.session_state.get("cloud_user_email"):
        st.session_state["dashboard_payload"] = payload
        st.session_state["report_md"] = build_markdown(payload)
    else:
        save_outputs(payload)
    return payload


def load_payload() -> dict:
    cached = st.session_state.get("dashboard_payload")
    if cached:
        if _payload_is_current(cached):
            return cached
        st.session_state.pop("dashboard_payload", None)
        st.session_state.pop("report_md", None)
    if st.session_state.pop("force_pipeline_reload", False):
        return run_pipeline()
    # If a user has logged in / guest state is active, always rebuild from that
    # user's portfolio/watchlist. This avoids showing a static payload from an
    # older release or another user.
    if st.session_state.get("cloud_user_email") or st.session_state.get("guest_mode_enabled"):
        return run_pipeline()
    if PAYLOAD_PATH.exists():
        try:
            payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
            if _payload_is_current(payload):
                return payload
        except Exception:
            pass
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


def price_html(price: float, change_pct: float, label: str = "今日股價") -> str:
    symbol = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "—"
    return (
        f"<div class='small-muted'>{label}</div>"
        f"<div class='{price_class(change_pct)}' style='font-size:1.05rem'>"
        f"{price:.2f}（{symbol} {change_pct}%）</div>"
    )


def _macd_chart_series(values: list[float]) -> dict:
    """Return DIF / DEA / histogram series for mini and full charts.

    v3.9.0 fixes a production NameError where the UI called this helper but
    it was missing from app.py. Keep the implementation local to the UI so
    mini MACD charts can render without importing additional modules.
    """
    clean = []
    for value in values:
        try:
            v = float(value)
            if v > 0:
                clean.append(v)
        except Exception:
            continue
    if len(clean) < 35:
        return {"macd": [], "signal": [], "hist": []}
    ema12 = ema_series(clean, 12)
    ema26 = ema_series(clean, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26):], ema26)]
    signal_line = ema_series(macd_line, 9)
    hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    n = min(len(macd_line), len(signal_line), len(hist))
    return {
        "macd": [round(x, 4) for x in macd_line[-n:]],
        "signal": [round(x, 4) for x in signal_line[-n:]],
        "hist": [round(x, 4) for x in hist[-n:]],
    }


def render_data_trust(card: dict) -> None:
    """Only show data warnings inside operating cards.

    Data source is metadata, not a reason to reduce confidence when it is the
    latest valid data. Keep details in the page footer.
    """
    trust = card.get("data_trust") or {}
    warnings = trust.get("warnings", [])
    if warnings:
        with st.expander("資料限制提醒", expanded=False):
            for warning in warnings:
                st.warning(warning)


def _teacher_block(title: str, text: str) -> None:
    if not text:
        return
    st.markdown(
        f"""
<div class='teacher-section'>
  <div class='teacher-label'>{title}</div>
  <div>{text}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_teacher_narrative(card: dict, expanded: bool = True) -> None:
    narrative = card.get("teacher_narrative") or {}
    if not narrative:
        st.write("**老師建議：** " + card.get("action", ""))
        return

    _teacher_block("老師判斷", narrative.get("teacher_judgement", ""))

    # v3.6.1: 今日可買與持股總教練共用同一套老師分析，並預設顯示主要面向。
    _teacher_block("技術面", narrative.get("technical", ""))
    _teacher_block("籌碼 / 法人面", narrative.get("chip", ""))
    _teacher_block("產業 / 消息面", narrative.get("news", ""))
    _teacher_block("支撐 / 壓力", narrative.get("support_resistance", ""))

    with st.expander("A / B / C 劇本與操作細節", expanded=expanded):
        st.markdown("**A 劇本**")
        st.write(narrative.get("scenario_a", ""))
        st.markdown("**B 劇本**")
        st.write(narrative.get("scenario_b", ""))
        st.markdown("**C 劇本**")
        st.write(narrative.get("scenario_c", ""))
        st.markdown("**未持有者策略**")
        st.write(narrative.get("no_position_strategy", ""))
        st.markdown("**已持有者策略**")
        st.write(narrative.get("holding_strategy", ""))
        st.markdown("**風險提醒**")
        st.write(narrative.get("risk", ""))


def render_card(card: dict, show_trust: bool = False) -> None:
    t = card["tech"]
    with st.container(border=True):
        st.subheader(f"{card['label']}｜{card['setup']}｜等級 {card['grade']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Radar", card["score"])
        c2.metric("信心", f"{card['confidence']}%")
        c3.markdown(price_html(t["close"], t["change_pct"], "今日股價"), unsafe_allow_html=True)
        c4.write(f"資料日：{card['latest_date']}")
        render_teacher_narrative(card, expanded=False)
        macd = t["macd"]
        st.caption(f"技術摘要：MACD(DIF) {macd['macd']}｜DEA {macd['signal']}｜柱狀體 {macd['hist']}｜0軸 {macd.get('zero_axis_status')}｜量能比 {t.get('volume_ratio')}")
        gate = card.get("quality_gate") or {}
        if gate.get("failures") or gate.get("warnings"):
            with st.expander("推薦品質檢查", expanded=False):
                for item in gate.get("failures", []):
                    st.warning(item)
                for item in gate.get("warnings", []):
                    st.info(item)
        render_data_trust(card)


def render_strength_card(row: dict) -> None:
    card = row.get("card") or {}
    t = card.get("tech") or {}
    with st.container(border=True):
        st.subheader(f"{row.get('label')}｜{row.get('strength_category')}｜強勢分 {row.get('strength_score')}")
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(price_html(float(row.get("close") or 0), float(row.get("change_pct") or 0), "今日股價"), unsafe_allow_html=True)
        c2.metric("量能比", row.get("volume_ratio"))
        c3.metric("RSI", row.get("rsi"))
        c4.write(f"波段判斷：{row.get('linked_decision')} / {row.get('linked_grade')}")
        st.write(f"**股市老師判斷：** {row.get('teacher_view')}")
        st.write(f"**明日接力觀察：** {row.get('tomorrow_plan')}")
        reasons = row.get("strength_reasons") or []
        if reasons:
            st.markdown("**強勢理由：**")
            for reason in reasons:
                st.markdown(f"- {reason}")
        if card:
            macd = t.get("macd", {})
            st.caption(f"對照技術：DIF {macd.get('macd')}｜DEA {macd.get('signal')}｜0軸 {macd.get('zero_axis_status')}｜突破價 {t.get('breakout')}")


def render_market_ranking(rows: list[dict], title: str) -> None:
    st.markdown(f"**{title}**")
    if not rows:
        st.caption("尚無資料。")
        return
    table = []
    for row in rows[:12]:
        table.append({
            "股票": row.get("label") or f"{row.get('symbol')} {row.get('name')}",
            "股價": row.get("close"),
            "漲跌幅%": row.get("change_pct"),
            "成交量": row.get("volume"),
            "成交值": row.get("value"),
            "來源": row.get("source"),
        })
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_technical_chart(card: dict, key: str) -> None:
    range_label = st.radio("觀察區間", ["1個月", "3個月", "6個月", "1年"], index=1, horizontal=True, key=f"range-{key}")
    days = {"1個月": 30, "3個月": 90, "6個月": 180, "1年": 252}[range_label]

    all_rows = card.get("prices", [])
    if len(all_rows) < 20:
        st.warning("價格資料不足，無法繪製完整技術圖。")
        return

    # 用完整價格序列計算 MACD，再只截取使用者選擇的觀察區間顯示。
    # 這可避免切到 1 個月時，因樣本不足而讓 MACD/DIF 消失。
    full_df = pd.DataFrame(all_rows).copy()
    full_df["date"] = pd.to_datetime(full_df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        full_df[col] = pd.to_numeric(full_df[col], errors="coerce")
    full_df = full_df.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    if len(full_df) < 20:
        st.warning("價格日期或價格欄位異常，無法繪製完整技術圖。")
        return
    df = full_df.tail(days).copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    closes_full = [float(x) for x in full_df["close"].tolist()]
    macd_series = _macd_chart_series(closes_full)

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
        display_n = min(len(df), len(macd_series["macd"]), len(macd_series["signal"]), len(macd_series["hist"]))
        x = df["date"].tolist()[-display_n:]
        macd_y = macd_series["macd"][-display_n:]
        dea_y = macd_series["signal"][-display_n:]
        hist_y = macd_series["hist"][-display_n:]
        hist_colors = [up if h >= 0 else down for h in hist_y]
        fig.add_trace(go.Bar(x=x, y=hist_y, marker_color=hist_colors, name="Hist"), row=3, col=1)
        fig.add_trace(go.Scatter(x=x, y=macd_y, mode="lines", name="MACD/DIF"), row=3, col=1)
        fig.add_trace(go.Scatter(x=x, y=dea_y, mode="lines", name="DEA"), row=3, col=1)
        fig.add_hline(y=0, line_width=1, line_dash="dash", row=3, col=1)
    else:
        fig.add_trace(go.Scatter(x=[df["date"].iloc[-1]], y=[0], mode="text", text=["MACD 樣本不足"], showlegend=False), row=3, col=1)

    tech = card["tech"]
    summary = f"RSI {tech.get('rsi')}｜KD {tech.get('kd', {}).get('k')}/{tech.get('kd', {}).get('d')}｜BIAS20 {tech.get('bias20')}%｜量能比 {tech.get('volume_ratio')}"
    fig.add_trace(go.Scatter(x=[df["date"].iloc[-1]], y=[0], mode="text", text=[summary], textposition="middle center", showlegend=False), row=4, col=1)
    fig.update_layout(height=820, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20))
    macd_status = card.get("tech", {}).get("macd", {}).get("zero_axis_status", "")
    st.caption(f"MACD 0軸狀態：{macd_status}｜本圖使用完整歷史資料先計算 DIF/DEA，再依觀察區間顯示。")
    st.plotly_chart(fig, use_container_width=True, key=f"chart-{key}-{range_label}")


def render_mini_macd_chart(card: dict, key: str) -> None:
    rows = card.get("prices", [])
    if len(rows) < 35:
        st.caption("MACD 樣本不足，暫不繪製。")
        return
    df = pd.DataFrame(rows).copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date")
    if len(df) < 35:
        st.caption("MACD 樣本不足，暫不繪製。")
        return
    macd_series = _macd_chart_series([float(x) for x in df["close"].tolist()])
    display_n = min(70, len(macd_series.get("macd", [])), len(df))
    if display_n < 10:
        st.caption("MACD 樣本不足，暫不繪製。")
        return
    x = df["date"].dt.strftime("%Y-%m-%d").tolist()[-display_n:]
    macd_y = macd_series["macd"][-display_n:]
    dea_y = macd_series["signal"][-display_n:]
    hist_y = macd_series["hist"][-display_n:]
    up = "#DC2626"
    down = "#16A34A"
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=hist_y, marker_color=[up if h >= 0 else down for h in hist_y], name="Hist"))
    fig.add_trace(go.Scatter(x=x, y=macd_y, mode="lines", name="MACD/DIF"))
    fig.add_trace(go.Scatter(x=x, y=dea_y, mode="lines", name="DEA"))
    fig.add_hline(y=0, line_width=1, line_dash="dash")
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=20), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True, key=f"mini-macd-{key}")


def add_watchlist_ui() -> None:
    st.subheader("新增指定觀察個股")
    st.caption("輸入資料時不會重新抓股價；只有按下『加入觀察清單』後才會解析股票並更新分析。")
    with st.form("watchlist_add_form", clear_on_submit=True):
        text = st.text_input("輸入股號或名稱", placeholder="例如：2313、華通；清單外可輸入股號或『股號 股票名稱』")
        submitted = st.form_submit_button("加入觀察清單")
    if submitted:
        try:
            stock = resolve_stock(text)
            with st.spinner(f"正在抓取 {stock.symbol} {stock.name} 最新資料..."):
                card = build_decision_card(stock)
            items = load_watchlist()
            if not any(i.get("symbol") == card["symbol"] for i in items):
                items.append({"symbol": card["symbol"], "name": card["name"]})
                ok = save_watchlist(items)
            else:
                ok = True
            status = last_save_status()
            if ok:
                st.success(f"已加入 {card['label']}｜{status.get('detail', '')}")
                st.session_state.pop("dashboard_payload", None)
                st.session_state.pop("report_md", None)
                st.session_state["force_pipeline_reload"] = True
                st.rerun()
            else:
                st.error(f"已暫存在本次瀏覽，但雲端保存失敗：{status.get('detail', '')}")
        except Exception as exc:
            st.error(str(exc))


def add_portfolio_ui() -> None:
    st.subheader("新增個人持股")
    st.caption("請先輸入股號 / 股數 / 成本；系統不會在輸入途中抓資料，只有按下『加入 / 更新持股』後才會抓取最新股價並更新持股總教練。")
    with st.form("portfolio_add_form", clear_on_submit=True):
        text = st.text_input("股號或名稱", placeholder="例如：3037、欣興；清單外可輸入股號或『股號 股票名稱』")
        col1, col2 = st.columns(2)
        shares = col1.number_input("股數", min_value=0.0, step=100.0, value=0.0)
        cost = col2.number_input("成本", min_value=0.0, step=1.0, value=0.0)
        submitted = st.form_submit_button("加入 / 更新持股")
    if submitted:
        try:
            stock = resolve_stock(text)
            with st.spinner(f"正在抓取 {stock.symbol} {stock.name} 最新資料..."):
                card = build_decision_card(stock)
            items = [i for i in load_portfolio() if i.get("symbol") != card["symbol"]]
            items.append({"symbol": card["symbol"], "name": card["name"], "shares": shares, "cost": cost})
            ok = save_portfolio(items)
            status = last_save_status()
            if ok:
                st.success(f"已儲存 {card['label']}｜{status.get('detail', '')}")
                st.session_state.pop("dashboard_payload", None)
                st.session_state.pop("report_md", None)
                st.session_state["force_pipeline_reload"] = True
                st.rerun()
            else:
                st.error(f"已暫存在本次瀏覽，但雲端保存失敗：{status.get('detail', '')}")
        except Exception as exc:
            st.error(str(exc))

ensure_user_mode_defaults()
render_beta_access()

st.title(f"🚀 AI Stock Radar {APP_VERSION}｜AI 股市老師")
st.caption("本版重點：Decision Quality Gate：推薦前先檢查價格可執行性、資料有效性與老師語句邏輯；今日可買與持股總教練共用老師敘事。")

if st.button("重新產生今日決策資料"):
    with st.spinner("股市老師重新抓取與分析中..."):
        payload = run_pipeline()
    st.success("已完成更新")
else:
    payload = load_payload()

status = payload["trading_status"]
st.caption(f"日期：{status['date']}｜台灣時間 {status.get('time', '--:--')}｜星期{status['weekday']}｜交易狀態：{status['session']}｜版本：{APP_VERSION}")
source_summary = payload.get("data_source_summary", {})
store = storage_status()

mcol, k2, k3, k4, k5 = st.columns([2.2, 1, 1, 1, 1])
with mcol:
    st.markdown(
        f"<div class='market-card'><div class='market-title'>市場結論</div><div class='market-view'>{payload['market_view']}</div></div>",
        unsafe_allow_html=True,
    )
k2.metric("今日可買", len(payload["buy_list"]))
k3.metric("今日強勢", len(payload.get("strong_momentum", {}).get("strong_list", [])))
k4.metric("等待突破", len(payload["wait_list"]))
k5.metric("避免名單", len(payload["avoid_list"]))

PAGES = ["今日可買", "強勢股雷達", "等待/避免", "每日報告", "持股總教練", "觀察清單", "MACD觀察", "個股線圖", "Supabase設定"]
st.session_state.setdefault("active_page", "今日可買")
page = st.radio("功能", PAGES, horizontal=True, key="active_page")
st.divider()

if page == "今日可買":
    st.header("今日可買進名單")
    if not payload["buy_list"]:
        st.warning("今日沒有 A 級可買進名單。資料不足或買點不佳時，股市老師不硬給買進。")
    for card in payload["buy_list"][:8]:
        render_card(card)

elif page == "強勢股雷達":
    st.header("今日強勢股雷達")
    st.caption("先掃全市場漲幅、成交量、成交值與接近漲停，再由 AI 判斷：哪些可追、哪些已漲不追、哪些適合明日接力。")
    strength = payload.get("strong_momentum", {})
    gap = payload.get("strength_gap_analysis", {})
    coverage = strength.get("data_coverage", {})
    if coverage.get("total_market_rows", 0):
        st.success(
            f"市場掃描：{coverage.get('total_market_rows')} 檔｜"
            f"官方解析：{coverage.get('official_rows', 0)} 檔｜"
            f"Yahoo 補充：{coverage.get('yahoo_rows', 0)} 檔｜"
            f"候選分析：{coverage.get('classified_rows', coverage.get('candidate_rows', 0))} 檔｜"
            f"來源：{', '.join(coverage.get('sources', []))}"
        )
        if coverage.get("mode") == "official_plus_yahoo_fallback":
            st.info("官方全市場快照不足，本版已補用官方股票主檔 + Yahoo Quote 擴大掃描；不會把此狀態隱藏成純官方全市場資料。")
    else:
        st.warning(coverage.get("message", "目前未取得全市場強勢資料。"))
    st.info(gap.get("summary", "今日強勢股雷達尚未產生落差分析。"))

    with st.expander("資料抓取診斷（若強勢股為空，先看這裡）", expanded=not bool(coverage.get("total_market_rows", 0))):
        attempts = coverage.get("endpoint_attempts", [])
        if attempts:
            diag_rows = []
            for a in attempts:
                diag_rows.append({
                    "來源": a.get("source"),
                    "狀態": a.get("status"),
                    "原始筆數": a.get("raw_rows", 0),
                    "解析筆數": a.get("parsed_rows", 0),
                    "錯誤 / 註記": a.get("error", ""),
                    "樣本欄位": ", ".join(a.get("sample_keys", [])[:8]),
                })
            st.dataframe(diag_rows, use_container_width=True, hide_index=True)
        else:
            st.caption("沒有資料抓取診斷。")

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(["可追強勢", "今日強勢", "漲停/接近漲停", "已漲不追", "明日接力", "全市場排行"])
    with tab0:
        rows = strength.get("chaseable_list", [])
        if not rows:
            st.warning("目前沒有符合『強勢且仍有合理操作空間』的可追名單；股市老師不把所有大漲股都列為可追。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab1:
        rows = strength.get("strong_list", [])
        if not rows:
            st.warning("目前沒有明確今日強勢名單。")
        for row in rows[:12]:
            render_strength_card(row)
    with tab2:
        rows = strength.get("limit_watch", [])
        if not rows:
            st.info("目前沒有接近漲停的觀察名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab3:
        rows = strength.get("no_chase_list", [])
        if not rows:
            st.info("目前沒有明顯已漲不追名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab4:
        rows = strength.get("tomorrow_watch", [])
        if not rows:
            st.info("目前沒有明確明日接力觀察名單。")
        for row in rows[:12]:
            render_strength_card(row)
    with tab5:
        rankings = strength.get("ranking_tables", {})
        render_market_ranking(rankings.get("top_gainers", []), "全市場漲幅排行")
        render_market_ranking(rankings.get("top_volume", []), "全市場成交量排行")
        render_market_ranking(rankings.get("top_value", []), "全市場成交值排行")
        sectors = strength.get("sector_strength", [])
        if sectors:
            st.markdown("**族群強度**")
            st.dataframe(sectors, use_container_width=True, hide_index=True)

elif page == "等待/避免":
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("等待突破 / 拉回")
        for card in payload["wait_list"][:8]:
            render_card(card)
    with c2:
        st.subheader("今日避免")
        for card in payload["avoid_list"][:8]:
            render_card(card)

elif page == "持股總教練":
    st.header("個人持股分析｜股市老師總教練")
    add_portfolio_ui()
    coach = payload["portfolio_coach"]
    st.write(coach["summary"])
    if coach["rows"]:
        st.metric("總損益", f"{coach['total_pnl']:.0f}", f"{coach['total_pnl_pct']}%")
        for row in coach["rows"]:
            with st.container(border=True):
                st.subheader(row["stock"])
                card = row["card"]
                tech = card["tech"]
                css = price_class(tech.get("change_pct", 0))
                st.markdown(price_html(tech["close"], tech["change_pct"], "今日股價"), unsafe_allow_html=True)
                st.write(f"股數：{row['shares']}｜成本：{row['cost']}｜市值：{row['value']}｜損益：{row['pnl']}（{row['pnl_pct']}%）｜Radar：{card.get('score')}｜等級：{card.get('grade')}")
                render_teacher_narrative(card, expanded=False)
                render_data_trust(row["card"])
    else:
        st.info("尚未輸入持股。")

elif page == "觀察清單":
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

elif page == "MACD觀察":
    st.header("MACD 0軸觀察名單")
    st.caption("本頁已整合原本 MACD 與 0軸MACD；只關注 MACD/DIF 從 0 軸下方即將翻正，或剛站上 0 軸的股票。若資料不新、fallback 或樣本不足，不列入推薦。")
    zero_items = payload.get("macd_zero_axis_list", [])[:10]
    if not zero_items:
        st.info("目前沒有符合『即將或剛從 0 軸轉強』且資料可信的名單；沒有訊號時不硬湊推薦。")
    for card in zero_items:
        t = card["tech"]
        css = price_class(t.get("change_pct", 0))
        with st.container(border=True):
            st.subheader(f"{card['label']}｜{t['macd'].get('zero_axis_status')}")
            st.markdown(price_html(t["close"], t["change_pct"], "今日股價"), unsafe_allow_html=True)
            render_mini_macd_chart(card, key=card["symbol"])
            st.write(f"MACD(DIF)：{t['macd']['macd']}｜DEA：{t['macd']['signal']}｜柱狀體：{t['macd']['hist']}｜RSI：{t['rsi']}")
            st.write(f"**老師判斷：** {card.get('teacher_narrative', {}).get('teacher_judgement', card['action'])}")

elif page == "個股線圖":
    st.header("個股技術線圖")
    dynamic_cards = payload["all_cards"][:30] + payload.get("watchlist_analysis", []) + [row.get("card") for row in payload.get("portfolio_coach", {}).get("rows", []) if row.get("card")]
    choices = {card["label"]: card for card in dynamic_cards}
    selected = st.selectbox("選擇個股", list(choices.keys()))
    render_technical_chart(choices[selected], key=choices[selected]["symbol"])

elif page == "Supabase設定":
    st.header("Supabase 設定助手")
    cloud_info = cloud_status()
    st.write(f"目前狀態：**{cloud_info.get('status')}**")
    st.write(f"資料表：`{cloud_info.get('table')}`")
    if cloud_info.get('url'):
        st.write(f"Project URL：`{cloud_info.get('url')}`")
    if cloud_info.get('key_preview'):
        st.write(f"Key：`{cloud_info.get('key_preview')}`")

    if st.button("測試 Supabase 連線與權限", key="supabase_connection_test"):
        check = check_cloud_connection()
        if check.ok:
            st.success(check.message)
        else:
            st.error(check.message)
            if check.detail:
                st.code(check.detail)

    err = last_cloud_error()
    if err:
        st.warning(f"最近一次雲端保存錯誤：{err}")
        detail = last_cloud_response()
        if detail:
            st.code(detail)

    if is_cloud_store_configured():
        st.success("Supabase 已設定。朋友使用 Email + 自訂存取碼後，持股與觀察清單會保存到雲端。")
    else:
        st.warning("Supabase 尚未設定，所以朋友資料目前只會暫存在本次瀏覽。")
        st.markdown("""
<div class='setup-box'>
<b>你需要完成三件事：</b><br>
1. 在 Supabase 建立 <code>user_profiles</code> 資料表。<br>
2. 複製 Supabase Project URL 與 Secret / service_role key。<br>
3. 到 Streamlit Cloud → Manage app → Settings → Secrets 貼上設定。<br><br>
完整步驟請看 repo 內：<code>docs/deploy/supabase-beginner-guide.md</code>
</div>
""", unsafe_allow_html=True)
        st.code("""[supabase]
url = "https://你的專案.supabase.co"
service_role_key = "你的 Supabase Secret 或 service_role key"
table = "user_profiles""" , language="toml")

elif page == "每日報告":
    st.markdown(current_report(payload))


st.divider()
with st.expander("資料來源與更新說明", expanded=False):
    st.caption(payload.get("teacher_summary", ""))
    st.write(f"資料基準：預期 {source_summary.get('expected_latest_date', '未知')}｜實際 {source_summary.get('price_date_min', '未知')}～{source_summary.get('price_date_max', '未知')}｜狀態：{source_summary.get('truth_status', '未知')}")
    st.write(f"資料來源：官方採用 {source_summary.get('official_confirmed', 0)} 檔｜Yahoo 採用 {source_summary.get('yahoo_selected', source_summary.get('yahoo_only', 0) + source_summary.get('yahoo_newer_than_official', 0))} 檔｜Fallback {source_summary.get('fallback', 0)} 檔")
    st.write(f"使用者資料：{store['label']}｜{store['detail']}")
