"""Estructura única «Observatorio»: observatorio astronómico abandonado en una cumbre ventosa.

Diseño completo en docs/unicas/observatorio.md. Se construye en una sola plantilla de diseño (coordenadas con
y = 0 en la losa de la planta baja) que se audita entera y luego se parte en dos piezas rígidas unidas por un
jigsaw vertical: superficie (y >= 0) y subsuelo (y < 0).
Uso para planos y renders: python3 tools/gen/unicas/observatorio.py --docs docs/unicas/observatorio
"""
import os, sys
from collections import deque

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import Template
from unicas._comun import piezas, redstone, botin
from unicas._comun.piezas import door
from unicas._comun.recorrido import shifted, walk, DY
from unicas._comun.botin import pool as _pool, table as _table
from loot import item, empty
import lint

SID = "observatorio"
P = f"unicas/{SID}"
NSP = f"heraldia:{P}"

STRUCTURE = dict(
    biomes=["minecraft:windswept_hills", "minecraft:windswept_gravelly_hills", "minecraft:windswept_savanna"],
    start_pool=f"{P}/inicio", size=3, max_distance=48, terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190)

NOMBRE = {"es_es": "Observatorio", "en_us": "Observatory"}

# ------------------------------------------------------------------ textos
_T = {
    "guardian": ("Custodio de las Estrellas", "Keeper of the Stars"),
    "catalejo": ("Catalejo del Astrónomo", "Astronomer's Spyglass"),
    "reloj": ("Reloj de las Estrellas", "Star Clock"),
    "brujula": ("Brújula Celeste", "Celestial Compass"),
    "yelmo": ("Yelmo del Vigía", "Watcher's Helm"),
}
LANG = {"es_es": {f"heraldia.{SID}.{k}": v[0] for k, v in _T.items()},
        "en_us": {f"heraldia.{SID}.{k}": v[1] for k, v in _T.items()}}


def text(k):
    return {"translate": f"heraldia.{SID}.{k}", "fallback": _T[k][0]}


# ------------------------------------------------------------------ botín
def nm(name, w, k, levels=None):
    return botin.named(name, w, f"heraldia.{SID}.{k}", _T[k][0], levels=levels)


LOOT = {
    "menor": _table(
        _pool((3, 5), [item("paper", 12, 2, 6), item("book", 8, 1, 2), item("candle", 8, 1, 3), item("bread", 10, 1, 3),
                       item("coal", 8, 2, 5), item("copper_ingot", 8, 1, 4), item("glass", 6, 2, 5),
                       item("glass_bottle", 4, 1, 2), item("amethyst_shard", 5, 1, 3), item("feather", 5, 1, 3),
                       item("ink_sac", 5, 1, 2), item("torch", 6, 2, 5), item("string", 4, 1, 3)]),
        _pool(1, [item("compass", 2), item("clock", 2), item("spyglass", 1), item("map", 3), empty(12)]),
        _pool((1, 2), [item("paper", 6, 1, 4), item("bread", 6, 1, 2), item("coal", 5, 1, 3), item("copper_ingot", 5, 1, 3),
                       item("iron_nugget", 4, 2, 6)], extra=True)),
    "archivo": _table(
        _pool((3, 5), [item("book", 12, 1, 3), item("paper", 10, 2, 8), item("map", 6), item("lapis_lazuli", 8, 2, 6),
                       item("gold_ingot", 6, 1, 3), item("experience_bottle", 6, 1, 3), item("writable_book", 4),
                       item("ink_sac", 4, 1, 3), item("bone", 5, 1, 3), item("rotten_flesh", 5, 1, 3)]),
        _pool(1, [item("book", 4, rand_ench=True), item("name_tag", 2), item("spyglass", 2), item("iron_ingot", 4, 2, 4),
                  empty(6)]),
        _pool((1, 2), [item("book", 5, 1, 2), item("lapis_lazuli", 5, 1, 4), item("gold_nugget", 5, 2, 6),
                       item("experience_bottle", 3, 1, 2)], extra=True)),
    "oculto": _table(
        _pool((3, 5), [item("emerald", 10, 2, 5), item("gold_ingot", 8, 2, 4), item("amethyst_shard", 8, 2, 6),
                       item("experience_bottle", 8, 2, 5), item("lapis_lazuli", 6, 3, 8), item("book", 5, ench=(10, 20)),
                       item("spyglass", 4), item("golden_apple", 2), item("diamond", 3, 1, 2),
                       item("globe_banner_pattern", 2), item("clock", 3), item("compass", 3)]),
        _pool((1, 2), [item("emerald", 5, 1, 3), item("gold_ingot", 5, 1, 2), item("experience_bottle", 4, 1, 3)],
              extra=True)),
    # 90 % vistoso (primer grupo siempre; el segundo da algo fuerte solo el 10 % de las veces)
    "premium": _table(
        _pool((4, 6), [nm("spyglass", 8, "catalejo"), nm("clock", 6, "reloj"),
                       nm("compass", 6, "brujula"), nm("iron_helmet", 5, "yelmo", (10, 20)),
                       item("wayfinder_armor_trim_smithing_template", 4), item("shaper_armor_trim_smithing_template", 4),
                       item("music_disc_far", 3), item("music_disc_mall", 3), item("globe_banner_pattern", 4),
                       item("gold_ingot", 8, 3, 8), item("amethyst_shard", 8, 4, 12), item("emerald", 8, 4, 10),
                       item("experience_bottle", 6, 3, 8), item("golden_carrot", 4, 4, 8), item("book", 5, rand_ench=True)]),
        _pool(1, [empty(90), item("diamond", 4, 2, 4), item("book", 3, ench=(25, 30)),
                  item("diamond_chestplate", 2, ench=(15, 25)), item("golden_apple", 1, 1, 2)]),
        _pool((2, 3), [item("gold_ingot", 6, 1, 4), item("emerald", 6, 2, 5), item("amethyst_shard", 5, 2, 6),
                       item("experience_bottle", 4, 2, 4)], extra=True)),
}

