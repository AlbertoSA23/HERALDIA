"""Medium structures: smaller than a unique structure (from 11 x 11 to 40 x 40 blocks), more frequent (by default one every
~400-800 blocks among all of them), with modest loot (no premium chest) and few entities. Each module of this package
(medianas/<id>.py) defines a type; the generator discovers it on its own (no need to touch main.py, pack.py or writer.py).

Contract of each module:
  DISPLAY_NAME = {"es_es": "Torre de vigía", "en_us": "Watchtower"}      # required (name in /heraldia info and advancements)
  SEPARATION = 640              # blocks between two of the same type, by default (option medianas.<id>.separacion_bloques)
  STYLES = {"<estilo>": dict(  # each style is a structure heraldia:medianas/<id>/<estilo>, in its biome
      biomas=["minecraft:taiga", ...],            # vanilla list -> tag heraldia:medianas/<id>/<estilo>
      convencionales=["c:is_taiga", ...],         # optional: extra tags (biomes.CONVENTIONAL, same rules)
      paleta={...},                               # whatever the variants need (materials)
      variantes={"a": fn, "b": fn})}              # fn(paleta, nombre) -> core.Template; same weight in its pool
  LOOT = {"<tabla>": tabla}     # heraldia:medianas/<id>/<tabla>; no "premium" or FORBIDDEN (modest loot)
  LANG = {"es_es": {...}, "en_us": {...}}          # optional: own texts (same keys in both languages)
  ADVANCEMENT_ICON = "minecraft:spyglass"               # optional: type icon in the medium structures advancement
  BIOME_NEIGHBORS = 2                                # optional: biomes in strips (beaches); see colocacion
  DIMENSION = "nether"                             # optional: "nether" or "end" (dimensions.py; by default the
                                                   # overworld): type heraldia:dimension, which looks for the floor under
                                                   # the Nether roof or on an outer End island
  YIELDS_TO_MINES = True                              # optional: yields the spot to mine entrances (tag
                                                   # heraldia:medianas/ceden_a_minas; common/MediumStructures.yieldsToMine in Java)
  ADVANCEMENTS = [dict(id="pesca", icono="minecraft:cod", titulo=(es, en), descripcion=(es, en),   # optional: own
                tabla="pesca")]       # advancements (heraldia:medianas/<id>/<advancement id>, children of "Al borde del camino"):
                                      # open a container from that LOOT table, or own `criteria` instead of `tbl`
Templates (names medianas/<id>/<estilo>/<variante>): a single rigid piece with y = 0 at ground level, the entrance
(jigsaw heraldia:entrance, mediana.entrada) on the north face (z = 0) and nothing that gives life to the courtyard floor (path,
gravel, packed mud...: no trees grow inside). The entities (few: MAX_ENTITIES) carry the tags
heraldia_mediana and heraldia_mediana.<id> (mediana.marcar) and, for mobs, persistent and anchored (core.anclado).
They pass the generic audit of lint.py (supports, doors, stairs, accesses) and `errors` (this contract).

The generator also writes: the structure (single-piece jigsaw, beard_thin) and the biome tag of each style,
the structure_set heraldia:medianas/<id> (grid heraldia:rejilla, group medianas/<id>, origin shifted by the salt;
exclusion zone in front of vanilla villages), the structure tags heraldia:medianas (all of them) and
heraldia:medianas/<id>, the loot, the texts and the options (options.py). In the game, comun/Medianas.java discards a
medium structure next to a Heraldia village or unique structure that actually generate and next to another medium structure of higher rank (the same
rule as the minimum distance between unique structures); Atlantis already excludes everything that falls in its zone.
"""
import importlib, pkgutil, zlib
from core import NS, nsid

