import pytest

from radar.engine.decision import run_decision_pipeline


@pytest.fixture(scope="module")
def payload():
    return run_decision_pipeline(news_limit=3, price_days=120)


def test_pipeline_generates_payload(payload):
    assert payload["version"] == "2.1.0"
    assert payload["decision_cards"]
    assert payload["macd_candidates"]
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
