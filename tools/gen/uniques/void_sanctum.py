"""Unique structure "Void Sanctum" (End, outer islands, far from the central island and the dragon): the sanctuary of
an order that worshipped the void between the islands. A rigid 33 x 33 template: an end stone brick platform
with a ring of eight purpur pillars crowned with end rods, three chapels in the corners (the reliquary,
the endermite chapel with its spawner and the sacristy) and a fourth with no visible door (the hidden crypt, behind
a piston door with a lever), and in the middle the temple (unicas/_recinto): corridor with a plate trap and arrows, nave
of the Hierophant (the guardian, an evoker with phases), treasure chamber behind an iron door with buttons and the high
choir with the library.

It is placed with heraldia:dimension (dimensions.py): the centre and the corners must be on an island (no void
underneath) and more than 1,024 blocks from the centre of the End. Loot that does not break progression: no elytra, nothing from the dragon, no
netherite (dimensions.FORBIDDEN); at most a shulker shell."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from uniques._common.chest_loot import pool
from uniques import _enclosure as r
import dimensions

SID = "sagrario_vacio"
P = f"unicas/{SID}"
NSP = f"heraldia:{P}"
DIMENSION = dimensions.END
SIDE = 33
HEIGHT = r.HEIGHT + 2
BIOME_MAP = ["end_highlands", "end_midlands"]

STRUCTURE = dict(biomes=[f"minecraft:{b}" for b in BIOME_MAP], start_pool=f"{P}/inicio", size=1, max_distance=40,
                 terrain_adaptation="beard_thin", step="surface_structures", spacing=125, separation=95,
                 json=dimensions.structure(f"{P}/inicio", [f"minecraft:{b}" for b in BIOME_MAP], 1, 40,
                                             dimensions.END, 12, HEIGHT + dimensions.SLACK))
DISPLAY_NAME = {"es_es": "Sagrario del Vacío", "en_us": "Sanctum of the Void"}
MAP = {"decoration": "minecraft:red_x"}
REINFORCEMENTS = ["vindicator", "stray"]      # bosses.py: the ones the Hierophant calls when dropping below 66 % and 33 %
TROPHY = {"objeto": "ender_eye", "rareza": "epic",
          "nombre": ("Ojo del Hierofante", "The Hierophant's Eye"),
          "lore": [("Miraba al vacío hasta que el vacío le devolvió la mirada.",
                    "It gazed into the void until the void gazed back.")]}
STORY = {
    "cofre": "oculto",
    "relato": [
        ("Más allá del dragón, en las islas que flotan sobre la nada, una orden levantó un sagrario de púrpura. Rezaban"
         " al vacío entre las islas y su hierofante me enseñó a orientarme por las varas que brillan.",
         "Beyond the dragon, on the islands that float above nothing, an order raised a sanctum of purpur. They prayed"
         " to the void between the islands, and their hierophant taught me to find my way by the shining rods."),
        ("Le confié mi pliego y lo selló en la cripta oculta. Cuando me fui, el hierofante seguía mirando al vacío. Dicen"
         " que ya no parpadea y que los espíritus le obedecen.",
         "I entrusted him with my leaf and he sealed it in the hidden crypt. When I left, the hierophant was still"
         " staring into the void. They say he no longer blinks and that the spirits obey him."),
    ],
    "pista": ("el End, más allá del dragón, donde un sagrario de púrpura rodeado de pilares mira al vacío",
              "the End, beyond the dragon, where a purpur sanctum ringed with pillars gazes into the void"),
}
ADVANCEMENT = {"icono": "minecraft:purpur_pillar"}

_T = {
    "guardian": ("Hierofante del Vacío", "Hierophant of the Void"),
    "baculo": ("Báculo del Coro", "Choir Staff"),
    "corona": ("Diadema del Vacío", "Void Diadem"),
}
LANG = chest_loot.lang(f"heraldia.{SID}.", _T)


def text(k):
    return pieces.text(f"heraldia.{SID}.{k}", _T[k][0])


LOOT = {
    "premium": chest_loot.place_chest(
        ((3, 5), [item("ender_pearl", 10, 2, 5), item("diamond", 3, 1, 2), item("emerald", 6, 2, 6),
                  item("amethyst_shard", 6, 3, 8), item("shulker_shell", 1), item("golden_apple", 4),
                  item("book", 4, ench=(15, 25)), item("experience_bottle", 4, 2, 5),
                  chest_loot.named("golden_helmet", 3, f"heraldia.{SID}.corona", _T["corona"][0], levels=(10, 20)),
                  item("spire_armor_trim_smithing_template", 2), item("music_disc_otherside", 1)]),
        ((1, 2), [item("ender_eye", 3, 1, 2), item("diamond", 2), item("emerald", 4, 1, 3), empty(6)])),
    "cuartel": chest_loot.place_chest(((2, 4), [item("chorus_fruit", 8, 2, 6), item("popped_chorus_fruit", 5, 1, 4),
                                     item("arrow", 6, 4, 10), item("candle", 5, 1, 3), item("iron_ingot", 5, 1, 3),
                                     item("ender_pearl", 3, 1, 2), empty(5)]),
                           ((1, 1), [item("gold_ingot", 3, 1, 2), item("emerald", 3, 1, 2), empty(8)])),
    "relicario": chest_loot.place_chest(((2, 4), [item("amethyst_shard", 6, 2, 6), item("candle", 5, 1, 3), item("gold_ingot", 4, 1, 3),
                                       item("end_rod", 4, 1, 3), item("ender_eye", 2),
                                       chest_loot.named("blaze_rod", 1, f"heraldia.{SID}.baculo", _T["baculo"][0]),
                                       item("purple_banner", 2), empty(4)]),
                             ((1, 1), [item("emerald", 3, 1, 3), item("golden_apple", 1), empty(8)])),
    "sacristia": chest_loot.place_chest(((2, 4), [item("chorus_fruit", 8, 2, 6), item("glass_bottle", 5, 1, 3), item("candle", 5, 1, 3),
                                       item("purple_wool", 4, 1, 3), item("iron_nugget", 5, 2, 6), empty(5)]),
                             ((1, 1), [item("ender_pearl", 3), item("emerald", 2), empty(8)])),
    "forja": chest_loot.table(pool((1, 3), [item("iron_nugget", 6, 2, 6), item("gold_nugget", 6, 2, 6), item("purpur_block", 5, 2, 6),
                                       item("end_rod", 3, 1, 2), item("chorus_fruit", 4, 1, 3), empty(6)])),
    "biblioteca": chest_loot.place_chest(((2, 4), [item("paper", 8, 2, 6), item("book", 6, 1, 3), item("book", 3, rand_ench=True),
                                        item("map", 3), item("ink_sac", 4, 1, 3), item("feather", 4, 1, 3), empty(5)]),
                              ((1, 1), [item("experience_bottle", 3, 1, 3), item("ender_pearl", 2), empty(8)])),
    "oculto": chest_loot.place_chest(((2, 4), [item("ender_pearl", 6, 1, 3), item("amethyst_shard", 6, 3, 8), item("diamond", 1),
                                    item("emerald", 5, 1, 4), item("ender_eye", 3), item("obsidian", 3, 1, 3), empty(4)]),
                          ((1, 1), [item("golden_apple", 2), item("experience_bottle", 3, 2, 4), empty(6)])),
}

PALETTE = dict(piso="purpur_block", muro="purpur_block", esquina="purpur_pillar[axis=y]", forjado="end_stone_bricks",
              almena="end_stone_brick_wall", puerta="birch_door", columna="purpur_pillar[axis=y]", tesoro="purpur_pillar[axis=y]")
CHAPEL = dict(PALETTE, muro="end_stone_bricks", piso="end_stone_bricks", forjado="purpur_block", almena="purpur_slab")
PLATFORM = ["minecraft:end_stone_bricks", "minecraft:end_stone_bricks", "minecraft:purpur_block",
              "minecraft:end_stone_bricks", "minecraft:purpur_pillar[axis=y]"]
PILLARS = [(6, 3), (16, 2), (26, 3), (30, 16), (26, 29), (16, 30), (6, 29), (2, 16)]


def place_chest(t, x, y, z, facing, tbl, kind="chest"):
    if kind == "barrel":
        t.barrel(x, y, z, facing="up", loot=f"{NSP}/{tbl}")
    else:
        pieces.chest(lambda *a, **k: t.set(*a, **k), x, y, z, facing, f"{NSP}/{tbl}")


def guardian():
    k = text("guardian")
    return pieces.guardian("evoker", k["translate"], k["fallback"], 70.0, armor=4,
                           attributes={"knockback_resistance": 0.3})


def construction():
    t = Template(f"{P}/sagrario")
    n = SIDE - 1
    # platform with air above and a border of slabs
    for x in range(SIDE):
        for z in range(SIDE):
            edge_block = x in (0, n) or z in (0, n)
            t.set(x, 0, z, "minecraft:purpur_block" if edge_block else PLATFORM[(x * 5 + z * 11 + x * z) % len(PLATFORM)])
            for y in range(1, 10):
                t.set(x, y, z, "air", keep=True)
            if edge_block and (x + z) % 4 == 0 and not 14 <= x <= 18:
                t.set(x, 1, z, "end_stone_brick_wall")
    # ring of pillars with end rods (the light of the void)
    for x, z in PILLARS:
        for y in range(1, 7):
            t.set(x, y, z, "purpur_pillar[axis=y]")
        t.set(x, 7, z, "end_rod[facing=up]")
    # corner chapels
    r.tower(t, CHAPEL, 0, 0, 5, (4, 2, "east"), merlon=False)
    place_chest(t, 2, 1, 1, "south", "relicario")
    t.set(1, 1, 3, "candle[candles=4,lit=true,waterlogged=false]")
    r.tower(t, CHAPEL, n - 4, 0, 5, (n - 4, 2, "west"), merlon=False)
    pieces.spawner(t.set, n - 2, 1, 2, "endermite")
    r.tower(t, CHAPEL, 0, n - 4, 5, (4, n - 2, "east"), merlon=False)
    place_chest(t, 2, 1, n - 1, "north", "sacristia")
    place_chest(t, 1, 1, n - 1, "north", "forja", "barrel")
    is_open = r.hidden(t, CHAPEL, n - 4, n - 4)
    place_chest(t, n - 2, 1, n - 1, "north", "oculto")
    t.set(n - 1, 1, n - 3, "candle[candles=2,lit=true,waterlogged=false]")
    # the temple in the middle
    r.great_tower(t, PALETTE, 9, 10, place_chest, guardian())
    for x in (12, 20):                                    # flight of steps of the portal
        t.set(x, 1, 8, "end_rod[facing=up]")
    pieces.connect(t)
    t.lint_open = is_open
    t.jigsaw(16, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
             final_state="minecraft:purpur_block")
    return t


def build(reg):
    t = construction()
    reg.add(t, f"unica:{SID}")
    reg.pool(f"{P}/inicio", [(t.name, 1, "rigid", None)])