# ------------------------------------------------------------------ materiales
WALL, TRIM, ROOF = "stone_bricks", "polished_andesite", "stone_bricks"
PLANK, DARK = "spruce_planks", "dark_oak_planks"
CU, CU2, CU3 = "waxed_oxidized_cut_copper", "waxed_weathered_cut_copper", "waxed_oxidized_copper"
WALLB, FLOORB, CEILB, SHELL = "deepslate_bricks", "deepslate_tiles", "polished_deepslate", "stone"
SIDES = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0))
CX, CZ = 20, 20                    # centro de la rotonda
R_IN, R_OUT = 8.5 ** 2, 9.5 ** 2


def _b(st):
    return lint.bname(st)


def hang(t, x, y, z, kind="lantern"):
    t.set(x, y, z, f"{kind}[hanging=true]")


def stair(kind, facing, half="bottom"):
    return f"{kind}[facing={facing},half={half},shape=straight]"


def processors(rules):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": [
        {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + a, "probability": p},
         "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + b}
        for a, b, p in rules]}]}


def d2(x, z):
    return (x - CX) ** 2 + (z - CZ) ** 2


def window(t, x, y, z, kind="glass_pane", h=2):
    for k in range(h):
        t.set(x, y + k, z, kind)


def chest(t, x, y, z, facing, table):
    t.chest(x, y, z, facing, f"{NSP}/{table}")


# ------------------------------------------------------------------ superficie
GROUND = {"V": (12, 7, 28, 10), "L": (2, 7, 10, 19), "O": (30, 7, 38, 19), "W2": (2, 21, 10, 33),
          "E2": (30, 21, 38, 33), "GS": (12, 31, 28, 33)}
UPPER = {"GN": (12, 7, 28, 10), "D1": (2, 7, 10, 19), "ST": (30, 7, 38, 19), "D2": (2, 21, 10, 33),
         "E2": (30, 21, 38, 33), "GS": (12, 31, 28, 33)}
FLOORS = {"V": TRIM, "L": PLANK, "O": TRIM, "W2": PLANK, "E2": TRIM, "GS": TRIM,
          "GN": DARK, "D1": PLANK, "ST": DARK, "D2": PLANK}
FLIGHTS = []        # (x, y, z) de cada peldaño de los tramos principales: la auditoría exige pisarlos todos
DAMAGE = set()      # celdas de la envolvente con ruina diseñada (para el cálculo del estado)


