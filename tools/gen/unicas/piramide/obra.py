"""Construcción del Templo-pirámide en coordenadas globales (y >= 0 superficie, y < 0 subsuelo)."""
import zlib
from core import Template, B, F, OPP
from unicas._comun import piezas

CX, CZ = 30, 42                 # eje de la pirámide
W, D = 79, 70                   # huella: x 0..78, z 0..69
UG = (8, 0, 52, 64)             # caja del subsuelo: x 8..52, z 0..64
UG_Y = (-27, -1)
AIR_TOP, AIR_TOP_PYR = 20, 36

LOOT = "heraldia:unicas/piramide/"
MASS = {"sup": "tuff", "sub": "stone"}
LINING = {   # zona: (pared, suelo, techo)
    "pir": ("tuff_bricks", "polished_tuff", "tuff_bricks"),
    "l1": ("stone_bricks", "stone_bricks", "stone_bricks"),
    "cen": ("stone", "stone", "stone"),
    "l3": ("deepslate_tiles", "polished_deepslate", "deepslate_bricks"),
}
DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def h(*a):
    return zlib.crc32(repr(a).encode()) % 1000 / 1000.0


class Obra:
    def __init__(self):
        self.t = Template("unicas/piramide/_global")
        self.carved = {}            # celda -> zona (aire interior)
        self.ext_air = set()        # aire exterior explícito
        self.marks = {}             # nombre -> [celdas]
        self.sealed = set()         # tapiado que se rompe (pasable en la auditoría)
        self.puzzle = []            # bloques de la puerta secreta
        self.water_dive = set()     # agua por la que se bucea
        self.ruin = set()           # ruina hecha a mano (para la fracción de buen estado)
        self.collapse = set()       # aire del derrumbe: el núcleo de toba queda a la vista

    # ------------------------------------------------------------ básicos
    def set(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def fill(self, x0, y0, z0, x1, y1, z1, st):
        self.t.fill(x0, y0, z0, x1, y1, z1, st)

    def carve(self, x0, y0, z0, x1, y1, z1, zone):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, "air")
                    self.carved[(x, y, z)] = zone

    def mark(self, name, *pos):
        self.marks.setdefault(name, []).append(tuple(pos))

    def chest(self, x, y, z, facing, table, name):
        piezas.chest(self.set, x, y, z, facing, LOOT + table)
        self.mark("cofre:" + name, x, y, z)

    def spawner(self, x, y, z, mob, name):
        piezas.spawner(self.set, x, y, z, mob)
        self.mark("generador:" + name, x, y, z)

    def flight(self, axis, lo, hi, u0, d, w0, n, zone, st="tuff_brick_stairs"):
        """Tramo que baja n peldaños desde la cota w0 avanzando en el eje (x|z) con sentido d (+1/-1).
        lo..hi es el ancho en el otro eje. Devuelve la coordenada del último peldaño."""
        name = {("z", 1): "south", ("z", -1): "north", ("x", 1): "east", ("x", -1): "west"}[(axis, d)]
        face = OPP[name]
        for i in range(1, n + 1):
            u, s = u0 + d * i, w0 - i + 1          # el primer peldaño queda a ras del rellano
            for v in range(lo, hi + 1):
                x, z = (v, u) if axis == "z" else (u, v)
                self.carve(x, s, z, x, s + 2, z, zone)
                self.set(x, s - 1, z, f"{st}[facing={face},half=bottom,shape=straight,waterlogged=false]")
        return u0 + d * n

    def up_flight(self, axis, lo, hi, u0, d, w0, n, st, clear_to=None):
        """Escalera exterior que sube n peldaños desde la cota w0 (relleno macizo debajo)."""
        name = {("z", 1): "south", ("z", -1): "north", ("x", 1): "east", ("x", -1): "west"}[(axis, d)]
        for i in range(n):
            u, s = u0 + d * i, w0 + i
            for v in range(lo, hi + 1):
                x, z = (v, u) if axis == "z" else (u, v)
                for yy in range(w0 - 1, s):
                    self.set(x, yy, z, "tuff_bricks")
                self.set(x, s, z, f"{st}[facing={name},half=bottom,shape=straight,waterlogged=false]")
                for yy in range(s + 1, max(s + 4, (clear_to or 0) + 1)):
                    cur = self.get(x, yy, z)
                    if cur and cur != "minecraft:air":
                        self.set(x, yy, z, "air")


