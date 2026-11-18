"""Trades of the Heraldia villagers (26.3 data: villager_trade + tag #minecraft:<profession>/level_N).

A single way to write a trade (`trade`) and to filter who is offered it (`predicate`), used by:
  - maps.py: the treasure map of each unique structure at the Heraldia master cartographers (heraldia:cartografo/<id>);
  - the characterful trades of each style (STYLES, heraldia:estilos/<style>/<n>) and the map of the unique structure of its zone at
    the cartographers of each family (heraldia:familias/<family>/mapa), only for Heraldia villagers (Tags "heraldia")
    who are inside a village of that style or family (location predicate with its structures) and with the option
    aldeas.vida.tratos_estilo enabled (condition heraldia:opcion);
  - the siege of the fortified villages (FORTIFIED): an ominous bottle at the armourer, with aldeas.vida.asedios.

How a trade comes out (AbstractVillager.addOffersFromItemListingsWithoutDuplicates, 26.3): on reaching a level,
`amount` trades (2) are drawn at random from the level's tag; if the predicate of one fails, it is removed and another is drawn, so the
trades of other styles subtract nothing. With n vanilla trades in the tag and one of the style, the style one comes out with
probability 2 / (n + 1): that is why they go in levels with few vanilla trades (VANILLA_LEVEL). They apply on levelling up,
also in villages already generated (only what the villager offers from then on changes).
"""
from themes import THEMES, FAMILIES
import uniques

NS = "heraldia"
VILLAGER_TAG = NS            # core.villager puts this tag on the Heraldia villagers
OPTION_STYLE, OPTION_SIEGES = "aldeas.vida.tratos_estilo", "aldeas.vida.asedios"
EM = "minecraft:emerald"

# Vanilla trades of each tag #minecraft:<profession>/level_N (26.3) at the levels used by the style trades:
# all levels draw 2. The test village_life.py checks it against the game .jar.
VANILLA_LEVEL = {("weaponsmith", 2): 1, ("weaponsmith", 3): 2, ("toolsmith", 2): 1, ("butcher", 4): 1,
                 ("butcher", 5): 1, ("fisherman", 3): 2, ("fisherman", 4): 1, ("shepherd", 5): 1, ("armorer", 2): 3,
                 ("armorer", 4): 3, ("fletcher", 4): 2, ("fletcher", 5): 3, ("leatherworker", 2): 3,
                 ("leatherworker", 3): 2, ("leatherworker", 4): 2, ("leatherworker", 5): 2, ("librarian", 2): 3,
                 ("librarian", 3): 3, ("cleric", 3): 2, ("cleric", 4): 3, ("cleric", 5): 2, ("mason", 1): 2,
                 ("mason", 5): 2, ("farmer", 4): 2, ("farmer", 5): 2, ("cartographer", 3): 3}
XP = {1: 2, 2: 10, 3: 20, 4: 30, 5: 30}

# The unique structure "of the zone" of each family (its map is sold by the family cartographer, level 3).
ZONE = {"llanuras": "castillo", "bosque": "catedral", "oscuro": "torre_mago", "taiga": "salon_jarl",
        "nieve": "fortaleza_hielo", "desierto": "acueducto", "sabana": "coliseo", "jungla": "piramide",
        "pantano": "mansion", "cerezos": "palacio", "badlands": "acueducto", "costa": "galeon"}
MAP_FAMILY = dict(oficio="cartographer", nivel=3, precio=16, usos=3)

# Fortified styles: the game can trigger a siege (pillager raid) in them if a player with the omen
# enters; the armourer sells the mildest ominous bottle (amplifier 0: level 1 raid). Disabled by default.
FORTIFIED = ("oscuro_fortificada", "nieve_fortaleza", "badlands_canon")
SIEGE = dict(oficio="weaponsmith", nivel=3, precio=10, usos=1)


def _c(key, es):
    return {"translate": key, "fallback": es}


