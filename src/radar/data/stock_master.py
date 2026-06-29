"""Taiwan stock master utilities.

v3.0.2 note:
The v3.0 reset accidentally reduced the stock master. v3.0.2 restores a broader
Taiwan stock master and adds regression coverage for user-entered holdings such
as 2313 華通, 2408 南亞科, and 4952 凌通. Unknown numeric symbols keep the
user-provided Chinese name when available instead of falling back to 自訂個股.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


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


def _s(symbol: str, name: str, theme: str = "台股", market: str = "TW") -> StockInfo:
    return StockInfo(symbol=symbol, name=name, market=market, theme=theme)


# Expanded stock master restored from the v2.x Stock Master work.
# It covers AI supply chain, major electronics, financials, shipping, ETFs,
# and frequently user-entered Taiwan stocks. It is intentionally local and
# deterministic so user-entered holdings do not fall back to 自訂個股 too easily.
STOCKS: dict[str, StockInfo] = {
    "0050": _s("0050", "元大台灣50", "ETF"),
    "0056": _s("0056", "元大高股息", "ETF"),
    "00878": _s("00878", "國泰永續高股息", "ETF"),
    "00919": _s("00919", "群益台灣精選高息", "ETF"),
    "1101": _s("1101", "台泥", "水泥"),
    "1102": _s("1102", "亞泥", "水泥"),
    "1216": _s("1216", "統一", "食品"),
    "1301": _s("1301", "台塑", "塑化"),
    "1303": _s("1303", "南亞", "塑化"),
    "1326": _s("1326", "台化", "塑化"),
    "1402": _s("1402", "遠東新", "紡織"),
    "1513": _s("1513", "中興電", "重電"),
    "1560": _s("1560", "中砂", "半導體耗材"),
    "1590": _s("1590", "亞德客-KY", "自動化"),
    "2002": _s("2002", "中鋼", "鋼鐵"),
    "2207": _s("2207", "和泰車", "汽車"),
    "2301": _s("2301", "光寶科", "電子零組件"),
    "2303": _s("2303", "聯電", "晶圓代工"),
    "2308": _s("2308", "台達電", "電源管理"),
    "2313": _s("2313", "華通", "PCB"),
    "2317": _s("2317", "鴻海", "AI伺服器"),
    "2324": _s("2324", "仁寶", "電子代工"),
    "2327": _s("2327", "國巨", "被動元件"),
    "2328": _s("2328", "廣宇", "電子零組件"),
    "2330": _s("2330", "台積電", "半導體"),
    "2337": _s("2337", "旺宏", "記憶體"),
    "2344": _s("2344", "華邦電", "記憶體"),
    "2345": _s("2345", "智邦", "網通"),
    "2353": _s("2353", "宏碁", "PC"),
    "2356": _s("2356", "英業達", "AI伺服器"),
    "2357": _s("2357", "華碩", "PC"),
    "2360": _s("2360", "致茂", "測試設備"),
    "2368": _s("2368", "金像電", "PCB"),
    "2376": _s("2376", "技嘉", "AI伺服器"),
    "2377": _s("2377", "微星", "AI PC"),
    "2379": _s("2379", "瑞昱", "IC設計"),
    "2382": _s("2382", "廣達", "AI伺服器"),
    "2383": _s("2383", "台光電", "PCB"),
    "2392": _s("2392", "正崴", "連接器"),
    "2395": _s("2395", "研華", "工業電腦"),
    "2408": _s("2408", "南亞科", "記憶體"),
    "2409": _s("2409", "友達", "面板"),
    "2401": _s("2401", "凌陽", "IC設計"),
    "2412": _s("2412", "中華電", "電信"),
    "2421": _s("2421", "建準", "散熱"),
    "2449": _s("2449", "京元電子", "測試"),
    "2454": _s("2454", "聯發科", "IC設計"),
    "2458": _s("2458", "義隆", "IC設計"),
    "2436": _s("2436", "偉詮電", "IC設計"),
    "2467": _s("2467", "志聖", "設備"),
    "2474": _s("2474", "可成", "機殼"),
    "2603": _s("2603", "長榮", "航運"),
    "2605": _s("2605", "新興", "航運"),
    "2606": _s("2606", "裕民", "航運"),
    "2609": _s("2609", "陽明", "航運"),
    "2615": _s("2615", "萬海", "航運"),
    "3006": _s("3006", "晶豪科", "記憶體"),
    "3008": _s("3008", "大立光", "光學"),
    "3013": _s("3013", "晟銘電", "機殼"),
    "3017": _s("3017", "奇鋐", "散熱"),
    "3023": _s("3023", "信邦", "連接器"),
    "3034": _s("3034", "聯詠", "IC設計"),
    "3035": _s("3035", "智原", "ASIC"),
    "3037": _s("3037", "欣興", "PCB"),
    "3045": _s("3045", "台灣大", "電信"),
    "3062": _s("3062", "建漢", "網通"),
    "3094": _s("3094", "聯傑", "IC設計", "TWO"),
    "3081": _s("3081", "聯亞", "光通訊", "TWO"),
    "3105": _s("3105", "穩懋", "砷化鎵", "TWO"),
    "3131": _s("3131", "弘塑", "半導體設備", "TWO"),
    "3167": _s("3167", "大量", "PCB設備"),
    "3189": _s("3189", "景碩", "載板"),
    "3227": _s("3227", "原相", "IC設計", "TWO"),
    "3257": _s("3257", "虹冠電", "IC設計", "TWO"),
    "3231": _s("3231", "緯創", "AI伺服器"),
    "3264": _s("3264", "欣銓", "測試", "TWO"),
    "3324": _s("3324", "雙鴻", "散熱", "TWO"),
    "3374": _s("3374", "精材", "封測", "TWO"),
    "3413": _s("3413", "京鼎", "半導體設備"),
    "3443": _s("3443", "創意", "ASIC"),
    "3529": _s("3529", "力旺", "IP", "TWO"),
    "3563": _s("3563", "牧德", "AOI設備"),
    "3588": _s("3588", "通嘉", "IC設計", "TWO"),
    "3583": _s("3583", "辛耘", "半導體設備"),
    "3596": _s("3596", "智易", "網通"),
    "3653": _s("3653", "健策", "散熱"),
    "3661": _s("3661", "世芯-KY", "ASIC"),
    "3665": _s("3665", "貿聯-KY", "連接器"),
    "3680": _s("3680", "家登", "半導體耗材", "TWO"),
    "3711": _s("3711", "日月光投控", "封測"),
    "4763": _s("4763", "材料-KY", "材料"),
    "4904": _s("4904", "遠傳", "電信"),
    "4906": _s("4906", "正文", "網通"),
    "4919": _s("4919", "新唐", "IC設計"),
    "4952": _s("4952", "凌通", "IC設計"),
    "4958": _s("4958", "臻鼎-KY", "PCB"),
    "4966": _s("4966", "譜瑞-KY", "IC設計"),
    "4977": _s("4977", "眾達-KY", "光通訊"),
    "5274": _s("5274", "信驊", "IC設計", "TWO"),
    "5347": _s("5347", "世界", "晶圓代工", "TWO"),
    "5388": _s("5388", "中磊", "網通"),
    "5469": _s("5469", "瀚宇博", "PCB"),
    "5471": _s("5471", "松翰", "IC設計", "TWO"),
    "5871": _s("5871", "中租-KY", "金融服務"),
    "5876": _s("5876", "上海商銀", "金融"),
    "5880": _s("5880", "合庫金", "金融"),
    "6121": _s("6121", "新普", "電池", "TWO"),
    "6153": _s("6153", "嘉聯益", "PCB"),
    "6187": _s("6187", "萬潤", "半導體設備", "TWO"),
    "6191": _s("6191", "精成科", "PCB"),
    "6196": _s("6196", "帆宣", "設備工程"),
    "6202": _s("6202", "盛群", "IC設計"),
    "6213": _s("6213", "聯茂", "PCB"),
    "6217": _s("6217", "中探針", "測試", "TWO"),
    "6230": _s("6230", "超眾", "散熱"),
    "6239": _s("6239", "力成", "封測"),
    "6257": _s("6257", "矽格", "測試"),
    "6271": _s("6271", "同欣電", "封測"),
    "6278": _s("6278", "台表科", "SMT"),
    "6285": _s("6285", "啟碁", "網通"),
    "6412": _s("6412", "群電", "電源"),
    "6415": _s("6415", "矽力*-KY", "IC設計"),
    "6438": _s("6438", "迅得", "自動化設備"),
    "6485": _s("6485", "點序", "記憶體控制", "TWO"),
    "6488": _s("6488", "環球晶", "矽晶圓", "TWO"),
    "6505": _s("6505", "台塑化", "塑化"),
    "6515": _s("6515", "穎崴", "測試介面"),
    "6531": _s("6531", "愛普*", "記憶體"),
    "6538": _s("6538", "倉和", "半導體耗材", "TWO"),
    "6552": _s("6552", "易華電", "IC設計"),
    "6669": _s("6669", "緯穎", "AI伺服器"),
    "6672": _s("6672", "騰輝電子-KY", "PCB"),
    "6695": _s("6695", "芯鼎", "IC設計"),
    "6756": _s("6756", "威鋒電子", "IC設計"),
    "6770": _s("6770", "力積電", "晶圓代工"),
    "8046": _s("8046", "南電", "載板"),
    "8016": _s("8016", "矽創", "IC設計"),
    "8050": _s("8050", "廣積", "工業電腦", "TWO"),
    "8213": _s("8213", "志超", "PCB"),
    "8299": _s("8299", "群聯", "記憶體控制", "TWO"),
    "8358": _s("8358", "金居", "銅箔基板", "TWO"),
    "8996": _s("8996", "高力", "散熱"),
    "9910": _s("9910", "豐泰", "製鞋"),
}


def _normalize_name(text: str) -> str:
    return (text or "").strip().replace(" ", "").replace("　", "").upper()


def _extract_symbol(text: str) -> str:
    match = re.search(r"\d{4}", (text or ""))
    return match.group(0) if match else ""


NAME_TO_SYMBOL: dict[str, str] = {}
for symbol, stock in STOCKS.items():
    NAME_TO_SYMBOL[_normalize_name(stock.name)] = symbol
    NAME_TO_SYMBOL[_normalize_name(stock.label)] = symbol

ALIASES: dict[str, str] = {
    "台灣50": "0050",
    "永續高股息": "00878",
    "世芯": "3661",
    "中租": "5871",
    "愛普": "6531",
    "材料": "4763",
    "矽力": "6415",
    "南亞科": "2408",
    "華通": "2313",
    "國巨": "2327",
    "凌通": "4952",
    "新唐": "4919",
    "凌陽": "2401",
    "偉詮電": "2436",
    "松翰": "5471",
    "盛群": "6202",
    "矽創": "8016",
    "聯傑": "3094",
    "通嘉": "3588",
    "芯鼎": "6695",
}
for alias, symbol in ALIASES.items():
    NAME_TO_SYMBOL[_normalize_name(alias)] = symbol


def resolve_stock(text: str) -> StockInfo:
    """Resolve input text to StockInfo. Supports symbol, name, alias, or 'symbol name'."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("請輸入股號或股票名稱")

    symbol = _extract_symbol(raw)
    if symbol and symbol in STOCKS:
        return STOCKS[symbol]

    normalized = _normalize_name(raw)
    if normalized in NAME_TO_SYMBOL:
        return STOCKS[NAME_TO_SYMBOL[normalized]]

    for name_key, code in NAME_TO_SYMBOL.items():
        if normalized and (normalized in name_key or name_key in normalized):
            return STOCKS[code]

    if symbol:
        supplied_name = re.sub(r"\d{4}", "", raw).strip().replace(" ", "").replace("　", "")
        if supplied_name:
            return StockInfo(symbol, supplied_name, "TW", "自訂")
        return StockInfo(symbol, f"自訂個股{symbol}", "TW", "自訂")
    raise ValueError(f"找不到個股：{text}")


