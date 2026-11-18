"""Treasure maps to the unique structures: in the village epic chest and for sale from cartographers.

For each unicas/ module the following are written:
  item_modifier heraldia:mapas/<id>   exploration (tag heraldia:unicas/<id>) + translated name; without a destination, it is discarded
  loot_table    heraldia:mapas/<id>   one map (used by the epic chest; also works for /loot give)
  villager_trade heraldia:cartografo/<id>, in the tag minecraft:cartographer/level_5, only for Heraldia cartographers
                                      (written by trades.write; the trade comes from trades.trade)
Optional in the module: DISPLAY_NAME = {"es_es": ..., "en_us": ...} and MAP = {"decoration": "minecraft:<map_decoration_type>"}.
"""
import math
import trades

NS = "heraldia"
# The search walks cells of the placement grid (one per "spacing" chunks), in rings up to search_radius.
# It is limited to about 10,000 blocks and 8 rings (289 cells): a map with no reachable structure does not hang the server.
MAP_RANGE_BLOCKS, MIN_RADIUS, MAX_RADIUS = 10_000, 2, 8
DEFAULT_DECORATION = "minecraft:red_x"
# Probability that an epic chest carries a map (one among all the unique structures).
EPIC_MAP_CHANCE = 0.05
# Price of the master cartographer trade: high (one and a half times a mansion map) and with barely any reputation discount.
PRICE_EMERALDS, MAX_USES, TRADE_XP, REPUTATION_DISCOUNT = 24, 2, 30, 0.05
PREDICATE = f"{NS}:aldeano_heraldia"


def search_radius(st):
    spacing = st.get("spacing", 250)
    return max(MIN_RADIUS, min(MAX_RADIUS, math.ceil(MAP_RANGE_BLOCKS / (spacing * 16))))


def names(sid, mod):
    n = getattr(mod, "DISPLAY_NAME", None) or {}
    fallback = sid.replace("_", " ").capitalize()
    return n.get("es_es", fallback), n.get("en_us", n.get("es_es", fallback))


def key(sid):
    return f"item.{NS}.mapa.unicas.{sid}"


def lang(modules):
    out = {"es_es": {}, "en_us": {}}
    for sid, mod in modules:
        es, en = names(sid, mod)
        out["es_es"][key(sid)] = f"Mapa: {es}"
        out["en_us"][key(sid)] = f"Map: {en}"
    return out


def item_modifier(sid, mod):
    st = mod.STRUCTURE
    deco = (getattr(mod, "MAP", None) or {}).get("decoration", DEFAULT_DECORATION)
    return [
        {"type": "minecraft:exploration_map", "destination": f"#{NS}:unicas/{sid}", "decoration": deco,
         "zoom": 2, "search_radius": search_radius(st), "skip_existing_chunks": False},
        {"type": "minecraft:filtered", "item_filter": {"predicates": {"minecraft:map_id": {}}},
         "on_fail": {"type": "minecraft:discard"}},
        {"type": "minecraft:set_name", "target": "item_name",
         "name": {"translate": key(sid), "fallback": f"Mapa: {names(sid, mod)[0]}"}},
    ]


def map_entry(sid, mod, w):
    # 26.3 has no "reference" modifier or condition: it is written inline (and also as a standalone item_modifier).
    return {"type": "minecraft:item", "name": "minecraft:filled_map", "weight": w, "modifier": item_modifier(sid, mod)}


def with_maps(table, modules):
    """Adds to the epic chest a group with a random map (EPIC_MAP_CHANCE in total)."""
    if not modules:
        return table
    n = len(modules)
    empty = round(n * (1 - EPIC_MAP_CHANCE) / EPIC_MAP_CHANCE)
    pool = {"rolls": 1, "entries": [map_entry(sid, mod, 1) for sid, mod in modules] + [{"type": "minecraft:empty", "weight": empty}]}
    return dict(table, pools=table["pools"] + [pool])


def villager_predicate():
    return trades.villager_predicate()


def trade(sid, mod):
    return trades.trade(PRICE_EMERALDS, {"id": "minecraft:filled_map"}, extra={"id": "minecraft:compass"},
                        modifier=item_modifier(sid, mod), pred=villager_predicate(), uses=MAX_USES, xp=TRADE_XP,
                        discount=REPUTATION_DISCOUNT)


def write(out, modules, jdump):
    """Modifiers and tables of the maps; the trades (heraldia:cartografo/<id>) are written by trades.write along with the others."""
    for sid, mod in modules:
        jdump(out, f"data/{NS}/item_modifier/mapas/{sid}.json", {"type": "minecraft:sequence", "functions": item_modifier(sid, mod)})
        jdump(out, f"data/{NS}/loot_table/mapas/{sid}.json", {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [map_entry(sid, mod, 1)]}]})
    jdump(out, f"data/{NS}/predicate/aldeano_heraldia.json", villager_predicate())   # the same filter, to test it
