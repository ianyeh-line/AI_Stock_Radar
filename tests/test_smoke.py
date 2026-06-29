from radar.teacher.decision import run_teacher_pipeline
from radar.data.stock_master import resolve_stock


def test_pipeline_runs():
    payload = run_teacher_pipeline()
    assert payload["version"] == "3.0.1"
    assert "buy_list" in payload


def test_stock_master_huatong():
    assert resolve_stock("2313").name == "華通"
    assert resolve_stock("華通").symbol == "2313"


def test_stock_master_nanya_tech():
    assert resolve_stock("2408").name == "南亞科"
    assert resolve_stock("南亞科").symbol == "2408"


def test_custom_fallback_last_resort():
    assert resolve_stock("9999").name == "自訂個股9999"