def ai_universe() -> list[StockInfo]:
    """Core universe used by Teacher Mode.

    Keep this broad enough for Taiwan AI supply chain but not too large for local runs.
    User watchlist / portfolio can still analyze stocks outside this universe through
    resolve_stock().
    """
    core_symbols = [
        "2330", "2317", "2382", "3231", "6669", "2327", "2313", "2408", "3037", "8046",
        "2449", "2454", "2379", "2603", "2308", "8299", "3324", "3017", "6257", "3711",
        "6213", "6121", "2368", "2383", "4958", "5469", "8050", "8213", "8358", "2356",
        "2376", "2377", "2345", "3034", "3661", "3443", "5274", "6239", "6230", "3653",
    ]
    return [STOCKS[s] for s in core_symbols if s in STOCKS]

# v3.1.0 dynamic stock support -------------------------------------------------
# Keep these definitions at the end so they override the earlier v3.0.x resolver.
import json
from pathlib import Path

CUSTOM_STOCK_PATH = Path.home() / ".ai_stock_radar" / "custom_stocks.json"


def _load_custom_stock_map() -> dict[str, StockInfo]:
    if not CUSTOM_STOCK_PATH.exists():
        return {}
    try:
        rows = json.loads(CUSTOM_STOCK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, StockInfo] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip()
        name = str(row.get("name", "")).strip()
        market = str(row.get("market", "TW")).strip() or "TW"
        theme = str(row.get("theme", "自動新增")).strip() or "自動新增"
        if re.fullmatch(r"\d{4}", symbol) and name:
            out[symbol] = StockInfo(symbol=symbol, name=name, market=market, theme=theme)
    return out


