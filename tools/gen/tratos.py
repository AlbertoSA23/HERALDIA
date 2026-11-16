"""Tratos de los aldeanos de Heraldia (datos de 26.3: villager_trade + etiqueta #minecraft:<oficio>/level_N).

Una sola forma de escribir un trato (`trato`) y de filtrar a quién se le ofrece (`predicado`), que usan:
  - mapas.py: el mapa del tesoro de cada única en los cartógrafos maestros de Heraldia (heraldia:cartografo/<id>);
  - los tratos con carácter de cada estilo (ESTILOS, heraldia:estilos/<estilo>/<n>) y el mapa de la única de su zona en
    los cartógrafos de cada familia (heraldia:familias/<familia>/mapa), solo para aldeanos de Heraldia (Tags "heraldia")
    que están dentro de una aldea de ese estilo o familia (predicado de ubicación con sus estructuras) y con la opción
    aldeas.vida.tratos_estilo activada (condición heraldia:opcion);
  - el asedio de las aldeas fortificadas (FORTIFICADAS): una botella ominosa en el armero, con aldeas.vida.asedios.

Cómo sale un trato (AbstractVillager.addOffersFromItemListingsWithoutDuplicates, 26.3): al subir a un nivel se sacan
`amount` tratos (2) al azar de la etiqueta del nivel; si el predicado de uno falla, se quita y se saca otro, así que los
tratos de otros estilos no restan nada. Con n tratos vanilla en la etiqueta y uno del estilo, el del estilo sale con
probabilidad 2 / (n + 1): por eso van en niveles con pocos tratos vanilla (NIVEL_VANILLA). Se aplican al subir de nivel,
también en las aldeas ya generadas (solo cambia lo que el aldeano ofrezca a partir de entonces).
"""
from themes import THEMES, FAMILIES
import unicas

NS = "heraldia"
VILLAGER_TAG = NS            # core.villager pone esta etiqueta a los aldeanos de Heraldia
OPCION_ESTILO, OPCION_ASEDIOS = "aldeas.vida.tratos_estilo", "aldeas.vida.asedios"
EM = "minecraft:emerald"

# Tratos vanilla de cada etiqueta #minecraft:<oficio>/level_N (26.3) en los niveles que usan los tratos de estilo:
# todos los niveles sacan 2. Lo comprueba la prueba aldeas_vida.py contra el .jar del juego.
NIVEL_VANILLA = {("weaponsmith", 2): 1, ("weaponsmith", 3): 2, ("toolsmith", 2): 1, ("butcher", 4): 1,
                 ("butcher", 5): 1, ("fisherman", 3): 2, ("fisherman", 4): 1, ("shepherd", 5): 1, ("armorer", 2): 3,
                 ("armorer", 4): 3, ("fletcher", 4): 2, ("fletcher", 5): 3, ("leatherworker", 2): 3,
                 ("leatherworker", 3): 2, ("leatherworker", 4): 2, ("leatherworker", 5): 2, ("librarian", 2): 3,
                 ("librarian", 3): 3, ("cleric", 3): 2, ("cleric", 4): 3, ("cleric", 5): 2, ("mason", 1): 2,
                 ("mason", 5): 2, ("farmer", 4): 2, ("farmer", 5): 2, ("cartographer", 3): 3}
XP = {1: 2, 2: 10, 3: 20, 4: 30, 5: 30}

# Única «de la zona» de cada familia (su mapa lo vende el cartógrafo de la familia, nivel 3).
ZONA = {"llanuras": "castillo", "bosque": "catedral", "oscuro": "torre_mago", "taiga": "salon_jarl",
        "nieve": "fortaleza_hielo", "desierto": "acueducto", "sabana": "coliseo", "jungla": "piramide",
        "pantano": "mansion", "cerezos": "palacio", "badlands": "acueducto", "costa": "galeon"}
MAPA_FAMILIA = dict(oficio="cartographer", nivel=3, precio=16, usos=3)

# Estilos fortificados: el juego puede lanzar en ellos un asedio (asalto de saqueadores) si un jugador con el presagio
# entra; el armero vende la botella ominosa más leve (amplificador 0: asalto de nivel 1). Desactivado por defecto.
FORTIFICADAS = ("oscuro_fortificada", "nieve_fortaleza", "badlands_canon")
ASEDIO = dict(oficio="weaponsmith", nivel=3, precio=10, usos=1)


def _c(key, es):
    return {"translate": key, "fallback": es}


def _dye(rgb):
    return {"minecraft:dyed_color": rgb}


def _ench(**lv):
    return {"minecraft:enchantments": {f"minecraft:{k}": v for k, v in lv.items()}}


def _trim(material, pattern):
    return {"minecraft:trim": {"material": f"minecraft:{material}", "pattern": f"minecraft:{pattern}"}}


