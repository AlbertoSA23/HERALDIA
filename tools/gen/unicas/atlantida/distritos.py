"""Distritos singulares de la Atlántida. Cada función recibe una Vista centrada en el distrito cuyo «norte» local
(v negativo) mira al centro de la ciudad; y = 0 es el pavimento."""
import math
from . import urbanismo as U
from . import cosas as C
from . import edificios as E
from . import redstone as R
from .._comun import piezas as P
from .edificios import LADRILLO, OSCURA, PRISMARINA, LINTERNA, CRISTAL, CUARZO, PILAR, CORALES, h, puerta, columna

COMBINACION_CENTRAL = [True, False, True, True]         # palancas del vestíbulo del templo: I, III y IV alzadas
COMBINACION_ACADEMIA = [False, True, True, False]


def sala(v, u1, v1, u2, v2, y1, y2, muro=LADRILLO, suelo=OSCURA, techo=OSCURA):
    """Sala seca: caja con aire dentro. y1 = suelo, y2 = techo."""
    v.shell(u1, y1, v1, u2, y2, v2, muro, floor=suelo, roof=techo)
    v.air(u1 + 1, y1 + 1, v1 + 1, u2 - 1, y2 - 1, v2 - 1)


def pista(n, es, en):
    """Cartel con una cifra de la combinación del templo."""
    return [C.texto("pista.titulo", "Sello del templo", "Seal of the temple", bold=C.B(1)),
            C.texto(f"pista.{n}", es, en)]