# ====================================================================== superficie
def tiers(o):
    for k in range(6):
        hf, b = 24 - 3 * k, 4 * k
        o.fill(CX - hf, b, CZ - hf, CX + hf, b + 3, CZ + hf, "tuff")
    for k in range(6):
        hf, b = 24 - 3 * k, 4 * k
        for x in range(CX - hf, CX + hf + 1):
            for z in range(CZ - hf, CZ + hf + 1):
                dx, dz = x - CX, z - CZ
                m = max(abs(dx), abs(dz))
                corner = abs(dx) == abs(dz) == hf
                if m == hf:
                    if corner:
                        o.fill(x, b, z, x, b + 3, z, "polished_tuff")
                        continue
                    inward = "south" if dz == -hf else "north" if dz == hf else "east" if dx == -hf else "west"
                    o.set(x, b, z, f"tuff_brick_stairs[facing={inward},half=bottom,shape=straight,waterlogged=false]")
                    o.set(x, b + 1, z, "polished_tuff")
                    o.set(x, b + 2, z, "air")
                    o.ext_air.add((x, b + 2, z))
                    o.set(x, b + 3, z, "polished_tuff")
                elif m == hf - 1 and not (abs(dx) == abs(dz)):
                    along = dx if abs(dz) == hf - 1 else dz
                    o.set(x, b + 2, z, "chiseled_tuff_bricks" if along % 3 == 0 else "tuff_bricks")
                if k < 5 and hf - 2 <= m <= hf - 1 and b + 3 >= 0:
                    o.set(x, b + 3, z, "tuff_bricks")
    # cima
    for x in range(CX - 9, CX + 10):
        for z in range(CZ - 9, CZ + 10):
            if max(abs(x - CX), abs(z - CZ)) < 9:
                o.set(x, 23, z, "chiseled_tuff" if (x - CX) % 4 == 0 and (z - CZ) % 4 == 0 else "polished_tuff")


