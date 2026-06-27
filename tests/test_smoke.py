from radar.datasource.mock_news import load_news
from radar.engine.decision import build_daily_decision
from radar.report.markdown import render_report


def test_pipeline_smoke():
    news = load_news()
    decision = build_daily_decision(news)
    report = render_report(decision)
    assert "AI Stock Radar Daily Report" in report
    assert decision.top_cards
