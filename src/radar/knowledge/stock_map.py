"""Keyword-based knowledge layer for Taiwan stock impact mapping."""

STOCK_KNOWLEDGE = {
    "2330": {
        "name": "台積電",
        "keywords": ["nvidia", "semiconductor", "chip", "ai", "cowos", "tsmc", "foundry", "gpu"],
    },
    "2382": {
        "name": "廣達",
        "keywords": ["ai server", "server", "nvidia", "datacenter", "data center", "cloud"],
    },
    "3231": {
        "name": "緯創",
        "keywords": ["ai server", "server", "nvidia", "datacenter", "data center"],
    },
    "6669": {
        "name": "緯穎",
        "keywords": ["ai server", "server", "datacenter", "data center", "cloud"],
    },
    "2449": {
        "name": "京元電子",
        "keywords": ["semiconductor", "testing", "chip", "ai", "gpu", "nvidia"],
    },
    "2454": {
        "name": "聯發科",
        "keywords": ["semiconductor", "smartphone", "chip", "edge ai", "mobile"],
    },
    "2603": {
        "name": "長榮",
        "keywords": ["shipping", "freight", "container", "red sea", "suez"],
    },
}

POSITIVE_KEYWORDS = ["strong", "higher", "gain", "surge", "demand", "growth", "optimism", "record", "improve"]
NEGATIVE_KEYWORDS = ["cautious", "risk", "inflation", "fed", "rate", "higher yields", "pressure", "decline", "weak"]
