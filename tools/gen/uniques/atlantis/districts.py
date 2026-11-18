"""Distritos singulares de la Atlántida. Cada función recibe una Vista centrada en el distrito cuyo «norte» local
(v negativo) mira al centro de la ciudad; y = 0 es el pavimento."""
import math
from . import urban_layout as U
from . import things as C
from . import buildings as E
from . import redstone as R
from .._common import pieces as P
from .buildings import BRICK, DARK, PRISMARINE, LANTERN, GLASS, QUARTZ, PILLAR, CORALS, h, door, column

COMBINATION_CENTRAL = [True, False, True, True]         # palancas del vestíbulo del templo: I, III y IV alzadas
COMBINATION_ACADEMY = [False, True, True, False]


def room(v, u1, v1, u2, v2, y1, y2, wall=BRICK, floor=DARK, roof=DARK):
    """Sala seca: caja con aire dentro. y1 = suelo, y2 = techo."""
    v.shell(u1, y1, v1, u2, y2, v2, wall, floor=floor, roof=roof)
    v.air(u1 + 1, y1 + 1, v1 + 1, u2 - 1, y2 - 1, v2 - 1)


def clue(n, es, en):
    """Cartel con una cifra de la combinación del templo."""
    return [C.text("pista.titulo", "Sello sagrado", "Temple seal", bold=C.B(1)),
            C.text(f"pista.{n}", es, en)]


