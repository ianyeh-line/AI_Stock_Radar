from radar.teacher.decision import run_teacher_pipeline, build_decision_card
from radar.data.stock_master import resolve_stock, register_custom_stock, StockInfo
from radar.core.indicators import macd


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.8.2"
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
    required = ["technical", "chip", "news", "support_resistance", "scenario_a", "scenario_b", "scenario_c", "no_position_strategy", "holding_strategy", "risk"]
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
