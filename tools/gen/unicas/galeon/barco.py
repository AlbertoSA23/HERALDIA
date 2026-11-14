"""El galeón: casco, cubiertas, estancias, palos y la brecha del costado de tierra.

Coordenadas de diseño: X de tierra a mar (crujía SC), Z de proa (0) a popa (61), y = 0 nivel del mar.
Pies: bodega -4, cubierta de cañones 1, principal 5, castillo de proa 9, alcázar 10, toldilla 15, cofa 23.
"""
from .comun import SC

HULL, HULL_LOW, WALE = "dark_oak_planks", "dark_oak_wood[axis=y]", "stripped_dark_oak_log[axis=z]"
DECK, WALL, TRIM = "spruce_planks", "spruce_planks", "honeycomb_block"
MAST = "stripped_spruce_log[axis=y]"
FOREMAST, MAINMAST, MIZZEN = 16, 30, 47
BREACH = range(25, 34)        # brecha del costado de tierra (cubierta de cañones)
BREACH_HOLD = range(27, 32)   # y su prolongación hasta la bodega


def hw(y, z):
    hy = {-6: 2, -5: 4, -4: 6, -3: 7}.get(y, 8 if y <= 8 else 7)
    hz = (2, 3, 4, 5, 5, 6, 6, 7, 7, 7, 8, 8, 8, 8)[z] if z < 14 else (7 if z >= 58 else 8)
    return min(hy, hz)


def bottom(z):
    return {0: -1, 1: -3, 2: -5}.get(z, -6)


def top(z):
    return 9 if z <= 13 else 5 if z <= 44 else 10 if z <= 49 else 15


def in_hull(x, y, z):
    return 0 <= z <= 61 and bottom(z) <= y <= top(z) and abs(x - SC) <= hw(y, z)


def side(o, x, z):
    """Lado del barco de una columna: 'tierra' (X menor) o 'mar'."""
    return "tierra" if x < SC else "mar"


def casco(o):
    shell = set()
    for z in range(0, 62):
        for y in range(bottom(z), top(z) + 1):
            h = hw(y, z)
            for x in range(SC - h, SC + h + 1):
                if any(not in_hull(*n) for n in ((x - 1, y, z), (x + 1, y, z), (x, y, z - 1), (x, y, z + 1), (x, y - 1, z))):
                    shell.add((x, y, z))
                    outer = abs(x - SC) == h
                    if y <= -1:
                        st = HULL_LOW
                    elif y in (0, 4) and outer:
                        st = WALE
                    elif y == top(z) and outer and z >= 45:
                        st = TRIM
                    else:
                        st = HULL
                    o.s(x, y, z, st)
                    if y >= 0 and (outer or z in (0, 61)):
                        o.superficie.add((x, y, z))
                else:
                    o.s(x, y, z, "air")
    o.shell = shell


def interior_row(y, z):
    h = hw(y, z)
    return [x for x in range(SC - h + 1, SC + h) if in_hull(x, y, z) and in_hull(x, y - 1, z)]


def cubiertas(o):
    for z in range(1, 61):
        for y, zs in ((-5, range(1, 61)), (0, range(1, 61)), (4, range(1, 61)), (8, range(1, 13)),
                      (9, range(46, 61)), (14, range(51, 61))):
            if z in zs:
                for x in interior_row(y, z):
                    o.s(x, y, z, DECK)
                    if y in (4, 8, 14) or (y == 9 and z <= 49):
                        o.superficie.add((x, y, z))


def mamparo(o, z, y1, y2, door_x=None, opening=False, door_facing="south"):
    for y in range(y1, y2 + 1):
        for x in interior_row(y, z):
            o.s(x, y, z, WALL)
    if door_x is not None:
        if opening:
            o.air(door_x, y1, z, door_x, y1 + 1, z)
        else:
            o.door(door_x, y1, z, door_facing)


