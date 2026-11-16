"""Acrópolis (centro) y subsuelo: templo de Poseidón, vestíbulo, galerías de N-1 y cámaras de N-2.

Aquí se trabaja en coordenadas del plano con y absoluta (Vista con oy = 0 y sin giro).
"""
import math
from . import urbanismo as U
from . import cosas as C
from . import edificios as E
from . import redstone as R
from .edificios import LADRILLO, OSCURA, PRISMARINA, LINTERNA, CRISTAL, CUARZO, PILAR, puerta, columna, h
from .distritos import sala, COMBINACION_CENTRAL

S = U.SUELO
G0, G1 = 13, 18            # galerías de N-1: suelo y techo (interior 14..17)
ANILLO = 156               # las galerías forman un cuadrado de este semilado, más cuatro radiales bajo las avenidas
VESTIBULO = 10             # semilado interior del vestíbulo bajo el templo
TRAMO = 24                 # longitud de cada tramo (seco o inundado) entre puertas


def templo(v):
    """Basamento escalonado, columnata y cella con cúpula; en el centro, el pozo de cristal que baja al vestíbulo."""
    v.sitio("templo", -64, S, -64, 64, S + 27, 64)
    for k, r in enumerate((62, 54, 46)):                                    # tres gradas de 2 de alto
        y = S + 1 + 2 * k
        for u in range(-r, r + 1):
            for w in range(-r, r + 1):
                d = math.hypot(u, w)
                if d <= r + 0.3:
                    escalinata = min(abs(u), abs(w)) <= 4
                    if escalinata and d > r - 2.3 and k < 3:
                        # escalinata en los cuatro ejes: dos peldaños por grada
                        hacia = ("north" if w > 0 else "south") if abs(w) > abs(u) else ("west" if u > 0 else "east")
                        paso = int(r + 0.3 - d)                               # 0 fuera, 1 dentro
                        v.set(u, y + paso, w, f"prismarine_brick_stairs[facing={hacia},half=bottom]")
                        if paso:
                            v.set(u, y, w, LADRILLO)
                    else:
                        v.fill(u, y, w, u, y + 1, w, OSCURA if d > r - 1.3 else LADRILLO if (u + w) % 7 else PRISMARINA)
    top = S + 6                                                              # plataforma
    for k in range(24):                                                      # columnata
        a = (k + 0.5) * math.pi / 12
        cu, cw = round(36 * math.cos(a)), round(36 * math.sin(a))
        columna(v, cu, cw, top + 1, top + 9)
    v.disco(0, 0, 38, top + 10, top + 10, OSCURA, hueco=33)
    v.disco(0, 0, 37, top + 11, top + 11, LADRILLO, hueco=34)
    # cella
    rc = 16
    v.disco(0, 0, rc, top + 1, top + 5, LADRILLO, hueco=rc - 1)
    v.disco(0, 0, rc, top + 5, top + 5, OSCURA, hueco=rc - 1)
    v.cupula(0, 0, rc, top + 5, CRISTAL, nervio=OSCURA)
    v.set(0, top + 5 + rc, 0, LINTERNA)
    for du, dw in ((0, -1), (0, 1), (-1, 0), (1, 0)):                         # cuatro portales
        for t in (-1, 0, 1):
            cu, cw = du * rc + (t if du == 0 else 0), dw * rc + (t if dw == 0 else 0)
            v.quitar(cu, top + 1, cw, cu, top + 3, cw)
        v.set(du * (rc - 4), top + 1, dw * (rc - 4), LINTERNA)
    v.disco(0, 0, rc - 1, top, top, OSCURA)
    v.disco(0, 0, 6, top, top, PRISMARINA)
    v.entity(6, top + 6, 6, C.anciano())
    for u, w in ((8, -8), (-8, 8), (-8, -8)):
        v.entity(u, top + 2, w, C.ahogado(True))
    C.cartel(v, 3, top + 2, 0, "east", [C.texto("templo.1", "Bajo el templo,", "Below the temple,"),
                                         C.texto("templo.2", "cuatro palancas.", "four levers."),
                                         C.texto("templo.3", "Cada sello dice", "Each seal tells"),
                                         C.texto("templo.4", "cómo dejar una.", "how to leave one.")])
    v.set(2, top + 2, 0, CUARZO)
    v.set(2, top + 1, 0, CUARZO)
    # pozo: tubo de cristal de 2 x 2 de agua desde la cella hasta el suelo del vestíbulo
    for y in range(G0 + 1, top + 1):
        for u in range(-1, 3):
            for w in range(-1, 3):
                dentro = 0 <= u <= 1 and 0 <= w <= 1
                v.set(u, y, w, "water" if dentro else (CRISTAL if G0 < y < G1 else LADRILLO))
    v.set(0, top + 1, -1, LINTERNA)
    v.marca("pozo", 0, top, 0)