def surface(t):
    t.fill(1, 0, 6, 39, 12, 34, WALL)
    for key, (x1, z1, x2, z2) in GROUND.items():
        t.air(x1, 1, z1, x2, 5, z2)
        t.fill(x1, 0, z1, x2, 0, z2, FLOORS[key])
    for key, (x1, z1, x2, z2) in UPPER.items():
        t.air(x1, 7, z1, x2, 11, z2)
        t.fill(x1, 6, z1, x2, 6, z2, FLOORS.get(key, TRIM))
    # rotonda: planetario abajo, sala del telescopio arriba, abierta a la cúpula
    for x in range(10, 31):
        for z in range(10, 31):
            dd = d2(x, z)
            if dd <= R_IN:
                t.air(x, 1, z, x, 5, z)
                t.air(x, 7, z, x, 11, z)
                ring = 30.25 < dd <= 42.25
                t.set(x, 0, z, "chiseled_polished_blackstone" if dd <= 2 else CU if ring else "polished_deepslate")
                star = (x * 7 + z * 13) % 11 == 0 and 4 < dd < 64
                t.set(x, 6, z, "sea_lantern" if star else "polished_blackstone")
            for y in range(12, 22):
                r = dd + (y - 12) ** 2
                if r <= R_IN:
                    t.set(x, y, z, "air")
                elif r <= R_OUT and dd <= R_OUT:
                    if y == 12:
                        t.set(x, y, z, TRIM)
                    else:
                        ang = (x - CX, z - CZ)
                        rib = ang[0] == 0 or ang[1] == 0 or abs(ang[0]) == abs(ang[1])
                        t.set(x, y, z, CU3 if rib else (CU2 if (x + y + z) % 5 == 0 else CU))
    # rendija de observación al norte
    for x in range(CX - 1, CX + 2):
        for z in range(10, CZ + 1):
            for y in range(15, 22):
                r = d2(x, z) + (y - 12) ** 2
                if R_IN < r <= R_OUT + 4:
                    t.set(x, y, z, "air")
    # paneles caídos al sureste de la cúpula (ruina) y sus escombros sobre el suelo del telescopio
    for x in range(24, 29):
        for z in range(24, 29):
            for y in range(14, 18):
                r = d2(x, z) + (y - 12) ** 2
                if R_IN < r <= R_OUT and (x + z) in (51, 52, 53) and y <= 16:
                    t.set(x, y, z, "air")
                    DAMAGE.add((x, y, z))
    for (x, z, st) in ((24, 24, "cobblestone"), (25, 23, f"{CU}_slab[type=bottom]"), (23, 25, f"{CU2}_slab[type=bottom]"),
                       (24, 25, "gravel")):
        t.set(x, 7, z, st)
    # cubierta, pretil, impostas y esquinas
    for x in range(1, 40):
        for z in range(6, 35):
            if d2(x, z) > R_OUT:
                t.set(x, 12, z, ROOF)
            edge = x in (1, 39) or z in (6, 34)
            if edge:
                t.set(x, 6, z, TRIM)
                t.set(x, 13, z, "stone_brick_wall")
    for x in (1, 11, 29, 39):
        for z in (6, 34):
            t.fill(x, 0, z, x, 12, z, TRIM)
            t.set(x, 13, z, "stone_bricks")
            t.set(x, 14, z, "lantern[hanging=false]")
    # esquina noreste del pretil derrumbada, con cascotes en la azotea
    for x, z in ((35, 6), (36, 6), (37, 6), (38, 6), (39, 6), (39, 7), (39, 8), (39, 9)):
        t.set(x, 13, z, "air")
        t.set(x, 14, z, "air")
        DAMAGE.add((x, 13, z))
    t.set(39, 12, 6, "cobblestone")
    DAMAGE.add((39, 12, 6))
    for x, z, st in ((37, 8, "cobblestone"), (36, 7, "stone_brick_slab[type=bottom]"), (38, 9, "mossy_cobblestone_slab[type=bottom]")):
        t.set(x, 13, z, st)

    # ---- fachada y ventanas
    for y0 in (2, 8):
        for x in (4, 8, 14, 17, 23, 26):
            window(t, x, y0, 6)
        for x in (4, 8, 14, 17, 20, 23, 26, 32, 36):
            window(t, x, y0, 34)
        for z in (10, 13, 16, 24, 27, 30):
            window(t, 1, y0, z)
            window(t, 39, y0, z)
        for x in (32, 36):
            window(t, x, y0, 6, "tinted_glass" if y0 == 2 else "glass_pane")
    for z, c in ((10, "purple"), (13, "light_blue"), (16, "cyan")):
        window(t, 39, 2, z, f"{c}_stained_glass_pane")
    # ventanas rotas del dormitorio (fachada oeste)
    for z in (13, 16):
        for y in (8, 9):
            t.set(1, y, z, "air")
            DAMAGE.add((1, y, z))
    # pretil sur caído sobre la galería, con cascotes; ventanas rotas del rellano este
    for x in range(13, 18):
        t.set(x, 13, 34, "air")
        DAMAGE.add((x, 13, 34))
    for x, st in ((13, "cobblestone"), (15, "stone_brick_slab[type=bottom]"), (16, "cobblestone")):
        t.set(x, 13, 33, st)
    for z in (24, 27):
        for y in (8, 9):
            t.set(39, y, z, "air")
            DAMAGE.add((39, y, z))
    # portada con reloj
    t.fill(19, 1, 6, 19, 4, 6, TRIM)
    t.fill(21, 1, 6, 21, 4, 6, TRIM)
    t.set(20, 3, 6, "chiseled_stone_bricks")
    t.set(20, 4, 6, "chiseled_stone_bricks")
    door(t.set, 20, 1, 6, "south", "dark_oak_door")
    t.set(19, 3, 5, "wall_torch[facing=north]")
    t.set(21, 3, 5, "wall_torch[facing=north]")
    for x in range(19, 22):
        for y in range(8, 11):
            t.set(x, y, 6, "chiseled_quartz_block" if (x, y) == (20, 9) else "smooth_quartz")
    t.set(20, 10, 5, "end_rod[facing=north]")      # aguja del reloj, sujeta a la esfera
    # camino de acceso y farolas
    t.fill(17, 0, 0, 23, 0, 5, TRIM)
    t.fill(19, 0, 0, 21, 0, 5, "polished_andesite")
    for x in (17, 23):
        t.fill(x, 1, 2, x, 2, 2, "stone_brick_wall")
        t.set(x, 3, 2, "lantern[hanging=false]")

    # ---- puertas
    for (x, y, z, f) in ((11, 1, 9, "west"), (29, 1, 9, "east"), (20, 1, 11, "south"), (6, 1, 20, "south"),
                         (34, 1, 20, "south"), (11, 1, 32, "east"), (29, 1, 32, "east"), (20, 1, 30, "south"),
                         (11, 7, 9, "west"), (29, 7, 9, "east"), (20, 7, 11, "south"), (6, 7, 20, "south"),
                         (34, 7, 20, "south"), (11, 7, 32, "east"), (29, 7, 32, "east"), (20, 7, 30, "south")):
        door(t.set, x, y, z, f)
    t.air(20, 1, 29, 20, 2, 29)
    t.air(20, 7, 29, 20, 8, 29)

    # ---- escalera este: planta baja -> alta (x 36-37) y alta -> azotea (x 31-32)
    for i in range(1, 7):
        z = 23 + i
        for x in (36, 37):
            t.fill(x, 1, z, x, i - 1, z, WALL) if i > 1 else None
            t.set(x, i, z, stair("stone_brick_stairs", "south"))
            t.air(x, i + 1, z, x, min(i + 3, 7), z)
            FLIGHTS.append((x, i, z))
    for j in range(1, 7):
        z = 31 - j
        for x in (31, 32):
            if j > 1:
                t.fill(x, 7, z, x, 6 + j - 1, z, WALL)
            t.set(x, 6 + j, z, stair("stone_brick_stairs", "north"))
            t.air(x, 7 + j, z, x, min(9 + j, 13), z)
            FLIGHTS.append((x, 6 + j, z))
    for z in range(25, 30):
        t.set(35, 7, z, "spruce_fence")
        t.set(38, 7, z, "spruce_fence")
    for x in (36, 37):
        t.set(x, 7, 25, "spruce_fence")
    for z in range(25, 30):
        t.set(30, 13, z, "spruce_fence")
        t.set(33, 13, z, "spruce_fence")
    for x in (31, 32):
        t.set(x, 13, 29, "spruce_fence")
    # ---- escalera al archivo (antesala, x 5-7), peldaños bajo la losa: ver subsuelo()
    for z in range(23, 26):
        t.set(4, 1, z, "spruce_fence")
        t.set(8, 1, z, "spruce_fence")
    for x in range(4, 9):
        t.set(x, 1, 26, "spruce_fence")

    furnish_ground(t)
    furnish_upper(t)
    roof(t)


