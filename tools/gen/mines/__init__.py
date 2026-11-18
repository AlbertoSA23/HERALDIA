"""Mine entrances (heraldia:minas/<size>/<style>): mine mouths on real hillsides that genuinely descend to a
gallery of their own, in three sizes and five styles per biome (see blueprints.py and surface.py).

  sizes    pequena (mouth with tracks, minecart and lanterns), mediana (mining camp: foreman's cabin, pile of
           ore, cargo minecart and smelter) and grande (complex with the hoist tower and its pulley, tracks and a
           vertical shaft with a spiral staircase down to a larger two-level network).
  styles   montana (oak and stone), taiga (spruce; also snow), desierto (sandstone), badlands (terracotta) and
           picos (deepslate, on the peaks), each with two variants (a, b: the mirrored courtyard and another gallery).

Each template is a single piece: the courtyard and its foundation, the mouth, the descent and the gallery, without a box (what is excavated carries
its lining and two layers of shell; outside, nothing). It is placed by the own type heraldia:mina_entrada (Java, minas/), which looks for
a hillside: in front of the mouth dry, nearly flat terrain, behind it a mountain higher than the tunnel and above the gallery
enough rock (the `roof` samples). Its placement is the grid heraldia:rejilla (group minas/<size>, options
mines.entrances.*) and the rule of minas/Minas.java (never next to villages, unique structures, medium structures or vanilla structures that
poke out; between the three sizes, the minimum distance of the medium structures).

In addition, mines.vanilla.multiplicador multiplies the frequency of vanilla abandoned mines in new chunks
(heraldia:minas_vanilla, which replaces the placement of the structure_set minecraft:mineshafts; with 1, identical to vanilla).

Ids: structure, template and pool heraldia:minas/<size>/<style>/<variant> (one structure per variant: each
knows where its mouth is), structure_set heraldia:minas/<size> (its 10 structures; the biome chooses the style), structure
tags #heraldia:minas and #heraldia:minas/<size>, biome tags #heraldia:minas (all) and
#heraldia:minas/<style>, loot heraldia:minas/<table>, texts heraldia.minas.*.
"""
import functools
from core import NS, nsid
from . import blueprints, chest_loot as _loot
from .chest_loot import LOOT

PREFIX = "minas"
SIZES = ("pequena", "mediana", "grande")
DISPLAY_NAME = {"pequena": ("Boca de mina", "Mine Adit"), "mediana": ("Campamento minero", "Mining Camp"),
          "grande": ("Complejo minero", "Mining Complex")}
# separation between two of the same size (blocks): the small one is that of the option mines.entrances.separacion_bloques and
# the others keep the proportion (GridPlacement scales all three with the option)
SEPARATION = {"pequena": 768, "mediana": 1152, "grande": 1920}
SEPARATION_RANGE = (256, 4000)
SALT = {"pequena": 1907261101, "mediana": 1907261102, "grande": 1907261103}
BIOME_Y = 96
VANILLA_VILLAGE_EXCLUSION = 8
VARIANTS = ("a", "b")