def vestibulo(v):
    """Sala seca bajo el templo: el pozo de cristal en el centro, cuatro puertas a las galerías, las tres arcas
    cerradas y la puerta de combinación que baja a N-2."""
    L = VESTIBULO + 1
    v.sitio("vestibulo", -L - 14, G0 - 1, -L - 6, L + 14, G1 + 3, L + 6)
    v.shell(-L, G0, -L, L, G1 + 2, L, LADRILLO, floor=OSCURA, roof=OSCURA)
    v.air(-L + 1, G0 + 1, -L + 1, L - 1, G1 + 1, L - 1)
    for y in range(G0 + 1, G1 + 2):                                         # se repone el pozo (el aire lo ha pisado)
        for u in range(-1, 3):
            for w in range(-1, 3):
                dentro = 0 <= u <= 1 and 0 <= w <= 1
                v.set(u, y, w, "water" if dentro else CRISTAL)
    v.fill(-1, G1 + 2, -1, 2, G1 + 2, 2, LADRILLO)
    v.fill(0, G1 + 2, 0, 1, G1 + 2, 1, "water")
    puerta(v, 0, G0 + 1, -1, "north")                                       # salida del pozo
    v.set(0, G0 + 3, -1, CRISTAL)
    for u, w in ((-L + 1, -L + 1), (L - 1, -L + 1), (-L + 1, L - 1), (L - 1, L - 1), (-5, -5), (5, 5), (-5, 5), (5, -5)):
        v.set(u, G1 + 1, w, LINTERNA)
    # arcas (muro oeste, a los lados de la puerta de la galería oeste en w = 0) con su cartel
    for w, cual in zip((-6, -3, 3), ("arsenal", "academia", "anfiteatro")):
        C.cofre(v, -L + 1, G0 + 1, w, "east", "arca", llave=cual)
        C.cartel(v, -L + 1, G0 + 2, w + 1, "east", [C.texto("arca." + cual, *{"arsenal": ("Arca: Arsenal", "Arsenal Coffer"),
                                                                              "academia": ("Arca: Academia", "Academy Coffer"),
                                                                              "anfiteatro": ("Arca: Anfiteatro", "Theatre Coffer")}[cual])])
    # combinación en el muro sur, hacia el este; el paso baja a N-2
    fin = R.combinacion(v, -3, G0 + 2, L, COMBINACION_CENTRAL, "templo")
    v.marca("seca", 4, G0 + 1, -4)
    v.marca("vestibulo", 4, G0 + 1, -4)
    return fin


