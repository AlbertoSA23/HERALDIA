"""Plantilla única del faro: promontorio, casa del farero, faro y cueva de contrabandistas.

Ejes de la plantilla: x hacia el este, z hacia el mar (sur), y hacia arriba. y=SEA es la fila de agua más alta
(nivel del mar - 1): los suelos de la cueva están en esa fila, así que el interior queda por encima del mar.
Coordenadas citadas en docs/unicas/faro.md.
"""
import zlib
from core import Template
from unicas._comun import piezas
from unicas._comun.piezas import spawner

NAME = "unicas/faro/faro"
LOOT = "heraldia:unicas/faro/"
X, Z = 44, 48          # huella
SEA = 8                # fila del agua (y del suelo de la cueva)
TOP = 21               # hierba de la cima
G = TOP + 1            # pies en la cima
WATER = "water[level=0]"


def h(*a):
    return zlib.crc32(repr(a).encode()) & 0xFFFF


def cliff(x):
    """Último z con roca alta (borde del acantilado)."""
    return 42 + h("c", x) % 3 if 5 <= x <= 38 else 41 + h("c", x) % 2


def rock(x, y, z):
    r = h("r", x, y, z) % 100
    return "stone" if r < 70 else "andesite" if r < 85 else "tuff" if r < 93 else "diorite"






def sign(t, x, y, z, facing, *keys):
    from unicas.faro import LANG
    piezas.sign(t.set, x, y, z, facing, [piezas.text(k, LANG["es_es"][k]) for k in keys], wood="spruce")


def door(t, x, y, z, facing, mat="spruce", hinge="left"):
    for half, dy in (("lower", 0), ("upper", 1)):
        t.set(x, y + dy, z, f"{mat}_door[facing={facing},half={half},hinge={hinge},open=false,powered=false]")


def table(t, x, y, z, chairs):
    t.set(x, y, z, "spruce_fence")
    t.set(x, y + 1, z, "spruce_pressure_plate")
    for cx, cz, f in chairs:
        t.set(cx, y, cz, f"spruce_stairs[facing={f},half=bottom,shape=straight]")


def hang(t, x, y, z):
    t.set(x, y, z, "lantern[hanging=true]")


# ------------------------------------------------------------------ terreno
def headland(t):
    for x in range(X):
        zc = cliff(x)
        for z in range(Z):
            if z <= zc:
                top = TOP - max(0, 4 - x, x - 39)
                if z == zc and h("e", x) % 2:
                    top -= 1
                for y in range(top + 1):
                    st = "grass_block" if y == top else "dirt" if y >= top - 2 else rock(x, y, z)
                    t.set(x, y, z, st)
            else:
                top = max(1, 7 - 2 * (z - zc))
                if 19 <= x <= 25:
                    top = min(top, 3)
                for y in range(top + 1):
                    t.set(x, y, z, "gravel" if y == top and top > 1 else rock(x, y, z))
                if 20 <= x <= 24:
                    for y in range(top + 1, SEA + 1):
                        t.set(x, y, z, WATER)