# Styles by biome (vanilla lists; the extra tags follow the rules of biomes.CONVENTIONAL).
STYLES = {
    "montana": dict(
        biomas=["windswept_hills", "windswept_gravelly_hills", "windswept_forest", "meadow", "cherry_grove"],
        paleta=dict(madera="oak", tronco="minecraft:oak_log", tablas="oak_planks", cama="brown",
                    muro=["cobblestone", "cobblestone", "cobblestone", "mossy_cobblestone", "stone_bricks"],
                    techo=["cobblestone", "stone_bricks"], suelo=["cobblestone", "stone_bricks", "polished_andesite"],
                    escalon_piedra="cobblestone_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "packed_mud", "packed_mud", "cobblestone"], cimiento=["cobblestone", "mossy_cobblestone"],
                    mineral=["gravel", "cobblestone", "coal_ore", "iron_ore", "copper_ore", "stone"],
                    vetas=["coal_ore", "coal_ore", "iron_ore", "copper_ore"],
                    vetas_ricas=["iron_ore", "coal_ore", "copper_ore", "gold_ore", "redstone_ore", "lapis_ore"])),
    "taiga": dict(
        biomas=["taiga", "snowy_taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga", "grove", "snowy_slopes"],
        convencionales=["minecraft:is_taiga", "c:is_taiga"],
        paleta=dict(madera="spruce", tronco="minecraft:spruce_log", tablas="spruce_planks", cama="blue",
                    muro=["cobblestone", "cobblestone", "stone_bricks", "mossy_stone_bricks"],
                    techo=["cobblestone", "stone_bricks"], suelo=["cobblestone", "stone_bricks"],
                    escalon_piedra="cobblestone_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "packed_mud", "cobblestone", "packed_mud"], cimiento=["cobblestone", "stone_bricks"],
                    mineral=["gravel", "cobblestone", "coal_ore", "iron_ore", "iron_ore", "stone"],
                    vetas=["coal_ore", "iron_ore", "iron_ore", "copper_ore"],
                    vetas_ricas=["iron_ore", "coal_ore", "gold_ore", "lapis_ore", "redstone_ore", "copper_ore"])),
    "desierto": dict(
        biomas=["desert"], convencionales=["c:is_desert"],
        paleta=dict(madera="birch", tronco="minecraft:birch_log", tablas="birch_planks", cama="yellow",
                    muro=["sandstone", "sandstone", "cut_sandstone", "smooth_sandstone"],
                    techo=["cut_sandstone", "sandstone"], suelo=["sandstone", "smooth_sandstone"],
                    escalon_piedra="sandstone_stairs", casco="sandstone", casco_hondo="stone",
                    patio=["smooth_sandstone", "sandstone", "gravel"], cimiento=["sandstone", "cut_sandstone"],
                    mineral=["gravel", "sandstone", "coal_ore", "iron_ore", "copper_ore", "gold_ore"],
                    vetas=["coal_ore", "iron_ore", "copper_ore", "copper_ore"],
                    vetas_ricas=["gold_ore", "iron_ore", "copper_ore", "coal_ore", "lapis_ore", "redstone_ore"])),
    "badlands": dict(
        biomas=["badlands", "eroded_badlands", "wooded_badlands"], convencionales=["minecraft:is_badlands", "c:is_badlands"],
        paleta=dict(madera="dark_oak", tronco="minecraft:dark_oak_log", tablas="dark_oak_planks", cama="red",
                    muro=["terracotta", "orange_terracotta", "red_terracotta", "yellow_terracotta", "brown_terracotta",
                          "white_terracotta"],
                    techo=["terracotta", "red_sandstone"], suelo=["red_sandstone", "smooth_red_sandstone"],
                    escalon_piedra="red_sandstone_stairs", casco="terracotta", casco_hondo="stone",
                    patio=["smooth_red_sandstone", "red_sandstone", "gravel"], cimiento=["red_sandstone", "cut_red_sandstone"],
                    mineral=["gravel", "terracotta", "gold_ore", "iron_ore", "coal_ore", "red_sandstone"],
                    vetas=["gold_ore", "coal_ore", "iron_ore", "gold_ore"],
                    vetas_ricas=["gold_ore", "gold_ore", "iron_ore", "redstone_ore", "copper_ore", "coal_ore"])),
    "picos": dict(
        biomas=["jagged_peaks", "frozen_peaks", "stony_peaks"], convencionales=["c:is_mountain/peak"],
        paleta=dict(madera="spruce", tronco="minecraft:stripped_spruce_log", tablas="spruce_planks", cama="light_gray",
                    muro=["cobbled_deepslate", "cobbled_deepslate", "deepslate_bricks", "deepslate_tiles"],
                    techo=["deepslate_bricks", "cobbled_deepslate"], suelo=["polished_deepslate", "cobbled_deepslate"],
                    escalon_piedra="cobbled_deepslate_stairs", casco="stone", casco_hondo="deepslate",
                    patio=["gravel", "cobbled_deepslate", "polished_andesite"], cimiento=["cobbled_deepslate", "deepslate_bricks"],
                    mineral=["gravel", "cobbled_deepslate", "deepslate_iron_ore", "deepslate_coal_ore", "deepslate_copper_ore"],
                    vetas=["deepslate_coal_ore", "deepslate_iron_ore", "deepslate_copper_ore", "deepslate_iron_ore"],
                    vetas_ricas=["deepslate_iron_ore", "deepslate_gold_ore", "deepslate_redstone_ore", "deepslate_lapis_ore",
                                 "deepslate_copper_ore", "deepslate_coal_ore"])),
}

