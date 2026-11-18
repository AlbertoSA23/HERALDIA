"""Lighthouses and shipwrecks of the coast (heraldia:costa/<type>/<style>/<variant>, T42).

  lighthouse  28-block tower on firm ground next to the water, with the light always on at the top (redstone lamp
              on a redstone block, no circuits), the keeper's house and a pier on piles.
              Variants: a, octagonal tower with bands and the keeper (a villager standing still with sea trades); b, square tower in
              stripes, the house on the other side and no one around.
  shipwreck   a broken Heraldia galleon, with one mast standing and its sail torn, the stump of another and the captain's cabin
              at the stern. Variants: a, run aground on the beach (bow in the sand, stern in the water); b, half-sunk in
              shallow water (the hold flooded, with an anchored drowned).

Styles by coast (the climate: the biome of the land and that of the sea in front): templada (stone and brick; oak),
calida (sandstone; jungle), fria (slate and dark stone; dark oak) and nevada (spruce wood and snow). Each style
states in `climates` which (land, sea) pairs belong to it; the four share all the pairs without overlapping
(test_costa checks it), so the structure_set of each type comes out with the style of its coast.

Each template is a single piece placed by the heraldia:costa type (Java, costa/): it looks for the shore around the
candidate (firm, low ground behind, water in front, with the depth the variant asks for), rotates the template so
that its +z faces the sea and puts its `anchor_point` on the shore. The lighthouse goes at terrain height (its foundations and piles go down
to the ground with heraldia:acueducto_hasta_el_suelo); the shipwreck, with the template's `sea_row` row at
sea level - 1. Below that row the template has no air (the water and sand inside the hull stay: nothing
spills), which audit.py checks. Placement: heraldia:rejilla (group costa/<type>, options faros.* and naufragios.*)
with the candidate on the beaches and the rule of costa/Costa.java (that of the mines: never next to villages, unique structures, medium structures,
mines nor vanilla or other-mod structures that poke out; between lighthouses and shipwrecks, the minimum distance of the medium structures).

Ids: structure, template and pool heraldia:costa/<type>/<style>/<variant>, structure_set heraldia:costa/<type>,
structure tags #heraldia:costa and #heraldia:costa/<type>, biome tags #heraldia:litoral (the beaches,
for the grid), #heraldia:litoral/<style> (its land), #heraldia:litoral/tierra/<group> and
#heraldia:litoral/mar/<group> (heraldia:costa is that of the coast village family), loot
heraldia:costa/<table> (restocked by loot/Reposicion), texts heraldia.costa.*.
"""
import functools
from core import NS, nsid
from . import constructions
from .chest_loot import LOOT

PREFIX = "costa"
# The biome tags go separately: heraldia:costa is already that of the coast village family.
BIOME_MAP = "litoral"
KINDS = ("faro", "naufragio")
VARIANTS = ("a", "b")
DISPLAY_NAME = {"faro": ("Faro", "Lighthouse"), "naufragio": ("Galeón naufragado", "Wrecked Galleon")}
# Options of each type (options.py): <OPTION>.activado and <OPTION>.separacion_bloques
OPTION = {"faro": "faros", "naufragio": "naufragios"}
SEPARATION = {"faro": 1024, "naufragio": 768}
SEPARATION_RANGE = (256, 4000)
SALT = {"faro": 1907261201, "naufragio": 1907261202}
VANILLA_VILLAGE_EXCLUSION = 8
BIOME_NEIGHBORS = 2                  # the beaches are strips a few tens of blocks wide (like the fisherman's hut)
MODE = {("faro", "a"): "faro", ("faro", "b"): "faro", ("naufragio", "a"): "encallado", ("naufragio", "b"): "hundido"}

