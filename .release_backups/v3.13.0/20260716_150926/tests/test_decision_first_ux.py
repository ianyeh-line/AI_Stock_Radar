from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from radar.ui.decision_copy_guard import (
    APP_VERSION,
    BANNED_MAIN_COPY,
    assert_clean_main_copy,
    check_main_copy,
    find_banned_main_copy,
    sanitize_user_facing_copy,
)
from radar.ui.decision_data_adapter import (
    CATEGORY_ACTIONABLE,
    CATEGORY_HOLDING,
    CATEGORY_RISK,
    CATEGORY_WAIT,
    CATEGORY_WATCH,
    build_dashboard_view,
    derive_summary,
    normalize_decision_rows,
    normalize_row,
)
from radar.ui.decision_first_home import KPI_CARDS, TODAY_ACTIONS, validate_static_main_copy


@pytest.mark.parametrize("phrase", BANNED_MAIN_COPY)
def test_banned_main_copy_is_detected(phrase):
    assert phrase in find_banned_main_copy(f"主畫面不應出現：{phrase}")


def test_assert_clean_main_copy_allows_decision_copy():
    assert_clean_main_copy("今天只做有價格條件的低接或突破確認，盤中急拉不追。")


def test_assert_clean_main_copy_rejects_old_today_copy():
    with pytest.raises(ValueError):
        assert_clean_main_copy("股市老師先給今天怎麼做；本版將 UI 收斂成四個核心頁。")


@pytest.mark.parametrize(
    "source, expected",
    [
        ("重新產生今日決策資料", "更新今日資料"),
        ("測試 Supabase 連線", "資料庫連線檢查"),
        ("Responsive Decision UX", "今日決策"),
        ("資料來源、診斷與版本資訊已移至頁尾", "先處理持股風險，再看今日可操作清單"),
    ],
)
def test_sanitize_user_facing_copy_known_replacements(source, expected):
    assert sanitize_user_facing_copy(source) == expected


def test_sanitize_user_facing_copy_uses_fallback_for_remaining_banned_text():
    assert sanitize_user_facing_copy("有官方三大法人資料就納入", "乾淨文案") == "乾淨文案"


def test_static_main_copy_has_no_forbidden_terms():
    validate_static_main_copy()


def test_today_action_copy_is_user_facing():
    text = " ".join(item["title"] + item["body"] for item in TODAY_ACTIONS)
    assert check_main_copy(text).clean is True
    assert "本版" not in text
    assert "先處理持股風險" in text


def test_kpi_copy_is_user_facing():
    text = " ".join(label + hint for label, _, hint in KPI_CARDS)
    assert check_main_copy(text).clean is True
    assert "今日可操作" in text
    assert "風險線" in text


def test_version_is_3130():
    assert APP_VERSION == "v3.13.0"


def test_normalize_row_composes_stock_name_from_symbol_name():
    row = normalize_row({"symbol": "2330", "name": "台積電", "suggestion": "拉回低接"})
    assert row["stock"] == "2330 台積電"


@pytest.mark.parametrize(
    "item, expected",
    [
        ({"category": "今日可操作", "suggestion": "拉回低接"}, CATEGORY_ACTIONABLE),
        ({"suggestion": "等突破確認"}, CATEGORY_WAIT),
        ({"suggestion": "強勢觀察"}, CATEGORY_WATCH),
        ({"suggestion": "不追高，先控風險"}, CATEGORY_RISK),
        ({"category": "我的持股", "suggestion": "續抱觀察"}, CATEGORY_HOLDING),
    ],
)
def test_normalize_row_infers_category(item, expected):
    item = {"symbol": "TEST", **item}
    assert normalize_row(item)["category"] == expected


def test_normalize_row_uses_safe_defaults():
    row = normalize_row({"symbol": "TEST"})
    assert row["suggestion"] == "等待條件"
    assert row["trigger"] == "等價格條件成立"
    assert row["risk_line"] == "跌破風險線減碼"


def test_normalize_row_translates_missing_chip_status():
    row = normalize_row({"symbol": "TEST", "has_official_chip_data": False})
    assert row["data_status"] == "籌碼資料不足"


