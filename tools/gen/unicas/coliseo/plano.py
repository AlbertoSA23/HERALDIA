"""Geometría del Coliseo en ruinas: anfiteatro elíptico (pieza principal, y >= 0) e hipogeo (pieza hija, y < 0).

Todo se construye en un único "mundo" con coordenadas centradas en la arena (dx, y, dz) y al final se parte en
las dos plantillas. Así los elementos que cruzan y=0 (pozo, escalera oeste, pasadizo de Cómodo) son una sola pieza
de diseño. `construir()` devuelve el mundo, las dos plantillas y el inventario de elementos para la auditoría.
"""
import math, random
from core import Template, parse_state, state_str, B, F
from .._comun import piezas
from .._comun.recorrido import is_full

A0, B0 = 16.5, 9.5          # semiejes del borde de la arena
CX, CZ = 43, 36             # centro de la arena en la plantilla principal (87 x 73)
NX, NZ = 87, 73
TOP = 27                    # techo de la caja de la pieza principal
NB = 40                     # vanos de la fachada
WEDGE = (23.5, 29.5)        # vanos del tramo derrumbado (noroeste)
HYP = (-31, 24, -16, 16, -14, -1)   # caja del hipogeo: dx0, dx1, dz0, dz1, y0, y1

FILL, FLOOR, WALL = "bricks", "smooth_sandstone", "smooth_sandstone"
SEAT = "smooth_sandstone_stairs"
MARBLE, MARBLE_TOP, PARAPET = "quartz_bricks", "smooth_quartz", "diorite_wall"
ROCK, LINING = "stone", "stone_bricks"

OUT = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}
OPP = {"east": "west", "west": "east", "south": "north", "north": "south"}


class DesignError(Exception):
    pass


