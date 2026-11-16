"""El fuerte del corsario en la meseta del cerro: muralla con camino de ronda, baluarte con cañones mirando al norte,
la casa del corsario, el cuartel, el aljibe, el mástil de la bandera y la torre de la bajada a las cuevas."""
from .obra import S, slab, stairs, h, FUERTE, PLAT, SB, COB, PL, LOG, DV
from .._comun import piezas

Y = PLAT + 1                 # pies en el patio
TOP = Y + 4                  # cima del adarve (bloque); pies del camino de ronda a TOP + 1
GATE = (71, 72)              # puerta de la muralla sur (x)
BASTION = [(66, 24), (64, 19), (72, 13), (80, 19), (78, 24)]   # polígono del baluarte (x, z)


def dentro(poly, x, z):
    """Punto en polígono (par-impar) sobre los centros de las celdas."""
    px, pz, c = x + 0.5, z + 0.5, False
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz) and px < x1 + (pz - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def construir(o):
    x0, x1, z0, z1 = FUERTE
    patio(o, x0, x1, z0, z1)
    muralla(o, x0, x1, z0, z1)
    baluarte(o)
    casa(o)
    cuartel(o)
    aljibe(o, 74, 39)
    bandera(o, 66, 41)
    o.mech["bajada"] = bajada(o)


def patio(o, x0, x1, z0, z1):
    """Patio empedrado (grava y piedra) a la altura de la meseta; nada fértil donde pueda nacer vegetación."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            o.s(x, PLAT, z, "gravel" if h(x, z, 11) < 0.55 else ("cobblestone" if h(x, z, 12) < 0.6 else "andesite"))
            o.s(x, PLAT - 1, z, "stone")
            o.a(x, Y, z, x, Y + 8, z)


def muralla(o, x0, x1, z0, z1):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            outer = x in (x0, x1) or z in (z0, z1)
            inner = not outer and (x in (x0 + 1, x1 - 1) or z in (z0 + 1, z1 - 1))
            if outer:
                o.f(x, PLAT, z, x, TOP + 1, z, SB)
                o.s(x, PLAT, z, COB)
                corner = x in (x0, x1) and z in (z0, z1)
                if corner or (x + z) % 2 == 0:
                    if not corner and h(x, z, 41) < 0.22:
                        o.ruin.add((x, TOP + 2, z))           # almena caída
                    else:
                        o.s(x, TOP + 2, z, SB)                 # almenas
            elif inner:
                o.f(x, PLAT, z, x, TOP, z, SB)
    # puerta: arco de dos de ancho en la muralla sur, puerta doble de abeto
    for x in GATE:
        o.a(x, Y, z1 - 1, x, Y + 2, z1)
    piezas.double_door(o.s, GATE[0], Y, z1, "south", "east", kind="spruce_door")
    o.s(GATE[0] - 1, Y + 2, z1 + 1, S("wall_torch", facing="south"))
    o.s(GATE[1] + 1, Y + 2, z1 + 1, S("wall_torch", facing="south"))
    o.sign(GATE[1] + 1, Y + 1, z1 + 1, "south", "fuerte", [("Fuerte de", "Fort of"), ("Roque Salitre", "Roque Salitre"),
                                                             ("No se admiten", "No flags but"), ("otras banderas", "the black one")])
    # subidas al camino de ronda (oeste y este), de 5 peldaños hacia el norte pegadas a la muralla
    for x in (x0 + 2, x1 - 2):
        o.flight(x, z1 - 4, Y, "north", 5, mat="stone_brick", support=SB)
    # paso del camino de ronda al baluarte (sin almena en la muralla norte)
    for x in (71, 72, 73):
        o.a(x, TOP + 1, z0, x, TOP + 3, z0)


def baluarte(o):
    """Baluarte de cinco lados al norte, macizo hasta la plataforma (a la altura del camino de ronda) y con parapeto,
    cuatro cañones en sus caras y un polvorín."""
    cells = [(x, z) for x in range(60, 86) for z in range(10, FUERTE[2]) if dentro(BASTION, x, z)]
    cs = set(cells)
    for (x, z) in cells:
        g = o.ground.get((x, z))
        y0 = g if g is not None else -1
        for y in range(min(y0, PLAT), TOP + 1):
            o.s(x, y, z, SB if y > PLAT else COB)
        borde = any((x + a, z + b) not in cs and z + b < FUERTE[2] for a in (-1, 0, 1) for b in (-1, 0, 1))
        if borde:
            o.s(x, TOP + 1, z, SB)
            if (x + z) % 2 == 0:
                o.s(x, TOP + 2, z, SB)
        else:
            o.a(x, TOP + 1, z, x, TOP + 4, z)
    # cañones: dispensadores (decorativos, vacíos) en el parapeto, mirando afuera, con ruedas de trampilla
    o.mech["canones"] = []
    for (x, z, f) in ((68, 17, "north"), (76, 17, "north"), (66, 20, "west"), (78, 20, "east")):
        dx, dz = DV[f]
        bx, bz = x + dx, z + dz       # celda del parapeto donde va la boca
        if (bx, bz) not in cs:
            bx, bz = x, z
        o.s(bx, TOP + 1, bz, S("dispenser", facing=f, triggered=False), {"id": "minecraft:dispenser"})
        o.a(bx, TOP + 2, bz, bx, TOP + 2, bz)
        o.mech["canones"].append((bx, TOP + 1, bz))
    o.s(72, TOP + 1, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.chest(71, TOP + 1, 21, "south", "polvorin")
    o.s(73, TOP + 1, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})


def casa(o):
    """Casa del corsario (pegada a la muralla norte, al oeste): planta baja con la mesa de los capitanes y la chimenea,
    y arriba la alcoba del corsario. Muros de abeto con pies derechos, zócalo de piedra y tejado a dos aguas."""
    x0, x1, z0, z1 = 62, 70, 26, 33
    yt = Y + 4                  # forjado del piso (pies arriba a yt + 1)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            o.s(x, PLAT, z, COB if edge else PL)
            for y in range(Y, yt + 5):
                if edge:
                    o.s(x, y, z, LOG if corner else (COB if y == Y else PL))
                else:
                    o.s(x, y, z, "air")
            if not edge:
                o.s(x, yt, z, PL)
    # tejado a dos aguas a lo largo de x (cumbrera en z = 29,5)
    for i in range(5):
        for x in range(x0 - 1, x1 + 2):
            o.s(x, yt + 4 + i, z0 - 1 + i, stairs("dark_oak", "south"))
            o.s(x, yt + 4 + i, z1 + 1 - i, stairs("dark_oak", "north"))
            if 0 < i:
                for z in range(z0 - 1 + i + 1, z1 + 1 - i):
                    if x in (x0, x1):
                        o.s(x, yt + 4 + i, z, PL)       # hastiales
    # ventanas
    for z in (28, 31):
        for y in (Y + 1, yt + 2):
            o.s(x0, y, z, S("glass_pane"))
            o.s(x1, y, z, S("glass_pane"))
    for x in (64, 68):
        o.s(x, yt + 2, z1, S("glass_pane"))
    o.door(66, Y, z1, "south")
    # planta baja: mesa larga con sillas, chimenea al este y la mesa de cartografía
    for x in range(64, 68):
        o.table(x, Y, 30)
        o.chair(x, Y, 29, "north")
        o.chair(x, Y, 31, "south")
    o.s(69, Y, 30, "campfire[facing=west,lit=true,signal_fire=false,waterlogged=false]")
    o.f(69, Y + 1, 30, 69, yt + 6, 30, "bricks")
    o.s(69, Y, 28, "cartography_table")
    o.chest(69, Y, 32, "west", "casa")
    o.hang(66, yt - 1, 30)
    # escalera al piso pegada al muro norte: sube hacia el este desde el rincón noroeste (pies 8 a pies 13)
    o.flight(64, 27, Y, "east", 5, mat="spruce", support=PL)
    for x in range(64, 68):
        o.a(x, yt, 27, x, yt, 27)
        o.s(x, yt + 1, 28, "spruce_fence")
    # piso: alcoba del corsario
    yy = yt + 1
    o.s(63, yy, 31, S("black_bed", facing="south", part="foot", occupied=False))
    o.s(63, yy, 32, S("black_bed", facing="south", part="head", occupied=False))
    o.chest(64, yy, 32, "north", "corsario")
    o.s(68, yy, 32, "lectern[facing=north,has_book=false,powered=false]")
    o.s(66, yy, 32, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.banner(66, yy + 2, 32, "north", "black")
    o.hang(65, yy + 3, 30)


def cuartel(o):
    """Cuartel de la tripulación (al este del patio): literas, armero y la mesa de juego."""
    x0, x1, z0, z1 = 75, 82, 26, 32
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            o.s(x, PLAT, z, COB if edge else PL)
            for y in range(Y, Y + 4):
                o.s(x, y, z, (LOG if x in (x0, x1) and z in (z0, z1) else (COB if y == Y else PL)) if edge else "air")
            o.s(x, Y + 4, z, slab("spruce") if edge else PL)
    o.door(78, Y, z1, "south")
    for x in (76, 80):
        o.s(x, Y + 1, z1, S("glass_pane"))
    for z in (28, 30):
        o.s(x1, Y + 1, z, S("glass_pane"))
    for x in (76, 78, 80):
        o.bed(x, Y, 28, "north", "brown")
    o.chest(81, Y, 27, "west", "cuartel")
    o.s(76, Y, 31, "crafting_table")
    o.hang(78, Y + 3, 29)


def aljibe(o, x, z):
    """Aljibe del patio: brocal de piedra, agua y tejadillo sobre postes."""
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            o.s(x + a, PLAT, z + b, SB)
            if a or b:
                o.s(x + a, Y, z + b, SB)
    o.s(x, PLAT, z, "water")
    o.s(x, PLAT - 1, z, SB)
    for (a, b) in ((-1, -1), (1, 1)):
        o.f(x + a, Y + 1, z + b, x + a, Y + 2, z + b, "spruce_fence")
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            o.s(x + a, Y + 3, z + b, slab("spruce"))
    o.s(x, Y + 2, z, S("iron_chain", axis="y"))
    o.s(x, Y + 1, z, S("lantern", hanging=True, waterlogged=False))


def bandera(o, x, z):
    o.s(x, PLAT, z, SB)
    o.f(x, Y, z, x, Y + 7, z, "spruce_fence")
    o.s(x + 1, Y + 6, z, "black_wool")
    o.s(x + 2, Y + 6, z, "black_wool")
    o.s(x + 1, Y + 5, z, "black_wool")
    o.s(x + 2, Y + 5, z, "white_wool")


def bajada(o):
    """Torre de la bajada a las cuevas (rincón sureste del patio): una escalera recta que baja al cuerpo de guardia."""
    x0, x1, z0, z1 = 77, 82, 37, 43
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            for y in range(Y, Y + 4):
                o.s(x, y, z, SB if edge else "air")
            o.s(x, Y + 4, z, SB)
            if edge:
                o.s(x, Y + 5, z, SB if (x + z) % 2 == 0 else "air")
    o.door(79, Y, z0, "north")
    o.hang(79, Y + 3, 40)
    # escalera que baja hacia el sur desde el patio (pies 8) hasta las cuevas (pies 1): 7 peldaños en x = 80
    return dict(x=80, z_top=38)
