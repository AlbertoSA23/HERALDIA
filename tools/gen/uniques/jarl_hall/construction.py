"""Construcción del Salón del Jarl en un único sistema de coordenadas (ver docs/unicas/salon_jarl.md).

x de oeste a este (0..73), z de norte a sur (0..73; la puerta está al norte, z = 0); y = 0 es la capa de suelo
(pies a y = 1). Lo que queda por debajo de y = 0 (el túmulo de los reyes) es otra pieza, que rellena toda su caja.
Todo se construye en una «obra» que luego se parte en dos plantillas (auditoria.preparar).
"""
import zlib
from core import Template, B, F
from .._common import pieces
from .._common.pieces import spawner, chest, guardian, sign, text

SID = "salon_jarl"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
W = D = 74
YARD_AIR = 6                     # aire explícito sobre el patio (el terreno no asoma dentro de la empalizada)

# materiales
LOG, SLOG, PL = "spruce_log", "stripped_spruce_log", "spruce_planks"
ROOF, RIDGE = "dark_oak", "dark_oak_planks"
COB, SB = "cobblestone", "stone_bricks"
TUFF, CTUFF, PTUFF = "tuff_bricks", "chiseled_tuff", "polished_tuff"

# cripta: pies del nivel alto y del bajo
F1, F2 = -6, -12
CRYPT = (14, 62, 30, 71, -15, -1)       # caja de la pieza del túmulo: x0, x1, z0, z1, y0, y1
NATURAL = ("minecraft:dirt", "minecraft:stone")

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def stair(m, facing, half="bottom"):
    return S(f"{m}_stairs", facing=facing, half=half, shape="straight", waterlogged=False)


def h(*a):
    return zlib.crc32(",".join(map(str, a)).encode()) % 1000 / 1000.0


