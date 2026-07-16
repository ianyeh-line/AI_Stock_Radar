from radar.teacher.market_strength import MarketRow, build_market_strength_payload
from radar.data.stock_master import StockInfo


def _card(symbol: str, name: str, change_pct: float = 4.0, volume_ratio: float = 1.8):
    close = 100.0
    return {
        "symbol": symbol,
        "name": name,
        "label": f"{symbol} {name}",
        "decision": "波段觀察",
        "grade": "B",
        "score": 70,
        "data_trust": {"actionable": True},
        "prices": [{"date": f"2026-06-{i:02d}", "high": 90 + i, "close": 88 + i, "volume": 1000+i} for i in range(1, 25)],
        "tech": {
            "close": close,
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "rsi": 60,
            "ma20": 92,
            "ma60": 88,
            "breakout": 98,
            "macd": {"zero_axis_status": "0軸上方延續"},
        },
    }


def test_market_strength_uses_full_market_rows(monkeypatch):
    rows = [
        MarketRow("9991", "測試強勢", "TW", "TWSE OpenAPI", 100, 5, 5.26, 96, 102, 95, 100000, 10000000),
        MarketRow("9992", "測試漲停", "TW", "TWSE OpenAPI", 50, 4.5, 9.89, 47, 50, 46, 200000, 10000000),
    ]
    monkeypatch.setattr("radar.teacher.market_strength.fetch_market_snapshot", lambda: {"rows": rows, "total": 2, "errors": [], "sources": ["TWSE OpenAPI"]})

    def build_card(stock: StockInfo):
        return _card(stock.symbol, stock.name, change_pct=5.26 if stock.symbol == "9991" else 9.89)

    payload = build_market_strength_payload([], {}, build_card)
    assert payload["data_coverage"]["mode"] == "full_market_scan"
    assert payload["data_coverage"]["total_market_rows"] == 2
    assert payload["ranking_tables"]["top_gainers"][0]["symbol"] == "9992"
    assert payload["limit_watch"][0]["symbol"] == "9992"
    assert any(row["symbol"] == "9991" for row in payload["strong_list"])
