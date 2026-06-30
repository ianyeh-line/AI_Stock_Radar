from radar.teacher.decision import run_teacher_pipeline, build_decision_card
from radar.data.stock_master import resolve_stock, register_custom_stock, StockInfo
from radar.core.indicators import macd


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.5.0"
    assert "buy_list" in payload
    assert "macd_zero_axis_list" in payload


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
