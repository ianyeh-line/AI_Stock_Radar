from radar.datasource.rss_news import fetch_rss_news
from radar.engine.decision import build_decision_cards
from radar.engine.personalization import load_investor_profile
from radar.knowledge.stock_map import load_stock_universe


def test_pipeline_smoke():
    news, _ = fetch_rss_news(limit=3)
    stocks = load_stock_universe()
    profile = load_investor_profile()
    cards = build_decision_cards(news, stocks, profile)
    assert news
    assert stocks
    assert cards
    assert cards[0].radar_score > 0
