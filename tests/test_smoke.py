import pytest

from radar.engine.decision import run_decision_pipeline


@pytest.fixture(scope="module")
def payload():
    return run_decision_pipeline(news_limit=3, price_days=120)


def test_pipeline_generates_payload(payload):
    assert payload["version"] == "2.4.0"
    assert payload["decision_cards"]
    assert "macd_candidates" in payload
    if payload["macd_candidates"]:
        assert "latest_date" in payload["macd_candidates"][0]
    assert "portfolio_analysis" in payload
    assert "user_watchlist" in payload
    assert "generated_at" in payload
    assert payload["pm_brief"]["data_quality"].get("price_latest_date_max")
    assert len(payload["stock_index"]) >= 100
    assert "institutional_flows" in payload
    assert payload["institutional_flows"]
    assert "portfolio_coach" in payload


def test_teacher_buy_list_exists(payload):
    teacher = payload["teacher_buy_list"]
    assert "headline" in teacher
    assert "ready_to_buy" in teacher
    assert "wait_breakout" in teacher
    assert "pullback_watch" in teacher
    assert "observe_only" in teacher
    assert "avoid_or_reduce" in teacher
    assert "grading_rule" in teacher
    all_items = teacher["ready_to_buy"] + teacher["wait_breakout"] + teacher["pullback_watch"] + teacher["observe_only"] + teacher["avoid_or_reduce"]
    assert all_items
    first = all_items[0]
    for key in ["grade", "action_type", "suggested_entry_zone", "breakout_trigger", "invalidation_price", "first_profit_take", "second_profit_take"]:
        assert key in first


def test_pm_precision_fields_exist(payload):
    pm = payload["pm_brief"]
    assert pm["recommended_stocks"]
    first = payload["decision_cards"][0]
    for key in ["breakout_price", "pullback_low", "pullback_high", "reduce_price", "stop_loss_price", "volume_ratio_note"]:
        assert key in first
    assert "突破" in first["entry_condition"] or "拉回" in first["entry_condition"]
    assert "量能比" in first["volume_ratio_note"]


def test_technical_profile_contains_short_term_chart_fields(payload):
    profile = next(iter(payload["technical_profiles"].values()))
    latest_bar = profile["history"][-1]
    assert "ma5" in latest_bar
    assert "ma10" in latest_bar
    assert "volume_ma5" in latest_bar
    assert "volume_ma20" in latest_bar


def test_institutional_flow_fields_exist(payload):
    first = payload["decision_cards"][0]
    assert "institutional_summary" in first
    assert "institutional_flow" in first
    assert "institutional_flow" in first["score_breakdown"]
    quality = payload["pm_brief"]["data_quality"]
    assert "institutional_official_count" in quality
    assert "institutional_fallback_count" in quality


def test_portfolio_coach_exists(payload):
    coach = payload["portfolio_coach"]
    assert "headline" in coach
    assert "risk_level" in coach
    assert "teacher_actions" in coach


def test_phase5_fields_exist(payload):
    assert "data_trust" in payload
    assert "backtest_summary" in payload
    assert payload["data_trust"].get("guardrails_by_symbol")
    assert "per_symbol" in payload["backtest_summary"]
    teacher = payload["teacher_buy_list"]
    all_items = teacher["ready_to_buy"] + teacher["wait_breakout"] + teacher["pullback_watch"] + teacher["observe_only"] + teacher["avoid_or_reduce"]
    first = all_items[0]
    assert "guardrail_status" in first
    assert "backtest_sample_count" in first
    assert "capital_policy" in payload["portfolio_coach"]


def test_v220_ai_teacher_brief_exists(payload):
    teacher = payload["ai_teacher_brief"]
    assert "posture" in teacher
    assert "scenario_plan" in teacher
    assert "macd_commentary" in teacher


def test_macd_candidates_are_not_fallback(payload):
    for item in payload["macd_candidates"]:
        assert item["price_source"].startswith("Yahoo Finance")


def test_price_context_entry_language_does_not_say_stand_back_to_lower_support():
    from radar.engine.decision import _manager_language
    from radar.models.domain import StockMeta, TechnicalProfile

    stock = StockMeta(
        symbol="2327",
        name="國巨",
        sector="Passive Components",
        theme=["passive"],
        yahoo_symbol="2327.TW",
        pm_view="以波段價格紀律評估。",
    )
    profile = TechnicalProfile(
        symbol="2327",
        name="國巨",
        yahoo_symbol="2327.TW",
        price_source="Yahoo Finance .TW",
        bars_count=160,
        latest_close=1015.0,
        change_pct=1.2,
        ma5=1000.0,
        ma10=980.0,
        ma20=900.0,
        ma60=850.0,
        ma120=800.0,
        volume_ma5=1,
        volume_ma20=1,
        bb_upper=1100.0,
        bb_lower=850.0,
        dif=-1.0,
        dea=0.0,
        macd_hist=-1.0,
        macd_hist_prev=-0.5,
        rsi=55.0,
        volume_ratio=1.0,
        trend_score=45,
        risk_score=65,
        ma_state="測試",
        technical_summary="測試",
        latest_date="2026-06-26",
        history=[],
    )
    levels = {"breakout": 1160.0, "pullback_low": 890.0, "pullback_high": 915.0, "reduce": 880.0, "stop": 820.0}
    _, entry, *_ = _manager_language(stock, profile, "減碼/避開", levels, "量能比 1.00：測試")
    assert "現價 1015.00 已高於支撐區" in entry
    assert "重新站回 915.00" not in entry


def test_user_data_uses_persistent_home_directory():
    from radar.engine.user_space import get_user_data_status

    status = get_user_data_status()
    assert ".ai_stock_radar" in status["portfolio_path"]
    assert ".ai_stock_radar" in status["watchlist_path"]
    assert status["legacy_portfolio_path"] == "config/portfolio.json"
