"""Modelo de la catedral en un único sistema de coordenadas.

x: eje de la nave (fachada oeste en x=6, ábside hacia +x); z: anchura (eje de simetría z=30); y=0: suelo
(pies del jugador en y=1); y<0: cripta (pieza aparte). Se construye la mitad norte (z<=30), se refleja y se
añaden las partes asimétricas (sacristía y biblioteca al norte, claustro al sur, cripta, mecanismos, ruina)."""
import math
from core import Template
from .base import *
from .._comun import piezas

NAVE_POSTS = [17, 23, 29, 35, 41, 47, 53, 59]
CHOIR_POSTS = [71, 77, 83, 89]
PIER_A = [-90, -54, -18, 18, 54, 90]
OPEN_A = [-72, -36, 0, 36, 72]
CHAPEL_A = [-36, 0, 36]
BUTT_A = [-54, -18, 18, 54]
TOWER_FLOORS = [0, 11, 16, 27, 39, 55]
RING = piezas.SLAB_RING


def vault(r):
    """Cota del intradós de la bóveda según la distancia al eje (0..5)."""
    return {5: 23, 4: 25, 3: 26}.get(r, 27 if r <= 2 else 22)


def roofh(r):
    """Cota superior de la cubierta (pendiente 2:1) según la distancia al caballete (0..6)."""
    return 40 - 2 * r


def bay(x):
    """(u, anchura, índice de tramo) o None si x es un pilar."""
    posts = NAVE_POSTS if x <= 59 else CHOIR_POSTS
    if x in posts or x < posts[0] or x > posts[-1]:
        return None
    p = max(q for q in posts if q < x)
    n = min(q for q in posts if q > x)
    return x - p - 1, n - p - 1, posts.index(p) + (0 if x <= 59 else 10)


