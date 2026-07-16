from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.13.1"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def require_file(rel: str) -> None:
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"Missing required file: {rel}")


def main() -> None:
    required_files = [
        "app.py",
        "src/radar/version.py",
        "src/radar/cli.py",
        "src/radar/teacher/decision.py",
        "src/radar/teacher/decision_loop.py",
        "src/radar/teacher/market_strength.py",
        "src/radar/core/report.py",
        "src/radar/core/official_data.py",
        "src/radar/core/chip_data.py",
        "src/radar/data/user_store.py",
        "src/radar/integrations/cloud_user_store.py",
        "tests/test_smoke.py",
        "tests/test_decision_first_safepatch.py",
    ]
    for rel in required_files:
        require_file(rel)

    version_source = read("src/radar/version.py")
    if f'APP_VERSION = "{VERSION}"' not in version_source:
        raise SystemExit("APP_VERSION is not 3.13.1")
    if 'APP_RELEASE_NAME = "Decision-first SafePatch"' not in version_source:
        raise SystemExit("APP_RELEASE_NAME is not Decision-first SafePatch")

    app_source = read("app.py")
    decision_source = read("src/radar/teacher/decision.py")
    forbidden = [
        "本版將 UI",
        "股市老師先給今天怎麼做",
        "資料來源、診斷與版本資訊已移至頁尾",
        "重新產生今日決策資料",
        "籌碼資料基礎檢查",
        "有官方三大法人資料就納入",
    ]
    joined_runtime = app_source + "\n" + decision_source
    for text in forbidden:
        if text in joined_runtime:
            raise SystemExit(f"Forbidden user-facing/developer copy still present: {text}")

    expected_copy = [
        "更新今日資料",
        "今天先做這 3 件事",
        "先處理持股風險",
        "只看已符合條件的標的",
        "不追盤中急拉",
        "今日優先清單",
    ]
    for text in expected_copy:
        if text not in app_source:
            raise SystemExit(f"Missing decision-first copy: {text}")

    expected_pages = ["今天怎麼做", "今日強勢", "我的持股", "個股研究", "每日報告", "設定"]
    for page in expected_pages:
        if page not in app_source:
            raise SystemExit(f"Missing existing page: {page}")

    forbidden_release_files = ["output/daily_report.md", "output/dashboard_data.json"]
    for rel in forbidden_release_files:
        if (ROOT / rel).exists():
            raise SystemExit(f"Release package must not include generated output file: {rel}")

    print("v3.13.1 Decision-first SafePatch validation passed")


if __name__ == "__main__":
    main()