# Advancements: a small -> medium -> large chain (advancements.py adds them under the root).
ADVANCEMENTS = {
    "pequena": dict(icono="minecraft:minecart", titulo=("Bajo la ladera", "Under the Hillside"),
                    descripcion=("Entra en una boca de mina de Heraldia", "Enter a Heraldia mine adit")),
    "mediana": dict(icono="minecraft:iron_pickaxe", titulo=("Campamento minero", "Mining Camp"),
                    descripcion=("Entra en un campamento minero", "Enter a mining camp")),
    "grande": dict(icono="minecraft:chest_minecart", titulo=("Señor de las galerías", "Lord of the Galleries"),
                   descripcion=("Entra en un complejo minero con su torre de extracción",
                                "Enter a mining complex with its headframe")),
}
XP = {"pequena": 20, "mediana": 40, "grande": 80}

LANG = {
    "es_es": {f"{NS}.minas.{t}.nombre": DISPLAY_NAME[t][0] for t in SIZES},
    "en_us": {f"{NS}.minas.{t}.nombre": DISPLAY_NAME[t][1] for t in SIZES},
}
for _t, ((_es1, _en1), (_es2, _en2)) in blueprints.area.SIGNS.items():
    LANG["es_es"].update({f"{NS}.minas.cartel.{_t}.1": _es1, f"{NS}.minas.cartel.{_t}.2": _es2})
    LANG["en_us"].update({f"{NS}.minas.cartel.{_t}.1": _en1, f"{NS}.minas.cartel.{_t}.2": _en2})

MAX_ENTITIES = 6
MAX_GENERATORS = {"pequena": 0, "mediana": 1, "grande": 1}


def salt(size):
    return SALT[size]


def template(size, style, variant):
    return f"{PREFIX}/{size}/{style}/{variant}"


def table_ident(tbl):
    return f"{NS}:{PREFIX}/{tbl}"


# ------------------------------------------------------------------ construction
@functools.lru_cache(maxsize=None)
def construction(size, style, variant):
    """Work of a variant (cached: build, the audit and the tests construct it) and its metadata for Java."""
    pal = STYLES[style]["paleta"]
    o = blueprints.construct(size, style, variant, pal, template(size, style, variant))
    x0, y0, z0, *_ = o.t.bounds()
    sh = lambda x, y, z: (x - x0, y - y0, z - z0)
    px, pz = blueprints.SIZES[size]["patio"]
    meta = dict(entrada=list(sh(0, 0, 0)), patio=[-px - x0, -pz - z0, px - x0, -1 - z0],
                techo=[[x - x0, z - z0, y + 1] for (x, z), y in o.roof_samples()])
    return o, (x0, y0, z0), meta


def build(reg, size):
    """Templates and pools of a size (a part of pack.build_all) and the errors of its audit."""
    from . import audit
    for style in STYLES:
        for v in VARIANTS:     # one structure per variant: each with the position of its mouth in the template
            o, _, _ = construction(size, style, v)
            reg.warnings += [f"{o.t.name}: {e}" for e in audit.errors(o, size)]
            reg.pool(template(size, style, v), [(reg.add(_copy(o.t), f"mina:{size}"), 1, "rigid", None)])


