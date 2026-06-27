from radar.datasource.rss_news import load_news
from radar.engine.decision import build_decision
from radar.report.markdown import render_markdown


def test_decision_report_smoke():
    source, news = load_news()
    decision = build_decision(source, news)
    report = render_markdown(decision)
    assert "Decision Cards" in report
    assert decision.cards