def barandillas(o):
    """Bordas con barandilla y bordes de cubierta con huecos para las escaleras."""
    for z in range(0, 62):
        y = top(z)
        h = hw(y, z)
        for x in (SC - h, SC + h):
            o.s(x, y + 1, z, "spruce_fence")
        if z in (0, 61):
            for x in range(SC - h, SC + h + 1):
                o.s(x, y + 1, z, "spruce_fence")
    # bordes interiores: proa (z=13, pies 9), alcázar (z=45, pies 10), toldilla (z=50, pies 15)
    for z, y, gaps in ((13, 9, {SC}), (45, 10, {59, 69}), (50, 15, {SC})):
        for x in interior_row(y, z) or range(SC - hw(y, z) + 1, SC + hw(y, z)):
            o.s(x, y, z, "air" if x in gaps else "spruce_fence")
    # popa: faroles sobre postes
    for x in (SC - 4, SC, SC + 4):
        o.s(x, 17, 61, "lantern[hanging=false,waterlogged=false]")


def palo(o, z, y_top, lean):
    """Palo desde la bodega; lean = [(y, desplazamiento)] hacia el mar."""
    prev = 0
    for y in range(-4, y_top + 1):
        d = 0
        for yy, dd in lean:
            if y >= yy:
                d = dd
        if d != prev:
            o.s(SC + prev, y, z, MAST)
        o.s(SC + d, y, z, MAST)
        prev = d


def vela(o, z, x1, x2, y1, y2, cruz=False, torn=()):
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            if o.g(x, y, z) and "log" in o.g(x, y, z):
                continue
            if (x, y) in torn:
                o.ruina.add((x, y, z))
                o.superficie.add((x, y, z))
                continue
            st = "white_wool"
            if cruz:
                u, v = (x - x1) / (x2 - x1), (y - y1) / (y2 - y1)
                if abs(u - v) < 0.09 or abs(u - (1 - v)) < 0.09:
                    st = "red_wool"
            o.s(x, y, z, st)
            o.superficie.add((x, y, z))


def verga(o, z, y, x1, x2):
    for x in range(x1, x2 + 1):
        if not (o.g(x, y, z) and "log[axis=y" in o.g(x, y, z)):
            o.s(x, y, z, "spruce_log[axis=x]")


def palos(o):
    palo(o, FOREMAST, 22, [])
    palo(o, MAINMAST, 38, [(26, 1), (31, 2), (35, 3)])
    palo(o, MIZZEN, 28, [(24, 1)])
    # trinquete: el mastelero se partió (está en la playa); queda la verga baja
    verga(o, FOREMAST, 17, SC - 6, SC + 6)
    vela(o, FOREMAST, SC - 5, SC + 5, 9, 16, torn={(SC - 5, 9), (SC - 5, 10), (SC - 4, 9), (SC + 5, 9), (SC + 3, 9), (SC + 4, 9),
                                                     (SC + 5, 10), (SC + 5, 11), (SC - 2, 9)})
    # mayor con la cruz de Borgoña, cofa y gavia
    verga(o, MAINMAST, 19, SC - 7, SC + 7)
    vela(o, MAINMAST, SC - 6, SC + 6, 9, 18, cruz=True,
         torn={(SC - 6, 9), (SC - 6, 10), (SC - 5, 9), (SC + 6, 9), (SC + 2, 9), (SC + 3, 9), (SC + 3, 10), (SC + 6, 13), (SC + 6, 14)})
    o.fill(SC - 2, 22, MAINMAST - 2, SC + 2, 22, MAINMAST + 2, DECK)
    o.s(SC, 22, MAINMAST, MAST)
    for x in range(SC - 2, SC + 3):
        for zz in range(MAINMAST - 2, MAINMAST + 3):
            if x in (SC - 2, SC + 2) or zz in (MAINMAST - 2, MAINMAST + 2):
                o.s(x, 23, zz, "spruce_fence")
    o.ladder(SC, MAINMAST - 1, 5, 22, "north")
    o.chest(SC + 1, 23, MAINMAST + 1, "north", "cofa")
    verga(o, MAINMAST, 31, SC - 3, SC + 7)
    vela(o, MAINMAST, SC - 2, SC + 6, 26, 30, torn={(SC - 2, 26), (SC + 6, 26), (SC + 5, 26)})
    verga(o, MAINMAST, 36, SC, SC + 6)
    # mesana: vela latina pequeña sobre el alcázar
    verga(o, MIZZEN, 22, SC - 4, SC + 5)
    vela(o, MIZZEN, SC - 3, SC + 4, 16, 21, torn={(SC - 3, 16), (SC + 4, 16), (SC + 4, 17)})
    # bauprés
    y, z = 9, -1
    o.s(SC, 9, 0, "stripped_spruce_log[axis=z]")
    for step in range(10):
        o.s(SC, y, z, "stripped_spruce_log[axis=z]")
        if step % 2 == 1:
            y += 1
            o.s(SC, y, z, "stripped_spruce_log[axis=z]")
        z -= 1