def galerias(v):
    """N-1: cuatro radiales bajo las avenidas y un anillo cuadrado; tramos alternos secos e inundados con puertas."""
    def tramo_eje(eje, fijo, a, b, seco, sal):
        """Galería recta a lo largo de 'eje' ('x' o 'z') en la coordenada fija, de a a b (a < b)."""
        for t in range(a, b + 1):
            for lat in range(-2, 3):
                u, w = (t, fijo + lat) if eje == "x" else (fijo + lat, t)
                for y in range(G0, G1 + 1):
                    if abs(lat) == 2 or y in (G0, G1):
                        mat = OSCURA if y in (G0, G1) and lat == 0 else LADRILLO
                        if y == G1 and lat == 0 and t % 8 == 0:
                            mat = LINTERNA
                        v.set(u, y, w, mat)
                    else:
                        v.set(u, y, w, "air" if seco else "water")

    def tabique(eje, fijo, t):
        for lat in range(-1, 2):
            u, w = (t, fijo + lat) if eje == "x" else (fijo + lat, t)
            v.fill(u, G0 + 1, w, u, G1 - 1, w, LADRILLO)
        u, w = (t, fijo) if eje == "x" else (fijo, t)
        puerta(v, u, G0 + 1, w, "west" if eje == "x" else "north")

    def galeria(eje, fijo, a, b, nombre, empieza_seco):
        """De a a b con tabiques cada TRAMO; devuelve [(a_i, b_i, seco)]."""
        v.m.sitio(nombre, *((a, G0 - 1, fijo - 3, b, G1 + 1, fijo + 3) if eje == "x" else (fijo - 3, G0 - 1, a, fijo + 3, G1 + 1, b)))
        tramos, t, seco = [], a, empieza_seco
        while t <= b:
            fin = min(b, t + TRAMO - 1)
            if b - fin < 8:
                fin = b
            tramo_eje(eje, fijo, t, fin, seco, 0)
            tramos.append((t, fin, seco))
            if fin < b:
                tabique(eje, fijo, fin + 1)
                # el tabique cierra el tubo: muros, suelo y techo en esa sección
                for lat in (-2, 2):
                    u, w = (fin + 1, fijo + lat) if eje == "x" else (fijo + lat, fin + 1)
                    v.fill(u, G0, w, u, G1, w, LADRILLO)
                for y in (G0, G1):
                    for lat in range(-1, 2):
                        u, w = (fin + 1, fijo + lat) if eje == "x" else (fijo + lat, fin + 1)
                        v.set(u, y, w, OSCURA)
            t, seco = fin + 2, not seco
        return tramos

    todos = []
    L = VESTIBULO + 1
    # radiales: salen del vestíbulo por una puerta en cada muro
    for eje, signo in (("x", 1), ("x", -1), ("z", 1), ("z", -1)):
        if eje == "z" and signo == 1:
            a, b = L + 8, ANILLO - 3            # el muro sur lleva la combinación: la radial sur arranca más lejos, por un codo
        else:
            a, b = L + 1, ANILLO - 3
        lo, hi = (a, b) if signo == 1 else (-b, -a)
        tr = galeria(eje, 0, lo, hi, "radial", empieza_seco=(signo == 1))
        todos += [(eje, 0, t) for t in tr]
        if not (eje == "z" and signo == 1):
            u, w = (signo * L, 0) if eje == "x" else (0, signo * L)
            mira = {("x", 1): "east", ("x", -1): "west", ("z", -1): "north"}[(eje, signo)]
            puerta(v, u, G0 + 1, w, mira)
    # anillo cuadrado
    for eje, fijo in (("x", -ANILLO), ("x", ANILLO), ("z", -ANILLO), ("z", ANILLO)):
        tr = galeria(eje, fijo, -ANILLO + 3, ANILLO - 3, "anillo", empieza_seco=False)
        todos += [(eje, fijo, t) for t in tr]
    # nudos: cámaras inundadas de 7 x 7 en las esquinas y en los cruces con las radiales
    nudos = [(sx * ANILLO, sz * ANILLO) for sx in (-1, 1) for sz in (-1, 1)] + [(0, -ANILLO), (0, ANILLO), (-ANILLO, 0), (ANILLO, 0)]
    for cu, cw in nudos:
        v.shell(cu - 4, G0, cw - 4, cu + 4, G1 + 2, cw + 4, LADRILLO, floor=OSCURA, roof=OSCURA)
        v.fill(cu - 3, G0 + 1, cw - 3, cu + 3, G1 + 1, cw + 3, "water")
        v.set(cu, G1 + 2, cw, LINTERNA)
        v.m.sitio("nudo", cu - 4, G0 - 1, cw - 4, cu + 4, S + 8, cw + 4)
        for du, dw in ((1, 0), (-1, 0), (0, 1), (0, -1)):                    # bocas hacia las galerías que lleguen
            for lat in (-1, 0, 1):
                u, w = cu + du * 4 + (lat if du == 0 else 0), cw + dw * 4 + (lat if dw == 0 else 0)
                fuera = v.get(u + du, G0 + 1, w + dw)
                if fuera == "minecraft:water":
                    v.fill(u, G0 + 1, w, u, G1 - 1, w, "water")
                elif fuera == "minecraft:air" and lat == 0:
                    puerta(v, u, G0 + 1, w, {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(du, dw)])
        # pozo de acceso desde la calle: brocal con templete
        px, pw = cu + 2, cw + 2
        for y in range(G1 + 2, S + 1):
            for u in range(px - 1, px + 3):
                for w in range(pw - 1, pw + 3):
                    dentro = px <= u <= px + 1 and pw <= w <= pw + 1
                    v.set(u, y, w, "water" if dentro else LADRILLO)
        if v.get(px, S + 1, pw) == "minecraft:water" and v.get(px - 1, S + 1, pw - 1) == "minecraft:water":   # al aire libre: templete
            for u, w in ((px - 1, pw - 1), (px + 2, pw - 1), (px - 1, pw + 2), (px + 2, pw + 2)):
                columna(v, u, w, S + 1, S + 4)
            v.fill(px - 1, S + 5, pw - 1, px + 2, S + 5, pw + 2, OSCURA)
            v.set(px, S + 5, pw, LINTERNA)
        v.marca("pozo", px, S, pw)
    return todos


