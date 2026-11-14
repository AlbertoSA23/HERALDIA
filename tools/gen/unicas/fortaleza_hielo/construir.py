"""Construcción a mano de la fortaleza de hielo (una sola pieza rígida). Ver docs/unicas/fortaleza_hielo.md.

Coordenadas de la plantilla: x de oeste a este (0..50), z de norte a sur (0..64), y hacia arriba (0..45).
Zócalo macizo y = 0..10; patio a pie 11; criptas a pie 6; cámara del tesoro a pie 1; adarve a pie 20.
"""
from core import Template, B, F
from unicas._comun.piezas import door, hang, chair, table, spawner, dispenser, tripwire, guardian as _guardian

SID = "fortaleza_hielo"
L = f"heraldia:unicas/{SID}/"
W, D, H = 51, 65, 46

PI, BI, SB, CSB, ST = "packed_ice", "blue_ice", "stone_bricks", "chiseled_stone_bricks", "stone"
PD, SPR = "polished_diorite", "spruce_planks"
WEATHER = 0.42        # hielo compacto a la vista con costra de nieve: deja la superficie dañada en torno al 18 %
RUIN = set()          # posiciones dañadas a mano (para la estimación de estado)


def box(t, x1, y1, z1, x2, y2, z2, st):
    t.fill(x1, y1, z1, x2, y2, z2, st)


def air(t, x1, y1, z1, x2, y2, z2):
    t.fill(x1, y1, z1, x2, y2, z2, "air")


def ruin(t, x, y, z, st="air"):
    t.set(x, y, z, st)
    RUIN.add((x, y, z))






def pane(t, x, y, z):
    t.set(x, y, z, "light_blue_stained_glass_pane")






def chest(t, x, y, z, facing, name):
    t.chest(x, y, z, facing, L + name)


# ------------------------------------------------------------------ partes
def plinth(t):
    box(t, 0, 0, 12, 50, 10, 64, ST)
    for x in range(51):
        for z in range(12, 65):
            if x in (0, 50) or z in (12, 64):
                for y in range(0, 11):
                    t.set(x, y, z, CSB if y == 5 and (x + z) % 4 == 0 else SB)
    box(t, 1, 10, 13, 49, 10, 63, PD)              # suelo del patio
    for x in range(3, 48):                         # caminos de piedra en cruz
        for z in (24, 25, 26):
            t.set(x, 10, z + 6 * 0, SB) if 13 <= x <= 37 else None
    for z in range(15, 41):
        for x in (24, 25, 26):
            t.set(x, 10, z, SB)
    # escalinata norte encajada entre pretiles
    for x in range(22, 29):
        t.set(x, 0, 0, "stone_brick_slab[type=bottom]")
    for k in range(1, 12):
        for x in range(22, 29):
            box(t, x, 0, k, x, k - 2, k, SB) if k >= 2 else None
            t.set(x, k - 1, k, "stone_brick_stairs[facing=south,half=bottom,shape=straight]")
        for x in (21, 29):
            box(t, x, 0, k, x, k - 1, k, SB)
            t.set(x, k, k, "stone_brick_wall")


def curtain(t):
    def column(x, z):
        for y in range(11, 20):
            st = SB if y in (11, 12, 19) else (BI if y == 18 else PI)
            t.set(x, y, z, st)
    for x in range(51):
        for z in list(range(12, 15)) + list(range(62, 65)):
            column(x, z)
    for z in range(12, 65):
        for x in (0, 1, 2, 48, 49, 50):
            column(x, z)
    # almenas en la fila exterior
    def merlon(x, z, k):
        if k % 2 == 0:
            t.set(x, 20, z, PI)
            t.set(x, 21, z, "stone_brick_slab[type=bottom]")
        else:
            t.set(x, 20, z, "stone_brick_wall")
    for x in range(51):
        merlon(x, 12, x)
        merlon(x, 64, x)
    for z in range(13, 64):
        merlon(0, z, z)
        merlon(50, z, z)


