"""Templo-pirámide: gran pirámide escalonada mesoamericana en la selva (diseño en docs/unicas/piramide.md)."""
from core import Template
from uniques import DEFAULT_SPACING, DEFAULT_SEPARATION
from uniques._common import chest_loot
from . import construction, audit

STRUCTURE = dict(
    biomes=["minecraft:jungle", "minecraft:sparse_jungle"],
    start_pool="unicas/piramide/inicio",
    size=2, max_distance=80,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=DEFAULT_SPACING, separation=DEFAULT_SEPARATION,
)

DISPLAY_NAME = {"es_es": "Templo-pirámide", "en_us": "Pyramid Temple"}
TROPHY = {"objeto": "golden_chestplate", "rareza": "rare",
          "nombre": ("Pectoral del Rey Jaguar", "Breastplate of the Jaguar King"),
          "lore": [("El oro de la selva aún guarda su rugido.", "The jungle's gold still holds his roar.")],
          "encantamientos": {"minecraft:protection": 1},
          "componentes": {"minecraft:trim": {"material": "minecraft:emerald", "pattern": "minecraft:wild"}}}   # trofeo del guardián (_comun/botin.trofeo)
STORY = {   # su pliego de la Crónica de los Heraldos (docs/STORY.md, _comun/botin.historia_*)
    "cofre": "tumba",
    "relato": [
        ("En lo más espeso de la selva, un templo-pirámide escalonado asoma sobre los árboles. Sus "
         "sacerdotes servían al Rey Jaguar, que gobernaba desde lo alto con un pectoral de oro.",
         "In the thick of the jungle, a stepped pyramid temple rises above the trees. Its priests served "
         "the Jaguar King, who ruled from on high wearing a golden breastplate."),
        ("El rey aceptó el pliego como ofrenda y mandó sellarlo en una tumba bajo el templo. Juró rugir "
         "contra cualquier ladrón hasta el fin de los tiempos. En la selva aún se oye su rugido.",
         "The king accepted the leaf as an offering and had it sealed in a tomb beneath the temple. He "
         "swore to roar at every thief until the end of time. In the jungle his roar is still heard."),
    ],
    "pista": ("la selva, donde un templo-pirámide escalonado asoma sobre los árboles",
              "the jungle, where a stepped pyramid temple rises above the trees"),
}
ADVANCEMENT = {"icono": "minecraft:mossy_stone_bricks"}   # logros.py

K = "heraldia.piramide."
LANG = chest_loot.lang(K, {
    "guardian": ("El Rey Jaguar", "The Jaguar King"), "corona": ("Corona del Rey Jaguar", "Crown of the Jaguar King"),
    "cetro": ("Cetro de la Selva", "Scepter of the Jungle"),
    "pectoral_oro": ("Pectoral de Oro del Sacerdote", "Golden Pectoral of the Priest"),
    "garra": ("Garra del Jaguar", "Claw of the Jaguar"), "pectoral": ("Pectoral del Rey", "Pectoral of the King")})


# ------------------------------------------------------------------ botín (piezas de unicas/_comun/botin.py)
def it(name, w, lo=1, hi=1, levels=None):
    return chest_loot.item(name, w, lo, hi, ench=levels)


def nm(name, w, key, ench=None, levels=None):
    return chest_loot.named(name, w, K + key, LANG["es_es"][K + key],
                       ench={"minecraft:" + k: v for k, v in (ench or {}).items()} or None, levels=levels)


pool, table, empty = chest_loot.pool, chest_loot.table, chest_loot.empty


JUNGLE = [it("cocoa_beans", 8, 2, 6), it("melon_slice", 8, 2, 5), it("bread", 6, 1, 3), it("arrow", 8, 2, 8),
         it("bone", 6, 1, 3), it("string", 5, 1, 3), it("bamboo", 5, 2, 6), it("glow_berries", 4, 1, 3),
         it("candle", 3, 1, 2), it("gold_nugget", 10, 2, 7)]
METAL = [it("gold_ingot", 6, 1, 2), it("iron_ingot", 6, 1, 3), it("lapis_lazuli", 4, 2, 6), it("redstone", 3, 2, 5),
         it("emerald", 3), it("experience_bottle", 3, 1, 3), it("golden_carrot", 3, 1, 2), it("book", 2, levels=(5, 15))]
SHERDS = [it("archer_pottery_sherd", 2), it("prize_pottery_sherd", 2), it("skull_pottery_sherd", 2), it("miner_pottery_sherd", 1)]

SHOWY = table(pool(3, [
    nm("golden_helmet", 3, "corona", dict(protection=2, unbreaking=2)),
    nm("golden_sword", 3, "cetro", dict(sharpness=2, unbreaking=2)),
    nm("golden_chestplate", 2, "pectoral_oro", dict(protection=2)),
    it("music_disc_otherside", 1), it("music_disc_relic", 1), it("music_disc_cat", 1), it("music_disc_chirp", 1),
    it("wild_armor_trim_smithing_template", 3), it("raiser_armor_trim_smithing_template", 1),
    it("wayfinder_armor_trim_smithing_template", 1), it("shaper_armor_trim_smithing_template", 1),
    it("host_armor_trim_smithing_template", 1), it("book", 2, levels=(15, 25)), it("golden_apple", 2, 1, 2)] + SHERDS))
