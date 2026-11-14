"""Mobiliario, luz, reflejo y partes asimétricas sobre la superficie (sacristía, biblioteca, claustro)."""
import math
from .base import *
from .modelo import bay, vault, NAVE_POSTS, CHOIR_POSTS, OPEN_A, CHAPEL_A, RING


def furnish_symmetric(c):
    # --- nave: bancos, alfombra, arañas
    for x in range(20, 58, 2):
        for z in range(26, 29):
            c.set(x, 1, z, stairs("oak", "west"))
    for x in range(8, 59):
        for z in (29, 30):
            c.set(x, 1, z, "red_carpet")
    for x in (20, 32, 44, 56):
        c.hang(x, 8, 30, 27)
    for x in (26, 38, 50):
        c.lamp(x, 1, 25)
    # púlpito adosado a un pilar
    c.set(41, 1, 25, CSB)
    c.set(41, 2, 25, s("oak_trapdoor", facing="south", half="top", open=False))
    c.set(42, 1, 25, s("oak_stairs", facing="east"))
    # --- colaterales y triforio: un farol por tramo
    for x in list(range(18, 59)) + list(range(72, 89)):
        b = bay(x)
        if b and b[0] == (b[1] - 1) // 2:
            c.hang(x, 9, 21, 11)
            c.hang(x, 15, 21, 16)
    # --- pasarela alta sobre el brazo del crucero (une los triforios de la nave y del coro)
    for x in range(60, 71):
        for z in (20, 21, 22):
            c.set(x, 11, z, SB)
            c.set(x, 10, z, stairs("stone_brick", "south" if z == 20 else ("north" if z == 22 else "west"), "top") if z != 21 else SB)
        c.set(x, 12, 19, WALLB)
        c.set(x, 12, 23, WALLB)
    c.lamp(65, 13, 19)
    c.lamp(62, 13, 23)
    c.lamp(68, 13, 23)
    # --- brazo del crucero y crucero
    c.hang(65, 8, 12, 27)
    c.hang(65, 10, 26, 27)
    c.lamp(60, 1, 9)
    c.lamp(70, 1, 9)
    c.lamp(60, 1, 21)
    c.lamp(70, 1, 21)
    # --- coro: sillería con respaldo, arañas
    for x in range(73, 88):
        if x in (79, 80):
            continue
        c.set(x, 1, 25, "spruce_planks")
        c.set(x, 2, 25, "spruce_planks")
        c.set(x, 3, 25, s("spruce_trapdoor", facing="south", half="bottom", open=False))
        c.set(x, 1, 26, stairs("spruce", "north"))
    c.hang(78, 8, 30, 27)
    c.hang(85, 8, 30, 27)
    c.lamp(79, 1, 27)
    # --- altar mayor sobre estrado (ábside)
    for x in range(86, 96):
        for z in range(24, 31):
            d = math.hypot(x - AX, z - AZ)
            if x >= 88 and d <= 4.6:
                c.set(x, 1, z, PD)
            elif x == 87 and d <= 4.6:
                c.set(x, 1, z, stairs("polished_diorite", "east"))
    for z in (29, 30):
        c.set(91, 2, z, "smooth_quartz")
        c.candles(91, 3, z, 4 if z == 30 else 3)
    c.set(92, 2, 30, "smooth_quartz")
    c.set(92, 3, 30, "gold_block")
    c.hang(90, 12, 30, 27)
    # --- girola: faroles por vano; capillas con altar, velas y un barril
    for a in (-72, -36, 0):
        for (dd, y, top) in ((9, 9, 11), (9, 15, 16)):
            x = int(round(AX + dd * math.cos(math.radians(a))))
            z = int(round(AZ + dd * math.sin(math.radians(a))))
            c.hang(x, y, z, top)
    for a in CHAPEL_A:
        if a > 0:
            continue
        cx, cz = c.chapel_center(a)
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        ax, az = int(round(cx + 2 * ca)), int(round(cz + 2 * sa))
        c.set(ax, 1, az, CSB)
        c.candles(ax, 2, az, 3)
        px, pz = int(round(cx - sa * 1.6)), int(round(cz + ca * 1.6))
        if a == 0:
            px, pz = int(round(cx)), int(round(cz - 2))
        c.chest(px, 1, pz, "south" if a == 0 else "up", "capilla", f"capilla radial {int(a)}", kind="barrel")
        c.lamp(int(round(cx - 1.5 * ca)), 1, int(round(cz - 1.5 * sa)) + (1 if a else 0))
    # --- torres: un farol por estancia
    for f in (1, 12, 17, 28, 40):
        c.hang(14, f + 2, 20, f + 4) if f in (12,) else c.lamp(15, f, 21)
    c.lamp(9, 56, 21)
    # --- nártex y tribuna (órgano)
    for x in (10, 14):
        c.hang(x, 8, 27, 10)
    for x in (8, 9, 10, 14):
        h = 6 + (3 - abs(x - 11.5)) * 2
        for y in range(12, 12 + int(h)):
            c.set(x, y, 24, s("lightning_rod", facing="up"))
    c.set(11, 12, 26, "note_block")
    c.set(12, 12, 26, "note_block")
    c.set(11, 12, 27, stairs("dark_oak", "west"))
    c.lamp(14, 12, 29)
    # --- desván: faroles a lo largo del caballete
    for x in (22, 34, 46, 58, 66, 78, 88):
        c.lamp(x, 28, 30)
    for z in (12, 20):
        c.lamp(65, 28, z)
    # --- terraza de la fachada
    c.lamp(16, 28, 26)