def furnish_ground(t):
    # vestíbulo
    for x in list(range(13, 16)) + list(range(25, 28)):
        t.set(x, 1, 7, stair("spruce_stairs", "north"))
    for x in (16, 24):
        hang(t, x, 5, 9)
    for x in (12, 28):
        t.set(x, 1, 10, "potted_fern")
    # planetario: sistema solar colgado del techo
    t.set(CX, 5, CZ, "iron_chain[axis=y]")
    t.set(CX, 4, CZ, "shroomlight")
    for (x, z, n, st) in ((22, 20, 1, "polished_granite"), (18, 22, 1, "light_blue_glazed_terracotta"),
                          (20, 16, 2, "orange_terracotta"), (25, 21, 2, CU2), (15, 18, 2, "smooth_sandstone"),
                          (23, 15, 3, "cyan_terracotta")):
        for k in range(n):
            t.set(x, 5 - k, z, "iron_chain[axis=y]")
        t.set(x, 5 - n, z, st)
    # pista del puzle en el anillo del suelo: luna nueva y llena con luz al lado
    t.set(20, 0, 14, "black_concrete")
    t.set(20, 0, 26, "white_concrete")
    t.set(26, 0, 20, "light_gray_concrete")
    t.set(14, 0, 20, "gray_concrete")
    t.set(20, 0, 15, "sea_lantern")
    t.set(20, 0, 25, "sea_lantern")
    for z in (19, 21):
        t.set(28, 1, z, "cartography_table")
        t.set(12, 1, z, "lectern[facing=east,has_book=false,powered=false]")
    # biblioteca
    for z in (7, 8, 11, 12, 14, 15, 18, 19):
        t.fill(2, 1, z, 2, 3, z, "bookshelf")
    for z in (10, 13, 16):
        t.set(2, 1, z, "lectern[facing=east,has_book=false,powered=false]")
    t.fill(10, 1, 12, 10, 3, 18, "bookshelf")
    t.fill(5, 1, 7, 7, 3, 7, "bookshelf")
    for x in (3, 4, 8, 9):
        t.fill(x, 1, 19, x, 3, 19, "bookshelf")
    for x in range(5, 8):
        t.set(x, 1, 12, "spruce_slab[type=top]")
        t.set(x, 1, 11, stair("spruce_stairs", "north"))
        t.set(x, 1, 13, stair("spruce_stairs", "south"))
    t.set(6, 2, 12, "lantern[hanging=false]")
    for x in range(4, 9):
        for z in range(15, 19):
            t.set(x, 1, z, "red_carpet" if (x in (4, 8) or z in (15, 18)) else "brown_carpet")
    t.set(6, 0, 17, "spruce_trapdoor[facing=north,half=top,open=false,powered=false]")   # trampilla oculta
    chest(t, 10, 1, 11, "west", "menor")
    for x, z in ((4, 10), (8, 10), (4, 16), (8, 16)):
        hang(t, x, 5, z)
    # taller de óptica
    t.set(38, 1, 8, "furnace[facing=west,lit=false]")
    t.set(38, 1, 9, "blast_furnace[facing=west,lit=false]")
    t.set(38, 1, 11, "crafting_table")
    t.set(38, 1, 12, "grindstone[face=floor,facing=west]")
    t.set(38, 1, 14, "cauldron")
    t.set(38, 1, 15, "stonecutter[facing=west]")
    for z in range(13, 16):
        t.set(30, 1, z, "spruce_slab[type=top]")
    t.set(30, 2, 13, "cyan_stained_glass")
    t.set(30, 2, 15, "purple_stained_glass")
    t.set(30, 2, 14, "flower_pot")
    t.barrel(30, 1, 17)
    t.barrel(30, 1, 18)
    chest(t, 30, 1, 12, "east", "menor")
    for x in range(33, 36):
        t.set(x, 1, 13, "spruce_slab[type=top]")
    t.set(34, 2, 13, "lantern[hanging=false]")
    for x, z in ((33, 10), (35, 16)):
        hang(t, x, 5, z)
    # antesala del archivo
    for z in range(28, 33):
        t.barrel(2, 1, z)
    t.barrel(2, 2, 29)
    t.barrel(2, 2, 31)
    chest(t, 10, 1, 24, "west", "menor")
    t.set(10, 1, 23, "crafting_table")
    for x, z in ((6, 22), (6, 30)):
        hang(t, x, 5, z)
    # escalera este y galería sur
    t.barrel(30, 1, 33)
    for x, z in ((34, 22), (33, 31)):
        hang(t, x, 5, z)
    for x in (14, 20, 26):
        hang(t, x, 5, 32)


