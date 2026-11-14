"""Templo-pirámide: gran pirámide escalonada mesoamericana en la selva (diseño en docs/unicas/piramide.md)."""
from core import Template
from unicas import DEFAULT_SPACING, DEFAULT_SEPARATION
from . import obra, auditoria

STRUCTURE = dict(
    biomes=["minecraft:jungle", "minecraft:sparse_jungle"],
    start_pool="unicas/piramide/inicio",
    size=2, max_distance=80,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=DEFAULT_SPACING, separation=DEFAULT_SEPARATION,
)

NOMBRE = {"es_es": "Templo-pirámide", "en_us": "Pyramid Temple"}

K = "heraldia.piramide."
LANG = {
    "es_es": {K + "guardian": "El Rey Jaguar", K + "corona": "Corona del Rey Jaguar", K + "cetro": "Cetro de la Selva",
              K + "pectoral_oro": "Pectoral de Oro del Sacerdote", K + "garra": "Garra del Jaguar",
              K + "pectoral": "Pectoral del Rey"},
    "en_us": {K + "guardian": "The Jaguar King", K + "corona": "Crown of the Jaguar King", K + "cetro": "Scepter of the Jungle",
              K + "pectoral_oro": "Golden Pectoral of the Priest", K + "garra": "Claw of the Jaguar",
              K + "pectoral": "Pectoral of the King"},
}


# ------------------------------------------------------------------ botín
def it(name, w, lo=1, hi=1, *mods):
    m = list(mods)
    if hi > 1 or lo > 1:
        m.insert(0, {"type": "minecraft:set_count", "count": {"type": "minecraft:uniform", "min": lo, "max": hi}})
    e = {"type": "minecraft:item", "name": "minecraft:" + name, "weight": w}
    if m:
        e["modifier"] = m[0] if len(m) == 1 else m
    return e


def named(key):
    return {"type": "minecraft:set_name", "name": {"translate": K + key, "fallback": LANG["es_es"][K + key]},
            "target": "item_name"}


def ench(**lv):
    return {"type": "minecraft:set_enchantments", "enchantments": {"minecraft:" + k: v for k, v in lv.items()}}


def levels(a, b):
    return {"type": "minecraft:enchant_with_levels", "levels": {"type": "minecraft:uniform", "min": a, "max": b},
            "options": "#minecraft:on_random_loot"}


def empty(w):
    return {"type": "minecraft:empty", "weight": w}


def pool(rolls, entries, extra=False):
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


SELVA = [it("cocoa_beans", 8, 2, 6), it("melon_slice", 8, 2, 5), it("bread", 6, 1, 3), it("arrow", 8, 2, 8),
         it("bone", 6, 1, 3), it("string", 5, 1, 3), it("bamboo", 5, 2, 6), it("glow_berries", 4, 1, 3),
         it("candle", 3, 1, 2), it("gold_nugget", 10, 2, 7)]
METAL = [it("gold_ingot", 6, 1, 2), it("iron_ingot", 6, 1, 3), it("lapis_lazuli", 4, 2, 6), it("redstone", 3, 2, 5),
         it("emerald", 3), it("experience_bottle", 3, 1, 3), it("golden_carrot", 3, 1, 2), it("book", 2, 1, 1, levels(5, 15))]
SHERDS = [it("archer_pottery_sherd", 2), it("prize_pottery_sherd", 2), it("skull_pottery_sherd", 2), it("miner_pottery_sherd", 1)]

VISTOSO = table(pool(3, [
    it("golden_helmet", 3, 1, 1, named("corona"), ench(protection=2, unbreaking=2)),
    it("golden_sword", 3, 1, 1, named("cetro"), ench(sharpness=2, unbreaking=2)),
    it("golden_chestplate", 2, 1, 1, named("pectoral_oro"), ench(protection=2)),
    it("music_disc_otherside", 1), it("music_disc_relic", 1), it("music_disc_cat", 1), it("music_disc_chirp", 1),
    it("wild_armor_trim_smithing_template", 3), it("raiser_armor_trim_smithing_template", 1),
    it("wayfinder_armor_trim_smithing_template", 1), it("shaper_armor_trim_smithing_template", 1),
    it("host_armor_trim_smithing_template", 1), it("book", 2, 1, 1, levels(15, 25)), it("golden_apple", 2, 1, 2)] + SHERDS))
FUERTE = table(pool((1, 2), [
    it("diamond_sword", 3, 1, 1, named("garra"), levels(20, 30)),
    it("diamond_chestplate", 2, 1, 1, named("pectoral"), levels(20, 30)),
    it("enchanted_golden_apple", 2), it("diamond", 3, 3, 5)]))