def _copy(t):
    """Another template with the same blocks (Registry.add normalizes it and adds chains: the cached work, which the audit
    and the Java metadata use, stays in design coordinates)."""
    from core import Template
    c = Template(t.name)
    c.blocks, c.entities, c.jigsaws = dict(t.blocks), list(t.entities), [dict(j) for j in t.jigsaws]
    c.no_generic_audit = True
    return c


# ------------------------------------------------------------------ escritura
def structure(size, style, variant, biomes):
    _, _, meta = construction(size, style, variant)
    return {"type": f"{NS}:mina_entrada", "biomes": biomes, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "none", "start_pool": nsid(template(size, style, variant)), **meta}


def placement(size):
    """heraldia:rejilla of the size (default spacing and separation; the Java side recalculates them with the configuration)
    with the candidate searched in the biomes of all the styles (like the medium structures)."""
    spacing = round(SEPARATION[size] / 16)
    return {"type": f"{NS}:rejilla", "grupo": f"{PREFIX}/{size}", "spacing": spacing, "separation": spacing // 3,
            "salt": salt(size), "bioma": f"{NS}:{PREFIX}", "bioma_y": BIOME_Y,
            "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": VANILLA_VILLAGE_EXCLUSION}}


# Vanilla abandoned mines (structure_set minecraft:mineshafts of 26.3): the same placement with the own type, which
# multiplies the frequency by mines.vanilla.multiplicador (1 = exact vanilla: same grid, salt and roll).
VANILLA_SET = {"structures": [{"structure": "minecraft:mineshaft", "weight": 1},
                              {"structure": "minecraft:mineshaft_mesa", "weight": 1}],
               "placement": {"type": f"{NS}:minas_vanilla", "frequency": 0.004,
                             "frequency_reduction_method": "legacy_type_3", "salt": 0, "separation": 0, "spacing": 1}}
MULTIPLIER = (2.0, 1, 5)          # default, minimum and maximum of mines.vanilla.multiplicador


def write(out, jdump):
    """Structures, biome and structure tags, structure_sets, loot and the placement of the vanilla mines."""
    import biomes
    from writer import lootr_aware
    import treasure
    all_items = []
    biomes.CONVENTIONAL[PREFIX] = sorted({c for d in STYLES.values() for c in d.get("convencionales", [])})
    biomes.tag(out, PREFIX, sorted({b for d in STYLES.values() for b in d["biomas"]}))
    for style, d in STYLES.items():
        if d.get("convencionales"):
            biomes.CONVENTIONAL[f"{PREFIX}/{style}"] = list(d["convencionales"])
        biomes.tag(out, f"{PREFIX}/{style}", d["biomas"])
    for size in SIZES:
        ids = []
        for style in STYLES:
            for v in VARIANTS:
                jdump(out, f"data/{NS}/worldgen/structure/{template(size, style, v)}.json",
                      structure(size, style, v, f"#{NS}:{PREFIX}/{style}"))
                ids.append(f"{NS}:{template(size, style, v)}")
        jdump(out, f"data/{NS}/worldgen/structure_set/{PREFIX}/{size}.json",
              {"structures": [{"structure": s, "weight": 1} for s in ids], "placement": placement(size)})
        jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}/{size}.json", {"values": ids})
        all_items += ids
    jdump(out, f"data/{NS}/tags/worldgen/structure/{PREFIX}.json", {"values": all_items})
    for name, tbl in LOOT.items():
        jdump(out, f"data/{NS}/loot_table/{PREFIX}/{name}.json", lootr_aware(treasure.with_hint(tbl, "minas")))
    jdump(out, "data/minecraft/worldgen/structure_set/mineshafts.json", VANILLA_SET)
    return lang()


def lang():
    return {k: dict(v) for k, v in LANG.items()}


def tables():
    """{short id: table} of all the mines' loot (for validate_loot)."""
    return {f"{PREFIX}/{n}": t for n, t in LOOT.items()}


def structures():
    """Ids of all the mine structures (for /heraldia info and the tests)."""
    return [f"{NS}:{template(t, e, v)}" for t in SIZES for e in STYLES for v in VARIANTS]