def poblar_galerias(v, tramos):
    """Contenido de cada tramo: nichos con cofres, trampas, generadores y vigías."""
    for n, (eje, fijo, (a, b, seco)) in enumerate(tramos):
        medio = (a + b) // 2
        def pos(t, lat):
            return (t, fijo + lat) if eje == "x" else (fijo + lat, t)
        sal = U.dispersion(a, fijo, 51)
        if b - a < 12:
            continue
        if seco:
            tipo = sal % 4
            if tipo == 0:                                                    # nicho con cofre a un lado
                u, w = pos(medio, 2)
                v.set(u, G0 + 1, w, "air")
                v.set(u, G0 + 2, w, "air")
                ext = pos(medio, 3)
                v.fill(ext[0], G0, ext[1], ext[0], G0 + 3, ext[1], LADRILLO)
                v.set(u, G0 + 3, w, LADRILLO)
                mira = ("north" if eje == "x" else "west")
                C.cofre(v, u, G0 + 1, w, mira, "media" if sal % 3 == 0 else "menor")
            elif tipo == 1:                                                  # trampa de flechas
                u, w = pos(medio, 1)
                d = pos(medio, 2)
                mira = ("north" if eje == "x" else "west")
                C.dispensador(v, d[0], G0 + 1, d[1], mira, "arrow", 24)
                v.set(u, G0 + 1, w, "stone_pressure_plate[powered=false]")
                c = pos(medio, 0)
                v.set(c[0], G0 + 1, c[1], "stone_pressure_plate[powered=false]")
                o = pos(medio, -1)
                d2 = pos(medio, -2)
                C.dispensador(v, d2[0], G0 + 1, d2[1], ("south" if eje == "x" else "east"), "arrow", 24)
                v.set(o[0], G0 + 1, o[1], "stone_pressure_plate[powered=false]")
                v.marca("trampa", u, G0 + 1, w)
            elif tipo == 2:                                                  # generador de ahogados
                u, w = pos(medio, 0)
                C.generador(v, u, G0 + 1, w, "drowned", tridente=sal % 2 == 0)
            else:                                                            # hoplita de guardia
                u, w = pos(medio, 0)
                v.entity(u, G0 + 1, w, C.ahogado(True))
        else:
            tipo = sal % 3
            u, w = pos(medio, 0)
            if tipo == 0:
                v.entity(u, G0 + 2, w, C.guardian())
            elif tipo == 1:
                C.generador(v, u, G0 + 1, w, "guardian")
            else:
                for t in range(medio - 3, medio + 4):
                    c = pos(t, 0)
                    v.set(c[0], G0, c[1], "magma_block")