# ------------------------------------------------------------------ cueva
def cave(t):
    f = SEA
    # gruta del muelle y boca al mar
    t.air(13, f + 1, 25, 31, f + 5, 40)
    for x in range(15, 30):
        for z in range(27, 39):
            if h("t", x, z) % 3 == 0 and (x, z) not in ((16, 30), (28, 30), (16, 37), (28, 37)):
                t.set(x, f + 6, z, "air")
    for x in range(20, 25):
        for z in range(30, cliff(x) + 1 if x else 0):
            for y in range(4, f + 1):
                t.set(x, y, z, WATER)
        for z in range(41, cliff(x) + 1):
            t.air(x, f + 1, z, x, f + 4 if x in (20, 24) else f + 5, z)
    for z in range(30, 41):
        for x in (19, 25):
            t.set(x, f, z, "spruce_planks")
    for z in (32, 36, 40):
        t.set(19, f + 1, z, "spruce_fence")
        t.set(25, f + 1, z, "spruce_fence")
    for x, z in ((14, 26), (14, 27), (15, 26), (30, 26), (30, 27), (29, 26), (14, 38), (30, 38)):
        t.barrel(x, f + 1, z)
    t.barrel(14, f + 2, 26)
    t.barrel(30, f + 2, 26)
    for p in ((16, 30), (28, 30), (16, 37), (28, 37)):
        hang(t, p[0], f + 5, p[1])
    t.entity(22, f + 1, 35, {"id": "minecraft:spruce_chest_boat", "LootTable": LOOT + "bote"})
    # corredor este-oeste
    t.air(3, f + 1, 23, 41, f + 3, 24)
    for x in (6, 36):
        hang(t, x, f + 3, 23)
    # almacén oeste (generador de esqueletos)
    t.air(3, f + 1, 26, 11, f + 4, 38)
    t.air(12, f + 1, 30, 12, f + 2, 31)
    for z in range(27, 37, 2):
        t.barrel(3, f + 1, z)
    t.barrel(3, f + 2, 27)
    t.barrel(3, f + 1, 32, loot=LOOT + "almacen")
    t.barrel(11, f + 1, 37, loot=LOOT + "almacen")
    t.chest(3, f + 1, 30, "east", LOOT + "almacen")
    for x in range(5, 10):
        t.barrel(x, f + 1, 38)
    spawner(t.set, 7, f + 1, 35, "skeleton")
    hang(t, 7, f + 4, 29)
    # almacén este (derrumbe y cofre señuelo con TNT)
    t.air(33, f + 1, 26, 41, f + 4, 38)
    t.air(32, f + 1, 30, 32, f + 2, 31)
    t.chest(41, f + 1, 31, "west", LOOT + "almacen")
    for z in (27, 29, 33, 35):
        t.barrel(41, f + 1, z)
    t.barrel(41, f + 2, 33)
    for x, z, y in ((39, 26, 1), (40, 26, 1), (41, 26, 1), (40, 26, 2), (41, 26, 2), (41, 27, 1), (40, 27, 1), (41, 26, 3)):
        t.set(x, f + y, z, "gravel" if (x + z + y) % 2 else "cobblestone")
    t.air(37, f + 1, 39, 37, f + 2, 39)
    t.chest(37, f + 1, 40, "north", LOOT + "senuelo")
    t.set(37, f, 39, "stone")
    piezas.tnt_trap(t.set, 37, f + 1, 39)
    for x in (36, 38):
        t.set(x, f - 1, 39, "tnt[unstable=false]")
    hang(t, 37, f + 4, 30)
    # dormitorio (y rendija a la gruta del alijo)
    t.air(3, f + 1, 14, 12, f + 4, 21)
    door(t, 8, f + 1, 22, "south")
    for z in (16, 18, 20):
        t.set(3, f + 1, z, "red_bed[facing=west,part=head,occupied=false]")
        t.set(4, f + 1, z, "red_bed[facing=west,part=foot,occupied=false]")
    t.chest(12, f + 1, 16, "west", LOOT + "dormitorio")
    table(t, 8, f + 1, 18, ((7, 18, "west"), (9, 18, "east")))
    for p in ((8, 15), (8, 20)):
        hang(t, p[0], f + 4, p[1])
    t.barrel(4, f + 1, 14)
    t.barrel(6, f + 1, 14)
    t.air(5, f + 1, 11, 5, f + 2, 13)
    t.set(5, f + 2, 12, "cobweb")
    # gruta del alijo (sala oculta)
    t.air(3, f + 1, 6, 9, f + 3, 10)
    t.air(4, f + 4, 7, 8, f + 4, 9)
    t.chest(6, f + 1, 6, "south", LOOT + "oculto")
    t.set(3, f + 1, 8, "bone_block[axis=x]")
    t.set(4, f + 1, 10, "candle[candles=3,lit=true]")
    t.set(9, f + 1, 7, "candle[candles=2,lit=true]")
    # calabozo (generador de zombis)
    t.air(32, f + 1, 14, 40, f + 4, 21)
    door(t, 36, f + 1, 22, "south")
    for x in range(32, 41):
        for y in range(f + 1, f + 4):
            t.set(x, y, 17, "iron_bars")
    for x in (35, 38):
        t.fill(x, f + 1, 14, x, f + 4, 16, "stone_bricks")
        t.set(x, f + 1, 17, "stone_bricks")
    for x in (33, 36, 39):
        door(t, x, f + 1, 17, "south")
    t.set(40, f + 1, 17, "air")
    t.set(40, f + 2, 17, "air")
    t.chest(40, f + 1, 14, "south", LOOT + "calabozo")
    t.set(32, f + 1, 14, "bone_block[axis=y]")
    for p in ((32, 16), (37, 14), (34, 21), (40, 21)):
        t.set(p[0], f + 4, p[1], "cobweb")
    spawner(t.set, 36, f + 1, 19, "zombie")
    hang(t, 33, f + 4, 20)
    # despacho del capitán (puzle 2) y cámara del tesoro
    t.air(18, f + 1, 14, 26, f + 4, 21)
    door(t, 22, f + 1, 22, "south")
    for z in range(16, 21):
        t.set(18, f + 1, z, "bookshelf")
        t.set(18, f + 2, z, "bookshelf")
    t.set(19, f + 1, 14, "bookshelf")
    t.set(19, f + 2, 14, "bookshelf")
    table(t, 22, f + 1, 18, ((22, 17, "north"), (22, 19, "south")))
    t.chest(26, f + 1, 21, "west", LOOT + "despacho")
    t.set(26, f + 1, 17, "cartography_table")
    t.set(26, f + 1, 19, "lectern[facing=west,has_book=false,powered=false]")
    hang(t, 22, f + 4, 16)
    hang(t, 22, f + 4, 20)
    circuit(t)
    t.air(18, f + 1, 10, 18, f + 2, 12)
    t.air(13, f + 1, 3, 23, f + 5, 9)
    t.fill(13, f, 3, 23, f, 9, "stone_bricks")
    t.set(18, f + 1, 4, "chiseled_stone_bricks")
    t.chest(18, f + 2, 4, "south", LOOT + "premium")
    t.set(18, f + 1, 5, "stone_brick_stairs[facing=north,half=bottom,shape=straight]")
    for x in (17, 19):
        t.set(x, f + 1, 4, f"stone_brick_stairs[facing={'east' if x == 17 else 'west'},half=bottom,shape=straight]")
    for x in (14, 22):
        t.barrel(x, f + 1, 4, loot=LOOT + "tesoro")
    for x in (16, 20):
        t.set(x, f + 1, 3, "decorated_pot[cracked=false,facing=south,waterlogged=false]", {"id": "minecraft:decorated_pot"})
    for x in (15, 21):
        t.set(x, f + 1, 3, "candle[candles=4,lit=true]")
        hang(t, x, f + 5, 6)
    t.entity(18, f + 1, 7, piezas.guardian(
        "drowned", "heraldia.unicas.faro.guardian", "Capitán Bruma", 40,
        equipment={"mainhand": {"id": "minecraft:iron_sword", "count": 1},
                   "head": {"id": "minecraft:chainmail_helmet", "count": 1},
                   "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}},
        drop_chances={"mainhand": 0.0, "head": 0.0, "chest": 0.0}))






# Puzle 2: tres palancas (A, B, C) en el muro norte del despacho (z=13). La puerta abre con A y C bajadas y B subida.
LEVERS = {"A": (22, SEA + 2, 14), "B": (24, SEA + 2, 14), "C": (26, SEA + 2, 14)}
REST = {"A": True, "B": False, "C": False}
VAULT_DOOR = (18, SEA + 1, 13)


def circuit(t):
    y, W = SEA + 2, 13
    for k, (x, _, z) in LEVERS.items():
        t.set(x, y, z, f"lever[face=wall,facing=south,powered={str(REST[k]).lower()}]")
    door(t, 18, SEA + 1, W, "south", mat="iron")
    t.set(19, y, W, "redstone_wall_torch[facing=west,lit=false]")      # tG, junto a la mitad alta de la puerta
    t.set(24, y, W - 1, "redstone_wall_torch[facing=north,lit=true]")  # tB, inversor de la palanca B
    dust = {(20, W - 1): "ns", (22, W - 1): "ns", (26, W - 1): "ns",
            (20, W - 2): "es", (21, W - 2): "ew", (22, W - 2): "ews", (23, W - 2): "ew",
            (24, W - 2): "ews", (25, W - 2): "ew", (26, W - 2): "ws"}
    names = {"n": "north", "s": "south", "e": "east", "w": "west"}
    for (x, z), c in dust.items():
        props = {d: ("side" if k in c else "none") for k, d in names.items()}
        t.set(x, y, z, "redstone_wire[" + ",".join(f"{d}={v}" for d, v in props.items()) + ",power=0]")
    sign(t, 24, y + 1, 14, "south", "heraldia.unicas.faro.cartel.despacho1", "heraldia.unicas.faro.cartel.despacho2")


# ------------------------------------------------------------------ pasadizo secreto y sótano
def passage(t):
    f = SEA
    t.air(15, f + 1, 16, 15, 15, 16)
    for y in range(f + 1, 16):
        t.set(15, y, 16, "ladder[facing=east,waterlogged=false]")
    t.air(15, f + 1, 17, 15, f + 2, 22)
    # trampa 1: cable trampa con un dispensador encima de cada gancho
    piezas.tripwire_trap(t.set, (14, 19), (16, 19), f + 1, "x",
                         [((14, f + 2, 19), "east"), ((16, f + 2, 19), "west")], arrows=9)


def cellar(t):
    t.air(15, 17, 15, 28, 20, 23)
    t.fill(15, 16, 15, 28, 16, 23, "cobblestone")
    # puzle 1: trampilla de hierro; la palanca entre los barriles alimenta el suelo pegado a ella
    t.set(15, 16, 16, "iron_trapdoor[facing=east,half=top,open=false,powered=false,waterlogged=false]")
    t.set(16, 17, 16, "lever[face=floor,facing=north,powered=false]")
    for x in (15, 16, 17):
        t.barrel(x, 17, 15)
    t.barrel(17, 17, 16, loot=LOOT + "bodega")
    t.barrel(16, 18, 15)
    for z in range(17, 23, 2):
        t.barrel(28, 17, z)
        t.barrel(28, 18, z)
    t.barrel(20, 17, 23)
    t.barrel(21, 17, 23)
    sign(t, 19, 18, 15, "south", "heraldia.unicas.faro.cartel.bodega1", "heraldia.unicas.faro.cartel.bodega2")
    hang(t, 20, 20, 19)
    hang(t, 25, 20, 19)


# ------------------------------------------------------------------ casa del farero
def house(t):
    x0, x1, z0, z1 = 15, 29, 14, 24
    t.fill(x0, TOP, z0, x1, TOP, z1, "cobblestone")
    t.fill(x0 + 1, TOP, z0 + 1, x1 - 1, TOP, z1 - 1, "spruce_planks")
    for y in range(G, G + 4):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                if not edge:
                    t.set(x, y, z, "air")
                elif x in (x0, x1) and z in (z0, z1):
                    t.set(x, y, z, "spruce_log[axis=y]")
                else:
                    t.set(x, y, z, "stone_bricks" if y == G else "spruce_planks")
    # tejado a dos aguas (cumbrera este-oeste en z=19)
    for k in range(6):
        y = G + 4 + k
        for x in range(x0 - 1, x1 + 2):
            t.set(x, y, z0 - 1 + k, "spruce_stairs[facing=south,half=bottom,shape=straight]")
            t.set(x, y, z1 + 1 - k, "spruce_stairs[facing=north,half=bottom,shape=straight]")
        for x in range(x0 + 1, x1):
            for z in range(z0 + k, z1 + 1 - k):
                if z0 - 1 + k < z < z1 + 1 - k:
                    t.set(x, y, z, "air")
        for x in (x0, x1):
            for z in range(z0 + k, z1 - k + 1):
                if z0 - 1 + k < z < z1 + 1 - k:
                    t.set(x, y, z, "spruce_planks")
    for x in range(x0 - 1, x1 + 2):
        t.set(x, G + 9, 19, "spruce_planks")
        t.set(x, G + 10, 19, "spruce_slab[type=bottom]")
    # ruina: hueco en el faldón norte sobre la cocina
    t.set(20, G + 6, 16, "air")
    t.set(21, G + 6, 16, "air")
    t.set(26, G + 7, 23, "air")
    t.set(27, G + 7, 23, "air")
    # ventanas
    for x in (18, 19, 25, 26):
        for y in (G + 1, G + 2):
            t.set(x, y, z0, "glass_pane[east=true,west=true]")
            t.set(x, y, z1, "glass_pane[east=true,west=true]")
    for z in (17, 18, 20, 21):
        for y in (G + 1, G + 2):
            t.set(x0, y, z, "glass_pane[north=true,south=true]")
    for z in (17, 18):
        for y in (G + 1, G + 2):
            t.set(x1, y, z, "glass_pane[north=true,south=true]")
    t.set(26, G + 2, z0, "air")       # cristales rotos
    t.set(x0, G + 1, 21, "air")
    door(t, 22, G, z0, "south")
    door(t, 22, G, z1, "south")
    # muebles
    t.set(16, G, 16, "white_bed[facing=north,part=head,occupied=false]")
    t.set(16, G, 17, "white_bed[facing=north,part=foot,occupied=false]")
    t.chest(16, G, 19, "east", LOOT + "casa")
    t.set(20, G, 15, "smoker[facing=south,lit=false]")
    t.barrel(21, G, 15)
    t.set(23, G, 15, "crafting_table")
    t.set(24, G, 15, "furnace[facing=south,lit=false]")
    table(t, 22, G, 19, ((21, 19, "west"), (23, 19, "east")))
    for z in (19, 20, 21):
        t.set(28, G, z, "bookshelf")
        t.set(28, G + 1, z, "bookshelf")
    t.set(25, G, 23, "lectern[facing=north,has_book=false,powered=false]")
    t.set(26, G, 23, "cartography_table")
    hang(t, 19, G + 3, 19)
    hang(t, 25, G + 3, 19)
    # pasillo cubierto hasta el faro
    t.fill(21, TOP, 25, 23, TOP, 27, "stone_bricks")
    t.fill(21, G, 25, 21, G + 2, 27, "spruce_planks")
    t.fill(23, G, 25, 23, G + 2, 27, "spruce_planks")
    t.air(22, G, 25, 22, G + 2, 27)
    t.fill(21, G + 3, 25, 23, G + 3, 27, "spruce_slab[type=bottom]")
    t.set(21, G + 3, 26, "air")                   # ruina: tablas caídas del pasillo
    t.set(22, G + 3, 26, "air")
    # camino y jardín
    for z in range(0, z0):
        t.set(22, TOP, z, "dirt_path")
    for x, z in ((20, 4), (24, 4), (20, 10), (24, 10)):
        t.set(x, G, z, "spruce_fence")
        t.set(x, G + 1, z, "lantern[hanging=false]")
    for i, (x, z) in enumerate(((18, 6), (19, 8), (26, 7), (25, 9), (17, 11), (27, 11), (10, 20), (34, 18))):
        t.set(x, G, z, ("poppy", "dandelion", "cornflower", "oxeye_daisy")[i % 4])


# ------------------------------------------------------------------ faro
RING = [(23, 29), (24, 29), (25, 29)] + [(25, z) for z in range(30, 36)] + [(x, 35) for x in range(24, 18, -1)] \
    + [(19, 34), (19, 33)]
FLOOR = G + 16          # suelo de la sala de guardia (y=38)


def tower(t):
    x0, x1, z0, z1 = 18, 26, 28, 36
    t.fill(x0, TOP, z0, x1, TOP, z1, "stone_bricks")
    for y in range(G, FLOOR + 5):
        band = "red_terracotta" if (y - G) // 4 % 2 else "white_terracotta"
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    t.set(x, y, z, band)
                elif 20 <= x <= 24 and 30 <= z <= 34 and y < FLOOR:
                    t.set(x, y, z, "stone_bricks")
                else:
                    t.set(x, y, z, "air")
    door(t, 22, G, z0, "south")
    # escalera de caracol
    for k, (x, z) in enumerate(RING):
        px, pz = RING[k - 1] if k else (22, 29)
        dx, dz = (x - px, z - pz)
        facing = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]
        t.set(x, G + k, z, f"stone_brick_stairs[facing={facing},half=bottom,shape=straight]")
    t.fill(19, FLOOR, 29, 25, FLOOR, 35, "spruce_planks")
    t.set(19, FLOOR, 35, "air")
    t.set(19, FLOOR, 34, "air")
    t.set(19, FLOOR, 33, "stone_brick_stairs[facing=north,half=bottom,shape=straight]")   # último peldaño
    for x, y, z, fc in ((20, G + 2, 29, "north"), (24, G + 4, 29, "north"), (25, G + 8, 32, "east"),
                        (22, G + 13, 35, "south"), (19, G + 2, 31, "west")):
        t.set(x, y, z, f"wall_torch[facing={fc}]")
    for x, y, z, axis in ((26, G + 7, 32, "ns"), (22, G + 12, 36, "ew"), (18, G + 13, 33, "ns")):
        for dy in (0, 1):
            t.set(x, y + dy, z, "glass_pane[north=true,south=true]" if axis == "ns" else "glass_pane[east=true,west=true]")
    # sala de guardia
    w = FLOOR + 1
    for x in (21, 22, 23):
        for y in (w + 1, w + 2):
            t.set(x, y, z0, "glass_pane[east=true,west=true]")
    for z in (31, 32, 33):
        for y in (w + 1, w + 2):
            t.set(x1, y, z, "glass_pane[north=true,south=true]")
            t.set(x0, y, z, "glass_pane[north=true,south=true]")
    t.set(25, w, 29, "lectern[facing=west,has_book=false,powered=false]")
    t.chest(25, w, 32, "west", LOOT + "faro")
    t.barrel(25, w, 33)
    t.fill(22, w, 35, 22, w + 3, 35, "stone_bricks")
    for y in range(w, w + 5):
        t.set(22, y, 34, "ladder[facing=north,waterlogged=false]")
    hang(t, 22, w + 3, 31)
    # galería, linterna y cubierta
    g = FLOOR + 5                                   # y=43
    t.fill(16, g, 26, 28, g, 38, "stone_bricks")
    t.set(22, g, 34, "ladder[facing=north,waterlogged=false]")
    t.set(21, g, 38, "air")                       # ruina: losas desprendidas junto a la barandilla caída
    t.set(22, g, 38, "air")
    for x in range(16, 29):
        for z in range(26, 39):
            if x in (16, 28) or z in (26, 38):
                if not (z == 38 and 21 <= x <= 23):     # ruina: barandilla caída del lado del mar
                    t.set(x, g + 1, z, "spruce_fence")
    for x in range(17, 28):
        for z in range(27, 38):
            if (x in (17, 27) or z in (27, 37)):
                fc = "east" if x == 17 else "west" if x == 27 else "south" if z == 27 else "north"
                if not (x in (17, 27) and z in (27, 37)):
                    t.set(x, g - 1, z, f"stone_brick_stairs[facing={fc},half=top,shape=straight]")
    for y in range(g + 1, g + 4):
        for x in range(19, 26):
            for z in range(29, 36):
                if x in (19, 25) and z in (29, 35):
                    t.set(x, y, z, "stone_bricks")
                elif x in (19, 25):
                    t.set(x, y, z, "glass_pane[north=true,south=true]")
                elif z in (29, 35):
                    t.set(x, y, z, "glass_pane[east=true,west=true]")
                else:
                    t.set(x, y, z, "air")
    t.set(22, g + 1, 29, "air")
    t.set(22, g + 2, 29, "air")
    t.set(22, g + 1, 32, "waxed_cut_copper")
    t.set(22, g + 2, 32, "waxed_copper_bulb[lit=true,powered=false]")
    t.set(22, g + 3, 32, "waxed_copper_bulb[lit=true,powered=false]")
    for i, r in enumerate((3, 2, 1)):
        t.fill(22 - r, g + 4 + i, 32 - r, 22 + r, g + 4 + i, 32 + r, "waxed_cut_copper")
    t.set(22, g + 7, 32, "waxed_copper_block")
    t.set(22, g + 8, 32, "lightning_rod[facing=up,powered=false,waterlogged=false]")


def make():
    t = Template(NAME)
    headland(t)
    cave(t)
    passage(t)
    cellar(t)
    house(t)
    tower(t)
    for y in range(17, 22):                       # escalera de mano casa -> sótano (tras el suelo de la casa)
        t.set(28, y, 15, "ladder[facing=west,waterlogged=false]")
    from unicas.faro.checks import settle
    settle(t)
    t.jigsaw(22, TOP, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="dirt_path")
    # estado con los puzles resueltos, para el recorrido a pie de lint.py
    t.lint_open = {(15, 16, 16): "iron_trapdoor[facing=east,half=top,open=true,powered=true,waterlogged=false]"}
    return t