def mirror(c):
    t = c.t
    for (x, y, z), (st, nbt) in list(t.blocks.items()):
        if z < ZC:
            t.set(x, y, 2 * ZC - z, mirror_state(st), dict(nbt) if nbt else None)
    for (pos, tabla, sitio) in list(c.chests):
        x, y, z = pos
        if z < ZC:
            c.chests.append(((x, y, 2 * ZC - z), tabla, sitio + " (sur)"))
    c.flights |= {(x, y, 2 * ZC - z) for (x, y, z) in c.flights if z < ZC}


# ---------------------------------------------------------------------- partes asimétricas
def annex(c):
    """Sacristía (planta baja), biblioteca (alta) y gabinete secreto, al norte del coro."""
    X0, X1, Z0, Z1 = 78, 94, 4, 17
    # contrafuertes que sustituye el anejo
    for x in (77, 83, 89):
        c.air(x, 0, 13, x, 26, 17)
        for r in range(7, 13):
            for y in range(18, 27):
                if c.get(x, y, 30 - r) == "minecraft:stone_bricks":
                    c.set(x, y, 30 - r, "air")
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            edge = x in (X0, X1) or z in (Z0, Z1)
            c.fill(x, 0, z, x, 16, z, SB)
            if not edge:
                c.set(x, 0, z, PA)
                c.air(x, 1, z, x, 7, z)
                c.set(x, 8, z, "spruce_planks")
                c.air(x, 9, z, x, 14, z)
                c.set(x, 16, z, SM)
            else:
                c.set(x, 17, z, WALLB)
    for x in range(90, 95):
        for z in range(17, 20):
            d, _ = polar(x, z)
            if d > 11.5 and c.get(x, 1, z) in (None, "minecraft:air"):
                c.fill(x, 0, z, x, 16, z, SB)
    # el muro del colateral pierde aquí sus ventanas (dan al anejo)
    for x in range(X0, 90):
        c.fill(x, 3, 18, x, 9, 18, SB)
        c.fill(x, 13, 18, x, 14, 18, SB)
    # muro grueso del gabinete (x 86..88, z 5..10) y su cierre (z = 11, x 89..93)
    for x in range(86, 89):
        for z in range(5, 11):
            c.fill(x, 8, z, x, 15, z, SB)
    for x in range(89, 94):
        c.fill(x, 9, 11, x, 15, 11, SB)
    for x in range(89, 94):
        for z in range(5, 11):
            c.set(x, 8, z, "spruce_planks")
    # puerta de la sacristía desde la girola norte
    c.air(80, 1, 17, 80, 2, 18)
    c.door(80, 1, 17, "north", "left", wood="spruce")
    # escalera sacristía -> biblioteca (z = 16, sube hacia el este)
    for k in range(8):
        x = 82 + k
        c.stair_flight([(x, 1 + k, 16, stairs("spruce", "east"))])
        if k:
            c.fill(x, 1, 16, x, k, 16, "spruce_planks")
    c.air(87, 8, 16, 88, 8, 16)
    for x in (87, 88):
        c.set(x, 9, 15, "spruce_fence")
    c.set(86, 9, 16, "spruce_fence")
    # salida a la terraza del coro por la cubierta del anejo
    c.air(85, 17, 18, 86, 17, 18)
    # sacristía: armarios, cofres, pila, facistol
    for x in range(79, 86):
        c.set(x, 1, 5, s("barrel", facing="up") if x % 2 else "spruce_planks")
        if x % 2 == 0:
            c.set(x, 2, 5, s("spruce_trapdoor", facing="south", half="bottom", open=False))
    c.chest(87, 1, 5, "south", "sacristia", "sacristía, junto a los armarios")
    c.chest(92, 1, 12, "west", "sacristia", "sacristía, rincón este")
    c.set(92, 1, 8, s("water_cauldron", level=3))
    c.set(89, 1, 8, s("lectern", facing="east"))
    for x in range(81, 90, 4):
        c.hang(x, 6, 10, 8)
    c.lamp(93, 1, 15)
    for x in range(90, 93):
        c.set(x, 1, 15, "white_carpet" if x % 2 else "red_carpet")
    # biblioteca: estanterías en los muros, mesas de lectura y atriles
    for x in range(79, 86):
        for y in range(9, 12):
            if x != 82:
                c.set(x, y, 5, "bookshelf")
    for z in range(6, 16):
        for y in range(9, 12):
            if z not in (8, 12):
                c.set(79, y, z, "bookshelf")
    for x in range(89, 94):
        for y in range(9, 12):
            c.set(x, y, 12, "bookshelf")
    for x in (81, 82, 83):
        c.set(x, 9, 9, s("spruce_slab", type="top"))
    c.set(82, 10, 9, s("candle", candles=2, lit=True))
    for x in (81, 83):
        c.set(x, 9, 8, stairs("spruce", "north"))
        c.set(x, 9, 10, stairs("spruce", "south"))
    c.set(91, 9, 15, s("lectern", facing="north"))
    c.chest(84, 9, 6, "south", "biblioteca", "biblioteca")
    for (x, z) in ((82, 13), (90, 14)):
        c.hang(x, 13, z, 15)
    for z in (8, 12):
        c.fill(78, 10, z, 78, 13, z, "white_stained_glass_pane")
    for x in (82, 91):
        c.fill(x, 10, 4, x, 13, 4, "white_stained_glass_pane")
        c.fill(x, 3, 4, x, 5, 4, "white_stained_glass_pane")
    # gabinete secreto (x 89..93, z 5..10)
    c.chest(93, 9, 7, "west", "oculto", "gabinete secreto de la biblioteca")
    c.set(91, 9, 5, "bookshelf")
    c.set(92, 9, 5, "bookshelf")
    c.set(90, 9, 10, s("lectern", facing="south"))
    c.set(93, 9, 10, "spruce_planks")
    c.candles(93, 10, 10, 3)
    c.set(89, 9, 5, s("cartography_table"))
    c.hang(91, 13, 7, 15)
    c.hang(84, 13, 9, 15)
    # torreta de servicio (escalera de caracol: sacristía -> triforio del coro -> terraza)
    tb(c)