def bodega(o):
    mamparo(o, 13, -4, -1, door_x=SC, opening=True)
    mamparo(o, 42, -4, -1, door_x=SC)
    mamparo(o, 49, -4, -1, door_x=SC)
    # bodega de proa: escala al pañol del contramaestre, víveres y generador
    o.ladder(SC - 3, 12, -4, 0, "north")
    o.spawner(SC, -4, 7, "drowned", dark=True)
    o.chest(SC + 2, -4, 11, "west", "bodega")
    for x, z in ((SC - 2, 5), (SC - 2, 6), (SC + 2, 5), (SC + 2, 6), (SC + 3, 8), (SC + 3, 9)):
        o.barrel(x, -4, z)
    # bodega mayor: carga estibada; el pasillo junto al casco lleva al pañol oculto
    for x in range(SC - 3, SC + 5):
        if x != SC:
            for y in (-4, -3, -2, -1):
                o.barrel(x, y, 16)
    for y in (-4, -3, -2, -1):
        o.barrel(SC - 3, y, 17)
    o.chest(SC - 2, -4, 14, "south", "contrabando")
    o.barrel(SC - 1, -4, 14)
    o.barrel(SC + 1, -4, 15, "bodega")
    for z in (19, 20, 21, 34, 35):
        for y in (-4, -3):
            o.barrel(SC + 4, y, z)
    o.chest(SC + 4, -4, 22, "west", "bodega")
    for z in (20, 21, 22):
        o.s(SC - 3, -4, z, "hay_block[axis=y]")
    o.spawner(SC + 3, -4, 25, "drowned", dark=True)
    # pañol de pólvora: sin luz
    for x, z in ((SC - 3, 44), (SC - 3, 45), (SC + 3, 44), (SC + 3, 45), (SC + 3, 46), (SC - 3, 46)):
        o.barrel(x, -4, z)
        o.barrel(x, -3, z)
    o.barrel(SC + 2, -4, 48, "polvora")
    # santabárbara: placa ante el cofre y TNT bajo el suelo
    o.chest(SC, -4, 57, "north", "santabarbara")
    o.s(SC, -4, 56, "stone_pressure_plate[powered=false]")
    for x, z in ((SC, 56), (SC - 1, 56), (SC + 1, 56), (SC, 55)):
        o.s(x, -6, z, "tnt[unstable=false]")
    for x in (SC - 3, SC + 3):
        for z in (51, 52):
            o.barrel(x, -4, z)
    o.circuitos.append(("santabarbara", [("pisar", (SC, -4, 56))], [("tnt", (SC, -6, 56))]))
    # escalera de la bodega a la cubierta de cañones (sube hacia popa)
    o.flight(SC + 3, 36, -4, "south", 5)
    for z in (38, 39, 40):
        o.s(SC + 2, 1, z, "spruce_fence")
        o.s(SC + 4, 1, z, "spruce_fence")
    o.s(SC + 3, 1, 37, "spruce_fence")


def canon(o, x_in, x_out, z):
    o.s(x_out, 2, z, "polished_basalt[axis=x]")
    o.s(x_in, 2, z, "polished_basalt[axis=x]")
    o.s(x_in, 1, z, "spruce_slab[type=top,waterlogged=false]")


def cubierta_canones(o):
    mamparo(o, 13, 1, 3, door_x=SC)
    mamparo(o, 45, 1, 3, door_x=SC)
    # pañol del contramaestre
    o.barrel(SC - 2, 1, 5, "bodega")
    o.barrel(SC + 2, 1, 5)
    o.barrel(SC + 3, 1, 8)
    o.barrel(SC + 3, 1, 9)
    o.s(SC + 4, 1, 11, "grindstone[face=floor,facing=west]")
    o.lantern_hang(SC, 3, 8)
    # batería: siete cañones a estribor, cuatro a babor (la brecha se llevó el resto)
    for z in (16, 20, 24, 28, 32, 36, 40):
        if z == 36 or z == 40:
            pass
        canon(o, SC + 7, SC + 8, z)
    for z in (16, 20, 38, 42):
        canon(o, SC - 7, SC - 8, z)
    o.table(SC, 1, 24)
    o.chair(SC - 1, 1, 24, "west")
    o.chair(SC + 1, 1, 24, "east")
    o.table(SC, 1, 36)
    o.chair(SC - 1, 1, 36, "west")
    for z in (20, 38):
        o.lantern_hang(SC - 2, 3, z)
    o.flight(SC - 3, 18, 1, "south", 4)
    # enfermería del cirujano
    o.bed(SC - 7, 1, 47, "west", "white")
    o.bed(SC - 7, 1, 50, "west", "white")
    o.chest(SC + 7, 1, 48, "west", "cirujano")
    o.s(SC + 7, 1, 50, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]")
    o.s(SC + 7, 1, 52, "water_cauldron[level=3]")
    o.lantern_hang(SC + 3, 3, 52)
    for x in (SC - 2, SC + 2):
        o.s(x, 2, 61, "glass_pane")