def _save_custom_stock_map(data: dict[str, StockInfo]) -> None:
    CUSTOM_STOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"symbol": s.symbol, "name": s.name, "market": s.market, "theme": s.theme}
        for s in sorted(data.values(), key=lambda x: x.symbol)
    ]
    CUSTOM_STOCK_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def register_custom_stock(stock: StockInfo) -> StockInfo:
    """Persist user/discovered stock metadata outside the repository.

    This prevents release upgrades from deleting user-added stocks.
    """
    if stock.symbol in STOCKS:
        return STOCKS[stock.symbol]
    data = _load_custom_stock_map()
    existing = data.get(stock.symbol)
    if existing and not existing.name.startswith(("待識別", "自訂個股")):
        return existing
    data[stock.symbol] = stock
    _save_custom_stock_map(data)
    return stock


def _custom_name_to_symbol() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for symbol, stock in _load_custom_stock_map().items():
        mapping[_normalize_name(stock.name)] = symbol
        mapping[_normalize_name(stock.label)] = symbol
    return mapping


def resolve_stock(text: str) -> StockInfo:  # type: ignore[no-redef]
    """Resolve input text to StockInfo.

    Supports:
    - Built-in stock master: 2330 / 台積電 / 2330 台積電
    - User-added custom stocks stored in ~/.ai_stock_radar/custom_stocks.json
    - Unknown numeric Taiwan stocks: creates a dynamic stock candidate so price
      data can be fetched automatically and then registered with a better name
      if Yahoo returns one.
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("請輸入股號或股票名稱")

    symbol = _extract_symbol(raw)
    supplied_name = re.sub(r"\d{4}", "", raw).strip().replace(" ", "").replace("　", "") if symbol else ""

    if symbol and symbol in STOCKS:
        return STOCKS[symbol]

    custom = _load_custom_stock_map()
    if symbol and symbol in custom:
        return custom[symbol]

    normalized = _normalize_name(raw)
    custom_names = _custom_name_to_symbol()
    if normalized in custom_names:
        return custom[custom_names[normalized]]

    if normalized in NAME_TO_SYMBOL:
        return STOCKS[NAME_TO_SYMBOL[normalized]]

    for name_key, code in {**NAME_TO_SYMBOL, **custom_names}.items():
        if normalized and (normalized in name_key or name_key in normalized):
            return STOCKS.get(code) or custom[code]

    if symbol:
        # For unknown codes, do not block the user. Create a candidate; market_data
        # will try .TW and .TWO, then update the label if Yahoo returns metadata.
        name = supplied_name or f"待識別{symbol}"
        stock = StockInfo(symbol, name, "TW", "自動新增")
        if supplied_name:
            register_custom_stock(stock)
        return stock

    raise ValueError(f"找不到個股：{text}。清單外個股請輸入股號，或輸入『股號 股票名稱』。")