class Catedral:
    def __init__(self):
        self.t = Template("unicas/catedral/_mundo")
        self.chests = []        # (pos, tabla, nombre del sitio)
        self.spawners = []      # (pos, criatura)
        self.mech = []          # mecanismos de redstone
        self.ruin = set()       # posiciones con daño de ruina explícito
        self.flights = set()    # peldaños de escaleras transitables
        self.entities = []

    # ------------------------------------------------------------------ primitivas
    def set(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def fill(self, x1, y1, z1, x2, y2, z2, st):
        if y2 >= y1:                       # un intervalo vacío (y2 < y1) no coloca nada
            self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def air(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, "air")

    def chest(self, x, y, z, facing, tabla, sitio, kind="chest"):
        loot = f"heraldia:unicas/catedral/{tabla}"
        if kind == "barrel":
            self.t.barrel(x, y, z, facing, loot)
        else:
            self.t.chest(x, y, z, facing, loot)
        self.chests.append(((x, y, z), tabla, sitio))

    def hang(self, x, y, z, top, soul=False):
        """Farol colgado en y con cadena hasta el bloque de la cota top (excluido)."""
        for yy in range(y + 1, top):
            self.set(x, yy, z, "iron_chain[axis=y]")
        self.set(x, y, z, s("soul_lantern" if soul else "lantern", hanging=True))

    def lamp(self, x, y, z, soul=False):
        self.set(x, y, z, s("soul_lantern" if soul else "lantern", hanging=False))

    def candles(self, x, y, z, n=3):
        self.set(x, y, z, s("candle", candles=n, lit=True))

    def door(self, x, y, z, facing, hinge="left", wood="dark_oak"):
        self.set(x, y, z, s(f"{wood}_door", facing=facing, half="lower", hinge=hinge, open=False, powered=False))
        self.set(x, y + 1, z, s(f"{wood}_door", facing=facing, half="upper", hinge=hinge, open=False, powered=False))

    def stair_flight(self, cells):
        for (x, y, z, st) in cells:
            self.set(x, y, z, st)
            self.flights.add((x, y, z))

    def spiral(self, cx, cz, start, k_max, y0=0, mat="stone_brick"):
        steps = piezas.spiral_slabs(self.set, cx, cz, y0 + 0.5, y0 + 0.5 * (k_max + 1), start, f"{mat}_slab",
                                    ring=piezas.SLAB_RING, props="")
        self.flights.update((x, piezas.slab_y(sv)[0], z) for (_, x, z, sv) in steps)

    # ------------------------------------------------------------------ cuerpo simétrico (mitad norte)
    def build_symmetric(self):
        for x in range(18, 90):
            if 59 <= x <= 71:
                continue
            for z in range(13, 31):
                self.rect_column(x, z, 30 - z)
        for x in range(90, 108):
            for z in range(13, 31):
                self.polar_column(x, z)
        for x in range(57, 74):
            for z in range(5, 31):
                self.transept_column(x, z)
        self.towers()
        self.narthex()
        self.buttresses()
        self.chapels()
        self.parvis()
        self.crypt_stairs()

    def window_glass(self, k):
        return GLASS[k % len(GLASS)]

    def rect_column(self, x, z, r):
        b = bay(x)
        post = b is None
        u, w, k = b if b else (0, 0, 0)
        mid = (w - 1) // 2
        nave_part = x <= 58
        if r <= 5:
            self.set(x, 0, z, PA if (x + z) % 2 else PD)
            U = vault(r)
            self.air(x, 1, z, x, U - 1, z)
            self.fill(x, U, z, x, 27, z, PA if post else SB)
            H = roofh(r)
            self.air(x, 28, z, x, H - 3, z)
            self.fill(x, H - 2, z, x, H, z, ROOF)
        elif r == 6:
            self.fill(x, 0, z, x, 27, z, SB)
            self.set(x, 0, z, PA)
            if post:
                self.fill(x, 1, z, x, 10, z, PA)
                self.set(x, 1, z, CSB)
                self.set(x, 10, z, CSB)
            else:
                self.air(x, 1, z, x, 7, z)
                if 1 <= u <= w - 2:
                    self.set(x, 8, z, "air")
                if u == mid:
                    self.set(x, 9, z, "air")
                if 1 <= u <= w - 2:
                    self.set(x, 12, z, WALLB)
                    self.air(x, 13, z, x, 14, z)
                if u == mid:
                    self.set(x, 15, z, "air")
                if 1 <= u <= w - 2:
                    self.fill(x, 18, z, x, 21, z, self.window_glass(k))
                if u == mid:
                    self.set(x, 22, z, self.window_glass(k))
            if nave_part:
                self.set(x, 27, z, SB)          # pasillo de canalón (pies en 28)
            else:
                self.set(x, 28, z, ROOF)        # alero del coro
        elif r <= 11:
            self.set(x, 0, z, PA)
            self.air(x, 1, z, x, 10, z)
            self.set(x, 11, z, PA if post else SB)
            self.air(x, 12, z, x, 15, z)
            self.set(x, 16, z, SM)
            if r == 7 and nave_part:
                self.set(x, 27, z, stairs("stone_brick", "south", "top"))     # cornisa bajo el pretil del canalón
                self.set(x, 28, z, WALLB)
        elif r == 12:
            self.fill(x, 0, z, x, 16, z, SB)
            self.set(x, 0, z, PA)
            self.set(x, 17, z, WALLB)
            if not post:
                if 1 <= u <= w - 2:
                    self.fill(x, 3, z, x, 8, z, self.window_glass(k + 1))
                if u == mid:
                    self.set(x, 9, z, self.window_glass(k + 1))
                    self.fill(x, 13, z, x, 14, z, "white_stained_glass_pane")
            else:
                self.set(x, 17, z, CSB)

    def polar_column(self, x, z):
        d, a = polar(x, z)
        if a > 0.01 or d > 12.5:
            return
        ri = min(5, int(round(d)))
        dp = min(angdist(a, p) for p in PIER_A)
        dc = min(angdist(a, c) for c in OPEN_A)
        k = int(round((a + 90) / 36))
        if d <= 5.5:
            self.set(x, 0, z, PA if (x + z) % 2 else PD)
            U = vault(ri)
            self.air(x, 1, z, x, U - 1, z)
            self.fill(x, U, z, x, 27, z, SB)
            H = int(round(40 - 2 * d))
            self.air(x, 28, z, x, H - 4, z)
            self.fill(x, max(28, H - 3), z, x, H, z, ROOF)
        elif d <= 6.5:
            self.fill(x, 0, z, x, 27, z, SB)
            self.set(x, 0, z, PA)
            self.set(x, 28, z, ROOF)
            if dp < 6:
                self.fill(x, 1, z, x, 10, z, PA)
                self.set(x, 1, z, CSB)
                self.set(x, 10, z, CSB)
            else:
                self.air(x, 1, z, x, 7, z)
                if dp >= 11:
                    self.set(x, 8, z, "air")
                if dp >= 15:
                    self.set(x, 9, z, "air")
                if dp >= 9:
                    self.set(x, 12, z, WALLB)
                    self.air(x, 13, z, x, 14, z)
                    self.fill(x, 18, z, x, 21, z, self.window_glass(k))
                if dp >= 15:
                    self.set(x, 15, z, "air")
                    self.set(x, 22, z, self.window_glass(k))
        elif d <= 11.5:
            self.set(x, 0, z, PA)
            self.air(x, 1, z, x, 10, z)
            self.set(x, 11, z, SB)
            self.air(x, 12, z, x, 15, z)
            self.set(x, 16, z, SM)
        else:
            self.fill(x, 0, z, x, 16, z, SB)
            self.set(x, 0, z, PA)
            self.set(x, 17, z, WALLB)
            if dc <= 8 and min(angdist(a, c) for c in CHAPEL_A) > 12:
                self.fill(x, 3, z, x, 8, z, self.window_glass(k + 1))
                if dc <= 4:
                    self.set(x, 9, z, self.window_glass(k + 1))
                    self.fill(x, 13, z, x, 14, z, "white_stained_glass_pane")

    def transept_column(self, x, z):
        rx, r = abs(x - 65), 30 - z
        if rx > 6:
            # esquinas del brazo: contrafuertes diagonales del hastial
            if rx == 7 and r in (22, 23):
                self.fill(x, 0, z, x, 22, z, SB)
                self.set(x, 23, z, CSB)
                self.set(x, 24, z, WALLB)
                self.set(x, 25, z, WALLB)
            return
        if r <= 5:
            self.set(x, 0, z, PA if (x + z) % 2 else PD)
            U = max(vault(r), vault(rx)) if rx <= 5 else vault(r)
            self.air(x, 1, z, x, U - 1, z)
            self.fill(x, U, z, x, 27, z, SB)
            H = max(roofh(r), roofh(min(rx, 6)))
            self.air(x, 28, z, x, H - 3, z)
            self.fill(x, H - 2, z, x, H, z, ROOF)
            return
        if r in (6, 7) and rx in (5, 6):
            self.fill(x, 0, z, x, 27, z, PA)          # pilar del crucero
            self.set(x, 1, z, CSB)
            self.set(x, 10, z, CSB)
            self.set(x, 22, z, CSB)
            self.set(x, 28, z, ROOF)
            return
        if rx == 6:
            if r <= 12:
                # el colateral desemboca en el brazo; encima, muro con el paso de la pasarela alta
                self.set(x, 0, z, PA)
                self.air(x, 1, z, x, 10, z)
                self.set(x, 11, z, SB)
                self.fill(x, 12, z, x, 27, z, SB)
                self.set(x, 28, z, ROOF)
                if r == 12:
                    self.fill(x, 0, z, x, 27, z, SB)
                if 8 <= r <= 10:
                    self.air(x, 12, z, x, 14, z)
                return
            if r <= 21:
                self.fill(x, 0, z, x, 27, z, SB)
                self.set(x, 28, z, ROOF)
                if z in (10, 11, 12, 14, 15, 16) and not (x == 71 and 11 <= z <= 17):
                    lo = 3
                    if z in (11, 15):
                        self.fill(x, 3, z, x, 9, z, self.window_glass(z))
                        self.fill(x, 17, z, x, 23, z, self.window_glass(z + 1))
                    else:
                        self.fill(x, lo, z, x, 8, z, self.window_glass(z))
                        self.fill(x, 17, z, x, 22, z, self.window_glass(z + 1))
                return
            # r 22..23: esquina del hastial
            self.fill(x, 0, z, x, 28, z, SB)
            return
        # rx <= 5: interior del brazo o del crucero
        if r <= 21:
            self.set(x, 0, z, PA if (x + z) % 2 else PD)
            U = vault(rx)
            self.air(x, 1, z, x, U - 1, z)
            self.fill(x, U, z, x, 27, z, SB)
            H = roofh(rx)
            self.air(x, 28, z, x, H - 3, z)
            self.fill(x, H - 2, z, x, H, z, ROOF)
            return
        # hastial del brazo (z = 7..8): muro de dos capas hasta la cubierta, rosetón y portada
        H = roofh(rx)
        self.fill(x, 0, z, x, H, z, SB)
        cy, rr = 18.5, 5.6
        dd = math.hypot(rx, 0)
        for y in range(12, 26):
            dist = math.hypot(x - 65, y - cy)
            if dist <= rr:
                self.set(x, y, z, self.rose_cell(x - 65, y - cy, dist, True))
        if rx <= 1:
            self.air(x, 1, z, x, 2, z)
            self.fill(x, 3, z, x, 6, z, CSB)
            if z == 7:
                if rx == 0:
                    self.fill(x, 1, z, x, 2, z, CSB)
                else:
                    self.door(x, 1, z, "south", "left" if x > 65 else "right")
                self.set(x, 0, 6, stairs("stone_brick", "south"))
                if rx == 1:
                    self.set(x + (1 if x > 65 else -1), 0, 6, stairs("stone_brick", "south"))

    def rose_cell(self, dx, dy, dist, outer):
        """Celda de un rosetón: tracería radial de piedra y vidrieras en la capa exterior."""
        if not outer:
            return "air"
        if dist > 4.8 or dist < 1.0:
            return CSB
        ang = math.degrees(math.atan2(dy, dx)) % 45
        if ang < 6 or ang > 39:
            return SB
        if 2.4 < dist < 3.0:
            return SB
        return "red_stained_glass_pane" if dist < 2.4 else ("blue_stained_glass_pane" if int(dist * 2) % 2 else "purple_stained_glass_pane")

    # ------------------------------------------------------------------ torres
    def towers(self):
        x0, x1, z0, z1 = 6, 17, 12, 23
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                wall = x <= 7 or x >= 16 or z <= 13 or z >= 22
                if wall:
                    self.fill(x, 0, z, x, 55, z, SB)
                else:
                    self.set(x, 0, z, PA)
                    self.air(x, 1, z, x, 54, z)
                    for f in TOWER_FLOORS[1:]:
                        self.set(x, f, z, SB if f != 55 else SM)
        # pretil almenado y pináculos de esquina
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    self.set(x, 56, z, WALLB if (x + z) % 2 else SB)
        for (x, z) in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            self.fill(x, 56, z, x, 58, z, SB)
            self.set(x, 59, z, CSB)
            self.set(x, 60, z, WALLB)
        # torreta de la escalera de caracol (esquina noroeste del interior)
        tx0, tz0 = 8, 14
        self.fill(tx0, 0, tz0, tx0 + 4, 58, tz0 + 4, SB)
        self.air(tx0 + 1, 1, tz0 + 1, tx0 + 3, 58, tz0 + 3)
        self.fill(tx0 + 1, 0, tz0 + 1, tx0 + 3, 0, tz0 + 3, PA)
        self.fill(10, 0, 16, 10, 58, 16, SB)
        self.spiral(10, 16, start=0, k_max=110)
        for k in range(4, 110, 12):                       # antorchas en el núcleo, a la altura de la cabeza
            dx, dz = RING[k % 8]
            if dx == 0 or dz == 0:
                y = int(0.5 * (k + 1)) + 2
                f = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]
                self.set(10 + dx, y, 16 + dz, s("wall_torch", facing=f))
        for x in range(tx0, tx0 + 5):
            for z in range(tz0, tz0 + 5):
                d = max(abs(x - 10), abs(z - 16))
                self.set(x, 59, z, ROOF if d == 2 else SB)
                if d <= 1:
                    self.set(x, 60, z, ROOF)
        self.set(10, 61, 16, s("lightning_rod", facing="up"))
        for f in (1, 12, 17, 28, 40):
            self.air(12, f, 16, 12, f + 1, 16)               # puerta este de la torreta
        self.air(10, 56, 18, 10, 57, 18)                       # salida a la azotea
        # puertas de las estancias
        self.air(6, 1, 19, 7, 2, 20)                           # portada lateral
        self.door(6, 1, 19, "east", "left")
        self.door(6, 1, 20, "east", "right")
        self.fill(6, 4, 18, 6, 6, 21, CSB)
        for f in (1, 12, 17):
            self.air(16, f, 20, 17, f + 1, 20)                 # al colateral, al triforio y a la terraza
        for f in (1, 12, 28):
            self.air(12, f, 22, 12, f + 1, 23)                 # al nártex, a la tribuna y a la terraza de la fachada
        # ventanas en saetera
        for (y0, y1) in ((4, 8), (13, 14), (19, 24), (30, 36)):
            if y0 != 4:
                self.fill(6, y0, 20, 7, y1, 20, "white_stained_glass_pane")
            self.fill(14, y0, 12, 14, y1, 13, "white_stained_glass_pane")
        # campanario: vanos altos con celosía en las cuatro caras
        for y in range(42, 52):
            for (x, z) in ((6, 20), (6, 21), (13, 12), (14, 12), (17, 19), (17, 20), (13, 23), (14, 23)):
                self.set(x, y, z, "iron_bars")
            for (x, z) in ((7, 20), (7, 21), (13, 13), (14, 13), (16, 19), (16, 20), (13, 22), (14, 22)):
                self.set(x, y, z, "air")

    # ------------------------------------------------------------------ nártex, tribuna y fachada
    def narthex(self):
        for x in range(6, 18):
            for z in range(24, 31):
                r = 30 - z
                if x <= 7:
                    self.fill(x, 0, z, x, 27, z, SB)
                    continue
                self.set(x, 0, z, PA if (x + z) % 2 else PD)
                U = vault(min(r, 6)) if r <= 5 else 22
                self.air(x, 1, z, x, U - 1, z)
                self.fill(x, U, z, x, 26, z, SB)
                self.set(x, 27, z, SM)
                if x <= 15:
                    self.set(x, 11, z, SB)
                    self.set(x, 10, z, stairs("stone_brick", "west" if x == 15 else "south", "top") if x == 15 else SB)
        for z in range(24, 31):
            self.set(15, 12, z, WALLB)
        # portada central: dos hojas a cada lado del parteluz
        self.air(6, 1, 28, 7, 2, 30)
        self.door(6, 1, 28, "east", "left")
        self.door(6, 1, 29, "east", "right")
        self.fill(6, 1, 30, 7, 2, 30, CSB)
        self.fill(6, 3, 27, 6, 9, 30, CSB)
        for z in range(24, 28):
            self.set(6, 9, z, stairs("stone_brick", "east", "bottom"))
        # galería de los reyes: hornacinas ciegas
        for z in range(24, 31, 2):
            self.set(6, 11, z, WALLB)
            self.set(6, 10, z, CSB)
            self.set(6, 12, z, CSB)
        # rosetón occidental
        cy, rr = 19.5, 5.6
        for z in range(24, 31):
            for y in range(13, 27):
                dist = math.hypot(z - 30, y - cy)
                if dist <= rr:
                    self.set(6, y, z, self.rose_cell(z - 30, y - cy, dist, True))
                    self.set(7, y, z, self.rose_cell(z - 30, y - cy, dist, True))
        # galería superior abierta y terraza entre torres (pies en 28)
        for z in range(24, 31):
            self.set(6, 28, z, WALLB if z % 2 else PA)
            for y in range(29, 34):
                if z % 2 == 0:
                    self.set(6, y, z, PA)
            self.set(6, 33, z, SB)
            self.set(6, 34, z, CSB)
            self.set(7, 34, z, slab("stone_brick", "bottom"))
        # hastial de la nave sobre la terraza, con puerta al desván
        for z in range(25, 31):
            r = 30 - z
            self.fill(17, 28, z, 17, roofh(r) - 1, z, SB)
        self.air(17, 28, 30, 17, 29, 30)

    # ------------------------------------------------------------------ contrafuertes y arbotantes
    def buttress(self, cells_out, cells_arch):
        """cells_out: [(x, z, t)] con t = distancia (13..16); cells_arch: [(x, z, y)]."""
        hgt = {13: 17, 14: 14, 15: 11, 16: 8}
        for (x, z, tt) in cells_out:
            h = hgt[tt]
            self.fill(x, 0, z, x, h, z, SB)
            if tt == 13:
                self.fill(x, h + 1, z, x, h + 3, z, SB)
                self.set(x, h + 4, z, CSB)
                self.set(x, h + 5, z, WALLB)
                self.set(x, h + 6, z, WALLB)
        for (x, z, y) in cells_arch:
            if self.get(x, y, z) in (None, "minecraft:air"):
                self.set(x, y, z, SB)
            if self.get(x, y + 1, z) in (None, "minecraft:air"):
                self.set(x, y + 1, z, SB)

    def buttresses(self):
        for x in NAVE_POSTS[1:-1] + CHOIR_POSTS[1:]:
            outs = [(x, 30 - tt, tt) for tt in (13, 14, 15, 16)]
            arch = [(x, 30 - r, 19 + (12 - r)) for r in range(7, 13)]
            self.buttress(outs, arch)
        for a in BUTT_A:
            if a > 0:
                continue
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            outs, seen = [], set()
            t = 12.6
            while t <= 16.5:
                p = (int(round(AX + t * ca)), int(round(AZ + t * sa)))
                if p not in seen:
                    seen.add(p)
                    outs.append((p[0], p[1], min(16, max(13, int(round(t))))))
                t += 0.2
            arch, seen, last = [], set(), None
            t = 12.5
            while t >= 6.6:
                p = (int(round(AX + t * ca)), int(round(AZ + t * sa)))
                y = 19 + int(round(12.5 - t))
                if p not in seen:
                    seen.add(p)
                    if last and last[0] != p[0] and last[1] != p[1]:
                        arch.append((p[0], last[1], y))      # celda de unión: sin ella el arco solo se toca por aristas
                    arch.append((p[0], p[1], y))
                    last = p
                t -= 0.2
            self.buttress(outs, arch)

    # ------------------------------------------------------------------ capillas radiales
    def chapel_center(self, a):
        return AX + 15 * math.cos(math.radians(a)), AZ + 15 * math.sin(math.radians(a))

    def chapels(self):
        for a in CHAPEL_A:
            if a > 0:
                continue
            cx, cz = self.chapel_center(a)
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            for x in range(int(cx) - 5, int(cx) + 6):
                for z in range(int(cz) - 5, min(31, int(cz) + 6)):
                    dc = math.hypot(x - cx, z - cz)
                    if dc <= 3.6:
                        self.fill(x, 0, z, x, 9, z, SB)
                        self.set(x, 10, z, ROOF if dc > 1.6 else CSB)
                        if dc <= 2.6:
                            self.set(x, 0, z, PA)
                            self.air(x, 1, z, x, 7, z)
                            if dc <= 1.6:
                                self.set(x, 8, z, "air")
            # paso desde la girola
            for x in range(int(cx) - 6, int(cx) + 6):
                for z in range(int(cz) - 6, min(31, int(cz) + 6)):
                    d, aa = polar(x, z)
                    if 11.0 <= d <= 13.2 and angdist(aa, a) * math.pi / 180 * d <= 1.3:
                        self.set(x, 0, z, PA)
                        self.air(x, 1, z, x, 7, z)
            # ventana al exterior en el eje
            wx, wz = int(round(cx + 3.1 * ca)), int(round(cz + 3.1 * sa))
            self.fill(wx, 3, wz, wx, 6, wz, self.window_glass(int(a)))

    # ------------------------------------------------------------------ atrio y escalinata
    def parvis(self):
        for x in range(0, 6):
            for z in range(10, 31):
                if x == 0 or z == 10:
                    f = "east" if x == 0 else "south"
                    self.set(x, 0, z, stairs("stone_brick", f))
                else:
                    self.set(x, 0, z, SB if (x + z) % 3 else PA)

    # ------------------------------------------------------------------ escalera a la cripta (brazo norte)
    def crypt_stairs(self):
        for k in range(8):
            z = 14 + k
            for x in range(64, 67):
                self.set(x, -k, z, stairs("polished_andesite", "north"))
                self.flights.add((x, -k, z))
                if k >= 1:
                    self.fill(x, -k - 1, z, x, -k - 1, z, SB)
                for y in range(-k + 1, 0 if k >= 3 else 1):
                    self.set(x, y, z, "air")
        for z in range(14, 23):
            self.fill(63, -8, z, 63, -1, z, SB)
            self.fill(67, -8, z, 67, -1, z, SB)
        for z in range(15, 18):
            self.set(63, 1, z, WALLB)
            self.set(67, 1, z, WALLB)
        for x in range(64, 67):
            self.set(x, 1, 17, WALLB)