def _dye(rgb):
    return {"minecraft:dyed_color": rgb}


def _ench(**lv):
    return {"minecraft:enchantments": {f"minecraft:{k}": v for k, v in lv.items()}}


def _trim(material, pattern):
    return {"minecraft:trim": {"material": f"minecraft:{material}", "pattern": f"minecraft:{pattern}"}}


def _potion(pid):
    return {"minecraft:potion_contents": {"potion": f"minecraft:{pid}"}}


def _chronicle_copy(sid):
    """Copy of the account of a unique structure (without the heraldia_historia mark: it does not count for the chronicler's challenge)."""
    from uniques._common import chest_loot
    mod = dict(uniques.modules())[sid]
    k = chest_loot.story_key(sid)
    pages = [_c(f"{k}.pagina{i + 1}", es) for i, (es, _) in enumerate(mod.STORY["relato"])]
    name = _c(f"item.{NS}.trato.copia_cronica", "Copia de la Crónica de los Heraldos")
    e = chest_loot.written_book(pages, name, "Crónica (copia)", chest_loot.STORY_AUTHOR,
                    lore=[_c(f"item.{NS}.trato.copia_cronica.lore", "Copiada en el scriptorium de la abadía")])
    comps = dict(e["modifier"][0]["components"])
    del comps["minecraft:custom_name"]   # the name is set by the trade (item_name + custom_name without italics)
    return comps


