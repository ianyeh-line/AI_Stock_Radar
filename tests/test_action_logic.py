from radar.engine.decision import _entry_text_for_non_buy, _level_context
from radar.models.domain import TechnicalProfile


def test_non_buy_entry_does_not_ask_to_stand_back_above_support_when_price_already_above_support():
    profile = TechnicalProfile(
        symbol="2327",
        name="國巨",
        yahoo_symbol="2327.TW",
        price_source="Yahoo Finance .TW",
        bars_count=160,
        latest_close=1015.0,
        change_pct=1.0,
        ma5=1000.0,
        ma10=990.0,
        ma20=900.0,
        ma60=880.0,
        ma120=850.0,
        volume_ma5=1000,
        volume_ma20=1000,
        bb_upper=1100.0,
        bb_lower=880.0,
        dif=1.0,
        dea=0.5,
        macd_hist=0.5,
        macd_hist_prev=0.3,
        rsi=55.0,
        volume_ratio=1.1,
        trend_score=50,
        risk_score=70,
        ma_state="測試",
        technical_summary="測試",
    )
    levels = {
        "breakout": 1160.0,
        "pullback_low": 890.0,
        "pullback_high": 915.0,
        "reduce": 900.0,
        "stop": 850.0,
    }
    ctx = _level_context(profile, levels)
    text = _entry_text_for_non_buy(ctx, "解除減碼觀點")
    assert "現價 1015.00 已高於支撐區" in text
    assert "需先站回 915.00" not in text
    assert "尚未突破關鍵壓力 1160.00" in text