# ------------------------------------------------------------------ N: ágora
def agora(v):
    A, F = 44, 38                                   # semiancho y semifondo de la plaza porticada
    v.site("agora", -A, 0, -F, A, 12, F)
    for u in range(-A, A + 1):
        for w in range(-F, F + 1):
            edge_block = max(abs(u) - (A - 4), abs(w) - (F - 4))
            if abs(u) <= U.AVENUE:
                continue                            # la avenida cruza la plaza
            if edge_block >= 0:
                v.set(u, 0, w, BRICK)
                v.set(u, 7, w, DARK if edge_block in (0, 4) else BRICK)       # arquitrabe del pórtico
                if edge_block == 0 and (u % 4 == 0 and abs(w) <= F - 4 or w % 4 == 0 and abs(u) <= A - 4):
                    column(v, u, w, 1, 6)
                if edge_block == 4:
                    if (u + w) % 6 == 0:
                        v.set(u, 6, w, LANTERN)
            else:
                v.set(u, 0, w, DARK if (u // 2 + w // 2) % 2 else PRISMARINE)
    for side in (-1, 1):                            # estatuas del tridente a cada lado de la avenida
        cu = side * 22
        v.fill(cu - 2, 1, -2, cu + 2, 1, 2, QUARTZ)
        v.fill(cu - 1, 2, -1, cu + 1, 2, 1, QUARTZ)
        v.fill(cu, 3, 0, cu, 9, 0, "waxed_oxidized_cut_copper")
        for du in (-2, 2):
            v.fill(cu + du, 8, 0, cu + du, 11, 0, "waxed_oxidized_cut_copper")
        v.fill(cu - 2, 8, 0, cu + 2, 8, 0, "waxed_oxidized_cut_copper")
        v.fill(cu, 10, 0, cu, 12, 0, "waxed_oxidized_cut_copper")
        v.set(cu, 2, -2, LANTERN)
        v.set(cu, 2, 2, LANTERN)
    # casa del consejo (seca), al fondo este de la plaza, con puerta a la plaza
    u1, u2, w1, w2 = 14, 34, 12, 28
    room(v, u1, w1, u2, w2, 0, 7)
    door(v, (u1 + u2) // 2, 1, w1, "north")
    for u in range(u1 + 2, u2 - 1):                 # graderío de tres filas al fondo
        for row in range(3):
            v.set(u, 1 + row, w2 - 1 - (2 - row), "prismarine_brick_stairs[facing=south,half=bottom]")
            for y in range(1, 1 + row):
                v.set(u, y, w2 - 1 - (2 - row), BRICK)
    for u in (u1 + 1, u2 - 1):
        v.set(u, 6, w1 + 1, LANTERN)
        v.set(u, 6, w2 - 1, LANTERN)
    C.sign(v, u1 + 4, 2, w1 + 1, "south", [C.text("agora.1", "Tres sellos dan", "Three seals open"),
                                             C.text("agora.2", "paso al templo:", "the temple path:"),
                                             C.text("agora.3", "arsenal, academia", "arsenal, academy"),
                                             C.text("agora.4", "y anfiteatro.", "and amphitheatre.")])
    C.sign(v, u2 - 4, 2, w1 + 1, "south", [C.text("agora.5", "Sus llaves abren", "Their keys open"),
                                             C.text("agora.6", "arcas del templo.", "temple coffers."),
                                             C.text("agora.7", "La de Poseidón", "Poseidon's key"),
                                             C.text("agora.8", "es del guardián.", "is with his warden.")])
    C.cofre(v, u1 + 1, 1, w1 + 4, "east", "media")
    v.set(u2 - 1, 1, w1 + 4, "lectern[facing=west]", {"id": "minecraft:lectern"})
    v.mark("seca", u1 + 3, 1, w1 + 3)
    E.windows(v, u1, "w", w1, w2, 3, 4)
    E.windows(v, u2, "w", w1, w2, 3, 4)
    E.ornament(v, u1, w1, u2, w2, 0, 7, step=5)
    # mercado en ruinas (inundado), al fondo oeste
    for k in range(4):
        cu, cw = -18 - (k % 2) * 10, 14 + (k // 2) * 10
        v.fill(cu - 2, 1, cw - 2, cu + 2, 1, cw - 2, "stripped_warped_stem[axis=x]")
        for du in (-2, 2):
            v.fill(cu + du, 1, cw - 1, cu + du, 3, cw - 1, "warped_fence")
        v.fill(cu - 2, 4, cw - 2, cu + 2, 4, cw, "warped_slab[type=bottom]") if k != 2 else None
        v.set(cu, 1, cw, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLE + "menor"})
        v.mark("cofre", cu, 1, cw)
    v.entity(-10, 2, -10, C.guardian())
    v.entity(10, 2, -14, C.guardian())
    v.entity(-24, 2, 6, C.drowned())


# ------------------------------------------------------------------ E: termas
def ends_of(side, u1, u2):
    return u2 - 2 if side == 1 else u1 + 2


def baths(v):
    v.site("termas", -36, 0, -30, 36, 22, 30)
    # tres naves paralelas a la avenida, a cada lado: frigidario (inundado, cúpula), tepidario (seco) y caldario (magma)
    for side in (-1, 1):
        u1, u2 = (10, 34) if side == 1 else (-34, -10)
        # frigidario: gran sala inundada con cúpula de cristal
        v.shell(u1, 0, -28, u2, 9, -8, BRICK, floor=DARK, roof=DARK)
        cu, cw = (u1 + u2) // 2, -18
        v.remove(cu - 6, 9, cw - 6, cu + 6, 9, cw + 6)
        v.dome(cu, cw, 8, 9, GLASS, rib=DARK)
        v.disk(cu, cw, 8, 9, 9, DARK, cavity=7)
        v.remove(u1 if side == 1 else u2, 1, cw - 1, u1 if side == 1 else u2, 3, cw + 1)        # portal a la avenida
        v.fill(cu - 4, 0, cw - 4, cu + 4, 0, cw + 4, PRISMARINE)
        v.disk(cu, cw, 3, 0, 0, LANTERN, cavity=2)
        for du, dw in ((-9, -8), (9, -8), (-9, 8), (9, 8)):
            column(v, cu + du, cw + dw, 1, 8)
        # tepidario: sala seca con bancos
        room(v, u1, -8, u2, 8, 0, 7)
        door(v, cu, 1, -8, "north")
        for u in range(u1 + 2, u2 - 1, 2):
            v.set(u, 1, -6, "prismarine_brick_stairs[facing=north,half=bottom]")
            v.set(u, 1, 6, "prismarine_brick_stairs[facing=south,half=bottom]")
        v.set(u1 + 1, 6, -7, LANTERN)
        v.set(u2 - 1, 6, 7, LANTERN)
        v.set(u1 + 1, 6, 7, LANTERN)
        v.set(u2 - 1, 6, -7, LANTERN)
        v.mark("seca", cu, 1, 0)
        door(v, cu, 1, 8, "south")
        # caldario: sala inundada con suelo de magma (arrastra al fondo) y un ascensor de burbujas a la galería alta
        v.shell(u1, 0, 8, u2, 16, 28, BRICK, floor=DARK, roof=DARK)
        door(v, cu, 1, 8, "south")
        for u in range(u1 + 3, u2 - 2):
            for w in range(12, 26):
                if (u + w) % 3 == 0 and abs(u - ends_of(side, u1, u2)) > 2:
                    v.set(u, 0, w, "magma_block")
                    v.fill(u, 1, w, u, 8, w, "bubble_column[drag=true]")
        v.fill(u1 + 1, 9, 9, u2 - 1, 9, 27, DARK)                                          # forjado de la galería
        v.fill(u1 + 1, 10, 9, u2 - 1, 15, 27, "air")
        ex = u2 - 2 if side == 1 else u1 + 2                                                 # ascensor: columna de arena de almas
        v.set(ex, 0, 26, "soul_sand")
        v.fill(ex - 1, 1, 25, ex + 1, 8, 27, GLASS)
        v.fill(ex, 1, 26, ex, 9, 26, "bubble_column[drag=false]")           # explícita: en la generación no hay actualizaciones
        v.remove(ex, 1, 25, ex, 2, 25)
        v.set(u1 + 1, 15, 9, LANTERN)
        v.set(u2 - 1, 15, 27, LANTERN)
        C.cofre(v, cu, 10, 10, "south", "media")
        if side == 1:
            C.sign(v, cu + 2, 11, 9, "south", clue(4, "IV: alzada", "IV: raised"))
        v.mark("seca", cu, 10, 18)
        v.mark("burbuja", ex, 9, 26)
        v.entity(cu, 4, 18, C.guardian())
        C.generator(v, u1 + 1 if side == 1 else u2 - 1, 1, 27, "guardian")
        back = u2 if side == 1 else u1
        E.windows(v, back, "w", -8, 8, 3, 4)
        E.windows(v, back, "w", 8, 28, 11, 13)
        E.ornament(v, u1, -28, u2, -8, 0, 9)
        E.ornament(v, u1, -8, u2, 8, 0, 7, parapet=False)
        E.ornament(v, u1, 8, u2, 28, 0, 16)
    v.entity(0, 4, -18, C.guardian())
    v.entity(0, 4, 18, C.guardian())


# ------------------------------------------------------------------ S: puerto hundido
def ship(v, cu, cw, length, salt, wood="spruce"):
    """Casco hundido y escorado, con la bodega abierta."""
    for i in range(length):
        width = 3 if 2 <= i < length - 3 else 2 if 1 <= i < length - 1 else 1
        w = cw + i
        for du in range(-width, width + 1):
            v.set(cu + du, 1, w, f"{wood}_planks")
            if abs(du) == width and h(cu + du, w, salt) % 6:
                v.fill(cu + du, 2, w, cu + du, 3 if h(cu + du, w, salt + 1) % 3 else 2, w, f"{wood}_planks")
        if i in (length // 3, 2 * length // 3):
            height = 4 + h(i, salt, 2) % 5
            v.fill(cu, 2, w, cu, height, w, f"stripped_{wood}_log[axis=y]")
    v.fill(cu - 1, 2, cw + length - 4, cu + 1, 2, cw + length - 2, f"{wood}_slab[type=top]")
    v.set(cu, 2, cw + length // 2, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLE + ("media" if salt % 2 else "menor")})
    v.mark("cofre", cu, 2, cw + length // 2)
    v.site("barco", cu - 4, 1, cw, cu + 4, 9, cw + length, ruinous=True)


def harbor(v):
    v.site("puerto", -46, 0, -36, 46, 14, 36, ruinous=True)
    for side in (-1, 1):
        for u in range(10, 46):
            for w in range(-36, 37):
                uu = side * u
                dock = u < 16 or abs(w) > 30 or abs(w) < 3
                if dock:
                    broken = h(uu, w, 21) % 9 == 0
                    v.fill(uu, 0, w, uu, 2 if not broken else 1, w, BRICK if (u + w) % 5 else DARK)
                    if u == 10 and w % 6 == 0 and not broken:
                        v.fill(uu, 3, w, uu, 4, w, "dark_oak_fence")
                        v.set(uu, 5, w, "sea_lantern")
                else:
                    v.set(uu, 0, w, "sand" if h(uu, w, 22) % 4 else "gravel")
                    r = h(uu, w, 23) % 60
                    if r < 3:
                        height = 2 + r * 2
                        v.fill(uu, 1, w, uu, height - 1, w, "kelp_plant")
                        v.set(uu, height, w, "kelp[age=25]")
                    elif r < 6:
                        v.set(uu, 1, w, "seagrass")
        ship(v, side * 24, -26, 20, 30 + side)
        ship(v, side * 36, 6, 22, 40 + side, wood="dark_oak")
    # faro derruido al fondo
    for k, (cu, cw) in enumerate(((-30, 0), (30, 0))):
        v.disk(cu, cw, 4, 3, 5 + (h(cu, cw, 24) % 4), BRICK, cavity=3)
        v.set(cu, 3, cw, "chest[facing=north]", {"id": "minecraft:chest", "LootTable": C.TABLE + "media"})
        v.mark("cofre", cu, 3, cw)
    for u, w, elite in ((-20, -10, True), (20, -10, True), (-34, 20, False), (34, 20, False), (-24, 30, False), (24, 30, True), (0, 20, True)):
        v.entity(u, 3, w, C.drowned(elite))
    for u, w in ((-28, -20), (28, 12)):
        C.generator(v, u, 2, w, "drowned", trident=True)


# ------------------------------------------------------------------ O: academia
def academy(v):
    v.site("academia", -42, 0, -30, 42, 16, 38)
    for side in (-1, 1):
        s = side
        u1, u2 = (10, 40) if side == 1 else (-40, -10)
        ua, ub = (u1, u2)
        # ala: vestíbulo + biblioteca, toda seca; puerta doble a la avenida
        room(v, ua, -26, ub, 26, 0, 9)
        face = u1 if side == 1 else u2
        P.double_door(v.set, face, 1, -1, "west" if side == 1 else "east", "south", E.PUERTA)
        for w in (-22, -14, -6, 6, 14, 22):                                   # ventanales
            back = u2 if side == 1 else u1
            v.fill(back, 3, w - 1, back, 6, w + 1, GLASS)
        for w in range(-24, 25, 6):                                           # estanterías en espina
            if abs(w) < 4:
                continue
            for u in range(min(ua, ub) + 4, max(ua, ub) - 3):
                if (u - ua) % 9 in (4, 5) or abs(u - (ua + ub) // 2) < 2:
                    continue
                v.fill(u, 1, w, u, 3, w, "bookshelf")
        for u in (ua + 1, ub - 1):
            for w in (-25, 25):
                v.set(u, 8, w, LANTERN)
        for w in (-12, 12):
            v.set((ua + ub) // 2, 9, w, LANTERN)
        v.set((ua + ub) // 2, 1, -24, "lectern[facing=south]", {"id": "minecraft:lectern"})
        v.set((ua + ub) // 2, 1, 24, "lectern[facing=north]", {"id": "minecraft:lectern"})
        v.mark("seca", (ua + ub) // 2, 1, 0)
        E.ornament(v, ua, -26, ub, 26, 0, 9)
        v.entity((ua + ub) // 2, 1, 10, C.drowned(side == 1))
        if side == 1:
            C.generator(v, ua + 2, 1, 20, "drowned", trident=False)
            C.cofre(v, ub - 1, 1, 20, "west", "media")
    # ala norte (lado 1, hacia v negativo): las cuatro pistas de la combinación, repartidas tras las estanterías
    clues = [("academia.p1", "Primera: suelta", "First: released"), ("academia.p2", "Segunda: alzada", "Second: raised"),
              ("academia.p3", "Tercera: alzada", "Third: raised"), ("academia.p4", "Cuarta: suelta", "Fourth: released")]
    for (key, es, en), (u, w, facing) in zip(clues, ((39, -20, "west"), (-39, -20, "east"), (39, 20, "west"), (-39, 20, "east"))):
        C.sign(v, u, 2, w, facing, [C.text(key, es, en)])
    # cámara del sello: tras la puerta de combinación, en el testero sur del ala este
    u0 = 14
    finish = R.combination(v, u0, 2, 26, COMBINATION_ACADEMY, "academia")
    room(v, u0 - 2, 29, u0 + 12, 37, 0, 5)
    v.air(finish[0], 1, 29, finish[0], 2, 29)
    v.set(u0 - 1, 4, 30, LANTERN)
    C.cofre(v, u0 + 4, 1, 36, "north", "sello_academia")
    C.sign(v, u0 + 6, 2, 36, "north", clue(2, "II: suelta", "II: released"))
    v.mark("seca", u0 + 5, 1, 33)
    v.mark("camara_academia", finish[0], 1, 31)


# ------------------------------------------------------------------ SE: arsenal
def arsenal(v):
    L = 34
    v.site("arsenal", -L, 0, -L, L, 20, L)
    # recinto amurallado con torres en las esquinas y patio inundado
    for u in range(-L, L + 1):
        for w in range(-L, L + 1):
            if max(abs(u), abs(w)) >= L - 2:
                v.fill(u, 0, w, u, 9, w, BRICK)
                if max(abs(u), abs(w)) == L and (u + w) % 2 == 0:
                    v.set(u, 10, w, DARK)
            else:
                v.set(u, 0, w, DARK if (u + w) % 2 else BRICK)
    for su in (-1, 1):
        for sw in (-1, 1):
            v.disk(su * (L - 2), sw * (L - 2), 5, 0, 13, BRICK)
            v.disk(su * (L - 2), sw * (L - 2), 5, 14, 14, DARK)
            v.set(su * (L - 2), 15, sw * (L - 2), LANTERN)
    v.remove(-2, 1, -L, 2, 5, -L + 2)                                        # puerta del recinto (al norte local)
    v.entity(0, 5, -16, C.elder())
    for u, w in ((-20, -20), (20, -20), (-22, 10), (22, 10)):
        v.entity(u, 3, w, C.guardian())
    C.generator(v, -L + 4, 1, 0, "guardian")
    C.generator(v, L - 4, 1, 0, "guardian")
    # torre del homenaje (seca): puerta -> pasillo de trampas -> armería -> cámara del sello tras una palanca oculta
    u1, u2, w1, w2 = -12, 12, -6, 26
    room(v, u1, w1, u2, w2, 0, 8)
    door(v, 0, 1, w1, "north")
    # pasillo de trampas: muros interiores dejan un corredor de 3 de ancho
    v.fill(-2, 1, w1 + 1, -2, 7, w1 + 12, BRICK)
    v.fill(2, 1, w1 + 1, 2, 7, w1 + 12, BRICK)
    v.fill(u1 + 1, 1, w1 + 1, -3, 7, w1 + 12, BRICK)                       # macizo a los lados del corredor
    v.fill(3, 1, w1 + 1, u2 - 1, 7, w1 + 12, BRICK)
    for k, w in enumerate(range(w1 + 3, w1 + 12, 2)):
        if k % 2 == 0:                                                        # filas pares: trampas a los lados, centro seguro
            R.arrow_trap(v, 1, 1, w, "east")
            (R.water_trap if k == 2 else R.arrow_trap)(v, -1, 1, w, "west")
        else:                                                                 # impares: dispensador bajo la baldosa central
            C.dispenser(v, 0, 0, w, "up", "arrow", 24)
            v.set(0, 1, w, "stone_pressure_plate[powered=false]")
            v.mark("trampa", 0, 1, w)
    v.set(0, 7, w1 + 6, LANTERN)
    # armería
    aw = w1 + 13
    for u in range(u1 + 2, u2 - 1, 3):
        if abs(u) > 2:
            v.entity(u, 1, w2 - 2, {"id": "minecraft:armor_stand", "equipment": {"head": {"id": "minecraft:chainmail_helmet", "count": 1},
                                                                           "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}}})
    for u in (u1 + 1, u2 - 1):
        v.set(u, 7, aw, LANTERN)
        v.set(u, 7, w2 - 1, LANTERN)
    R.cofre_bomba(v, 0, 1, w2 - 1, "north", "menor")
    C.cofre(v, u1 + 1, 1, aw + 4, "east", "media")
    v.entity(-4, 1, aw + 5, C.drowned(True))
    v.entity(4, 1, aw + 5, C.drowned(True))
    C.generator(v, u2 - 1, 1, aw + 1, "drowned", trident=True)
    v.mark("seca", 0, 1, aw + 3)
    # cámara del sello: al este de la armería, tras una puerta de hierro que abre una palanca escondida tras un tapiz
    cu1, cu2 = u2, u2 + 9
    room(v, cu1, aw + 2, cu2, aw + 10, 0, 5)
    v.set(cu1, 1, aw + 6, "iron_door[facing=west,half=lower,hinge=left,open=false,powered=false]")
    v.set(cu1, 2, aw + 6, "iron_door[facing=west,half=upper,hinge=left,open=false,powered=false]")
    v.set(cu1, 2, aw + 5, BRICK)
    v.set(cu1 - 1, 2, aw + 5, "lever[face=wall,facing=west,powered=false]")   # acciona el bloque contiguo a la puerta
    v.set(cu1 - 1, 3, aw + 5, "cyan_wall_banner[facing=west]", {"id": "minecraft:banner"})
    v.set(cu2 - 1, 4, aw + 3, LANTERN)
    C.cofre(v, cu2 - 1, 1, aw + 6, "west", "sello_arsenal")
    C.sign(v, cu2 - 1, 2, aw + 8, "west", clue(1, "I: alzada", "I: raised"))
    v.mark("seca", cu1 + 3, 1, aw + 6)
    v.mark("camara_arsenal", cu1 + 2, 1, aw + 6)
    E.ornament(v, u1, w1, u2, w2, 0, 8)
    v.mark("palanca_arsenal", cu1 - 1, 2, aw + 5)
    v.mark("toque_arsenal", cu1, 3, aw + 6)
    v.mark("puerta_arsenal", cu1, 2, aw + 6)


# ------------------------------------------------------------------ SO: jardines de coral
def gardens(v):
    v.site("jardines", -46, 0, -46, 46, 20, 46, ruinous=True)
    for k, (cu, cw, r) in enumerate(((0, 0, 14), (-28, -24, 10), (26, -26, 9), (-26, 26, 9), (28, 24, 10))):
        v.disk(cu, cw, r, 0, 0, "sand")
        v.disk(cu, cw, r, 0, 1, BRICK, cavity=r - 1)
        for u in range(cu - r, cu + r + 1):                                  # cúpula rota: faltan gajos
            for w in range(cw - r, cw + r + 1):
                for y in range(0, r + 1):
                    d = math.sqrt((u - cu) ** 2 + (w - cw) ** 2 + y * y)
                    if r - 1 < d <= r:
                        segment = int((math.atan2(w - cw, u - cu) + math.pi) * 6 / math.pi)
                        if h(segment, k, 31) % 3 == 0 or y > r * 0.7 and h(u, w, 32) % 2:
                            continue
                        v.set(u, 1 + y, w, DARK if (u == cu or w == cw or abs(u - cu) == abs(w - cw)) else GLASS)
        for u in range(cu - r + 2, cu + r - 1):
            for w in range(cw - r + 2, cw + r - 1):
                if (u - cu) ** 2 + (w - cw) ** 2 > (r - 2) ** 2:
                    continue
                q = h(u + v.ox, w + v.oz, 33) % 30
                if q < 5:
                    height = 1 + h(u, w, 34) % 3
                    v.fill(u, 1, w, u, height, w, CORALS[(q + k) % 5])
                    v.set(u, height + 1, w, f"{CORALS[(q + k) % 5].replace('_block', '')}[waterlogged=true]")
                elif q < 9:
                    height = 3 + q
                    v.fill(u, 1, w, u, height - 1, w, "kelp_plant")
                    v.set(u, height, w, "kelp[age=25]")
                elif q < 12:
                    v.set(u, 1, w, "sea_pickle[pickles=4,waterlogged=true]")
                elif q < 16:
                    v.set(u, 1, w, "seagrass")
        v.set(cu, 1, cw, LANTERN)
        v.entity(cu + 2, 4, cw + 2, C.guardian())
        if k:
            v.set(cu + r - 3, 1, cw, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLE + "menor"})
            v.mark("cofre", cu + r - 3, 1, cw)
    # invernadero intacto y seco, al fondo: se entra buceando por debajo
    gu, gw = 0, 34
    v.disk(gu, gw, 7, 0, 0, DARK)
    v.disk(gu, gw, 7, 1, 5, BRICK, cavity=6)
    v.disk(gu, gw, 6, 5, 5, DARK)
    v.remove(gu, 1, gw - 7, gu, 2, gw - 7)
    v.dome(gu, gw, 7, 5, GLASS, rib=DARK)
    for u in range(gu - 6, gu + 7):
        for w in range(gw - 6, gw + 7):
            for y in range(1, 7):
                if math.sqrt((u - gu) ** 2 + (w - gw) ** 2 + y * y) <= 6:
                    v.air(u, 5 + y, w, u, 5 + y, w)
    v.fill(gu, 5, gw - 3, gu + 1, 5, gw - 2, "water")
    for u, w in ((-3, 2), (3, 2), (-2, 4), (2, 4)):
        v.set(gu + u, 6, gw + w, "moss_block")
        v.set(gu + u, 7, gw + w, "flowering_azalea_leaves[persistent=true]")
    C.cofre(v, gu, 6, gw + 4, "north", "media")
    v.mark("seca", gu, 6, gw)
    v.mark("agua", gu, 5, gw - 3)
    C.generator(v, -12, 1, 12, "guardian")
    C.generator(v, 12, 1, -12, "guardian")


# ------------------------------------------------------------------ NO: anfiteatro
def amphitheater(v):
    R0, R1 = 13, 40
    v.site("anfiteatro", -R1, 0, -R1, R1, 16, R1)
    for u in range(-R1, R1 + 1):
        for w in range(-R1, R1 + 1):
            d = math.hypot(u, w)
            if d > R1 + 0.3:
                continue
            vomitorio = (abs(u) <= 2 or abs(w) <= 2)
            if d <= R0:
                v.set(u, 0, w, "sand" if d < R0 - 1 else DARK)
            else:
                tier = min(12, 1 + int((d - R0) / 2))
                broken = h(u >> 1, w >> 1, 41) % 100 < 8 and tier > 3
                if vomitorio and tier <= 8:
                    v.set(u, 0, w, DARK)
                    continue
                height = tier - (2 if broken else 0)
                v.fill(u, 0, w, u, height, w, BRICK if (int(d) % 2) else PRISMARINE)
                if int(d - R0) % 2 == 0 and not broken and d < R1 - 1:
                    v.set(u, height, w, DARK)
    for u in range(-2, 3):                                                   # dinteles de los vomitorios
        for w in range(-R1, R1 + 1):
            for (a, b) in ((u, w), (w, u)):
                d = math.hypot(a, b)
                if R0 + 14 < d <= R1 and v.built(a, 5, b) is None:
                    tier = min(12, 1 + int((d - R0) / 2))
                    v.fill(a, 5, b, a, tier, b, BRICK)
    # arena: tarima central con el cofre del sello, generadores bajo rejas y guardián anciano
    v.disk(-5, -5, 3, 1, 1, QUARTZ)                                         # tarima (descentrada: en el centro está el pozo)
    C.cofre(v, -5, 2, -5, "north", "sello_anfiteatro")
    v.set(-4, 2, -5, QUARTZ)
    C.sign(v, -4, 2, -6, "north", clue(3, "III: alzada", "III: raised"))
    for k in range(6):
        a = k * math.pi / 3 + 0.5
        gu, gw = round(9 * math.cos(a)), round(9 * math.sin(a))
        C.generator(v, gu, 0, gw, "drowned" if k % 2 else "guardian", trident=True)
        v.set(gu, 1, gw, "iron_bars")
    v.entity(0, 8, 0, C.elder())
    for u, w in ((6, 6), (-6, 6), (6, -6), (-6, -6)):
        v.entity(u, 2, w, C.drowned(True))
    for k in range(8):
        a = k * math.pi / 4
        column(v, round((R0 + 1) * math.cos(a + 0.39)), round((R0 + 1) * math.sin(a + 0.39)), 1, 5)
    v.mark("arena", 0, 2, 2)


# ------------------------------------------------------------------ NE: lonja de los artesanos
def artisans(v):
    u1, u2, w1, w2 = -17, 17, -9, 9
    v.site("lonja", u1, -6, w1, u2, 12, w2)
    room(v, u1, w1, u2, w2, 0, 8)
    P.double_door(v.set, -1, 1, w1, "north", "east", E.PUERTA)
    for u in range(u1 + 3, u2 - 2, 6):
        v.fill(u, 3, w1, u + 1, 5, w1, GLASS) if abs(u) > 3 else None
        v.fill(u, 3, w2, u + 1, 5, w2, GLASS)
    stalls = ["blast_furnace[facing=north,lit=false]", "anvil[facing=north]", "smithing_table", "stonecutter[facing=north]", "loom[facing=north]",
               "cartography_table", "fletching_table", "grindstone[face=floor,facing=north]", "crafting_table", "barrel[facing=up]"]
    for k, u in enumerate(range(u1 + 2, u2 - 1, 3)):
        st = stalls[k % len(stalls)]
        nbt = {"id": "minecraft:" + st.split("[")[0]} if st.split("[")[0] in ("blast_furnace", "barrel") else None
        v.set(u, 1, w2 - 1, st, nbt)
    for u in (u1 + 1, u2 - 1):
        for w in (w1 + 1, w2 - 1):
            v.set(u, 7, w, LANTERN)
    v.set(0, 8, 0, LANTERN)
    E.ornament(v, u1, w1, u2, w2, 0, 8)
    v.fill(-4, 1, 0, 4, 1, 0, "warped_slab[type=top]")                      # mesa larga
    C.cofre(v, u1 + 1, 1, 0, "east", "media")
    v.mark("seca", 0, 1, -4)
    # sala oculta: sótano bajo una trampilla tapada por la alfombra, en la esquina
    tu, tw = u2 - 2, w1 + 2
    room(v, tu - 4, tw - 2, tu + 1, tw + 3, -5, -1)
    v.set(tu, 0, tw, "warped_trapdoor[facing=north,half=top,open=false]")
    v.set(tu, 1, tw, "cyan_carpet")
    for y in range(-4, 0):
        v.set(tu, y, tw, "ladder[facing=west]")
    v.set(tu + 1, -1, tw, BRICK)
    v.set(tu - 3, -2, tw - 1, LANTERN)
    C.cofre(v, tu - 3, -4, tw + 2, "north", "tesoro")
    v.mark("seca", tu - 2, -4, tw)
    v.mark("oculta", tu - 2, -4, tw)
    v.entity(6, 1, 4, C.drowned())


DISTRICTS = {"agora": agora, "termas": baths, "puerto": harbor, "academia": academy, "arsenal": arsenal,
             "jardines": gardens, "anfiteatro": amphitheater, "artesanos": artisans}
