"""Streamlit dashboard for AI Stock Radar."""

from __future__ import annotations

from collections import Counter

from radar.datasource.rss_news import load_news
from radar.engine.decision import build_decision
from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import DailyDecision, DecisionCard, NewsItem, TechnicalSnapshot


def _tone_icon(tone: str) -> str:
    if tone == "positive":
        return "✅"
    if tone == "negative":
        return "⚠️"
    return "➖"


def _sentiment_zh(sentiment: str) -> str:
    if sentiment == "positive":
        return "正向"
    if sentiment == "negative":
        return "負向"
    return "中性"


def _score_label(score: int) -> str:
    if score >= 78:
        return "高優先"
    if score >= 66:
        return "密切觀察"
    if score >= 54:
        return "等待確認"
    return "風險優先"


def _stock_link(ticker: str, name: str) -> str:
    return f"[{ticker} {name}](?ticker={ticker})"


def _query_ticker(st, decision: DailyDecision) -> str:
    default = decision.cards[0].ticker if decision.cards else "2330"
    try:
        value = st.query_params.get("ticker", default)
        if isinstance(value, list):
            return value[0] if value else default
        return value or default
    except Exception:
        try:
            params = st.experimental_get_query_params()
            values = params.get("ticker", [default])
            return values[0] if values else default
        except Exception:
            return default


def _card_by_ticker(decision: DailyDecision, ticker: str) -> DecisionCard:
    for card in decision.cards:
        if card.ticker == ticker:
            return card
    return decision.cards[0]


def _load_decision() -> DailyDecision:
    news_source, news_items = load_news()
    return build_decision(news_source, news_items)