def furnish_upper(t):
    # galería norte: catalejos sobre trípode mirando por las ventanas
    for x in (14, 26):
        t.set(x, 7, 7, "spruce_fence")
        t.set(x, 8, 7, "lightning_rod[facing=north,powered=false]")
    for x in (16, 24):
        hang(t, x, 11, 9)
    # sala del telescopio
    t.set(20, 7, 20, "polished_deepslate")
    t.set(20, 8, 20, CU3)
    for k in range(6):
        t.set(20, 9 + k, 20 - k, "tinted_glass" if k == 5 else CU)
        if k < 5:
            t.set(20, 9 + k, 19 - k, stair(f"{CU}_stairs", "south", "top"))
    t.set(20, 9, 21, "lightning_rod[facing=south,powered=false]")
    for z in (19, 20, 21):
        t.set(28, 7, z, stair("spruce_stairs", "east"))
    chest(t, 12, 7, 20, "east", "menor")
    for x, z in ((15, 25), (25, 15), (15, 15)):
        hang(t, x, 15, z)
    # dormitorio
    for z in (8, 11, 14, 17):
        t.set(2, 7, z, "white_bed[facing=west,occupied=false,part=head]")
        t.set(3, 7, z, "white_bed[facing=west,occupied=false,part=foot]")
    for z in (9, 15):
        t.barrel(2, 7, z)
        t.set(2, 8, z, "lantern[hanging=false]")
    chest(t, 2, 7, 19, "east", "menor")
    t.fill(10, 7, 13, 10, 8, 15, "bookshelf")
    for x in range(5, 8):
        for z in range(10, 17):
            t.set(x, 7, z, "light_blue_carpet")
    for z in (10, 16):
        hang(t, 6, 11, z)
    # comedor
    for z in range(25, 30):
        t.set(6, 7, z, "spruce_slab[type=top]")
        t.set(5, 7, z, stair("spruce_stairs", "west"))
        t.set(7, 7, z, stair("spruce_stairs", "east"))
    t.set(6, 8, 27, "lantern[hanging=false]")
    t.set(2, 7, 22, "smoker[facing=east,lit=false]")
    t.barrel(2, 7, 23)
    t.barrel(2, 7, 32)
    chest(t, 10, 7, 22, "west", "menor")
    for z in (23, 31):
        hang(t, 6, 11, z)
    # gabinete del astrónomo jefe
    t.set(38, 7, 8, "cartography_table")
    t.set(38, 7, 11, "lectern[facing=west,has_book=false,powered=false]")
    for z in range(13, 19):
        t.set(38, 7, z, "bookshelf")
    for x in range(33, 36):
        t.set(x, 7, 15, "spruce_slab[type=top]")
    t.set(34, 7, 16, stair("spruce_stairs", "south"))
    t.set(34, 8, 15, "lantern[hanging=false]")
    chest(t, 30, 7, 12, "east", "menor")
    hang(t, 34, 11, 11)
    # rellano de la escalera y galería sur alta
    for x, z in ((34, 31), (34, 22)):
        hang(t, x, 11, z)
    for x in (14, 26):
        hang(t, x, 11, 32)


def roof(t):
    # reloj de sol sobre el ala oeste; sensores de luz junto a las marcas de luna nueva (N) y llena (S)
    cx, cz = 6, 20
    for x in range(2, 11):
        for z in range(16, 25):
            if (x - cx) ** 2 + (z - cz) ** 2 <= 11:
                t.set(x, 13, z, "smooth_stone_slab[type=bottom]")
    for x, z in ((4, 18), (8, 18), (4, 22), (8, 22)):
        t.set(x, 13, z, "polished_andesite_slab[type=bottom]")
    t.set(6, 13, 17, "black_concrete")
    t.set(6, 13, 23, "white_concrete")
    t.set(9, 13, 20, "light_gray_concrete")
    t.set(3, 13, 20, "gray_concrete")
    t.set(6, 13, 18, "daylight_detector[inverted=false,power=0]")
    t.set(6, 13, 22, "daylight_detector[inverted=false,power=0]")
    t.fill(6, 13, 20, 6, 14, 20, "stone_brick_wall")
    t.set(6, 15, 20, "lightning_rod[facing=up,powered=false]")
    # catalejos sobre trípode en el ala este
    for x, z in ((33, 9), (36, 13)):
        t.set(x, 13, z, "spruce_fence")
        t.set(x, 14, z, "lightning_rod[facing=north,powered=false]")


# ------------------------------------------------------------------ subsuelo
ROOMS_B = {   # nombre: (x1, z1, x2, z2, y1, y2) interiores
    "escalera": (5, 23, 7, 28, -6, -1),
    "rellano": (4, 29, 8, 33, -6, -3),
    "pasillo": (9, 31, 13, 32, -6, -4),
    "archivo": (14, 20, 26, 33, -6, -2),
    "gabinete1": (3, 12, 9, 17, -6, -3),
    "gabinete2": (17, 13, 23, 16, -6, -3),
    "escalera2": (28, 15, 28, 21, -13, -5),
    "horas": (25, 7, 31, 14, -13, -9),
    "losas": (17, 10, 24, 10, -13, -12),
    "guardian": (8, 5, 16, 15, -13, -9),
    "tesoro": (2, 8, 6, 12, -13, -10),
}
LEVERS = {25: True, 27: False, 29: True, 31: False}     # z de cada palanca de fase: debe estar levantada
SOLVE = {}          # cambios del estado «resuelto» para la auditoría a pie