PREFIX = "medianas"
MIN_SIDE, MAX_SIDE, MAX_HEIGHT = 11, 40, 32     # footprint in blocks (x y z) and height of each template
MAX_ENTITIES = 4                              # per template
MAX_GENERATORS = 1
MARK = "heraldia_mediana"                     # Tags of every entity of a medium structure (and heraldia_mediana.<id>)
# Modest loot: no premium chest or unique structure chest items.
FORBIDDEN = ("diamond", "netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "music_disc")
SEPARATION_RANGE = (256, 4000)
VANILLA_VILLAGE_EXCLUSION = 8                   # chunks (128 blocks) to the candidate of a vanilla village
YIELD_TO_MINES = f"{PREFIX}/ceden_a_minas"     # etiqueta de estructura (comun/Medianas.YIELD_TO_MINES en Java)
BIOME_Y = 96                                   # height at which the grid looks for the candidate's biome


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
    """[(id, module)] sorted by id, for deterministic output."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            found.append((published_id(info.name), importlib.import_module(f"{__name__}.{info.name}")))
    return sorted(found)


def salt(mid):
    """Stable salt per type (own grid; GridPlacement shifts the origin according to it)."""
    return zlib.crc32(f"{NS}:{PREFIX}/{mid}".encode()) & 0x7FFFFFFF


def key_name(mid):
    return f"{NS}.{PREFIX}.{mid}.nombre"


def template(mid, style, variant):
    return f"{PREFIX}/{mid}/{style}/{variant}"


def table_ident(mid, tbl):
    return f"{NS}:{PREFIX}/{mid}/{tbl}"


# ------------------------------------------------------------------ construction
def dimension(mod):
    import dimensions
    return dimensions.dimension_of(mod)


def build(reg, mid):
    """Templates and pools of a type (a part of pack.build_all) and their contract errors."""
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
    """Contract of a type over its already built templates (and its module)."""
    import dimensions
    errs, pre = dimensions.errors(f"{PREFIX}/{mid}", mod), f"{PREFIX}/{mid}"
    n = getattr(mod, "DISPLAY_NAME", None) or {}
    if not (n.get("es_es") and n.get("en_us")):
        errs.append(f"{pre}: NOMBRE without es_es or en_us")
    vec = getattr(mod, "BIOME_NEIGHBORS", None)
    if vec is not None and not (isinstance(vec, int) and 1 <= vec <= 9):
        errs.append(f"{pre}: BIOMA_VECINOS {vec!r} fuera de 1-9")
    sep = getattr(mod, "SEPARATION", None)
    if not (isinstance(sep, int) and SEPARATION_RANGE[0] <= sep <= SEPARATION_RANGE[1]):
        errs.append(f"{pre}: SEPARACION {sep!r} fuera de {SEPARATION_RANGE}")
    loot = getattr(mod, "LOOT", {})
    if not loot:
        errs.append(f"{pre}: no LOOT")
    for name, tbl in loot.items():
        if "premium" in name:
            errs.append(f"{pre}: table '{name}': medium structures have no premium chest")
        for obj in _items(tbl):
            if any(p in obj for p in FORBIDDEN):
                errs.append(f"{pre}/{name}: {obj} is not modest loot (medianas.PROHIBIDO)")
        if dimension(mod) != dimensions.MAIN:
            errs += [f"{pre}/{name}: {o} rompe la progresión (dimensiones.PROHIBIDO)"
                     for o in dimensions.forbidden_items(_items(tbl))]
    for ex in getattr(mod, "ADVANCEMENTS", ()):
        if not all(ex.get(k) for k in ("id", "icono", "titulo", "descripcion")) or not (ex.get("tabla") or ex.get("criterios")):
            errs.append(f"{pre}: advancement {ex.get('id')!r} without id, icono, titulo, descripcion or tabla/criterios")
        elif ex.get("tabla") and ex["tabla"] not in loot:
            errs.append(f"{pre}: advancement {ex['id']} asks for table {ex['tabla']}, which is not in LOOT")
    lang = getattr(mod, "LANG", None)
    if lang and set(lang.get("es_es", {})) != set(lang.get("en_us", {})):
        errs.append(f"{pre}: LANG with different keys in es_es and en_us")
    if not mod.STYLES:
        errs.append(f"{pre}: no ESTILOS")
    used = set()
    for style, d in mod.STYLES.items():
        if not d.get("biomas") or not d.get("variantes"):
            errs.append(f"{pre}/{style}: no biomes or no variants")
        for v in d.get("variantes", {}):
            name = template(mid, style, v)
            t = reg.templates.get(name)
            if t is None:
                errs.append(f"{name}: has not been built")
                continue
            errs += [f"{name}: {e}" for e in template_errors(t, mid, loot, dimension(mod))]
            used |= {str(nbt["LootTable"]) for _, nbt in t.blocks.values() if nbt and nbt.get("LootTable")}
    for name in loot:
        if table_ident(mid, name) not in used:
            errs.append(f"{pre}: table {name} is not used by any container")
    return errs


def template_errors(t, mid, loot, dim="overworld"):
    from uniques._common.pieces import GUARDIAN_TAG
    import dimensions
    errs = []
    live = LIVE_FLOOR | (dimensions.LIVE_FLOOR if dim != dimensions.MAIN else set())
    sx, sy, sz = t.size()
    if not (MIN_SIDE <= sx <= MAX_SIDE and MIN_SIDE <= sz <= MAX_SIDE and sy <= MAX_HEIGHT):
        errs.append(f"size {sx} x {sy} x {sz} outside {MIN_SIDE}-{MAX_SIDE} (height {MAX_HEIGHT})")
    entrances = [j for j in t.jigsaws if j["name"] == f"{NS}:entrance"]
    if len(entrances) != 1 or entrances[0]["pos"][2] != 0:
        errs.append("must have a single entrance (mediana.entrada) on the north face")
    if len(t.entities) > MAX_ENTITIES:
        errs.append(f"{len(t.entities)} entities (maximum {MAX_ENTITIES})")
    for *_, n in t.entities:
        tags = n.get("Tags") or []
        if GUARDIAN_TAG in tags:
            errs.append("a medium structure has no final guardian (or trophy)")
        if n["id"] not in ("minecraft:armor_stand", "minecraft:item_frame") and not n.get("PersistenceRequired"):
            errs.append(f"{n['id']} without PersistenceRequired (it would despawn before anyone arrives)")
    generators = 0
    for (x, y, z), (st, nbt) in t.blocks.items():
        if st.startswith("minecraft:spawner"):
            generators += 1
        lt = nbt.get("LootTable") if nbt else None
        if lt and not (str(lt).startswith(f"{NS}:{PREFIX}/{mid}/") and str(lt).split("/")[-1] in loot):
            errs.append(f"container at {(x, y, z)} with a table that is not from its LOOT: {lt}")
        if y == 0 and st.split("[")[0] in live:
            errs.append(f"fertile ground at {(x, 0, z)}: trees and bushes would grow inside")
    if generators > MAX_GENERATORS:
        errs.append(f"{generators} spawners (maximum {MAX_GENERATORS})")
    if not any(nbt and nbt.get("LootTable") for _, nbt in t.blocks.values()):
        errs.append("no chest at all")
    return errs


# #minecraft:supports_vegetation (and the taiga boulders): see LESSONS, "Patio sin árboles".
LIVE_FLOOR = {f"minecraft:{b}" for b in ("dirt", "coarse_dirt", "rooted_dirt", "mud", "moss_block", "grass_block",
                                          "podzol", "mycelium", "stone", "granite", "diorite", "andesite", "deepslate",
                                          "tuff")}


# ------------------------------------------------------------------ escritura
def structure(mid, style, biomes, mod=None, height=MAX_HEIGHT, side=MAX_SIDE):
    """JSON of a style. In the Nether or the End (DIMENSION), heraldia:dimension (dimensions.structure): checks the ground
    at the corners of the footprint (`side`) and requires air for the template height (`height`) under the roof."""
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
    """heraldia:rejilla of the type; spacing and separation are the defaults (the Java side recalculates them with the config).
    With "bioma" (the tag of all its styles) the candidate of each cell is the point of the window furthest inside
    its biomes, not a random chunk (GridPlacement): with biomes covering 5-30 % of the world, at random almost all
    cells are lost (measured with MedianasFrecuenciaTest). Checked at y = BIOME_Y (above the terrain almost everywhere).
    The point must have 6 of its 9 mesh neighbors (at 64 blocks) in the biomes; a type of biomes in strips (the
    beaches, a few tens of blocks wide) asks for fewer with BIOME_NEIGHBORS (bioma_vecinos in the grid)."""
    import dimensions
    spacing = round(mod.SEPARATION / 16)
    out = {"type": f"{NS}:rejilla", "grupo": f"{PREFIX}/{mid}", "spacing": spacing, "separation": spacing // 3,
           "salt": salt(mid)}
    if dimensions.dimension_of(mod) != dimensions.MAIN:
        # Nether and End: random candidate in the cell (the biome search only reads the overworld's noise; their
        # biomes are large) and without the vanilla village zone, since there are none there
        return out
    out.update({"bioma": f"{NS}:{PREFIX}/{mid}", "bioma_y": BIOME_Y,
                "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": VANILLA_VILLAGE_EXCLUSION}})
    if getattr(mod, "BIOME_NEIGHBORS", None):
        out["bioma_vecinos"] = mod.BIOME_NEIGHBORS
    return out


def write(out, jdump):
    """Structures, biome and structure tags, structure_sets and loot. Returns the texts."""
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
        # tag of all its styles: the grid looks for each cell's candidate in it
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
    """Largest (height, side) of the variants of a Nether or End style (they are built again: write does not have
    the registry)."""
    height = side = 0
    for v, fn in d["variantes"].items():
        sx, sy, sz = fn(d["paleta"], template(mid, style, v)).size()
        height, side = max(height, sy), max(side, sx, sz)
    return height, side
def yield_to_mines():
    """Structures (styles) of the types that yield the spot to mine entrances (YIELDS_TO_MINES)."""
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
    """{short id: table} of all the medium structures' loot (for validate_loot)."""
    return {f"{mid}/{n}": t for mid, mod in modules() for n, t in mod.LOOT.items()}
