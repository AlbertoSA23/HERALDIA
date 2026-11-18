"""Estructuras medianas: más pequeñas que una única (de 11 x 11 a 40 x 40 bloques), más frecuentes (por defecto una cada
~400-800 bloques entre todas), con botín modesto (sin cofre premium) y pocas entidades. Cada módulo de este paquete
(medianas/<id>.py) define un tipo; el generador lo descubre solo (no hace falta tocar main.py, pack.py ni writer.py).

Contrato de cada módulo:
  NOMBRE = {"es_es": "Torre de vigía", "en_us": "Watchtower"}      # obligatorio (nombre en /heraldia info y logros)
  SEPARACION = 640              # bloques entre dos del mismo tipo, por defecto (opción medianas.<id>.separacion_bloques)
  ESTILOS = {"<estilo>": dict(  # cada estilo es una estructura heraldia:medianas/<id>/<estilo>, en su bioma
      biomas=["minecraft:taiga", ...],            # lista vanilla -> etiqueta heraldia:medianas/<id>/<estilo>
      convencionales=["c:is_taiga", ...],         # opcional: etiquetas extra (biomas.CONVENCIONALES, mismas reglas)
      paleta={...},                               # lo que necesiten las variantes (materiales)
      variantes={"a": fn, "b": fn})}              # fn(paleta, nombre) -> core.Template; mismo peso en su pool
  LOOT = {"<tabla>": tabla}     # heraldia:medianas/<id>/<tabla>; nada de «premium» ni de PROHIBIDO (botín modesto)
  LANG = {"es_es": {...}, "en_us": {...}}          # opcional: textos propios (mismas claves en los dos idiomas)
  LOGRO_ICONO = "minecraft:spyglass"               # opcional: icono del tipo en el logro de las medianas
  BIOMA_VECINOS = 2                                # opcional: biomas en franja (playas); ver colocacion
  DIMENSION = "nether"                             # opcional: "nether" o "end" (dimensiones.py; por defecto el mundo
                                                   # principal): tipo heraldia:dimension, que busca el suelo bajo el
                                                   # techo del Nether o sobre una isla exterior del End
  CEDE_A_MINAS = True                              # opcional: cede el sitio a las entradas a mina (etiqueta
                                                   # heraldia:medianas/ceden_a_minas; comun/Medianas.cedeMina en Java)
  LOGROS = [dict(id="pesca", icono="minecraft:cod", titulo=(es, en), descripcion=(es, en),   # opcional: logros
                tabla="pesca")]       # propios (heraldia:medianas/<id>/<id del logro>, hijos de «Al borde del camino»):
                                      # abrir un contenedor de esa tabla de LOOT, o `criterios` propios en vez de `tabla`
Plantillas (nombres medianas/<id>/<estilo>/<variante>): una sola pieza rígida con y = 0 a ras de suelo, la entrada
(jigsaw heraldia:entrance, mediana.entrada) en la cara norte (z = 0) y nada que dé vida al suelo del patio (camino,
grava, barro compacto...: dentro no nacen árboles). Las entidades (pocas: MAX_ENTIDADES) llevan las etiquetas
heraldia_mediana y heraldia_mediana.<id> (mediana.marcar) y, los mobs, persistentes y anclados (core.anclado).
Pasan la auditoría genérica de lint.py (apoyos, puertas, escaleras, accesos) y `errores` (este contrato).

El generador escribe además: la estructura (jigsaw de una pieza, beard_thin) y la etiqueta de biomas de cada estilo,
el structure_set heraldia:medianas/<id> (rejilla heraldia:rejilla, grupo medianas/<id>, origen desplazado por la sal;
zona de exclusión frente a las aldeas vanilla), las etiquetas de estructura heraldia:medianas (todas) y
heraldia:medianas/<id>, el botín, los textos y las opciones (opciones.py). En el juego, comun/Medianas.java descarta una
mediana junto a una aldea o una única de Heraldia que salen de verdad y junto a otra mediana de rango mayor (la misma
regla que la distancia mínima entre únicas); la Atlántida ya excluye todo lo que caiga en su zona.
"""
import importlib, pkgutil, zlib
from core import NS, nsid