LOOT = {
    "menor": table(pool((2, 4), SELVA + [it("emerald", 2), empty(6)]),
                   pool(1, [it("gold_ingot", 4), it("emerald", 3), it("iron_ingot", 3), it("lapis_lazuli", 3, 2, 5), empty(8)], True)),
    "galeria": table(pool((3, 5), SELVA + METAL),
                     pool((1, 2), [it("gold_ingot", 5, 1, 3), it("emerald", 4, 1, 2), it("iron_ingot", 4, 1, 3),
                                   it("name_tag", 1), it("saddle", 1), empty(6)], True)),
    "oculto": table(pool((3, 5), [it("gold_ingot", 8, 2, 4), it("emerald", 8, 2, 4), it("diamond", 2), it("golden_apple", 3),
                                  it("experience_bottle", 4, 2, 5), it("book", 3, 1, 1, levels(15, 25)),
                                  it("wild_armor_trim_smithing_template", 2)] + SHERDS),
                    pool((1, 2), [it("gold_ingot", 6, 1, 3), it("emerald", 6, 1, 3), it("diamond", 2), it("golden_carrot", 3, 1, 3),
                                  empty(4)], True)),
    "tumba": table(pool((3, 5), [it("gold_ingot", 10, 2, 5), it("emerald", 8, 2, 5), it("golden_helmet", 2, 1, 1, levels(10, 20)),
                                 it("golden_sword", 2, 1, 1, levels(10, 20)), it("wild_armor_trim_smithing_template", 3),
                                 it("music_disc_relic", 1), it("music_disc_otherside", 1), it("golden_apple", 3),
                                 it("experience_bottle", 4, 2, 5)] + SHERDS),
                   pool((1, 2), [it("gold_ingot", 6, 1, 3), it("emerald", 6, 1, 3), it("diamond", 1), empty(4)], True)),
    "premium": table(pool((3, 5), [it("gold_ingot", 8, 3, 7), it("emerald", 8, 3, 7), it("experience_bottle", 6, 4, 8),
                                   it("diamond", 2, 1, 2), it("gold_block", 1)]),
                     pool(1, [{"type": "minecraft:loot_table", "value": VISTOSO, "weight": 90},
                              {"type": "minecraft:loot_table", "value": FUERTE, "weight": 10}]),
                     pool((1, 2), [it("gold_ingot", 6, 2, 4), it("emerald", 6, 2, 4), it("diamond", 2), it("golden_apple", 2)], True)),
}


# ------------------------------------------------------------------ procesadores (ruina)
def rule(block, out, p):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": p},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


def processors(rules):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": rules}]}


def split(o):
    sup, sub = Template("unicas/piramide/superficie"), Template("unicas/piramide/subsuelo")
    for (x, y, z), (st, nbt) in o.t.blocks.items():
        (sup if y >= 0 else sub).blocks[(x, y, z)] = (st, nbt)
    for (x, y, z, n) in o.t.entities:
        (sup if y >= 0 else sub).entities.append((x, y, z, n))
    jx, jz = obra.CX, obra.CZ - 12
    assert o.get(jx, 0, jz) == "minecraft:tuff_bricks" and o.get(jx, -1, jz) == "minecraft:stone"
    sup.jigsaw(jx, 0, jz, "down_north", "unicas/piramide/abajo", "unicas/piramide/arriba", "unicas/piramide/subsuelo",
               final_state="minecraft:tuff_bricks")
    sub.jigsaw(jx, -1, jz, "up_north", "unicas/piramide/arriba", "minecraft:empty", "minecraft:empty",
               final_state="minecraft:stone")
    return sup, sub


def build(reg):
    o = obra.build_all()
    wear = auditoria.tune_wear(o)
    issues, stats, _ = auditoria.audit(o, wear)
    for msg, pos in issues[:30]:
        reg.warnings.append(f"unicas/piramide: {msg} en {pos}")
    sup, sub = split(o)
    reg.add(sup, "unica")
    reg.add(sub, "unica")
    reg.pool("unicas/piramide/inicio", [(sup.name, 1, "rigid", processors([
        rule("tuff_bricks", "tuff", wear), rule("polished_tuff", "tuff", wear),
        rule("red_terracotta", "terracotta", auditoria.WEAR["red_terracotta"])]))])
    reg.pool("unicas/piramide/subsuelo", [(sub.name, 1, "rigid", processors([
        rule("stone_bricks", "mossy_stone_bricks", 0.15), rule("stone_bricks", "cracked_stone_bricks", 0.12),
        rule("deepslate_tiles", "cracked_deepslate_tiles", 0.12), rule("deepslate_bricks", "cracked_deepslate_bricks", 0.12)]))])
    build.stats = stats