def camaras(v, fin):
    """N-2: escalera seca desde la puerta de combinación, antecámara, sala del guardián final (inundada), tesoro
    (seco) y la cripta oculta del cofre premium bajo una trampilla tapada."""
    pu, py, pw = fin                                                         # celda tras la puerta, y = pies
    # codo: pasillo hacia el este y escalera que baja hacia el este
    y = py
    u = pu
    v.m.sitio("bajada", pu - 2, -10, pw - 1, pu + 40, G1 + 3, pw + 4)
    v.fill(pu - 1, y - 1, pw, pu + 3, y + 3, pw + 3, LADRILLO)
    v.air(pu, y, pw, pu + 2, y + 2, pw + 2)
    u, w = pu + 3, pw + 1
    baja = (py - (-6))
    for k in range(baja):
        # cada peldaño: un bloque más abajo y un bloque más al este
        yy = py - k
        v.fill(u + k, yy - 2, w - 1, u + k, yy + 3, w + 1, LADRILLO)
        v.air(u + k, yy, w, u + k, yy + 2, w)
        v.set(u + k, yy - 1, w, "prismarine_brick_stairs[facing=west,half=bottom]")
        if k % 6 == 3:
            v.set(u + k, yy + 3, w, LINTERNA)
    ex = u + baja                                                            # x donde termina la escalera, pies en y = -6
    piso = -7
    # antecámara seca
    sala(v, ex - 1, w - 5, ex + 9, w + 5, piso, piso + 6)
    v.air(ex - 1, piso + 1, w, ex - 1, piso + 3, w)
    v.fill(ex - 1, piso + 4, w, ex - 1, piso + 4, w, LADRILLO)
    v.set(ex + 4, piso + 5, w, LINTERNA)
    C.cartel(v, ex + 8, piso + 2, w - 2, "west", [C.texto("antecamara.1", "Aquí vela", "Here watches"),
                                                  C.texto("antecamara.2", "el Guardián", "the Warden"),
                                                  C.texto("antecamara.3", "de Poseidón.", "of Poseidon.")])
    C.cofre(v, ex + 1, piso + 1, w - 4, "south", "media")
    v.marca("seca", ex + 4, piso + 1, w + 2)
    # sala del guardián final: 31 x 31 x 12, inundada
    bx1, bx2, bz1, bz2 = ex + 9, ex + 41, w - 16, w + 16
    v.m.sitio("camaras", ex - 2, -24, bz1 - 1, bx2 + 24, piso + 14, bz2 + 1)
    v.shell(bx1, piso - 1, bz1, bx2, piso + 12, bz2, LADRILLO, floor=OSCURA, roof=OSCURA)
    v.fill(bx1 + 1, piso, bz1 + 1, bx2 - 1, piso + 11, bz2 - 1, "water")
    puerta(v, bx1, piso + 1, w, "west")
    v.set(bx1, piso, w, OSCURA)
    v.fill(bx1 + 1, piso, w - 1, bx1 + 2, piso, w + 1, OSCURA)               # rellano interior a la altura de la puerta
    cx = (bx1 + bx2) // 2
    for du in (-10, 0, 10):
        for dw in (-10, 10):
            columna(v, cx + du, w + dw, piso, piso + 11)
    for du, dw in ((-12, -12), (12, -12), (-12, 12), (12, 12), (0, 0)):
        v.set(cx + du, piso + 12, w + dw, LINTERNA)
        v.set(cx + du, piso - 1, w + dw, LINTERNA)
    v.entity(cx, piso + 5, w, C.jefe())
    for du, dw in ((-6, -6), (6, -6), (-6, 6), (6, 6)):
        v.entity(cx + du, piso + 1, w + dw, C.ahogado(True))
    C.generador(v, cx - 13, piso, w - 13, "guardian")
    C.generador(v, cx + 13, piso, w + 13, "guardian")
    v.marca("jefe", cx, piso + 5, w)
    # tesoro (seco), al este
    tx1, tx2 = bx2, bx2 + 16
    sala(v, tx1, w - 7, tx2, w + 7, piso, piso + 6)
    puerta(v, tx1, piso + 1, w, "west")
    for k, dw in enumerate((-6, -3, 3, 6)):
        C.cofre(v, tx2 - 1, piso + 1, w + dw, "west", "tesoro")
    for u_ in (tx1 + 2, tx2 - 2):
        for dw in (-6, 6):
            v.set(u_, piso + 5, w + dw, LINTERNA)
    v.fill(tx1 + 4, piso + 1, w - 6, tx1 + 5, piso + 1, w - 6, "gold_block")
    v.fill(tx1 + 4, piso + 1, w + 6, tx1 + 5, piso + 1, w + 6, "gold_block")
    v.fill(tx1 + 3, piso, w - 2, tx2 - 3, piso, w + 2, "cyan_terracotta")
    v.marca("seca", tx1 + 6, piso + 1, w)
    # cripta oculta: bajo la trampilla de la esquina, tapada por una alfombra
    hu, hw = tx2 - 2, w - 1
    sala(v, hu - 5, hw - 3, hu + 1, hw + 3, piso - 7, piso - 1)
    v.set(hu, piso, hw, "warped_trapdoor[facing=north,half=top,open=false]")
    v.set(hu, piso + 1, hw, "cyan_carpet")
    for yy in range(piso - 6, piso):
        v.set(hu, yy, hw, "ladder[facing=west]")
    v.set(hu + 1, piso - 1, hw, LADRILLO)
    v.set(hu - 4, piso - 2, hw - 2, LINTERNA)
    v.set(hu - 4, piso - 2, hw + 2, LINTERNA)
    v.fill(hu - 4, piso - 6, hw - 1, hu - 4, piso - 6, hw + 1, "gold_block")
    from . import botin
    C.cofre_fijo(v, hu - 4, piso - 5, hw, "east", botin.premium(), llave="poseidon", por_jugador="atlantida")
    v.marca("premium", hu - 4, piso - 5, hw)
    v.marca("seca", hu - 2, piso - 6, hw)
    v.marca("oculta", hu - 2, piso - 6, hw)
