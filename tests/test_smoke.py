from radar.teacher.decision import run_teacher_pipeline, build_decision_card
from radar.data.stock_master import resolve_stock, register_custom_stock, StockInfo
from radar.core.indicators import macd


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.12.0"
    assert "buy_list" in payload
    assert "macd_zero_axis_list" in payload
    assert "strong_momentum" in payload
    assert "strength_gap_analysis" in payload


def test_stock_master_huatong():
    assert resolve_stock("2313").name == "華通"
    assert resolve_stock("華通").symbol == "2313"
    assert resolve_stock("2313 華通").label == "2313 華通"


def test_stock_master_nanya_tech():
    assert resolve_stock("2408").name == "南亞科"
    assert resolve_stock("南亞科").symbol == "2408"
    assert resolve_stock("2408 南亞科").label == "2408 南亞科"


def test_stock_master_generalplus():
    assert resolve_stock("4952").name == "凌通"
    assert resolve_stock("凌通").symbol == "4952"
    assert resolve_stock("4952 凌通").label == "4952 凌通"


def test_custom_fallback_keeps_supplied_name():
    assert resolve_stock("9999 測試股").name == "測試股"


def test_unknown_numeric_is_allowed_for_dynamic_fetch():
    stock = resolve_stock("7777")
    assert stock.symbol == "7777"
    assert stock.name.startswith("待識別")


def test_register_custom_stock_name_lookup():
    register_custom_stock(StockInfo("8888", "測試自動新增", "TW", "自動新增"))
    assert resolve_stock("測試自動新增").symbol == "8888"
    assert resolve_stock("8888").name == "測試自動新增"


def test_macd_zero_axis_field_exists():
    values = [100 - i * 0.2 for i in range(80, 40, -1)] + [92 + i * 0.8 for i in range(40)]
    m = macd(values)
    assert "zero_axis_status" in m
    assert "zero_axis_score" in m


def test_positive_macd_never_labelled_below_zero():
    # Rising then mild pullback: MACD/DIF stays above zero but may decline.
    values = [50 + i * 2 for i in range(80)] + [210, 208, 207, 206, 205]
    m = macd(values)
    if m["macd"] > 0:
        assert "下方" not in m["zero_axis_status"]


def test_data_trust_exists_on_decision_card():
    card = build_decision_card(resolve_stock("2330"))
    assert "data_trust" in card
    assert "status" in card["data_trust"]

from radar.integrations.cloud_user_store import _normalize_supabase_url, _normalize_table_name


def test_supabase_secret_url_normalization():
    assert _normalize_supabase_url("https://abc.supabase.co/rest/v1") == "https://abc.supabase.co"
    assert _normalize_supabase_url("abc.supabase.co/rest/v1/user_profiles") == "https://abc.supabase.co"


def test_supabase_secret_table_normalization():
    assert _normalize_table_name("public.user_profiles") == "user_profiles"
    assert _normalize_table_name("/rest/v1/user_profiles") == "user_profiles"


def test_macd_observation_uses_zero_axis_candidates():
    payload = run_teacher_pipeline()
    assert payload["macd_list"] == payload["macd_zero_axis_list"]
    for card in payload["macd_list"]:
        assert card["data_trust"]["actionable"]
        assert card["tech"]["macd"]["zero_axis_status"] in {"即將從0軸翻正", "剛從0軸翻正"}


from radar.core.official_data import _normalize_symbol, _snapshot_from_row, OfficialSnapshot, apply_official_snapshot
from radar.data.stock_master import StockInfo


def test_official_snapshot_parser_twse_style():
    stock = StockInfo("2330", "台積電", "TW", "半導體")
    row = {"Code": "2330", "Name": "台積電", "OpeningPrice": "1000", "HighestPrice": "1020", "LowestPrice": "990", "ClosingPrice": "1010", "TradeVolume": "1,234,000", "Change": "+10"}
    snapshot = _snapshot_from_row(row, stock, "TWSE OpenAPI")
    assert snapshot.ok
    assert snapshot.close == 1010
    assert snapshot.volume == 1234000