def tb(c):
    cx, cz = 74, 14
    c.fill(cx - 2, 0, cz - 2, cx + 2, 19, cz + 2, SB)
    c.air(cx - 1, 1, cz - 1, cx + 1, 19, cz + 1)
    c.fill(cx - 1, 0, cz - 1, cx + 1, 0, cz + 1, PA)
    c.fill(cx, 0, cz, cx, 19, cz, SB)
    c.spiral(cx, cz, start=6, k_max=32)
    for x in range(cx - 2, cx + 3):
        for z in range(cz - 2, cz + 3):
            d = max(abs(x - cx), abs(z - cz))
            c.set(x, 20, z, ROOF if d == 2 else SB)
            if d <= 1:
                c.set(x, 21, z, ROOF)
    # planta baja: puerta este hacia la sacristía
    c.air(76, 1, 14, 78, 2, 14)
    c.set(77, 0, 14, PA)
    c.fill(77, 3, 13, 77, 3, 15, SB)
    for z in (13, 15):
        c.fill(77, 0, z, 77, 2, z, SB)
    # triforio (pies en 12) y terraza (pies en 17), por la cara sur
    c.air(74, 12, 16, 74, 13, 16)
    c.air(74, 17, 16, 74, 18, 16)
    c.set(74, 11, 17, SB)
    c.air(74, 12, 17, 74, 13, 17)
    c.fill(74, 14, 17, 74, 16, 17, SB)
    c.air(74, 17, 17, 74, 18, 17)
    for x in (73, 75):
        c.fill(x, 11, 17, x, 16, 17, SB)
    c.air(74, 12, 18, 74, 13, 18)
    c.set(74, 17, 18, "air")
    c.lamp(73, 1, 13)