def test_normalize_row_marks_complete_data():
    row = normalize_row({"symbol": "TEST", "has_official_chip_data": True})
    assert row["data_status"] == "資料完整"


def test_normalize_rows_from_actionable_section():
    rows = normalize_decision_rows({"actionable": [{"symbol": "2330", "name": "台積電", "suggestion": "拉回低接"}]})
    assert len(rows) == 1
    assert rows[0]["category"] == CATEGORY_ACTIONABLE


def test_normalize_rows_from_chinese_section():
    rows = normalize_decision_rows({"強勢觀察": [{"股票": "2382 廣達", "今日建議": "等突破確認"}]})
    assert rows[0]["stock"] == "2382 廣達"
    assert rows[0]["category"] == CATEGORY_WATCH


def test_normalize_rows_deduplicates_same_stock_category_suggestion():
    payload = {
        "decision_rows": [{"symbol": "2330", "name": "台積電", "suggestion": "拉回低接"}],
        "actionable": [{"symbol": "2330", "name": "台積電", "suggestion": "拉回低接"}],
    }
    assert len(normalize_decision_rows(payload)) == 1


def test_derive_summary_counts_rows():
    rows = normalize_decision_rows(
        {
            "actionable": [{"symbol": "A", "suggestion": "拉回低接"}],
            "risk": [{"symbol": "B", "suggestion": "不追高"}],
        }
    )
    summary = derive_summary(rows, {})
    assert summary["actionable"] == 1
    assert summary["risk"] == 1


def test_derive_summary_respects_explicit_counts():
    rows = []
    summary = derive_summary(rows, {"summary": {"actionable_count": 3, "watch_count": 2}})
    assert summary["actionable"] == 3
    assert summary["watch"] == 2


def test_build_dashboard_view_defaults_are_clean():
    view = build_dashboard_view({})
    assert view["market_state"] == "偏多但不追高"
    assert check_main_copy(view["market_guidance"]).clean is True


def test_build_dashboard_view_sanitizes_bad_market_guidance():
    view = build_dashboard_view({"market_guidance": "資料來源、診斷與版本資訊已移至頁尾"})
    assert view["market_guidance"] == "先處理持股風險，再看今日可操作清單"


def test_build_dashboard_view_splits_actionable_rows():
    view = build_dashboard_view({"actionable": [{"symbol": "2330", "name": "台積電", "suggestion": "拉回低接"}]})
    assert len(view["actionable_rows"]) == 1
    assert view["summary"]["actionable"] == 1


def test_build_dashboard_view_splits_risk_rows():
    view = build_dashboard_view({"risk": [{"symbol": "3231", "name": "緯創", "suggestion": "不追高"}]})
    assert len(view["risk_rows"]) == 1
    assert view["summary"]["risk"] == 1


def test_build_dashboard_view_splits_holding_rows():
    view = build_dashboard_view({"holdings": [{"symbol": "2454", "name": "聯發科", "suggestion": "續抱觀察"}]})
    assert len(view["holding_rows"]) == 1


def test_build_dashboard_view_keeps_diagnostics_out_of_main_rows():
    view = build_dashboard_view({"diagnostics": {"official_chip_status": "部分股票有三大法人資料"}})
    assert view["diagnostics"]["official_chip_status"] == "部分股票有三大法人資料"
    assert view["decision_rows"] == []


def test_old_today_copy_is_explicitly_rejected():
    old_copy = "股市老師先給今天怎麼做；本版將 UI 收斂成四個核心頁，並加入籌碼資料基礎檢查：有官方三大法人資料就納入，沒有就明確說明不以籌碼面加分。"
    result = check_main_copy(old_copy)
    assert result.clean is False
    assert "本版將 UI" in result.banned_terms
    assert "籌碼資料基礎檢查" in result.banned_terms


@pytest.mark.parametrize("label", ["今天怎麼做", "今日可操作", "我的持股", "風險清單", "個股研究", "每日報告"])
def test_navigation_labels_are_clean(label):
    assert_clean_main_copy(label)
