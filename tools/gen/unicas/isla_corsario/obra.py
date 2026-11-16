"""Construcción de la Isla del corsario en un único sistema de coordenadas (ver docs/unicas/isla_corsario.md).

x de oeste a este (0..W-1), z de norte a sur (0..D-1); y = 0 es la primera capa sobre el agua (el mar llega a y = -1)
y la plantilla baja hasta BASE, cuya fila se prolonga hasta el fondo al colocarse (HastaElSueloProcessor). El islote
trae su roca, su arena y sus palmeras: al norte y al este, un cerro con acantilados donde se alza el fuerte; al sur y al
oeste, playas, el puerto con el muelle y el bergantín, la taberna, los almacenes, la horca y el faro de la punta. Bajo
el cerro, las cuevas marinas (la ensenada oculta, la sala del mapa, la armería, los calabozos y la cámara del tesoro).
"""
import math, zlib
from core import Template
from .._comun import piezas
from .._comun.piezas import spawner, chest, text

SID = "isla_corsario"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
W, D = 112, 110
BASE = -18                      # fila inferior de la plantilla (se prolonga hasta el fondo)
CX, CZ, RX, RZ = 56, 48, 42, 37  # islote: superelipse (exponente 3) con la costa ondulada
PLAT = 7                        # suelo del fuerte (pies a 8)
HILL = (75, 28, 22, 19)         # meseta del fuerte: centro y semiejes (superelipse de exponente 4)
ARBOLES = 3                     # sin hierba (ni árboles) a menos de estos bloques de la obra
FUERTE = (60, 84, 24, 45)       # recinto del fuerte en la meseta: x0, x1, z0, z1 (muros incluidos)
PUEBLO = (24, 66, 52, 78)       # explanada del puerto (suelo a y = 1): x0, x1, z0, z1

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

ROCK = ["stone"] * 12 + ["andesite"] * 4 + ["tuff"] * 2
SB, MSB, CRSB, CSB = "stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks", "chiseled_stone_bricks"
COB, MCOB = "cobblestone", "mossy_cobblestone"
PL, LOG, SLOG = "spruce_planks", "spruce_log", "stripped_spruce_log"
DPL = "dark_oak_planks"


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def slab(m, typ="bottom"):
    return S(f"{m}_slab", type=typ, waterlogged=False)


def stairs(m, facing, half="bottom"):
    return S(f"{m}_stairs", facing=facing, half=half, shape="straight", waterlogged=False)


def h(*a):
    """Azar determinista en [0, 1) a partir de las coordenadas."""
    return zlib.crc32(",".join(map(str, a)).encode()) % 1000 / 1000.0


def forma(x, z):
    """Distancia normalizada a la costa (< 1 dentro del islote)."""
    dx, dz = (x - CX) / RX, (z - CZ) / RZ
    a = math.atan2(dz, dx)
    w = 1 + 0.07 * math.sin(3 * a + 3.93) + 0.045 * math.sin(5 * a + 2.1) + 0.03 * math.sin(9 * a + 0.3)
    return (abs(dx) ** 2.4 + abs(dz) ** 2.4) ** (1 / 2.4) / w


def fuera_cerro(x, z):
    """Bloques (aprox.) desde el borde de la meseta del cerro; 0 dentro."""
    hx, hz, rx, rz = HILL
    d = ((abs(x - hx) / rx) ** 4 + (abs(z - hz) / rz) ** 4) ** 0.25
    return max(0, int(round((d - 1) * min(rx, rz))))


def suelo(x, z):
    """Altura del bloque de superficie del islote en (x, z), o None si es mar."""
    d = forma(x, z)
    if d > 1:
        return None
    low = 0 if d > 0.86 else 1
    px0, px1, pz0, pz1 = PUEBLO
    if px0 <= x <= px1 and pz0 <= z <= pz1 and d <= 0.86:
        low = 1                                   # la explanada del puerto, a nivel
    e = fuera_cerro(x, z)
    hill = PLAT - (e * 3 + 1) // 2 if e else PLAT
    return max(low, hill)


def lecho(x, z):
    """Cima del talud bajo el agua (y < 0) fuera de la costa, o None lejos del islote."""
    d = forma(x, z)
    if d <= 1:
        return None
    k = (d - 1) * RX          # bloques (aprox.) desde la costa
    if k > 9:
        return None
    return max(BASE, -2 - int(k * 1.8))


