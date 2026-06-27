"""Taiwan stock master and symbol/name resolver.

This module is intentionally independent from user_space and stock_map so both
can use the same authoritative local mapping without circular imports.
It is not a full exchange master yet, but it prevents common Taiwan stocks from
being displayed as 自訂觀察 when the user enters only a stock number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StockIdentity:
    symbol: str
    name: str
    sector: str = "台股"
    yahoo_symbol: Optional[str] = None

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"


def normalize_symbol(text: str) -> str:
    import re

    cleaned = text.strip().upper().replace(" ", "")
    match = re.search(r"\d{4}", cleaned)
    if match:
        return match.group(0)
    return cleaned


def _normalize_name(text: str) -> str:
    return text.strip().replace(" ", "").replace("　", "").upper()


# Core Taiwan stock master for personal watchlist / portfolio resolution.
# This list intentionally covers AI supply chain, major electronics, financials,
# shipping, ETFs, and common user-entered names. It can be expanded safely.
STOCK_MASTER: dict[str, StockIdentity] = {
    "0050": StockIdentity("0050", "元大台灣50", "ETF", "0050.TW"),
    "0056": StockIdentity("0056", "元大高股息", "ETF", "0056.TW"),
    "00878": StockIdentity("00878", "國泰永續高股息", "ETF", "00878.TW"),
    "00919": StockIdentity("00919", "群益台灣精選高息", "ETF", "00919.TW"),
    "1101": StockIdentity("1101", "台泥", "水泥", "1101.TW"),
    "1102": StockIdentity("1102", "亞泥", "水泥", "1102.TW"),
    "1216": StockIdentity("1216", "統一", "食品", "1216.TW"),
    "1301": StockIdentity("1301", "台塑", "塑化", "1301.TW"),
    "1303": StockIdentity("1303", "南亞", "塑化", "1303.TW"),
    "1326": StockIdentity("1326", "台化", "塑化", "1326.TW"),
    "1402": StockIdentity("1402", "遠東新", "紡織", "1402.TW"),
    "1513": StockIdentity("1513", "中興電", "重電", "1513.TW"),
    "1560": StockIdentity("1560", "中砂", "半導體耗材", "1560.TW"),
    "1590": StockIdentity("1590", "亞德客-KY", "自動化", "1590.TW"),
    "2002": StockIdentity("2002", "中鋼", "鋼鐵", "2002.TW"),
    "2207": StockIdentity("2207", "和泰車", "汽車", "2207.TW"),
    "2301": StockIdentity("2301", "光寶科", "電子零組件", "2301.TW"),
    "2303": StockIdentity("2303", "聯電", "晶圓代工", "2303.TW"),
    "2308": StockIdentity("2308", "台達電", "電源管理", "2308.TW"),
    "2313": StockIdentity("2313", "華通", "PCB", "2313.TW"),
    "2317": StockIdentity("2317", "鴻海", "電子代工", "2317.TW"),
    "2324": StockIdentity("2324", "仁寶", "電子代工", "2324.TW"),
    "2327": StockIdentity("2327", "國巨", "被動元件", "2327.TW"),
    "2328": StockIdentity("2328", "廣宇", "電子零組件", "2328.TW"),
    "2330": StockIdentity("2330", "台積電", "半導體製造", "2330.TW"),
    "2337": StockIdentity("2337", "旺宏", "記憶體", "2337.TW"),
    "2344": StockIdentity("2344", "華邦電", "記憶體", "2344.TW"),
    "2345": StockIdentity("2345", "智邦", "網通", "2345.TW"),
    "2353": StockIdentity("2353", "宏碁", "PC", "2353.TW"),
    "2356": StockIdentity("2356", "英業達", "AI Server", "2356.TW"),
    "2357": StockIdentity("2357", "華碩", "PC", "2357.TW"),
    "2360": StockIdentity("2360", "致茂", "測試設備", "2360.TW"),
    "2368": StockIdentity("2368", "金像電", "PCB", "2368.TW"),
    "2376": StockIdentity("2376", "技嘉", "AI Server", "2376.TW"),
    "2377": StockIdentity("2377", "微星", "AI PC", "2377.TW"),
    "2379": StockIdentity("2379", "瑞昱", "IC Design", "2379.TW"),
    "2382": StockIdentity("2382", "廣達", "AI Server", "2382.TW"),
    "2383": StockIdentity("2383", "台光電", "PCB", "2383.TW"),
    "2392": StockIdentity("2392", "正崴", "連接器", "2392.TW"),
    "2395": StockIdentity("2395", "研華", "工業電腦", "2395.TW"),
    "2408": StockIdentity("2408", "南亞科", "記憶體", "2408.TW"),
    "2412": StockIdentity("2412", "中華電", "電信", "2412.TW"),
    "2421": StockIdentity("2421", "建準", "散熱", "2421.TW"),
    "2449": StockIdentity("2449", "京元電子", "測試", "2449.TW"),
    "2454": StockIdentity("2454", "聯發科", "IC Design", "2454.TW"),
    "2458": StockIdentity("2458", "義隆", "IC Design", "2458.TW"),
    "2467": StockIdentity("2467", "志聖", "設備", "2467.TW"),
    "2474": StockIdentity("2474", "可成", "機殼", "2474.TW"),
    "2603": StockIdentity("2603", "長榮", "航運", "2603.TW"),
    "2605": StockIdentity("2605", "新興", "航運", "2605.TW"),
    "2606": StockIdentity("2606", "裕民", "航運", "2606.TW"),
    "2609": StockIdentity("2609", "陽明", "航運", "2609.TW"),
    "2615": StockIdentity("2615", "萬海", "航運", "2615.TW"),
    "3006": StockIdentity("3006", "晶豪科", "記憶體", "3006.TW"),
    "3008": StockIdentity("3008", "大立光", "光學", "3008.TW"),
    "3013": StockIdentity("3013", "晟銘電", "機殼", "3013.TW"),
    "3017": StockIdentity("3017", "奇鋐", "散熱", "3017.TW"),
    "3023": StockIdentity("3023", "信邦", "連接器", "3023.TW"),
    "3034": StockIdentity("3034", "聯詠", "IC Design", "3034.TW"),
    "3035": StockIdentity("3035", "智原", "ASIC", "3035.TW"),
    "3037": StockIdentity("3037", "欣興", "PCB", "3037.TW"),
    "3045": StockIdentity("3045", "台灣大", "電信", "3045.TW"),
    "3062": StockIdentity("3062", "建漢", "網通", "3062.TW"),
    "3081": StockIdentity("3081", "聯亞", "光通訊", "3081.TWO"),
    "3105": StockIdentity("3105", "穩懋", "砷化鎵", "3105.TWO"),
    "3131": StockIdentity("3131", "弘塑", "半導體設備", "3131.TWO"),
    "3167": StockIdentity("3167", "大量", "PCB設備", "3167.TW"),
    "3189": StockIdentity("3189", "景碩", "載板", "3189.TW"),
    "3227": StockIdentity("3227", "原相", "IC Design", "3227.TWO"),
    "3231": StockIdentity("3231", "緯創", "AI Server", "3231.TW"),
    "3264": StockIdentity("3264", "欣銓", "測試", "3264.TWO"),
    "3324": StockIdentity("3324", "雙鴻", "散熱", "3324.TWO"),
    "3374": StockIdentity("3374", "精材", "封測", "3374.TWO"),
    "3413": StockIdentity("3413", "京鼎", "半導體設備", "3413.TW"),
    "3443": StockIdentity("3443", "創意", "ASIC", "3443.TW"),
    "3529": StockIdentity("3529", "力旺", "IP", "3529.TWO"),
    "3563": StockIdentity("3563", "牧德", "AOI設備", "3563.TW"),
    "3583": StockIdentity("3583", "辛耘", "半導體設備", "3583.TW"),
    "3596": StockIdentity("3596", "智易", "網通", "3596.TW"),
    "3653": StockIdentity("3653", "健策", "散熱", "3653.TW"),
    "3661": StockIdentity("3661", "世芯-KY", "ASIC", "3661.TW"),
    "3665": StockIdentity("3665", "貿聯-KY", "連接器", "3665.TW"),
    "3680": StockIdentity("3680", "家登", "半導體耗材", "3680.TWO"),
    "3711": StockIdentity("3711", "日月光投控", "封測", "3711.TW"),
    "4763": StockIdentity("4763", "材料-KY", "材料", "4763.TW"),
    "4904": StockIdentity("4904", "遠傳", "電信", "4904.TW"),
    "4906": StockIdentity("4906", "正文", "網通", "4906.TW"),
    "4958": StockIdentity("4958", "臻鼎-KY", "PCB", "4958.TW"),
    "4966": StockIdentity("4966", "譜瑞-KY", "IC Design", "4966.TW"),
    "4977": StockIdentity("4977", "眾達-KY", "光通訊", "4977.TW"),
    "5274": StockIdentity("5274", "信驊", "IC Design", "5274.TWO"),
    "5347": StockIdentity("5347", "世界", "晶圓代工", "5347.TWO"),
    "5388": StockIdentity("5388", "中磊", "網通", "5388.TW"),
    "5469": StockIdentity("5469", "瀚宇博", "PCB", "5469.TW"),
    "5871": StockIdentity("5871", "中租-KY", "金融服務", "5871.TW"),
    "5876": StockIdentity("5876", "上海商銀", "金融", "5876.TW"),
    "5880": StockIdentity("5880", "合庫金", "金融", "5880.TW"),
    "6121": StockIdentity("6121", "新普", "電池", "6121.TWO"),
    "6153": StockIdentity("6153", "嘉聯益", "PCB", "6153.TW"),
    "6187": StockIdentity("6187", "萬潤", "半導體設備", "6187.TWO"),
    "6191": StockIdentity("6191", "精成科", "PCB", "6191.TW"),
    "6196": StockIdentity("6196", "帆宣", "設備工程", "6196.TW"),
    "6213": StockIdentity("6213", "聯茂", "PCB", "6213.TW"),
    "6217": StockIdentity("6217", "中探針", "測試", "6217.TWO"),
    "6230": StockIdentity("6230", "超眾", "散熱", "6230.TW"),
    "6239": StockIdentity("6239", "力成", "封測", "6239.TW"),
    "6257": StockIdentity("6257", "矽格", "測試", "6257.TW"),
    "6271": StockIdentity("6271", "同欣電", "封測", "6271.TW"),
    "6278": StockIdentity("6278", "台表科", "SMT", "6278.TW"),
    "6285": StockIdentity("6285", "啟碁", "網通", "6285.TW"),
    "6412": StockIdentity("6412", "群電", "電源", "6412.TW"),
    "6415": StockIdentity("6415", "矽力*-KY", "IC Design", "6415.TW"),
    "6438": StockIdentity("6438", "迅得", "自動化設備", "6438.TW"),
    "6485": StockIdentity("6485", "點序", "記憶體控制", "6485.TWO"),
    "6488": StockIdentity("6488", "環球晶", "矽晶圓", "6488.TWO"),
    "6505": StockIdentity("6505", "台塑化", "塑化", "6505.TW"),
    "6515": StockIdentity("6515", "穎崴", "測試介面", "6515.TW"),
    "6531": StockIdentity("6531", "愛普*", "記憶體", "6531.TW"),
    "6538": StockIdentity("6538", "倉和", "半導體耗材", "6538.TWO"),
    "6669": StockIdentity("6669", "緯穎", "AI Server", "6669.TW"),
    "6672": StockIdentity("6672", "騰輝電子-KY", "PCB", "6672.TW"),
    "6756": StockIdentity("6756", "威鋒電子", "IC Design", "6756.TW"),
    "6770": StockIdentity("6770", "力積電", "晶圓代工", "6770.TW"),
    "8046": StockIdentity("8046", "南電", "載板", "8046.TW"),
    "8050": StockIdentity("8050", "廣積", "工業電腦", "8050.TWO"),
    "8213": StockIdentity("8213", "志超", "PCB", "8213.TW"),
    "8299": StockIdentity("8299", "群聯", "記憶體控制", "8299.TWO"),
    "8358": StockIdentity("8358", "金居", "銅箔基板", "8358.TWO"),
    "8996": StockIdentity("8996", "高力", "散熱", "8996.TW"),
    "9910": StockIdentity("9910", "豐泰", "製鞋", "9910.TW"),
}

NAME_TO_SYMBOL: dict[str, str] = {}
for symbol, identity in STOCK_MASTER.items():
    NAME_TO_SYMBOL[_normalize_name(identity.name)] = symbol
    NAME_TO_SYMBOL[_normalize_name(identity.display_name)] = symbol

# Additional aliases that users are likely to type.
ALIASES: dict[str, str] = {
    "台灣50": "0050",
    "永續高股息": "00878",
    "世芯": "3661",
    "中租": "5871",
    "愛普": "6531",
    "材料": "4763",
    "矽力": "6415",
}
for alias, symbol in ALIASES.items():
    NAME_TO_SYMBOL[_normalize_name(alias)] = symbol


def get_stock_identity(symbol_or_name: str) -> Optional[StockIdentity]:
    text = (symbol_or_name or "").strip()
    if not text:
        return None
    symbol = normalize_symbol(text)
    if symbol in STOCK_MASTER:
        return STOCK_MASTER[symbol]
    normalized = _normalize_name(text)
    if normalized in NAME_TO_SYMBOL:
        return STOCK_MASTER[NAME_TO_SYMBOL[normalized]]
    for name_key, mapped_symbol in NAME_TO_SYMBOL.items():
        if normalized and normalized in name_key:
            return STOCK_MASTER[mapped_symbol]
    return None


def enrich_stock_name(symbol: str, current_name: Optional[str] = None) -> str:
    identity = get_stock_identity(symbol)
    if identity:
        return identity.name
    name = (current_name or "").strip()
    if name and not name.startswith("自訂觀察"):
        return name
    clean_symbol = normalize_symbol(symbol)
    return f"自訂觀察{clean_symbol}"