def tower(t, x0, z0, ladder, mid_doors, ground_doors, chest_name=None, broken=False):
    """Torre de 9 × 9 con tres plantas (pies 11, 20 y 26) y aguja de hielo azul."""
    x1, z1 = x0 + 8, z0 + 8
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            for y in range(11, 30):
                if edge:
                    st = SB if y in (11, 12, 29) else (BI if corner or y in (18, 24) else PI)
                    t.set(x, y, z, st)
                else:
                    t.set(x, y, z, "air")
            if not edge:
                t.set(x, 10, z, SPR)
                t.set(x, 19, z, SPR)
                t.set(x, 25, z, SPR)
    cx, cz = x0 + 4, z0 + 4
    # aguja
    layers = [(30, 30, 0), (31, 32, 1), (33, 35, 2), (36, 39, 3), (40, 44, 4)]
    for ya, yb, ins in layers:
        for x in range(x0 + ins, x1 - ins + 1):
            for z in range(z0 + ins, z1 - ins + 1):
                for y in range(ya, yb + 1):
                    t.set(x, y, z, SB if ins == 0 else (PI if ins == 1 else BI))
    t.set(cx, 45, cz, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    if broken:                                     # punta derribada por el hielo
        for y in range(41, 46):
            ruin(t, cx, y, cz)
        for x, z in ((x0 + 3, z0 + 3), (x0 + 5, z0 + 3)):
            for y in range(37, 40):
                ruin(t, x, y, z)
    # ventanas: sala alta en las cuatro caras, saeteras en la planta media hacia fuera
    for y in (27, 28):
        pane(t, cx, y, z0); pane(t, cx, y, z1); pane(t, x0, y, cz); pane(t, x1, y, cz)
    # escalera de mano y huecos en los forjados
    lx, lz, lf = ladder
    for y in range(11, 26):
        t.set(lx, y, lz, f"ladder[facing={lf},waterlogged=false]")
    for (x, z) in mid_doors:
        air(t, x, 20, z, x, 21, z)
    for (x, z) in ground_doors:
        air(t, x, 11, z, x, 12, z)
    hang(t, cx, 18, cz)
    hang(t, cx, 24, cz)
    hang(t, cx, 29, cz)
    if chest_name:
        chest(t, x0 + 1, 26, z0 + 1 if lz > cz else z1 - 1, "east", chest_name)


def gatehouse(t):
    box(t, 19, 11, 12, 31, 24, 18, PI)
    box(t, 19, 11, 12, 31, 12, 18, SB)
    box(t, 19, 18, 12, 31, 18, 18, BI)
    air(t, 23, 11, 12, 27, 17, 18)                 # paso de la puerta
    for x in (22, 28):
        for y in range(11, 18):
            t.set(x, y, 12, BI)
    for x in range(23, 28):
        t.set(x, 17, 13, "iron_bars")              # rastrillo alzado
    hang(t, 25, 17, 16)
    box(t, 19, 19, 12, 31, 19, 18, SB)             # suelo de la sala del rastrillo
    air(t, 20, 20, 13, 30, 24, 17)
    box(t, 19, 25, 12, 31, 25, 18, SB)
    for x in range(19, 32):
        for z in range(12, 19):
            if x in (19, 31) or z in (12, 18):
                if (x + z) % 2 == 0:
                    t.set(x, 26, z, PI)
                    t.set(x, 27, z, "stone_brick_slab[type=bottom]")
                else:
                    t.set(x, 26, z, "stone_brick_wall")
    for xa in (19, 29):                            # pináculos
        box(t, xa, 26, 12, xa + 2, 28, 14, PI)
        box(t, xa + 1, 29, 13, xa + 1, 32, 13, BI)
    air(t, 19, 20, 13, 19, 21, 14)                 # salidas al adarve
    air(t, 31, 20, 13, 31, 21, 14)
    for x in (22, 28):
        pane(t, x, 21, 12); pane(t, x, 22, 12); pane(t, x, 21, 18); pane(t, x, 22, 18)
    chest(t, 20, 20, 16, "east", "garita")
    t.barrel(20, 20, 17)
    t.set(25, 20, 17, "grindstone[face=floor,facing=east]")
    hang(t, 25, 24, 15)


def building(t, x1, z1, x2, z2, walls, floor=SPR, snow=True):
    """Ala de una planta adosada a la muralla: muros en los lados indicados, tejado plano a y = 16."""
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            wall = ("w" in walls and x == x1) or ("e" in walls and x == x2) or \
                   ("n" in walls and z == z1) or ("s" in walls and z == z2)
            for y in range(11, 16):
                t.set(x, y, z, (SB if y == 11 else PI) if wall else "air")
            if not wall:
                t.set(x, 10, z, floor)
            t.set(x, 16, z, SB)
            if snow:
                t.set(x, 17, z, "snow[layers=1]")


def barracks(t):
    building(t, 3, 21, 12, 39, "nes")
    door(t, 12, 11, 30, "east")
    for z in (23, 25, 27, 32, 34, 36):
        t.set(3, 11, z, "light_blue_bed[facing=west,occupied=false,part=head]")
        t.set(4, 11, z, "light_blue_bed[facing=west,occupied=false,part=foot]")
    chest(t, 3, 11, 29, "east", "barracones")
    chest(t, 3, 11, 38, "east", "barracones")
    for z in (29, 30, 31):
        table(t, 7, 11, z)
        chair(t, 6, 11, z, "west")
        chair(t, 8, 11, z, "east")
    t.barrel(11, 11, 23); t.barrel(11, 11, 24)
    t.set(11, 11, 37, "grindstone[face=floor,facing=north]")
    t.set(11, 11, 36, "crafting_table")
    for z in (25, 35):
        pane(t, 12, 12, z); pane(t, 12, 13, z)
    hang(t, 7, 15, 25); hang(t, 7, 15, 35)


def gallery(t):
    building(t, 3, 41, 12, 55, "nes", floor=PD)
    door(t, 8, 11, 41, "north")
    air(t, 12, 11, 47, 13, 13, 47)                 # paso al gran salón
    air(t, 5, 11, 55, 5, 12, 56)                   # paso a la torre suroeste
    for z in range(42, 55):
        t.set(7, 10, z, BI)                        # franja de hielo azul
    for zc in (44, 48, 52):                        # pedestales junto al muro oeste
        box(t, 3, 11, zc - 1, 5, 11, zc + 1, CSB)
    # caballero
    box(t, 4, 12, 44, 4, 14, 44, BI); t.set(4, 15, 44, PI)
    t.set(4, 14, 43, PI); t.set(4, 14, 45, PI); t.set(4, 12, 45, PI); t.set(4, 13, 45, PI)
    # lobo
    box(t, 4, 12, 47, 4, 12, 49, PI); t.set(4, 13, 47, BI); t.set(4, 13, 49, "packed_ice")
    t.set(5, 13, 47, BI)
    # oso
    box(t, 3, 12, 51, 4, 13, 53, BI); t.set(5, 13, 52, PI); t.set(4, 14, 52, PI)
    # dragón en el lado este
    box(t, 9, 11, 50, 11, 11, 53, CSB)
    box(t, 10, 12, 51, 11, 12, 52, BI); box(t, 10, 13, 50, 10, 14, 50, PI); t.set(10, 15, 50, BI)
    t.set(11, 13, 53, PI); t.set(9, 13, 51, PI); t.set(9, 13, 52, PI)
    chest(t, 3, 11, 54, "east", "galeria")
    for x in (5, 10):
        pane(t, x, 12, 41); pane(t, x, 13, 41)
    for z in (44, 48, 52):
        hang(t, 8, 15, z)


def kitchen(t):
    building(t, 38, 21, 47, 30, "wns")
    door(t, 38, 11, 26, "west")
    for z in (24, 27):                             # hogueras bajo el tiro
        t.set(47, 11, z, "campfire[facing=west,lit=true,signal_fire=false,waterlogged=false]")
        t.set(47, 16, z, "air")
        t.set(47, 17, z, "air")
        for zz in (z - 1, z + 1):
            t.set(47, 11, zz, SB)
    chest(t, 39, 11, 23, "east", "cocina")
    t.set(39, 11, 28, "smoker[facing=east,lit=false]")
    t.set(39, 11, 24, "water_cauldron[level=3]")
    t.barrel(40, 11, 22); t.barrel(41, 11, 22)
    for z in (25, 26):
        table(t, 43, 11, z)
        chair(t, 42, 11, z, "west")
        chair(t, 44, 11, z, "east")
    pane(t, 38, 12, 23); pane(t, 38, 13, 23); pane(t, 38, 12, 29); pane(t, 38, 13, 29)
    hang(t, 42, 15, 28)


def kennel(t):
    building(t, 38, 31, 47, 39, "ws")
    door(t, 38, 11, 35, "west")
    for z in range(31, 39):
        t.set(44, 11, z, "spruce_fence")
    for z in (33, 37):
        t.set(44, 11, z, "spruce_fence_gate[facing=east,in_wall=false,open=false,powered=false]")
    for x in (45, 46, 47):
        t.set(x, 11, 35, "spruce_fence")
    t.set(39, 11, 31, "water_cauldron[level=3]")
    t.set(39, 11, 32, "bone_block[axis=y]")
    t.barrel(39, 11, 38, loot=L + "perrera")
    hang(t, 41, 15, 35)
    pane(t, 38, 12, 32); pane(t, 38, 13, 32)
    for x in range(45, 48):
        for z in range(31, 39):
            t.set(x, 10, z, "white_wool") if z != 35 else None
    # tejado hundido: hueco con escombros dentro del corral
    for x, z in ((45, 37), (46, 37), (46, 38)):
        ruin(t, x, 16, z); ruin(t, x, 17, z)
    ruin(t, 47, 11, 38, "cobblestone")
    ruin(t, 47, 12, 38, "cobblestone_slab[type=bottom]")
    for pos in ((46, 11, 32), (46, 11, 33), (46, 11, 37)):
        t.entity(*pos, {"id": "minecraft:wolf", "PersistenceRequired": B(1), "variant": "minecraft:snowy"})


def mausoleum(t):
    building(t, 38, 41, 47, 55, "wns", floor=PD)
    door(t, 42, 11, 41, "north")
    air(t, 46, 11, 55, 46, 12, 56)                 # paso a la torre sureste
    for z in range(45, 50):
        t.set(40, 11, z, "stone_brick_wall"); t.set(44, 11, z, "stone_brick_wall")
    for x in range(41, 44):
        t.set(x, 11, 49, "stone_brick_wall")
    for (x, z) in ((46, 43), (46, 47), (46, 51), (39, 52)):
        box(t, x, 11, z, x + 1 if x < 47 else x, 11, z + 1, PD)
        t.set(x, 12, z, "candle[candles=2,lit=false,waterlogged=false]")
    hang(t, 42, 15, 52, soul=True)
    hang(t, 42, 15, 43, soul=True)


def great_hall(t):
    x1, x2, z1, z2 = 13, 37, 41, 56
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            wall = x in (x1, x2) or z == z1 or z >= 54
            for y in range(11, 22):
                if wall:
                    t.set(x, y, z, SB if y in (11, 21) else (BI if x in (x1, x2) and z in (z1, z2) else PI))
                else:
                    t.set(x, y, z, "air")
            t.set(x, 22, z, PI)
            if not wall:
                t.set(x, 10, z, PD)
    for z in range(42, 54):
        t.set(25, 10, z, BI)
    # tejado a dos aguas
    for i in range(13):
        y = 23 + i
        for x in range(x1 + i, x2 - i + 1):
            for z in range(z1, z2 + 1):
                if i == 12:
                    t.set(x, y, z, BI)
                elif x == x1 + i:
                    t.set(x, y, z, "stone_brick_stairs[facing=east,half=bottom,shape=straight]")
                elif x == x2 - i:
                    t.set(x, y, z, "stone_brick_stairs[facing=west,half=bottom,shape=straight]")
                else:
                    t.set(x, y, z, PI)
    air(t, 24, 11, 41, 26, 15, 41)                 # puerta mayor
    pane(t, 25, 17, 41); pane(t, 25, 18, 41); pane(t, 25, 19, 41)
    for z in (44, 48, 52):
        for y in range(17, 21):
            pane(t, x1, y, z); pane(t, x2, y, z)
    for x in (17, 33):                             # pilares de hielo azul
        for z in (44, 48, 52):
            box(t, x, 11, z, x, 21, z, BI)
    for xt, (ca, cb) in ((20, ("west", "east")), (30, ("west", "east"))):
        for z in range(44, 50):
            table(t, xt, 11, z)
            chair(t, xt - 1, 11, z, ca)
            chair(t, xt + 1, 11, z, cb)
    # estrado y trono
    box(t, 23, 11, 51, 27, 11, 53, SB)
    for x in range(23, 28):
        t.set(x, 11, 50, "stone_brick_stairs[facing=south,half=bottom,shape=straight]")
    t.set(25, 12, 53, "quartz_stairs[facing=south,half=bottom,shape=straight]")
    t.set(24, 12, 53, BI); t.set(26, 12, 53, BI)
    box(t, 25, 12, 54, 25, 18, 54, BI)
    for x in (24, 26):
        box(t, x, 13, 54, x, 16, 54, BI)
    for x in (23, 27):
        box(t, x, 14, 54, x, 15, 54, BI)
    for x in (19, 31):
        t.set(x, 15, 53, "light_blue_wall_banner[facing=north]")
    for (x, z) in ((20, 46), (30, 46), (25, 44), (25, 49)):
        hang(t, x, 18, z)
    # hornacinas del fondo: la izquierda es señuelo, la derecha es la puerta secreta
    for x in (21, 29):
        air(t, x, 11, 54, x, 12, 54)
        t.set(x, 11, 55, CSB); t.set(x, 12, 55, CSB)
    piston_door(t, door=[(29, 11, 55), (29, 12, 55)], axis=(1, 0, 0), side="west",
                dust=(32, 12, 55), lever=((32, 12, 53), "north"))
    air(t, 29, 11, 56, 29, 12, 56)


def hidden_room(t):
    """Sala oculta del rey, entre el salón y la muralla sur."""
    x1, x2, z1, z2 = 23, 34, 56, 61
    for x in range(x1, x2 + 1):
        for z in range(z1, z2 + 1):
            for y in range(11, 17):
                wall = x in (x1, x2) or z in (z1, z2) or y == 16
                if (x, y, z) in t.blocks and z == 56:
                    continue                       # el muro sur del salón ya está
                t.set(x, y, z, PI if wall else "air")
            if not (x in (x1, x2) or z in (z1, z2)):
                t.set(x, 10, z, SPR)
    air(t, 29, 11, 56, 29, 12, 56)
    chest(t, 24, 11, 60, "east", "tesoro_real")
    t.set(24, 11, 57, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
    t.set(33, 11, 57, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
    t.set(33, 11, 60, "lectern[facing=west,has_book=false,powered=false]")
    for x in (26, 31):
        t.set(x, 13, 60, "light_blue_wall_banner[facing=north]")
    hang(t, 28, 15, 59)


def piston_door(t, door, axis, side, dust, lever):
    """Puerta de dos bloques sujetos por pistones pegajosos extendidos y alimentados por una palanca encendida.
    axis: dirección de la cabeza al pistón (los pistones miran hacia la puerta, `side`)."""
    ax, ay, az = axis
    for (x, y, z) in door:
        t.set(x, y, z, CSB)
        t.set(x + ax, y, z + az, f"piston_head[facing={side},short=false,type=sticky]")
        t.set(x + 2 * ax, y, z + 2 * az, f"sticky_piston[extended=true,facing={side}]")
    dx, dy, dz = dust
    t.set(dx, dy - 1, dz, ST)
    t.set(dx, dy, dz, "redstone_wire[east=side,north=side,power=15,south=side,west=side]")
    (lx, ly, lz), lf = lever
    t.set(lx, ly, lz, f"lever[face=wall,facing={lf},powered=true]")


def courtyard(t):
    # fuente helada
    box(t, 23, 11, 28, 27, 11, 32, BI)
    air(t, 24, 11, 29, 26, 11, 31)
    box(t, 24, 10, 29, 26, 10, 31, PI)
    box(t, 25, 11, 30, 25, 13, 30, PI)
    ruin(t, 25, 14, 30, "air")
    ruin(t, 26, 11, 31, PI)                        # trozo de la estatua caído al vaso
    for (x, z) in ((18, 22), (32, 22), (18, 37), (32, 37)):
        t.set(x, 11, z, "stone_brick_wall"); t.set(x, 12, z, "stone_brick_wall")
        t.set(x, 13, z, "lantern[hanging=false,waterlogged=false]")
    for (x, z) in ((13, 15), (14, 15), (13, 16), (36, 15), (37, 15), (36, 16), (9, 20), (41, 20)):
        t.set(x, 11, z, "snow[layers=2]")


def crypts(t):
    def cave(x1, z1, x2, z2, y1=6, y2=9):
        air(t, x1, y1, z1, x2, y2, z2)
    # escalera del panteón (bajando hacia el sur)
    for i, z in enumerate(range(45, 49)):
        y = 9 - i
        for x in range(41, 44):
            t.set(x, y, z, "stone_brick_stairs[facing=north,half=bottom,shape=straight]")
            air(t, x, y + 1, z, x, 10, z)
    cave(39, 49, 46, 54)                           # vestíbulo
    hang(t, 42, 9, 52, soul=True)
    cave(31, 50, 38, 52)                           # pasillo del cable trampa
    cave(30, 50, 30, 52)
    tripwire(t, (35, 6, 50), (35, 6, 52))
    for x in (34, 36):
        dispenser(t, x, 6, 49, "south", count=16, stacks=3)
        dispenser(t, x, 6, 53, "north", count=16, stacks=3)
    # osario (strays)
    cave(31, 42, 37, 47)
    air(t, 32, 6, 48, 32, 7, 49)
    spawner(t, 34, 6, 45, "stray")
    chest(t, 36, 6, 42, "south", "cripta")
    for x in (31, 32):
        for z in (44, 45):
            t.set(x, 5, z, "powder_snow")
    t.set(31, 6, 42, "skeleton_skull[powered=false,rotation=8]")
    for z in (43, 46):
        t.set(37, 6, z, "bone_block[axis=y]")
    # sala de ofrendas (esqueletos) con derrumbe
    cave(31, 55, 37, 58)
    air(t, 32, 6, 53, 32, 7, 54)
    spawner(t, 34, 6, 57, "skeleton")
    chest(t, 32, 6, 58, "north", "cripta")
    for (x, y, z, st) in ((36, 6, 58, "cobblestone"), (37, 6, 58, "cobblestone"), (37, 7, 58, "gravel"),
                          (37, 6, 57, "cobblestone_slab[type=bottom]")):
        ruin(t, x, y, z, st)
    # cripta del Rey
    cave(17, 45, 29, 57)
    for (x, z) in ((19, 47), (27, 47), (19, 55), (27, 55), (18, 54)):
        box(t, x, 6, z, x, 9, z, BI if (x, z) != (18, 54) else SB)
    box(t, 22, 6, 50, 24, 6, 52, PD)
    t.set(23, 7, 51, "skeleton_skull[powered=false,rotation=0]")
    hang(t, 20, 9, 51, soul=True); hang(t, 26, 9, 51, soul=True)
    t.entity(23, 6, 48, guardian())
    # muro oeste: hornacina señuelo (z = 48) y puerta secreta (z = 51)
    for z in (48, 51):
        air(t, 16, 6, z, 16, 7, z)
        t.set(15, 6, z, CSB); t.set(15, 7, z, CSB)
    piston_door(t, door=[(15, 6, 51), (15, 7, 51)], axis=(0, 0, 1), side="north",
                dust=(15, 7, 54), lever=((17, 7, 54), "east"))
    air(t, 14, 6, 51, 14, 7, 51)
    # escalera a la cámara del tesoro (bajando hacia el oeste)
    air(t, 13, 6, 50, 13, 9, 52)
    for i, x in enumerate(range(12, 8, -1)):
        y = 4 - i
        for z in range(50, 53):
            t.set(x, y, z, "stone_brick_stairs[facing=east,half=bottom,shape=straight]")
            air(t, x, y + 1, z, x, 9, z)
    hang(t, 11, 9, 51, soul=True)
    # antecámara, pasillo de la placa y cámara final
    air(t, 4, 1, 48, 8, 4, 54)
    hang(t, 6, 4, 51, soul=True)
    air(t, 6, 1, 55, 6, 2, 56)
    t.set(6, 1, 55, "stone_pressure_plate[powered=false]")
    dispenser(t, 5, 1, 55, "east", count=16, stacks=3)
    dispenser(t, 7, 1, 55, "west", count=16, stacks=3)
    air(t, 3, 1, 57, 9, 4, 62)
    for (x, z) in ((3, 57), (9, 57), (3, 62), (9, 62)):
        box(t, x, 1, z, x, 4, z, BI)
    chest(t, 6, 1, 62, "north", "premium")
    for x in (4, 8):
        t.set(x, 3, 62, "light_blue_wall_banner[facing=north]")
    hang(t, 6, 4, 59, soul=True)






def wall_ruins(t):
    for z in range(31, 36):                        # brecha en el parapeto este
        ruin(t, 50, 20, z); ruin(t, 50, 21, z)
    for z in (32, 33, 34):
        ruin(t, 50, 19, z, "cobblestone")
    for z in (44, 46, 48):                         # almenas caídas en la muralla oeste
        ruin(t, 0, 20, z); ruin(t, 0, 21, z)


def weather(t, rate):
    """Costras de nieve en el hielo compacto a la vista, en manchas (nunca en una cima: allí nacerían picos de hielo)."""
    import zlib
    for (x, y, z), (st, _) in list(t.blocks.items()):
        if st != "minecraft:packed_ice" or t.get(x, y + 1, z) in (None, "minecraft:air"):
            continue
        if not any(t.get(x + a, y, z + c) == "minecraft:air" for a, c in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        h = zlib.crc32(f"{x // 3},{y // 2},{z // 3}".encode()) % 1000 + zlib.crc32(f"{x},{y},{z}".encode()) % 400
        if h < rate * 1400:
            ruin(t, x, y, z, "snow_block")


def build_template():
    RUIN.clear()
    t = Template(f"unicas/{SID}/fortaleza")
    plinth(t)
    curtain(t)
    air(t, 3, 11, 15, 47, 25, 61)                  # volumen interior del recinto
    gatehouse(t)
    barracks(t)
    gallery(t)
    kitchen(t)
    kennel(t)
    mausoleum(t)
    great_hall(t)
    hidden_room(t)
    tower(t, 0, 12, (1, 16, "east"), [(8, 13), (8, 14), (1, 20), (2, 20)], [(8, 17)])
    tower(t, 42, 12, (49, 16, "west"), [(42, 13), (42, 14), (48, 20), (49, 20)], [(42, 17)], "atalaya", broken=True)
    tower(t, 0, 56, (1, 60, "east"), [(8, 62), (8, 63), (1, 56), (2, 56)], [(5, 56)])
    tower(t, 42, 56, (49, 60, "west"), [(42, 62), (42, 63), (48, 56), (49, 56)], [(46, 56)])
    courtyard(t)
    crypts(t)
    wall_ruins(t)
    # aire explícito en el resto de la caja (el terreno y la nieve no se cuelan dentro)
    for x in range(W):
        for z in range(D):
            for y in range(H):
                if (x, y, z) not in t.blocks:
                    t.set(x, y, z, "air")
    weather(t, WEATHER)
    t.jigsaw(25, 0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
             final_state="minecraft:stone_brick_slab[type=bottom]")
    return t


def guardian():
    return _guardian("stray", "heraldia.unicas.fortaleza_hielo.guardian", "El Rey Escarcha", 40,
                     {"mainhand": {"id": "minecraft:bow", "count": 1, "components": {"minecraft:enchantments": {"minecraft:power": 2}}},
                      "head": "iron_helmet", "chest": "chainmail_chestplate"},
                     {"mainhand": 0.25, "head": 0.15, "chest": 0.15}, CustomNameVisible=B(1))
