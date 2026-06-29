"""Taiwan stock master utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockInfo:
    symbol: str
    name: str
    market: str = "TW"
    theme: str = "台股"

    @property
    def label(self) -> str:
        return f"{self.symbol} {self.name}"

    @property
    def yahoo_symbol(self) -> str:
        suffix = ".TWO" if self.market == "TWO" else ".TW"
        return f"{self.symbol}{suffix}"


STOCKS: dict[str, StockInfo] = {
    "2330": StockInfo("2330", "台積電", "TW", "半導體"),
    "2317": StockInfo("2317", "鴻海", "TW", "AI伺服器"),
    "2382": StockInfo("2382", "廣達", "TW", "AI伺服器"),
    "3231": StockInfo("3231", "緯創", "TW", "AI伺服器"),
    "6669": StockInfo("6669", "緯穎", "TW", "AI伺服器"),
    "2327": StockInfo("2327", "國巨", "TW", "被動元件"),
    "2313": StockInfo("2313", "華通", "TW", "PCB"),
    "3037": StockInfo("3037", "欣興", "TW", "PCB"),
    "8046": StockInfo("8046", "南電", "TW", "ABF"),
    "2449": StockInfo("2449", "京元電子", "TW", "測試"),
    "2454": StockInfo("2454", "聯發科", "TW", "IC設計"),
    "2379": StockInfo("2379", "瑞昱", "TW", "IC設計"),
    "2603": StockInfo("2603", "長榮", "TW", "航運"),
    "2308": StockInfo("2308", "台達電", "TW", "電源/AI"),
    "8299": StockInfo("8299", "群聯", "TWO", "儲存"),
    "3324": StockInfo("3324", "雙鴻", "TWO", "散熱"),
    "3017": StockInfo("3017", "奇鋐", "TW", "散熱"),
    "6257": StockInfo("6257", "矽格", "TW", "測試"),
    "3711": StockInfo("3711", "日月光投控", "TW", "封測"),
    "6213": StockInfo("6213", "聯茂", "TW", "CCL"),
    "6121": StockInfo("6121", "新普", "TW", "電池"),
}

NAME_TO_SYMBOL = {stock.name: symbol for symbol, stock in STOCKS.items()}


def resolve_stock(text: str) -> StockInfo:
    """Resolve input text to StockInfo. Supports symbol, name, or 'symbol name'."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("請輸入股號或股票名稱")
    symbol = "".join(ch for ch in raw if ch.isdigit())[:4]
    if symbol and symbol in STOCKS:
        return STOCKS[symbol]
    if raw in NAME_TO_SYMBOL:
        return STOCKS[NAME_TO_SYMBOL[raw]]
    for name, code in NAME_TO_SYMBOL.items():
        if name in raw:
            return STOCKS[code]
    if symbol:
        return StockInfo(symbol, "自訂個股", "TW", "自訂")
    raise ValueError(f"找不到個股：{text}")


def ai_universe() -> list[StockInfo]:
    return list(STOCKS.values())
