"""Stock universe and theme mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from radar.engine.user_space import load_portfolio, load_user_watchlist, make_custom_stock, normalize_symbol
from radar.knowledge.stock_master import get_stock_identity
from radar.models.domain import StockMeta

# Lightweight local alias table so users can add common Taiwan stocks by name.
# This does not expand the default Radar universe; it only resolves user input.
TW_STOCK_ALIASES: dict[str, tuple[str, str]] = {
    "台積電": ("2330", "台積電"),
    "聯發科": ("2454", "聯發科"),
    "台達電": ("2308", "台達電"),
    "鴻海": ("2317", "鴻海"),
    "廣達": ("2382", "廣達"),
    "緯創": ("3231", "緯創"),
    "緯穎": ("6669", "緯穎"),
    "京元電子": ("2449", "京元電子"),
    "群聯": ("8299", "群聯"),
    "奇鋐": ("3017", "奇鋐"),
    "世芯": ("3661", "世芯-KY"),
    "世芯-KY": ("3661", "世芯-KY"),
    "台泥": ("1101", "台泥"),
    "亞泥": ("1102", "亞泥"),
    "統一": ("1216", "統一"),
    "台塑": ("1301", "台塑"),
    "南亞": ("1303", "南亞"),
    "台化": ("1326", "台化"),
    "遠東新": ("1402", "遠東新"),
    "中鋼": ("2002", "中鋼"),
    "和泰車": ("2207", "和泰車"),
    "光寶科": ("2301", "光寶科"),
    "聯電": ("2303", "聯電"),
    "仁寶": ("2324", "仁寶"),
    "國巨": ("2327", "國巨"),
    "智邦": ("2345", "智邦"),
    "宏碁": ("2353", "宏碁"),
    "英業達": ("2356", "英業達"),
    "華碩": ("2357", "華碩"),
    "瑞昱": ("2379", "瑞昱"),
    "技嘉": ("2376", "技嘉"),
    "微星": ("2377", "微星"),
    "研華": ("2395", "研華"),
    "南亞科": ("2408", "南亞科"),
    "中華電": ("2412", "中華電"),
    "可成": ("2474", "可成"),
    "長榮": ("2603", "長榮"),
    "新興": ("2605", "新興"),
    "裕民": ("2606", "裕民"),
    "陽明": ("2609", "陽明"),
    "萬海": ("2615", "萬海"),
    "大立光": ("3008", "大立光"),
    "聯詠": ("3034", "聯詠"),
    "欣興": ("3037", "欣興"),
    "台灣大": ("3045", "台灣大"),
    "創意": ("3443", "創意"),
    "日月光投控": ("3711", "日月光投控"),
    "遠傳": ("4904", "遠傳"),
    "中租": ("5871", "中租-KY"),
    "中租-KY": ("5871", "中租-KY"),
    "上海商銀": ("5876", "上海商銀"),
    "合庫金": ("5880", "合庫金"),
    "台塑化": ("6505", "台塑化"),
    "南電": ("8046", "南電"),
    "豐泰": ("9910", "豐泰"),
    "元大台灣50": ("0050", "元大台灣50"),
    "台灣50": ("0050", "元大台灣50"),
    "國泰永續高股息": ("00878", "國泰永續高股息"),
}


def load_base_universe(path: Union[str, Path] = "data/universe/taiwan_watchlist.json") -> list[StockMeta]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [StockMeta(**item) for item in raw]


def load_stock_universe(path: Union[str, Path] = "data/universe/taiwan_watchlist.json", include_user: bool = True) -> list[StockMeta]:
    stocks = load_base_universe(path)
    if not include_user:
        return stocks
    by_symbol = {stock.symbol: stock for stock in stocks}
    personal_items = load_user_watchlist() + load_portfolio()
    for item in personal_items:
        symbol = normalize_symbol(str(item.get("symbol", "")))
        if not symbol or symbol in by_symbol:
            continue
        by_symbol[symbol] = make_custom_stock(symbol, item.get("name"))
    return list(by_symbol.values())


def stock_lookup() -> dict[str, StockMeta]:
    return {stock.symbol: stock for stock in load_stock_universe()}


def lookup_by_display_name() -> dict[str, StockMeta]:
    return {stock.display_name: stock for stock in load_stock_universe()}


def normalize_stock_symbol(text: str) -> str:
    return normalize_symbol(text.split()[0].strip())


def _normalize_name(text: str) -> str:
    return text.strip().replace(" ", "").replace("　", "").upper()


def _resolve_alias(text: str) -> Optional[StockMeta]:
    identity = get_stock_identity(text)
    if identity:
        return make_custom_stock(identity.symbol, identity.name)
    normalized_text = _normalize_name(text)
    for alias, (symbol, name) in TW_STOCK_ALIASES.items():
        normalized_alias = _normalize_name(alias)
        normalized_name = _normalize_name(name)
        if normalized_text in {normalized_alias, normalized_name} or normalized_text in normalized_alias or normalized_text in normalized_name:
            return make_custom_stock(symbol, name)
    return None


def resolve_stock_query(query: str) -> Optional[StockMeta]:
    text = query.strip()
    if not text:
        return None
    symbol = normalize_symbol(text)
    normalized_text = _normalize_name(text)
    for stock in load_stock_universe(include_user=True):
        normalized_name = _normalize_name(stock.name)
        normalized_display = _normalize_name(stock.display_name)
        if stock.symbol == symbol or normalized_text in {normalized_name, normalized_display} or normalized_text in normalized_name:
            return stock
    alias_stock = _resolve_alias(text)
    if alias_stock:
        return alias_stock
    if symbol.isdigit() and len(symbol) == 4:
        return make_custom_stock(symbol)
    return None