FORT = table(pool((1, 2), [
    nm("diamond_sword", 3, "garra", levels=(20, 30)),
    nm("diamond_chestplate", 2, "pectoral", levels=(20, 30)),
    it("enchanted_golden_apple", 2), it("diamond", 3, 3, 5)]))

LOOT = {
    "menor": table(pool((2, 4), JUNGLE + [it("emerald", 2), empty(6)]),
                   pool(1, [it("gold_ingot", 4), it("emerald", 3), it("iron_ingot", 3), it("lapis_lazuli", 3, 2, 5), empty(8)], True)),
    "galeria": table(pool((3, 5), JUNGLE + METAL),
                     pool((1, 2), [it("gold_ingot", 5, 1, 3), it("emerald", 4, 1, 2), it("iron_ingot", 4, 1, 3),
                                   it("name_tag", 1), it("saddle", 1), empty(6)], True)),
    "oculto": table(pool((3, 5), [it("gold_ingot", 8, 2, 4), it("emerald", 8, 2, 4), it("diamond", 2), it("golden_apple", 3),
                                  it("experience_bottle", 4, 2, 5), it("book", 3, levels=(15, 25)),
                                  it("wild_armor_trim_smithing_template", 2)] + SHERDS),
                    pool((1, 2), [it("gold_ingot", 6, 1, 3), it("emerald", 6, 1, 3), it("diamond", 2), it("golden_carrot", 3, 1, 3),
                                  empty(4)], True)),
    "tumba": table(pool((3, 5), [it("gold_ingot", 10, 2, 5), it("emerald", 8, 2, 5), it("golden_helmet", 2, levels=(10, 20)),
                                 it("golden_sword", 2, levels=(10, 20)), it("wild_armor_trim_smithing_template", 3),
                                 it("music_disc_relic", 1), it("music_disc_otherside", 1), it("golden_apple", 3),
                                 it("experience_bottle", 4, 2, 5)] + SHERDS),
                   pool((1, 2), [it("gold_ingot", 6, 1, 3), it("emerald", 6, 1, 3), it("diamond", 1), empty(4)], True)),
    "premium": table(pool((3, 5), [it("gold_ingot", 8, 3, 7), it("emerald", 8, 3, 7), it("experience_bottle", 6, 4, 8),
                                   it("diamond", 2, 1, 2), it("gold_block", 1)]),
                     pool(1, [{"type": "minecraft:loot_table", "value": SHOWY, "weight": 90},
                              {"type": "minecraft:loot_table", "value": FORT, "weight": 10}]),
                     pool((1, 2), [it("gold_ingot", 6, 2, 4), it("emerald", 6, 2, 4), it("diamond", 2), it("golden_apple", 2)], True)),
}


# ------------------------------------------------------------------ procesadores (ruina)
def rule(block, out, p):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": p},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


def processors(rules):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": rules}]}


def split(o):
    area, sub = Template("unicas/piramide/superficie"), Template("unicas/piramide/subsuelo")
    for (x, y, z), (st, nbt) in o.t.blocks.items():
        (area if y >= 0 else sub).blocks[(x, y, z)] = (st, nbt)
    for (x, y, z, n) in o.t.entities:
        (area if y >= 0 else sub).entities.append((x, y, z, n))
    jx, jz = construction.CX, construction.CZ - 12
    assert o.get(jx, 0, jz) == "minecraft:tuff_bricks" and o.get(jx, -1, jz) == "minecraft:stone"
    area.jigsaw(jx, 0, jz, "down_north", "unicas/piramide/abajo", "unicas/piramide/arriba", "unicas/piramide/subsuelo",
               final_state="minecraft:tuff_bricks")
    sub.jigsaw(jx, -1, jz, "up_north", "unicas/piramide/arriba", "minecraft:empty", "minecraft:empty",
               final_state="minecraft:stone")
    return area, sub


def build(reg):
    o = construction.build_all()
    wear = audit.tune_wear(o)
    issues, stats, _ = audit.audit(o, wear)
    for msg, pos in issues[:30]:
        reg.warnings.append(f"unicas/piramide: {msg} en {pos}")
    area, sub = split(o)
    reg.add(area, "unica")
    reg.add(sub, "unica")
    reg.pool("unicas/piramide/inicio", [(area.name, 1, "rigid", processors([
        rule("tuff_bricks", "tuff", wear), rule("polished_tuff", "tuff", wear),
        rule("red_terracotta", "terracotta", audit.WEAR["red_terracotta"])]))])
    reg.pool("unicas/piramide/subsuelo", [(sub.name, 1, "rigid", processors([
        rule("stone_bricks", "mossy_stone_bricks", 0.15), rule("stone_bricks", "cracked_stone_bricks", 0.12),
        rule("deepslate_tiles", "cracked_deepslate_tiles", 0.12), rule("deepslate_bricks", "cracked_deepslate_bricks", 0.12)]))])
    build.stats = stats