def _pocion(pid):
    return {"minecraft:potion_contents": {"potion": f"minecraft:{pid}"}}


def _copia_cronica(sid):
    """Copia del relato de una única (sin la marca heraldia_historia: no cuenta para el desafío del cronista)."""
    from unicas._comun import botin
    mod = dict(unicas.modules())[sid]
    k = botin.historia_clave(sid)
    paginas = [_c(f"{k}.pagina{i + 1}", es) for i, (es, _) in enumerate(mod.HISTORIA["relato"])]
    nombre = _c(f"item.{NS}.trato.copia_cronica", "Copia de la Crónica de los Heraldos")
    e = botin.libro(paginas, nombre, "Crónica (copia)", botin.HISTORIA_AUTOR,
                    lore=[_c(f"item.{NS}.trato.copia_cronica.lore", "Copiada en el scriptorium de la abadía")])
    comps = dict(e["modifier"][0]["components"])
    del comps["minecraft:custom_name"]   # el nombre lo pone el trato (item_name + custom_name sin cursiva)
    return comps


# Tratos con carácter de cada estilo: (oficio, nivel, objeto, cantidad, esmeraldas, (es, en) nombre, (es, en) lore,
# componentes extra, usos). Solo objetos vanilla con componentes; encantamientos moderados (como mucho nivel 3).
ESTILOS = {
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
                       ("Bendecida bajo la bóveda", "Blessed beneath the vault"), _pocion("healing"), 6)],
    "oscuro_alquimistas": [("cleric", 3, "potion", 1, 6, ("Elixir del herbolario", "Herbalist's Elixir"),
                            ("Raíz pálida y musgo", "Pale root and moss"), _pocion("regeneration"), 4)],
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
                        ("No preguntes qué lleva", "Don't ask what's in it"), _pocion("night_vision"), 4)],
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
    """Predicado de aldeano de Heraldia (Tags "heraldia"); con `structures` (lista de ids o etiqueta), además dentro de
    una pieza de esas estructuras. entity_tags lee las Tags sin serializar al aldeano."""
    if structures is None:   # el filtro de siempre de los mapas de los cartógrafos maestros (mismo JSON que antes)
        return {"type": "minecraft:entity_properties", "entity": "this", "predicate": {"nbt": "{Tags:[\"%s\"]}" % VILLAGER_TAG}}
    return {"type": "minecraft:entity_properties", "entity": "this", "predicate": {
        "minecraft:entity_tags": {"all_of": [VILLAGER_TAG]}, "minecraft:location": {"structures": structures}}}


def predicado(structures=None, *opciones):
    """merchant_predicate: aldeano de Heraldia (en esas estructuras) y opciones sí/no activadas (las opciones van
    primero: son lo más barato)."""
    v = villager_predicate(structures)
    if not opciones:
        return v
    return {"type": "minecraft:all_of", "terms": [{"type": f"{NS}:opcion", "clave": o} for o in opciones] + [v]}


def trato(precio, gives, *, extra=None, modifier=None, pred=None, usos=3, xp=10, descuento=0.05):
    """Trato de 26.3: `precio` esmeraldas (y `extra`, otro objeto que se pide) por `gives` ({id, count, components})."""
    t = {"wants": {"id": EM, "count": precio}}
    if extra:
        t["additional_wants"] = extra
    t["gives"] = gives
    if modifier:
        t["given_item_modifier"] = modifier
    if pred:
        t["merchant_predicate"] = pred
    t.update(max_uses=usos, xp=xp, reputation_discount=descuento)
    return t


def nombre_clave(tid, n):
    return f"item.{NS}.trato.{tid}.{n}"


def estructuras_estilo(tid):
    return [f"{NS}:{tid}", f"{NS}:{tid}_grande"]


