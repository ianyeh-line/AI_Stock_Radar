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
from radar.version import APP_VERSION, APP_RELEASE_NAME


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
    .decision-hero { border:1px solid #DBEAFE; border-radius:18px; padding:18px 20px; background:linear-gradient(135deg,#EFF6FF,#FFFFFF); margin-bottom:12px; }
    .decision-hero h3 { margin:0 0 6px 0; }
    .quick-card { border:1px solid #E5E7EB; border-radius:14px; padding:14px 16px; background:#FFFFFF; margin-bottom:10px; }
    .next-step { border-left:4px solid #F59E0B; padding:8px 12px; background:#FFFBEB; border-radius:8px; margin-top:8px; }
    .chip-badge { display:inline-block; padding:4px 8px; border-radius:999px; background:#F3F4F6; font-size:0.82rem; color:#374151; margin-right:6px; }
    @media (max-width: 768px) {
        .block-container { padding:0.75rem 0.75rem 2rem 0.75rem; }
        .market-card { min-height:auto; padding:12px; }
        .market-view { font-size:1.1rem; }
        .teacher-section { padding:8px 10px; }
        .quick-card { padding:12px; }
        div[data-testid="stHorizontalBlock"] { gap:0.5rem; }
    }
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


def _report_matches_current_version(text: str) -> bool:
    return f"AI Stock Radar {APP_VERSION}" in text


def current_report(payload: dict) -> str:
    """Return a report generated by the current app version only.

    Older runtime files were the source of version mismatches, for example the
    shell showing v3.11.1 while the report body still showed v3.9.0. If the
    cached/session/file report is not from the current version, rebuild from
    the current payload instead of displaying stale content.
    """
    session_report = st.session_state.get("report_md")
    if session_report and _report_matches_current_version(session_report):
        return session_report
    if session_report:
        st.session_state.pop("report_md", None)

    if REPORT_PATH.exists():
        text = REPORT_PATH.read_text(encoding="utf-8")
        if _report_matches_current_version(text):
            return text

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

    v3.11.2 keeps the production fix where the UI called this helper but
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


def render_card(card: dict, show_trust: bool = False, compact: bool = False) -> None:
    t = card["tech"]
    with st.container(border=True):
        st.subheader(f"{card['label']}｜{card['setup']}｜等級 {card['grade']}")
        c1, c2, c3 = st.columns([0.9, 0.9, 1.4])
        c1.metric("Radar", card["score"])
        c2.metric("信心", f"{card['confidence']}%")
        c3.markdown(price_html(t["close"], t["change_pct"], "今日股價"), unsafe_allow_html=True)
        chip = card.get("chip_flow") or {}
        if chip.get("available"):
            st.markdown(f"<span class='chip-badge'>籌碼：{chip.get('bias')}｜合計 {chip.get('total_net_lot', 0):,} 張</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='chip-badge'>法人籌碼：未取得</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='next-step'><b>下一步：</b>{card.get('action','')}</div>", unsafe_allow_html=True)
        render_teacher_narrative(card, expanded=False if compact else True)
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


def render_decision_loop(loop: dict) -> None:
    session = loop.get("session_mode") or {}
    st.header("決策閉環｜盤前計畫 → 盤中觀察 → 盤後檢討 → 明日準備")
    st.info(f"目前模式：{session.get('mode', '未判斷')}｜{session.get('headline', '')}")
    st.caption(session.get("primary_question", ""))

    p1, p2 = st.columns(2)
    with p1:
        st.subheader("今日作戰計畫")
        plan = loop.get("pre_market_plan") or []
        if not plan:
            st.warning("目前沒有通過品質閘門的 A 級作戰標的；先以等待突破、強勢接力與持股管理為主。")
        for row in plan[:5]:
            with st.container(border=True):
                st.markdown(f"**{row.get('label')}｜{row.get('type')}**")
                st.write(row.get("teacher_view", ""))
                st.write(row.get("action", ""))
                st.caption(row.get("watch_price", ""))
    with p2:
        st.subheader("前次推薦檢討")
        review = loop.get("recommendation_review") or {}
        st.write(review.get("summary", "尚無檢討資料。"))
        rows = review.get("rows") or []
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("AI 沒選到強勢股的原因")
    missed = (loop.get("strength_loop") or {}).get("missed_strength") or []
    if not missed:
        st.caption("目前沒有明確『強勢但未列入可買』的落差，或強勢資料尚不足。")
    else:
        for row in missed[:8]:
            with st.container(border=True):
                st.markdown(f"**{row.get('label')}｜漲跌 {row.get('change_pct')}%｜量能比 {row.get('volume_ratio', '--')}**")
                st.write(row.get("reason", ""))
                st.caption("下一步：" + str(row.get("next_step", "")))

    st.subheader("持股策略是否改變")
    updates = loop.get("portfolio_strategy_updates") or []
    if not updates:
        st.caption("尚未建立個人持股，暫無策略變更檢討。")
    else:
        for row in updates:
            with st.container(border=True):
                st.markdown(f"**{row.get('stock')}｜{row.get('status')}｜今日股價 {row.get('today_price')}｜損益 {row.get('pnl_pct')}%**")
                st.write(row.get("action", ""))
                st.caption(row.get("risk_line", ""))

    st.subheader("明日準備")
    tomorrow = loop.get("tomorrow_preparation") or {}
    st.write(tomorrow.get("summary", ""))
    for row in (tomorrow.get("rows") or [])[:10]:
        st.markdown(f"- **{row.get('label')}**｜{row.get('source')}｜{row.get('plan')}")


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


def _safe_text(value: object, default: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else default


def _pill(text: str, tone: str = "neutral") -> str:
    tone_class = {
        "good": "pill-good",
        "warn": "pill-warn",
        "bad": "pill-bad",
        "info": "pill-info",
    }.get(tone, "pill-neutral")
    return f"<span class='ux-pill {tone_class}'>{text}</span>"


def _decision_tone(card: dict) -> str:
    grade = str(card.get("grade", ""))
    setup = str(card.get("setup", ""))
    if grade == "A" or "買" in setup:
        return "good"
    if "避" in setup or "減" in setup:
        return "bad"
    if "等" in setup or "觀察" in setup:
        return "warn"
    return "info"


def _format_key_prices(card: dict) -> str:
    tech = card.get("tech", {})
    support = tech.get("pullback_low") or tech.get("support") or tech.get("ma20")
    support_high = tech.get("pullback_high") or tech.get("ma60") or support
    invalid = tech.get("invalid") or tech.get("stop_loss") or tech.get("risk_line")
    breakout = tech.get("breakout")
    parts = []
    try:
        if support and support_high:
            parts.append(f"觀察區 {float(support):.2f}～{float(support_high):.2f}")
    except Exception:
        pass
    try:
        if breakout:
            parts.append(f"突破 {float(breakout):.2f}")
    except Exception:
        pass
    try:
        if invalid:
            parts.append(f"失效 {float(invalid):.2f}")
    except Exception:
        pass
    return "｜".join(parts) if parts else "關鍵價位待補足"


def _compact_next_step(card: dict) -> str:
    action = str(card.get("action") or "").strip()
    if action:
        return action
    tech = card.get("tech", {})
    try:
        close = float(tech.get("close") or 0)
        low = float(tech.get("pullback_low") or tech.get("support") or 0)
        high = float(tech.get("pullback_high") or low)
        breakout = float(tech.get("breakout") or 0)
        invalid = float(tech.get("invalid") or tech.get("stop_loss") or 0)
        if low <= close <= high:
            return f"股價在 {low:.2f}～{high:.2f} 觀察區內，可依量能分批；跌破 {invalid:.2f} 停止加碼。"
        if close > high and breakout and close < breakout:
            return f"現價已高於拉回區，不追價；等回測 {high:.2f} 附近守穩，或放量站上 {breakout:.2f} 再評估。"
        if breakout and close >= breakout:
            return f"已站上 {breakout:.2f}，持股可續抱；未持有者等回測不破再找買點。"
    except Exception:
        pass
    return "先觀察價格是否回到可執行區，再決定是否動作。"


def _render_summary_card(card: dict, *, key: str, detail_open: bool = False, show_chart: bool = False) -> None:
    tech = card.get("tech", {})
    tone = _decision_tone(card)
    label = _safe_text(card.get("label"))
    setup = _safe_text(card.get("setup"))
    grade = _safe_text(card.get("grade"))
    score = _safe_text(card.get("score"))
    confidence = _safe_text(card.get("confidence"))
    price = float(tech.get("close") or 0)
    change = float(tech.get("change_pct") or 0)
    title = f"{label}｜{setup}｜等級 {grade}"
    with st.container(border=True):
        st.markdown(
            f"""
<div class='ux-card-head'>
  <div>
    <div class='ux-card-title'>{title}</div>
    <div class='ux-card-sub'>{_format_key_prices(card)}</div>
  </div>
  <div>{_pill('Radar ' + str(score), tone)} {_pill('信心 ' + str(confidence) + '%', 'info')}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([0.9, 2.1])
        with c1:
            st.markdown(price_html(price, change, "今日股價"), unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='ux-next'><b>下一步</b><br>{_compact_next_step(card)}</div>", unsafe_allow_html=True)

        with st.expander("展開股市老師完整分析", expanded=detail_open):
            render_teacher_narrative(card, expanded=False)
            gate = card.get("quality_gate") or {}
            if gate.get("failures") or gate.get("warnings"):
                with st.expander("推薦品質檢查", expanded=False):
                    for item in gate.get("failures", []):
                        st.warning(item)
                    for item in gate.get("warnings", []):
                        st.info(item)
            render_data_trust(card)
        if show_chart:
            with st.expander("技術圖", expanded=False):
                render_technical_chart(card, key=key)


def _render_list(cards: list[dict], empty: str, limit: int = 5, prefix: str = "card") -> None:
    if not cards:
        st.info(empty)
        return
    for i, card in enumerate(cards[:limit], start=1):
        _render_summary_card(card, key=f"{prefix}-{card.get('symbol', i)}", detail_open=False)


def _render_mobile_intro(payload: dict) -> None:
    status = payload.get("trading_status", {})
    st.markdown(
        f"""
<div class='ux-hero'>
  <div class='ux-eyebrow'>AI 股市老師｜{status.get('session', '交易狀態')}｜{status.get('date', '')} {status.get('time', '')}</div>
  <div class='ux-hero-title'>{payload.get('market_view', '今日策略待產生')}</div>
  <div class='ux-hero-text'>先看今天怎麼做，再展開個股細節。資料來源、診斷與版本資訊已移至頁尾。</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_kpis(payload: dict) -> None:
    strength = payload.get("strong_momentum", {})
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='ux-kpi'><span>今日可操作</span><b>{len(payload.get('buy_list', []))}</b></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='ux-kpi'><span>強勢觀察</span><b>{len(strength.get('strong_list', []))}</b></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='ux-kpi'><span>等待條件</span><b>{len(payload.get('wait_list', []))}</b></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='ux-kpi'><span>避開/控風險</span><b>{len(payload.get('avoid_list', []))}</b></div>", unsafe_allow_html=True)


def _render_clean_daily_report(payload: dict) -> None:
    st.header("每日報告")
    st.caption("摘要優先；完整個股分析預設收合。")
    st.subheader("股市老師今日結論")
    st.markdown(f"<div class='ux-callout'>{payload.get('market_view', '今日策略待產生')}</div>", unsafe_allow_html=True)

    st.subheader("今日可買進摘要")
    buy_list = payload.get("buy_list", [])
    if not buy_list:
        st.info("今日沒有通過品質閘門的 A 級可買名單。")
    for i, card in enumerate(buy_list[:6], start=1):
        with st.expander(f"{i}. {card.get('label')}｜{card.get('setup')}｜Radar {card.get('score')}｜等級 {card.get('grade')}", expanded=False):
            _render_summary_card(card, key=f"report-buy-{card.get('symbol', i)}", detail_open=True)

    st.subheader("等待 / 避免摘要")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**等待條件**")
        for card in payload.get("wait_list", [])[:5]:
            st.markdown(f"- **{card.get('label')}**｜{card.get('setup')}｜{_format_key_prices(card)}")
    with c2:
        st.markdown("**避免 / 控風險**")
        for card in payload.get("avoid_list", [])[:5]:
            st.markdown(f"- **{card.get('label')}**｜{card.get('setup')}｜{_compact_next_step(card)}")

    with st.expander("完整 Markdown 報告", expanded=False):
        st.markdown(current_report(payload))


def _render_footer(payload: dict) -> None:
    source_summary = payload.get("data_source_summary", {})
    store = storage_status()
    with st.expander("資料來源、更新狀態與系統資訊", expanded=False):
        st.write(f"資料基準：預期 {source_summary.get('expected_latest_date', '未知')}｜實際 {source_summary.get('price_date_min', '未知')}～{source_summary.get('price_date_max', '未知')}｜狀態：{source_summary.get('truth_status', '未知')}")
        st.write(f"資料來源：官方採用 {source_summary.get('official_confirmed', 0)} 檔｜Yahoo 採用 {source_summary.get('yahoo_selected', source_summary.get('yahoo_only', 0) + source_summary.get('yahoo_newer_than_official', 0))} 檔｜Fallback {source_summary.get('fallback', 0)} 檔")
        st.write(f"使用者資料：{store['label']}｜{store['detail']}")
        st.write(f"版本：{APP_VERSION}｜{APP_RELEASE_NAME}")


st.markdown(
    """
<style>
    .main .block-container { max-width: 1120px; padding-top: 1.25rem; padding-bottom: 3rem; }
    h1, h2, h3 { letter-spacing:-0.02em; }
    .ux-topbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:0.6rem; }
    .ux-brand { font-size:2.1rem; font-weight:850; color:#0F172A; line-height:1.15; }
    .ux-version { color:#64748B; font-weight:650; }
    .ux-hero { border:1px solid #DBEAFE; border-radius:24px; padding:24px; background:linear-gradient(135deg,#EFF6FF 0%,#FFFFFF 72%); box-shadow:0 12px 36px rgba(15,23,42,0.06); margin:0.7rem 0 1rem 0; }
    .ux-eyebrow { color:#2563EB; font-size:0.9rem; font-weight:800; margin-bottom:8px; }
    .ux-hero-title { font-size:1.8rem; line-height:1.35; font-weight:900; color:#0F172A; }
    .ux-hero-text { color:#64748B; margin-top:8px; line-height:1.55; }
    .ux-kpi { border:1px solid #E5E7EB; border-radius:18px; padding:16px; background:#FFFFFF; box-shadow:0 6px 22px rgba(15,23,42,0.05); }
    .ux-kpi span { display:block; color:#64748B; font-size:0.9rem; margin-bottom:8px; }
    .ux-kpi b { font-size:2rem; color:#0F172A; }
    .ux-card-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:12px; }
    .ux-card-title { font-size:1.35rem; font-weight:850; color:#0F172A; line-height:1.35; }
    .ux-card-sub { color:#64748B; margin-top:4px; }
    .ux-pill { display:inline-block; padding:5px 10px; border-radius:999px; font-weight:800; font-size:0.82rem; margin:2px; white-space:nowrap; }
    .pill-good { background:#DCFCE7; color:#166534; }
    .pill-warn { background:#FEF3C7; color:#92400E; }
    .pill-bad { background:#FEE2E2; color:#991B1B; }
    .pill-info { background:#DBEAFE; color:#1D4ED8; }
    .pill-neutral { background:#F1F5F9; color:#334155; }
    .ux-next { border-left:4px solid #F59E0B; background:#FFFBEB; padding:10px 12px; border-radius:12px; line-height:1.55; }
    .ux-callout { border:1px solid #E2E8F0; background:#F8FAFC; border-radius:18px; padding:18px; font-size:1.15rem; font-weight:750; line-height:1.6; }
    .teacher-section { border-left:4px solid #2563EB; padding:10px 12px; margin:8px 0; background:#F8FAFC; border-radius:10px; }
    .teacher-label { color:#0F172A; font-weight:850; margin-bottom:4px; }
    div[data-testid="stExpander"] { border-radius:16px; }
    section[data-testid="stSidebar"] { background:#F8FAFC; }
    @media (max-width: 768px) {
        .main .block-container { padding:0.8rem 0.8rem 2.5rem 0.8rem; }
        .ux-brand { font-size:1.55rem; }
        .ux-hero { padding:18px; border-radius:20px; }
        .ux-hero-title { font-size:1.35rem; }
        .ux-card-head { display:block; }
        .ux-card-title { font-size:1.15rem; }
        .ux-kpi { padding:12px; margin-bottom:8px; }
        .ux-kpi b { font-size:1.55rem; }
        div[data-testid="stHorizontalBlock"] { gap:0.5rem; }
    }
</style>
""",
    unsafe_allow_html=True,
)

ensure_user_mode_defaults()
render_beta_access()

st.markdown(
    f"""
<div class='ux-topbar'>
  <div>
    <div class='ux-brand'>🚀 AI Stock Radar</div>
    <div class='ux-version'>v{APP_VERSION}｜AI 股市老師｜{APP_RELEASE_NAME}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if st.button("重新產生今日決策資料", use_container_width=False):
    with st.spinner("股市老師重新抓取與分析中..."):
        payload = run_pipeline()
    st.success("已完成更新")
else:
    payload = load_payload()

_render_mobile_intro(payload)
_render_kpis(payload)

PAGES = ["今天怎麼做", "今日強勢", "我的持股", "個股研究", "每日報告", "設定"]
st.session_state.setdefault("active_page", "今天怎麼做")
page = st.radio("功能", PAGES, horizontal=True, key="active_page", label_visibility="collapsed")
st.divider()

if page == "今天怎麼做":
    st.header("今天怎麼做")
    st.markdown(f"<div class='ux-callout'>{payload.get('teacher_summary') or payload.get('market_view')}</div>", unsafe_allow_html=True)
    st.subheader("今日可操作")
    _render_list(payload.get("buy_list", []), "今日沒有通過品質閘門的 A 級買進名單；先看等待條件與持股策略。", limit=4, prefix="home-buy")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("等待條件")
        _render_list(payload.get("wait_list", []), "目前沒有等待突破 / 拉回觀察名單。", limit=3, prefix="home-wait")
    with col_b:
        st.subheader("今天不要追")
        no_chase = payload.get("strong_momentum", {}).get("no_chase_list", [])[:4]
        if not no_chase:
            st.info("目前沒有明確已漲不追名單。")
        for row in no_chase:
            with st.container(border=True):
                st.markdown(f"**{row.get('label')}｜{row.get('strength_category')}**")
                st.write(row.get("teacher_view", ""))
                st.caption("下一步：" + str(row.get("tomorrow_plan", "")))

elif page == "今日強勢":
    st.header("今日強勢")
    st.caption("分清楚：可追強勢、強但不追、明日接力。")
    strength = payload.get("strong_momentum", {})
    tab0, tab1, tab2, tab3 = st.tabs(["可追", "強勢", "已漲不追", "明日接力"])
    with tab0:
        rows = strength.get("chaseable_list", [])
        if not rows:
            st.warning("目前沒有符合『強勢且仍有合理操作空間』的可追名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab1:
        rows = strength.get("strong_list", [])
        if not rows:
            st.warning("目前沒有明確今日強勢名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab2:
        rows = strength.get("no_chase_list", [])
        if not rows:
            st.info("目前沒有明顯已漲不追名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with tab3:
        rows = strength.get("tomorrow_watch", [])
        if not rows:
            st.info("目前沒有明確明日接力觀察名單。")
        for row in rows[:10]:
            render_strength_card(row)
    with st.expander("資料抓取診斷與全市場排行", expanded=False):
        rankings = strength.get("ranking_tables", {})
        render_market_ranking(rankings.get("top_gainers", []), "全市場漲幅排行")
        render_market_ranking(rankings.get("top_volume", []), "全市場成交量排行")
        render_market_ranking(rankings.get("top_value", []), "全市場成交值排行")
        coverage = strength.get("data_coverage", {})
        st.write(coverage)

elif page == "我的持股":
    st.header("我的持股")
    add_portfolio_ui()
    coach = payload.get("portfolio_coach", {})
    st.markdown(f"<div class='ux-callout'>{coach.get('summary', '尚未建立持股。')}</div>", unsafe_allow_html=True)
    if coach.get("rows"):
        c1, c2 = st.columns(2)
        c1.metric("總損益", f"{coach.get('total_pnl', 0):.0f}", f"{coach.get('total_pnl_pct', 0)}%")
        c2.metric("持股檔數", len(coach.get("rows", [])))
        for row in coach["rows"]:
            with st.container(border=True):
                st.subheader(row.get("stock"))
                card = row.get("card")
                if card:
                    tech = card.get("tech", {})
                    st.markdown(price_html(float(tech.get("close") or 0), float(tech.get("change_pct") or 0), "今日股價"), unsafe_allow_html=True)
                    st.write(f"股數：{row.get('shares')}｜成本：{row.get('cost')}｜市值：{row.get('value')}｜損益：{row.get('pnl')}（{row.get('pnl_pct')}%）｜Radar：{card.get('score')}｜等級：{card.get('grade')}")
                    st.markdown(f"<div class='ux-next'><b>持股下一步</b><br>{row.get('advice','')}</div>", unsafe_allow_html=True)
                    with st.expander("展開股市老師分析", expanded=False):
                        render_teacher_narrative(card, expanded=False)
                    with st.expander("技術圖", expanded=False):
                        render_technical_chart(card, key=f"portfolio-{card.get('symbol')}")
    else:
        st.info("尚未輸入持股。")

elif page == "個股研究":
    st.header("個股研究")
    add_watchlist_ui()
    dynamic_cards = payload.get("all_cards", [])[:30] + payload.get("watchlist_analysis", []) + [row.get("card") for row in payload.get("portfolio_coach", {}).get("rows", []) if row.get("card")]
    choices = {card["label"]: card for card in dynamic_cards if card}
    if choices:
        selected = st.selectbox("選擇個股", list(choices.keys()))
        card = choices[selected]
        _render_summary_card(card, key=f"study-{card.get('symbol')}", detail_open=False, show_chart=True)
    else:
        st.info("尚無可研究個股。")

    st.subheader("0軸轉強雷達")
    zero_items = payload.get("macd_zero_axis_list", [])[:8]
    if not zero_items:
        st.info("目前沒有符合 0 軸轉強條件且資料可用的名單。")
    for card in zero_items:
        with st.container(border=True):
            t = card.get("tech", {})
            macd = t.get("macd", {})
            st.markdown(f"**{card.get('label')}｜{macd.get('zero_axis_status')}**")
            st.markdown(price_html(float(t.get("close") or 0), float(t.get("change_pct") or 0), "今日股價"), unsafe_allow_html=True)
            st.caption(f"DIF {macd.get('macd')}｜DEA {macd.get('signal')}｜柱狀體 {macd.get('hist')}｜RSI {t.get('rsi')}｜量能比 {t.get('volume_ratio')}")
            render_mini_macd_chart(card, key=str(card.get("symbol")))
            st.write(_compact_next_step(card))

elif page == "每日報告":
    _render_clean_daily_report(payload)

elif page == "設定":
    st.header("設定")
    st.subheader("Supabase 狀態")
    cloud_info = cloud_status()
    st.write(f"狀態：**{cloud_info.get('status')}**")
    st.write(f"資料表：`{cloud_info.get('table')}`")
    if cloud_info.get('warning'):
        st.warning(cloud_info.get('warning'))
    if st.button("測試 Supabase 連線與權限", key="supabase_connection_test"):
        check = check_cloud_connection()
        if check.ok:
            st.success(check.message)
        else:
            st.error(check.message)
            if check.detail:
                st.code(check.detail)
    with st.expander("部署與資料保存說明", expanded=False):
        st.markdown("完整設定請看 `docs/deploy/supabase-beginner-guide.md`。朋友若使用 Email + 自訂存取碼，設定 Supabase 後可跨次保存持股。")

st.divider()
_render_footer(payload)