PREFIX = "medianas"
MIN_SIDE, MAX_SIDE, MAX_HEIGHT = 11, 40, 32     # huella en bloques (x y z) y altura de cada plantilla
MAX_ENTITIES = 4                              # por plantilla
MAX_GENERATORS = 1
MARK = "heraldia_mediana"                     # Tags de toda entidad de una mediana (y heraldia_mediana.<id>)
# Botín modesto: sin cofre premium ni objetos de cofre de única.
FORBIDDEN = ("diamond", "netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "music_disc")
SEPARATION_RANGE = (256, 4000)
VANILLA_VILLAGE_EXCLUSION = 8                   # chunks (128 bloques) hasta la candidata de una aldea vanilla
YIELD_TO_MINES = f"{PREFIX}/ceden_a_minas"     # etiqueta de estructura (comun/Medianas.CEDEN_A_MINAS en Java)
BIOME_Y = 96                                   # altura a la que la rejilla busca el bioma de la candidata


# Published id of each module whose name is not its id: the id (heraldia:medianas/<id>, its tags, options,
# advancements and translation keys) is already in players' worlds and configurations, so it never changes;
# a new module is published under its own name.
PUBLISHED_IDS = {
    "basalt_lookout": "atalaya_basalto",
    "camp": "campamento",
    "fisherman": "pescador",
    "hermitage": "ermita",
    "hunters": "cazadores",
    "inn": "posada",
    "magma_altar": "altar_magma",
    "mill": "molino",
    "mushroom_sanctuary": "santuario_hongos",
    "piglin_outpost": "puesto_piglin",
    "purpur_mausoleum": "mausoleo_purpura",
    "shrine": "templete",
    "shulker_dock": "embarcadero_shulker",
    "void_observatory": "observatorio_vacio",
    "watchtower": "torre_vigia",
    "wizard_hut": "choza_mago",
}


def published_id(module_name):
    return PUBLISHED_IDS.get(module_name, module_name)


def module_name(sid):
    """Module name of the published id sid (the inverse of published_id)."""
    return next((m for m, i in PUBLISHED_IDS.items() if i == sid), sid)


def modules():
    """[(id, módulo)] ordenados por id, para una salida determinista."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            found.append((published_id(info.name), importlib.import_module(f"{__name__}.{info.name}")))
    return sorted(found)


def salt(mid):
    """Sal estable por tipo (rejilla propia; GridPlacement desplaza el origen según ella)."""
    return zlib.crc32(f"{NS}:{PREFIX}/{mid}".encode()) & 0x7FFFFFFF


def key_name(mid):
    return f"{NS}.{PREFIX}.{mid}.nombre"


def template(mid, style, variant):
    return f"{PREFIX}/{mid}/{style}/{variant}"


def table_ident(mid, tbl):
    return f"{NS}:{PREFIX}/{mid}/{tbl}"


# ------------------------------------------------------------------ construcción
def dimension(mod):
    import dimensions
    return dimensions.dimension_of(mod)


def build(reg, mid):
    """Plantillas y pools de un tipo (una parte de pack.build_all) y sus errores de contrato."""
    mod = dict(modules())[mid]
    for style, d in mod.STYLES.items():
        els = []
        for v, fn in d["variantes"].items():
            t = fn(d["paleta"], template(mid, style, v))
            mark_entities(t, mid)
            els.append((reg.add(t, f"mediana:{mid}"), 1, "rigid", None))
        reg.pool(f"{PREFIX}/{mid}/{style}", els)
    reg.warnings += errors(reg, mid, mod)


def mark_entities(t, mid):
    for *_, n in t.entities:
        tags = list(n.get("Tags") or [])
        n["Tags"] = tags + [m for m in (MARK, f"{MARK}.{mid}") if m not in tags]


def _items(tbl):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "minecraft:item" and isinstance(o.get("name"), str):
                out.append(o["name"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tbl)
    return out


def errors(reg, mid, mod):
    """Contrato de un tipo sobre sus plantillas ya construidas (y su módulo)."""
    import dimensions
    errs, pre = dimensions.errors(f"{PREFIX}/{mid}", mod), f"{PREFIX}/{mid}"
    n = getattr(mod, "DISPLAY_NAME", None) or {}
    if not (n.get("es_es") and n.get("en_us")):
        errs.append(f"{pre}: NOMBRE sin es_es o en_us")
    vec = getattr(mod, "BIOME_NEIGHBORS", None)
    if vec is not None and not (isinstance(vec, int) and 1 <= vec <= 9):
        errs.append(f"{pre}: BIOMA_VECINOS {vec!r} fuera de 1-9")
    sep = getattr(mod, "SEPARATION", None)
    if not (isinstance(sep, int) and SEPARATION_RANGE[0] <= sep <= SEPARATION_RANGE[1]):
        errs.append(f"{pre}: SEPARACION {sep!r} fuera de {SEPARATION_RANGE}")
    loot = getattr(mod, "LOOT", {})
    if not loot:
        errs.append(f"{pre}: sin LOOT")
    for name, tbl in loot.items():
        if "premium" in name:
            errs.append(f"{pre}: tabla «{name}»: las medianas no tienen cofre premium")
        for obj in _items(tbl):
            if any(p in obj for p in FORBIDDEN):
                errs.append(f"{pre}/{name}: {obj} no es botín modesto (medianas.PROHIBIDO)")
        if dimension(mod) != dimensions.MAIN:
            errs += [f"{pre}/{name}: {o} rompe la progresión (dimensiones.PROHIBIDO)"
                     for o in dimensions.forbidden_items(_items(tbl))]
    for ex in getattr(mod, "ADVANCEMENTS", ()):
        if not all(ex.get(k) for k in ("id", "icono", "titulo", "descripcion")) or not (ex.get("tabla") or ex.get("criterios")):
            errs.append(f"{pre}: logro {ex.get('id')!r} sin id, icono, titulo, descripcion o tabla/criterios")
        elif ex.get("tabla") and ex["tabla"] not in loot:
            errs.append(f"{pre}: el logro {ex['id']} pide la tabla {ex['tabla']}, que no está en LOOT")
    lang = getattr(mod, "LANG", None)
    if lang and set(lang.get("es_es", {})) != set(lang.get("en_us", {})):
        errs.append(f"{pre}: LANG con claves distintas en es_es y en_us")
    if not mod.STYLES:
        errs.append(f"{pre}: sin ESTILOS")
    used = set()
    for style, d in mod.STYLES.items():
        if not d.get("biomas") or not d.get("variantes"):
            errs.append(f"{pre}/{style}: sin biomas o sin variantes")
        for v in d.get("variantes", {}):
            name = template(mid, style, v)
            t = reg.templates.get(name)
            if t is None:
                errs.append(f"{name}: no se ha construido")
                continue
            errs += [f"{name}: {e}" for e in template_errors(t, mid, loot, dimension(mod))]
            used |= {str(nbt["LootTable"]) for _, nbt in t.blocks.values() if nbt and nbt.get("LootTable")}
    for name in loot:
        if table_ident(mid, name) not in used:
            errs.append(f"{pre}: la tabla {name} no la usa ningún contenedor")
    return errs


def template_errors(t, mid, loot, dim="overworld"):
    from uniques._common.pieces import GUARDIAN_TAG
    import dimensions
    errs = []
    live = LIVE_FLOOR | (dimensions.LIVE_FLOOR if dim != dimensions.MAIN else set())
    sx, sy, sz = t.size()
    if not (MIN_SIDE <= sx <= MAX_SIDE and MIN_SIDE <= sz <= MAX_SIDE and sy <= MAX_HEIGHT):
        errs.append(f"tamaño {sx} x {sy} x {sz} fuera de {MIN_SIDE}-{MAX_SIDE} (alto {MAX_HEIGHT})")
    entrances = [j for j in t.jigsaws if j["name"] == f"{NS}:entrance"]
    if len(entrances) != 1 or entrances[0]["pos"][2] != 0:
        errs.append("debe tener una sola entrada (mediana.entrada) en la cara norte")
    if len(t.entities) > MAX_ENTITIES:
        errs.append(f"{len(t.entities)} entidades (máximo {MAX_ENTITIES})")
    for *_, n in t.entities:
        tags = n.get("Tags") or []
        if GUARDIAN_TAG in tags:
            errs.append("una mediana no tiene guardián final (ni trofeo)")
        if n["id"] not in ("minecraft:armor_stand", "minecraft:item_frame") and not n.get("PersistenceRequired"):
            errs.append(f"{n['id']} sin PersistenceRequired (desaparecería antes de que llegue nadie)")
    generators = 0
    for (x, y, z), (st, nbt) in t.blocks.items():
        if st.startswith("minecraft:spawner"):
            generators += 1
        lt = nbt.get("LootTable") if nbt else None
        if lt and not (str(lt).startswith(f"{NS}:{PREFIX}/{mid}/") and str(lt).split("/")[-1] in loot):
            errs.append(f"contenedor en {(x, y, z)} con una tabla que no es de su LOOT: {lt}")
        if y == 0 and st.split("[")[0] in live:
            errs.append(f"suelo fértil en {(x, 0, z)}: dentro nacerían árboles y matas")
    if generators > MAX_GENERATORS:
        errs.append(f"{generators} generadores (máximo {MAX_GENERATORS})")
    if not any(nbt and nbt.get("LootTable") for _, nbt in t.blocks.values()):
        errs.append("sin ningún cofre")
    return errs


# #minecraft:supports_vegetation (y los peñascos de la taiga): ver LESSONS, «Patio sin árboles».
LIVE_FLOOR = {f"minecraft:{b}" for b in ("dirt", "coarse_dirt", "rooted_dirt", "mud", "moss_block", "grass_block",
                                          "podzol", "mycelium", "stone", "granite", "diorite", "andesite", "deepslate",
                                          "tuff")}


# ------------------------------------------------------------------ escritura
def structure(mid, style, biomes, mod=None, height=MAX_HEIGHT, side=MAX_SIDE):
    """JSON de un estilo. En el Nether o el End (DIMENSION), heraldia:dimension (dimensiones.estructura): mira el suelo
    en las esquinas de la huella (`lado`) y pide aire para el alto de la plantilla (`alto`) bajo el techo."""
    import dimensions
    dim = dimensions.dimension_of(mod) if mod else dimensions.MAIN
    if dim != dimensions.MAIN:
        return dimensions.structure(f"{PREFIX}/{mid}/{style}", biomes, 1, 32, dim, side // 2,
                                      height + dimensions.SLACK)
    return {"type": "minecraft:jigsaw", "biomes": biomes, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "beard_thin", "start_pool": nsid(f"{PREFIX}/{mid}/{style}"), "size": 1,
            "max_distance_from_center": 32, "start_height": {"absolute": 0},
            "project_start_to_heightmap": "WORLD_SURFACE_WG", "use_expansion_hack": False}


def placement(mid, mod):
    """heraldia:rejilla del tipo; spacing y separation son los de por defecto (el Java los recalcula con la config).
    Con «bioma» (la etiqueta de todos sus estilos) la candidata de cada casilla es el punto de la ventana más metido en
    sus biomas, no un chunk al azar (GridPlacement): con biomas que cubren el 5-30 % del mundo, al azar casi todas las
    casillas se pierden (medido con MedianasFrecuenciaTest). Mirado a y = BIOMA_Y (sobre el terreno de casi todo).
    El punto debe tener 6 de sus 9 vecinos de la malla (a 64 bloques) en los biomas; un tipo de biomas en franja (las
    playas, de pocas decenas de bloques) pide menos con BIOMA_VECINOS (bioma_vecinos en la rejilla)."""
    import dimensions
    spacing = round(mod.SEPARATION / 16)
    out = {"type": f"{NS}:rejilla", "grupo": f"{PREFIX}/{mid}", "spacing": spacing, "separation": spacing // 3,
           "salt": salt(mid)}
    if dimensions.dimension_of(mod) != dimensions.MAIN:
        # Nether y End: candidata al azar en la casilla (la búsqueda de bioma solo lee el ruido del mundo principal; sus
        # biomas son grandes) y sin la zona de las aldeas vanilla, que allí no hay
        return out
    out.update({"bioma": f"{NS}:{PREFIX}/{mid}", "bioma_y": BIOME_Y,
                "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": VANILLA_VILLAGE_EXCLUSION}})
    if getattr(mod, "BIOME_NEIGHBORS", None):
        out["bioma_vecinos"] = mod.BIOME_NEIGHBORS
    return out


def write(out, jdump):
    """Estructuras, etiquetas de biomas y de estructura, structure_sets y botín. Devuelve los textos."""
    import biomes
    from writer import lootr_aware
    import treasure
    all_items = []
    for mid, mod in modules():
        ids = []
        for style, d in mod.STYLES.items():
            tag = f"{PREFIX}/{mid}/{style}"
            if d.get("convencionales"):
                biomes.CONVENTIONAL[tag] = list(d["convencionales"])
            sid = f"{NS}:{tag}"
            jdump(out, f"data/{NS}/worldgen/structure/{tag}.json", structure(mid, style, biomes.tag(out, tag, d["biomas"]),
                                                                              mod, *(_measures(mid, style, d) if dimension(mod) != "overworld" else ())))
            ids.append(sid)
        # etiqueta de todos sus estilos: la rejilla busca la candidata de cada casilla en ella
        biomes.CONVENTIONAL[f"{PREFIX}/{mid}"] = sorted({c for d in mod.STYLES.values() for c in d.get("convencionales", [])})
        biomes.tag(out, f"{PREFIX}/{mid}", sorted({b for d in mod.STYLES.values() for b in d["biomas"]}))
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIX}/{mid}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": placement(mid, mod)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}/{mid}.json", {"values": ids})
        all_items += ids
        for name, tbl in mod.LOOT.items():
            jdump(out, f"data/{NS}/loot_table/{PREFIX}/{mid}/{name}.json", lootr_aware(treasure.with_hint(tbl, "medianas")))
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}.json", {"values": all_items})
    jdump(out, f"data/{NS}/tags/worldgen/structure/{YIELD_TO_MINES}.json", {"values": yield_to_mines()})
    return lang()


def _measures(mid, style, d):
    """(alto, lado) mayores de las variantes de un estilo del Nether o el End (se construyen de nuevo: write no tiene
    el registro)."""
    height = side = 0
    for v, fn in d["variantes"].items():
        sx, sy, sz = fn(d["paleta"], template(mid, style, v)).size()
        height, side = max(height, sy), max(side, sx, sz)
    return height, side
def yield_to_mines():
    """Estructuras (estilos) de los tipos que ceden el sitio a las entradas a mina (CEDE_A_MINAS)."""
    return [f"{NS}:{PREFIX}/{mid}/{style}" for mid, mod in modules() if getattr(mod, "YIELDS_TO_MINES", False)
            for style in mod.STYLES]


def lang():
    out = {"es_es": {}, "en_us": {}}
    for mid, mod in modules():
        for l in out:
            out[l][key_name(mid)] = mod.DISPLAY_NAME[l]
            out[l].update(getattr(mod, "LANG", {}).get(l, {}))
    return out


def tables():
    """{id corto: tabla} de todo el botín de las medianas (para validate_loot)."""
    return {f"{mid}/{n}": t for mid, mod in modules() for n, t in mod.LOOT.items()}
