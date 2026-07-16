from pathlib import Path

from radar.teacher.decision import run_teacher_pipeline
from radar.version import APP_VERSION, APP_RELEASE_NAME

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def test_safe_patch_version_metadata():
    assert APP_VERSION == "3.13.1"
    assert APP_RELEASE_NAME == "Decision-first SafePatch"


def test_teacher_summary_is_user_facing_not_release_notes():
    payload = run_teacher_pipeline()
    summary = payload.get("teacher_summary", "")
    assert "今天先處理持股風險" in summary
    assert "本版將 UI" not in summary
    assert "籌碼資料基礎檢查" not in summary
    assert "有官方三大法人資料就納入" not in summary


def test_main_page_uses_decision_first_copy():
    assert "更新今日資料" in APP_SOURCE
    assert "今天先做這 3 件事" in APP_SOURCE
    assert "先處理持股風險" in APP_SOURCE
    assert "只看已符合條件的標的" in APP_SOURCE
    assert "不追盤中急拉" in APP_SOURCE
    assert "今日優先清單" in APP_SOURCE


def test_old_developer_copy_not_rendered_in_app():
    forbidden = [
        "本版將 UI",
        "股市老師先給今天怎麼做",
        "資料來源、診斷與版本資訊已移至頁尾",
        "重新產生今日決策資料",
        "籌碼資料基礎檢查",
        "有官方三大法人資料就納入",
    ]
    for text in forbidden:
        assert text not in APP_SOURCE


def test_v312_feature_pages_are_still_present():
    for page in ["今天怎麼做", "今日強勢", "我的持股", "個股研究", "每日報告", "設定"]:
        assert page in APP_SOURCE


def test_v312_runtime_features_are_not_replaced_by_stub_app():
    required_symbols = [
        "run_teacher_pipeline",
        "render_strength_card",
        "render_technical_chart",
        "add_watchlist_ui",
        "add_portfolio_ui",
        "_render_clean_daily_report",
        "check_cloud_connection",
        "render_mini_macd_chart",
    ]
    for symbol in required_symbols:
        assert symbol in APP_SOURCE