# Characterful trades of each style: (profession, level, item, quantity, emeralds, (es, en) name, (es, en) lore,
# extra components, uses). Only vanilla items with components; moderate enchantments (at most level 3).
STYLES = {
    "llanuras_castellana": [("weaponsmith", 2, "iron_sword", 1, 12, ("Espada de la mesnada", "Militia Sword"),
                             ("Forjada para la ronda de la villa", "Forged for the town watch"), _ench(sharpness=1, unbreaking=1), 3)],
    "llanuras_gallega": [("fisherman", 4, "fishing_rod", 1, 10, ("Caña de la ría", "Estuary Rod"),
                          ("Para el pulpo y la sardina", "For octopus and sardine"), _ench(luck_of_the_sea=2, lure=1), 3)],
    "llanuras_entramado": [("butcher", 4, "pumpkin_pie", 4, 2, ("Pastel de la campiña", "Countryside Pie"),
                            ("Receta de la abuela", "Grandmother's recipe"), {}, 8)],
    "bosque_lenadores": [("toolsmith", 2, "iron_axe", 1, 10, ("Hacha del aserradero", "Sawmill Axe"),
                          ("Tala sin mellarse", "Fells without chipping"), _ench(efficiency=2, unbreaking=1), 3)],
    "bosque_elfica": [("fletcher", 5, "bow", 1, 15, ("Arco élfico", "Elven Bow"),
                       ("Tallado en abedul blanco", "Carved from white birch"), _ench(power=2, unbreaking=1), 2)],
    "bosque_abadia": [("librarian", 3, "written_book", 1, 6, ("Copia de la Crónica de los Heraldos",
                                                               "Copy of the Chronicle of the Heralds"),
                       None, "cronica:catedral", 3)],
    "oscuro_gotica": [("cleric", 4, "splash_potion", 1, 4, ("Agua bendita", "Holy Water"),
                       ("Bendecida bajo la bóveda", "Blessed beneath the vault"), _potion("healing"), 6)],
    "oscuro_alquimistas": [("cleric", 3, "potion", 1, 6, ("Elixir del herbolario", "Herbalist's Elixir"),
                            ("Raíz pálida y musgo", "Pale root and moss"), _potion("regeneration"), 4)],
    "oscuro_fortificada": [("armorer", 2, "shield", 1, 8, ("Escudo de la empalizada", "Palisade Shield"),
                            ("Tablas de abeto y clavos", "Spruce boards and nails"), _ench(unbreaking=2), 3)],
    "taiga_nordica": [("butcher", 5, "honey_bottle", 3, 3, ("Hidromiel del jarl", "Jarl's Mead"),
                       ("Para las noches largas", "For the long nights"), {}, 6)],
    "taiga_eslava": [("leatherworker", 3, "leather_helmet", 1, 4, ("Gorro de fieltro", "Felt Cap"),
                      ("Bordado a mano", "Hand-embroidered"), _dye(0xB02E26), 4)],
    "taiga_cazadores": [("leatherworker", 4, "leather_chestplate", 1, 7, ("Zamarra del cazador", "Hunter's Jerkin"),
                         ("Piel curtida al humo", "Smoke-tanned hide"), {**_dye(0x6B4A2B), **_ench(protection=1)}, 3)],
    "nieve_alpina": [("toolsmith", 2, "iron_pickaxe", 1, 10, ("Pico de la cordada", "Roped Party Pickaxe"),
                      ("Para el hielo de la cumbre", "For the summit ice"), _ench(efficiency=2), 3)],
    "nieve_fortaleza": [("armorer", 2, "iron_helmet", 1, 10, ("Yelmo del norte", "Northern Helm"),
                         ("Adorno de lapislázuli", "Lapis inlay"), _trim("lapis", "sentry"), 3)],
    "nieve_pastores": [("leatherworker", 2, "leather_boots", 1, 5, ("Abarcas de pastor", "Shepherd's Boots"),
                        ("Para la nieve honda", "For deep snow"), {**_dye(0xF0F0F0), **_ench(feather_falling=1)}, 4)],
    "desierto_andalusi": [("mason", 5, "cyan_glazed_terracotta", 8, 3, ("Azulejo del oasis", "Oasis Tile"),
                           ("Esmaltado al fuego", "Fire-glazed"), {}, 6)],
    "desierto_obelisco": [("armorer", 4, "leather_chestplate", 1, 9, ("Peto de las dunas", "Dune Breastplate"),
                           ("Teñido del color de la arena, con adorno de oro", "Dyed sand-colour, with gold trim"),
                           {**_dye(0xD9C38C), **_trim("gold", "dune"), **_ench(protection=1)}, 3)],
    "desierto_caravanera": [("leatherworker", 5, "saddle", 1, 6, ("Silla de la caravana", "Caravan Saddle"),
                             ("Cuero de camello", "Camel leather"), {}, 3)],
    "sabana_paja": [("fletcher", 4, "arrow", 16, 3, ("Flechas de caza", "Hunting Arrows"),
                     ("Plumas de la sabana", "Savanna feathers"), {}, 6)],
    "sabana_terracota": [("mason", 5, "orange_glazed_terracotta", 8, 3, ("Barro pintado", "Painted Clay"),
                          ("Pintado a mano", "Hand-painted"), {}, 6)],
    "sabana_pastores": [("shepherd", 5, "bell", 1, 10, ("Cencerro del rebaño", "Herd Bell"),
                         ("Se oye desde el otro valle", "Heard from the next valley"), {}, 2)],
    "jungla_arboles": [("fletcher", 5, "bow", 1, 12, ("Arco de la copa", "Canopy Bow"),
                        ("Para cazar entre las ramas", "For hunting among the branches"), _ench(power=1, punch=1), 2)],
    "jungla_templos": [("cleric", 5, "cocoa_beans", 8, 3, ("Cacao ceremonial", "Ceremonial Cocoa"),
                        ("Ofrenda del templo", "Temple offering"), {}, 6)],
    "jungla_bambu": [("fisherman", 4, "bamboo_raft", 1, 4, ("Balsa del río", "River Raft"),
                      ("Atada con lianas", "Lashed with vines"), {}, 3)],
    "pantano_palafitos": [("fisherman", 3, "fishing_rod", 1, 8, ("Caña del manglar", "Mangrove Rod"),
                           ("Pesca entre las raíces", "Fishes among the roots"), _ench(lure=2), 3)],
    "pantano_brujas": [("cleric", 3, "potion", 1, 6, ("Brebaje de la ciénaga", "Bog Brew"),
                        ("No preguntes qué lleva", "Don't ask what's in it"), _potion("night_vision"), 4)],
    "pantano_turba": [("mason", 1, "mud_bricks", 16, 2, ("Ladrillos de turba", "Peat Bricks"),
                       ("Secados al sol", "Sun-dried"), {}, 8)],
    "cerezos_japonesa": [("weaponsmith", 2, "iron_sword", 1, 14, ("Sable del santuario", "Shrine Sabre"),
                          ("Templado al alba", "Tempered at dawn"), _ench(sharpness=2), 3)],
    "cerezos_templo": [("cleric", 4, "pink_candle", 4, 3, ("Velas del templo", "Temple Candles"),
                        ("Huelen a flor de cerezo", "They smell of cherry blossom"), {}, 6)],
    "cerezos_artesanos": [("toolsmith", 2, "lantern", 4, 4, ("Farolillo de la casa de té", "Teahouse Lantern"),
                           ("Hierro y papel de arroz", "Iron and rice paper"), {}, 6)],
    "badlands_minera": [("toolsmith", 2, "iron_pickaxe", 1, 12, ("Pico del filón", "Lode Pickaxe"),
                         ("Para el oro del cañón", "For the canyon gold"), _ench(fortune=1, efficiency=1), 3)],
    "badlands_roca": [("mason", 5, "red_terracotta", 16, 2, ("Terracota del risco", "Cliff Terracotta"),
                       ("Cortada de la pared del cañón", "Cut from the canyon wall"), {}, 8)],
    "badlands_canon": [("armorer", 2, "iron_helmet", 1, 10, ("Yelmo del cañón", "Canyon Helm"),
                        ("Adorno de cobre", "Copper inlay"), _trim("copper", "dune"), 3)],
    "costa_pescadores": [("fisherman", 4, "fishing_rod", 1, 12, ("Caña del patrón", "Skipper's Rod"),
                          ("Nunca vuelve sin pescado", "Never comes back empty"), _ench(luck_of_the_sea=2, lure=2), 2)],
    "costa_mercante": [("librarian", 2, "compass", 1, 4, ("Brújula del puerto", "Harbour Compass"),
                        ("Marca el norte en la niebla", "Points north in the fog"), {}, 4)],
    "costa_mediterranea": [("farmer", 5, "honey_bottle", 2, 3, ("Ánfora de miel", "Amphora of Honey"),
                            ("Miel de tomillo", "Thyme honey"), {}, 6)],
}