def subsuelo(t):
    t.fill(1, -3, 6, 39, -1, 34, SHELL)        # losa de roca bajo toda la planta: sella el subsuelo por arriba
    for k in (2, 1):
        for (x1, z1, x2, z2, y1, y2) in ROOMS_B.values():
            t.fill(x1 - k, y1 - k, z1 - k, x2 + k, min(y2 + k, -1), z2 + k, SHELL if k == 2 else WALLB,
                   keep=(k == 2))
    for (x1, z1, x2, z2, y1, y2) in ROOMS_B.values():
        t.air(x1, y1, z1, x2, y2, z2)
        t.fill(x1, y1 - 1, z1, x2, y1 - 1, z2, FLOORB)
        if y2 < -1:
            t.fill(x1, y2 + 1, z1, x2, y2 + 1, z2, CEILB)
    # escalera desde la antesala
    t.fill(5, -6, 23, 7, -1, 28, WALLB)
    for i in range(1, 7):
        z = 22 + i
        for x in (5, 6, 7):
            t.set(x, -i, z, stair("deepslate_brick_stairs", "north"))
            for y in range(-i + 1, -i + 4):
                t.set(x, y, z, "air")
            FLIGHTS.append((x, -i, z))
    # pasillo con cable trampa (trampa 1)
    piezas.tripwire_trap(t.set, (11, 30), (11, 33), -6, "z", [((11, -5, 30), "south"), ((11, -5, 33), "north")])
    # archivo
    for z in (23, 26, 29):
        for x in list(range(15, 19)) + list(range(22, 26)):
            t.fill(x, -6, z, x, -4, z, "bookshelf")
    for x in range(14, 27):
        for z in (20, 33):
            if x not in (17, 20) and (x + z) % 3:
                t.fill(x, -6, z, x, -5, z, "bookshelf")
    piezas.spawner(t.set, 20, -6, 31, "zombie")
    piezas.spawner(t.set, 20, -6, 25, "spider")
    chest(t, 14, -6, 21, "east", "archivo")
    chest(t, 26, -6, 33, "west", "archivo")
    t.set(14, -6, 27, "lectern[facing=east,has_book=false,powered=false]")
    for (x, y, z) in ((14, -2, 33), (26, -2, 20), (15, -2, 20), (25, -2, 27), (14, -2, 24), (21, -2, 30)):
        t.set(x, y, z, "cobweb")
    # gabinete del bibliotecario (sala oculta 1): escalera de mano bajo la trampilla
    for y in range(-6, 0):
        t.set(6, y, 17, "ladder[facing=north]")
    SOLVE[(6, 1, 17)] = "air"
    SOLVE[(6, 0, 17)] = "spruce_trapdoor[facing=north,half=top,open=true,powered=false]"
    chest(t, 3, -6, 12, "south", "oculto")
    t.fill(3, -6, 15, 3, -4, 16, "bookshelf")
    t.fill(9, -6, 12, 9, -4, 14, "bookshelf")
    t.set(5, -6, 12, "spruce_slab[type=top]")
    t.set(6, -6, 12, "spruce_slab[type=top]")
    t.set(5, -6, 13, stair("spruce_stairs", "south"))
    t.set(6, -5, 12, "candle[candles=3,lit=true]")
    t.set(8, -6, 12, "lectern[facing=south,has_book=false,powered=false]")
    # gabinete de instrumentos (sala oculta 2) tras la puerta de pistones del nicho norte
    piston_door(t)
    chest(t, 23, -6, 13, "west", "oculto")
    t.set(17, -6, 13, "cartography_table")
    t.set(17, -6, 16, "lightning_rod[facing=up,powered=false]")
    t.set(17, -6, 14, CU3)
    t.set(17, -5, 14, "lightning_rod[facing=east,powered=false]")
    t.set(20, -6, 13, "smithing_table")
    t.set(22, -6, 13, "candle[candles=2,lit=true]")
    # puzle de las fases y puerta de hierro
    phase_puzzle(t)
    # escalera a la cámara de las horas (x 28, baja hacia el norte)
    for z in range(15, 21):
        y = -8 - (20 - z)
        t.set(28, y, z, stair("deepslate_brick_stairs", "south"))
        t.fill(28, -14, z, 28, y - 1, z, WALLB)
        for yy in range(y + 1, y + 4):
            t.set(28, yy, z, "air")
        FLIGHTS.append((28, y, z))
    # cámara de las horas
    for x in (26, 30):
        t.set(x, -13, 8, "polished_andesite")
        t.set(x, -12, 8, "daylight_detector[inverted=true,power=0]")
        t.set(x, -13, 13, "polished_andesite")
        t.set(x, -12, 13, "daylight_detector[inverted=false,power=0]")
    for x in range(26, 31):
        for z in range(9, 13):
            if (x - 28) ** 2 + (z - 10.5) ** 2 <= 4.5:
                t.set(x, -14, z, "chiseled_deepslate" if (x + z) % 2 else "polished_deepslate")
    t.barrel(31, -13, 11, "west", f"{NSP}/archivo")
    for x in (26, 30):
        hang(t, x, -9, 11, "soul_lantern")
    # pasillo de las losas (trampa 2)
    piezas.plate_trap(t.set, [(20, -13, 10), (22, -13, 10)],
                      [((x, -13, z), f) for x in (20, 22) for z, f in ((9, "south"), (11, "north"))])
    # sala del guardián
    for x in (10, 14):
        for z in (7, 13):
            t.fill(x, -13, z, x, -9, z, "polished_deepslate")
    piezas.spawner(t.set, 12, -13, 6, "skeleton")
    door(t.set, 7, -13, 10, "west", "iron_door")
    t.set(8, -12, 11, "stone_button[face=wall,facing=east,powered=false]")
    t.set(6, -12, 11, "stone_button[face=wall,facing=west,powered=false]")
    t.set(16, -13, 5, "skeleton_skull[rotation=6]")
    t.entity(12, -13, 10, guardian())
    # cámara del tesoro
    chest(t, 2, -13, 10, "east", "premium")
    for z in (8, 12):
        t.set(2, -13, z, "amethyst_cluster[facing=up,waterlogged=false]")
        t.set(4, -13, z, "candle[candles=2,lit=true]")