# ------------------------------------------------------------------ N: ágora
def agora(v):
    A, F = 44, 38                                   # semiancho y semifondo de la plaza porticada
    v.sitio("agora", -A, 0, -F, A, 12, F)
    for u in range(-A, A + 1):
        for w in range(-F, F + 1):
            borde = max(abs(u) - (A - 4), abs(w) - (F - 4))
            if abs(u) <= U.AVENIDA:
                continue                            # la avenida cruza la plaza
            if borde >= 0:
                v.set(u, 0, w, LADRILLO)
                v.set(u, 7, w, OSCURA if borde in (0, 4) else LADRILLO)       # arquitrabe del pórtico
                if borde == 0 and (u % 4 == 0 and abs(w) <= F - 4 or w % 4 == 0 and abs(u) <= A - 4):
                    columna(v, u, w, 1, 6)
                if borde == 4:
                    if (u + w) % 6 == 0:
                        v.set(u, 6, w, LINTERNA)
            else:
                v.set(u, 0, w, OSCURA if (u // 2 + w // 2) % 2 else PRISMARINA)
    for lado in (-1, 1):                            # estatuas del tridente a cada lado de la avenida
        cu = lado * 22
        v.fill(cu - 2, 1, -2, cu + 2, 1, 2, CUARZO)
        v.fill(cu - 1, 2, -1, cu + 1, 2, 1, CUARZO)
        v.fill(cu, 3, 0, cu, 9, 0, "waxed_oxidized_cut_copper")
        for du in (-2, 2):
            v.fill(cu + du, 8, 0, cu + du, 11, 0, "waxed_oxidized_cut_copper")
        v.fill(cu - 2, 8, 0, cu + 2, 8, 0, "waxed_oxidized_cut_copper")
        v.fill(cu, 10, 0, cu, 12, 0, "waxed_oxidized_cut_copper")
        v.set(cu, 2, -2, LINTERNA)
        v.set(cu, 2, 2, LINTERNA)
    # casa del consejo (seca), al fondo este de la plaza, con puerta a la plaza
    u1, u2, w1, w2 = 14, 34, 12, 28
    sala(v, u1, w1, u2, w2, 0, 7)
    puerta(v, (u1 + u2) // 2, 1, w1, "north")
    for u in range(u1 + 2, u2 - 1):                 # graderío de tres filas al fondo
        for fila in range(3):
            v.set(u, 1 + fila, w2 - 1 - (2 - fila), "prismarine_brick_stairs[facing=south,half=bottom]")
            for y in range(1, 1 + fila):
                v.set(u, y, w2 - 1 - (2 - fila), LADRILLO)
    for u in (u1 + 1, u2 - 1):
        v.set(u, 6, w1 + 1, LINTERNA)
        v.set(u, 6, w2 - 1, LINTERNA)
    C.cartel(v, u1 + 4, 2, w1 + 1, "south", [C.texto("agora.1", "Tres sellos guardan", "Three seals guard"),
                                             C.texto("agora.2", "el paso al templo:", "the way to the temple:"),
                                             C.texto("agora.3", "arsenal, academia", "arsenal, academy"),
                                             C.texto("agora.4", "y anfiteatro.", "and amphitheatre.")])
    C.cartel(v, u2 - 4, 2, w1 + 1, "south", [C.texto("agora.5", "Sus llaves abren", "Their keys open"),
                                             C.texto("agora.6", "las arcas del templo.", "the temple coffers."),
                                             C.texto("agora.7", "La de Poseidón", "The Key of Poseidon"),
                                             C.texto("agora.8", "la guarda su guardián.", "lies with his warden.")])
    C.cofre(v, u1 + 1, 1, w1 + 4, "east", "media")
    v.set(u2 - 1, 1, w1 + 4, "lectern[facing=west]", {"id": "minecraft:lectern"})
    v.marca("seca", u1 + 3, 1, w1 + 3)
    E.ventanas(v, u1, "w", w1, w2, 3, 4)
    E.ventanas(v, u2, "w", w1, w2, 3, 4)
    E.ornamentar(v, u1, w1, u2, w2, 0, 7, paso=5)
    # mercado en ruinas (inundado), al fondo oeste
    for k in range(4):
        cu, cw = -18 - (k % 2) * 10, 14 + (k // 2) * 10
        v.fill(cu - 2, 1, cw - 2, cu + 2, 1, cw - 2, "stripped_warped_stem[axis=x]")
        for du in (-2, 2):
            v.fill(cu + du, 1, cw - 1, cu + du, 3, cw - 1, "warped_fence")
        v.fill(cu - 2, 4, cw - 2, cu + 2, 4, cw, "warped_slab[type=bottom]") if k != 2 else None
        v.set(cu, 1, cw, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLA + "menor"})
        v.marca("cofre", cu, 1, cw)
    v.entity(-10, 2, -10, C.guardian())
    v.entity(10, 2, -14, C.guardian())
    v.entity(-24, 2, 6, C.ahogado())


# ------------------------------------------------------------------ E: termas
def ex_de(lado, u1, u2):
    return u2 - 2 if lado == 1 else u1 + 2


def termas(v):
    v.sitio("termas", -36, 0, -30, 36, 22, 30)
    # tres naves paralelas a la avenida, a cada lado: frigidario (inundado, cúpula), tepidario (seco) y caldario (magma)
    for lado in (-1, 1):
        u1, u2 = (10, 34) if lado == 1 else (-34, -10)
        # frigidario: gran sala inundada con cúpula de cristal
        v.shell(u1, 0, -28, u2, 9, -8, LADRILLO, floor=OSCURA, roof=OSCURA)
        cu, cw = (u1 + u2) // 2, -18
        v.quitar(cu - 6, 9, cw - 6, cu + 6, 9, cw + 6)
        v.cupula(cu, cw, 8, 9, CRISTAL, nervio=OSCURA)
        v.disco(cu, cw, 8, 9, 9, OSCURA, hueco=7)
        v.quitar(u1 if lado == 1 else u2, 1, cw - 1, u1 if lado == 1 else u2, 3, cw + 1)        # portal a la avenida
        v.fill(cu - 4, 0, cw - 4, cu + 4, 0, cw + 4, PRISMARINA)
        v.disco(cu, cw, 3, 0, 0, LINTERNA, hueco=2)
        for du, dw in ((-9, -8), (9, -8), (-9, 8), (9, 8)):
            columna(v, cu + du, cw + dw, 1, 8)
        # tepidario: sala seca con bancos
        sala(v, u1, -8, u2, 8, 0, 7)
        puerta(v, cu, 1, -8, "north")
        for u in range(u1 + 2, u2 - 1, 2):
            v.set(u, 1, -6, "prismarine_brick_stairs[facing=north,half=bottom]")
            v.set(u, 1, 6, "prismarine_brick_stairs[facing=south,half=bottom]")
        v.set(u1 + 1, 6, -7, LINTERNA)
        v.set(u2 - 1, 6, 7, LINTERNA)
        v.set(u1 + 1, 6, 7, LINTERNA)
        v.set(u2 - 1, 6, -7, LINTERNA)
        v.marca("seca", cu, 1, 0)
        puerta(v, cu, 1, 8, "south")
        # caldario: sala inundada con suelo de magma (arrastra al fondo) y un ascensor de burbujas a la galería alta
        v.shell(u1, 0, 8, u2, 16, 28, LADRILLO, floor=OSCURA, roof=OSCURA)
        puerta(v, cu, 1, 8, "south")
        for u in range(u1 + 3, u2 - 2):
            for w in range(12, 26):
                if (u + w) % 3 == 0 and abs(u - ex_de(lado, u1, u2)) > 2:
                    v.set(u, 0, w, "magma_block")
                    v.fill(u, 1, w, u, 8, w, "bubble_column[drag=true]")
        v.fill(u1 + 1, 9, 9, u2 - 1, 9, 27, OSCURA)                                          # forjado de la galería
        v.fill(u1 + 1, 10, 9, u2 - 1, 15, 27, "air")
        ex = u2 - 2 if lado == 1 else u1 + 2                                                 # ascensor: columna de arena de almas
        v.set(ex, 0, 26, "soul_sand")
        v.fill(ex - 1, 1, 25, ex + 1, 8, 27, CRISTAL)
        v.fill(ex, 1, 26, ex, 9, 26, "bubble_column[drag=false]")           # explícita: en la generación no hay actualizaciones
        v.quitar(ex, 1, 25, ex, 2, 25)
        v.set(u1 + 1, 15, 9, LINTERNA)
        v.set(u2 - 1, 15, 27, LINTERNA)
        C.cofre(v, cu, 10, 10, "south", "media")
        if lado == 1:
            C.cartel(v, cu + 2, 11, 9, "south", pista(4, "IV: alzada", "IV: raised"))
        v.marca("seca", cu, 10, 18)
        v.marca("burbuja", ex, 9, 26)
        v.entity(cu, 4, 18, C.guardian())
        C.generador(v, u1 + 1 if lado == 1 else u2 - 1, 1, 27, "guardian")
        fondo = u2 if lado == 1 else u1
        E.ventanas(v, fondo, "w", -8, 8, 3, 4)
        E.ventanas(v, fondo, "w", 8, 28, 11, 13)
        E.ornamentar(v, u1, -28, u2, -8, 0, 9)
        E.ornamentar(v, u1, -8, u2, 8, 0, 7, peto=False)
        E.ornamentar(v, u1, 8, u2, 28, 0, 16)
    v.entity(0, 4, -18, C.guardian())
    v.entity(0, 4, 18, C.guardian())


# ------------------------------------------------------------------ S: puerto hundido
def barco(v, cu, cw, largo, sal, madera="spruce"):
    """Casco hundido y escorado, con la bodega abierta."""
    for i in range(largo):
        ancho = 3 if 2 <= i < largo - 3 else 2 if 1 <= i < largo - 1 else 1
        w = cw + i
        for du in range(-ancho, ancho + 1):
            v.set(cu + du, 1, w, f"{madera}_planks")
            if abs(du) == ancho and h(cu + du, w, sal) % 6:
                v.fill(cu + du, 2, w, cu + du, 3 if h(cu + du, w, sal + 1) % 3 else 2, w, f"{madera}_planks")
        if i in (largo // 3, 2 * largo // 3):
            alto = 4 + h(i, sal, 2) % 5
            v.fill(cu, 2, w, cu, alto, w, f"stripped_{madera}_log[axis=y]")
    v.fill(cu - 1, 2, cw + largo - 4, cu + 1, 2, cw + largo - 2, f"{madera}_slab[type=top]")
    v.set(cu, 2, cw + largo // 2, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLA + ("media" if sal % 2 else "menor")})
    v.marca("cofre", cu, 2, cw + largo // 2)
    v.sitio("barco", cu - 4, 1, cw, cu + 4, 9, cw + largo, ruinoso=True)


def puerto(v):
    v.sitio("puerto", -46, 0, -36, 46, 14, 36, ruinoso=True)
    for lado in (-1, 1):
        for u in range(10, 46):
            for w in range(-36, 37):
                uu = lado * u
                muelle = u < 16 or abs(w) > 30 or abs(w) < 3
                if muelle:
                    roto = h(uu, w, 21) % 9 == 0
                    v.fill(uu, 0, w, uu, 2 if not roto else 1, w, LADRILLO if (u + w) % 5 else OSCURA)
                    if u == 10 and w % 6 == 0 and not roto:
                        v.fill(uu, 3, w, uu, 4, w, "dark_oak_fence")
                        v.set(uu, 5, w, "sea_lantern")
                else:
                    v.set(uu, 0, w, "sand" if h(uu, w, 22) % 4 else "gravel")
                    r = h(uu, w, 23) % 60
                    if r < 3:
                        alto = 2 + r * 2
                        v.fill(uu, 1, w, uu, alto - 1, w, "kelp_plant")
                        v.set(uu, alto, w, "kelp[age=25]")
                    elif r < 6:
                        v.set(uu, 1, w, "seagrass")
        barco(v, lado * 24, -26, 20, 30 + lado)
        barco(v, lado * 36, 6, 22, 40 + lado, madera="dark_oak")
    # faro derruido al fondo
    for k, (cu, cw) in enumerate(((-30, 0), (30, 0))):
        v.disco(cu, cw, 4, 3, 5 + (h(cu, cw, 24) % 4), LADRILLO, hueco=3)
        v.set(cu, 3, cw, "chest[facing=north]", {"id": "minecraft:chest", "LootTable": C.TABLA + "media"})
        v.marca("cofre", cu, 3, cw)
    for u, w, elite in ((-20, -10, True), (20, -10, True), (-34, 20, False), (34, 20, False), (-24, 30, False), (24, 30, True), (0, 20, True)):
        v.entity(u, 3, w, C.ahogado(elite))
    for u, w in ((-28, -20), (28, 12)):
        C.generador(v, u, 2, w, "drowned", tridente=True)


# ------------------------------------------------------------------ O: academia
def academia(v):
    v.sitio("academia", -42, 0, -30, 42, 16, 38)
    for lado in (-1, 1):
        s = lado
        u1, u2 = (10, 40) if lado == 1 else (-40, -10)
        ua, ub = (u1, u2)
        # ala: vestíbulo + biblioteca, toda seca; puerta doble a la avenida
        sala(v, ua, -26, ub, 26, 0, 9)
        frente = u1 if lado == 1 else u2
        P.double_door(v.set, frente, 1, -1, "west" if lado == 1 else "east", "south", E.PUERTA)
        for w in (-22, -14, -6, 6, 14, 22):                                   # ventanales
            fondo = u2 if lado == 1 else u1
            v.fill(fondo, 3, w - 1, fondo, 6, w + 1, CRISTAL)
        for w in range(-24, 25, 6):                                           # estanterías en espina
            if abs(w) < 4:
                continue
            for u in range(min(ua, ub) + 4, max(ua, ub) - 3):
                if (u - ua) % 9 in (4, 5) or abs(u - (ua + ub) // 2) < 2:
                    continue
                v.fill(u, 1, w, u, 3, w, "bookshelf")
        for u in (ua + 1, ub - 1):
            for w in (-25, 25):
                v.set(u, 8, w, LINTERNA)
        for w in (-12, 12):
            v.set((ua + ub) // 2, 9, w, LINTERNA)
        v.set((ua + ub) // 2, 1, -24, "lectern[facing=south]", {"id": "minecraft:lectern"})
        v.set((ua + ub) // 2, 1, 24, "lectern[facing=north]", {"id": "minecraft:lectern"})
        v.marca("seca", (ua + ub) // 2, 1, 0)
        E.ornamentar(v, ua, -26, ub, 26, 0, 9)
        v.entity((ua + ub) // 2, 1, 10, C.ahogado(lado == 1))
        if lado == 1:
            C.generador(v, ua + 2, 1, 20, "drowned", tridente=False)
            C.cofre(v, ub - 1, 1, 20, "west", "media")
    # ala norte (lado 1, hacia v negativo): las cuatro pistas de la combinación, repartidas tras las estanterías
    pistas = [("academia.p1", "La primera, suelta", "The first, released"), ("academia.p2", "La segunda, alzada", "The second, raised"),
              ("academia.p3", "La tercera, alzada", "The third, raised"), ("academia.p4", "La cuarta, suelta", "The fourth, released")]
    for (clave, es, en), (u, w, mira) in zip(pistas, ((39, -20, "west"), (-39, -20, "east"), (39, 20, "west"), (-39, 20, "east"))):
        C.cartel(v, u, 2, w, mira, [C.texto(clave, es, en)])
    # cámara del sello: tras la puerta de combinación, en el testero sur del ala este
    u0 = 14
    fin = R.combinacion(v, u0, 2, 26, COMBINACION_ACADEMIA, "academia")
    sala(v, u0 - 2, 29, u0 + 12, 37, 0, 5)
    v.air(fin[0], 1, 29, fin[0], 2, 29)
    v.set(u0 - 1, 4, 30, LINTERNA)
    C.cofre(v, u0 + 4, 1, 36, "north", "sello_academia")
    C.cartel(v, u0 + 6, 2, 36, "north", pista(2, "II: suelta", "II: released"))
    v.marca("seca", u0 + 5, 1, 33)
    v.marca("camara_academia", fin[0], 1, 31)


# ------------------------------------------------------------------ SE: arsenal
def arsenal(v):
    L = 34
    v.sitio("arsenal", -L, 0, -L, L, 20, L)
    # recinto amurallado con torres en las esquinas y patio inundado
    for u in range(-L, L + 1):
        for w in range(-L, L + 1):
            if max(abs(u), abs(w)) >= L - 2:
                v.fill(u, 0, w, u, 9, w, LADRILLO)
                if max(abs(u), abs(w)) == L and (u + w) % 2 == 0:
                    v.set(u, 10, w, OSCURA)
            else:
                v.set(u, 0, w, OSCURA if (u + w) % 2 else LADRILLO)
    for su in (-1, 1):
        for sw in (-1, 1):
            v.disco(su * (L - 2), sw * (L - 2), 5, 0, 13, LADRILLO)
            v.disco(su * (L - 2), sw * (L - 2), 5, 14, 14, OSCURA)
            v.set(su * (L - 2), 15, sw * (L - 2), LINTERNA)
    v.quitar(-2, 1, -L, 2, 5, -L + 2)                                        # puerta del recinto (al norte local)
    v.entity(0, 5, -16, C.anciano())
    for u, w in ((-20, -20), (20, -20), (-22, 10), (22, 10)):
        v.entity(u, 3, w, C.guardian())
    C.generador(v, -L + 4, 1, 0, "guardian")
    C.generador(v, L - 4, 1, 0, "guardian")
    # torre del homenaje (seca): puerta -> pasillo de trampas -> armería -> cámara del sello tras una palanca oculta
    u1, u2, w1, w2 = -12, 12, -6, 26
    sala(v, u1, w1, u2, w2, 0, 8)
    puerta(v, 0, 1, w1, "north")
    # pasillo de trampas: muros interiores dejan un corredor de 3 de ancho
    v.fill(-2, 1, w1 + 1, -2, 7, w1 + 12, LADRILLO)
    v.fill(2, 1, w1 + 1, 2, 7, w1 + 12, LADRILLO)
    v.fill(u1 + 1, 1, w1 + 1, -3, 7, w1 + 12, LADRILLO)                       # macizo a los lados del corredor
    v.fill(3, 1, w1 + 1, u2 - 1, 7, w1 + 12, LADRILLO)
    for k, w in enumerate(range(w1 + 3, w1 + 12, 2)):
        if k % 2 == 0:                                                        # filas pares: trampas a los lados, centro seguro
            R.trampa_flechas(v, 1, 1, w, "east")
            (R.trampa_agua if k == 2 else R.trampa_flechas)(v, -1, 1, w, "west")
        else:                                                                 # impares: dispensador bajo la baldosa central
            C.dispensador(v, 0, 0, w, "up", "arrow", 24)
            v.set(0, 1, w, "stone_pressure_plate[powered=false]")
            v.marca("trampa", 0, 1, w)
    v.set(0, 7, w1 + 6, LINTERNA)
    # armería
    aw = w1 + 13
    for u in range(u1 + 2, u2 - 1, 3):
        if abs(u) > 2:
            v.entity(u, 1, w2 - 2, {"id": "minecraft:armor_stand", "equipment": {"head": {"id": "minecraft:chainmail_helmet", "count": 1},
                                                                           "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}}})
    for u in (u1 + 1, u2 - 1):
        v.set(u, 7, aw, LINTERNA)
        v.set(u, 7, w2 - 1, LINTERNA)
    R.cofre_bomba(v, 0, 1, w2 - 1, "north", "menor")
    C.cofre(v, u1 + 1, 1, aw + 4, "east", "media")
    v.entity(-4, 1, aw + 5, C.ahogado(True))
    v.entity(4, 1, aw + 5, C.ahogado(True))
    C.generador(v, u2 - 1, 1, aw + 1, "drowned", tridente=True)
    v.marca("seca", 0, 1, aw + 3)
    # cámara del sello: al este de la armería, tras una puerta de hierro que abre una palanca escondida tras un tapiz
    cu1, cu2 = u2, u2 + 9
    sala(v, cu1, aw + 2, cu2, aw + 10, 0, 5)
    v.set(cu1, 1, aw + 6, "iron_door[facing=west,half=lower,hinge=left,open=false,powered=false]")
    v.set(cu1, 2, aw + 6, "iron_door[facing=west,half=upper,hinge=left,open=false,powered=false]")
    v.set(cu1, 2, aw + 5, LADRILLO)
    v.set(cu1 - 1, 2, aw + 5, "lever[face=wall,facing=west,powered=false]")   # acciona el bloque contiguo a la puerta
    v.set(cu1 - 1, 3, aw + 5, "cyan_wall_banner[facing=west]", {"id": "minecraft:banner"})
    v.set(cu2 - 1, 4, aw + 3, LINTERNA)
    C.cofre(v, cu2 - 1, 1, aw + 6, "west", "sello_arsenal")
    C.cartel(v, cu2 - 1, 2, aw + 8, "west", pista(1, "I: alzada", "I: raised"))
    v.marca("seca", cu1 + 3, 1, aw + 6)
    v.marca("camara_arsenal", cu1 + 2, 1, aw + 6)
    E.ornamentar(v, u1, w1, u2, w2, 0, 8)
    v.marca("palanca_arsenal", cu1 - 1, 2, aw + 5)
    v.marca("toque_arsenal", cu1, 3, aw + 6)
    v.marca("puerta_arsenal", cu1, 2, aw + 6)


# ------------------------------------------------------------------ SO: jardines de coral
def jardines(v):
    v.sitio("jardines", -46, 0, -46, 46, 20, 46, ruinoso=True)
    for k, (cu, cw, r) in enumerate(((0, 0, 14), (-28, -24, 10), (26, -26, 9), (-26, 26, 9), (28, 24, 10))):
        v.disco(cu, cw, r, 0, 0, "sand")
        v.disco(cu, cw, r, 0, 1, LADRILLO, hueco=r - 1)
        for u in range(cu - r, cu + r + 1):                                  # cúpula rota: faltan gajos
            for w in range(cw - r, cw + r + 1):
                for y in range(0, r + 1):
                    d = math.sqrt((u - cu) ** 2 + (w - cw) ** 2 + y * y)
                    if r - 1 < d <= r:
                        gajo = int((math.atan2(w - cw, u - cu) + math.pi) * 6 / math.pi)
                        if h(gajo, k, 31) % 3 == 0 or y > r * 0.7 and h(u, w, 32) % 2:
                            continue
                        v.set(u, 1 + y, w, OSCURA if (u == cu or w == cw or abs(u - cu) == abs(w - cw)) else CRISTAL)
        for u in range(cu - r + 2, cu + r - 1):
            for w in range(cw - r + 2, cw + r - 1):
                if (u - cu) ** 2 + (w - cw) ** 2 > (r - 2) ** 2:
                    continue
                q = h(u + v.ox, w + v.oz, 33) % 30
                if q < 5:
                    alto = 1 + h(u, w, 34) % 3
                    v.fill(u, 1, w, u, alto, w, CORALES[(q + k) % 5])
                    v.set(u, alto + 1, w, f"{CORALES[(q + k) % 5].replace('_block', '')}[waterlogged=true]")
                elif q < 9:
                    alto = 3 + q
                    v.fill(u, 1, w, u, alto - 1, w, "kelp_plant")
                    v.set(u, alto, w, "kelp[age=25]")
                elif q < 12:
                    v.set(u, 1, w, "sea_pickle[pickles=4,waterlogged=true]")
                elif q < 16:
                    v.set(u, 1, w, "seagrass")
        v.set(cu, 1, cw, LINTERNA)
        v.entity(cu + 2, 4, cw + 2, C.guardian())
        if k:
            v.set(cu + r - 3, 1, cw, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": C.TABLA + "menor"})
            v.marca("cofre", cu + r - 3, 1, cw)
    # invernadero intacto y seco, al fondo: se entra buceando por debajo
    gu, gw = 0, 34
    v.disco(gu, gw, 7, 0, 0, OSCURA)
    v.disco(gu, gw, 7, 1, 5, LADRILLO, hueco=6)
    v.disco(gu, gw, 6, 5, 5, OSCURA)
    v.quitar(gu, 1, gw - 7, gu, 2, gw - 7)
    v.cupula(gu, gw, 7, 5, CRISTAL, nervio=OSCURA)
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
    v.marca("seca", gu, 6, gw)
    v.marca("agua", gu, 5, gw - 3)
    C.generador(v, -12, 1, 12, "guardian")
    C.generador(v, 12, 1, -12, "guardian")


# ------------------------------------------------------------------ NO: anfiteatro
def anfiteatro(v):
    R0, R1 = 13, 40
    v.sitio("anfiteatro", -R1, 0, -R1, R1, 16, R1)
    for u in range(-R1, R1 + 1):
        for w in range(-R1, R1 + 1):
            d = math.hypot(u, w)
            if d > R1 + 0.3:
                continue
            vomitorio = (abs(u) <= 2 or abs(w) <= 2)
            if d <= R0:
                v.set(u, 0, w, "sand" if d < R0 - 1 else OSCURA)
            else:
                grada = min(12, 1 + int((d - R0) / 2))
                roto = h(u >> 1, w >> 1, 41) % 100 < 8 and grada > 3
                if vomitorio and grada <= 8:
                    v.set(u, 0, w, OSCURA)
                    continue
                alto = grada - (2 if roto else 0)
                v.fill(u, 0, w, u, alto, w, LADRILLO if (int(d) % 2) else PRISMARINA)
                if int(d - R0) % 2 == 0 and not roto and d < R1 - 1:
                    v.set(u, alto, w, OSCURA)
    for u in range(-2, 3):                                                   # dinteles de los vomitorios
        for w in range(-R1, R1 + 1):
            for (a, b) in ((u, w), (w, u)):
                d = math.hypot(a, b)
                if R0 + 14 < d <= R1 and v.built(a, 5, b) is None:
                    grada = min(12, 1 + int((d - R0) / 2))
                    v.fill(a, 5, b, a, grada, b, LADRILLO)
    # arena: tarima central con el cofre del sello, generadores bajo rejas y guardián anciano
    v.disco(-5, -5, 3, 1, 1, CUARZO)                                         # tarima (descentrada: en el centro está el pozo)
    C.cofre(v, -5, 2, -5, "north", "sello_anfiteatro")
    v.set(-4, 2, -5, CUARZO)
    C.cartel(v, -4, 2, -6, "north", pista(3, "III: alzada", "III: raised"))
    for k in range(6):
        a = k * math.pi / 3 + 0.5
        gu, gw = round(9 * math.cos(a)), round(9 * math.sin(a))
        C.generador(v, gu, 0, gw, "drowned" if k % 2 else "guardian", tridente=True)
        v.set(gu, 1, gw, "iron_bars")
    v.entity(0, 8, 0, C.anciano())
    for u, w in ((6, 6), (-6, 6), (6, -6), (-6, -6)):
        v.entity(u, 2, w, C.ahogado(True))
    for k in range(8):
        a = k * math.pi / 4
        columna(v, round((R0 + 1) * math.cos(a + 0.39)), round((R0 + 1) * math.sin(a + 0.39)), 1, 5)
    v.marca("arena", 0, 2, 2)


# ------------------------------------------------------------------ NE: lonja de los artesanos
def artesanos(v):
    u1, u2, w1, w2 = -17, 17, -9, 9
    v.sitio("lonja", u1, -6, w1, u2, 12, w2)
    sala(v, u1, w1, u2, w2, 0, 8)
    P.double_door(v.set, -1, 1, w1, "north", "east", E.PUERTA)
    for u in range(u1 + 3, u2 - 2, 6):
        v.fill(u, 3, w1, u + 1, 5, w1, CRISTAL) if abs(u) > 3 else None
        v.fill(u, 3, w2, u + 1, 5, w2, CRISTAL)
    puestos = ["blast_furnace[facing=north,lit=false]", "anvil[facing=north]", "smithing_table", "stonecutter[facing=north]", "loom[facing=north]",
               "cartography_table", "fletching_table", "grindstone[face=floor,facing=north]", "crafting_table", "barrel[facing=up]"]
    for k, u in enumerate(range(u1 + 2, u2 - 1, 3)):
        st = puestos[k % len(puestos)]
        nbt = {"id": "minecraft:" + st.split("[")[0]} if st.split("[")[0] in ("blast_furnace", "barrel") else None
        v.set(u, 1, w2 - 1, st, nbt)
    for u in (u1 + 1, u2 - 1):
        for w in (w1 + 1, w2 - 1):
            v.set(u, 7, w, LINTERNA)
    v.set(0, 8, 0, LINTERNA)
    E.ornamentar(v, u1, w1, u2, w2, 0, 8)
    v.fill(-4, 1, 0, 4, 1, 0, "warped_slab[type=top]")                      # mesa larga
    C.cofre(v, u1 + 1, 1, 0, "east", "media")
    v.marca("seca", 0, 1, -4)
    # sala oculta: sótano bajo una trampilla tapada por la alfombra, en la esquina
    tu, tw = u2 - 2, w1 + 2
    sala(v, tu - 4, tw - 2, tu + 1, tw + 3, -5, -1)
    v.set(tu, 0, tw, "warped_trapdoor[facing=north,half=top,open=false]")
    v.set(tu, 1, tw, "cyan_carpet")
    for y in range(-4, 0):
        v.set(tu, y, tw, "ladder[facing=west]")
    v.set(tu + 1, -1, tw, LADRILLO)
    v.set(tu - 3, -2, tw - 1, LINTERNA)
    C.cofre(v, tu - 3, -4, tw + 2, "north", "tesoro")
    v.marca("seca", tu - 2, -4, tw)
    v.marca("oculta", tu - 2, -4, tw)
    v.entity(6, 1, 4, C.ahogado())


DISTRITOS = {"agora": agora, "termas": termas, "puerto": puerto, "academia": academia, "arsenal": arsenal,
             "jardines": jardines, "anfiteatro": anfiteatro, "artesanos": artesanos}
