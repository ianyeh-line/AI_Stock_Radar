"""Streamlit UI for AI Stock Radar v3.13.0 Decision-first UX."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .decision_copy_guard import APP_VERSION, RELEASE_NAME, assert_clean_main_copy
from .decision_data_adapter import DEFAULT_MARKET_GUIDANCE, DEFAULT_MARKET_STATE, ROW_COLUMNS

TODAY_ACTIONS = (
    {
        "title": "先處理持股風險",
        "body": "持股若跌破風險線，先減碼；沒有跌破就續抱觀察。",
    },
    {
        "title": "只看已符合條件的標的",
        "body": "今日可操作清單內的股票，才進一步看進場區、停損線與理由。",
    },
    {
        "title": "不追盤中急拉",
        "body": "沒有進入買進區、法人籌碼不足、或量價結構轉弱的標的，今天先不碰。",
    },
)

KPI_CARDS = (
    ("今日可操作", "actionable", "已符合條件，可檢查進場區與風險線"),
    ("強勢觀察", "watch", "趨勢強，但需突破或回檔確認"),
    ("等待條件", "wait", "沒到價不做，避免追高"),
    ("避開/控風險", "risk", "風險偏高，先不新增部位"),
)

DISPLAY_COLUMNS = {
    "priority": "優先級",
    "stock": "股票",
    "category": "分類",
    "suggestion": "今日建議",
    "trigger": "觸發條件",
    "risk_line": "風險線",
    "reason": "理由",
    "data_status": "資料狀態",
}


def _st():
    import streamlit as st

    return st


def _escape(text: Any) -> str:
    value = "" if text is None else str(text)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def validate_static_main_copy() -> None:
    combined = " ".join(
        [DEFAULT_MARKET_STATE, DEFAULT_MARKET_GUIDANCE]
        + [item[0] + item[2] for item in KPI_CARDS]
        + [item["title"] + item["body"] for item in TODAY_ACTIONS]
        + ["更新今日資料", "今天怎麼做", "今日可操作", "我的持股", "風險清單", "個股研究", "每日報告"]
    )
    assert_clean_main_copy(combined, context="static main copy")


def render_global_css() -> None:
    st = _st()
    st.markdown(
        """
        <style>
        .block-container { max-width: 1180px; padding-top: 2rem; }
        div[data-testid="stMetric"] { border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px; }
        .asr-hero {
            padding: 1.5rem 1.7rem;
            border: 1px solid #e2e8f0;
            border-radius: 1.25rem;
            background: linear-gradient(135deg, #f8fbff 0%, #ffffff 76%);
            box-shadow: 0 10px 28px rgba(15,23,42,0.045);
            margin-bottom: 1.1rem;
        }
        .asr-hero-kicker { color: #2563eb; font-weight: 800; margin-bottom: .55rem; }
        .asr-hero-title { font-size: 2.05rem; font-weight: 900; color: #0f172a; margin-bottom: .45rem; }
        .asr-hero-subtitle { font-size: 1.04rem; color: #475569; line-height: 1.7; }
        .asr-kpi-card {
            min-height: 132px;
            padding: 1.1rem 1.2rem;
            border: 1px solid #e5e7eb;
            border-radius: 1rem;
            background: #ffffff;
            box-shadow: 0 8px 22px rgba(15,23,42,0.04);
        }
        .asr-kpi-label { color: #64748b; font-weight: 800; margin-bottom: .75rem; }
        .asr-kpi-value { font-size: 2rem; font-weight: 900; color: #0f172a; line-height: 1; }
        .asr-kpi-hint { font-size: .86rem; color: #64748b; line-height: 1.45; margin-top: .8rem; }
        .asr-action {
            padding: 1rem 1.2rem;
            border: 1px solid #e5e7eb;
            border-radius: .9rem;
            background: #ffffff;
            margin-bottom: .75rem;
        }
        .asr-action-title { font-weight: 900; color: #0f172a; margin-bottom: .25rem; }
        .asr-action-body { color: #475569; line-height: 1.65; }
        @media (max-width: 720px) {
            .asr-hero-title { font-size: 1.62rem; }
            .asr-hero { padding: 1.2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st = _st()
    st.sidebar.markdown("## 👤 使用者資料")
    st.sidebar.caption("朋友若要下次保留持股，請使用 Email 加自訂存取碼。")
    st.sidebar.text_input("Email", placeholder="friend@example.com")
    st.sidebar.text_input("自訂存取碼", placeholder="自己記得住即可", type="password")
    st.sidebar.button("載入 / 保存我的資料", use_container_width=True)
    with st.sidebar.expander("進階設定"):
        st.caption("進階檢查預設收合，不干擾每日決策。")
        st.button("資料庫連線檢查", use_container_width=True)


def render_header() -> None:
    st = _st()
    st.markdown(
        f"""
        <div style="margin-bottom: 1.35rem;">
            <h1 style="margin-bottom: .2rem;">🚀 AI Stock Radar</h1>
            <div style="color:#64748b; font-weight:700;">AI 股市老師｜今日決策</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_update_button() -> None:
    st = _st()
    left, right = st.columns([1.15, 4.85])
    with left:
        st.button("更新今日資料", use_container_width=True)
    with right:
        st.caption("更新後會重新整理今日策略、可操作清單與持股風險。")


def render_market_brief(view: dict[str, Any], snapshot_time: str = "盤中") -> None:
    st = _st()
    title = view.get("market_state") or DEFAULT_MARKET_STATE
    subtitle = view.get("market_guidance") or DEFAULT_MARKET_GUIDANCE
    assert_clean_main_copy(title + subtitle, context="market brief")
    st.markdown(
        f"""
        <div class="asr-hero">
            <div class="asr-hero-kicker">AI 股市老師｜{_escape(snapshot_time)}</div>
            <div class="asr-hero-title">{_escape(title)}</div>
            <div class="asr-hero-subtitle">{_escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(summary: dict[str, int]) -> None:
    st = _st()
    card_text = " ".join(label + hint for label, _, hint in KPI_CARDS)
    assert_clean_main_copy(card_text, context="kpi cards")
    columns = st.columns(4)
    for col, (label, key, hint) in zip(columns, KPI_CARDS):
        with col:
            value = int(summary.get(key, 0) or 0)
            st.markdown(
                f"""
                <div class="asr-kpi-card">
                    <div class="asr-kpi-label">{_escape(label)}</div>
                    <div class="asr-kpi-value">{value}</div>
                    <div class="asr-kpi-hint">{_escape(hint)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_today_action_plan() -> None:
    st = _st()
    main_copy = "今天先做這 3 件事" + "".join(item["title"] + item["body"] for item in TODAY_ACTIONS)
    assert_clean_main_copy(main_copy, context="today action plan")
    st.markdown("## 今天先做這 3 件事")
    for idx, item in enumerate(TODAY_ACTIONS, start=1):
        st.markdown(
            f"""
            <div class="asr-action">
                <div class="asr-action-title">{idx}. {_escape(item['title'])}</div>
                <div class="asr-action-body">{_escape(item['body'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_stock_table(rows: list[dict[str, Any]], empty_message: str = "目前沒有符合條件的標的。今天以等待為主，不追高。") -> None:
    st = _st()
    if not rows:
        st.info(empty_message)
        return

    clean_rows = []
    for row in rows:
        main_text = " ".join(str(row.get(column, "")) for column in ROW_COLUMNS)
        assert_clean_main_copy(main_text, context="stock decision table")
        clean_rows.append({column: row.get(column, "—") for column in ROW_COLUMNS})

    df = pd.DataFrame(clean_rows).rename(columns=DISPLAY_COLUMNS)
    st.dataframe(df[list(DISPLAY_COLUMNS.values())], hide_index=True, use_container_width=True)


def render_research_placeholder() -> None:
    st = _st()
    stock_code = st.text_input("輸入股票代號或名稱", placeholder="例如：2330 台積電")
    if stock_code:
        st.info("輸入後顯示該股的趨勢、籌碼、風險與操作條件。")


def render_report_placeholder(view: dict[str, Any]) -> None:
    st = _st()
    rows = view.get("decision_rows", [])
    if rows:
        st.markdown("### 今日摘要")
        st.write(f"今日共整理 {len(rows)} 檔標的，優先檢查可操作清單與風險清單。")
    else:
        st.info("尚未產生今日完整報告。請先執行資料更新流程。")


def render_footer_diagnostics(view: dict[str, Any]) -> None:
    st = _st()
    diagnostics = view.get("diagnostics") or {}
    with st.expander("資料來源與版本資訊"):
        st.write(f"版本：{APP_VERSION}｜{RELEASE_NAME}")
        st.write(f"價格資料狀態：{diagnostics.get('price_status', '未提供')}")
        st.write(f"三大法人資料狀態：{diagnostics.get('official_chip_status', '未提供')}")
        st.write(f"資料更新時間：{diagnostics.get('generated_at', '未提供')}")
        st.caption("資料不足時，系統不會把該項目當成加分理由；主畫面只呈現可理解的決策與資料狀態。")


def render_home_page(view: dict[str, Any], snapshot_time: str = "盤中") -> None:
    validate_static_main_copy()
    render_global_css()
    render_sidebar()
    render_header()
    render_update_button()
    st = _st()
    st.divider()
    render_market_brief(view, snapshot_time=snapshot_time)
    render_kpi_cards(view.get("summary", {}))
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    tab_today, tab_actionable, tab_holdings, tab_risk, tab_research, tab_report = st.tabs(
        ["今天怎麼做", "今日可操作", "我的持股", "風險清單", "個股研究", "每日報告"]
    )
    with tab_today:
        render_today_action_plan()
        st.markdown("### 今日優先清單")
        render_stock_table(view.get("decision_rows", []))
    with tab_actionable:
        st.markdown("## 今日可操作")
        render_stock_table(view.get("actionable_rows", []), "目前沒有已符合條件的標的。今天不追高，等待價格條件成立。")
    with tab_holdings:
        st.markdown("## 我的持股處置")
        render_stock_table(view.get("holding_rows", []), "目前沒有載入持股資料。")
    with tab_risk:
        st.markdown("## 風險清單")
        render_stock_table(view.get("risk_rows", []), "目前沒有需要列入風險清單的標的。")
    with tab_research:
        st.markdown("## 個股研究")
        render_research_placeholder()
    with tab_report:
        st.markdown("## 每日報告")
        render_report_placeholder(view)

    st.divider()
    render_footer_diagnostics(view)
