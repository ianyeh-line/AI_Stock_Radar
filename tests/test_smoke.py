from radar.datasource.rss_news import load_news
from radar.engine.decision import build_decision
from radar.report.markdown import render_markdown


def test_smoke_pipeline():
    source, items = load_news()
    decision = build_decision(source, items)
    report = render_markdown(decision)
    assert decision.version == "0.8.0"
    assert decision.cards
    assert "AI Stock Radar" in report
    assert "技術線圖" in report
