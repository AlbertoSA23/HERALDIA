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

PREFIJO = "medianas"
MIN_LADO, MAX_LADO, MAX_ALTO = 11, 40, 32     # huella en bloques (x y z) y altura de cada plantilla
MAX_ENTIDADES = 4                              # por plantilla
MAX_GENERADORES = 1
MARCA = "heraldia_mediana"                     # Tags de toda entidad de una mediana (y heraldia_mediana.<id>)
# Botín modesto: sin cofre premium ni objetos de cofre de única.
PROHIBIDO = ("diamond", "netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "music_disc")
SEPARACION_RANGO = (256, 4000)
EXCLUSION_ALDEAS_VANILLA = 8                   # chunks (128 bloques) hasta la candidata de una aldea vanilla
BIOMA_Y = 96                                   # altura a la que la rejilla busca el bioma de la candidata


def modules():
    """[(id, módulo)] ordenados por id, para una salida determinista."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            found.append((info.name, importlib.import_module(f"{__name__}.{info.name}")))
    return sorted(found)


def salt(mid):
    """Sal estable por tipo (rejilla propia; GridPlacement desplaza el origen según ella)."""
    return zlib.crc32(f"{NS}:{PREFIJO}/{mid}".encode()) & 0x7FFFFFFF


def nombre_clave(mid):
    return f"{NS}.{PREFIJO}.{mid}.nombre"


def plantilla(mid, estilo, variante):
    return f"{PREFIJO}/{mid}/{estilo}/{variante}"


def tabla_id(mid, tabla):
    return f"{NS}:{PREFIJO}/{mid}/{tabla}"


# ------------------------------------------------------------------ construcción
def build(reg, mid):
    """Plantillas y pools de un tipo (una parte de pack.build_all) y sus errores de contrato."""
    mod = dict(modules())[mid]
    for estilo, d in mod.ESTILOS.items():
        els = []
        for v, fn in d["variantes"].items():
            t = fn(d["paleta"], plantilla(mid, estilo, v))
            marcar_entidades(t, mid)
            els.append((reg.add(t, f"mediana:{mid}"), 1, "rigid", None))
        reg.pool(f"{PREFIJO}/{mid}/{estilo}", els)
    reg.warnings += errores(reg, mid, mod)


def marcar_entidades(t, mid):
    for *_, n in t.entities:
        tags = list(n.get("Tags") or [])
        n["Tags"] = tags + [m for m in (MARCA, f"{MARCA}.{mid}") if m not in tags]


def _objetos(tabla):
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
    walk(tabla)
    return out


def errores(reg, mid, mod):
    """Contrato de un tipo sobre sus plantillas ya construidas (y su módulo)."""
    errs, pre = [], f"{PREFIJO}/{mid}"
    n = getattr(mod, "NOMBRE", None) or {}
    if not (n.get("es_es") and n.get("en_us")):
        errs.append(f"{pre}: NOMBRE sin es_es o en_us")
    sep = getattr(mod, "SEPARACION", None)
    if not (isinstance(sep, int) and SEPARACION_RANGO[0] <= sep <= SEPARACION_RANGO[1]):
        errs.append(f"{pre}: SEPARACION {sep!r} fuera de {SEPARACION_RANGO}")
    loot = getattr(mod, "LOOT", {})
    if not loot:
        errs.append(f"{pre}: sin LOOT")
    for name, tabla in loot.items():
        if "premium" in name:
            errs.append(f"{pre}: tabla «{name}»: las medianas no tienen cofre premium")
        for obj in _objetos(tabla):
            if any(p in obj for p in PROHIBIDO):
                errs.append(f"{pre}/{name}: {obj} no es botín modesto (medianas.PROHIBIDO)")
    lang = getattr(mod, "LANG", None)
    if lang and set(lang.get("es_es", {})) != set(lang.get("en_us", {})):
        errs.append(f"{pre}: LANG con claves distintas en es_es y en_us")
    if not mod.ESTILOS:
        errs.append(f"{pre}: sin ESTILOS")
    usadas = set()
    for estilo, d in mod.ESTILOS.items():
        if not d.get("biomas") or not d.get("variantes"):
            errs.append(f"{pre}/{estilo}: sin biomas o sin variantes")
        for v in d.get("variantes", {}):
            name = plantilla(mid, estilo, v)
            t = reg.templates.get(name)
            if t is None:
                errs.append(f"{name}: no se ha construido")
                continue
            errs += [f"{name}: {e}" for e in plantilla_errores(t, mid, loot)]
            usadas |= {str(nbt["LootTable"]) for _, nbt in t.blocks.values() if nbt and nbt.get("LootTable")}
    for name in loot:
        if tabla_id(mid, name) not in usadas:
            errs.append(f"{pre}: la tabla {name} no la usa ningún contenedor")
    return errs


def plantilla_errores(t, mid, loot):
    from unicas._comun.piezas import GUARDIAN_TAG
    errs = []
    sx, sy, sz = t.size()
    if not (MIN_LADO <= sx <= MAX_LADO and MIN_LADO <= sz <= MAX_LADO and sy <= MAX_ALTO):
        errs.append(f"tamaño {sx} x {sy} x {sz} fuera de {MIN_LADO}-{MAX_LADO} (alto {MAX_ALTO})")
    entradas = [j for j in t.jigsaws if j["name"] == f"{NS}:entrance"]
    if len(entradas) != 1 or entradas[0]["pos"][2] != 0:
        errs.append("debe tener una sola entrada (mediana.entrada) en la cara norte")
    if len(t.entities) > MAX_ENTIDADES:
        errs.append(f"{len(t.entities)} entidades (máximo {MAX_ENTIDADES})")
    for *_, n in t.entities:
        tags = n.get("Tags") or []
        if GUARDIAN_TAG in tags:
            errs.append("una mediana no tiene guardián final (ni trofeo)")
        if n["id"] not in ("minecraft:armor_stand", "minecraft:item_frame") and not n.get("PersistenceRequired"):
            errs.append(f"{n['id']} sin PersistenceRequired (desaparecería antes de que llegue nadie)")
    generadores = 0
    for (x, y, z), (st, nbt) in t.blocks.items():
        if st.startswith("minecraft:spawner"):
            generadores += 1
        lt = nbt.get("LootTable") if nbt else None
        if lt and not (str(lt).startswith(f"{NS}:{PREFIJO}/{mid}/") and str(lt).split("/")[-1] in loot):
            errs.append(f"contenedor en {(x, y, z)} con una tabla que no es de su LOOT: {lt}")
        if y == 0 and st.split("[")[0] in SUELO_VIVO:
            errs.append(f"suelo fértil en {(x, 0, z)}: dentro nacerían árboles y matas")
    if generadores > MAX_GENERADORES:
        errs.append(f"{generadores} generadores (máximo {MAX_GENERADORES})")
    if not any(nbt and nbt.get("LootTable") for _, nbt in t.blocks.values()):
        errs.append("sin ningún cofre")
    return errs


# #minecraft:supports_vegetation (y los peñascos de la taiga): ver APRENDIZAJES, «Patio sin árboles».
SUELO_VIVO = {f"minecraft:{b}" for b in ("dirt", "coarse_dirt", "rooted_dirt", "mud", "moss_block", "grass_block",
                                          "podzol", "mycelium", "stone", "granite", "diorite", "andesite", "deepslate",
                                          "tuff")}


# ------------------------------------------------------------------ escritura
def estructura(mid, estilo, biomes):
    return {"type": "minecraft:jigsaw", "biomes": biomes, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "beard_thin", "start_pool": nsid(f"{PREFIJO}/{mid}/{estilo}"), "size": 1,
            "max_distance_from_center": 32, "start_height": {"absolute": 0},
            "project_start_to_heightmap": "WORLD_SURFACE_WG", "use_expansion_hack": False}


def colocacion(mid, mod):
    """heraldia:rejilla del tipo; spacing y separation son los de por defecto (el Java los recalcula con la config).
    Con «bioma» (la etiqueta de todos sus estilos) la candidata de cada casilla es el punto de la ventana más metido en
    sus biomas, no un chunk al azar (GridPlacement): con biomas que cubren el 5-30 % del mundo, al azar casi todas las
    casillas se pierden (medido con MedianasFrecuenciaTest). Mirado a y = BIOMA_Y (sobre el terreno de casi todo)."""
    spacing = round(mod.SEPARACION / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIJO}/{mid}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(mid), "bioma": f"{NS}:{PREFIJO}/{mid}", "bioma_y": BIOMA_Y,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": EXCLUSION_ALDEAS_VANILLA}}


def write(out, jdump):
    """Estructuras, etiquetas de biomas y de estructura, structure_sets y botín. Devuelve los textos."""
    import biomas
    from writer import lootr_aware
    todas = []
    for mid, mod in modules():
        ids = []
        for estilo, d in mod.ESTILOS.items():
            tag = f"{PREFIJO}/{mid}/{estilo}"
            if d.get("convencionales"):
                biomas.CONVENCIONALES[tag] = list(d["convencionales"])
            sid = f"{NS}:{tag}"
            jdump(out, f"data/{NS}/worldgen/structure/{tag}.json", estructura(mid, estilo, biomas.etiqueta(out, tag, d["biomas"])))
            ids.append(sid)
        # etiqueta de todos sus estilos: la rejilla busca la candidata de cada casilla en ella
        biomas.CONVENCIONALES[f"{PREFIJO}/{mid}"] = sorted({c for d in mod.ESTILOS.values() for c in d.get("convencionales", [])})
        biomas.etiqueta(out, f"{PREFIJO}/{mid}", sorted({b for d in mod.ESTILOS.values() for b in d["biomas"]}))
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIJO}/{mid}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": colocacion(mid, mod)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}/{mid}.json", {"values": ids})
        todas += ids
        for name, tabla in mod.LOOT.items():
            jdump(out, f"data/{NS}/loot_table/{PREFIJO}/{mid}/{name}.json", lootr_aware(tabla))
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIJO}.json", {"values": todas})
    return lang()


def lang():
    out = {"es_es": {}, "en_us": {}}
    for mid, mod in modules():
        for l in out:
            out[l][nombre_clave(mid)] = mod.NOMBRE[l]
            out[l].update(getattr(mod, "LANG", {}).get(l, {}))
    return out


def tablas():
    """{id corto: tabla} de todo el botín de las medianas (para validate_loot)."""
    return {f"{mid}/{n}": t for mid, mod in modules() for n, t in mod.LOOT.items()}