def _render_css(st) -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.25rem; padding-bottom: 2.5rem;}
        .radar-hero {
            padding: 1.35rem 1.5rem;
            border-radius: 20px;
            border: 1px solid rgba(120,120,120,0.28);
            background: linear-gradient(135deg, rgba(40,120,255,0.10), rgba(0,180,120,0.08));
            margin-bottom: 1rem;
        }
        .radar-title {font-size: 2.05rem; font-weight: 800; margin-bottom: .2rem;}
        .radar-subtitle {font-size: 1rem; opacity: .75;}
        .section-note {opacity: .78; font-size: .94rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(st, decision: DailyDecision) -> None:
    _render_css(st)
    st.markdown(
        f"""
        <div class="radar-hero">
          <div class="radar-title">🚀 AI Stock Radar｜每日台股 AI 決策</div>
          <div class="radar-subtitle">Decision OS v{decision.version}｜{decision.news_source}｜已分析 {decision.news_count} 則新聞｜介面與新聞摘要全中文</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("今日盤勢", decision.market_view)
    col2.metric("AI 信心", f"{decision.ai_confidence}%")
    col3.metric("決策卡數", len(decision.cards))
    buy_count = sum(1 for card in decision.cards if card.stance == "Buy")
    col4.metric("買進候選", buy_count)

    st.info(decision.today_action)


def _render_technical_chart(st, technical: TechnicalSnapshot) -> None:
    import pandas as pd

    st.markdown(f"### {_stock_link(technical.ticker, technical.name)} 技術線圖")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("最新價", f"{technical.price}")
    c2.metric("MA5", f"{technical.ma5}")
    c3.metric("MA20", f"{technical.ma20}")
    c4.metric("MA60", f"{technical.ma60}")
    c5.metric("RSI14", f"{technical.rsi14}")

    df = pd.DataFrame(technical.history)
    if not df.empty:
        df = df.rename(columns={"date": "日期", "close": "收盤價", "ma5": "MA5", "ma20": "MA20", "volume": "成交量"})
        df = df.set_index("日期")
        st.line_chart(df[["收盤價", "MA5", "MA20"]], use_container_width=True)
        st.bar_chart(df[["成交量"]], use_container_width=True)
    st.caption(f"資料來源：{technical.data_source}｜{technical.chart_note}")
    st.write(f"**技術判讀：** {technical.trend}｜{technical.signal}")


def _render_summary_tab(st, decision: DailyDecision, selected_card: DecisionCard) -> None:
    st.subheader("今日 3 分鐘決策摘要")
    top = decision.cards[0]
    cols = st.columns([1.2, 1.2, 1.2])
    cols[0].metric("第一優先", f"{top.ticker} {top.name}", top.decision)
    cols[1].metric("Radar Score", top.radar_score)
    cols[2].metric("信心", f"{top.confidence}%")

    st.markdown("#### Top 5 決策清單")
    for idx, card in enumerate(decision.cards[:5], start=1):
        st.markdown(
            f"{idx}. {_stock_link(card.ticker, card.name)}｜Radar **{card.radar_score}**｜{card.decision}｜"
            f"新聞 {card.news_score}｜技術 {card.technical_score}｜風險 {card.risk_score}｜{card.reason}"
        )

    st.divider()
    st.subheader("目前選定個股技術線圖")
    _render_technical_chart(st, selected_card.technical)


def _render_card(st, card: DecisionCard, rank: int) -> None:
    with st.container(border=True):
        header1, header2, header3, header4 = st.columns([2.25, 1, 1, 1.7])
        header1.markdown(f"### {rank}. {_stock_link(card.ticker, card.name)}")
        header2.metric("Radar", card.radar_score)
        header3.metric("信心", f"{card.confidence}%")
        header4.markdown(f"**決策：** {card.decision}  \n**等級：** {_score_label(card.radar_score)}")

        score_cols = st.columns(3)
        score_cols[0].metric("新聞", card.news_score)
        score_cols[1].metric("技術", card.technical_score)
        score_cols[2].metric("風險", card.risk_score)

        st.progress(min(100, max(0, card.radar_score)) / 100)
        st.markdown(f"**理由：** {card.reason}")

        action_col, rule_col = st.columns(2)
        action_col.markdown("**今日行動**")
        action_col.write(card.action)
        rule_col.markdown("**進出場條件**")
        rule_col.write(card.position_rule)

        st.markdown("**Evidence Chain**")
        for ev in card.evidence:
            sign = "+" if ev.score > 0 else ""
            st.write(f"{_tone_icon(ev.tone)} **{ev.category}｜{ev.signal_zh}** ({sign}{ev.score})｜{ev.source}｜{ev.reason}")

        st.warning(card.risk_note)


def _render_decision_tab(st, decision: DailyDecision) -> None:
    st.subheader("決策卡：News + Technical + Risk")
    st.caption("點擊任何個股代號，可在頁面上方或技術線圖分頁看到該股技術線圖。")
    for idx, card in enumerate(decision.cards, start=1):
        _render_card(st, card, idx)


def _render_news_item(st, item: NewsItem) -> None:
    affected = []
    for ticker in item.tickers:
        affected.append(_stock_link(ticker, WATCHLIST.get(ticker, {}).get("name", ticker)))
    affected_text = "、".join(affected) if affected else "大盤"
    icon = "✅" if item.sentiment == "positive" else "⚠️" if item.sentiment == "negative" else "➖"
    with st.container(border=True):
        st.markdown(f"**{icon} {item.title_zh}**")
        st.write(item.summary_zh)
        st.markdown(f"- 來源：{item.source}")
        st.markdown(f"- 訊號：{item.signal_zh}")
        st.markdown(f"- 情緒：{_sentiment_zh(item.sentiment)}")
        st.markdown(f"- 受影響個股：{affected_text}")
        if item.title and item.title != item.title_zh:
            with st.expander("查看英文原文"):
                st.write(item.title)
                if item.summary:
                    st.write(item.summary)


def _render_news_tab(st, decision: DailyDecision) -> None:
    st.subheader("新聞影響鏈：新聞 → 訊號 → 個股")
    signal_counter = Counter(item.signal_zh for item in decision.news_items)
    sentiment_counter = Counter(_sentiment_zh(item.sentiment) for item in decision.news_items)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**偵測到的訊號**")
        for signal, count in signal_counter.most_common():
            st.write(f"- {signal}: {count}")
    with c2:
        st.markdown("**新聞情緒結構**")
        for sentiment, count in sentiment_counter.most_common():
            st.write(f"- {sentiment}: {count}")

    st.divider()
    for item in decision.news_items[:15]:
        _render_news_item(st, item)


def _render_chart_tab(st, decision: DailyDecision, selected_card: DecisionCard) -> None:
    st.subheader("個股技術線圖")
    ticker_options = {f"{card.ticker} {card.name}": card for card in decision.cards}
    default_label = f"{selected_card.ticker} {selected_card.name}"
    labels = list(ticker_options)
    selected_label = st.selectbox("選擇個股", labels, index=labels.index(default_label) if default_label in labels else 0)
    _render_technical_chart(st, ticker_options[selected_label].technical)


def _render_risk_tab(st, decision: DailyDecision) -> None:
    st.subheader("風險提醒")
    for risk in decision.risk_alerts:
        st.warning(risk)

    st.subheader("賣出 / 等待清單")
    weak_cards = [card for card in decision.cards if card.stance in {"Sell", "Wait"}]
    if not weak_cards:
        st.success("目前 Top Cards 沒有賣出訊號。")
    for card in weak_cards:
        st.write(f"{_stock_link(card.ticker, card.name)}｜{card.decision}｜Radar {card.radar_score}｜{card.risk_note}")


def _render_report_tab(st, decision: DailyDecision) -> None:
    from radar.report.markdown import render_markdown

    st.subheader("Markdown 每日報告預覽")
    st.markdown(render_markdown(decision))


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="AI Stock Radar", page_icon="🚀", layout="wide")
    decision = _load_decision()
    selected_ticker = _query_ticker(st, decision)
    selected_card = _card_by_ticker(decision, selected_ticker)

    _render_hero(st, decision)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["今日總覽", "決策卡", "新聞影響鏈", "技術線圖", "風險與報告"])
    with tab1:
        _render_summary_tab(st, decision, selected_card)
    with tab2:
        _render_decision_tab(st, decision)
    with tab3:
        _render_news_tab(st, decision)
    with tab4:
        _render_chart_tab(st, decision, selected_card)
    with tab5:
        _render_risk_tab(st, decision)
        st.divider()
        _render_report_tab(st, decision)


if __name__ == "__main__":
    main()