def villager_predicate(structures=None):
    """Heraldia villager predicate (Tags "heraldia"); with `structures` (list of ids or tag), also inside
    a piece of those structures. entity_tags reads the Tags without serialising the villager."""
    if structures is None:   # the usual filter of the master cartographers' maps (same JSON as before)
        return {"type": "minecraft:entity_properties", "entity": "this", "predicate": {"nbt": "{Tags:[\"%s\"]}" % VILLAGER_TAG}}
    return {"type": "minecraft:entity_properties", "entity": "this", "predicate": {
        "minecraft:entity_tags": {"all_of": [VILLAGER_TAG]}, "minecraft:location": {"structures": structures}}}


def predicate(structures=None, *options):
    """merchant_predicate: Heraldia villager (in those structures) and yes/no options enabled (the options go
    first: they are the cheapest)."""
    v = villager_predicate(structures)
    if not options:
        return v
    return {"type": "minecraft:all_of", "terms": [{"type": f"{NS}:opcion", "clave": o} for o in options] + [v]}


def trade(price, gives, *, extra=None, modifier=None, pred=None, uses=3, xp=10, discount=0.05):
    """26.3 trade: `price` emeralds (and `extra`, another item that is asked for) for `gives` ({id, count, components})."""
    t = {"wants": {"id": EM, "count": price}}
    if extra:
        t["additional_wants"] = extra
    t["gives"] = gives
    if modifier:
        t["given_item_modifier"] = modifier
    if pred:
        t["merchant_predicate"] = pred
    t.update(max_uses=uses, xp=xp, reputation_discount=discount)
    return t