# ------------------------------------------------------------------ anillos
def kval(dx, dz):
    """Distancia de anillo: (dx/(A0+k))^2 + (dz/(B0+k))^2 = 1."""
    if dx == 0 and dz == 0:
        return -B0
    lo, hi = -B0 + 1e-6, 400.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if (dx / (A0 + mid)) ** 2 + (dz / (B0 + mid)) ** 2 > 1:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _arc_table():
    a, b = A0 + 24, B0 + 24
    n = 4096
    pts = [(a * math.cos(2 * math.pi * i / n), b * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    cum = [0.0]
    for i in range(n):
        cum.append(cum[-1] + math.dist(pts[i], pts[i + 1]))
    return cum, n


_CUM, _N = _arc_table()


def bay(dx, dz, k):
    """Posición en vanos (0..NB) a lo largo del anillo; los ejes caen en el centro de un vano (fracción 0,5)."""
    t = math.atan2(dz / (B0 + k), dx / (A0 + k)) % (2 * math.pi)
    i = t / (2 * math.pi) * _N
    j = min(int(i), _N - 1)
    s = _CUM[j] + (_CUM[j + 1] - _CUM[j]) * (i - j)
    return (NB * s / _CUM[-1] + 0.5) % NB


def outward(dx, dz, k):
    gx, gz = dx / (A0 + k) ** 2, dz / (B0 + k) ** 2
    if abs(gx) >= abs(gz):
        return "east" if gx > 0 else "west"
    return "south" if gz > 0 else "north"


def S(r):
    """Altura del bloque superior (pisable) del anillo r."""
    if r <= 3:
        return 4
    if r <= 9:
        return r + 1
    if r <= 11:
        return 10
    if r <= 19:
        return r - 1
    if r <= 21:
        return 18
    return 24


SEAT_RINGS = set(range(4, 10)) | set(range(12, 20))


class Col:
    __slots__ = ("k", "r", "u", "out")


COLS = {}
for _dx in range(-CX, NX - CX):
    for _dz in range(-CZ, NZ - CZ):
        c = Col()
        c.k = kval(_dx, _dz)
        c.r = math.floor(c.k) if c.k >= 0 else -1
        c.u = bay(_dx, _dz, max(c.k, 0))
        c.out = outward(_dx, _dz, max(c.k, 0.1))
        COLS[(_dx, _dz)] = c


def ring(dx, dz):
    c = COLS.get((dx, dz))
    return c.r if c else 99


def noise(seed, x):
    """Ruido 1D suave y determinista en [0, 1]."""
    i = math.floor(x)
    f = x - i
    def h(n):
        return random.Random(seed * 1000003 + n).random()
    f = f * f * (3 - 2 * f)
    return h(i) * (1 - f) + h(i + 1) * f


# ------------------------------------------------------------------ mundo
class Obra:
    def __init__(self):
        self.t = Template("unicas/coliseo/_mundo")
        self.feat = {k: [] for k in ("cofre", "generador", "puerta", "puzle", "trampa", "guardian", "palanca",
                                     "marco", "escalera")}
        self.solved = {}      # estado con los puzles resueltos: pos -> estado (o "air")
        self.ruined = set()   # columnas (x, z) tocadas por la ruina: el escombro puede dejar escalones de un bloque
        self.rooms = {}       # nombre -> (dx0, dx1, dz0, dz1, y) para planos y comprobaciones

    # coordenadas centradas
    def P(self, dx, y, dz):
        return (CX + dx, y, CZ + dz)

    def set(self, dx, y, dz, st, nbt=None):
        self.t.set(CX + dx, y, CZ + dz, st, nbt)

    def get(self, dx, y, dz):
        return self.t.get(CX + dx, y, CZ + dz)

    def fill(self, dx0, y0, dz0, dx1, y1, dz1, st):
        for x in range(min(dx0, dx1), max(dx0, dx1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(dz0, dz1), max(dz0, dz1) + 1):
                    self.set(x, y, z, st)

    def carve(self, dx, y, dz, open_=False):
        """Vacía una celda. En la pieza principal solo se permite por debajo de la superficie del graderío
        (si no, abriría un agujero visible), salvo que se pida expresamente (bocas de vomitorio)."""
        if y >= 0:
            r = ring(dx, dz)
            if 0 <= r <= 24 and y >= S(r) and not open_:
                raise DesignError(f"vaciado por encima de la superficie en {(dx, y, dz)} (anillo {r}, S={S(r)})")
            if open_ and 0 <= r <= 24 and y >= S(r):
                for yy in range(y, S(r) + 2):
                    self.set(dx, yy, dz, "air")
        else:
            x0, x1, z0, z1, y0, y1 = HYP
            if not (x0 <= dx <= x1 and z0 <= dz <= z1 and y0 <= y):
                raise DesignError(f"vaciado fuera de la caja del hipogeo en {(dx, y, dz)}")
        self.set(dx, y, dz, "air")

    def carve_box(self, dx0, y0, dz0, dx1, y1, dz1, open_=False):
        for x in range(min(dx0, dx1), max(dx0, dx1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(dz0, dz1), max(dz0, dz1) + 1):
                    self.carve(x, y, z, open_)

    def flight(self, cells, y0, facing, mat=SEAT, head=2):
        """Tramo de escalera: cells en orden ascendente; peldaño i en y0+i mirando hacia `facing` (lado alto)."""
        for i, (x, z) in enumerate(cells):
            y = y0 + i
            for hy in range(1, head + 1):
                self.carve(x, y + hy, z)
            self.set(x, y, z, f"{mat}[facing={facing},half=bottom]")

    def chest(self, dx, y, dz, facing, table, label):
        self.set(dx, y, dz, *piezas.cofre(f"heraldia:unicas/coliseo/{table}", facing))
        self.feat["cofre"].append((label, table, (dx, y, dz)))

    def barrel(self, dx, y, dz, facing="up"):
        self.set(dx, y, dz, f"barrel[facing={facing}]", {"id": "minecraft:barrel"})

    def spawner(self, dx, y, dz, mob, label):
        self.set(dx, y, dz, *piezas.generador(mob))
        self.feat["generador"].append((label, mob, (dx, y, dz)))

    def lantern(self, dx, y, dz):
        """Farol colgado del techo (fix_supports añade la cadena si hace falta)."""
        self.set(dx, y, dz, "lantern[hanging=true]")

    def entity(self, dx, y, dz, nbt):
        self.t.entity(CX + dx, y, CZ + dz, nbt)

    def frame(self, dx, y, dz, facing_byte, objeto=None):
        self.entity(dx, y, dz, piezas.marco(CX + dx, y, CZ + dz, facing_byte, objeto))


def cols_ring(pred):
    for (dx, dz), c in COLS.items():
        if pred(c):
            yield dx, dz, c


# ------------------------------------------------------------------ pieza principal
def base(o):
    for (dx, dz), c in COLS.items():
        r = c.r
        if c.k < 0:
            o.set(dx, 0, dz, "sand")
            o.fill(dx, 1, dz, dx, TOP, dz, "air")
            continue
        if r > 26:
            continue
        if r >= 25:
            o.set(dx, 0, dz, "smooth_sandstone_slab[type=bottom]")
            o.fill(dx, 1, dz, dx, 4, dz, "air")
            continue
        s = S(r)
        o.set(dx, 0, dz, FLOOR)
        if r >= 22:
            o.fill(dx, 1, dz, dx, s, dz, WALL)
        elif r == 0:
            o.fill(dx, 1, dz, dx, s, dz, MARBLE)
            o.set(dx, s + 1, dz, PARAPET)
        else:
            o.fill(dx, 1, dz, dx, s - 1, dz, FILL)
            if r <= 3:
                o.set(dx, s, dz, MARBLE_TOP)
            elif r in SEAT_RINGS:
                o.set(dx, s, dz, f"{SEAT}[facing={c.out},half=bottom]")
            else:
                o.set(dx, s, dz, FLOOR)
        for y in range(s + 1 + (r == 0), TOP + 1):
            o.set(dx, y, dz, "air")


def facade(o):
    """Arcos de dos órdenes abiertos, tercer orden ciego, ático con ventanas, impostas y mástiles del velario."""
    for (dx, dz), c in COLS.items():
        r = c.r
        if not (22 <= r <= 25):
            continue
        f = c.u % 1.0
        if r <= 24:
            if 0.2 <= f <= 0.8:
                o.fill(dx, 1, dz, dx, 4, dz, "air")
                o.fill(dx, 8, dz, dx, 10, dz, "air")
                if r == 24:
                    o.set(dx, 8, dz, "sandstone_wall")
            if 0.33 <= f <= 0.67:
                o.set(dx, 5, dz, "air")
                o.set(dx, 11, dz, "air")
            if 0.42 <= f <= 0.58:
                o.fill(dx, 20, dz, dx, 21, dz, "iron_bars" if r == 24 else "air")
            if r == 24:
                if 0.25 <= f <= 0.75:
                    o.fill(dx, 13, dz, dx, 15, dz, "air")
                if 0.38 <= f <= 0.62:
                    o.set(dx, 16, dz, "air")
                pier = f < 0.12 or f > 0.88
                if pier:
                    for y in range(1, 19):
                        if o.get(dx, y, dz) == "minecraft:" + WALL:
                            o.set(dx, y, dz, "chiseled_sandstone" if y in (4, 10, 16) else "cut_sandstone")
            if r == 23 and abs(f - 0.0) < 0.06 and int(c.u) % 2 == 0:
                o.set(dx, 25, dz, "spruce_fence")
                o.set(dx, 26, dz, "spruce_fence")
        else:
            for y in (6, 12, 18):
                o.set(dx, y, dz, "smooth_sandstone_slab[type=top]")
            o.set(dx, 24, dz, "smooth_sandstone_slab[type=top]")


def galleries(o):
    for dx, dz, c in cols_ring(lambda c: 19 <= c.r <= 21):
        o.carve_box(dx, 1, dz, dx, 5, dz)
        o.carve_box(dx, 8, dz, dx, 11, dz)
        f = c.u % 1.0
        if c.r == 20 and abs(f - 0.5) < 0.09 and int(c.u) % 3 == 0:
            o.lantern(dx, 5, dz)
            o.lantern(dx, 11, dz)


def tunnels(o):
    """Puerta Triunfal (este) y Libitinaria (oeste): túneles de la arena a G1; pasos norte y sur a los palcos."""
    for sign in (1, -1):
        for dz in (-1, 0, 1):
            dx = sign * 16
            while ring(dx, dz) <= 18:
                if ring(dx, dz) >= 0:
                    o.carve_box(dx, 1, dz, dx, 3, dz)
                dx += sign
        # rastrillo alzado en la boca de la arena
        for dz in (-1, 0, 1):
            dx = sign * 17
            while ring(dx, dz) < 0:
                dx += sign
            o.set(dx, 3, dz, "iron_bars")
        o.lantern(sign * 27, 3, 0)
        o.feat["puerta"].append(("Puerta Triunfal" if sign > 0 else "Puerta Libitinaria", (sign * 17, 1, 0)))
    # paso sur (palco imperial) y norte (palco del editor): llano hasta r=10 y escalera de 4 peldaños
    for sign, label in ((1, "palco imperial"), (-1, "palco del editor")):
        face = "north" if sign > 0 else "south"
        for dx in (-1, 0, 1):
            dz = sign * 33
            while ring(dx, dz) > 18:
                dz -= sign
            while dz * sign > 20:
                o.carve_box(dx, 1, dz, dx, 3, dz)
                dz -= sign
            o.flight([(dx, sign * z) for z in (20, 19, 18, 17)], 1, face, mat="sandstone_stairs")
        o.lantern(0, 3, sign * 24)


def g1_to_g2(o):
    """Cuatro escaleras de G1 (pisa 1) a G2 (pisa 8): tramo de 7 peldaños hacia dentro, rellano y vuelta en llano."""
    for sx in (1, -1):
        for sz in (1, -1):
            x = sx * 13
            z = sz * 31
            while ring(x, z) > 18:
                z -= sz
            cells = [(x, z - sz * i) for i in range(7)]
            o.flight(cells, 1, "north" if sz > 0 else "south", mat="brick_stairs")
            lz = z - sz * 7
            o.carve_box(x, 8, lz, x, 9, lz)
            x2 = x - sx
            zz = lz
            while ring(x2, zz) <= 18:
                o.carve_box(x2, 8, zz, x2, 9, zz)
                zz += sz
            o.feat["escalera"].append(("G1-G2", (x, 1, z)))


def vomitoria(o):
    """Seis vomitorios de G2 (pisa 8) al pasillo I (pisa 11): tres peldaños y llano; boca abierta en el graderío."""
    lines = []
    for sz in (1, -1):
        for sx in (1, -1):
            lines.append([(sx * x, sz) for x in (7, 8, 9)])
    for sxe in (1, -1):
        lines.append([(z, sxe) for z in (-1, 0, 1)])     # este / oeste: (dz, signo en x)
    for ln in lines[:4]:
        for x, sz in ln:
            z = sz * 31
            while ring(x, z) > 18:
                z -= sz
            o.flight([(x, z - sz * i) for i in range(3)], 8, "north" if sz > 0 else "south", head=2)
            zz = z - sz * 3
            while ring(x, zz) > 11:
                o.carve_box(x, 11, zz, x, 12, zz, open_=True)
                zz -= sz
    for ln in lines[4:]:
        for z, sx in ln:
            x = sx * 42
            while ring(x, z) > 18:
                x -= sx
            o.flight([(x - sx * i, z) for i in range(3)], 8, "west" if sx > 0 else "east", head=2)
            xx = x - sx * 3
            while ring(xx, z) > 11:
                o.carve_box(xx, 11, z, xx, 12, z, open_=True)
                xx -= sx


def tabernae(o):
    for sx, sz, label in ((1, -1, "taberna NE"), (-1, 1, "taberna SO")):
        x0, x1 = sorted((sx * 18, sx * 22))
        z0, z1 = sorted((sz * 18, sz * 21))
        o.carve_box(x0, 1, z0, x1, 3, z1)
        # pasillo de acceso hasta G1
        for x in (sx * 20, sx * 21):
            z = sz * 22
            while ring(x, z) <= 18:
                o.carve_box(x, 1, z, x, 3, z)
                z += sz
        # mobiliario contra la pared del fondo (la más interior)
        inner = z1 if sz < 0 else z0         # fila junto a la pared del lado de la arena
        face = "north" if sz < 0 else "south"
        xa = x0 if sx > 0 else x1
        o.chest(xa + sx * 1, 1, inner, face, "taberna", label)
        o.barrel(xa, 1, inner)
        o.barrel(xa + sx * 2, 1, inner)
        o.set(xa + sx * 3, 1, inner, "decorated_pot")
        o.barrel(xa, 2, inner)
        o.set(xa + sx * 4, 1, inner, "crafting_table")
        o.lantern(sx * 20, 3, (z0 + z1) // 2)


def palcos(o):
    """Palco imperial (sur, con el puzle 2) y palco del editor (norte)."""
    # --- palco imperial: interior dx -4..4, dz 11..15, suelo y=4; muros laterales gruesos (3) y fondo dz=16
    for x in range(-7, 8):
        for z in range(11, 17):
            o.fill(x, 1, z, x, 3, z, FILL)
            o.set(x, 4, z, MARBLE_TOP)
            o.fill(x, 5, z, x, TOP, z, "air")
    for x in range(-7, 8):
        for z in range(11, 17):
            wall = abs(x) >= 5 or z == 16
            if wall:
                o.fill(x, 5, z, x, 8, z, MARBLE)
            o.set(x, 9, z, MARBLE_TOP)
    for x in range(-7, 8):
        o.set(x, 10, 11, "quartz_slab[type=bottom]")
        o.set(x, 10, 16, "quartz_slab[type=bottom]")
    for z in range(12, 16):
        o.set(-7, 10, z, "quartz_slab[type=bottom]")
        o.set(7, 10, z, "quartz_slab[type=bottom]")
    for x in (-4, 4):
        o.fill(x, 5, 11, x, 8, 11, "quartz_pillar[axis=y]")
    for x in range(-3, 4):
        o.set(x, 5, 10, PARAPET)
    o.carve_box(-1, 5, 16, 1, 6, 16)                 # entrada desde la escalera
    # trono mirando a la arena, alfombra y estandartes
    o.set(0, 5, 13, "quartz_stairs[facing=south,half=bottom]")
    o.set(-1, 5, 13, "quartz_slab[type=bottom]")
    o.set(1, 5, 13, "quartz_slab[type=bottom]")
    for z in (14, 15):
        o.set(0, 5, z, "red_carpet")
    o.chest(3, 5, 15, "west", "palco", "palco imperial")
    o.barrel(4, 5, 14, "west")
    o.set(4, 5, 12, "decorated_pot")
    o.lantern(-2, 8, 13)
    o.lantern(2, 8, 13)
    # --- puzle 2: nicho + puerta de pistones enrasada en el muro oeste; palanca en el muro (x=-4, z=12)
    a = 5
    m = piezas.puerta_pistones(o.set, (-6, a, 15), "north", "east", "minecraft:chiseled_quartz_block", "minecraft:" + MARBLE)
    o.feat["palanca"].append(("puzle 2: palanca del palco", m["palanca"]))
    o.feat["puzle"].append(("puzle 2: puerta de pistones", m["puerta"]))
    o.solved.update({o.P(*p): st for p, st in m["solved"].items()})
    o.carve_box(-7, a, 15, -7, a + 1, 15)
    # --- palco del editor (norte): interior dx -3..3, dz -15..-11, muros de 1
    for x in range(-4, 5):
        for z in range(-16, -10):
            o.fill(x, 1, z, x, 3, z, FILL)
            o.set(x, 4, z, MARBLE_TOP)
            o.fill(x, 5, z, x, TOP, z, "air")
            if abs(x) == 4 or z == -16:
                o.fill(x, 5, z, x, 8, z, MARBLE)
            o.set(x, 9, z, MARBLE_TOP)
    for x in (-3, 3):
        o.fill(x, 5, -11, x, 8, -11, "quartz_pillar[axis=y]")
    for x in range(-2, 3):
        o.set(x, 5, -10, PARAPET)
    o.carve_box(-1, 5, -16, 1, 6, -16)
    o.set(0, 5, -13, "quartz_stairs[facing=north,half=bottom]")
    o.chest(-3, 5, -15, "east", "palco_menor", "palco del editor")
    o.set(-3, 5, -14, "decorated_pot")
    o.lantern(0, 8, -13)


def terrace(o):
    """Cofre del velario contra el ático, en un machón cerca del eje este."""
    best = None
    for (dx, dz), c in COLS.items():
        if c.r == 21 and dx > 30 and -12 < dz < 0:
            f = c.u % 1.0
            d = min(f, 1 - f)
            if best is None or d < best[0]:
                best = (d, dx, dz, c)
    _, dx, dz, c = best
    face = OPP[c.out]
    o.chest(dx, 19, dz, face, "velario", "velario")
    ddx, ddz = (0, 1) if c.out in ("east", "west") else (1, 0)
    if ring(dx + ddx, dz + ddz) == 21:
        o.barrel(dx + ddx, 19, dz + ddz)
    o.set(dx - ddx, 19, dz - ddz, "white_wool")


def west_stairs(o):
    """Escalera de G1 (oeste) al hipogeo: paso llano y 7 peldaños bajando hacia el este hasta H1."""
    for z in (2, 3):
        x = -40
        while ring(x, z) > 18:
            x += 1
        while x < -30:
            o.carve_box(x, 1, z, x, 3, z)
            x += 1
        o.flight([(xx, z) for xx in range(-24, -31, -1)], -6, "west", mat="stone_brick_stairs")
        o.carve(-30, 3, z)
    o.lantern(-33, 3, 2)
    o.feat["escalera"].append(("G1-hipogeo", (-30, 0, 2)))


# ------------------------------------------------------------------ hipogeo
def hypogeum(o):
    x0, x1, z0, z1, y0, y1 = HYP
    o.fill(x0, y0, z0, x1, y1, z1, ROCK)
    H1, H2 = -6, -13
    rooms = o.rooms
    def room(name, a, b, c, d, y, h):
        o.carve_box(a, y, c, b, y + h - 1, d)
        rooms[name] = (a, b, c, d, y)
    room("corredor central", -21, 17, -1, 1, H1, 4)
    room("corredor norte", -16, 16, -6, -5, H1, 3)
    room("corredor sur", -16, 16, 5, 6, H1, 3)
    for x in (-10, -9, 9, 10):
        o.carve_box(x, H1, -4, x, H1 + 2, -2)
        o.carve_box(x, H1, 2, x, H1 + 2, 4)
    # celdas de fieras (frente con rejas y puerta abierta)
    cells = [(-16, -13), (-11, -8), (-6, -3), (3, 6), (8, 11), (13, 16)]
    for sz in (1, -1):
        for a, b in cells:
            zc0, zc1 = sorted((sz * 8, sz * 10))
            o.carve_box(a, H1, zc0, b, H1 + 2, zc1)
            for x in range(a, b + 1):
                for y in range(H1, H1 + 3):
                    o.set(x, y, sz * 7, "iron_bars")
            o.carve_box(a + 1, H1, sz * 7, a + 1, H1 + 1, sz * 7)
        rooms["celdas " + ("sur" if sz > 0 else "norte")] = (-16, 16, min(sz * 8, sz * 10), max(sz * 8, sz * 10), H1)
    # contenidos de las celdas
    o.spawner(-10, H1, -9, "spider", "arañas (celda norte)")
    o.spawner(9, H1, 9, "zombie", "zombis (celda sur)")
    o.set(-15, H1, -10, "hay_block"); o.set(-14, H1, -10, "hay_block"); o.set(-15, H1 + 1, -10, "hay_block")
    o.set(-5, H1, -10, "bone_block"); o.set(-6, H1, -10, "cobweb"); o.set(-4, H1 + 2, -10, "cobweb")
    o.set(4, H1, -10, "hay_block"); o.set(5, H1, -10, "composter")
    o.set(15, H1, -10, "cobweb"); o.set(12 + 2, H1, -9, "bone_block")
    o.set(-15, H1, 10, "hay_block"); o.set(-12, H1, 10, "cobweb")
    o.set(-5, H1, 10, "bone_block"); o.set(-3, H1 + 2, 10, "cobweb")
    o.set(4, H1, 10, "hay_block"); o.set(5, H1, 10, "hay_block")
    o.chest(15, H1, 10, "north", "fieras", "domador (celda sur-este)")
    o.barrel(16, H1, 10); o.set(13, H1, 10, "hay_block")
    for x in (3, 5):          # rejas rotas: hueco con sentido
        o.set(x, H1 + 2, -7, "air")
    # montacargas: jaula de 2 x 1 con rejas, plataforma colgada y trampilla en la arena
    for a in (-14, -6, 5, 13):
        for sz in (1, -1):
            for x in (a, a + 1):
                for y in range(H1, H1 + 4):
                    o.set(x, y, sz * 2, "iron_bars")
                o.carve_box(x, H1, sz * 3, x, -2, sz * 3)
                o.set(x, 0, sz * 3, f"spruce_trapdoor[facing={'north' if sz > 0 else 'south'},half=top,open=false]")
                o.set(x, -4, sz * 3, "spruce_slab[type=top]")
            for y in (-2, -3):
                o.set(a, y, sz * 3, "iron_chain[axis=y]")
    # pozo central con escalera de mano a la arena
    for y in range(H1, 1):
        if y > -3:
            o.set(0, y, -1, "air")
        o.set(0, y, -1, "ladder[facing=south]")
    o.feat["escalera"].append(("pozo de la arena", (0, 0, -1)))
    # trampa 1: cable trampa en el corredor de la armería (dx=16)
    piezas.trampa_cable(o.set, (16, H1, -1), "south", 1, flechas=9)
    o.feat["trampa"].append(("trampa 1: cable y flechas", (16, H1, 0)))
    # armería (este)
    room("armería", 19, 23, -7, 7, H1, 4)
    o.carve_box(18, H1, -1, 18, H1 + 1, 1)
    for z, gear in ((-6, "iron"), (-3, "chainmail"), (0, "leather"), (3, "chainmail")):
        o.entity(23, H1, z, {"id": "minecraft:armor_stand", "ShowArms": B(1), "Rotation": [F(90.0), F(0.0)],
                             "equipment": {"head": {"id": f"minecraft:{gear}_helmet", "count": 1},
                                           "chest": {"id": f"minecraft:{gear}_chestplate", "count": 1}}})
    for z, it in ((-5, "iron_sword"), (-3, "bow"), (3, "stone_sword")):
        o.frame(19, H1 + 1, z, 5, it)
        o.set(18, H1 + 1, z, LINING)
    o.set(23, H1, -7, "smithing_table"); o.set(22, H1, -7, "grindstone[face=floor,facing=north]")
    o.chest(19, H1, -7, "south", "armeria", "armería")
    o.barrel(20, H1, -7, "south")
    o.lantern(21, H1 + 3, -4); o.lantern(21, H1 + 3, 0)
    # puzle 1: pedestal con marco vacío -> comparador -> trampilla de hierro sobre el pozo al despacho
    o.set(20, H1, 5, "chiseled_stone_bricks")
    o.frame(20, H1, 4, 2)
    o.set(20, H1, 6, "comparator[facing=north,mode=compare,powered=false]")
    o.set(20, H1, 7, "iron_trapdoor[facing=north,half=bottom,open=false,powered=false]")
    o.feat["marco"].append(("puzle 1: marco de la ofrenda", (20, H1, 4)))
    o.feat["puzle"].append(("puzle 1: trampilla de hierro", (20, H1, 7)))
    o.solved[o.P(20, H1, 7)] = "iron_trapdoor[facing=north,half=bottom,open=true,powered=true]"
    # barracones (oeste) con generador de esqueletos
    room("barracones", -24, -18, -9, -3, H1, 4)
    o.carve_box(-20, H1, -2, -20, H1 + 1, -2)
    for x in (-24, -22):
        o.set(x, H1, -9, "red_bed[facing=north,part=head]"); o.set(x, H1, -8, "red_bed[facing=north,part=foot]")
    for x in (-24,):
        o.set(x, H1, -5, "red_bed[facing=west,part=head]"); o.set(x + 1, H1, -5, "red_bed[facing=west,part=foot]")
    o.chest(-18, H1, -9, "west", "barracones", "barracones")
    o.barrel(-18, H1, -8, "west"); o.barrel(-18, H1, -7, "up")
    o.spawner(-23, H1, -3, "skeleton", "esqueletos (barracones)")
    # vestíbulo de la escalera oeste
    o.carve_box(-23, H1, 2, -21, H1 + 3, 3)
    rooms["vestíbulo oeste"] = (-23, -21, 2, 3, H1)
    # H2: despacho del lanista, pasillo de las placas, cámara del tesoro
    room("despacho del lanista", 16, 23, 1, 7, H2, 4)
    o.chest(23, H2, 1, "west", "lanista", "lanista (oculto)")
    o.set(17, H2, 1, "lectern[facing=south]"); o.set(18, H2, 1, "bookshelf"); o.set(19, H2, 1, "bookshelf")
    o.set(16, H2, 7, "barrel[facing=up]", {"id": "minecraft:barrel"})
    o.lantern(19, H2 + 3, 4)
    o.carve_box(15, H2, 3, 15, H2 + 1, 3)
    room("pasillo de las placas", 10, 14, 3, 3, H2, 2)
    piezas.trampa_placas(o.set, [(x, H2, 3) for x in (11, 12, 13)], "north", flechas=6)
    o.feat["trampa"].append(("trampa 2: placas y flechas", (12, H2, 3)))
    o.carve_box(9, H2, 3, 9, H2 + 1, 3)
    room("cámara del tesoro", -8, 8, -4, 4, H2, 5)
    for x in (-4, 4):
        for z in (-2, 2):
            o.fill(x, H2, z, x, H2 + 4, z, "quartz_pillar[axis=y]")
            o.lantern(x, H2 + 4, z + (1 if z > 0 else -1))
    o.fill(-8, H2, -4, -6, H2, 4, "polished_blackstone_bricks")
    for z in range(-4, 5):
        o.set(-5, H2, z, "polished_blackstone_brick_stairs[facing=west,half=bottom]")
    o.chest(-8, H2 + 1, 0, "east", "premium", "premium")
    o.set(-8, H2 + 1, -2, "gilded_blackstone"); o.set(-8, H2 + 1, 2, "gilded_blackstone")
    o.set(-7, H2 + 1, -3, "red_carpet"); o.set(-7, H2 + 1, 3, "red_carpet")
    for x in range(-3, 4):
        o.set(x, H2, 0, "red_carpet")
    o.entity(0, H2, 0, champion())
    o.feat["guardian"].append(("Campeón de la Arena", (0, H2, 0)))
    o.carve_box(0, H2, 5, 0, H2 + 1, 5)
    # pasadizo de Cómodo: tramo alto (dz=15) del palco al rellano H1, capilla, tramo bajo (dz=12) y pasillo a la cámara
    o.flight([(x, 15) for x in range(-18, -8)], -6, "east", mat="quartz_stairs")
    o.carve_box(-8, 4, 15, -8, 6, 15)
    o.set(-8, 4, 15, "quartz_stairs[facing=east,half=bottom]")
    room("rellano de Cómodo", -21, -19, 12, 15, H1, 3)
    room("capilla de Cómodo", -23, -22, 13, 14, H1, 3)
    o.chest(-23, H1, 13, "east", "cripta", "capilla de Cómodo (oculto)")
    o.set(-23, H1, 14, "decorated_pot")
    o.lantern(-20, H1 + 2, 13)
    o.flight([(x, 12) for x in range(-12, -19, -1)], -13, "west", mat="quartz_stairs")
    room("pasillo bajo de Cómodo", -11, 0, 12, 12, H2, 2)
    o.carve_box(0, H2, 6, 0, H2 + 1, 11)
    room("cripta", -7, -5, 13, 15, H2, 3)
    o.spawner(-6, H2, 15, "skeleton", "esqueletos (cripta de Cómodo)")
    for y in range(H2, H1):           # pozo del puzle 1 (después de vaciar el despacho)
        o.carve(20, y, 7)
        o.set(20, y, 7, "ladder[facing=north]")


def champion():
    return piezas.guardian("husk", "heraldia.coliseo.campeon", "Campeón de la Arena", vida=40.0,
                           equipo={"mainhand": "iron_sword", "offhand": "shield", "head": "golden_helmet",
                                   "chest": "iron_chestplate", "legs": "chainmail_leggings", "feet": "iron_boots"},
                           caida={"mainhand": 0.25, "head": 0.5},
                           extra_atributos=[{"id": "minecraft:knockback_resistance", "base": 0.3},
                                            {"id": "minecraft:follow_range", "base": 24.0}])


def lining(o):
    """Paredes, suelos y techos del hipogeo en ladrillo de piedra; la cámara del tesoro en piedra negra pulida."""
    x0, x1, z0, z1, y0, y1 = HYP
    tc = o.rooms["cámara del tesoro"]
    rock = "minecraft:" + ROCK
    todo = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(y0, y1 + 1):
                if o.get(x, y, z) != rock:
                    continue
                for ax, ay, az in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    n = o.get(x + ax, y + ay, z + az)
                    if n is not None and not is_full(n):
                        todo.append((x, y, z))
                        break
    for x, y, z in todo:
        inside_tc = tc[0] - 1 <= x <= tc[1] + 1 and tc[2] - 1 <= z <= tc[3] + 1 and y <= -8
        o.set(x, y, z, "polished_blackstone_bricks" if inside_tc else LINING)


# ------------------------------------------------------------------ ruina
def ruin(o):
    """Tramo derrumbado al noroeste, cornisas rotas, muescas en la coronación y asientos sueltos."""
    rng = random.Random(23)
    w0, w1 = WEDGE
    wc, wh = (w0 + w1) / 2, (w1 - w0) / 2
    rubble = ["cobblestone", "cobblestone", "sandstone", "coarse_dirt", "coarse_dirt", "bricks"]
    for (dx, dz), c in COLS.items():
        r = c.r
        if r < 12 or r > 25:
            continue
        d = abs(c.u - wc)
        w = max(0.0, 1 - d / wh) if d < wh + 0.6 else 0.0
        w = min(1.0, w * 1.6) * (0.75 + 0.25 * noise(5, c.u * 4))
        if w <= 0.05:
            continue
        o.ruined.add((CX + dx, CZ + dz))
        if r >= 25:
            for y in (6, 12, 18, 24):
                o.set(dx, y, dz, "air")
            continue
        if r >= 22:
            top = round(24 - w * (24 - 13) + 3 * (noise(7, c.u * 6 + r) - 0.5))
            top = max(top, 13)
        else:
            target = 12 + (r - 12) * 0.25 + 2 * noise(9, c.u * 5 + r * 0.7)
            top = round(S(r) - w * (S(r) - target))
            if r >= 19:
                top = max(top, 12)
        for y in range(top + 1, 26 + 1):
            if o.get(dx, y, dz) not in (None, "minecraft:air"):
                o.set(dx, y, dz, "air")
        cur = o.get(dx, top, dz)
        if cur and cur != "minecraft:air" and w > 0.3 and r < 22:
            m = rng.choice(rubble)
            o.set(dx, top, dz, m)
            if m == "coarse_dirt" and rng.random() < 0.3:
                o.set(dx, top + 1, dz, "dead_bush")
    # cornisas y coronación fuera del tramo
    for (dx, dz), c in COLS.items():
        if c.r == 25:
            for i, y in enumerate((6, 12, 18, 24)):
                if noise(11 + i, c.u * 3) > 0.45 and o.get(dx, y, dz) != "minecraft:air":
                    o.set(dx, y, dz, "air")
        elif 22 <= c.r <= 24:
            n = noise(17, c.u * 2.5)
            if n > 0.5:
                o.set(dx, 24, dz, "air")
                o.set(dx, 25, dz, "air")
                o.set(dx, 26, dz, "air")
                if n > 0.8 and o.get(dx, 23, dz) == "minecraft:" + WALL:
                    o.set(dx, 23, dz, "air")
        elif c.r in SEAT_RINGS:
            s = S(c.r)
            st = o.get(dx, s, dz)
            if st and st.startswith("minecraft:" + SEAT) and rng.random() < 0.06:
                o.ruined.add((CX + dx, CZ + dz))
                o.set(dx, s, dz, "smooth_sandstone_slab[type=bottom]" if rng.random() < 0.5 else "air")


# ------------------------------------------------------------------ conexiones de muros, rejas y vallas
def connect(t):
    for (x, y, z), (st, nbt) in list(t.blocks.items()):
        bid, props = parse_state(st)
        b = bid.replace("minecraft:", "")
        fam = "wall" if b.endswith("_wall") else "bars" if b == "iron_bars" else "fence" if b.endswith("_fence") else None
        if not fam:
            continue
        con = {}
        for d, (ax, az) in OUT.items():
            n = t.get(x + ax, y, z + az)
            nb = n.split("[")[0] if n else ""
            ok = is_full(n) or (fam == "wall" and nb.endswith("_wall")) or (fam == "bars" and nb.endswith("iron_bars")) \
                or (fam == "fence" and nb.endswith("_fence"))
            con[d] = ok
        if fam == "wall":
            for d in OUT:
                props[d] = "low" if con[d] else "none"
            straight = (con["east"] and con["west"] and not con["north"] and not con["south"]) or \
                       (con["north"] and con["south"] and not con["east"] and not con["west"])
            above = t.get(x, y + 1, z)
            props["up"] = "false" if straight and above in (None, "minecraft:air") else "true"
            props["waterlogged"] = "false"
        else:
            for d in OUT:
                props[d] = "true" if con[d] else "false"
            props["waterlogged"] = "false"
        t.blocks[(x, y, z)] = (state_str(bid, props), nbt)


def drop_floating(o):
    """Tras la ruina, los fragmentos que quedan sin unión con el suelo de su pieza se caen (se quitan)."""
    from .._comun.recorrido import flotantes
    for p in flotantes({p: st for p, (st, _) in o.t.blocks.items()}, (0, HYP[4])):
        o.t.blocks[p] = ("minecraft:air", None)


# ------------------------------------------------------------------ montaje
JIG = (3, 0)       # (dx, dz) del conector vertical bajo la arena


def construir(ruina=True):
    from pack import fix_supports
    o = Obra()
    base(o)
    facade(o)
    galleries(o)
    tunnels(o)
    g1_to_g2(o)
    vomitoria(o)
    tabernae(o)
    palcos(o)
    terrace(o)
    hypogeum(o)
    west_stairs(o)
    lining(o)
    if ruina:
        ruin(o)
    connect(o.t)
    fix_supports(o.t)
    if ruina:
        drop_floating(o)
    main = Template("unicas/coliseo/coliseo")
    hyp = Template("unicas/coliseo/hipogeo")
    for (x, y, z), (st, nbt) in o.t.blocks.items():
        (main if y >= 0 else hyp).blocks[(x, y, z)] = (st, nbt)
    for e in o.t.entities:
        (main if e[1] >= 0 else hyp).entities.append(e)
    jx, jz = CX + JIG[0], CZ + JIG[1]
    main.jigsaw(jx, 0, jz, "down_south", "heraldia:coliseo_arriba", "heraldia:coliseo_hipogeo",
                "heraldia:unicas/coliseo/hipogeo", final_state="minecraft:sand")
    hyp.jigsaw(jx, -1, jz, "up_south", "heraldia:coliseo_hipogeo", "minecraft:empty", "minecraft:empty",
               final_state="minecraft:" + ROCK)
    offs = {}
    for t in (main, hyp):
        x0, y0, z0, *_ = t.bounds()
        offs[t.name] = (x0, y0, z0)
    return o, main, hyp, offs
