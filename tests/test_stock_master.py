from radar.engine.user_space import make_custom_stock
from radar.knowledge.stock_map import resolve_stock_query
from radar.knowledge.stock_master import enrich_stock_name


def test_symbol_2313_resolves_to_compeq():
    stock = make_custom_stock("2313")
    assert stock.symbol == "2313"
    assert stock.name == "華通"
    assert stock.display_name == "2313 華通"


def test_query_huatong_resolves_to_2313():
    stock = resolve_stock_query("華通")
    assert stock is not None
    assert stock.symbol == "2313"
    assert stock.name == "華通"


def test_legacy_custom_name_is_repaired():
    assert enrich_stock_name("2313", "自訂觀察2313") == "華通"