def cloister(c):
    """Claustro al sur de la nave, sala capitular y refectorio en ruinas."""
    # paso desde el colateral sur (tramo x 30..34)
    c.fill(31, 3, 42, 33, 9, 42, SB)
    c.set(32, 3, 42, CSB)
    c.air(32, 1, 42, 32, 2, 42)
    for x in range(30, 35):
        for z in range(43, 47):
            edge = x in (30, 34)
            c.fill(x, 0, z, x, 5, z, SB)
            if not edge:
                c.set(x, 0, z, PA)
                c.air(x, 1, z, x, 4, z)
            c.set(x, 6, z, slab("stone_brick"))
    c.hang(32, 4, 44, 5)
    # recinto
    X0, X1, Z0, Z1 = 22, 56, 47, 77
    GX0, GX1, GZ0, GZ1 = 27, 51, 52, 72
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (X0, X1) or z in (Z0, Z1):
                c.fill(x, 0, z, x, 8, z, SB)
                c.set(x, 9, z, WALLB if (x + z) % 2 else SB)
            elif GX0 < x < GX1 and GZ0 < z < GZ1:
                c.set(x, 0, z, "grass_block")
            elif (x in (GX0, GX1) and GZ0 <= z <= GZ1) or (z in (GZ0, GZ1) and GX0 <= x <= GX1):
                c.set(x, 0, z, PA)
                along = x if z in (GZ0, GZ1) else z
                mid = (GX0 + GX1) // 2 if z in (GZ0, GZ1) else (GZ0 + GZ1) // 2
                corner = x in (GX0, GX1) and z in (GZ0, GZ1)
                if corner or (along - (GX0 if z in (GZ0, GZ1) else GZ0)) % 3 == 0:
                    c.fill(x, 1, z, x, 4, z, PA)
                    c.set(x, 1, z, CSB)
                else:
                    c.air(x, 1, z, x, 4, z)
                    if abs(along - mid) > 1:
                        c.set(x, 1, z, WALLB)
                    c.set(x, 4, z, stairs("stone_brick", "south" if z == GZ0 else "north" if z == GZ1 else
                                          "east" if x == GX0 else "west", "top"))
                c.fill(x, 5, z, x, 6, z, SB)
                c.set(x, 7, z, ROOF)
            else:
                c.set(x, 0, z, PA)
                c.air(x, 1, z, x, 5, z)
                c.set(x, 6, z, SB)
                inner = min(abs(x - GX0), abs(x - GX1), abs(z - GZ0), abs(z - GZ1))
                c.set(x, 7, z, ROOF)
                if inner >= 2:
                    c.set(x, 8, z, ROOF)
    c.air(32, 1, 47, 32, 2, 47)
    # jardín: caminos en cruz, pozo, flores y un árbol viejo
    for x in range(GX0 + 1, GX1):
        c.set(x, 0, 62, "gravel")
    for z in range(GZ0 + 1, GZ1):
        c.set(39, 0, z, "gravel")
    for x in range(37, 42):
        for z in range(60, 65):
            if max(abs(x - 39), abs(z - 62)) == 2:
                c.set(x, 0, z, SB)
                c.set(x, 1, z, WALLB)
            elif max(abs(x - 39), abs(z - 62)) == 1:
                c.set(x, 0, z, SB)
    c.set(39, 0, 62, "water")
    for (x, z) in ((37, 60), (41, 60), (37, 64), (41, 64)):
        c.fill(x, 2, z, x, 3, z, WALLB)
        c.set(x, 4, z, slab("stone_brick"))
    flowers = ["poppy", "cornflower", "lily_of_the_valley", "oxeye_daisy", "allium", "azure_bluet"]
    k = 0
    for x in range(GX0 + 2, GX1 - 1, 3):
        for z in range(GZ0 + 2, GZ1 - 1, 3):
            if x != 39 and z != 62 and not (36 <= x <= 42 and 59 <= z <= 65) and not (44 <= x <= 49 and 66 <= z <= 71):
                c.set(x, 1, z, flowers[k % len(flowers)])
                k += 1
    tx, tz = 47, 68
    for y in range(1, 6):
        c.set(tx, y, tz, s("oak_log", axis="y"))
    for x in range(tx - 2, tx + 3):
        for z in range(tz - 2, tz + 3):
            for y in range(4, 8):
                if (x, z) != (tx, tz) or y >= 6:
                    if abs(x - tx) + abs(z - tz) + max(0, y - 5) <= 3:
                        c.set(x, y, z, s("oak_leaves", persistent=True, distance=1))
    # luz bajo las pandas
    for (x, z) in ((24, 49), (39, 49), (54, 49), (24, 62), (54, 62), (24, 75), (54, 75), (31, 75), (47, 75), (31, 49), (47, 49),
                   (24, 55), (24, 69), (54, 55), (54, 69)):
        c.hang(x, 5, z, 6)
    c.chest(23, 1, 76, "north", "menor", "claustro, rincón suroeste", kind="barrel")
    # sala capitular (x 57..71, z 55..69), puerta desde la panda este
    S0, S1, T0, T1 = 57, 71, 58, 72
    for x in range(S0, S1 + 1):
        for z in range(T0, T1 + 1):
            edge = x in (S0, S1) or z in (T0, T1)
            c.fill(x, 0, z, x, 9, z, SB)
            if not edge:
                c.set(x, 0, z, PA if (x + z) % 2 else PD)
                c.air(x, 1, z, x, 8, z)
            hip = min(x - S0, S1 - x, z - T0, T1 - z)
            for y in range(10, 10 + min(hip, 4) + 1):
                c.set(x, y, z, ROOF)
    c.air(56, 1, 65, 57, 2, 65)
    c.set(56, 3, 65, CSB)
    for z in range(T0 + 2, T1 - 1):
        if z != 65:
            c.set(S1 - 1, 1, z, stairs("stone_brick", "east"))
    for x in range(S0 + 2, S1 - 1):
        c.set(x, 1, T0 + 1, stairs("stone_brick", "north"))
        c.set(x, 1, T1 - 1, stairs("stone_brick", "south"))
    c.set(64, 1, 65, s("lectern", facing="west"))
    c.hang(64, 5, 65, 9)
    c.hang(60, 6, 61, 9)
    c.hang(68, 6, 69, 9)
    c.hang(60, 6, 69, 9)
    c.hang(68, 6, 61, 9)
    c.chest(58, 1, 71, "north", "menor", "sala capitular")
    for z in (62, 68):
        c.fill(S1, 3, z, S1, 6, z, "white_stained_glass_pane")
    for x in (61, 67):
        c.fill(x, 3, T1, x, 6, T1, "white_stained_glass_pane")
    # refectorio arruinado (x 22..56, z 77..87): sin cubierta, muros mellados
    R0, R1, Q0, Q1 = 22, 56, 77, 87
    for x in range(R0, R1 + 1):
        for z in range(Q0, Q1 + 1):
            edge = x in (R0, R1) or z in (Q0, Q1)
            if edge:
                top = 8 if z == Q0 else 3 + (x * 7 + z * 3) % 5
                c.fill(x, 0, z, x, top, z, SB)
                if z != Q0:
                    c.ruin.add((x, top + 1, z))
            else:
                c.set(x, 0, z, PA if (x * 3 + z) % 7 else "mossy_cobblestone")
                c.air(x, 1, z, x, 6, z)
    c.air(39, 1, 77, 39, 2, 77)
    for x in range(26, 53):
        if x % 9 not in (4, 5):
            c.set(x, 1, 81, slab("spruce", "top"))
    for (x, z, b) in ((30, 84, "cobblestone"), (31, 84, "mossy_cobblestone"), (44, 79, "cobblestone"), (45, 80, "gravel"),
                      (50, 85, "mossy_cobblestone"), (35, 79, "moss_carpet"), (36, 79, "moss_carpet"), (27, 85, "moss_carpet")):
        c.set(x, 1, z, b)
        c.ruin.add((x, 1, z))
    c.chest(55, 1, 86, "west", "menor", "refectorio en ruinas")
    for x in range(R0 + 1, R1):
        for z in range(Q0 + 1, Q1):
            c.ruin.add((x, 7, z))      # cubierta desaparecida
