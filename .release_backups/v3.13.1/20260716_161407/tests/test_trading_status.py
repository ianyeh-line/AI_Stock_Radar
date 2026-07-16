from datetime import datetime, timezone

from radar.teacher.decision import trading_status


def test_streamlit_cloud_utc_after_hours_maps_to_taiwan_after_hours():
    # 2026-06-29 12:25 UTC = 2026-06-29 20:25 Asia/Taipei.
    status = trading_status(datetime(2026, 6, 29, 12, 25, tzinfo=timezone.utc))
    assert status["date"] == "2026-06-29"
    assert status["time"] == "20:25"
    assert status["session"] == "盤後"


def test_taiwan_market_hours_intraday():
    status = trading_status(datetime(2026, 6, 29, 10, 0))
    assert status["session"] == "盤中"
