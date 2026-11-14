"""Castellum (depósito, pieza de inicio) y acueducto de dos pisos."""

CX0, CZ0, CX1, CZ1 = 72, -12, 86, 4          # castellum
AX0, AX1, AZ0, AZ1 = 77, 81, -98, -13        # acueducto
WIRE = "redstone_wire[east={e},north={n},power=0,south={s},west={w}]"


def wire(o, x, y, z, n="none", s="none", e="none", w="none"):
    o.s(x, y, z, WIRE.format(n=n, s=s, e=e, w=w))


def castellum(o):
    o.air(CX0, 1, CZ0, CX1, 17, CZ1)
    o.f(CX0, 0, CZ0, CX1, 0, CZ1, "smooth_sandstone")
    o.ring(CX0, CZ0, CX1, CZ1, 1, 1, "cut_sandstone")
    o.ring(CX0, CZ0, CX1, CZ1, 2, 13, "smooth_sandstone")
    o.ring(CX0, CZ0, CX1, CZ1, 14, 14, "chiseled_sandstone")
    o.ring(CX0, CZ0, CX1, CZ1, 15, 16, "cut_sandstone")
    for y in range(2, 14):                            # pilastras
        for x in (CX0, 76, 82, CX1):
            o.s(x, y, CZ0, "cut_sandstone"); o.s(x, y, CZ1, "cut_sandstone")
        for z in (CZ0, -6, 0, CZ1):
            o.s(CX0, y, z, "cut_sandstone"); o.s(CX1, y, z, "cut_sandstone")
    for k in range(CX0, CX1 + 1, 2):
        if not 76 <= k <= 82:
            o.s(k, 17, CZ0, "cut_sandstone")
        o.s(k, 17, CZ1, "cut_sandstone")
    for k in range(CZ0, CZ1 + 1, 2):
        o.s(CX0, 17, k, "cut_sandstone"); o.s(CX1, 17, k, "cut_sandstone")
    o.f(73, 7, -11, 85, 7, 3, "smooth_sandstone")      # suelo de la planta 1
    o.f(73, 14, -11, 85, 14, 3, "smooth_sandstone")    # azotea
    o.f(73, 1, -11, 76, 13, 3, "smooth_sandstone")     # macizo oeste (muro doble y pasillo oculto)
    o.air(73, 1, -11, 74, 3, 3)
    # ---- planta baja: sala de reparto
    o.door(79, CZ1, "south"); o.s(79, 3, CZ1, "chiseled_sandstone")
    o.sign(80, 3, CZ1 + 1, "south", [("heraldia.unicas.acueducto.cartel.castellum1", "CASTELLVM"),
                                    ("heraldia.unicas.acueducto.cartel.castellum2", "AQVAE")])
    o.ring(79, -7, 83, -3, 1, 1, "cut_sandstone")
    o.f(80, 1, -6, 82, 1, -4, "water")
    o.f(81, 1, -5, 81, 3, -5, "quartz_pillar[axis=y]"); o.s(81, 4, -5, "chiseled_quartz_block")
    for k, z in enumerate(range(2, -5, -1)):          # escalera a la planta 1, junto al muro este
        y = k + 1
        o.f(85, 1, z, 85, y - 1, z, "smooth_sandstone") if y > 1 else None
        o.stair(85, y, z, "north")
    o.air(85, 7, -3, 85, 7, -2)
    for z in (-3, -2):
        o.s(84, 8, z, "sandstone_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
    o.lantern(81, 6, -9); o.lantern(81, 6, 1)
    o.pot(77, 1, 3, "east"); o.pot(82, 1, 3, "north"); o.barrel(77, 1, -11, None)
    # palancas del puzle 1 con sus rótulos
    for name, z, key, fb in (("A", -3, "aqva", "AQVA"), ("I", -1, "ignis", "IGNIS"), ("T", 1, "terra", "TERRA")):
        o.s(77, 1, z, "lever[face=wall,facing=east,powered=false]")
        o.sign(77, 2, z, "east", [("heraldia.unicas.acueducto.palanca." + key, fb)])
        o.red["palanca_" + name] = (77, 1, z)
    # hornacina y mecanismo dentro del muro doble (x 75-76) y del pasillo oculto (x 73-74)
    o.air(76, 1, -9, 76, 2, -9)
    o.f(75, 1, -9, 75, 2, -9, "chiseled_sandstone")
    for y in (1, 2):
        o.s(75, y, -8, "piston_head[facing=north,short=false,type=sticky]")
        o.s(75, y, -7, "sticky_piston[extended=true,facing=north]")
    o.red["piston_1"], o.red["piston_2"] = (75, 1, -7), (75, 2, -7)
    o.red["puerta_1"] = [(75, 1, -9), (75, 2, -9)]
    wire(o, 75, 2, -6, n="side", s="side")             # sobre el bloque que alimenta al pistón de abajo
    o.air(75, 2, -5, 75, 2, -5)
    wire(o, 75, 1, -5, w="side", n="up")
    for z in range(-5, 2):
        wire(o, 74, 1, z, n="side" if z > -5 else "none", s="side" if z < 1 else "none",
             e="side" if z in (-5, -3, -1, 1) else "none")
    o.s(75, 1, -3, "redstone_wall_torch[facing=west,lit=true]")
    o.s(75, 1, 1, "redstone_wall_torch[facing=west,lit=true]")
    wire(o, 75, 1, -1, w="side", e="side")
    o.red["antorcha_A"], o.red["antorcha_T"] = (75, 1, -3), (75, 1, 1)
    # escalera secreta: baja hacia el sur desde el pasillo oculto (sigue en la pieza de las cloacas)
    o.stair(73, 0, -6, "north", "stone_brick_stairs")
    o.air(73, 0, -5, 73, 0, -4)
    # ---- planta 1: oficina del curator aquarum
    for k, z in enumerate(range(2, -5, -1)):          # escalera a la azotea, junto al muro oeste
        y = k + 8
        if y > 8:
            o.f(77, 8, z, 77, y - 1, z, "smooth_sandstone")
        o.stair(77, y, z, "north")
    o.air(77, 14, -3, 77, 14, -2)
    for z in (-3, -2):
        o.s(78, 15, z, "sandstone_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
    o.s(81, 8, -11, "lectern[facing=south,has_book=false,powered=false]")
    o.chest(84, 8, -11, "south", "menor")
    for x in (78, 79, 80, 82, 83):
        o.f(x, 8, -11, x, 9, -11, "bookshelf")
    o.s(81, 8, -4, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
    o.s(81, 9, -4, "brown_carpet")
    o.stair(80, 8, -4, "west", "spruce_stairs"); o.stair(82, 8, -4, "east", "spruce_stairs")
    o.barrel(84, 8, 3, "menor"); o.barrel(83, 8, 3, None); o.pot(79, 8, 3, "north")
    o.s(85, 8, 3, "cartography_table")
    for z in (-8, -4, 0):
        o.s(CX1, 10, z, "iron_bars")
    for x in (79, 83):
        o.s(x, 10, CZ1, "iron_bars")
    o.lantern(81, 13, -7); o.lantern(81, 13, 0)
    # ---- azotea con el depósito
    o.ring(79, -10, 83, -6, 15, 15, "cut_sandstone")
    o.f(80, 15, -9, 82, 15, -7, "water")
    o.f(79, 15, CZ0, 79, 16, CZ0, "iron_bars")
    o.s(84, 15, 2, "lantern[hanging=false,waterlogged=false]")
    o.sup += 15 * 17


def acueducto(o):
    o.air(AX0, 0, AZ0, AX1, 17, AZ1)
    pillars = [(-13 - 7 * k, -14 - 7 * k) for k in range(13)]
    for (za, zb) in pillars:
        for z in (za, zb):
            o.f(AX0, 0, z, AX1, 0, z, "smooth_sandstone")
            o.f(AX0, 1, z, AX1, 13, z, "cut_sandstone")
            o.f(AX0, 5, z, AX1, 5, z, "smooth_sandstone")
    for k in range(12):
        hi, lo = pillars[k][1] - 1, pillars[k + 1][0] + 1     # vano de 5: hi (sur) .. lo (norte)
        for x in range(AX0, AX1 + 1):
            for base in (5, 11):
                o.stair(x, base, hi, "south", "smooth_sandstone_stairs", "top")
                o.stair(x, base, lo, "north", "smooth_sandstone_stairs", "top")
                o.s(x, base + 1, hi, "cut_sandstone"); o.s(x, base + 1, lo, "cut_sandstone")
                o.stair(x, base + 1, hi - 1, "south", "smooth_sandstone_stairs", "top")
                o.stair(x, base + 1, lo + 1, "north", "smooth_sandstone_stairs", "top")
                o.f(x, base + 2, lo, x, base + 2, hi, "cut_sandstone")
    # impostas, canal (specus) y cubierta
    o.f(AX0, 8, AZ0, AX1, 8, AZ1, "smooth_sandstone")
    o.f(AX0, 14, AZ0, AX1, 14, AZ1, "smooth_sandstone")
    o.f(78, 15, AZ0, 78, 16, AZ1, "cut_sandstone"); o.f(80, 15, AZ0, 80, 16, AZ1, "cut_sandstone")
    for z in range(AZ0, AZ1 + 1):
        o.slab(AX0, 15, z); o.slab(AX1, 15, z)
        for x in (78, 79, 80):
            o.slab(x, 17, z, "bottom", "smooth_sandstone_slab")
        if z % 9 == 0:
            o.s(79, 15, z, "sand")
    o.sup += 5 * (AZ1 - AZ0 + 1)
    # ruina 1: el vano 9-10 se ha desplomado (piso alto, canal y clave del arco bajo)
    hi, lo = pillars[9][1] - 1, pillars[10][0] + 1
    for z in range(lo, hi + 1):
        cut = 9 if lo < z < hi else 12
        o.air(AX0, cut, z, AX1, 17, z)
    o.air(AX0, 7, lo + 2, AX1, 8, lo + 2)
    # ruina 2: los dos últimos vanos y el último pilar perdieron el piso alto
    for z in range(AZ0, pillars[11][1]):
        o.air(AX0, 9, z, AX1, 17, z)
    hi, lo = pillars[11][1] - 1, pillars[12][0] + 1
    o.air(AX0, 5, lo, AX1, 8, hi - 1)
    for z, top in zip((pillars[12][0], pillars[12][1]), (5, 4)):
        o.air(AX0, top + 1, z, AX1, 8, z)
        o.air(AX0 + 1, top, z, AX0 + 2, top, z)
    o.ruina += 5 * (5 + 16)
    # la tapa del canal perdida en algunos tramos
    for z in range(-60, -52):
        o.air(78, 17, z, 80, 17, z)
    o.ruina += 3 * 8 // 2


def construir(o):
    castellum(o)
    acueducto(o)