# Land and sea biome groups (vanilla lists of 26.3). Each land biome of the coast is in a single group.
LAND = {
    "nevada": ["snowy_beach", "snowy_plains", "snowy_taiga", "ice_spikes", "grove", "snowy_slopes", "frozen_peaks",
               "jagged_peaks"],
    "rocosa": ["stony_shore", "windswept_hills", "windswept_gravelly_hills", "windswept_forest", "stony_peaks", "taiga",
               "old_growth_pine_taiga", "old_growth_spruce_taiga"],
    "calida": ["desert", "savanna", "savanna_plateau", "windswept_savanna", "badlands", "eroded_badlands",
               "wooded_badlands", "jungle", "sparse_jungle", "bamboo_jungle", "mangrove_swamp"],
    "templada": ["beach", "plains", "sunflower_plains", "forest", "flower_forest", "birch_forest",
                 "old_growth_birch_forest", "dark_forest", "pale_garden", "meadow", "cherry_grove", "swamp"],
}
SEA = {
    "todos": ["ocean", "deep_ocean", "cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean",
              "lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "calido": ["lukewarm_ocean", "deep_lukewarm_ocean", "warm_ocean"],
    "templado": ["ocean", "deep_ocean"],
    "frio": ["cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean"],
}
SEA["no_calido"] = SEA["templado"] + SEA["frio"]
# Grid candidate: on a beach (the shore is searched from there).
BEACHES = ["beach", "snowy_beach", "stony_shore"]

# Styles: (land, sea) pairs of the climate and their palette (lighthouse and shipwreck).
STYLES = {
    "templada": dict(
        climas=[("templada", "templado")],
        faro=dict(muro="stone_bricks", banda="bricks", zocalo="mossy_stone_bricks", esquina="chiseled_stone_bricks",
                  cimiento=["stone_bricks", "cobblestone", "stone_bricks", "andesite"], losa="stone_brick_slab",
                  escalon="stone_brick_stairs", madera="spruce", tronco="spruce_log", casa="spruce_planks",
                  teja="dark_oak_stairs", cumbrera="dark_oak_planks", cama="blue", aldeano="plains", nieve=False),
        barco=dict(madera="oak", tronco="spruce_log", banda="dark_oak_planks", vela="white_wool", nieve=False)),
    "calida": dict(
        climas=[("calida", "todos"), ("templada", "calido"), ("rocosa", "calido")],
        faro=dict(muro="smooth_sandstone", banda="cut_red_sandstone", zocalo="cut_sandstone", esquina="chiseled_sandstone",
                  cimiento=["sandstone", "smooth_sandstone", "sandstone", "cut_sandstone"], losa="smooth_sandstone_slab",
                  escalon="sandstone_stairs", madera="jungle", tronco="jungle_log", casa="birch_planks",
                  teja="jungle_stairs", cumbrera="jungle_planks", cama="yellow", aldeano="desert", nieve=False),
        barco=dict(madera="jungle", tronco="birch_log", banda="acacia_planks", vela="yellow_wool", nieve=False)),
    "fria": dict(
        climas=[("rocosa", "no_calido"), ("templada", "frio")],
        faro=dict(muro="deepslate_bricks", banda="polished_blackstone_bricks", zocalo="cobbled_deepslate",
                  esquina="polished_deepslate", cimiento=["cobbled_deepslate", "deepslate_tiles", "cobbled_deepslate", "tuff"],
                  losa="deepslate_tile_slab", escalon="deepslate_tile_stairs", madera="dark_oak", tronco="dark_oak_log",
                  casa="dark_oak_planks", teja="deepslate_tile_stairs", cumbrera="deepslate_tiles", cama="gray",
                  aldeano="taiga", nieve=False),
        barco=dict(madera="dark_oak", tronco="spruce_log", banda="spruce_planks", vela="gray_wool", nieve=False)),
    "nevada": dict(
        climas=[("nevada", "todos")],
        faro=dict(muro="spruce_planks", banda="stripped_spruce_wood", zocalo="cobblestone", esquina="stripped_spruce_log",
                  cimiento=["cobblestone", "stone_bricks", "cobblestone", "mossy_cobblestone"], losa="spruce_slab",
                  escalon="spruce_stairs", madera="spruce", tronco="spruce_log", casa="spruce_planks",
                  teja="spruce_stairs", cumbrera="dark_oak_planks", cama="white", aldeano="snow", nieve=True),
        barco=dict(madera="spruce", tronco="dark_oak_log", banda="dark_oak_planks", vela="light_gray_wool", nieve=True)),
}

# Advancements: enter a lighthouse, enter a shipwreck and open the cabin chest (advancements.py hangs them from the root).
ADVANCEMENTS = {
    "faro": dict(icono="minecraft:spyglass", titulo=("Luz en la costa", "Light on the Coast"),
                 descripcion=("Encuentra un faro de Heraldia", "Find a Heraldia lighthouse"),
                 criterio=("faro", f"#{NS}:costa/faro")),
    "naufragio": dict(icono="minecraft:oak_boat", titulo=("Restos del naufragio", "Flotsam and Jetsam"),
                      descripcion=("Encuentra un galeón naufragado en la costa", "Find a galleon wrecked on the coast"),
                      criterio=("naufragio", f"#{NS}:costa/naufragio")),
    "camarote": dict(icono="minecraft:compass", padre="naufragio", titulo=("El cofre del capitán", "The Captain's Chest"),
                     descripcion=("Abre el cofre del camarote de un galeón naufragado",
                                  "Open the cabin chest of a wrecked galleon"),
                     tabla="camarote"),
}
XP = {"faro": 20, "naufragio": 20, "camarote": 30}

TEXTS = {
    "farero": ("Farero", "Lighthouse Keeper"),
}

MAX_ENTITIES = 2
LIGHTHOUSE_HEIGHT = (20, 35)


def salt(kind):
    return SALT[kind]


def template(kind, style, variant):
    return f"{PREFIX}/{kind}/{style}/{variant}"


def table_ident(tbl):
    return f"{NS}:{PREFIX}/{tbl}"


# ------------------------------------------------------------------ construction
@functools.lru_cache(maxsize=None)
def construction(kind, style, variant):
    """Work of a variant (cached: built by build, the audit and the tests) and its metadata for Java (in
    coordinates of the already normalised template)."""
    pal = STYLES[style]["faro" if kind == "faro" else "barco"]
    o = constructions.construct(kind, variant, pal, template(kind, style, variant))
    x0, y0, z0, *_ = o.t.bounds()
    ax, az = o.anchor_point
    meta = dict(modo=MODE[(kind, variant)], ancla=[ax - x0, az - z0], tierra=list(o.land), mar=list(o.sea),
                fila_mar=(o.sea_row - y0) if o.sea_row is not None else -1)
    return o, (x0, y0, z0), meta


def build(reg, kind):
    """Templates and pools of a type (a part of pack.build_all) and the errors of its audit."""
    from . import audit
    for style in STYLES:
        for v in VARIANTS:
            o, _, _ = construction(kind, style, v)
            reg.warnings += [f"{o.t.name}: {e}" for e in audit.errors(o, kind)]
            reg.pool(template(kind, style, v), [(reg.add(_copy(o.t), f"costa:{kind}"), 1, "rigid", processors(kind))])


def _copy(t):
    """Another template with the same blocks (Registry.add normalises it: the cached work, used by the audit and the
    Java metadata, stays in design coordinates). The generic support audit does traverse it."""
    from core import Template
    c = Template(t.name)
    c.blocks, c.entities, c.jigsaws = dict(t.blocks), list(t.entities), [dict(j) for j in t.jigsaws]
    return c


# Processor of each type: what goes in the bottom row of the template (lighthouse foundations and piles; keel and bottom
# of the shipwreck hull) goes down to firm ground through the water. One per type: the pier planks of the
# lighthouse must not go down (those of the hull bottom must).
DEPTH_MAX = 12


def processors(kind):
    return f"{NS}:{PREFIX}/{kind}_suelo"


def descend(kind):
    """Blocks of the bottom row that the type's processor extends down to the ground (those of all its palettes)."""
    out = set()
    for d in STYLES.values():
        if kind == "faro":
            out |= {f"minecraft:{x}" for x in d["faro"]["cimiento"]} | {f"minecraft:{d['faro']['tronco']}"}
        else:
            out |= {f"minecraft:{d['barco']['tronco']}", f"minecraft:{d['barco']['madera']}_planks"}
    return sorted(out)


# ------------------------------------------------------------------ escritura
def structure(kind, style, variant):
    _, _, meta = construction(kind, style, variant)
    climates = [{"tierra": f"#{NS}:{BIOME_MAP}/tierra/{t}", "mar": f"#{NS}:{BIOME_MAP}/mar/{m}"}
              for t, m in STYLES[style]["climas"]]
    return {"type": f"{NS}:costa", "biomes": f"#{NS}:{BIOME_MAP}/{style}", "step": "surface_structures",
            "spawn_overrides": {}, "terrain_adaptation": "none", "start_pool": nsid(template(kind, style, variant)),
            "climas": climates, **meta}


def placement(kind):
    """heraldia:rejilla of the type (default spacing; the Java recalculates it with the configuration) with the candidate
    searched on the beaches."""
    spacing = round(SEPARATION[kind] / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIX}/{kind}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(kind), "bioma": f"{NS}:{BIOME_MAP}", "bioma_vecinos": BIOME_NEIGHBORS,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": VANILLA_VILLAGE_EXCLUSION}}


def land_of(style):
    return sorted({b for t, _ in STYLES[style]["climas"] for b in LAND[t]})


def write(out, jdump):
    """Structures, biome and structure tags, structure_sets, the processor and the loot."""
    import biomes
    from writer import lootr_aware, down_to_floor
    import treasure
    biomes.tag(out, BIOME_MAP, BEACHES)
    for g, lst in LAND.items():
        biomes.tag(out, f"{BIOME_MAP}/tierra/{g}", lst)
    for g, lst in SEA.items():
        biomes.tag(out, f"{BIOME_MAP}/mar/{g}", lst)
    for style in STYLES:
        biomes.tag(out, f"{BIOME_MAP}/{style}", land_of(style))
    for kind in KINDS:
        jdump(out, f"data/{NS}/worldgen/processor_list/{PREFIX}/{kind}_suelo.json",
              {"processors": [down_to_floor(descend(kind), DEPTH_MAX)]})
    all_items = []
    for kind in KINDS:
        ids = []
        for style in STYLES:
            for v in VARIANTS:
                jdump(out, f"data/{NS}/worldgen/structure/{template(kind, style, v)}.json", structure(kind, style, v))
                ids.append(f"{NS}:{template(kind, style, v)}")
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIX}/{kind}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": placement(kind)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}/{kind}.json", {"values": ids})
        all_items += ids
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}.json", {"values": all_items})
    for name, tbl in LOOT.items():
        if name == "camarote":          # a treasure hint, rare, in the captain's chest
            tbl = treasure.with_hint(tbl, PREFIX)
        jdump(out, f"data/{NS}/loot_table/{PREFIX}/{name}.json", lootr_aware(tbl))
    return lang()


