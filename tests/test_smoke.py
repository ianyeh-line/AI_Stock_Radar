from radar.datasource.rss_news import load_fallback_news
from radar.engine.decision import build_decision
from radar.report.markdown import build_markdown


def test_smoke_report_builds():
    news = load_fallback_news()
    decision = build_decision(news, live_news=False)
    report = build_markdown(decision)
    assert "AI Stock Radar Daily Report" in report
    assert decision.top_stocks
