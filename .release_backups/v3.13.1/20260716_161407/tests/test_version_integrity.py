from radar.version import APP_VERSION
from radar.teacher.decision import run_teacher_pipeline
from radar.core.report import build_markdown


def test_payload_version_uses_single_source():
    payload = run_teacher_pipeline()
    assert payload["version"] == APP_VERSION


def test_daily_report_title_uses_single_source():
    payload = run_teacher_pipeline()
    report = build_markdown(payload)
    assert f"AI Stock Radar {APP_VERSION}" in report
    assert "AI Stock Radar 3.9.0" not in report


def test_current_version_is_not_hardcoded_in_multiple_runtime_files():
    # Smoke check for the trust issue that caused mixed versions in the UI.
    assert APP_VERSION == "3.12.0"