def guardian():
    k = text("guardian")
    return piezas.guardian("skeleton", k["translate"], k["fallback"], 40.0, drop_chances={
        "mainhand": 0.15, "head": 0.15, "chest": 0.15}, equipment={
        "mainhand": {"id": "minecraft:bow", "count": 1, "components": {"minecraft:enchantments": {"minecraft:power": 2}}},
        "head": {"id": "minecraft:golden_helmet", "count": 1},
        "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}})


def piston_door(t):
    """Dos estanterías sujetas por pistones pegajosos extendidos; la antorcha (NO) los alimenta: arriba de forma
    directa y abajo por casi-conectividad. La palanca apaga la antorcha y los pistones tiran del sello."""
    t.fill(16, -7, 18, 24, -3, 18, SHELL)
    t.air(20, -6, 19, 20, -5, 19)              # nicho visible desde el archivo
    t.air(20, -6, 17, 20, -5, 17)              # paso al gabinete
    for y in (-6, -5):
        t.set(18, y, 18, "sticky_piston[extended=true,facing=east]")
        t.set(19, y, 18, "piston_head[facing=east,short=false,type=sticky]")
        t.set(20, y, 18, "bookshelf")
        SOLVE[(20, y, 18)] = "air"
    t.set(17, -5, 18, "redstone_wall_torch[facing=north,lit=true]")
    t.set(17, -5, 20, "lever[face=wall,facing=south,powered=false]")
    t.set(20, -4, 19, "chiseled_deepslate")


def phase_puzzle(t):
    """Palancas buenas -> antorcha (NO) -> línea O; malas -> polvo -> línea O; línea O -> soporte de la antorcha de
    salida (NO), que abre la puerta. Todo a y = -5 y el último polvo entra por el lado del soporte: encima de él, la
    antorcha de salida encendida le daría potencia a través del bloque de arriba y el circuito oscilaría."""
    t.fill(28, -7, 22, 31, -2, 33, SHELL)       # macizo que envuelve el circuito
    for z, good in LEVERS.items():
        t.set(26, -5, z, "lever[face=wall,facing=west,powered=false]")
        t.set(27, -4, z, {25: "black_concrete", 27: "light_gray_concrete", 29: "white_concrete",
                          31: "gray_concrete"}[z])
        if good:
            t.set(28, -5, z, "redstone_wall_torch[facing=east,lit=true]")
        else:
            t.set(28, -5, z, "redstone_wire")
        t.set(29, -5, z, "redstone_wire")
    for z in range(22, 32):
        t.set(30, -5, z, "redstone_wire")
    t.set(29, -5, 22, "redstone_wire")
    t.set(27, -5, 22, "redstone_wall_torch[facing=west,lit=false]")
    door(t.set, 27, -6, 21, "east", "iron_door")
    t.air(28, -6, 21, 28, -5, 21)
    t.fill(28, -13, 21, 28, -7, 21, WALLB)
    t.set(28, -7, 21, FLOORB)


def build_full():
    FLIGHTS.clear(); DAMAGE.clear(); SOLVE.clear()
    t = Template(P + "/_completa")
    surface(t)
    subsuelo(t)
    piezas.connect(t)
    redstone.wire_shapes(t)
    redstone.set_wire_power(t)
    redstone.set_torches(t)
    # jigsaws al final: entrada (para la auditoría a pie) y unión vertical superficie-subsuelo
    t.jigsaw(20, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
             final_state="minecraft:polished_andesite")
    t.jigsaw(17, 0, 23, "down_north", f"{NSP}/a_subsuelo", f"{NSP}/a_superficie", f"{P}/subsuelo",
             final_state="minecraft:polished_deepslate")
    t.jigsaw(17, -1, 23, "up_north", f"{NSP}/a_superficie", f"{NSP}/a_subsuelo", "minecraft:empty",
             final_state="minecraft:" + CEILB)
    from pack import fix_supports
    fix_supports(t)
    return t


def split(t):
    a, b = Template(P + "/superficie"), Template(P + "/subsuelo")
    for (x, y, z), v in t.blocks.items():
        (a if y >= 0 else b).blocks[(x, y, z)] = v
    for e in t.entities:
        (a if e[1] >= 0 else b).entities.append(e)
    for j in t.jigsaws:
        (a if j["pos"][1] >= 0 else b).jigsaws.append(dict(j))
    return a, b


def solved(t):
    s = Template(t.name + "_resuelta")
    s.blocks = dict(t.blocks)
    s.jigsaws = t.jigsaws
    for p, st in SOLVE.items():
        s.set(*p, st)
    for y in (-6, -5):                      # pistones retraídos, cabezas fuera
        s.set(18, y, 18, "sticky_piston[extended=false,facing=east]")
        s.set(19, y, 18, "bookshelf")
    return s


def exterior_damage(t):
    """Fracción de la envolvente exterior de la superficie en mal estado (diseño + procesador). La envolvente son los
    bloques que se ven desde fuera: el primero que encuentra cada rayo desde arriba y desde los cuatro lados."""
    blk = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0 and _b(st) not in ("air", "structure_void")}
    x0, _, z0, x1, y1, z1 = t.bounds()
    shell, holes = set(), set()

    def ray(cells):
        for c in cells:
            if c in DAMAGE:
                holes.add(c)
            if c in blk:
                shell.add(c)
                return
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            ray((x, y, z) for y in range(y1, -1, -1))
    for y in range(0, y1 + 1):
        for z in range(z0, z1 + 1):
            ray((x, y, z) for x in range(x0, x1 + 1))
            ray((x, y, z) for x in range(x1, x0 - 1, -1))
        for x in range(x0, x1 + 1):
            ray((x, y, z) for z in range(z0, z1 + 1))
            ray((x, y, z) for z in range(z1, z0 - 1, -1))
    proc = sum(PROC_P for p in shell if _b(blk[p]) == "stone_bricks")
    designed = len(holes) + sum(1 for p in shell if _b(blk[p]) in ("cobblestone", "mossy_cobblestone_slab", "gravel"))
    return (proc + designed) / (len(shell) + len(holes)), len(shell)


CRACK, MOSS = 0.14, 0.09
PROC_P = CRACK + (1 - CRACK) * MOSS     # agrietado y, del resto, musgoso


def audit(t):
    issues = []
    issues += [("apoyo: " + m, p) for m, p in lint.support_issues(t)]
    s = solved(t)
    cells = walk(s)
    hatch_top = (6, -1, 17)
    for m, (x, y, z) in lint.access_issues(shifted(s)):
        if not (m.startswith("escalera de mano que no lleva") and (x, y - DY, z) == hatch_top):
            issues.append(("acceso: " + m, (x, y - DY, z)))
    for p in FLIGHTS:
        if (p[0], p[1] + 1, p[2]) not in cells and p not in cells:
            issues.append(("peldaño no pisado", p))
    for p, (st, nbt) in t.blocks.items():
        if _b(st) in ("chest", "barrel", "spawner", "lever", "stone_button") or "_door" in _b(st) and "lower" in st:
            if not any((p[0] + dx, p[1] + dy, p[2] + dz) in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0))
                       for dy in (-2, -1, 0, 1)):
                issues.append((_b(st) + " fuera del recorrido", p))
    # las salas ocultas no se alcanzan sin resolver nada
    pt = Template("sin_resolver")
    pt.blocks = {p: (("minecraft:stone", None) if _b(v[0]) == "iron_door" else v) for p, v in t.blocks.items()}
    pt.jigsaws = t.jigsaws
    plain = walk(pt)
    for p in ((3, -6, 13), (23, -6, 14), (2, -13, 11), (12, -13, 9)):
        if p in plain:
            issues.append(("sala oculta alcanzable sin resolver", p))
        if p not in cells:
            issues.append(("sala no alcanzable resuelta", p))
    # redstone: estado colocado estable, puzle de las fases y puerta de pistones (simulador común)
    errs, _ = redstone.check_static(t)
    levers = [(26, -5, z) for z in sorted(LEVERS)]
    errs += redstone.check_puzzle(t, "fases", levers, tuple(LEVERS[z] for z in sorted(LEVERS)), [(27, -6, 21)])
    errs += redstone.check_puzzle(t, "pistones", [(17, -5, 20)], (True,), [(18, -6, 18), (18, -5, 18)], "sin_potencia")
    issues += [("redstone: " + e, None) for e in errs]
    # nada flotando: todo bloque unido a los demás
    solid = {p for p, (st, _) in t.blocks.items() if _b(st) not in ("air", "structure_void")}
    start = next(iter(solid))
    seen = {start}
    q = deque([start])
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in SIDES:
            n = (x + dx, y + dy, z + dz)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    for p in sorted(solid - seen)[:5]:
        issues.append(("bloque flotando", p))
    frac, _ = exterior_damage(t)
    if not 0.15 <= frac <= 0.20:
        issues.append(("estado exterior fuera de 80-85 %", round(1 - frac, 3)))
    return issues