def cubierta_principal(o):
    mamparo(o, 13, 5, 7, door_x=SC)
    mamparo(o, 45, 5, 8, door_x=SC)
    # castillo de proa: cocina a estribor, coyes a babor
    o.s(SC + 6, 5, 8, "smoker[facing=west,lit=false]")
    o.s(SC + 6, 5, 9, "furnace[facing=west,lit=false]")
    o.s(SC + 7, 5, 10, "water_cauldron[level=3]")
    o.barrel(SC + 7, 5, 11, "cocina")
    o.bed(SC - 6, 5, 9, "west", "brown")
    o.bed(SC - 7, 5, 11, "west", "brown")
    o.table(SC, 5, 7)
    o.chair(SC, 5, 6, "north")
    o.lantern_hang(SC, 7, 9)
    # escaleras dobles al castillo de proa y rellano sobre la puerta
    o.flight(SC - 4, 14, 5, "east", 4)
    o.flight(SC + 4, 14, 5, "west", 4)
    o.s(SC, 8, 14, DECK)
    # escotilla a la cubierta de cañones con barandilla
    for z in (18, 19, 20):
        o.s(SC - 4, 5, z, "spruce_fence")
        o.s(SC - 2, 5, z, "spruce_fence")
    o.s(SC - 3, 5, 17, "spruce_fence")
    # enjaretados, cabrestante y mastelero caído con trozos de vela
    for x in (SC + 1, SC + 2, SC + 3):
        for z in (36, 37):
            o.s(x, 4, z, "spruce_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]")
    o.s(SC, 5, 39, "stripped_spruce_log[axis=y]")
    o.s(SC, 6, 39, "spruce_slab[type=bottom,waterlogged=false]")
    for x in range(SC - 6, SC + 8):
        if x != SC:
            o.s(x, 5, 24, "spruce_log[axis=x]")
    for x, z in ((SC - 5, 25), (SC - 4, 25), (SC - 4, 26), (SC - 3, 26), (SC + 2, 25)):
        o.s(x, 5, z, "white_carpet")
    # escaleras dobles al alcázar
    o.flight(SC - 5, 40, 5, "south", 5)
    o.flight(SC + 5, 40, 5, "south", 5)
    # cámara de oficiales
    for z in range(50, 55):
        o.table(SC, 5, z)
        o.chair(SC - 1, 5, z, "west")
        o.chair(SC + 1, 5, z, "east")
    o.chest(SC + 7, 5, 57, "west", "oficiales")
    o.s(SC - 7, 5, 57, "cartography_table")
    for x in (SC - 6, SC - 5):
        for y in (5, 6):
            o.s(x, y, 59, "bookshelf")
    o.lantern_hang(SC, 8, 52)
    o.lantern_hang(SC, 8, 57)
    for x in range(SC - 3, SC + 4):
        if x != SC:
            o.s(x, 6, 61, "glass_pane")
            o.s(x, 7, 61, "glass_pane")