def stair_ramp(o):
    """Escalinata norte con alfardas y cabezas de serpiente."""
    for s in range(1, 24):
        z = CZ - 32 + s
        for x in range(CX - 5, CX + 6):
            for y in range(0, s):
                o.set(x, y, z, "tuff_bricks")
            if abs(x - CX) <= 4:
                o.set(x, s, z, "tuff_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
                top = s + 1
            else:
                o.set(x, s, z, "tuff_bricks")
                o.set(x, s + 1, z, "polished_tuff")
                top = s + 2
            for y in range(top, 30):
                cur = o.get(x, y, z)
                if cur and cur != "minecraft:air":
                    o.set(x, y, z, "air")
    for x in (CX - 5, CX + 5):
        o.set(x, 1, CZ - 32, "chiseled_tuff_bricks")
        o.set(x, 2, CZ - 32, "chiseled_tuff_bricks")
        o.set(x, 1, CZ - 33, "tuff_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
        o.set(x, 2, CZ - 33, "tuff_brick_slab[type=top,waterlogged=false]")
    # alfarda este mellada (ruina)
    for s in (14, 15, 16):
        z = CZ - 32 + s
        o.set(CX + 5, s + 1, z, "air")
        o.ruin.add((CX + 5, s, z))


def temple(o):
    x0, x1, z0, z1 = CX - 6, CX + 6, CZ - 5, CZ + 5
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            for y in range(24, 30):
                if corner:
                    st = "chiseled_tuff"
                elif edge:
                    st = "polished_tuff" if y == 24 else "chiseled_tuff_bricks" if y == 29 else "red_terracotta"
                else:
                    st = "polished_tuff" if y == 29 else "air"
                o.set(x, y, z, st)
            o.set(x, 30, z, "tuff_bricks")
    # interior
    o.carve(x0 + 1, 24, z0 + 1, x1 - 1, 28, z1 - 1, "pir")
    o.fill(x0 + 1, 24, CZ - 1, x1 - 1, 28, CZ - 1, "red_terracotta")      # muro del santuario
    o.carve(CX - 1, 24, CZ - 1, CX + 1, 26, CZ - 1, "pir")
    for x in (CX - 3, CX, CX + 3):                                          # vanos de la fachada
        w = 1 if x == CX else 0
        o.carve(x - w, 24, z0, x + w, 26, z0, "pir")
        o.fill(x - w, 27, z0, x + w, 27, z0, "polished_tuff")
    for x in (CX - 2, CX + 2, CX - 4, CX + 4):
        o.fill(x, 24, z0, x, 29, z0, "chiseled_tuff")
    for x in range(x0, x1 + 1):                                             # cornisa del techo
        for z in (z0 - 1, z1 + 1):
            o.set(x, 29, z, "tuff_brick_slab[type=top,waterlogged=false]")
    for z in range(z0, z1 + 1):
        for x in (x0 - 1, x1 + 1):
            o.set(x, 29, z, "tuff_brick_slab[type=top,waterlogged=false]")
    # crestería calada (rota en el extremo este)
    for x in range(CX - 4, CX + 5):
        for y in range(31, 36):
            if x % 2 == 0 or y in (33, 35) or x in (CX - 4, CX + 4):
                if x >= CX + 2 and y >= 34 or x == CX + 4 and y == 33:
                    o.ruin.add((x, y, CZ + 1))
                    continue
                o.set(x, y, CZ + 1, "chiseled_tuff_bricks" if y == 35 else "polished_tuff")
    o.ruin.add((CX + 3, 31, CZ + 1))
    # santuario
    o.fill(CX - 1, 24, CZ + 4, CX + 1, 24, CZ + 4, "chiseled_tuff_bricks")
    o.set(CX - 1, 25, CZ + 4, "candle[candles=3,lit=true,waterlogged=false]")
    o.set(CX + 1, 25, CZ + 4, "candle[candles=3,lit=true,waterlogged=false]")
    o.set(CX, 25, CZ + 4, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    o.chest(CX + 5, 24, CZ + 1, "west", "menor", "templo")
    o.set(CX + 5, 24, CZ + 4, "decorated_pot[cracked=false,facing=west,waterlogged=false]")
    o.set(CX + 3, 28, CZ + 2, "lantern[hanging=true,waterlogged=false]")
    o.set(CX - 3, 28, CZ - 3, "lantern[hanging=true,waterlogged=false]")
    o.set(CX + 3, 28, CZ - 3, "lantern[hanging=true,waterlogged=false]")


def inscriptions(o):
    """Escalera interior: tramo A (oeste, al norte) 24->12, rellano, tramo B (centro, al sur) 12->1."""
    o.carve(CX - 5, 24, CZ + 4, CX - 3, 26, CZ + 4, "pir")
    o.flight("z", CX - 5, CX - 3, CZ + 4, -1, 24, 12, "pir")          # z 45..34
    # pretil del hueco en el santuario
    for z in range(CZ, CZ + 3):
        o.set(CX - 2, 24, z, "tuff_brick_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
    # rellano (cota 12) y tramo B
    o.carve(CX - 5, 12, CZ - 10, CX + 5, 14, CZ - 9, "pir")
    o.flight("z", CX - 1, CX + 1, CZ - 9, 1, 12, 11, "pir")           # z 34..44 -> cota 1
    o.set(CX - 2, 14, CZ - 10, "lantern[hanging=true,waterlogged=false]")
    o.set(CX + 3, 14, CZ - 10, "lantern[hanging=true,waterlogged=false]")
    # Cámara de las Ofrendas (oeste)
    o.carve(CX - 13, 12, CZ - 12, CX - 7, 14, CZ - 7, "pir")
    o.carve(CX - 6, 12, CZ - 10, CX - 6, 13, CZ - 10, "pir")
    o.chest(CX - 13, 12, CZ - 10, "east", "menor", "ofrendas")
    for z in (CZ - 12, CZ - 7):
        o.set(CX - 13, 12, z, "decorated_pot[cracked=false,facing=east,waterlogged=false]")
    o.fill(CX - 10, 12, CZ - 12, CX - 10, 12, CZ - 12, "chiseled_tuff_bricks")
    o.set(CX - 10, 13, CZ - 12, "candle[candles=4,lit=true,waterlogged=false]")
    o.set(CX - 10, 14, CZ - 9, "lantern[hanging=true,waterlogged=false]")
    # Cámara tapiada (este): puerta cegada con adoquín y grava sospechosa
    o.carve(CX + 7, 12, CZ - 12, CX + 13, 14, CZ - 7, "pir")
    o.carve(CX + 6, 12, CZ - 10, CX + 6, 13, CZ - 10, "pir")
    o.chest(CX + 13, 12, CZ - 10, "west", "oculto", "tapiada")
    o.set(CX + 13, 12, CZ - 12, "decorated_pot[cracked=true,facing=west,waterlogged=false]")
    o.fill(CX + 10, 12, CZ - 7, CX + 10, 12, CZ - 7, "bone_block[axis=y]")
    o.set(CX + 10, 13, CZ - 7, "skeleton_skull[powered=false,rotation=8]")


def seal_doorway(o):
    x, z = CX + 6, CZ - 10
    o.set(x, 12, z, "suspicious_gravel[dusted=0]", {"id": "minecraft:brushable_block",
                                                    "LootTable": "minecraft:archaeology/desert_pyramid"})
    o.set(x, 13, z, "cobblestone")
    o.sealed |= {(x, 12, z), (x, 13, z)}
    o.mark("sala_oculta:tapiada", CX + 10, 12, CZ - 9)


def hall(o):
    """Sala del Cenote (cota 1) con la boca del pozo; brecha oeste con trampa de cable."""
    o.carve(CX - 12, 1, CZ + 3, CX + 12, 6, CZ + 19, "pir")
    for px in (CX - 9, CX + 8):
        for pz in (CZ + 6, CZ + 15):
            o.fill(px, 1, pz, px + 1, 6, pz + 1, "chiseled_tuff_bricks")
    cz = CZ + 11
    for x in range(CX - 6, CX + 7):
        for z in range(cz - 6, cz + 7):
            r = ((x - CX) ** 2 + (z - cz) ** 2) ** 0.5
            if r <= 4.5:
                o.carve(x, 0, z, x, 0, z, "pir")
            elif r <= 5.5:
                o.set(x, 1, z, "tuff_brick_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]")
    o.set(CX - 11, 1, CZ + 12, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    o.set(CX + 11, 1, CZ + 12, "campfire[facing=west,lit=true,signal_fire=false,waterlogged=false]")
    for x, z in ((CX - 6, CZ + 6), (CX + 6, CZ + 6), (CX - 6, CZ + 16), (CX + 6, CZ + 16)):
        o.set(x, 6, z, "lantern[hanging=true,waterlogged=false]")
    o.chest(CX - 12, 1, CZ + 18, "east", "menor", "sala")
    o.set(CX - 12, 1, CZ + 17, "decorated_pot[cracked=false,facing=east,waterlogged=false]")
    o.set(CX - 12, 1, CZ + 19, "decorated_pot[cracked=true,facing=east,waterlogged=false]")
    # escalera al subsuelo (esquina sureste): baja al sur de cota 1 a -6
    o.flight("z", CX + 6, CX + 8, CZ + 8, 1, 1, 7, "pir", st="stone_brick_stairs")   # z 51..57
    for z in range(CZ + 10, CZ + 13):
        o.set(CX + 9, 1, z, "tuff_brick_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
    for x in range(CX + 6, CX + 10):
        o.set(x, 1, CZ + 13, "tuff_brick_wall[east=tall,north=none,south=none,up=true,waterlogged=false,west=tall]")
    # galería de la brecha oeste
    o.carve(CX - 23, 1, cz - 1, CX - 13, 3, cz + 1, "pir")
    o.carve(CX - 24, 1, cz - 1, CX - 24, 3, cz + 1, "brecha")
    for (x, y, z) in ((CX - 24, 4, cz), (CX - 24, 4, cz - 1), (CX - 24, 1, cz - 2), (CX - 24, 2, cz - 2),
                      (CX - 24, 1, cz + 2), (CX - 24, 3, cz + 2), (CX - 23, 4, cz)):
        o.set(x, y, z, "air")
        o.collapse.add((x, y, z))
    for (x, z) in ((CX - 25, cz - 2), (CX - 26, cz + 2), (CX - 25, cz + 3)):
        o.set(x, 1, z, "tuff")
        o.ruin.add((x, 1, z))
    o.set(CX - 25, 2, cz - 2, "tuff_slab[type=bottom,waterlogged=false]")
    o.ruin.add((CX - 25, 2, cz - 2))
    # trampa de cable: dos dispensadores de flechas a la altura de la cabeza
    tx = CX - 19
    piezas.tripwire_trap(o.set, (tx, cz - 1), (tx, cz + 1), 1, "z",
                         [((tx, 2, cz - 2), "south"), ((tx, 2, cz + 2), "north")])
    o.mark("trampa:cable", tx, 1, cz)


def platforms(o):
    for x0, kind in ((CX - 18, "altar"), (CX + 10, "tzompantli")):
        o.fill(x0, 0, 2, x0 + 8, 3, 10, "tuff_bricks")
        for x in range(x0, x0 + 9):
            for z in range(2, 11):
                edge = x in (x0, x0 + 8) or z in (2, 10)
                o.set(x, 3, z, "polished_tuff" if edge else "tuff_bricks")
                if edge and not (x in (x0, x0 + 8) and z in (2, 10)):
                    o.set(x, 2, z, "chiseled_tuff_bricks" if (x + z) % 3 == 0 else "tuff_bricks")
        o.up_flight("z", x0 + 3, x0 + 5, 13, -1, 1, 3, "tuff_brick_stairs")   # z 13,12,11
        if kind == "altar":
            o.fill(x0 + 4, 4, 5, x0 + 4, 4, 6, "chiseled_tuff_bricks")
            o.set(x0 + 4, 5, 5, "candle[candles=2,lit=true,waterlogged=false]")
            o.set(x0 + 4, 5, 6, "candle[candles=3,lit=true,waterlogged=false]")
            o.chest(x0 + 2, 4, 4, "south", "menor", "altar")
            o.set(x0 + 6, 4, 4, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
            o.set(x0 + 6, 4, 7, "decorated_pot[cracked=true,facing=south,waterlogged=false]")
            for x in (x0, x0 + 8):
                o.fill(x, 4, 2, x, 5, 2, "chiseled_tuff")
        else:
            for x in range(x0 + 1, x0 + 8):
                end = x in (x0 + 1, x0 + 7)
                o.set(x, 4, 6, "bone_block[axis=y]" if end else
                      "dark_oak_fence[east=true,north=false,south=false,waterlogged=false,west=true]")
                o.set(x, 5, 6, "skeleton_skull[powered=false,rotation=8]")
            o.set(x0 + 2, 4, 8, "skeleton_skull[powered=false,rotation=0]")
            o.set(x0 + 6, 4, 4, "bone_block[axis=y]")
    # estelas
    for x in (CX - 8, CX + 8):
        o.fill(x, 1, 14, x, 3, 14, "chiseled_tuff")
        o.set(x, 4, 14, "tuff_brick_slab[type=bottom,waterlogged=false]")


def ballcourt(o):
    x0, z0, z1 = 57, CZ - 16, CZ + 16          # taludes x 57..61 y 71..75, callejón 63..69
    for xa, xb, bench, face in ((57, 61, 62, "west"), (71, 75, 70, "east")):
        o.fill(xa, 0, z0, xb, 6, z1, "tuff_bricks")
        for x in range(xa, xb + 1):
            for z in range(z0, z1 + 1):
                o.set(x, 6, z, "polished_tuff")
        for z in range(z0, z1 + 1):
            o.set(bench, 1, z, f"tuff_brick_stairs[facing={face},half=bottom,shape=straight,waterlogged=false]")
            o.set(bench, 0, z, "tuff_bricks")
        ring = bench
        for y in range(4, 7):
            for z in range(CZ - 1, CZ + 2):
                if not (y == 5 and z == CZ):
                    o.set(ring, y, z, "chiseled_tuff")
        o.up_flight("z", xa + 1, xb - 1, z0, 1, 1, 6, "tuff_brick_stairs", clear_to=6)
    # adoratorio sobre el talud oeste
    sx0, sx1, sz0, sz1 = 57, 61, z1 - 6, z1
    for x in range(sx0, sx1 + 1):
        for z in range(sz0, sz1 + 1):
            edge = x in (sx0, sx1) or z in (sz0, sz1)
            for y in range(7, 11):
                o.set(x, y, z, ("polished_tuff" if y == 7 else "red_terracotta") if edge else "air")
            o.set(x, 11, z, "tuff_bricks")
    o.carve(sx0 + 1, 7, sz0 + 1, sx1 - 1, 10, sz1 - 1, "pir")
    o.carve(59, 7, sz0, 59, 8, sz0, "pir")
    o.chest(59, 7, sz1 - 1, "north", "menor", "juego_de_pelota")
    o.set(58, 7, sz1 - 1, "candle[candles=2,lit=true,waterlogged=false]")
    # derrumbe del extremo sur del talud este
    for x in range(71, 76):
        for z in range(z1 - 5, z1 + 1):
            top = 2 + int(h(x, z) * 3) + max(0, z1 - 3 - z)
            for y in range(top + 1, 7):
                o.set(x, y, z, "air")
                o.collapse.add((x, y, z))
    for (x, z) in ((76, z1 - 1), (76, z1 - 3), (70, z1), (77, z1 - 2)):
        o.set(x, 1, z, "tuff")
        o.ruin.add((x, 1, z))


def collapse_corner(o):
    """Esquina sureste de los cuerpos 4-6 desplomada, con escombro en la terraza de abajo."""
    c = (CX + 13, 19, CZ + 13)
    for x in range(CX + 6, CX + 22):
        for y in range(12, 28):
            for z in range(CZ + 6, CZ + 22):
                d = ((x - c[0]) ** 2 + (y - c[1]) ** 2 * 0.6 + (z - c[2]) ** 2) ** 0.5
                if d < 5.2 + h(x, y, z) * 1.2 and o.get(x, y, z) not in (None, "minecraft:air"):
                    o.set(x, y, z, "air")
                    o.collapse.add((x, y, z))
    for (x, z) in ((CX + 16, CZ + 17), (CX + 17, CZ + 16), (CX + 17, CZ + 17), (CX + 15, CZ + 18), (CX + 18, CZ + 15)):
        for y in range(8, 20):
            below, here = o.get(x, y - 1, z), o.get(x, y, z)
            if below not in (None, "minecraft:air") and here in (None, "minecraft:air") and "stairs" not in below:
                o.set(x, y, z, "gravel" if (x + z) % 2 else "tuff")
                o.ruin.add((x, y, z))
                break


# ====================================================================== subsuelo
def underground(o):
    C = (CX, CZ + 11)          # centro del pozo y del cenote (30, 53)
    cx, cz = C
    # pozo: de la sala (y=0) al cenote
    for x in range(cx - 5, cx + 6):
        for z in range(cz - 5, cz + 6):
            if (x - cx) ** 2 + (z - cz) ** 2 <= 4.5 ** 2:
                o.carve(x, -8, z, x, -1, z, "cen")
    # --- L-1 galerías (cota -6)
    for x in range(cx - 8, cx + 9):
        for z in range(cz - 8, cz + 9):
            m = max(abs(x - cx), abs(z - cz))
            if 6 <= m <= 8 and not (cx + 6 <= x <= cx + 8 and cz - 2 <= z <= cz + 4):
                o.carve(x, -6, z, x, -3, z, "l1")
    for (xa, za, xb, zb) in ((cx - 1, cz - 5, cx + 1, cz - 5), (cx - 1, cz + 5, cx + 1, cz + 5), (cx - 5, cz - 1, cx - 5, cz + 1)):
        o.carve(xa, -5, za, xb, -4, zb, "l1")
        for x in range(xa, xb + 1):
            for z in range(za, zb + 1):
                o.set(x, -6, z, "stone_brick_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]")
    # norte: pasillo con trampa de foso y Cámara del Juicio
    o.carve(cx - 1, -6, cz - 14, cx + 1, -4, cz - 9, "l1")
    o.carve(cx - 5, -6, cz - 21, cx + 5, -3, cz - 15, "l1")
    pz = cz - 11                                   # fila de trampillas (z=42)
    o.carve(cx - 1, -9, pz, cx + 3, -8, pz, "l1")
    for x in range(cx - 1, cx + 2):
        o.set(x, -7, pz, "iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]")
        o.set(x, -6, pz + 1, "stone_pressure_plate[powered=false]")
        o.mark("trampa:foso", x, -6, pz + 1)
    o.carve(cx + 3, -8, pz + 1, cx + 3, -6, pz + 1, "l1")
    o.set(cx + 3, -9, pz + 1, "stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    o.carve(cx + 3, -7, pz + 2, cx + 3, -5, pz + 2, "l1")
    o.set(cx + 3, -8, pz + 2, "stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    o.set(cx + 3, -7, pz + 3, "stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    o.mark("foso", cx + 2, -9, pz)
    o.spawner(cx, -6, cz - 18, "bogged", "juicio")
    o.chest(cx + 5, -6, cz - 20, "west", "galeria", "juicio")
    for x in (cx - 5, cx + 5):
        o.fill(x, -6, cz - 15, x, -3, cz - 15, "chiseled_stone_bricks")
    o.set(cx - 4, -6, cz - 21, "candle[candles=2,lit=true,waterlogged=false]")
    # oeste: guarida de arañas
    o.carve(cx - 9, -6, cz, cx - 9, -5, cz, "l1")
    o.carve(cx - 17, -6, cz - 3, cx - 10, -3, cz + 3, "l1")
    o.spawner(cx - 15, -6, cz, "cave_spider", "arañas")
    for (x, y, z) in ((cx - 16, -6, cz - 2), (cx - 14, -6, cz + 2), (cx - 17, -4, cz + 1), (cx - 12, -3, cz - 3),
                      (cx - 15, -5, cz), (cx - 11, -3, cz + 3), (cx - 16, -3, cz)):
        o.set(x, y, z, "cobweb")
    o.chest(cx - 17, -6, cz - 3, "east", "galeria", "arañas")
    # este: osario
    o.carve(cx + 9, -6, cz - 6, cx + 9, -5, cz - 6, "l1")
    o.carve(cx + 10, -6, cz - 9, cx + 16, -3, cz - 3, "l1")
    o.spawner(cx + 14, -6, cz - 6, "skeleton", "osario")
    for (x, z) in ((cx + 16, cz - 9), (cx + 16, cz - 8), (cx + 16, cz - 4), (cx + 16, cz - 3), (cx + 10, cz - 9)):
        o.set(x, -6, z, "bone_block[axis=y]")
        o.set(x, -5, z, "skeleton_skull[powered=false,rotation=4]")
    o.chest(cx + 16, -6, cz - 6, "west", "galeria", "osario")
    # escalera L-1 -> L-2 (suroeste, al oeste)
    o.carve(cx - 9, -6, cz + 6, cx - 9, -4, cz + 8, "l1")
    o.flight("x", cz + 6, cz + 8, cx - 8, -1, -6, 8, "l1", st="stone_brick_stairs")      # x 21..14 -> -14
    o.carve(cx - 19, -14, cz + 2, cx - 17, -12, cz + 8, "cen")
    o.carve(cx - 16, -14, cz + 2, cx - 8, -12, cz + 4, "cen")
    # --- L-2 cenote
    for x in range(cx - 10, cx + 11):
        for z in range(cz - 10, cz + 11):
            r = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
            if r <= 9.5:
                top = -9 if r <= 6 else -10 if r <= 8 else -11
                o.carve(x, -14, z, x, top, z, "cen")
                if r <= 6.5:
                    for y in range(-19, -14):
                        o.set(x, y, z, "water[level=0]")
                    if h(x, z) < 0.12:
                        o.set(x, -19, z, "sea_pickle[pickles=3,waterlogged=true]")
                elif 8.2 < r and h(x, z, 1) < 0.18:
                    o.set(x, top, z, "pointed_dripstone[thickness=tip,vertical_direction=down,waterlogged=false]")
                    o.set(x, top + 1, z, "dripstone_block")
                elif 6.5 < r <= 8 and h(x, z, 2) < 0.1:
                    o.set(x, top, z, "hanging_roots[waterlogged=false]")
    # túnel sumergido y Cámara sumergida (este)
    for x in range(cx + 7, cx + 14):
        for y in (-19, -18, -17):
            o.set(x, y, cz, "water[level=0]")
            o.water_dive.add((x, y, cz))
        o.set(x, -20, cz, "stone")
        if x % 2:
            o.set(x, -19, cz, "sea_pickle[pickles=2,waterlogged=true]")
    for y in range(-19, -14):
        o.set(cx + 14, y, cz, "water[level=0]")
        o.water_dive.add((cx + 14, y, cz))
    o.carve(cx + 12, -14, cz - 3, cx + 18, -11, cz + 3, "cen")
    o.chest(cx + 18, -14, cz, "west", "oculto", "sumergida")
    o.set(cx + 18, -14, cz - 2, "decorated_pot[cracked=false,facing=west,waterlogged=false]")
    o.set(cx + 18, -14, cz + 2, "decorated_pot[cracked=false,facing=west,waterlogged=false]")
    o.set(cx + 15, -14, cz - 3, "soul_lantern[hanging=false,waterlogged=false]")
    o.mark("sala_oculta:sumergida", cx + 16, -14, cz)
    # escalera L-2 -> L-3 (norte de la cornisa)
    o.flight("z", cx - 1, cx + 1, cz - 9, -1, -14, 10, "l3", st="deepslate_tile_stairs")    # z 43..34 -> -24
    # --- L-3 tumba
    o.carve(cx - 5, -24, cz - 27, cx + 5, -20, cz - 20, "l3")          # Sala de los Guardianes z 26..33
    o.spawner(cx - 5, -24, cz - 27, "zombie", "guardianes")
    o.chest(cx + 5, -24, cz - 22, "west", "galeria", "guardianes")
    for x in (cx - 3, cx + 3):
        o.set(x, -24, cz - 21, "chiseled_deepslate")
        o.set(x, -23, cz - 21, "chiseled_deepslate")
        o.set(x, -22, cz - 21, "soul_lantern[hanging=false,waterlogged=false]")
    o.carve(cx - 1, -24, cz - 33, cx + 1, -22, cz - 28, "l3")          # losas de dardos z 20..25
    for z in (cz - 32, cz - 29):
        for x in range(cx - 1, cx + 2):
            o.set(x, -25, z, "dispenser[facing=up,triggered=false]",
                  {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": 8}]})
            o.set(x, -24, z, "polished_blackstone_pressure_plate[powered=false]")
            o.mark("trampa:dardos", x, -24, z)
    o.carve(cx - 7, -24, cz - 43, cx + 7, -18, cz - 34, "l3")          # Tumba del Rey z 10..19
    o.fill(cx - 1, -24, cz - 41, cx + 1, -24, cz - 37, "polished_blackstone")
    o.fill(cx - 1, -23, cz - 41, cx + 1, -23, cz - 37, "polished_blackstone")
    for x, z in ((cx - 1, cz - 41), (cx + 1, cz - 41), (cx - 1, cz - 37), (cx + 1, cz - 37)):
        o.set(x, -24, z, "gilded_blackstone")
    o.set(cx, -23, cz - 41, "chiseled_polished_blackstone")
    o.set(cx - 1, -22, cz - 39, "candle[candles=3,lit=true,waterlogged=false]")
    o.set(cx + 1, -22, cz - 39, "candle[candles=3,lit=true,waterlogged=false]")
    o.chest(cx - 7, -24, cz - 39, "east", "tumba", "ajuar")
    o.set(cx - 7, -24, cz - 41, "decorated_pot[cracked=false,facing=east,waterlogged=false]")
    o.set(cx - 7, -24, cz - 37, "decorated_pot[cracked=false,facing=east,waterlogged=false]")
    for x in (cx - 5, cx + 5):
        o.set(x, -18, cz - 39, "soul_lantern[hanging=true,waterlogged=false]")
    o.t.entity(cx - 3, -24, cz - 38, guardian())
    o.mark("guardian", cx - 3, -24, cz - 38)
    # Cámara del Tesoro (z 1..6) y puerta secreta (muro z 7..9)
    o.carve(cx - 4, -24, 1, cx + 4, -20, 6, "l3")
    o.chest(cx, -24, 1, "south", "premium", "tesoro")
    for x, z in ((cx - 4, 1), (cx + 4, 1)):
        o.set(x, -24, z, "gilded_blackstone")
        o.set(x, -23, z, "candle[candles=4,lit=true,waterlogged=false]")
    o.set(cx - 2, -24, 1, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
    o.set(cx + 2, -24, 1, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
    o.set(cx, -20, 4, "soul_lantern[hanging=true,waterlogged=false]")
    o.mark("sala_oculta:tesoro", cx, -24, 4)


def secret_door(o):
    """Puerta secreta: dos pistones pegajosos extendidos (antorcha encendida) sujetan los bloques de la puerta."""
    cx, F, z = CX, -24, 8                  # capa central del muro z 7..9
    o.carve(cx, F, z + 1, cx, F + 1, z + 1, "l3")      # nicho hacia la tumba (z 9)
    o.carve(cx, F, z - 1, cx, F + 1, z - 1, "l3")      # vano hacia el tesoro (z 7)
    piezas.piston_door(o.set, [(cx, F, z), (cx, F + 1, z)], (1, 0), "west", "deepslate_tiles")
    o.puzzle += [(cx, F, z), (cx, F + 1, z)]
    o.set(cx + 3, F, z, "redstone_wall_torch[facing=west,lit=true]")
    o.set(cx + 3, F + 1, z, "deepslate_tiles")                       # Y: carga fuerte desde la antorcha
    o.set(cx + 4, F, z, "deepslate_tiles")                           # X: bloque de la antorcha
    o.set(cx + 4, F, z + 1, "lever[face=wall,facing=south,powered=false]")
    o.mark("palanca", cx + 4, F, z + 1)
    o.door = dict(D=[(cx, F, z), (cx, F + 1, z)], heads=[(cx + 1, F, z), (cx + 1, F + 1, z)],
                  pistons=[(cx + 2, F, z), (cx + 2, F + 1, z)], torch=(cx + 3, F, z), Y=(cx + 3, F + 1, z),
                  X=(cx + 4, F, z), lever=(cx + 4, F, z + 1))


def guardian():
    """El Rey Jaguar: zombi con corona y pectoral de oro y espada de hierro; sin refuerzos ni botín de equipo."""
    n = piezas.guardian("zombie", "heraldia.piramide.guardian", "El Rey Jaguar", 40, armor=4,
                        equipment={"head": {"id": "minecraft:golden_helmet", "count": 1},
                                   "chest": {"id": "minecraft:golden_chestplate", "count": 1},
                                   "mainhand": {"id": "minecraft:iron_sword", "count": 1}},
                        drop_chances={"head": 0.0, "chest": 0.0, "mainhand": 0.0})
    n["attributes"] += [{"id": "minecraft:attack_damage", "base": 5.0},
                        {"id": "minecraft:knockback_resistance", "base": 0.4},
                        {"id": "minecraft:spawn_reinforcements", "base": 0.0}]
    n.update({"CanPickUpLoot": B(0), "IsBaby": B(0), "CanBreakDoors": B(0), "Tags": ["heraldia_piramide_guardian"]})
    return n


# ====================================================================== acabado
def plaza(o):
    for x in range(W):
        for z in range(D):
            if o.get(x, 0, z) is None:
                on_axis = abs(x - CX) <= 3 and z <= CZ - 33
                st = "polished_tuff" if on_axis else "tuff_bricks" if (x + z) % 7 == 0 else "tuff"
                if not on_axis and (x < 3 or x > 76 or z > 67 or (z < 2 and (x < 10 or x > 50))) and h(x, z) < 0.6:
                    st = "grass_block[snowy=false]"
                elif not on_axis and h(x, z, 3) < 0.04:
                    st = "moss_block"
                o.set(x, 0, z, st)
    for x in range(W):
        for z in range(D):
            if o.get(x, 0, z) == "minecraft:grass_block[snowy=false]" and o.get(x, 1, z) is None:
                r = h(x, z, 9)
                if r < 0.25:
                    o.set(x, 1, z, "short_grass")
                elif r < 0.33:
                    o.set(x, 1, z, "fern")


def overgrowth(o):
    """Enredaderas en la fachada norte y musgo en las terrazas."""
    for k in range(6):
        hf, b = 24 - 3 * k, 4 * k
        z = CZ - hf - 1
        for x in range(CX - hf + 1, CX + hf):
            if abs(x - CX) <= 6 or h(x, k, 5) > 0.22:
                continue
            for y in range(b + 1, b + 4):
                if o.get(x, y, z) in (None, "minecraft:air"):
                    o.set(x, y, z, "vine[east=false,north=false,south=true,up=false,west=false]")
                    o.ruin.add((x, y, z + 1))
        for x in range(CX - hf, CX + hf + 1):
            for zz in (CZ - hf + 1, CZ + hf - 1):
                if k < 5 and h(x, zz, k, 7) < 0.05 and o.get(x, b + 4, zz) in (None, "minecraft:air") \
                        and "stairs" not in (o.get(x, b + 3, zz) or "stairs"):
                    o.set(x, b + 4, zz, "moss_carpet")
                    o.ruin.add((x, b + 3, zz))


def finish(o):
    """Recubre la masa con su material: interior según la zona, exterior con ladrillo de toba."""
    for (x, y, z), (st, nbt) in list(o.t.blocks.items()):
        b = st.replace("minecraft:", "")
        if b not in ("tuff", "stone") or (x, y, z) in o.ruin:
            continue
        zone = None
        kind = None
        for dx, dy, dz in ((0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            if n in o.carved:
                zone = o.carved[n]
                kind = 2 if dy == -1 else 1 if dy == 1 else 0
                if dy == 1:
                    break
        if zone:
            if zone == "brecha":
                continue
            mat = LINING["pir" if zone == "pir" else zone][[0, 1, 2][kind]]
            if b == "stone" and zone == "pir":
                mat = "stone_bricks"
            if zone == "cen" and h(x, y, z) < 0.25:
                mat = "mossy_cobblestone" if kind == 0 else "moss_block"
            o.set(x, y, z, mat)
            continue
        if b == "tuff" and y >= 0:
            near_collapse = any((x + dx, y + dy, z + dz) in o.collapse
                                for dx, dy, dz in ((0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)))
            if near_collapse:
                o.ruin.add((x, y, z))
                continue
            above = o.get(x, y + 1, z)
            if above in (None, "minecraft:air") and (x, y + 1, z) not in o.carved:
                o.set(x, y, z, "polished_tuff")
            elif any(o.get(x + dx, y, z + dz) in (None, "minecraft:air") and (x + dx, y, z + dz) not in o.carved
                     for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                o.set(x, y, z, "tuff_bricks")


def exterior_air(o):
    x0, z0, x1, z1 = CX - 24, CZ - 24, CX + 24, CZ + 24
    for x in range(W):
        for z in range(D):
            top = AIR_TOP_PYR if x0 <= x <= x1 and z0 <= z <= z1 else AIR_TOP
            for y in range(1, top + 1):
                if o.get(x, y, z) is None:
                    o.set(x, y, z, "air")
                    o.ext_air.add((x, y, z))


def build_all():
    o = Obra()
    x0, z0, x1, z1 = UG
    o.fill(x0, UG_Y[0], z0, x1, UG_Y[1], z1, "stone")
    tiers(o)
    stair_ramp(o)
    temple(o)
    inscriptions(o)
    hall(o)
    platforms(o)
    ballcourt(o)
    collapse_corner(o)
    underground(o)
    secret_door(o)
    plaza(o)
    finish(o)
    seal_doorway(o)
    overgrowth(o)
    exterior_air(o)
    return o