LANG = {"es_es": {}, "en_us": {}}
for _t in KINDS:
    LANG["es_es"][f"{NS}.costa.{_t}.nombre"], LANG["en_us"][f"{NS}.costa.{_t}.nombre"] = DISPLAY_NAME[_t]
for _k, (_es, _en) in TEXTS.items():
    LANG["es_es"][f"{NS}.costa.{_k}"], LANG["en_us"][f"{NS}.costa.{_k}"] = _es, _en
# /heraldia info (those of status, web maps and review go with the others in admin.py)
LANG["es_es"][f"{NS}.info.costa"] = "Costa: faros %s, cada %s bloques; galeones naufragados %s, cada %s bloques; %s estructuras"
LANG["en_us"][f"{NS}.info.costa"] = "Coast: lighthouses %s, every %s blocks; wrecked galleons %s, every %s blocks; %s structures"


def lang():
    return {k: dict(v) for k, v in LANG.items()}


def tables():
    """{short id: table} of all the coast loot (for validate_loot)."""
    return {f"{PREFIX}/{n}": t for n, t in LOOT.items()}


def structures():
    """Ids of all the coast structures (for /heraldia info and the tests)."""
    return [f"{NS}:{template(t, e, v)}" for t in KINDS for e in STYLES for v in VARIANTS]