def castillo_popa(o):
    """Alcázar, antecámara, camarote del capitán, cámara del tesorero y toldilla."""
    # fachada del castillo (z=50) con puerta y escaleras dobles a la toldilla
    for y in range(10, 14):
        for x in interior_row(y, 50):
            o.s(x, y, 50, WALL)
    for x in interior_row(14, 50):
        o.s(x, 14, 50, DECK)
    o.door(SC, 10, 50, "south")
    o.flight(SC - 5, 49, 10, "east", 5)
    o.flight(SC + 5, 49, 10, "west", 5)
    o.s(SC, 14, 49, DECK)
    # mamparo entre antecámara y camarote (z=53) y bloque macizo que esconde el mecanismo
    for y in range(10, 14):
        for x in interior_row(y, 53):
            if x >= SC - 4:
                o.s(x, y, 53, WALL)
        for z in (51, 52):
            for x in range(SC - 4, SC):
                o.s(x, y, z, WALL)
        for z in range(54, 61):
            o.s(SC - 4, y, z, "bookshelf" if y <= 11 else WALL)
    o.door(SC + 3, 10, 53, "south")
    # cámara del tesorero (X 58-59) y puerta secreta de estanterías
    x_w = SC - 4                     # muro del camarote
    for y in (10, 11):
        o.s(x_w, y, 52, "sticky_piston[extended=true,facing=south]")
        o.s(x_w, y, 53, "piston_head[facing=south,short=false,type=sticky]")
        o.s(x_w, y, 54, "bookshelf")
        o.t.solved_open.add((x_w, y, 54))
    o.s(x_w + 1, 10, 52, "redstone_wall_torch[facing=north,lit=true]")
    o.s(x_w + 1, 10, 54, "lever[face=wall,facing=south,powered=false]")
    o.circuitos.append(("estanteria", [("palanca", (x_w + 1, 10, 54))],
                        [("retraido", (x_w, 10, 52)), ("retraido", (x_w, 11, 52))]))
    o.chest(SC - 6, 10, 60, "east", "tesorero")
    o.barrel(SC - 6, 10, 58)
    o.barrel(SC - 6, 11, 58)
    o.lantern_hang(SC - 5, 13, 56)
    # antecámara
    o.barrel(SC + 6, 10, 51)
    o.s(SC + 6, 10, 52, "spruce_slab[type=bottom,waterlogged=false]")
    # camarote del capitán
    for x in range(SC - 3, SC + 7):
        for z in range(55, 61):
            o.s(x, 10, z, "red_carpet")
    o.bed(SC + 6, 10, 60, "south", "red")
    o.table(SC + 1, 10, 58)
    o.chair(SC + 1, 10, 57, "north")
    o.chest(SC + 6, 10, 55, "west", "capitan")
    o.s(SC + 4, 10, 54, "lectern[facing=south,has_book=false,powered=false]")
    o.s(SC - 2, 10, 60, "cartography_table")
    o.lantern_hang(SC + 1, 13, 56)
    for x in range(SC - 2, SC + 6):
        for y in (11, 12):
            if (x, y) in ((SC, 11), (SC + 1, 12)):
                o.romper(x, y, 61)        # cristales rotos de la popa
            else:
                o.s(x, y, 61, "glass_pane")
            o.superficie.add((x, y, 61))


def brecha(o):
    """Costado de tierra reventado por la varada: se entra desde la playa a la cubierta de cañones."""
    xl = SC - 8
    for z in BREACH:
        for y in (1, 2, 3):
            o.romper(xl, y, z)
        o.romper(xl, 5, z)          # borda y barandilla arrancadas
        o.romper(xl, 6, z)
        if z in (27, 28, 29, 30):
            o.romper(xl + 1, 4, z)  # cubierta principal hundida sobre la brecha
            o.romper(xl + 2, 4, z) if z in (28, 29) else None
    o.romper(xl, 3, 24)
    o.romper(xl, 3, 34)
    for z in BREACH_HOLD:
        o.romper(SC - 7, -3, z, "sand")
        o.romper(SC - 8, -2, z)
        o.romper(SC - 8, -1, z)
        o.romper(SC - 5, -4, z, "sand")
        o.s(SC - 4, -4, z, "sand")
        o.romper(SC - 6, -3, z, "sand")
    for x, z in ((SC - 7, 26), (SC - 7, 31), (SC - 6, 28)):
        o.s(x, 1, z, "sand")
    # percebes en la línea de flotación del costado de mar
    for z in range(6, 58, 5):
        o.romper(SC + hw(0, z), 0, z, "dead_brain_coral_block")


def construir(o):
    casco(o)
    cubiertas(o)
    bodega(o)
    cubierta_canones(o)
    cubierta_principal(o)
    castillo_popa(o)
    barandillas(o)
    palos(o)
    brecha(o)
    # la escotilla de la proa y la escala de la cofa atraviesan cubiertas