def key_name(tid, n):
    return f"item.{NS}.trato.{tid}.{n}"


def style_structures(tid):
    return [f"{NS}:{tid}", f"{NS}:{tid}_grande"]


def style_trades(tid):
    """[(trade id, profession, level, trade)] of a style."""
    out = []
    for n, (depth, lvl, item, count, price, name, lore, comps, uses) in enumerate(STYLES.get(tid, ())):
        key = key_name(tid, n)
        if isinstance(comps, str) and comps.startswith("cronica:"):
            comps = _chronicle_copy(comps.split(":", 1)[1])
        c = dict(comps)
        c["minecraft:item_name"] = _c(key, name[0])
        if item == "written_book":   # the book title would act as the name: custom_name without italics (chest_loot.written_book)
            c["minecraft:custom_name"] = dict(_c(key, name[0]), italic=False)
        if lore:
            c["minecraft:lore"] = [dict(_c(key + ".lore", lore[0]), color="gray", italic=False)]
        gives = {"id": f"minecraft:{item}", "count": count, "components": c}
        out.append((f"{NS}:estilos/{tid}/{n}", depth, lvl,
                    trade(price, gives, pred=predicate(style_structures(tid), OPTION_STYLE), uses=uses, xp=XP[lvl])))
    if tid in FORTIFIED:
        a = SIEGE
        gives = {"id": "minecraft:ominous_bottle", "count": 1, "components": {
            "minecraft:ominous_bottle_amplifier": 0, "minecraft:item_name": _c(f"item.{NS}.trato.asedio", "Desafío del asedio"),
            "minecraft:lore": [dict(_c(f"item.{NS}.trato.asedio.lore", "Bébela y vuelve a la aldea: llegarán los saqueadores"),
                                    color="gray", italic=False)]}}
        out.append((f"{NS}:estilos/{tid}/asedio", a["oficio"], a["nivel"],
                    trade(a["precio"], gives, pred=predicate(style_structures(tid), OPTION_SIEGES), uses=a["usos"],
                          xp=XP[a["nivel"]])))
    return out


def family_trades(fam, modules):
    """Map of the unique structure of the family's zone at its cartographers (if that unique structure exists)."""
    import maps
    sid = ZONE.get(fam)
    mods = dict(modules)
    if sid not in mods:
        return []
    m = MAP_FAMILY
    t = trade(m["precio"], {"id": "minecraft:filled_map"}, extra={"id": "minecraft:compass"},
              modifier=maps.item_modifier(sid, mods[sid]), pred=predicate(f"#{NS}:aldeas/{fam}", OPTION_STYLE),
              uses=m["usos"], xp=XP[m["nivel"]])
    return [(f"{NS}:familias/{fam}/mapa", m["oficio"], m["nivel"], t)]


def everyone(modules):
    """[(id, profession, level, trade)] of Heraldia: maps of the master cartographers, of each family and of each style."""
    import maps
    import dimensions
    out = [(f"{NS}:cartografo/{sid}", "cartographer", 5, maps.trade(sid, mod)) for sid, mod in dimensions.overworld_only(modules)]
    for fam in FAMILIES:
        out += family_trades(fam, modules)
    for th in THEMES:
        out += style_trades(th["id"])
    return out


