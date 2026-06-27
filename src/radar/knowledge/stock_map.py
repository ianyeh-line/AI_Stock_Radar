"""Taiwan stock knowledge mapping for MVP decision support."""

STOCK_THEMES: dict[str, list[str]] = {
    "2330 台積電": ["Semiconductor", "CoWoS", "AI Infrastructure"],
    "3231 緯創": ["AI Server", "AI Infrastructure"],
    "6669 緯穎": ["AI Server", "High Valuation Tech"],
    "2382 廣達": ["AI Server", "AI Infrastructure"],
    "2454 聯發科": ["IC Design", "Semiconductor", "High Valuation Tech"],
    "2449 京元電子": ["Semiconductor", "Testing"],
    "2603 長榮": ["Shipping"],
}

WATCHLIST: list[str] = list(STOCK_THEMES.keys())
