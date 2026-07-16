"""Validation script for v3.13.0 Decision-first UX release."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from radar.ui.decision_copy_guard import assert_clean_main_copy, find_banned_main_copy
from radar.ui.decision_data_adapter import build_dashboard_view
from radar.ui.decision_first_home import TODAY_ACTIONS, validate_static_main_copy


def main() -> int:
    validate_static_main_copy()
    bad_today = "股市老師先給今天怎麼做；本版將 UI 收斂成四個核心頁，並加入籌碼資料基礎檢查：有官方三大法人資料就納入，沒有就明確說明不以籌碼面加分。"
    if not find_banned_main_copy(bad_today):
        raise AssertionError("copy guard failed to detect old engineering copy")

    view = build_dashboard_view(
        {
            "market_state": "偏多但不追高",
            "actionable": [
                {
                    "symbol": "2330",
                    "name": "台積電",
                    "suggestion": "拉回低接",
                    "trigger": "回到買進區才分批",
                    "risk_line": "跌破風險線減碼",
                    "reason": "趨勢仍強，但不追盤中急拉",
                    "has_official_chip_data": True,
                }
            ],
        }
    )
    assert view["summary"]["actionable"] == 1
    assert view["decision_rows"][0]["stock"] == "2330 台積電"
    assert_clean_main_copy(" ".join(item["title"] + item["body"] for item in TODAY_ACTIONS))
    print("v3.13.0 Decision-first UX validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