def errors(modules):
    """Contract of the data: existing styles, profession and level with their count of vanilla trades, moderate prices and
    enchantment levels, and no forbidden item."""
    from uniques._common import chest_loot
    ids = {th["id"] for th in THEMES}
    e = [f"tratos.ESTILOS: estilo desconocido {t}" for t in STYLES if t not in ids]
    for tid in ids:
        if not 1 <= len(STYLES.get(tid, ())) <= 2:
            e.append(f"tratos.ESTILOS: el estilo {tid} debe tener 1-2 tratos propios")
    e += [f"tratos.FORTIFICADAS: estilo desconocido {t}" for t in FORTIFIED if t not in ids]
    for tid_, depth, lvl, t in everyone(modules):
        if (depth, lvl) not in VANILLA_LEVEL and not tid_.startswith(f"{NS}:cartografo/"):
            e.append(f"{tid_}: {depth} nivel {lvl} no está en NIVEL_VANILLA (cuenta sus tratos vanilla)")
        if not 1 <= t["wants"]["count"] <= 64:
            e.append(f"{tid_}: precio fuera de 1-64 esmeraldas")
        g = t["gives"]
        if any(p in g["id"] for p in chest_loot.FORBIDDEN_ITEMS):
            e.append(f"{tid_}: objeto prohibido {g['id']}")
        for k, v in (g.get("components", {}).get("minecraft:enchantments") or {}).items():
            if v > chest_loot.MAX_LEVEL:
                e.append(f"{tid_}: {k} {v} pasa del nivel {chest_loot.MAX_LEVEL}")
    return e


def items(modules):
    """What the trades ask for and give, as loot entries (to validate ids, trims and enchantments)."""
    out = []
    for _, _, _, t in everyone(modules):
        for k in ("wants", "additional_wants", "gives"):
            if k in t:
                e = {"type": "minecraft:item", "name": t[k]["id"]}
                c = t[k].get("components")
                if c:
                    e["modifier"] = [{"type": "minecraft:set_components", "components": c},
                                     {"type": "minecraft:set_enchantments", "enchantments": c.get("minecraft:enchantments", {})}]
                out.append(e)
    return out


def lang():
    out = {"es_es": {}, "en_us": {}}
    for tid, lst in STYLES.items():
        for n, (_, _, _, _, _, name, lore, _, _) in enumerate(lst):
            k = key_name(tid, n)
            out["es_es"][k], out["en_us"][k] = name
            if lore:
                out["es_es"][k + ".lore"], out["en_us"][k + ".lore"] = lore
    out["es_es"][f"item.{NS}.trato.copia_cronica.lore"] = "Copiada en el scriptorium de la abadía"
    out["en_us"][f"item.{NS}.trato.copia_cronica.lore"] = "Copied in the abbey scriptorium"
    out["es_es"][f"item.{NS}.trato.copia_cronica"] = "Copia de la Crónica de los Heraldos"
    out["en_us"][f"item.{NS}.trato.copia_cronica"] = "Copy of the Chronicle of the Heralds"
    out["es_es"][f"item.{NS}.trato.asedio"], out["en_us"][f"item.{NS}.trato.asedio"] = "Desafío del asedio", "Siege Challenge"
    out["es_es"][f"item.{NS}.trato.asedio.lore"] = "Bébela y vuelve a la aldea: llegarán los saqueadores"
    out["en_us"][f"item.{NS}.trato.asedio.lore"] = "Drink it and return to the village: the raiders will come"
    return out


def write(out, modules, jdump):
    """Writes each trade and adds its id to the tag of its profession and level (without replacing the vanilla one)."""
    tags = {}
    for tid_, depth, lvl, t in everyone(modules):
        jdump(out, f"data/{NS}/villager_trade/{tid_.split(':', 1)[1]}.json", t)
        tags.setdefault((depth, lvl), []).append(tid_)
    for (depth, lvl), values in sorted(tags.items()):
        jdump(out, f"data/minecraft/tags/villager_trade/{depth}/level_{lvl}.json", {"replace": False, "values": values})
