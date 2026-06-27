"""Watchlist and stock knowledge map for AI Stock Radar."""

WATCHLIST: dict[str, dict] = {
    "2330": {
        "name": "台積電",
        "sector": "半導體製造",
        "yahoo": "2330.TW",
        "base_price": 980,
        "themes": {
            "AI Infrastructure": 1.25,
            "Semiconductor Momentum": 1.15,
            "CoWoS": 1.30,
            "Foundry": 1.20,
            "NVIDIA": 1.25,
            "TSMC ADR": 1.35,
            "Macro Risk": 1.00,
        },
    },
    "2382": {
        "name": "廣達",
        "sector": "AI 伺服器",
        "yahoo": "2382.TW",
        "base_price": 285,
        "themes": {
            "AI Infrastructure": 1.12,
            "AI Server": 1.30,
            "NVIDIA": 1.10,
            "Cloud Capex": 1.20,
            "Macro Risk": 1.00,
        },
    },
    "3231": {
        "name": "緯創",
        "sector": "AI 伺服器",
        "yahoo": "3231.TW",
        "base_price": 115,
        "themes": {
            "AI Infrastructure": 1.10,
            "AI Server": 1.28,
            "NVIDIA": 1.08,
            "Cloud Capex": 1.15,
            "Macro Risk": 1.00,
        },
    },
    "6669": {
        "name": "緯穎",
        "sector": "AI 伺服器",
        "yahoo": "6669.TW",
        "base_price": 2450,
        "themes": {
            "AI Infrastructure": 1.16,
            "AI Server": 1.32,
            "Cloud Capex": 1.28,
            "NVIDIA": 1.10,
            "Macro Risk": 1.10,
        },
    },
    "2449": {
        "name": "京元電子",
        "sector": "半導體測試",
        "yahoo": "2449.TW",
        "base_price": 105,
        "themes": {
            "Semiconductor Momentum": 1.08,
            "NVIDIA": 1.08,
            "AI Infrastructure": 0.95,
            "Testing": 1.30,
            "Macro Risk": 1.00,
        },
    },
    "2454": {
        "name": "聯發科",
        "sector": "IC 設計",
        "yahoo": "2454.TW",
        "base_price": 1320,
        "themes": {
            "Semiconductor Momentum": 1.05,
            "Edge AI": 1.20,
            "Smartphone": 1.20,
            "Macro Risk": 1.10,
        },
    },
    "2308": {
        "name": "台達電",
        "sector": "電源 / 散熱",
        "yahoo": "2308.TW",
        "base_price": 400,
        "themes": {
            "AI Infrastructure": 1.05,
            "AI Server": 1.10,
            "Power": 1.35,
            "Energy Efficiency": 1.25,
            "Macro Risk": 0.95,
        },
    },
    "8299": {
        "name": "群聯",
        "sector": "儲存 / NAND",
        "yahoo": "8299.TWO",
        "base_price": 620,
        "themes": {
            "Storage": 1.35,
            "NAND": 1.30,
            "AI PC": 1.15,
            "Semiconductor Momentum": 0.95,
            "Macro Risk": 1.10,
        },
    },
    "2603": {
        "name": "長榮",
        "sector": "航運",
        "yahoo": "2603.TW",
        "base_price": 190,
        "themes": {
            "Shipping": 1.35,
            "Freight Rate": 1.30,
            "Red Sea Risk": 1.15,
            "Oil Price": 1.05,
            "Macro Risk": 0.90,
        },
    },
}

SIGNAL_ZH: dict[str, str] = {
    "AI Infrastructure": "AI 基礎建設",
    "AI Server": "AI 伺服器",
    "CoWoS": "先進封裝 CoWoS",
    "Semiconductor Momentum": "半導體動能",
    "TSMC ADR": "台積電 ADR",
    "Testing": "半導體測試",
    "Storage": "儲存 / NAND",
    "Power": "電源與散熱",
    "Shipping": "航運",
    "Macro Risk": "總經風險",
    "Market News": "一般市場新聞",
}

SOURCE_ZH: dict[str, str] = {
    "Yahoo Finance": "Yahoo Finance",
    "CNBC Markets": "CNBC 市場",
    "CNBC Technology": "CNBC 科技",
    "Curated Baseline": "內建基準資料",
}

SIGNAL_KEYWORDS: list[tuple[str, list[str], str, list[str]]] = [
    ("AI Infrastructure", ["nvidia", "gpu", "ai chip", "artificial intelligence", "ai infrastructure", "blackwell", "accelerator"], "positive", ["2330", "2382", "3231", "6669", "2449"]),
    ("AI Server", ["ai server", "server", "data center", "datacenter", "cloud capex", "hyperscaler", "cloud spending"], "positive", ["2382", "3231", "6669", "2308"]),
    ("CoWoS", ["cowos", "advanced packaging", "packaging capacity", "tsmc packaging"], "positive", ["2330"]),
    ("Semiconductor Momentum", ["semiconductor", "chip", "sox", "nasdaq", "tsmc", "taiwan semiconductor", "chip stocks"], "positive", ["2330", "2454", "2449", "8299"]),
    ("TSMC ADR", ["tsm adr", "tsmc adr", "taiwan semiconductor adr"], "positive", ["2330"]),
    ("Testing", ["testing", "wafer test", "ic test"], "positive", ["2449"]),
    ("Storage", ["nand", "ssd", "storage", "memory"], "positive", ["8299"]),
    ("Power", ["power supply", "power management", "thermal", "cooling", "energy efficiency"], "positive", ["2308"]),
    ("Shipping", ["shipping", "container", "freight", "bdi", "red sea", "ports"], "positive", ["2603"]),
    ("Macro Risk", ["fed", "rate", "inflation", "yield", "powell", "cpi", "pce", "tariff", "geopolitical", "bond yields"], "negative", ["2330", "2382", "3231", "6669", "2454", "8299"]),
]