def tratos_estilo(tid):
    """[(id del trato, oficio, nivel, trato)] de un estilo."""
    out = []
    for n, (prof, lvl, item, count, price, name, lore, comps, uses) in enumerate(ESTILOS.get(tid, ())):
        key = nombre_clave(tid, n)
        if isinstance(comps, str) and comps.startswith("cronica:"):
            comps = _copia_cronica(comps.split(":", 1)[1])
        c = dict(comps)
        c["minecraft:item_name"] = _c(key, name[0])
        if item == "written_book":   # el título del libro haría de nombre: custom_name sin cursiva (botin.libro)
            c["minecraft:custom_name"] = dict(_c(key, name[0]), italic=False)
        if lore:
            c["minecraft:lore"] = [dict(_c(key + ".lore", lore[0]), color="gray", italic=False)]
        gives = {"id": f"minecraft:{item}", "count": count, "components": c}
        out.append((f"{NS}:estilos/{tid}/{n}", prof, lvl,
                    trato(price, gives, pred=predicado(estructuras_estilo(tid), OPCION_ESTILO), usos=uses, xp=XP[lvl])))
    if tid in FORTIFICADAS:
        a = ASEDIO
        gives = {"id": "minecraft:ominous_bottle", "count": 1, "components": {
            "minecraft:ominous_bottle_amplifier": 0, "minecraft:item_name": _c(f"item.{NS}.trato.asedio", "Desafío del asedio"),
            "minecraft:lore": [dict(_c(f"item.{NS}.trato.asedio.lore", "Bébela y vuelve a la aldea: llegarán los saqueadores"),
                                    color="gray", italic=False)]}}
        out.append((f"{NS}:estilos/{tid}/asedio", a["oficio"], a["nivel"],
                    trato(a["precio"], gives, pred=predicado(estructuras_estilo(tid), OPCION_ASEDIOS), usos=a["usos"],
                          xp=XP[a["nivel"]])))
    return out


def tratos_familia(fam, modules):
    """Mapa de la única de la zona de la familia en sus cartógrafos (si esa única existe)."""
    import mapas
    sid = ZONA.get(fam)
    mods = dict(modules)
    if sid not in mods:
        return []
    m = MAPA_FAMILIA
    t = trato(m["precio"], {"id": "minecraft:filled_map"}, extra={"id": "minecraft:compass"},
              modifier=mapas.item_modifier(sid, mods[sid]), pred=predicado(f"#{NS}:aldeas/{fam}", OPCION_ESTILO),
              usos=m["usos"], xp=XP[m["nivel"]])
    return [(f"{NS}:familias/{fam}/mapa", m["oficio"], m["nivel"], t)]


def todos(modules):
    """[(id, oficio, nivel, trato)] de Heraldia: mapas de los maestros cartógrafos, de cada familia y de cada estilo."""
    import mapas
    out = [(f"{NS}:cartografo/{sid}", "cartographer", 5, mapas.trade(sid, mod)) for sid, mod in modules]
    for fam in FAMILIES:
        out += tratos_familia(fam, modules)
    for th in THEMES:
        out += tratos_estilo(th["id"])
    return out


def errores(modules):
    """Contrato de los datos: estilos existentes, oficio y nivel con su cuenta de tratos vanilla, precios y niveles de
    encantamiento moderados, y ningún objeto prohibido."""
    from unicas._comun import botin
    ids = {th["id"] for th in THEMES}
    e = [f"tratos.ESTILOS: estilo desconocido {t}" for t in ESTILOS if t not in ids]
    for tid in ids:
        if not 1 <= len(ESTILOS.get(tid, ())) <= 2:
            e.append(f"tratos.ESTILOS: el estilo {tid} debe tener 1-2 tratos propios")
    e += [f"tratos.FORTIFICADAS: estilo desconocido {t}" for t in FORTIFICADAS if t not in ids]
    for tid_, prof, lvl, t in todos(modules):
        if (prof, lvl) not in NIVEL_VANILLA and not tid_.startswith(f"{NS}:cartografo/"):
            e.append(f"{tid_}: {prof} nivel {lvl} no está en NIVEL_VANILLA (cuenta sus tratos vanilla)")
        if not 1 <= t["wants"]["count"] <= 64:
            e.append(f"{tid_}: precio fuera de 1-64 esmeraldas")
        g = t["gives"]
        if any(p in g["id"] for p in botin.PROHIBIDOS):
            e.append(f"{tid_}: objeto prohibido {g['id']}")
        for k, v in (g.get("components", {}).get("minecraft:enchantments") or {}).items():
            if v > botin.MAX_NIVEL:
                e.append(f"{tid_}: {k} {v} pasa del nivel {botin.MAX_NIVEL}")
    return e


def objetos(modules):
    """Lo que piden y dan los tratos, como entradas de botín (para validar ids, adornos y encantamientos)."""
    out = []
    for _, _, _, t in todos(modules):
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
    for tid, lst in ESTILOS.items():
        for n, (_, _, _, _, _, name, lore, _, _) in enumerate(lst):
            k = nombre_clave(tid, n)
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
    """Escribe cada trato y suma su id a la etiqueta de su oficio y nivel (sin reemplazar la vanilla)."""
    tags = {}
    for tid_, prof, lvl, t in todos(modules):
        jdump(out, f"data/{NS}/villager_trade/{tid_.split(':', 1)[1]}.json", t)
        tags.setdefault((prof, lvl), []).append(tid_)
    for (prof, lvl), values in sorted(tags.items()):
        jdump(out, f"data/minecraft/tags/villager_trade/{prof}/level_{lvl}.json", {"replace": False, "values": values})
