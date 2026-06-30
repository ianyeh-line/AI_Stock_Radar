from radar.teacher.decision import run_teacher_pipeline, build_decision_card
from radar.data.stock_master import resolve_stock, register_custom_stock, StockInfo
from radar.core.indicators import macd


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.2.4"
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
