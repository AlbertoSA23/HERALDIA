"""Mapas del tesoro hacia las estructuras únicas: en el cofre épico de las aldeas y a la venta en los cartógrafos.

Por cada módulo de unicas/ se escriben:
  item_modifier heraldia:mapas/<id>   exploración (etiqueta heraldia:unicas/<id>) + nombre traducido; sin destino, se descarta
  loot_table    heraldia:mapas/<id>   un mapa (lo usa el cofre épico; sirve también para /loot give)
  villager_trade heraldia:cartografo/<id>, en la etiqueta minecraft:cartographer/level_5, solo para cartógrafos de Heraldia
                                      (lo escribe tratos.write; el trato sale de tratos.trato)
Opcional en el módulo: NOMBRE = {"es_es": ..., "en_us": ...} y MAPA = {"decoration": "minecraft:<map_decoration_type>"}.
"""
import math
import tratos

NS = "heraldia"
# La búsqueda recorre celdas de la rejilla de colocación (una por "spacing" chunks), en anillos hasta search_radius.
# Se limita a unos 10.000 bloques y a 8 anillos (289 celdas): un mapa sin estructura alcanzable no traba el servidor.
MAP_RANGE_BLOCKS, MIN_RADIUS, MAX_RADIUS = 10_000, 2, 8
DEFAULT_DECORATION = "minecraft:red_x"
# Probabilidad de que un cofre épico lleve un mapa (uno de entre todas las estructuras únicas).
EPIC_MAP_CHANCE = 0.05
# Precio del trato de maestro cartógrafo: alto (una vez y media un mapa de mansión) y sin apenas rebaja por reputación.
PRICE_EMERALDS, MAX_USES, TRADE_XP, REPUTATION_DISCOUNT = 24, 2, 30, 0.05
PREDICATE = f"{NS}:aldeano_heraldia"


def search_radius(st):
    spacing = st.get("spacing", 250)
    return max(MIN_RADIUS, min(MAX_RADIUS, math.ceil(MAP_RANGE_BLOCKS / (spacing * 16))))


def names(sid, mod):
    n = getattr(mod, "NOMBRE", None) or {}
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
    deco = (getattr(mod, "MAPA", None) or {}).get("decoration", DEFAULT_DECORATION)
    return [
        {"type": "minecraft:exploration_map", "destination": f"#{NS}:unicas/{sid}", "decoration": deco,
         "zoom": 2, "search_radius": search_radius(st), "skip_existing_chunks": False},
        {"type": "minecraft:filtered", "item_filter": {"predicates": {"minecraft:map_id": {}}},
         "on_fail": {"type": "minecraft:discard"}},
        {"type": "minecraft:set_name", "target": "item_name",
         "name": {"translate": key(sid), "fallback": f"Mapa: {names(sid, mod)[0]}"}},
    ]


def map_entry(sid, mod, w):
    # 26.3 no tiene modificador ni condición "reference": se escribe en línea (y también como item_modifier suelto).
    return {"type": "minecraft:item", "name": "minecraft:filled_map", "weight": w, "modifier": item_modifier(sid, mod)}


def with_maps(table, modules):
    """Añade al cofre épico un grupo con un mapa al azar (EPIC_MAP_CHANCE en total)."""
    if not modules:
        return table
    n = len(modules)
    empty = round(n * (1 - EPIC_MAP_CHANCE) / EPIC_MAP_CHANCE)
    pool = {"rolls": 1, "entries": [map_entry(sid, mod, 1) for sid, mod in modules] + [{"type": "minecraft:empty", "weight": empty}]}
    return dict(table, pools=table["pools"] + [pool])


def villager_predicate():
    return tratos.villager_predicate()


def trade(sid, mod):
    return tratos.trato(PRICE_EMERALDS, {"id": "minecraft:filled_map"}, extra={"id": "minecraft:compass"},
                        modifier=item_modifier(sid, mod), pred=villager_predicate(), usos=MAX_USES, xp=TRADE_XP,
                        descuento=REPUTATION_DISCOUNT)


def write(out, modules, jdump):
    """Modificadores y tablas de los mapas; los tratos (heraldia:cartografo/<id>) los escribe tratos.write con los demás."""
    for sid, mod in modules:
        jdump(out, f"data/{NS}/item_modifier/mapas/{sid}.json", {"type": "minecraft:sequence", "functions": item_modifier(sid, mod)})
        jdump(out, f"data/{NS}/loot_table/mapas/{sid}.json", {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [map_entry(sid, mod, 1)]}]})
    jdump(out, f"data/{NS}/predicate/aldeano_heraldia.json", villager_predicate())   # el mismo filtro, para probarlo