def test_apply_official_snapshot_updates_latest_row():
    payload = {"source": "Yahoo Finance", "latest_date": "2026-01-01", "prices": [{"date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100}], "data_quality": "live_daily"}
    snapshot = OfficialSnapshot("2330", "台積電", "TW", "TWSE OpenAPI", "2026-01-02", 12, 13, 11, 12.5, 200, 2.5, True)
    updated = apply_official_snapshot(payload, snapshot)
    assert updated["official_confirmed"] is True
    assert updated["prices"][-1]["close"] == 12.5
    assert updated["latest_date"] == "2026-01-02"


from radar.core.official_data import apply_official_snapshot, OfficialSnapshot


def test_yahoo_newer_than_official_is_kept():
    payload = {"source": "Yahoo Finance", "latest_date": "2026-06-30", "prices": [{"date": "2026-06-30", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100}], "data_quality": "live_daily"}
    snapshot = OfficialSnapshot("2330", "台積電", "TW", "TWSE OpenAPI", "2026-06-29", 12, 13, 11, 12.5, 200, 2.5, True)
    updated = apply_official_snapshot(payload, snapshot)
    assert updated["latest_date"] == "2026-06-30"
    assert updated["prices"][-1]["close"] == 10
    assert updated["official_lagging"] is True
    assert updated["data_quality"] == "yahoo_newer_than_official"


def test_undated_official_does_not_overwrite_yahoo():
    payload = {"source": "Yahoo Finance", "latest_date": "2026-06-30", "prices": [{"date": "2026-06-30", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100}], "data_quality": "live_daily"}
    snapshot = OfficialSnapshot("2330", "台積電", "TW", "TWSE OpenAPI", "", 12, 13, 11, 12.5, 200, 2.5, True)
    updated = apply_official_snapshot(payload, snapshot)
    assert updated["latest_date"] == "2026-06-30"
    assert updated["prices"][-1]["close"] == 10
    assert updated["official_confirmed"] is False

from radar.core.market_data import _merge_yahoo_latest_quote


def test_yahoo_latest_quote_merges_same_day_price():
    rows = [{"date": "2026-06-30", "open": 100, "high": 105, "low": 95, "close": 100, "volume": 1000}]
    meta = {"regularMarketPrice": 103, "regularMarketTime": 1782777600, "regularMarketVolume": 2000, "regularMarketOpen": 101, "regularMarketDayHigh": 104, "regularMarketDayLow": 99}
    updated, merged = _merge_yahoo_latest_quote(rows, meta)
    assert merged is True
    assert updated[-1]["close"] == 103
    assert updated[-1]["volume"] == 2000


from radar.teacher.decision import _data_trust, trading_status


def test_yahoo_latest_expected_date_is_actionable_without_official_confirmation():
    status = {"date": "2026-07-01", "time": "10:00", "timezone": "Asia/Taipei", "weekday": "三", "session": "盤中", "is_trade_day": True}
    prices = {"latest_date": "2026-07-01", "source": "Yahoo Finance 最新報價", "data_quality": "yahoo_latest_quote", "official_confirmed": False, "official_lagging": False}
    trust = _data_trust(prices, 90, status)
    assert trust["actionable"] is True
    assert trust["trust_level"] == "高"
    assert not trust["warnings"]


def test_premarket_previous_trading_day_is_actionable():
    status = {"date": "2026-07-01", "time": "08:30", "timezone": "Asia/Taipei", "weekday": "三", "session": "盤前", "is_trade_day": True}
    prices = {"latest_date": "2026-06-30", "source": "Yahoo Finance", "data_quality": "live_daily", "official_confirmed": False}
    trust = _data_trust(prices, 90, status)
    assert trust["actionable"] is True
    assert not trust["warnings"]


def test_teacher_narrative_has_required_facets_and_no_source_penalty_text():
    card = build_decision_card(resolve_stock("2330"))
    narrative = card["teacher_narrative"]
    required = ["technical", "news", "support_resistance", "scenario_a", "scenario_b", "scenario_c", "no_position_strategy", "holding_strategy", "risk"]
    for key in required:
        assert narrative.get(key)
    joined = " ".join(str(v) for v in narrative.values()) + " " + " ".join(card.get("reasons", []))
    assert "信心略降" not in joined
    assert "官方尚未完全同步" not in joined
    assert "Yahoo 較新" not in joined


def test_strong_momentum_payload_exists():
    payload = run_teacher_pipeline()
    strength = payload["strong_momentum"]
    assert "strong_list" in strength
    assert "limit_watch" in strength
    assert "no_chase_list" in strength
    assert "tomorrow_watch" in strength
    assert "summary" in payload["strength_gap_analysis"]


def test_teacher_narrative_omits_fake_chip_template_when_no_flow_data():
    card = build_decision_card(resolve_stock("2330"))
    chip = card["teacher_narrative"].get("chip", "")
    assert "籌碼面目前以量能" not in chip
    assert "分點主力" not in chip


def test_action_logic_does_not_buy_below_zone_when_price_extended():
    from radar.teacher.decision import _action_text
    tech = {
        "close": 5200.0,
        "support_low": 4876.73,
        "support_high": 5025.26,
        "breakout": 5797.40,
        "stop": 4836.0,
        "trim1": 5500.0,
        "trim2": 5700.0,
        "change_pct": 10.0,
        "volume_ratio": 1.4,
    }
    text = _action_text("今日可買", tech)
    assert "可在 4876.73～5025.26 分批" not in text
    assert "已離理想買點" in text or "不追" in text


def test_breakout_unreachable_today_not_used_as_current_condition():
    from radar.teacher.decision import _breakout_context
    tech = {
        "close": 5200.0,
        "support_low": 4876.73,
        "support_high": 5025.26,
        "breakout": 5797.40,
        "stop": 4836.0,
        "change_pct": 10.0,
        "volume_ratio": 1.4,
    }
    text = _breakout_context(tech)
    assert "今日不能把突破當成可執行條件" in text


def test_quality_gate_blocks_extended_price_from_a_grade():
    from radar.teacher.decision import _quality_gate
    tech = {
        "close": 5200.0,
        "support_low": 4876.73,
        "support_high": 5025.26,
        "breakout": 5797.40,
        "stop": 4836.0,
        "change_pct": 10.0,
        "volume_ratio": 1.4,
        "rsi": 62,
    }
    gate = _quality_gate(90, tech, {"actionable": True})
    assert gate["passed"] is False
    assert any("高於拉回買點" in x for x in gate["failures"])


def test_teacher_narrative_price_state_not_low_zone_buy_when_extended():
    from radar.teacher.decision import _teacher_narrative
    from radar.data.stock_master import resolve_stock
    stock = resolve_stock("6669")
    card = {
        "decision": "等待突破",
        "score": 88,
        "grade": "B",
        "quality_gate": {"passed": False, "failures": ["現價已高於拉回買點"]},
        "tech": {
            "close": 5200.0,
            "support_low": 4876.73,
            "support_high": 5025.26,
            "breakout": 5797.40,
            "stop": 4836.0,
            "trim1": 5512.0,
            "trim2": 5720.0,
            "change_pct": 10.0,
            "volume_ratio": 1.4,
            "rsi": 62,
            "ma20": 4950.0,
            "ma60": 4800.0,
            "macd": {"macd": 12.3, "signal": 10.1, "hist": 2.2, "zero_axis_status": "0軸上方延續", "hist_status": "柱狀體已翻正延續"},
        },
    }
    narrative = _teacher_narrative(stock, card)
    joined = " ".join(str(v) for v in narrative.values())
    assert "可在 4876.73～5025.26" not in joined
    assert "高於拉回買點" in joined or "不追" in joined


def test_no_yahoo_source_penalty_words_in_pipeline_payload():
    payload = run_teacher_pipeline()
    blob = str(payload.get("buy_list", "")) + str(payload.get("wait_list", "")) + str(payload.get("portfolio_coach", ""))
    assert "信心略降" not in blob
    assert "官方尚未完全同步" not in blob


def test_daily_decision_loop_exists():
    payload = run_teacher_pipeline()
    loop = payload.get("decision_loop")
    assert loop
    assert "session_mode" in loop
    assert "pre_market_plan" in loop
    assert "recommendation_review" in loop
    assert "tomorrow_preparation" in loop


def test_journal_runtime_output_is_gitignored():
    from pathlib import Path
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/journal/" in ignore

from radar.core.chip_data import fetch_chip_flow


def test_chip_flow_object_has_explicit_availability():
    flow = fetch_chip_flow(resolve_stock("2330")).as_dict()
    assert "available" in flow
    assert "message" in flow
    assert "source" in flow


def test_decision_card_contains_chip_flow():
    card = build_decision_card(resolve_stock("2330"))
    assert "chip_flow" in card
    assert "available" in card["chip_flow"]


def test_chip_quiet_mode_when_unavailable():
    card = build_decision_card(resolve_stock("2330"))
    chip = card["teacher_narrative"].get("chip", "")
    if not card.get("chip_flow", {}).get("available"):
        assert chip == "法人籌碼：未取得，不列入本次判斷。"


def test_action_text_contains_concrete_prices_and_no_vague_support():
    card = build_decision_card(resolve_stock("2330"))
    action = card.get("action", "")
    assert "等待回測支撐" not in action
    assert any(ch.isdigit() for ch in action)


def test_macd_zero_action_has_price_condition():
    payload = run_teacher_pipeline()
    for card in payload.get("macd_zero_axis_list", [])[:3]:
        text = card.get("macd_zero_action", "")
        assert text
        assert any(ch.isdigit() for ch in text)
        assert "DIF" in text