class Obra:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/isla")
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # celdas que solo se alcanzan resolviendo un puzle
        self.secret = []           # celdas de salas ocultas sin puzle (tapices, nichos)
        self.mech = {}             # mecanismos para el simulador y la prueba de servidor
        self.ruin = set()          # posiciones dañadas a mano (estado de conservación)
        self.signs = []
        self.ground = {}           # (x, z) -> altura del bloque de superficie del islote
        self.lining = set()        # celdas de muro de las cuevas (no pueden ser roca natural)
        self.agua = set()          # agua de la plantilla (ensenada, canal)
        self.camino = set()        # celdas (x, z) de los caminos del islote
        self.natural = {}          # roca, arena y hierba del islote tal como salen de islote() (no cuentan como obra)

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def f(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def a(self, x1, y1, z1, x2, y2, z2):
        self.t.fill(x1, y1, z1, x2, y2, z2, "air")

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def free(self, x, y, z):
        st = self.get(x, y, z)
        return st is None or st == "minecraft:air"

    def chest(self, x, y, z, facing, tabla, kind="chest"):
        chest(self.t.set, x, y, z, facing, LOOT + tabla, kind)
        self.chests.append(((x, y, z), tabla))

    def spawner(self, x, y, z, mob, luz=None):
        spawner(self.t.set, x, y, z, mob, potentials=True, luz=luz)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z):
        self.s(x, y, z, S("lantern", hanging=True, waterlogged=False))

    def lamp(self, x, y, z):
        self.s(x, y, z, S("lantern", hanging=False, waterlogged=False))

    def door(self, x, y, z, facing, hinge="left", kind="spruce_door"):
        piezas.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="black"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="red"):
        """Cama con la cabecera hacia `facing` (la cabecera en x, z; los pies detrás)."""
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="spruce"):
        """Cartel traducible: `lines` = [(es, en)] (las claves van a LANG con el sufijo .1, .2...)."""
        self.signs.append((key, lines))
        piezas.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
                    wood=wood)

    def ruin_set(self, x, y, z, st="air"):
        self.s(x, y, z, st)
        self.ruin.add((x, y, z))

    def table(self, x, y, z, top="spruce_pressure_plate"):
        self.s(x, y, z, "spruce_fence")
        self.s(x, y + 1, z, top if top != "spruce_pressure_plate" else S(top, powered=False))

    def chair(self, x, y, z, back):
        self.s(x, y, z, stairs("spruce", back))

    def flight(self, x, z, y0, d, n, mat="cobblestone", width=1, support=COB, air=3):
        """Tramo de n peldaños que sube hacia d desde los pies y0 (el primer peldaño a y0). Despeja `air` bloques sobre
        cada peldaño y rellena el apoyo por debajo hasta y0 - 1."""
        dx, dz = DV[d]
        sx, sz = (dz != 0, dx != 0)
        for w in range(width):
            for i in range(n):
                X, Y, Z = x + dx * i + sx * w, y0 + i, z + dz * i + sz * w
                self.s(X, Y, Z, stairs(mat, d))
                self.a(X, Y + 1, Z, X, Y + air, Z)
                self.f(X, y0 - 1, Z, X, Y - 1, Z, support) if Y - 1 >= y0 - 1 else None

    def roca(self, x, y, z):
        return ROCK[int(h(x, y, z) * len(ROCK))]

    # ------------------------------------------------------------ islote
    def islote(self):
        """Roca del islote desde BASE hasta la superficie, arena en las playas, hierba tierra adentro, piedra en el cerro
        y talud de arena y grava bajo el agua alrededor."""
        for x in range(W):
            for z in range(D):
                g = suelo(x, z)
                if g is not None:
                    self.ground[(x, z)] = g
                    d = forma(x, z)
                    e = fuera_cerro(x, z)
                    for y in range(BASE, g + 1):
                        self.s(x, y, z, self.roca(x, y, z))
                    if g == 0 and e > 1:
                        top = "sand"
                        for y in range(-3, 1):
                            self.s(x, y, z, "sand" if y > -3 else "sandstone")
                    elif e == 0 or g >= 3:
                        top = None                      # el cerro: roca, y hierba solo en la meseta
                        if e == 0 and d < 0.93:
                            self.s(x, g, z, "grass_block[snowy=false]")
                            self.s(x, g - 1, z, "dirt")
                        elif h(x, z, 7) < 0.25:
                            self.s(x, g, z, "gravel" if self.get(x, g - 1, z) else "stone")
                    else:
                        self.s(x, g, z, "grass_block[snowy=false]")
                        self.s(x, g - 1, z, "dirt")
                        if d > 0.8:
                            self.s(x, g, z, "sand")
                    continue
                top = lecho(x, z)
                if top is None:
                    continue
                for y in range(BASE, top + 1):
                    self.s(x, y, z, self.roca(x, y, z))
                self.s(x, top, z, "sand" if h(x, z, 3) < 0.7 else "gravel")
                if self.get(x, top - 1, z) and top - 1 >= BASE:
                    self.s(x, top - 1, z, "sandstone" if h(x, z, 4) < 0.5 else self.roca(x, top - 1, z))

    def fin_islote(self):
        """Recuerda el estado natural de cada celda del islote (para no contarla como obra en el estado de conservación)."""
        self.natural = {p: st for p, (st, _) in self.t.blocks.items()}

    def build(self):
        from . import fuerte, cuevas, puerto
        self.islote()
        self.fin_islote()
        fuerte.construir(self)
        puerto.construir(self)
        cuevas.Cuevas(self).construir()
        self.sin_arboles()
        piezas.connect(self.t)
        return self

    def obra_columnas(self):
        """Columnas (x, z) con obra por encima del suelo del islote (sin contar las palmeras)."""
        out = set()
        for (x, y, z), (st, _) in self.t.blocks.items():
            g = self.ground.get((x, z))
            if g is not None and y > g and self.natural.get((x, y, z)) != st and \
                    not any(k in st for k in ("jungle_", "cocoa", ":air")):
                out.add((x, z))
        return out

    def sin_arboles(self):
        """Los océanos tienen sus robles (trees_water) y su hierba: nacen sobre la hierba del islote. A menos de
        ARBOLES bloques de la obra el suelo es tierra pisada (tierra de camino), donde no nace nada: ningún árbol
        tapa una puerta ni crece contra un muro; en el resto de la isla, la hierba puede dar algún roble."""
        cols = self.obra_columnas()
        r = ARBOLES
        for (x, z), g in self.ground.items():
            st = self.get(x, g, z)
            if st != "minecraft:grass_block[snowy=false]":
                continue
            if any((x + a, z + b) in cols for a in range(-r, r + 1) for b in range(-r, r + 1)):
                self.s(x, g, z, "dirt_path")
