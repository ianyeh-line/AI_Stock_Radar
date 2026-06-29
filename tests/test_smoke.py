from radar.teacher.decision import run_teacher_pipeline
from radar.data.stock_master import resolve_stock


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.0.2"
    assert "buy_list" in payload


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