def build(reg):
    t = build_full()
    for m, p in audit(t):
        reg.warnings.append(f"{P}: {m} en {p}")
    a, b = split(t)
    na = reg.add(a, "unica")
    nb = reg.add(b, "unica")
    reg.pool(f"{P}/inicio", [(na, 1, "rigid", processors([
        ("stone_bricks", "cracked_stone_bricks", CRACK), ("stone_bricks", "mossy_stone_bricks", MOSS)]))])
    reg.pool(f"{P}/subsuelo", [(nb, 1, "rigid", processors([
        ("deepslate_bricks", "cracked_deepslate_bricks", 0.15), ("deepslate_tiles", "cracked_deepslate_tiles", 0.10),
        ("stone", "andesite", 0.12)]))])


# ------------------------------------------------------------------ planos y renders
LEVELS = (("Planta baja", 1), ("Planta alta", 7), ("Azotea", 13), ("Archivo", -6), ("Cámara del tesoro", -13))


def plans(t):
    s = solved(t)
    cells = walk(s)
    x0, _, z0, x1, _, z1 = t.bounds()
    out = ["Planos del Observatorio (norte arriba, x hacia la derecha). Leyenda: '.' celda alcanzable a pie "
           "(estado resuelto), '#' muro, 'C' cofre o barril, 'S' generador, 'D' puerta, '=' escalera, 'L' palanca, "
           "'T' trampa (gancho, placa o dispensador), 'H' escalera de mano, 'G' guardián, ' ' vacío o terreno.", ""]
    ents = {(e[0], e[1], e[2]) for e in t.entities}
    for name, y in LEVELS:
        out.append(f"== {name} (pies a y = {y}) ==")
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                st = s.get(x, y, z) or ""
                b = _b(st) if st else ""
                below = _b(s.get(x, y - 1, z) or "") if s.get(x, y - 1, z) else ""
                if (x, y, z) in ents:
                    c = "G"
                elif b in ("chest", "barrel"):
                    c = "C"
                elif b == "spawner":
                    c = "S"
                elif "_door" in b:
                    c = "D"
                elif b == "lever":
                    c = "L"
                elif b in ("tripwire_hook", "tripwire", "stone_pressure_plate", "dispenser") or below == "dispenser":
                    c = "T"
                elif b == "ladder":
                    c = "H"
                elif "stairs" in b or "stairs" in below and (x, y, z) in cells:
                    c = "="
                elif (x, y, z) in cells:
                    c = "."
                elif st and not lint.passable(st):
                    c = "#"
                else:
                    c = " "
                row += c
            out.append(row.rstrip())
        out.append("")
    return "\n".join(out)


def docs(out_dir):
    import render
    os.makedirs(out_dir, exist_ok=True)
    t = build_full()
    with open(os.path.join(out_dir, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write(plans(t) + "\n")
    a, b = split(t)
    a.normalize()
    b.normalize()
    render.render(a, os.path.join(out_dir, "superficie.png"), scale=4)
    render.render(a, os.path.join(out_dir, "superficie_planta_baja.png"), scale=4, cut_y=5)
    render.render(b, os.path.join(out_dir, "subsuelo.png"), scale=4, flip=True)
    iss = audit(t)
    frac, n = exterior_damage(t)
    print(f"auditoría: {len(iss)} avisos {iss[:10]}; envolvente {n} bloques, en buen estado {100 * (1 - frac):.1f} %")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    docs(ap.parse_args().docs)
