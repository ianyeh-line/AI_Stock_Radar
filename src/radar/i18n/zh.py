"""Chinese labels and lightweight market-news localization utilities."""

from __future__ import annotations

SOURCE_ZH = {
    "Yahoo Finance": "雅虎財經",
    "CNBC Markets": "CNBC 市場",
    "CNBC Technology": "CNBC 科技",
    "Curated Baseline": "精選基準新聞",
    "RSS Live": "即時 RSS 新聞",
    "RSS Live + Curated Baseline": "即時 RSS + 精選基準新聞",
}

SIGNAL_ZH = {
    "AI Infrastructure": "AI 基礎建設",
    "AI Server": "AI 伺服器",
    "CoWoS": "CoWoS 先進封裝",
    "Semiconductor Momentum": "半導體動能",
    "TSMC ADR": "台積電 ADR",
    "Testing": "半導體測試",
    "Storage": "儲存與 NAND",
    "Power": "電源與散熱",
    "Shipping": "航運與運價",
    "Macro Risk": "總經風險",
    "Market News": "市場新聞",
}

SENTIMENT_ZH = {
    "positive": "正向",
    "negative": "負向",
    "neutral": "中性",
}

_STOCK_NAME = {
    "2330": "台積電",
    "2382": "廣達",
    "3231": "緯創",
    "6669": "緯穎",
    "2449": "京元電子",
    "2454": "聯發科",
    "2308": "台達電",
    "8299": "群聯",
    "2603": "長榮",
}

_REPLACEMENTS = [
    ("Nvidia", "輝達"),
    ("NVIDIA", "輝達"),
    ("AI", "AI"),
    ("artificial intelligence", "人工智慧"),
    ("Artificial Intelligence", "人工智慧"),
    ("GPU", "GPU"),
    ("GPUs", "GPU"),
    ("semiconductor", "半導體"),
    ("Semiconductor", "半導體"),
    ("chip", "晶片"),
    ("chips", "晶片"),
    ("TSMC", "台積電"),
    ("Taiwan Semiconductor", "台積電"),
    ("Fed", "Fed"),
    ("Federal Reserve", "Fed"),
    ("inflation", "通膨"),
    ("rate", "利率"),
    ("rates", "利率"),
    ("Powell", "鮑爾"),
    ("market", "市場"),
    ("markets", "市場"),
    ("stock", "股票"),
    ("stocks", "股票"),
    ("earnings", "財報"),
    ("revenue", "營收"),
    ("data center", "資料中心"),
    ("datacenter", "資料中心"),
    ("server", "伺服器"),
    ("cloud", "雲端"),
    ("shipping", "航運"),
    ("freight", "運價"),
]


def source_zh(source: str) -> str:
    return SOURCE_ZH.get(source, source)


def signal_zh(signal: str) -> str:
    return SIGNAL_ZH.get(signal, signal)


def sentiment_zh(sentiment: str) -> str:
    return SENTIMENT_ZH.get(sentiment, sentiment)


def stock_label(ticker: str) -> str:
    name = _STOCK_NAME.get(ticker, "")
    return f"{ticker} {name}" if name else ticker


def localize_news_title(title: str, signal: str, sentiment: str, tickers: list[str]) -> str:
    """Create a Chinese product-facing news title.

    This is not a full machine translation system. For v0.8.0 it converts live RSS
    titles into a Chinese decision headline and keeps the original title available
    in the detail view. The output is intentionally action-oriented.
    """

    signal_name = signal_zh(signal)
    sentiment_name = sentiment_zh(sentiment)
    stocks = "、".join(stock_label(ticker) for ticker in tickers[:4])

    if signal == "AI Infrastructure":
        base = "AI 基礎建設新聞升溫，可能支撐半導體與 AI 伺服器供應鏈"
    elif signal == "AI Server":
        base = "AI 伺服器與雲端資本支出相關新聞，可能影響伺服器供應鏈"
    elif signal == "CoWoS":
        base = "CoWoS 先進封裝需求相關新聞，台積電受影響程度較高"
    elif signal == "Semiconductor Momentum":
        base = "半導體產業動能新聞，可能影響台股電子權值與晶片供應鏈"
    elif signal == "TSMC ADR":
        base = "台積電 ADR 或海外半導體情緒變化，可能牽動台積電開盤表現"
    elif signal == "Macro Risk":
        base = "Fed、利率或通膨相關新聞，可能壓抑高估值科技股風險偏好"
    elif signal == "Shipping":
        base = "航運與運價相關新聞，可能影響航運族群短線表現"
    elif signal == "Power":
        base = "電源、散熱與能源效率相關新聞，可能影響 AI 伺服器零組件"
    elif signal == "Storage":
        base = "儲存與 NAND 相關新聞，可能影響記憶體與控制晶片族群"
    elif signal == "Testing":
        base = "半導體測試相關新聞，可能影響測試供應鏈"
    else:
        translated = title
        for src, dst in _REPLACEMENTS:
            translated = translated.replace(src, dst)
        base = f"全球市場新聞：{translated}"

    if stocks:
        return f"{base}；關注個股：{stocks}（{sentiment_name}）"
    return f"{base}（{signal_name}，{sentiment_name}）"


def localize_news_summary(summary: str, signal: str, sentiment: str, tickers: list[str]) -> str:
    stocks = "、".join(stock_label(ticker) for ticker in tickers[:5]) or "大盤與相關族群"
    direction = "偏多" if sentiment == "positive" else "偏空" if sentiment == "negative" else "中性"
    return f"AI 判讀：此新聞屬於「{signal_zh(signal)}」訊號，方向為{direction}，主要影響 {stocks}。"