class Construction:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/obra")
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # celdas que solo se alcanzan resolviendo un puzle
        self.mech = {}             # mecanismos para el simulador y la prueba de servidor
        self.ruin = set()          # posiciones dañadas a mano (estado de conservación)
        self.carved = {}           # celdas de aire de la cripta -> (suelo, muro, techo)
        self.roofs = []            # peldaños de tejado (para el musgo)

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def f(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def a(self, x1, y1, z1, x2, y2, z2):
        self.t.fill(x1, y1, z1, x2, y2, z2, "air")

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def chest(self, x, y, z, facing, tbl, kind="chest"):
        chest(self.t.set, x, y, z, facing, LOOT + tbl, kind)
        self.chests.append(((x, y, z), tbl))

    def spawner(self, x, y, z, mob):
        spawner(self.t.set, x, y, z, mob, potentials=True)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=True, waterlogged=False))

    def stand_lamp(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=False, waterlogged=False))

    def door(self, x, y, z, facing, hinge="left", kind="spruce_door"):
        pieces.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="red"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="red"):
        """Cama con la cabecera hacia `facing` (la cabecera en x, z; los pies detrás)."""
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="spruce"):
        """Cartel traducible: `lines` = [(es, en)] (las claves van a LANG con el sufijo .1, .2...)."""
        self.signs.append((key, lines))
        pieces.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
                    wood=wood)

    def ruin_set(self, x, y, z, st="air"):
        self.s(x, y, z, st)
        self.ruin.add((x, y, z))

    # ------------------------------------------------------------ construcción
    def build(self):
        self.signs = []
        self.ground()
        self.palisade()
        for corner in ((0, 0), (1, 0), (0, 1), (1, 1)):
            self.tower(*corner)
        self.gatehouse()
        self.longhouse()
        self.annex()
        self.forge()
        self.stables()
        self.shipyard()
        self.warriors(27, burnt=False)
        self.warriors(45, burnt=True)
        self.storehouse()
        self.runestones()
        self.yard_ruins()
        self.crypt()
        self.yard_air()
        self.weather()
        self.moss_roofs()
        self.loose_debris()
        return self

    def loose_debris(self):
        """Lo que la ruina deja suelto (un peldaño de tejado entre dos huecos) se ha caído también."""
        from .._common.walkthrough import floating_blocks
        nearby_flag = {(x + a, y + b, z + c) for (x, y, z) in self.ruin for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)}
        area = {p: st for p, (st, _) in self.t.blocks.items() if p[1] >= 0}
        for p in floating_blocks(area, (0,)):
            if p in nearby_flag:
                self.ruin_set(*p)

    # ============================================================ superficie
    def inside(self, x, z):
        return 1 <= x <= W - 2 and 1 <= z <= D - 2

    def ground(self):
        """Suelo pisado del recinto: tierra de camino, grava y barro compacto (nada en lo que nazcan árboles)."""
        for x in range(1, W - 1):
            for z in range(1, D - 1):
                v = h(x // 3, z // 3) * 0.6 + h(x, z) * 0.4
                st = "dirt_path" if v < 0.62 else ("packed_mud" if v < 0.84 else "gravel")
                self.s(x, 0, z, st)
        for z in range(1, 22):                   # avenida de grava de la puerta al salón
            for x in range(35, 39):
                self.s(x, 0, z, "gravel")
        for x in range(23, 51):                  # explanada ante el salón
            for z in range(17, 22):
                self.s(x, 0, z, "gravel" if (x + z) % 5 else "packed_mud")

    def palisade(self):
        def post(x, z):
            for y in range(0, 6):
                self.s(x, y, z, S(LOG, axis="y"))
            if (x + z) % 2 == 0:
                self.s(x, 6, z, S(LOG, axis="y"))
        for i in range(W):
            for (x, z) in ((i, 0), (i, D - 1), (0, i), (W - 1, i)):
                if self.tower_cell(x, z) or (32 <= x <= 41 and z <= 5):
                    continue
                post(x, z)
        # adarve: tablones a media altura por dentro, sobre pies derechos
        for i in range(W):
            for (x, z) in ((i, 1), (i, D - 2), (1, i), (W - 2, i)):
                if self.tower_cell(x, z) or (32 <= x <= 41 and z <= 5) or not self.inside(x, z):
                    continue
                self.s(x, 4, z, S("spruce_slab", type="top", waterlogged=False))
                if i % 4 == 0:
                    self.f(x, 1, z, x, 3, z, "spruce_fence")

    @staticmethod
    def tower_cell(x, z):
        return (x <= 6 or x >= W - 7) and (z <= 6 or z >= D - 7)

    def tower(self, cx, cz):
        """Torre de esquina de 7 x 7: planta baja, sala del adarve (pies 5), atalaya (pies 10) y tejado a cuatro aguas."""
        X = (lambda i: i) if cx == 0 else (lambda i: W - 1 - i)
        Z = (lambda j: j) if cz == 0 else (lambda j: D - 1 - j)
        ox, oz = ("west", "east") if cx == 0 else ("east", "west")     # (exterior, interior) en x
        nz_, sz_ = ("north", "south") if cz == 0 else ("south", "north")
        for i in range(7):
            for j in range(7):
                x, z = X(i), Z(j)
                edge = i in (0, 6) or j in (0, 6)
                corner = i in (0, 6) and j in (0, 6)
                for y in range(0, 13):
                    if corner:
                        self.s(x, y, z, S(LOG, axis="y"))
                    elif edge and y <= 10:
                        self.s(x, y, z, COB if y <= 1 else PL)
                    elif not edge and y in (0, 4, 9):
                        self.s(x, y, z, PL)
                    else:
                        self.s(x, y, z, "air")
        # tejado a cuatro aguas macizo (cada hilada apoyada en la de debajo)
        for k in range(4):
            y = 13 + k
            for i in range(k, 7 - k):
                for j in range(k, 7 - k):
                    x, z = X(i), Z(j)
                    ring = i in (k, 6 - k) or j in (k, 6 - k)
                    if not ring or k == 3:
                        self.s(x, y, z, RIDGE)
                    elif i in (k, 6 - k) and j in (k, 6 - k):
                        self.s(x, y, z, RIDGE)
                    elif i == k:
                        self.s(x, y, z, stair(ROOF, oz))
                    elif i == 6 - k:
                        self.s(x, y, z, stair(ROOF, ox))
                    elif j == k:
                        self.s(x, y, z, stair(ROOF, sz_))
                    else:
                        self.s(x, y, z, stair(ROOF, nz_))
                    if ring and k < 3:
                        self.roofs.append((x, y, z))
        self.s(X(3), 17, Z(3), S("lightning_rod", facing="up", powered=False, waterlogged=False))
        # saeteras en las caras exteriores
        for (i, j) in ((3, 0), (0, 3)):
            self.a(X(i), 6, Z(j), X(i), 7, Z(j))
        # escalera de mano pegada al muro interior de z (lejos del adarve), por los forjados
        lx, lz = X(3), Z(5)
        for y in range(1, 10):
            self.s(lx, y, lz, S("ladder", facing=nz_, waterlogged=False))
        # puerta al patio y pasos al adarve
        self.door(X(6), 1, Z(3), oz)
        self.a(X(6), 5, Z(1), X(6), 6, Z(1))
        self.a(X(1), 5, Z(6), X(1), 6, Z(6))
        self.hang(X(3), 3, Z(2))
        self.hang(X(2), 8, Z(3))
        self.hang(X(3), 12, Z(2))
        if (cx, cz) == (0, 0):
            self.chest(X(1), 10, Z(1), oz, "atalaya")
        if (cx, cz) == (1, 0):                     # torre noreste: el tejado se ha hundido en parte
            for (i, j, y) in ((2, 2, 15), (3, 2, 15), (2, 3, 15), (3, 3, 16), (3, 3, 17), (2, 2, 14), (3, 2, 14),
                              (2, 1, 13), (2, 2, 13), (3, 1, 14)):
                self.ruin_set(X(i), y, Z(j))
            self.ruin_set(X(4), 10, Z(4), S("dark_oak_slab", type="bottom", waterlogged=False))
            self.ruin_set(X(2), 10, Z(4), stair(ROOF, sz_))
            self.ruin_set(X(1), 10, Z(4), RIDGE)

    def gatehouse(self):
        """Puerta de 10 x 6: túnel de 4 de ancho y sala de guardia encima, a la altura del adarve."""
        for x in range(32, 42):
            for z in range(0, 6):
                edge = x in (32, 41) or z in (0, 5)
                for y in range(0, 8):
                    if x in (32, 41) and z in (0, 5):
                        st = S(LOG, axis="y")
                    elif y == 0:
                        st = COB
                    elif edge or y in (4,) or y <= 3:
                        st = PL if y >= 2 else COB
                    else:
                        st = "air"
                    self.s(x, y, z, st)
        self.a(35, 1, 0, 38, 3, 5)                # túnel
        for x in range(35, 39):
            self.s(x, 0, 0, "gravel")
            for z in range(1, 6):
                self.s(x, 0, z, "gravel")
        for x in (34, 39):                         # jambas de troncos
            self.f(x, 1, 0, x, 3, 0, S(LOG, axis="y"))
        self.f(34, 4, 0, 39, 4, 0, S(LOG, axis="x"))   # dintel
        self.banner(35, 3, 1, "east")
        self.banner(38, 3, 1, "west")
        self.banner(35, 3, 4, "east", "black")
        self.banner(38, 3, 4, "west", "black")
        self.hang(36, 3, 3)
        self.hang(37, 3, 3)
        # tejado a dos aguas con la cumbrera en x
        for x in range(32, 42):
            self.s(x, 8, 0, stair(ROOF, "south"))
            self.s(x, 8, 5, stair(ROOF, "north"))
            self.f(x, 8, 1, x, 8, 4, PL)
            self.s(x, 9, 1, stair(ROOF, "south"))
            self.s(x, 9, 4, stair(ROOF, "north"))
            self.f(x, 9, 2, x, 9, 3, PL)
            self.s(x, 10, 2, stair(ROOF, "south"))
            self.s(x, 10, 3, stair(ROOF, "north"))
            for p in ((x, 8, 0), (x, 8, 5), (x, 9, 1), (x, 9, 4), (x, 10, 2), (x, 10, 3)):
                self.roofs.append(p)
        for x in (32, 41):
            self.f(x, 8, 1, x, 9, 4, PL)
        # sala de guardia: saeteras, pasos al adarve, cofre
        for x in (34, 36, 37, 39):
            self.s(x, 6, 0, "air")
        for x in (34, 39):
            self.s(x, 6, 5, "glass_pane")
        self.a(32, 5, 1, 32, 6, 1)
        self.a(41, 5, 1, 41, 6, 1)
        self.chest(33, 5, 4, "east", "atalaya")
        self.s(40, 5, 4, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.hang(36, 7, 2)
        self.hang(37, 7, 3)

    # ------------------------------------------------------------ casa larga
    @staticmethod
    def roof_y(x):
        return 6 + (x - 27) if x <= 36 else 6 + (46 - x)

    def longhouse(self):
        x1, x2, z1, z2 = 28, 45, 22, 58
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                wall = x in (x1, x2) or z in (z1, z2)
                self.s(x, 0, z, COB if wall else PL)
                for y in range(1, 6):
                    if not wall:
                        self.s(x, y, z, "air")
                    elif x in (x1, x2) and (z in (z1, z2) or (z - z1) % 4 == 0):
                        self.s(x, y, z, S(LOG, axis="y"))
                    elif x in (x1, x2):
                        self.s(x, y, z, S(SLOG, axis="z"))
                    else:
                        self.s(x, y, z, PL)
                if x in (x1, x2):
                    self.s(x, 6, z, S(LOG, axis="z"))
        # aire interior bajo la cubierta
        for x in range(x1 + 1, x2):
            for z in range(z1 + 1, z2):
                for y in range(6, self.roof_y(x) - 1):
                    self.s(x, y, z, "air")
        # cubierta: peldaño por fuera y peldaño invertido por dentro (dos de grueso, unidos por caras)
        for x in range(27, 47):
            r = self.roof_y(x)
            up = "east" if x <= 36 else "west"
            for z in range(z1 - 1, z2 + 2):
                self.s(x, r, z, stair(ROOF, up))
                self.roofs.append((x, r, z))
                if x not in (27, 28, 45, 46):
                    self.s(x, r - 1, z, stair(ROOF, OPP[up], "top"))
        for z in range(z1 - 1, z2 + 2):
            self.s(36, 16, z, S("dark_oak_slab", type="bottom", waterlogged=False))
            self.s(37, 16, z, S("dark_oak_slab", type="bottom", waterlogged=False))
        # hastiales de tablones hasta la cubierta
        for z in (z1, z2):
            for x in range(x1 + 1, x2):
                for y in range(6, self.roof_y(x) - 1):
                    self.s(x, y, z, PL)
        for z in (z1, z2):                         # ventanuco de humos en cada hastial
            self.s(36, 11, z, "air"); self.s(37, 11, z, "air")
        # lucernario de humos sobre el hogar
        for z in range(38, 43):
            for x in (36, 37):
                self.s(x, 16, z, "air"); self.s(x, 15, z, "air"); self.s(x, 14, z, "air")
        # pies derechos y tirantes
        for z in range(26, 57, 4):
            for x in (32, 41):
                top = self.roof_y(x) - 2
                self.f(x, 1 if z < 52 else 2, z, x, top, z, S(LOG, axis="y"))
            for x in list(range(29, 32)) + list(range(33, 41)) + list(range(42, 45)):
                self.s(x, 6, z, S(LOG, axis="x"))
        # puerta doble al norte, puertas laterales
        pieces.double_door(self.s, 36, 1, z1, "south", "east", "spruce_door")
        self.f(35, 3, z1, 38, 3, z1, S(LOG, axis="x"))
        self.door(x1, 1, 30, "west")
        self.door(x2, 1, 40, "east")
        for z in (34, 46):                          # ventanas
            for x in (x1, x2):
                self.f(x, 2, z, x, 3, z, "glass_pane")
        # hogar alargado
        for z in range(34, 47):
            for x in range(35, 39):
                edge = x in (35, 38) or z in (34, 46)
                if edge:
                    self.s(x, 1, z, S("stone_brick_slab", type="bottom", waterlogged=False))
                else:
                    self.s(x, 0, z, COB)
        for z in (37, 40, 43):
            for x in (36, 37):
                self.s(x, 1, z, S("campfire", facing="north", lit=True, signal_fire=False, waterlogged=False))
        # mesas largas con bancos (respaldo hacia fuera)
        for (zz1, zz2) in ((25, 32), (36, 44)):
            for z in range(zz1, zz2 + 1):
                if z in (26, 30, 34, 38, 40, 42):
                    continue                      # paso libre junto a cada par de pies derechos
                self.s(34, 1, z, S("spruce_slab", type="top", waterlogged=False))
                self.s(39, 1, z, S("spruce_slab", type="top", waterlogged=False))
                self.s(33, 1, z, stair("spruce", "west"))
                self.s(40, 1, z, stair("spruce", "east"))
        for z in (28, 43):
            for x in (34, 39):
                self.s(x, 2, z, S("candle", candles=3, lit=False, waterlogged=False))
        for z in (30, 38, 46, 54):
            self.hang(30, 5, z)
            self.hang(43, 5, z)
        for z in (30, 46):
            self.hang(36, 5, z)
            self.hang(37, 5, z)
        # nave oeste: escalera al túmulo, camas, telar
        self.crypt_stair()
        self.bed(29, 1, 32, "west", "red")
        self.bed(29, 1, 34, "west", "red")
        self.s(29, 1, 24, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(29, 1, 25, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.chest(29, 1, 27, "east", "salon")
        self.s(29, 1, 48, S("loom", facing="east"))
        self.s(29, 1, 50, S("spruce_fence"))
        self.s(29, 2, 50, S("lantern", hanging=False, waterlogged=False))
        # nave este: camas, cofre, mesa de trabajo, caldero
        for z in (31, 33, 35):
            self.bed(44, 1, z, "east", "red")
        self.s(44, 1, 24, "crafting_table")
        self.s(44, 1, 25, S("water_cauldron", level=3))
        self.chest(44, 1, 47, "west", "salon")
        self.s(44, 1, 49, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(44, 1, 50, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        # tapices en los muros largos
        for i, z in enumerate((28, 36, 44)):
            self.banner(29, 4, z, "east", "red" if i % 2 == 0 else "black")
            self.banner(44, 4, z, "west", "black" if i % 2 == 0 else "red")
        # estrado del jarl
        for x in range(29, 45):
            for z in range(52, 58):
                if self.get(x, 1, z) in (None, "minecraft:air"):
                    self.s(x, 1, z, PL)
        for x in range(34, 40):
            self.s(x, 1, 51, stair("spruce", "south"))
        for x in (36, 37):                        # dos tronos de respaldo alto
            self.s(x, 2, 56, stair("spruce", "south"))
            self.f(x, 2, 57, x, 4, 57, S("stripped_dark_oak_log", axis="y"))
        for x in (35, 38):
            self.s(x, 2, 56, "spruce_fence")
            self.s(x, 2, 57, S("stripped_dark_oak_log", axis="y"))
            self.s(x, 3, 57, S("lantern", hanging=False, waterlogged=False))
        for x in (31, 42):
            self.banner(x, 4, 57, "north", "red")
        self.banner(39, 4, 57, "north", "black")
        self.banner(34, 4, 57, "north", "black")   # tapiz que tapa el paso a la alcoba del jarl
        self.a(34, 2, 58, 34, 3, 58)
        self.s(30, 2, 53, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(43, 2, 53, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        # jigsaw de la cripta: lo pone auditoria.preparar en JIG
        self.mech["jig"] = (40, 0, 30)

    def crypt_stair(self):
        """Escalera de la nave oeste al túmulo: 7 peldaños hacia el sur, de los pies 1 a los pies -6."""
        for i in range(7):
            z, y = 38 + i, -i
            for x in (29, 30):
                self.s(x, y, z, stair("spruce", "north"))
                for yy in range(y + 1, y + 4):
                    self.s(x, yy, z, "air")
                for yy in range(y - 1, CRYPT[4] - 1, -1):
                    if yy < 0:
                        self.s(x, yy, z, "dirt" if yy >= -2 else "stone")
        for z in range(39, 42):                    # hueco del forjado sobre la escalera
            for x in (29, 30):
                self.s(x, 0, z, "air")
        for z in range(38, 42):
            self.s(31, 1, z, "spruce_fence")
        for x in (29, 30):
            self.s(x, 1, 42, "spruce_fence")

    def annex(self):
        """Alcoba del jarl (sala oculta) adosada al hastial sur: solo se entra por detrás del tapiz del estrado."""
        x1, x2, z1, z2 = 32, 41, 58, 63
        for x in range(x1, x2 + 1):
            for z in range(z1 + 1, z2 + 1):
                wall = x in (x1, x2) or z == z2
                self.s(x, 0, z, COB)
                self.s(x, 1, z, COB if wall else PL)
                for y in range(2, 6):
                    if wall:
                        self.s(x, y, z, S(LOG, axis="y") if (x in (x1, x2) and z == z2) else PL)
                    else:
                        self.s(x, y, z, "air")
                self.s(x, 6, z, PL)
        for x in range(x1 - 1, x2 + 2):           # tejado de una sola agua
            self.s(x, 7, z2, stair(ROOF, "north"))
            self.roofs.append((x, 7, z2))
        for x in range(x1, x2 + 1):
            for z in range(z1 + 1, z2):
                self.s(x, 7, z, S("dark_oak_slab", type="bottom", waterlogged=False))
        self.s(x1 - 1, 6, z2, PL)
        self.s(x2 + 1, 6, z2, PL)
        self.bed(39, 2, 60, "east", "black")
        self.chest(40, 2, 62, "west", "jarl")
        self.s(33, 2, 62, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(36, 2, 62, S("lectern", facing="north", has_book=False, powered=False))
        self.banner(37, 4, 62, "north", "red")
        self.hang(36, 5, 60)
        self.hidden_alcove = [(x, 2, z) for x in range(33, 41) for z in range(59, 63)]

    # ------------------------------------------------------------ talleres
    def shed(self, x1, x2, z1, z2, axis, walls, ridge_mat=RIDGE, h_wall=3):
        """Cobertizo de troncos con tejado a dos aguas (cumbrera a lo largo de `axis`) y muros en los lados `walls`
        ('n', 's', 'e', 'w'; el resto queda abierto entre pies derechos). Pies a 1, alero a h_wall + 1."""
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                ew = ("w" in walls and x == x1) or ("e" in walls and x == x2)
                ns = ("n" in walls and z == z1) or ("s" in walls and z == z2)
                corner = x in (x1, x2) and z in (z1, z2)
                edge = x in (x1, x2) or z in (z1, z2)
                post = edge and ((x - x1) % 4 == 0 or x == x2) and ((z - z1) % 4 == 0 or z == z2) and \
                    (x in (x1, x2) or z in (z1, z2))
                self.s(x, 0, z, COB if edge else PL)
                for y in range(1, h_wall + 1):
                    if corner or (edge and post):
                        self.s(x, y, z, S(LOG, axis="y"))
                    elif ew or ns:
                        self.s(x, y, z, COB if y == 1 else PL)
                    else:
                        self.s(x, y, z, "air")
                if edge:
                    self.s(x, h_wall + 1, z, S(LOG, axis="x" if z in (z1, z2) and x not in (x1, x2) else "z")
                           if not corner else S(LOG, axis="y"))
                else:
                    for y in range(h_wall + 1, h_wall + 3):
                        self.s(x, y, z, "air")
        e = h_wall + 1
        if axis == "z":                           # pendientes hacia el oeste y el este
            n = (x2 - x1) // 2 + 1
            for k in range(n + 1):
                for x, up in ((x1 - 1 + k, "east"), (x2 + 1 - k, "west")):
                    y = e + k
                    for z in range(z1 - 1, z2 + 2):
                        if x1 - 1 + k >= x2 + 1 - k:
                            self.s(x, y, z, ridge_mat)
                            self.s(x, y - 1, z, ridge_mat)
                        else:
                            self.s(x, y, z, stair(ROOF, up))
                            self.roofs.append((x, y, z))
                            if x1 < x < x2:
                                self.s(x, y - 1, z, stair(ROOF, OPP[up], "top"))
                    if x1 - 1 + k >= x2 + 1 - k:
                        break
            for z in (z1, z2):                     # hastiales
                if ("n" in walls and z == z1) or ("s" in walls and z == z2):
                    for x in range(x1 + 1, x2):
                        top = e + min(x - x1 + 1, x2 + 1 - x)
                        for y in range(e, top - 1):
                            self.s(x, y, z, PL)
        else:
            n = (z2 - z1) // 2 + 1
            for k in range(n + 1):
                for z, up in ((z1 - 1 + k, "south"), (z2 + 1 - k, "north")):
                    y = e + k
                    for x in range(x1 - 1, x2 + 2):
                        if z1 - 1 + k >= z2 + 1 - k:
                            self.s(x, y, z, ridge_mat)
                            self.s(x, y - 1, z, ridge_mat)
                        else:
                            self.s(x, y, z, stair(ROOF, up))
                            self.roofs.append((x, y, z))
                            if z1 < z < z2:
                                self.s(x, y - 1, z, stair(ROOF, OPP[up], "top"))
                    if z1 - 1 + k >= z2 + 1 - k:
                        break
            for x in (x1, x2):
                if ("w" in walls and x == x1) or ("e" in walls and x == x2):
                    for z in range(z1 + 1, z2):
                        top = e + min(z - z1 + 1, z2 + 1 - z)
                        for y in range(e, top - 1):
                            self.s(x, y, z, PL)
        # aire bajo la cubierta (que el terreno no se cuele)
        if axis == "z":
            for x in range(x1 + 1, x2):
                top = e + min(x - x1 + 1, x2 + 1 - x) - 1
                for z in range(z1 + 1, z2):
                    for y in range(e, top):
                        if self.get(x, y, z) is None:
                            self.s(x, y, z, "air")
        else:
            for z in range(z1 + 1, z2):
                top = e + min(z - z1 + 1, z2 + 1 - z) - 1
                for x in range(x1 + 1, x2):
                    for y in range(e, top):
                        if self.get(x, y, z) is None:
                            self.s(x, y, z, "air")

    def forge(self):
        """Herrería (noroeste): muros de piedra al norte, oeste y este; abierta al sur."""
        self.shed(9, 19, 9, 17, "x", "nwe")
        self.f(10, 1, 10, 11, 1, 11, COB)          # fragua con su campana y chimenea
        self.s(10, 1, 10, S("lava_cauldron"))
        self.s(11, 1, 10, S("blast_furnace", facing="south", lit=False))
        self.f(10, 3, 10, 11, 3, 11, COB)
        self.f(10, 4, 10, 10, 11, 10, COB)
        self.s(10, 2, 11, "air"); self.s(11, 2, 11, "air"); self.s(10, 2, 10, "air"); self.s(11, 2, 10, "air")
        self.s(10, 1, 11, COB)
        self.s(11, 1, 11, S("cobblestone_slab", type="bottom", waterlogged=False))
        self.s(14, 1, 13, S("anvil", facing="east"))
        self.s(13, 1, 10, "smithing_table")
        self.s(15, 1, 10, S("grindstone", face="floor", facing="south"))
        self.s(18, 1, 13, S("water_cauldron", level=3))
        self.chest(18, 1, 10, "south", "herreria")
        self.s(17, 1, 10, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.hang(14, 4, 12)
        for (x, z) in ((12, 15), (16, 15)):
            self.s(x, 0, z, COB)
        self.s(10, 1, 16, "coal_block")
        self.s(11, 1, 16, S("cobblestone_slab", type="bottom", waterlogged=False))

    def stables(self):
        """Establos (noreste): tres cuadras con su comedero contra el muro norte."""
        self.shed(54, 64, 9, 19, "x", "nwe")
        for x in (57, 61):                         # tabiques entre cuadras
            for z in range(10, 14):
                self.s(x, 1, z, "spruce_fence")
        for x0 in (55, 58, 62):
            self.s(x0, 1, 10, "hay_block[axis=x]")
            if x0 != 62:
                self.s(x0 + 1, 1, 10, S("water_cauldron", level=3))
            else:
                self.s(63, 1, 10, "hay_block[axis=z]")
            self.s(x0, 1, 14, S("spruce_fence_gate", facing="south", in_wall=False, open=False, powered=False))
            for x in range(x0 + 1, x0 + 3 if x0 != 62 else x0 + 2):
                if x not in (57, 61):
                    self.s(x, 1, 14, "spruce_fence")
        self.s(55, 1, 14, S("spruce_fence_gate", facing="south", in_wall=False, open=False, powered=False))
        self.s(56, 1, 14, "spruce_fence")
        self.s(57, 1, 14, "spruce_fence")
        self.chest(63, 1, 18, "west", "establo")
        self.s(63, 1, 17, "hay_block[axis=y]")
        self.s(63, 2, 17, "hay_block[axis=y]")
        self.s(62, 1, 18, "hay_block[axis=x]")
        self.s(55, 1, 18, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.hang(59, 4, 16)

    def shipyard(self):
        """Astillero (oeste): cobertizo largo abierto al patio con un barco largo a medio hacer sobre su grada."""
        x1, x2, z1, z2 = 8, 20, 27, 55
        self.shed(x1, x2, z1, z2, "z", "w", h_wall=4)
        # grada y quilla
        kx = 14
        for z in range(30, 53):
            if z % 4 == 0:
                for x in range(kx - 2, kx + 3):
                    self.s(x, 1, z, S(SLOG, axis="x"))
            self.s(kx, 1, z, S("stripped_dark_oak_log", axis="z")) if z % 4 else self.s(kx, 1, z, S(SLOG, axis="x"))
        for z in range(31, 52):
            hw = 3 if 36 <= z <= 46 else (2 if 33 <= z <= 49 else 1)
            for x in range(kx - hw + 1, kx + hw):
                self.s(x, 2, z, PL)
            for x in (kx - hw, kx + hw):
                self.s(x, 2, z, PL)
                self.s(x, 3, z, PL)
                self.s(x, 4, z, S("dark_oak_slab", type="bottom", waterlogged=False))
            if hw > 1:
                for x in range(kx - hw + 1, kx + hw):
                    for y in (3, 4):
                        self.s(x, y, z, "air")
        for z, sh in ((30, "north"), (52, "south")):   # roda y codaste
            self.f(kx, 2, z, kx, 5, z, S("stripped_dark_oak_log", axis="y"))
            self.s(kx, 6, z, stair(ROOF, OPP[sh], "top"))
        for z in (31, 51):
            self.s(kx, 3, z, PL)
            self.s(kx, 4, z, PL)
        for z in range(38, 45, 3):                  # bancos de remo
            self.f(kx - 2, 3, z, kx + 2, 3, z, S("spruce_slab", type="bottom", waterlogged=False))
        self.f(kx, 3, 41, kx, 8, 41, S(SLOG, axis="y"))   # mástil sin vela
        # banco del carpintero y materiales
        self.s(9, 1, 29, "crafting_table")
        self.s(9, 1, 30, S("barrel", facing="east"), {"id": "minecraft:barrel", "LootTable": LOOT + "astillero"})
        self.chests.append(((9, 1, 30), "astillero"))
        self.s(9, 1, 31, S("grindstone", face="floor", facing="east"))
        for z in (34, 35):
            self.s(9, 1, z, S(SLOG, axis="z"))
        self.s(9, 1, 50, S("loom", facing="east"))
        self.s(9, 1, 52, "white_wool")
        self.s(9, 1, 53, "white_wool")
        self.s(9, 2, 52, "white_wool")
        for z in (33, 41, 49):
            self.hang(11, 5, z)
            self.hang(17, 5, z)

    def warriors(self, z1, burnt):
        """Casa de los guerreros (este): 13 x 9, camas contra el muro este, mesa y hogar."""
        x1, x2, z2 = 53, 65, z1 + 8
        self.shed(x1, x2, z1, z2, "x", "nswe", h_wall=4)
        self.door(x1, 1, z1 + 4, "west")
        for z in (z1 + 1, z1 + 3, z1 + 5, z1 + 7):
            self.bed(64, 1, z, "east", "blue" if not burnt else "brown")
        for x in range(57, 61):
            self.s(x, 1, z1 + 4, S("spruce_slab", type="top", waterlogged=False))
            self.s(x, 1, z1 + 3, stair("spruce", "north"))
            self.s(x, 1, z1 + 5, stair("spruce", "south"))
        self.chest(54, 1, z1 + 1, "east", "guerreros")
        self.s(54, 1, z1 + 7, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        if not burnt:
            self.s(55, 1, z1 + 7, "crafting_table")
        for x in (56, 61):
            self.f(x, 2, z1, x, 3, z1, "glass_pane")
            self.f(x, 2, z2, x, 3, z2, "glass_pane")
        self.hang(58, 4, z1 + 2)
        self.hang(58, 4, z1 + 6)
        if burnt:
            # incendio: tablones carbonizados, cubierta hundida sobre el extremo este y rescoldos
            for (x, y, z), (st, _) in list(self.t.blocks.items()):
                if x1 <= x <= x2 and z1 <= z <= z2 and st == "minecraft:spruce_planks" and h(x, y, z, 3) < 0.35:
                    self.ruin_set(x, y, z, "dark_oak_planks")
            for x in range(60, 66):
                for z in range(z1 + 2, z2 - 1):
                    for y in range(6, 11):
                        if self.get(x, y, z) and "stairs" in self.get(x, y, z) or self.get(x, y, z) == "minecraft:" + RIDGE:
                            self.ruin_set(x, y, z)
            for (x, z) in ((61, z1 + 3), (62, z1 + 4), (60, z1 + 5)):
                self.ruin_set(x, 1, z, S("dark_oak_slab", type="bottom", waterlogged=False))
            self.ruin_set(62, 1, z1 + 5, S("campfire", facing="north", lit=False, signal_fire=False, waterlogged=False))
            for x in range(60, 66):                # los faroles del extremo hundido se cayeron
                for z in range(z1, z2 + 1):
                    st = self.get(x, 4, z)
                    if st and "lantern" in st:
                        self.ruin_set(x, 4, z)

    def storehouse(self):
        """Despensa (suroeste): almacén de víveres con toneles y heno."""
        self.shed(8, 17, 59, 67, "z", "nswe", h_wall=3)
        self.door(17, 1, 63, "east")
        self.chest(9, 1, 60, "south", "despensa")
        self.s(9, 1, 66, S("barrel", facing="up"), {"id": "minecraft:barrel", "LootTable": LOOT + "despensa"})
        self.chests.append(((9, 1, 66), "despensa"))
        for z in (61, 62, 64, 65):
            self.s(9, 1, z, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(16, 1, 60, "hay_block[axis=y]")
        self.s(16, 1, 66, "hay_block[axis=y]")
        self.s(15, 1, 60, "hay_block[axis=x]")
        self.s(12, 1, 60, S("composter", level=0))
        self.hang(12, 4, 63)

    def runestones(self):
        """Piedras rúnicas a los lados de la explanada; la del oeste lleva la adivinanza del muro de las runas."""
        for x in (31, 42):
            self.s(x, 0, 18, PTUFF)
            self.f(x, 1, 18, x, 2, 18, TUFF)
            self.s(x, 3, 18, CTUFF)
        self.sign(31, 2, 17, "north", "runas", [("Despierta al", "Wake the raven"), ("cuervo y al lobo;", "and the wolf;"),
                                               ("que la serpiente", "let the serpent"), ("y el oso duerman.", "and bear sleep.")])
        self.sign(42, 2, 17, "north", "salon", [("Aquí reina", "Here reigns"), ("Ulfgrim,", "Ulfgrim,"),
                                                ("jarl de la taiga.", "jarl of the taiga.")])
        for (x, z) in ((24, 12), (49, 13)):        # dos piedras sueltas en el patio
            self.s(x, 0, z, PTUFF)
            self.f(x, 1, z, x, 2, z, TUFF)

    def yard_ruins(self):
        """Ruina repartida: brecha en la empalizada este con troncos caídos, pies del adarve sueltos, musgo."""
        for z in range(40, 45):
            for y in range(2, 7):
                if self.get(W - 1, y, z) and "log" in self.get(W - 1, y, z):
                    self.ruin_set(W - 1, y, z)
            self.ruin_set(W - 2, 4, z)
        for z in range(39, 44):
            self.ruin_set(W - 4, 1, z, S(LOG, axis="z"))
        for x in range(46, 50):                    # brecha sur: troncos caídos hacia dentro
            for y in range(1, 7):
                if self.get(x, y, D - 1):
                    self.ruin_set(x, y, D - 1)
            self.ruin_set(x, 4, D - 2)
        for x in range(45, 50):
            self.ruin_set(x, 1, D - 4, S(LOG, axis="x"))
        for z in range(10, 14):                     # la empalizada oeste ha perdido sus puntas
            if self.get(0, 6, z):
                self.ruin_set(0, 6, z)
        for (x, z) in ((25, 19), (26, 20), (47, 20), (48, 19), (12, 21), (13, 22), (60, 23), (61, 24), (30, 66), (31, 67)):
            self.s(x, 1, z, "moss_carpet")

    def yard_air(self):
        for x in range(1, W - 1):
            for z in range(1, D - 1):
                for y in range(1, YARD_AIR + 1):
                    if self.get(x, y, z) is None:
                        self.s(x, y, z, "air")

    def weather(self):
        """Intemperie de la empalizada: troncos descortezados en manchas, puntas caídas y tramos del adarve rotos."""
        for i in range(W):
            for (x, z) in ((i, 0), (i, D - 1), (0, i), (W - 1, i)):
                for y in range(1, 7):
                    st = self.get(x, y, z)
                    if st != "minecraft:spruce_log[axis=y]":
                        continue
                    if y == 6 and h(x, z, 21) < 0.35:
                        self.ruin_set(x, y, z)
                    elif h(x // 3, y // 3, z // 3, 17) < 0.4 and h(x, y, z, 2) < 0.85:
                        self.ruin_set(x, y, z, S(SLOG, axis="y"))
        # cubiertas hundidas: despensa, establos y un tramo del salón junto al hastial norte (con escombro debajo)
        for (xa, xb, za, zb, ya, yb, debris) in ((13, 17, 61, 64, 5, 9, (14, 1, 62)), (56, 60, 15, 19, 5, 9, (58, 1, 17)),
                                                 (39, 42, 24, 26, 9, 13, (41, 1, 24))):
            for x in range(xa, xb + 1):
                for z in range(za, zb + 1):
                    if h(x, z, 31) >= 0.75:
                        continue
                    for y in range(ya, yb + 1):
                        st = self.get(x, y, z)
                        if st and ("dark_oak" in st or "spruce_planks" in st or "mossy" in st):
                            self.ruin_set(x, y, z)
            self.ruin_set(*debris, S("dark_oak_slab", type="bottom", waterlogged=False))
        for (x, z) in [(x, D - 2) for x in range(20, 25)] + [(1, z) for z in range(48, 52)] + \
                      [(x, 1) for x in range(50, 53)]:
            if self.get(x, 4, z) and "slab" in self.get(x, 4, z):
                self.ruin_set(x, 4, z)

    def moss_roofs(self):
        """Manchas de musgo en las cubiertas (tejas de madera cubiertas de piedra musgosa)."""
        for (x, y, z) in self.roofs:
            st = self.get(x, y, z)
            if not st or "dark_oak_stairs" not in st:
                continue
            if h(x // 4, z // 4, 11) < 0.5 and h(x, y, z, 5) < 0.85:
                self.ruin_set(x, y, z, st.replace("dark_oak_stairs", "mossy_cobblestone_stairs"))

    # ============================================================ túmulo
    def room(self, x1, x2, z1, z2, y1, y2, floor=SB, wall=COB, ceil=SB):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                for y in range(y1, y2 + 1):
                    self.s(x, y, z, "air")
                    self.carved[(x, y, z)] = (floor, wall, ceil)

    def lining(self, default=(SB, COB, SB)):
        """Recubre de piedra labrada las caras de la roca que dan al aire de la cripta (sin manantiales ni liquen)."""
        x0, x1, z0, z1, y0, y1 = CRYPT
        air = {p for p, (st, _) in self.t.blocks.items() if p[1] < 0 and st == "minecraft:air"}
        for (x, y, z) in air:
            mat = self.carved.get((x, y, z), default)
            for (dx, dy, dz) in ((0, -1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
                p = (x + dx, y + dy, z + dz)
                if p[1] >= 0 or self.get(*p) not in NATURAL:
                    continue
                self.s(*p, mat[0] if dy == -1 else mat[2] if dy == 1 else mat[1])

    def crypt(self):
        x0, x1, z0, z1, y0, y1 = CRYPT
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(y0, y1 + 1):
                    if self.get(x, y, z) is None:
                        self.s(x, y, z, "dirt" if y >= -2 else "stone")
        U = (F1, F1 + 3)                             # aire de las salas altas: pies -6 a -3
        self.room(25, 34, 45, 52, *U)                # vestíbulo de los antepasados
        self.room(35, 35, 48, 49, F1, F1 + 2)        # paso a la galería
        self.room(36, 52, 48, 51, *U)                # galería de los reyes
        self.room(53, 58, 45, 54, *U)                # sala de los ecos
        self.room(55, 56, 44, 44, F1, F1 + 2)        # paso al osario
        self.room(51, 60, 32, 43, *U)                # osario
        self.room(55, 56, 55, 61, F1, F1 + 2)        # pasillo del cable trampa
        self.room(47, 60, 62, 69, *U)                # sala de las ofrendas
        self.room(40, 46, 64, 65, F1, F1 + 2)        # pasillo a las runas
        self.room(34, 39, 57, 70, *U)                # sala de las runas
        T = ("spruce_planks", "spruce_planks", "stripped_spruce_log[axis=x]")
        self.room(15, 24, 53, 65, F2, F2 + 4, *T)    # cámara del jarl (de madera, como un túmulo de barco)
        self.room(19, 20, 52, 52, F2, F2 + 2, *T)    # paso al tesoro
        self.room(17, 22, 46, 51, F2, F2 + 3, *T)    # cámara del tesoro
        self.lining()
        self.vestibule()
        self.gallery()
        self.echoes()
        self.ossuary()
        self.trap_corridor()
        self.offerings()
        self.runes()
        self.jarl_chamber()
        self.treasury()
        self.lining()                                # lo que hayan abierto los mecanismos

    def vestibule(self):
        y = F1
        for x in (27, 32):                           # dos guerreros de piedra montan guardia
            self.t.entity(x, y, 46, armor_stand(0))
        for x in (26, 33):
            self.s(x, y, 46, "chiseled_stone_bricks")
        self.hang(29, F1 + 3, 48, soul=True)
        self.hang(30, F1 + 3, 48, soul=True)
        for z in (47, 50):
            self.banner(25, F1 + 2, z, "east", "black")
        self.sign(34, F1 + 1, 51, "west", "vestibulo",
                  [("Aquí duermen los", "Here sleep the"), ("reyes del salón.", "kings of the hall."),
                   ("Nadie despierte", "Let no one wake"), ("al jarl.", "the jarl.")])
        for (x, z) in ((25, 52), (34, 45)):
            self.s(x, y, z, S("candle", candles=2, lit=False, waterlogged=False))
        self.s(25, y, 45, S("decorated_pot", cracked=True, facing="south", waterlogged=False))

    def gallery(self):
        y = F1
        # nichos funerarios en los dos muros (el del norte tiene dos de grueso: tras él, la cámara del escaldo)
        for x in (37, 39, 47, 49):
            self.a(x, y, 47, x, y + 1, 47)
            self.s(x, y, 47, S("skeleton_skull", rotation=8, powered=False) if x in (37, 47) else "bone_block[axis=x]")
        for x in (38, 41, 44, 50):
            self.a(x, y, 52, x, y + 1, 52)
            self.s(x, y, 52, "bone_block[axis=y]" if x != 41 else S("skeleton_skull", rotation=0, powered=False))
        self.chest(38, y, 52, "north", "tumba")      # el ajuar de un rey menor
        self.spawner(49, y, 50, "zombie")
        # puerta secreta (puzle 2): un nicho sellado; la palanca, junto al pie del tercer rey
        rec = pieces.lever_door(self.s, (41, y, 46), "east", "south", "chiseled_stone_bricks", COB)
        self.mech["puerta_escaldo"] = rec
        self.room(41, 41, 45, 45, y, y + 1)
        self.room(38, 45, 39, 44, *(F1, F1 + 2))     # cámara del escaldo (oculta)
        self.chest(38, y, 39, "south", "escaldo")
        for x in (39, 40, 43, 44):
            self.s(x, y, 39, "bookshelf")
            self.s(x, y + 1, 39, "bookshelf")
        self.s(45, y, 39, "note_block[instrument=harp,note=0,powered=false]")
        self.s(45, y, 44, S("lectern", facing="west", has_book=False, powered=False))
        self.s(38, y, 44, S("candle", candles=3, lit=False, waterlogged=False))
        self.hang(42, y + 2, 41, soul=True)
        self.hidden += [(x, y, z) for x in range(38, 46) for z in range(40, 44)]

    def echoes(self):
        y = F1
        self.spawner(57, y, 50, "spider")
        for (x, yy, z) in ((53, y + 3, 45), (58, y + 3, 45), (53, y + 3, 54), (58, y + 3, 54), (58, y, 46), (57, y + 3, 50)):
            self.s(x, yy, z, "cobweb")
        self.s(53, y, 53, S("decorated_pot", cracked=True, facing="east", waterlogged=False))

    def ossuary(self):
        y = F1
        self.spawner(55, y, 37, "skeleton")
        self.chest(52, y, 33, "south", "osario")
        for (x, z) in ((51, 32), (60, 32), (51, 43), (60, 43), (60, 38), (51, 38)):
            self.s(x, y, z, "bone_block[axis=y]")
            self.s(x, y + 1, z, "bone_block[axis=y]")
            if (x + z) % 2:
                self.s(x, y + 2, z, S("skeleton_skull", rotation=4, powered=False))
        for (x, z) in ((53, 35), (58, 40), (57, 34), (53, 41)):
            self.s(x, y, z, "bone_block[axis=x]")
        for (x, z) in ((54, 33), (59, 42)):
            self.s(x, y, z, S("skeleton_skull", rotation=(x + z) % 16, powered=False))

    def trap_corridor(self):
        y = F1
        self.a(54, y, 58, 54, y + 1, 58)
        self.a(57, y, 58, 57, y + 1, 58)
        pieces.tripwire_trap(self.s, (54, 58), (57, 58), y, "x", [((54, y + 1, 58), "east"), ((57, y + 1, 58), "west")],
                             arrows=16)
        self.mech["ganchos"] = [(54, y, 58), (57, y, 58)]
        self.mech["dispensadores"] = [(54, y + 1, 58), (57, y + 1, 58)]

    def offerings(self):
        y = F1
        self.chest(59, y, 68, "west", "ofrendas")    # su pliego de la Crónica de los Heraldos
        for (x, z) in ((48, 62), (59, 62), (48, 69), (53, 69), (56, 69)):
            self.s(x, y, z, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        for x in (51, 57):
            self.s(x, y, 69, PTUFF)
            self.s(x, y + 1, 69, S("candle", candles=4, lit=True, waterlogged=False))
        self.hang(53, y + 3, 65, soul=True)
        self.hang(57, y + 3, 65, soul=True)
        for z in (63, 67):
            self.banner(60, y + 2, z, "west", "red")
        # la codicia: un cofre sobre un altar con una placa delante y dinamita debajo (trampa 2)
        self.s(48, y, 65, PTUFF)
        self.s(48, y, 66, PTUFF)
        self.chest(49, y, 65, "east", "codicia")
        self.s(49, y, 66, PTUFF)
        pieces.tnt_trap(self.s, 50, y, 65)
        pieces.tnt_trap(self.s, 50, y, 66)
        self.s(50, y - 1, 65, SB); self.s(50, y - 1, 66, SB)
        self.mech["placas"] = [(50, y, 65), (50, y, 66)]
        self.mech["tnt"] = [(50, y - 2, 65), (50, y - 2, 66)]

    def runes(self):
        """Muro de las runas (puzle 1): cuatro piedras rúnicas con palanca; solo el cuervo y el lobo despiertos y la
        serpiente y el oso dormidos abren la puerta. Las palancas falsas alimentan la línea directamente."""
        y = F1
        for z in range(57, 71):                      # cara del muro de las runas
            for yy in range(y, y + 4):
                self.s(33, yy, z, TUFF)
        rec = pieces.combo_door(self.s, (31, y, 59), "z", 1,
                                [((34, y + 1, 65), (33, y + 1, 65)), ((34, y + 1, 69), (33, y + 1, 69))],
                                name="runas", block=PTUFF)
        for z in (63, 67):                           # palancas falsas: polvo del bloque de la runa a la línea
            self.s(34, y + 1, z, S("lever", face="wall", facing="east", powered=False))
            self.s(32, y + 1, z, "redstone_wire[east=side,north=none,south=none,west=side,power=0]")
        for z in (63, 65, 67, 69):
            for yy in (y, y + 1, y + 2):
                self.s(33, yy, z, CTUFF)
        names = {63: ("serpiente", ("Ormr,", "Ormr,"), ("la serpiente", "the serpent")),
                 65: ("cuervo", ("Hrafn,", "Hrafn,"), ("el cuervo", "the raven")),
                 67: ("oso", ("Björn,", "Björn,"), ("el oso", "the bear")),
                 69: ("lobo", ("Ulfr,", "Ulfr,"), ("el lobo", "the wolf"))}
        for z, (key, l1, l2) in names.items():
            self.sign(34, y + 2, z, "east", "runa_" + key, [l1, l2])
        self.a(33, y, 59, 32, y + 1, 59)
        self.a(30, y, 59, 30, y + 1, 59)
        for x in (32, 33):
            self.carved[(x, y, 59)] = (SB, COB, SB)
        self.mech["runas"] = rec
        self.mech["palancas"] = [(34, y + 1, z) for z in (63, 65, 67, 69)]
        self.mech["solucion"] = (False, True, False, True)
        self.hang(37, y + 3, 60, soul=True)
        self.hang(37, y + 3, 67, soul=True)
        for z in (58, 70):
            self.banner(39, y + 2, z, "west", "black")
        # escalera estrecha al nivel bajo, hacia el oeste
        for i in range(6):                           # peldaños de arriba (cima a ras del paso) a abajo
            x, sy = 29 - i, -7 - i
            self.s(x, sy, 59, stair("stone_brick", "east"))
            for yy in range(sy + 1, sy + 4):
                self.s(x, yy, 59, "air")
                self.carved[(x, yy, 59)] = (SB, COB, SB)
        self.hidden += [(30, F1, 59)] + [(29 - i, -6 - i, 59) for i in range(6)]

    def jarl_chamber(self):
        y = F2
        for (x, z) in ((15, 53), (24, 53), (15, 65), (24, 65), (15, 59), (24, 57), (24, 61)):
            self.f(x, y, z, x, y + 4, z, S(SLOG, axis="y"))
        self.f(18, y, 57, 21, y, 61, PTUFF)          # el túmulo del jarl, abierto y vacío
        self.f(19, y + 1, 58, 20, y + 1, 60, S("spruce_slab", type="bottom", waterlogged=False))
        for (x, z) in ((16, 56), (23, 56), (16, 62), (23, 62)):
            self.s(x, y, z, S("decorated_pot", cracked=True, facing="east", waterlogged=False))
        for z in (55, 63):
            self.banner(15, y + 3, z, "east", "red")
            self.banner(24, y + 3, z, "west", "red")
        self.hang(19, y + 4, 55, soul=True)
        self.hang(20, y + 4, 63, soul=True)
        self.t.entity(20, y, 56, jarl())
        self.hidden += [(x, y, z) for x in range(16, 24) for z in range(54, 65) if not (18 <= x <= 21 and 57 <= z <= 61)]

    def treasury(self):
        y = F2
        self.chest(19, y, 46, "south", "premium")
        for x in (17, 22):
            self.f(x, y, 46, x, y + 3, 46, S(SLOG, axis="y"))
            self.s(x, y, 51, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        self.s(20, y, 46, "gold_block")
        self.s(20, y + 1, 46, S("candle", candles=3, lit=True, waterlogged=False))
        self.s(18, y, 46, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.hang(19, y + 3, 49, soul=True)
        self.hidden += [(x, y, z) for x in range(18, 22) for z in range(47, 51)]


# ------------------------------------------------------------------ entidades
def armor_stand(yaw):
    from nbtlib import Float, List
    return {"id": "minecraft:armor_stand", "ShowArms": B(1), "NoBasePlate": B(0), "Invulnerable": B(0),
            "Rotation": List[Float]([Float(yaw), Float(0)]),
            "equipment": {"head": {"id": "minecraft:iron_helmet", "count": 1},
                          "chest": {"id": "minecraft:chainmail_chestplate", "count": 1},
                          "mainhand": {"id": "minecraft:stone_axe", "count": 1}},
            "drop_chances": {"head": F(0.0), "chest": F(0.0), "mainhand": F(0.0)}}


def jarl():
    """El jarl Ulfgrim, el Insepulto: zombi con su hacha, yelmo y cota; sin refuerzos ni botín de equipo."""
    eq = {"mainhand": {"id": "minecraft:iron_axe", "count": 1},
          "head": {"id": "minecraft:iron_helmet", "count": 1},
          "chest": {"id": "minecraft:chainmail_chestplate", "count": 1},
          "legs": {"id": "minecraft:leather_leggings", "count": 1}}
    return guardian("zombie", K + "guardian", "Jarl Ulfgrim, el Insepulto", 60, armor=4, equipment=eq,
                    drop_chances={"mainhand": 0.0, "head": 0.1, "chest": 0.1, "legs": 0.0},
                    attributes={"attack_damage": 5, "knockback_resistance": 0.5, "follow_range": 24,
                                "spawn_reinforcements": 0},
                    extra={"IsBaby": B(0), "CanPickUpLoot": B(0), "CanBreakDoors": B(0)})
