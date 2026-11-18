"""Construcción del Laboratorio del micólogo en un único sistema de coordenadas (ver docs/unicas/laboratorio_micelio.md).

x de oeste a este (0..63), z de norte a sur (0..63; la entrada está al norte, z = 0); y = 0 es la capa de suelo del
jardín (pies a y = 1). Tres champiñones gigantes: el rojo grande (la casa del micólogo, con la escalera de caracol que
baja a las galerías), el rojo pequeño (los ayudantes) y el pardo (biblioteca de esporas en el tallo y secadero en el
sombrero), unidos por pasarelas. Lo que queda por debajo de y = 0 (las galerías) es otra pieza, que rellena toda su
caja. Todo se construye en una «obra» que luego se parte en dos plantillas (auditoria.preparar).
"""
import math, zlib
from core import Template, B
from .._common import pieces
from .._common.pieces import spawner, chest, guardian, text

SID = "laboratorio_micelio"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
W = D = 64
C = 31.5                      # centro del jardín (disco de radio R)
R, R_COURTYARD = 32, 28           # disco del suelo; dentro de R_PATIO, tierra de camino (fuera, micelio)
AIR_H = 8                     # aire explícito sobre el jardín (el terreno no asoma entre los edificios)

# champiñones gigantes: (x, z) del eje
RX, RZ = 32, 34               # rojo grande: casa del micólogo (eje de la escalera de caracol)
BX, BZ = 12, 30               # rojo pequeño: los ayudantes
PX, PZ = 50, 15               # pardo: biblioteca de esporas y secadero
F2, F1 = -11, -5              # pies de los dos niveles de galerías
CAP = 13                      # pies de la sala del sombrero rojo grande y del secadero del pardo
LOW = 7                       # pies del sombrero pequeño y de la pasarela baja
TUNNELS = (4, 61, 6, 61, -14, -1)      # caja de la pieza del subsuelo: x0, x1, z0, z1, y0, y1
NATURAL = ("minecraft:dirt", "minecraft:stone")

STEM = "mushroom_stem"
RED = "red_mushroom_block"
BROWN = "brown_mushroom_block"
PL, LOG, SLOG = "spruce_planks", "spruce_log", "stripped_spruce_log"
SB, CSB, MSB, CRSB = "stone_bricks", "chiseled_stone_bricks", "mossy_stone_bricks", "cracked_stone_bricks"
DS, CDS = "deepslate_tiles", "cobbled_deepslate"

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def slab(m, typ="bottom"):
    return S(f"{m}_slab", type=typ, waterlogged=False)


def h(*a):
    return zlib.crc32(",".join(map(str, a)).encode()) % 1000 / 1000.0


def dist(x, z, cx, cz):
    return math.hypot(x - cx, z - cz)


def disc(cx, cz, r):
    R_ = int(r) + 1
    return [(x, z) for x in range(int(cx) - R_, int(cx) + R_ + 2) for z in range(int(cz) - R_, int(cz) + R_ + 2)
            if dist(x, z, cx, cz) <= r]


def edge8(cells):
    """Celdas de `cells` con algún vecino (también en diagonal) fuera: barandillas sin huecos en diagonal."""
    s = set(cells)
    return [(x, z) for (x, z) in cells if any((x + a, z + b) not in s for a in (-1, 0, 1) for b in (-1, 0, 1))]


class Construction:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/obra")
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # celdas que solo se alcanzan resolviendo un puzle
        self.hidden_alcove = []    # celdas tras el tapiz (se alcanzan sin puzle)
        self.mech = {}             # mecanismos para el simulador y la prueba de servidor
        self.ruin = set()          # posiciones dañadas a mano (estado de conservación)
        self.carved = {}           # celdas de aire del subsuelo -> (suelo, muro, techo)
        self.signs = []
        self.animals = []

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

    def chest(self, x, y, z, facing, tbl, kind="chest"):
        chest(self.t.set, x, y, z, facing, LOOT + tbl, kind)
        self.chests.append(((x, y, z), tbl))

    def spawner(self, x, y, z, mob):
        spawner(self.t.set, x, y, z, mob, potentials=True)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=True, waterlogged=False))

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

    def brewing(self, x, y, z):
        self.s(x, y, z, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]",
               {"id": "minecraft:brewing_stand"})

    # ------------------------------------------------------------ construcción
    def build(self):
        self.ground()
        self.avenue()
        self.great_mushroom()
        self.small_mushroom()
        self.brown_mushroom()
        self.walkways()
        self.greenhouse()
        self.distillery()
        self.pen()
        self.galleries()
        self.garden_air()
        self.spores()
        self.weather()
        self.loose_debris()
        return self

    def loose_debris(self):
        """Lo que la ruina deja suelto (un trozo de sombrero entre dos huecos) se ha caído también."""
        from .._common.walkthrough import floating_blocks
        for _ in range(3):
            area = {p: st for p, (st, _) in self.t.blocks.items() if p[1] >= 0}
            fl = floating_blocks(area, (0,))
            if not fl:
                break
            for p in fl:
                self.ruin_set(*p)

    # ============================================================ superficie
    def courtyard(self, x, z):
        return dist(x, z, C, C) <= R_COURTYARD

    def roofed(self, x, z):
        """Hay algo macizo encima (invernadero, sombreros): ahí no cabe un champiñón gigante."""
        import lint
        return any(not lint.passable(self.get(x, y, z)) for y in range(2, 16) if self.get(x, y, z))

    def ground(self):
        """Suelo: tierra de camino en el jardín (no nacen champiñones gigantes en ella); fuera, micelio."""
        for x in range(W):
            for z in range(D):
                d = dist(x, z, C, C)
                if d <= R:
                    self.s(x, 0, z, "dirt_path" if d <= R_COURTYARD else "mycelium[snowy=false]")

    def avenue(self):
        """Senda de ladrillo de piedra de la entrada a la puerta del champiñón grande, con un cartel."""
        for z in range(0, RZ - 3):
            for x in (31, 32, 33):
                if dist(x, z, C, C) <= R:
                    self.s(x, 0, z, SB if h(x, z, 1) < 0.7 else MSB)
        self.mech["jig"] = (32, 0, 20)
        self.f(29, 0, 4, 29, 2, 4, S(STEM))
        self.sign(29, 2, 3, "north", "entrada", [("Jardín del", "Garden of"), ("micólogo", "the mycologist"),
                                                ("Se ruega no", "Please do not"), ("pisar las setas", "step on the fungi")])

    # ------------------------------------------------------------ champiñones gigantes
    def stem(self, cx, cz, r, y0, y1, hollow, floor=PL):
        """Tallo de radio r, hueco hasta `hollow`, de y0 a y1; con `floor`, el suelo del hueco en y = 0."""
        for (x, z) in disc(cx, cz, r):
            d = dist(x, z, cx, cz)
            if floor:
                self.s(x, 0, z, floor if d <= hollow else STEM)
            for y in range(y0, y1 + 1):
                self.s(x, y, z, "air" if d <= hollow else STEM)

    def cap(self, cx, cz, cy, rx, ry, block, floor_y, inner=1.3):
        """Sombrero en cúpula macizo (rx, ry) desde floor_y, hueco por dentro: devuelve las celdas (x, z) de la sala."""
        room = []
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            for z in range(int(cz - rx) - 1, int(cz + rx) + 2):
                for y in range(floor_y, int(cy + ry) + 1):
                    q = ((x - cx) ** 2 + (z - cz) ** 2) / rx ** 2 + ((y - cy) / ry) ** 2
                    if q > 1:
                        continue
                    qi = ((x - cx) ** 2 + (z - cz) ** 2) / (rx - inner) ** 2 + ((y - cy) / (ry - inner)) ** 2
                    if y > floor_y and qi <= 1:
                        self.s(x, y, z, "air")
                    elif y == floor_y and ((x - cx) ** 2 + (z - cz) ** 2) / (rx - inner) ** 2 + \
                            ((y + 1 - cy) / (ry - inner)) ** 2 <= 1:
                        self.s(x, y, z, PL)
                        room.append((x, z))
                    else:
                        self.s(x, y, z, block)
        return room

    def cut_door(self, cx, cz, y, side, kind="spruce_door"):
        """Puerta en la pared del sombrero hacia `side`: abre el paso desde la sala y pone la hoja en la última celda
        maciza. Devuelve la posición de la puerta."""
        dx, dz = DV[side]
        x, z = cx, cz
        last = None
        for _ in range(16):
            x, z = x + dx, z + dz
            if not self.free(x, y, z) or not self.free(x, y + 1, z):
                last = (x, z)
            elif last:
                break
        self.a(cx + dx, y, cz + dz, last[0], y + 1, last[1])
        for k in range(1, 16):
            px, pz = cx + dx * k, cz + dz * k
            if (px, pz) == last:
                break
            if self.get(px, y - 1, pz) is None or self.free(px, y - 1, pz):
                self.s(px, y - 1, pz, PL)
        self.door(last[0], y, last[1], side)
        return last

    def great_mushroom(self):
        """Champiñón rojo grande: tallo hueco de 7 de ancho con la escalera de caracol de las galerías al sombrero, y en el
        sombrero la casa del micólogo (estudio, alambique, cama) con la alcoba tras el tapiz."""
        self.stem(RX, RZ, 3.5, 0, CAP - 2, 1.5, floor=None)
        room = self.cap(RX, RZ, CAP - 1, 9.5, 7, RED, CAP - 1)
        self.great_room = set(room)
        # hueco de la escalera: anillo de 3 x 3 desde el fondo de las galerías hasta la sala del sombrero
        for y in range(F2, CAP + 1):
            for x in range(RX - 1, RX + 2):
                for z in range(RZ - 1, RZ + 2):
                    if y < 0:
                        self.room(x, x, z, z, y, y, PL, STEM, PL)
                    elif y != CAP - 1:
                        self.s(x, y, z, "air")
        pieces.spiral_stair(self.s, RX, RZ, [F2, F1, 1, LOW], "spruce_stairs", STEM, PL, newel_top=CAP + 1)
        for (dx, dz) in pieces.RING[:4]:                   # rellano de llegada al sombrero
            self.s(RX + dx, CAP - 1, RZ + dz, PL)
        dx, dz = pieces.RING[4]                             # hueco sobre el peldaño de debajo (altura libre)
        self.s(RX + dx, CAP - 1, RZ + dz, "air")
        for f in (1, LOW):                                  # luz en el tallo
            self.s(RX - 2, f + 2, RZ, "shroomlight")
            self.s(RX + 2, f + 4, RZ, "shroomlight")
        # puerta al jardín y a la pasarela baja (norte), y a la pasarela del secadero (este, desde la sala)
        for f in (1, LOW):
            self.a(RX, f, RZ - 2, RX, f + 1, RZ - 2)
            self.door(RX, f, RZ - 3, "north")
        self.mech["puerta_este"] = self.cut_door(RX, RZ, CAP, "east")
        self.house(RX, RZ)

    def house(self, cx, cz):
        y = CAP
        # alcoba al sur, tras un tabique de tallo con un paso tapado por el tapiz
        zw = cz + 5
        for (x, z) in self.great_room:
            if z == zw:
                for yy in range(y, y + 6):
                    if self.free(x, yy, z) and self.get(x, yy, z) is not None:
                        self.s(x, yy, z, STEM)
        self.a(cx, y, zw, cx, y + 1, zw)
        self.banner(cx, y + 2, zw - 1, "north", "red")
        self.hidden_alcove = [(x, y, z) for (x, z) in self.great_room
                              if z > zw and self.free(x, y, z) and self.free(x, y + 1, z)]
        self.chest(cx + 2, y, zw + 2, "west", "alcoba")
        self.s(cx - 2, y, zw + 1, S("lectern", facing="south", has_book=False, powered=False))
        self.hang(cx, y + 3, zw + 2)
        # estudio: mesa, atril, estanterías, alambique y la cama del micólogo
        self.bed(cx - 6, y, cz, "west", "red")
        self.s(cx - 6, y, cz - 2, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.chest(cx - 5, y, cz + 3, "east", "estudio")
        for x in range(cx - 2, cx + 3):
            self.s(x, y, cz - 6, "bookshelf")
            self.s(x, y + 1, cz - 6, "bookshelf")
        self.s(cx + 5, y, cz - 3, slab("spruce", "top"))
        self.s(cx + 5, y + 1, cz - 3, "potted_brown_mushroom")
        self.brewing(cx + 5, y, cz + 3)
        self.s(cx + 6, y, cz + 2, S("water_cauldron", level=3))
        for (x, z) in ((cx - 4, cz - 3), (cx + 3, cz - 4), (cx - 3, cz + 3), (cx + 4, cz + 4)):
            self.hang(x, y + 3, z)

    def small_mushroom(self):
        """Champiñón rojo pequeño: escalera de mano en el tallo y, en el sombrero, el dormitorio de los ayudantes."""
        self.stem(BX, BZ, 2.5, 1, LOW - 2, 1.5)
        room = self.cap(BX, BZ, LOW - 1, 6.5, 4.5, RED, LOW - 1, inner=1.2)
        self.small_room = set(room)
        for y in range(1, LOW):
            self.s(BX - 1, y, BZ, S("ladder", facing="east", waterlogged=False))
        self.s(BX - 1, LOW - 1, BZ, S("ladder", facing="east", waterlogged=False))
        self.s(BX - 2, LOW - 1, BZ, STEM)
        self.door(BX + 2, 1, BZ, "east")
        self.mech["puerta_pequena"] = self.cut_door(BX, BZ, LOW, "east")
        y = LOW
        self.bed(BX - 3, y, BZ - 2, "west", "brown")
        self.bed(BX - 3, y, BZ + 2, "west", "brown")
        self.chest(BX, y, BZ - 3, "south", "ayudantes")
        self.chest(BX, y, BZ + 3, "north", "ayudantes")
        self.s(BX + 2, y, BZ + 3, "crafting_table")
        self.hang(BX + 1, y + 2, BZ)

    def brown_mushroom(self):
        """Champiñón pardo: tallo ancho con la biblioteca de esporas y el herbario; en el sombrero plano, el secadero."""
        top = CAP - 1
        self.stem(PX, PZ, 4.5, 1, top - 1, 3.0)
        for (x, z) in disc(PX, PZ, 8.5):
            self.s(x, top, z, BROWN)
        mid = 6
        for (x, z) in disc(PX, PZ, 3.0):
            self.s(x, mid, z, PL)
        # escalera de mano en el muro este, de la biblioteca al secadero
        lx = PX + 3
        for y in range(1, top + 1):
            self.s(lx, y, PZ, S("ladder", facing="west", waterlogged=False))
        self.door(PX - 4, 1, PZ, "west")
        self.s(PX - 3, 1, PZ, "air")
        self.s(PX - 3, 2, PZ, "air")
        # biblioteca (pies 1)
        y = 1
        inner = set(disc(PX, PZ, 3.0))
        wall = [(x, z) for (x, z) in inner if any((x + a, z + b) not in inner for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for (x, z) in wall:
            if (x, z) in ((PX - 3, PZ), (lx, PZ), (PX + 3, PZ - 1), (PX + 3, PZ + 1)):
                continue
            for yy in (y, y + 1, y + 2):
                self.s(x, yy, z, "bookshelf")
        self.chest(PX, y, PZ - 3, "south", "biblioteca")          # su pliego de la Crónica de los Heraldos
        self.s(PX, y, PZ + 3, S("lectern", facing="north", has_book=False, powered=False))
        self.s(PX, y, PZ, slab("spruce", "top"))
        self.s(PX, y + 1, PZ, S("candle", candles=3, lit=False, waterlogged=False))
        self.hang(PX - 1, mid - 1, PZ - 1)
        self.hang(PX + 1, mid - 1, PZ + 1)
        self.sign(PX - 1, y + 1, PZ - 2, "south", "biblioteca", [("Esporoteca:", "Spore library:"),
                                                                  ("cada cepa", "every strain"),
                                                                  ("en su frasco.", "in its jar.")])
        # herbario (pies 7): vasijas con muestras y macetas
        y = mid + 1
        for (x, z) in ((PX - 2, PZ - 2), (PX + 2, PZ - 2), (PX - 2, PZ + 2), (PX + 2, PZ + 2), (PX - 3, PZ)):
            self.s(x, y, z, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        for (x, z, pot) in ((PX, PZ - 3, "potted_red_mushroom"), (PX, PZ + 3, "potted_brown_mushroom"),
                            (PX - 1, PZ - 3, "potted_crimson_fungus"), (PX + 1, PZ + 3, "potted_warped_fungus")):
            self.s(x, y, z, pot)
        self.chest(PX - 2, y, PZ - 1, "east", "herbario", kind="barrel")
        self.hang(PX, top - 1, PZ)
        # secadero (pies 13 sobre el sombrero): barandilla, toneles, compostadores y faroles
        y = CAP
        cap = disc(PX, PZ, 8.5)
        rim = edge8(cap)
        gate = (PX, PZ + 8)
        for (x, z) in rim:
            if abs(x - gate[0]) <= 0 and z >= PZ + 7:
                continue
            self.s(x, y, z, "spruce_fence")
        for (x, z) in cap:
            if (x, z) not in rim:
                for yy in range(y, y + 3):
                    if self.free(x, yy, z) and self.get(x, yy, z) is None:
                        self.s(x, yy, z, "air")
        for (x, z) in ((PX - 5, PZ - 4), (PX + 5, PZ - 4), (PX - 5, PZ + 4), (PX + 5, PZ + 4)):
            self.s(x, y, z, S("composter", level=5))
        for (x, z) in ((PX - 6, PZ), (PX - 6, PZ + 1)):
            self.s(x, y, z, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.chest(PX + 6, y, PZ, "west", "secadero", kind="barrel")
        for (x, z) in ((PX - 3, PZ - 7), (PX + 3, PZ - 7)):
            self.s(x, y + 1, z, S("lantern", hanging=False, waterlogged=False))
        # el hueco de la escalera de mano en el sombrero
        self.s(lx, top, PZ, S("ladder", facing="west", waterlogged=False))

    # ------------------------------------------------------------ pasarelas
    def deck(self, x, y, z, along):
        self.s(x, y, z, PL)
        for side in ((0, 1), (0, -1)) if along == "x" else ((1, 0), (-1, 0)):
            px, pz = x + side[0], z + side[1]
            if self.free(px, y + 1, pz) and self.get(px, y, pz) is None:
                self.s(px, y + 1, pz, "spruce_fence")
                self.s(px, y, pz, PL)
        for yy in (y + 1, y + 2, y + 3):
            if self.get(x, yy, z) is None:
                self.s(x, yy, z, "air")

    def post(self, x, z, y_top):
        for y in range(1, y_top + 1):
            self.s(x, y, z, S(STEM))

    def walkways(self):
        """Pasarela baja (pies 7) del tallo grande al sombrero pequeño y alta (pies 13) del sombrero grande al secadero."""
        y = LOW - 1
        dz = RZ - 3 - 1                                     # delante de la puerta norte de la pasarela baja
        door_small = self.mech["puerta_pequena"]
        self.deck(RX, y, dz, "z")
        for x in range(door_small[0] + 1, RX):
            self.deck(x, y, dz, "x")
        self.post(RX - 8, dz, y - 1)
        self.post(RX - 15, dz, y - 1)
        # alta: sale por el este del sombrero grande, sigue hacia el este y gira al norte hasta el secadero
        y = CAP - 1
        ex, ez = self.mech["puerta_este"]
        for x in range(ex + 1, PX + 1):
            self.deck(x, y, ez, "x")
        for z in range(PZ + 9, ez):
            self.deck(PX, y, z, "z")
        self.s(PX + 1, y + 1, ez, "spruce_fence")
        self.s(PX + 1, y, ez, PL)
        self.s(PX, y, ez + 1, PL)
        self.s(PX, y + 1, ez + 1, "spruce_fence")
        self.post(PX, ez, y - 1)
        self.post(ex + 4, ez, y - 1)
        self.post(PX, PZ + 12, y - 1)

    # ------------------------------------------------------------ invernadero, destilería y corral
    def greenhouse(self):
        """Invernadero de cristal con cultivos raros: verruga del Nether, flor antorcha, bayas, cacao, coro y bayas
        luminosas colgadas del caballete."""
        x1, x2, z1, z2 = 9, 23, 41, 53
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                wall = x in (x1, x2) or z in (z1, z2)
                corner = x in (x1, x2) and z in (z1, z2)
                self.s(x, 0, z, SB)
                if wall:
                    post = corner or (x - x1) % 4 == 0 and z in (z1, z2) or (z - z1) % 4 == 0 and x in (x1, x2)
                    for y in range(1, 5):
                        self.s(x, y, z, S(SLOG, axis="y") if post else (SB if y == 1 else "glass_pane"))
                else:
                    for y in range(1, 5):
                        self.s(x, y, z, "air")
        # cubierta a dos aguas de cristal con caballete de troncos
        zc = (z1 + z2) // 2
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                rise = (z2 - z1) // 2 - abs(z - zc)
                y = 5 + rise // 2
                self.s(x, y, z, S(SLOG, axis="x") if z == zc or x in (x1, x2) else "glass")
                for yy in range(5, y):
                    if x in (x1, x2):
                        self.s(x, yy, z, "glass")
                    elif self.get(x, yy, z) is None:
                        self.s(x, yy, z, "air")
        door_x = 16
        self.door(door_x, 1, z1, "north")
        for x in range(x1 + 1, x2):
            if x == door_x:
                continue
            self.s(x, 0, z1 + 1, "soul_sand")
            self.s(x, 1, z1 + 1, S("nether_wart", age=3))
            self.s(x, 0, z1 + 2, S("farmland", moisture=7))
            self.s(x, 1, z1 + 2, S("torchflower_crop", age=1))
            self.s(x, 0, z1 + 3, "water[level=0]")
            self.s(x, 0, z1 + 4, S("farmland", moisture=7))
            self.s(x, 1, z1 + 4, S("beetroots", age=3))
        for z in range(z1 + 1, z2):
            self.s(door_x, 0, z, "dirt_path" if z != z1 + 3 else SB)
        # al fondo: bayas, cacao en troncos de jungla y un coro sobre piedra del End
        for x in range(x1 + 1, x2):
            if x == door_x:
                continue
            if x in (x1 + 2, x2 - 2):
                self.f(x, 1, z2 - 2, x, 3, z2 - 2, S("jungle_log", axis="y"))
                self.s(x, 0, z2 - 2, SB)
                self.s(x, 2, z2 - 3, S("cocoa", age=2, facing="south"))
                self.s(x - 1, 2, z2 - 2, S("cocoa", age=2, facing="east"))
            elif x in (x1 + 4, x1 + 5, x2 - 4, x2 - 5):
                self.s(x, 0, z2 - 1, "grass_block[snowy=false]")
                self.s(x, 1, z2 - 1, S("sweet_berry_bush", age=3))
        self.s(x1 + 1, 0, z2 - 1, "end_stone")
        self.s(x1 + 1, 1, z2 - 1, S("chorus_flower", age=5))
        for x in (x1 + 3, x2 - 3):
            self.s(x, 6, zc, S(SLOG, axis="x"))
            self.s(x, 5, zc, S("cave_vines_plant", berries=True))
            self.s(x, 4, zc, S("cave_vines", age=25, berries=True))
        self.chest(x2 - 1, 1, z1 + 5, "west", "invernadero")
        self.s(x1 + 1, 1, z1 + 5, S("composter", level=3))
        self.s(x1 + 1, 1, z1 + 6, S("barrel", facing="up"), {"id": "minecraft:barrel"})

    def distillery(self):
        """Destilería de pociones: muros de ladrillo con postes de tallo, alambiques en el mostrador, calderos y toneles."""
        x1, x2, z1, z2 = 42, 54, 42, 52
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                wall = x in (x1, x2) or z in (z1, z2)
                self.s(x, 0, z, SB if wall else PL)
                for y in range(1, 5):
                    if wall:
                        post = (x in (x1, x2) and z in (z1, z2)) or (x in (x1, x2) and z == (z1 + z2) // 2) \
                            or (z in (z1, z2) and x == (x1 + x2) // 2)
                        self.s(x, y, z, S(STEM) if post else (SB if y < 4 else PL))
                    else:
                        self.s(x, y, z, "air")
        # cubierta a dos aguas de tejas pardas (escaleras de pícea) sobre un forjado
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                self.s(x, 5, z, PL)
        xc = (x1 + x2) // 2
        for k in range(0, 4):
            for z in range(z1 - 1, z2 + 2):
                self.s(xc - 6 + k, 6 + k, z, S("spruce_stairs", facing="east", half="bottom", shape="straight",
                                               waterlogged=False))
                self.s(xc + 6 - k, 6 + k, z, S("spruce_stairs", facing="west", half="bottom", shape="straight",
                                               waterlogged=False))
                for x in range(xc - 5 + k, xc + 6 - k):
                    if k == 3 or x in (xc - 5 + k, xc + 5 - k):
                        self.s(x, 6 + k, z, PL)
            for x in range(xc - 5 + k, xc + 6 - k):
                for z in (z1 - 1, z2 + 1):
                    pass
        for z in range(z1 - 1, z2 + 2):
            self.s(xc, 10, z, slab("spruce"))
        for k in range(0, 4):                                     # hastiales
            for x in range(xc - 5 + k, xc + 6 - k):
                for z in (z1, z2):
                    self.s(x, 6 + k, z, PL)
        self.door(xc, 1, z1, "north")
        self.s(x1 - 1 + 1, 2, (z1 + z2) // 2 - 2, "glass_pane")
        for z in ((z1 + z2) // 2 - 2, (z1 + z2) // 2 + 2):
            self.s(x1, 2, z, "glass_pane")
            self.s(x2, 2, z, "glass_pane")
        # mostrador de los alambiques al sur, calderos al este y toneles al oeste
        for x in range(x1 + 2, x2 - 1):
            self.s(x, 1, z2 - 1, slab("smooth_stone", "top"))
        for x in (x1 + 3, x1 + 6, x2 - 3):
            self.brewing(x, 2, z2 - 1)
        for z in (z1 + 2, z1 + 4):
            self.s(x2 - 1, 1, z, S("water_cauldron", level=3))
        self.s(x2 - 1, 1, z1 + 3, S("cauldron"))
        for z in range(z1 + 2, z1 + 6):
            self.s(x1 + 1, 1, z, S("barrel", facing="east"), {"id": "minecraft:barrel"})
        self.chest(x1 + 1, 1, z1 + 7, "east", "destileria")
        self.chest(x2 - 1, 1, z2 - 2, "west", "destileria", kind="barrel")
        self.s(xc, 1, z1 + 5, "copper_block")
        self.s(xc, 2, z1 + 5, "waxed_copper_grate")
        self.s(xc, 3, z1 + 5, "lightning_rod[facing=up,powered=false,waterlogged=false]")
        self.hang(xc - 3, 4, z1 + 4)
        self.hang(xc + 3, 4, z2 - 3)
        self.sign(xc + 1, 2, z1 + 1, "south", "destileria", [("Destilería", "Distillery"),
                                                             ("Nada sale de", "Nothing leaves"),
                                                             ("aquí sin su", "here without"),
                                                             ("etiqueta.", "its label.")])

    def pen(self):
        """Corral de los champiñocas: cercado, comedero de heno y un abrevadero."""
        x1, x2, z1, z2 = 10, 20, 9, 18
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x in (x1, x2) or z in (z1, z2):
                    self.s(x, 1, z, "spruce_fence")
                else:
                    self.s(x, 0, z, "packed_mud" if h(x, z, 3) < 0.4 else "dirt_path")
                    for y in range(1, 4):
                        self.s(x, y, z, "air")
        self.s(15, 1, z2, S("spruce_fence_gate", facing="south", in_wall=False, open=False, powered=False))
        for (x, z) in ((x1 + 1, z1 + 1), (x1 + 1, z1 + 2), (x1 + 2, z1 + 1)):
            self.s(x, 1, z, "hay_block[axis=y]")
        self.s(x2 - 1, 1, z1 + 1, S("water_cauldron", level=3))
        self.s(x2 - 2, 1, z1 + 1, S("water_cauldron", level=3))
        self.chest(x1 + 1, 1, z2 - 1, "north", "corral", kind="barrel")
        for i, (x, z, variant) in enumerate(((13, 13, "red"), (17, 14, "red"), (15, 11, "brown"))):
            self.animals.append((x, 1, z))
            self.t.entity(x, 1, z, {"id": "minecraft:mooshroom", "PersistenceRequired": B(1), "Type": variant,
                                    "Age": 0})

    # ------------------------------------------------------------ acabados de la superficie
    def garden_air(self):
        for x in range(W):
            for z in range(D):
                if not self.courtyard(x, z):
                    continue
                for y in range(1, AIR_H + 1):
                    if self.get(x, y, z) is None:
                        self.s(x, y, z, "air")

    def spores(self):
        """Setas pequeñas en el anillo de micelio (sobre micelio sobreviven con cualquier luz)."""
        for x in range(W):
            for z in range(D):
                if self.get(x, 0, z) == "minecraft:mycelium[snowy=false]" and self.get(x, 1, z) is None \
                        and h(x, z, 5) < 0.12:
                    self.s(x, 1, z, "red_mushroom" if h(x, z, 6) < 0.5 else "brown_mushroom")

    def weather(self):
        """El jardín lleva años sin cuidar: los sombreros tienen la copa carcomida y manchas pardas de podredumbre, la
        cubierta del invernadero ha perdido cristales, la de la destilería se ha hundido en una esquina y las barandillas
        tienen tramos caídos."""
        lamps = {(x, z) for (x, y, z), (st, _) in self.t.blocks.items() if "lantern" in st or "chain" in st}
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if "red_mushroom_block" not in st or y < LOW:
                continue
            exposed = self.free(x, y + 1, z)
            if not exposed or (x, z) in lamps:
                continue
            big = dist(x, z, RX, RZ) < 11 and y >= CAP + 3
            small = dist(x, z, BX, BZ) < 7 and y >= LOW + 2
            if (big or small) and h(x // 2, y // 2, z // 2, 13) < 0.42 and h(x, y, z, 6) < 0.85:
                self.ruin_set(x, y, z)                              # agujeros en la copa
            elif h(x // 3, y // 2, z // 3, 41) < 0.35 and h(x, y, z, 42) < 0.8:
                self.ruin_set(x, y, z, BROWN)                       # podredumbre parda
        peeled = S(STEM, down=False, east=False, north=False, south=False, up=False, west=False)
        for (x, y, z), (st, _) in list(self.t.blocks.items()):   # piel del tallo desprendida (se ve la carne porosa)
            if st == "minecraft:" + STEM and y >= 1 and any(self.free(x + a, y, z + c) for a, _, c in N6[:2] + N6[4:]) \
                    and h(x // 2, y // 3, z // 2, 71) < 0.3 and h(x, y, z, 72) < 0.85:
                self.ruin_set(x, y, z, peeled)
        for (x, y, z), (st, _) in list(self.t.blocks.items()):   # cristales rotos de la cubierta del invernadero
            if st == "minecraft:glass" and h(x // 2, z // 2, 31) < 0.55:
                self.ruin_set(x, y, z)
        for (x, y, z), (st, _) in list(self.t.blocks.items()):   # la esquina hundida de la cubierta de la destilería
            if "spruce_stairs" in st and y >= 6 and x >= 49 and z >= 48 and h(x, y, z, 51) < 0.75:
                self.ruin_set(x, y, z)
        for (x, y, z), (st, _) in list(self.t.blocks.items()):   # barandillas rotas en las pasarelas y el secadero
            if st.startswith("minecraft:spruce_fence[") and y >= LOW and h(x, y, z, 61) < 0.18:
                self.ruin_set(x, y, z)
        for (x, z) in ((10, 12), (20, 15), (13, 9)):             # cerca del corral rota
            self.ruin_set(x, 1, z)

    # ============================================================ subsuelo
    def room(self, x1, x2, z1, z2, y1, y2, floor=SB, wall=SB, ceil=SB):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                for y in range(y1, y2 + 1):
                    self.s(x, y, z, "air")
                    self.carved[(x, y, z)] = (floor, wall, ceil)

    def lining(self, default=(SB, SB, SB)):
        """Recubre las caras de la roca que dan al aire del subsuelo (sin manantiales ni liquen)."""
        air = {p for p, (st, _) in self.t.blocks.items() if p[1] < 0 and st == "minecraft:air"}
        for (x, y, z) in air:
            mat = self.carved.get((x, y, z), default)
            for (dx, dy, dz) in N6:
                p = (x + dx, y + dy, z + dz)
                if p[1] >= 0 or self.get(*p) not in NATURAL:
                    continue
                self.s(*p, mat[0] if dy == -1 else mat[2] if dy == 1 else mat[1])

    def galleries(self):
        x0, x1, z0, z1, y0, y1 = TUNNELS
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(y0, y1 + 1):
                    if self.get(x, y, z) is None:
                        self.s(x, y, z, "dirt" if y >= -2 else "stone")
        U, L = (F1, F1 + 3), (F2, F2 + 3)
        DAMP = ("mycelium[snowy=false]", "mud_bricks", "packed_mud")       # galerías húmedas de los criaderos
        LAB = (SB, SB, SB)
        STEM_PROFILE = (PL, STEM, PL)
        OSC = (DS, CDS, DS)
        # nivel alto
        self.room(RX, RX, RZ - 5, RZ - 2, F1, F1 + 1, *STEM_PROFILE)       # del tallo a los criaderos
        self.room(22, 42, 18, 28, *U, *DAMP)                          # criaderos de setas
        self.room(21, 21, 23, 23, F1, F1 + 1, *LAB)                  # puerta del laboratorio
        self.room(10, 20, 18, 28, *U, *LAB)                          # laboratorio
        self.room(43, 43, 23, 23, F1, F1 + 1, *STEM_PROFILE)                # puerta del pasillo de las esporas
        self.room(44, 52, 22, 23, F1, F1 + 2, *STEM_PROFILE)                # pasillo del cable trampa
        self.room(53, 59, 16, 28, *U, *DAMP)                          # criadero abandonado (arañas)
        # nivel bajo
        self.room(RX, RX, RZ - 5, RZ - 2, F2, F2 + 1, *STEM_PROFILE)       # del tallo a la galería de la luz
        self.room(22, 42, 20, 28, *L, *DAMP)                          # galería de la luz
        self.room(21, 21, 24, 24, F2, F2 + 1, *DAMP)                  # puerta de los capullos
        self.room(10, 20, 18, 28, *L, *DAMP)                          # sala de los capullos (arañas de cueva)
        self.room(43, 43, 24, 24, F2, F2 + 1, *LAB)                  # puerta de los experimentos
        self.room(44, 56, 18, 28, *L, *LAB)                          # experimentos fallidos (zombis)
        self.room(40, 40, 29, 35, F2, F2 + 1, *LAB)                  # pasillo a la sala de los reactivos
        self.room(37, 43, 36, 52, *L, *LAB)                          # sala de los reactivos (puzle 1)
        self.room(18, 32, 38, 52, F2, F2 + 5, *OSC)                  # cámara de la cepa madre (guardián)
        self.room(25, 26, 53, 54, F2, F2 + 2, *OSC)                  # paso al tesoro
        self.room(21, 30, 55, 59, *L, *STEM_PROFILE)                        # cámara del tesoro
        self.lining()
        self.nurseries()
        self.laboratory()
        self.trap_corridor()
        self.abandoned()
        self.light_gallery()
        self.cocoons()
        self.failed()
        self.reagents()
        self.mother_strain()
        self.treasury()
        self.lining()                                                # lo que hayan abierto los mecanismos

    def bed_of_fungi(self, x1, x2, z1, z2, y):
        """Bancal de micelio con setas, a ras de suelo (el micelio ya es el suelo de los criaderos)."""
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                self.s(x, y - 1, z, "mycelium[snowy=false]")
                if h(x, z, y, 8) < 0.55:
                    self.s(x, y, z, "red_mushroom" if h(x, z, 9) < 0.5 else "brown_mushroom")

    def nurseries(self):
        """Criaderos de setas (nivel alto): bancales elevados con setas, setas luminosas en el techo y dos cofres."""
        y = F1
        for (x1, x2) in ((24, 29), (35, 40)):
            for (z1, z2) in ((19, 21), (25, 27)):
                for x in range(x1, x2 + 1):
                    for z in range(z1, z2 + 1):
                        edge = x in (x1, x2) or z in (z1, z2)
                        self.s(x, y, z, "mud_bricks" if edge else "mycelium[snowy=false]")
                        if not edge:
                            self.s(x, y + 1, z, "red_mushroom" if h(x, z, 2) < 0.5 else "brown_mushroom")
        for (x, z) in ((32, 20), (32, 26), (27, 23), (37, 23)):
            self.s(x, y + 4, z, "shroomlight")
        for x in (23, 41):
            for z in (19, 27):
                self.s(x, y + 3, z, S("glow_lichen", up=True, north=False, south=False, east=False, west=False,
                                      down=False, waterlogged=False))
        self.chest(22, y, 18, "south", "criadero")
        self.chest(42, y, 28, "north", "criadero")
        self.sign(31, y + 1, 28, "north", "criaderos", [("Criaderos", "Nurseries"), ("Humedad: alta", "Humidity: high"),
                                                        ("Luz: la justa", "Light: just so")])

    def laboratory(self):
        """Laboratorio (nivel alto): mesas, alambiques, calderos y la receta de la cura; tras el panel de tallo del muro
        norte (puzle 2), el cepario."""
        y = F1
        for x in range(12, 19):
            self.s(x, y, 28, slab("smooth_stone", "top"))
        for x in (13, 16):
            self.brewing(x, y + 1, 28)
        self.s(10, y, 22, S("water_cauldron", level=3))
        self.s(10, y, 24, S("water_cauldron", level=3))
        self.s(10, y, 23, "crafting_table")
        for z in (20, 26):
            self.s(20, y, z, S("barrel", facing="west"), {"id": "minecraft:barrel"})
        self.chest(10, y, 27, "east", "laboratorio")
        for x in (12, 18):
            self.s(x, y, 23, slab("spruce", "top"))
            self.s(x, y + 1, 23, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        self.s(15, y, 23, slab("spruce", "top"))
        self.s(15, y + 1, 23, S("candle", candles=2, lit=False, waterlogged=False))
        self.hang(14, y + 3, 21)
        self.hang(14, y + 3, 26)
        self.sign(19, y + 1, 18, "south", "receta", [("La cura del", "The cure for"), ("micelio: espora,", "mycelium: spore,"),
                                                     ("verruga y luz.", "wart and light."), ("Nada más.", "Nothing else.")])
        # puerta secreta (puzle 2): un panel de tallo del muro norte se recoge; la palanca, a ras de suelo junto a él
        rec = pieces.lever_door(self.s, (13, y, 16), "east", "south", STEM, SB)
        self.mech["puerta_cepario"] = rec
        self.room(13, 13, 15, 15, y, y + 1, *(PL, STEM, PL))
        self.room(10, 18, 9, 14, y, y + 2, *(PL, STEM, PL))          # cepario (oculto)
        self.chest(11, y, 9, "south", "cepario")
        for x in (12, 13, 14, 16, 17, 18):
            self.s(x, y, 9, "bookshelf")
            self.s(x, y + 1, 9, S("decorated_pot", cracked=False, facing="south", waterlogged=False))
        self.s(18, y, 12, S("lectern", facing="west", has_book=False, powered=False))
        self.hang(14, y + 2, 11, soul=True)
        self.hidden += [(x, y, z) for x in range(10, 19) for z in range(10, 15)]

    def trap_corridor(self):
        y = F1
        self.a(48, y, 21, 48, y + 1, 21)
        self.a(48, y, 24, 48, y + 1, 24)
        pieces.tripwire_trap(self.s, (48, 21), (48, 24), y, "z", [((48, y + 1, 21), "south"), ((48, y + 1, 24), "north")],
                             arrows=16)
        self.mech["ganchos"] = [(48, y, 21), (48, y, 24)]
        self.mech["dispensadores"] = [(48, y + 1, 21), (48, y + 1, 24)]

    def abandoned(self):
        """Criadero abandonado: bancales podridos, telarañas, un generador de arañas y un cofre, a oscuras."""
        y = F1
        self.spawner(57, y, 25, "spider")
        for (x, yy, z) in ((53, y + 3, 16), (59, y + 3, 16), (55, y + 3, 27), (58, y, 17), (53, y + 2, 28)):
            self.s(x, yy, z, "cobweb")
        for z in range(18, 23):
            self.s(59, y, z, "mud_bricks")
            self.s(59, y + 1, z, S("brown_mushroom"))
        self.chest(54, y, 17, "south", "galeria")
        self.s(56, y, 20, S("decorated_pot", cracked=True, facing="north", waterlogged=False))

    def light_gallery(self):
        """Galería de la luz (nivel bajo): micelio, setas luminosas en el techo, liquen y un cofre."""
        y = F2
        for (x, z) in ((30, 22), (34, 22), (30, 26), (34, 26), (32, 24)):
            self.s(x, y + 4, z, "shroomlight")
        for x in (28, 36):
            for z in (21, 27):
                self.s(x, y + 3, z, S("glow_lichen", up=True, north=False, south=False, east=False, west=False,
                                      down=False, waterlogged=False))
        self.bed_of_fungi(24, 27, 20, 21, y)
        self.bed_of_fungi(37, 40, 27, 28, y)
        self.chest(22, y, 28, "north", "galeria")

    def cocoons(self):
        y = F2
        self.spawner(13, y, 21, "cave_spider")
        for (x, yy, z) in ((10, y + 3, 18), (11, y + 3, 18), (10, y + 2, 18), (20, y + 3, 18), (16, y + 3, 28),
                           (12, y, 25), (17, y + 3, 22), (14, y + 3, 26)):
            self.s(x, yy, z, "cobweb")
        self.chest(18, y, 28, "north", "capullos")
        for (x, z) in ((10, 28), (11, 28)):
            self.s(x, y, z, "mushroom_stem")

    def failed(self):
        """Experimentos fallidos: jaulas de barrotes vacías, mesas volcadas y un generador de zombis, a oscuras."""
        y = F2
        self.spawner(52, y, 21, "zombie")
        for (cx, cz) in ((46, 19), (46, 27), (55, 27)):
            for (dx, dz) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if 44 <= cx + dx <= 56 and 18 <= cz + dz <= 28:
                    for yy in (y, y + 1):
                        self.s(cx + dx, yy, cz + dz, "iron_bars")
        for x in range(48, 51):
            self.s(x, y, 28, slab("smooth_stone", "top"))
        self.s(49, y + 1, 28, S("brewing_stand", has_bottle_0=True, has_bottle_1=False, has_bottle_2=False),
               {"id": "minecraft:brewing_stand"})
        self.chest(56, y, 24, "west", "experimentos")
        self.sign(44, y + 1, 23, "north", "experimentos", [("Prueba 31:", "Trial 31:"), ("fallida.", "failed."),
                                                           ("Prueba 32:", "Trial 32:"), ("en mí.", "on myself.")])

    def reagents(self):
        """Sala de los reactivos (puzle 1): cinco frascos con su palanca; la cura del cartel del laboratorio (espora,
        verruga y luz) abre la puerta; los falsos alimentan la línea directamente."""
        y = F2
        for z in range(36, 53):                            # cara del muro de los reactivos
            for yy in range(y, y + 4):
                self.s(36, yy, z, SB)
        good = [((37, y + 1, 46), (36, y + 1, 46)), ((37, y + 1, 50), (36, y + 1, 50)), ((37, y + 1, 52), (36, y + 1, 52))]
        rec = pieces.combo_door(self.s, (34, y, 40), "z", 1, good, name="reactivos", block=CSB)
        for z in (44, 48):                                 # frascos falsos: polvo del bloque del frasco a la línea
            self.s(37, y + 1, z, S("lever", face="wall", facing="east", powered=False))
            self.s(35, y + 1, z, "redstone_wire[east=side,north=none,south=none,west=side,power=0]")
        for z in (44, 46, 48, 50, 52):
            for yy in (y, y + 1, y + 2):
                self.s(36, yy, z, "polished_andesite")
        names = {44: ("ojo", ("Ojo de", "Spider"), ("araña", "eye")),
                 46: ("espora", ("Espora", "Red"), ("roja", "spore")),
                 48: ("polvora", ("Pólvora", "Gun-"), ("", "powder")),
                 50: ("verruga", ("Verruga", "Nether"), ("del Nether", "wart")),
                 52: ("luz", ("Polvo de", "Glowstone"), ("piedra luminosa", "dust"))}
        for z, (key, l1, l2) in names.items():
            self.sign(37, y + 2, z, "east", "reactivo_" + key, [l1, l2] if l2[0] else [l1])
        self.a(36, y, 40, 35, y + 1, 40)
        self.a(33, y, 40, 33, y + 1, 40)
        for x in (33, 35, 36):
            self.carved[(x, y, 40)] = (SB, SB, SB)
            self.carved[(x, y + 1, 40)] = (SB, SB, SB)
        self.mech["reactivos"] = rec
        self.mech["palancas"] = [(37, y + 1, z) for z in (44, 46, 48, 50, 52)]
        self.mech["solucion"] = (False, True, False, True, True)
        self.hang(41, y + 3, 40, soul=True)
        self.hang(41, y + 3, 48, soul=True)
        # la codicia: el armario de reactivos al fondo de un nicho con placas (trampa 2: flechas desde los lados)
        self.a(44, y, 38, 45, y + 1, 38)
        pieces.plate_trap(self.s, [(44, y, 38), (45, y, 38)], "north", arrows=16)
        self.chest(46, y, 38, "west", "reactivos")
        self.mech["placas"] = [(44, y, 38), (45, y, 38)]
        self.mech["flechas"] = [(44, y, 37), (44, y, 39), (45, y, 37), (45, y, 39)]
        for z in (42, 51):
            self.s(43, y, z, S("barrel", facing="west"), {"id": "minecraft:barrel"})

    def mother_strain(self):
        """Cámara de la cepa madre: un champiñón gigante creciendo bajo tierra, setas luminosas y el micólogo."""
        y = F2
        cx, cz = 25, 45
        self.f(cx, y, cz, cx, y + 3, cz, STEM)
        for (x, z) in disc(cx, cz, 3.5):
            self.s(x, y + 4, z, RED)
        for (x, z) in ((cx - 2, cz), (cx + 2, cz), (cx, cz - 2), (cx, cz + 2)):
            self.s(x, y + 5, z, "shroomlight")
        for (x, z) in disc(cx, cz, 6.2):
            d = dist(x, z, cx, cz)
            if 5.2 < d <= 6.2 and (x + z) % 2 == 0:
                self.s(x, y - 1, z, "mycelium[snowy=false]")
                self.s(x, y, z, "red_mushroom" if (x * z) % 3 else "brown_mushroom")
        for z in (40, 50):
            self.banner(18, y + 3, z, "east", "brown")
        self.hang(20, y + 4, 40, soul=True)
        self.hang(30, y + 4, 50, soul=True)
        self.chest(19, y, 51, "north", "cepa")
        self.t.entity(cx + 3, y, cz + 3, mycologist())
        self.hidden += [(x, y, z) for x in range(19, 33) for z in range(38, 53)]

    def treasury(self):
        y = F2
        self.chest(25, y, 59, "north", "premium")
        self.s(26, y, 59, "gold_block")
        self.s(26, y + 1, 59, S("candle", candles=3, lit=True, waterlogged=False))
        self.s(24, y, 59, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        for (x, z) in ((21, 55), (30, 55), (21, 59), (30, 59)):
            self.s(x, y, z, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        for (x, z) in ((22, 57), (29, 57)):
            self.f(x, y, z, x, y + 3, z, STEM)
        self.hang(25, y + 3, 57, soul=True)
        self.hidden += [(x, y, z) for x in range(22, 30) for z in range(56, 59)] + [(25, y, 53), (26, y, 54)]


# ------------------------------------------------------------------ guardián
def mycologist():
    """Maese Ambrosio, el Esporado: un esqueleto pantanoso (las setas ya le crecen) con un sombrero de champiñón."""
    return guardian("bogged", K + "guardian", "Maese Ambrosio, el Esporado", 50, armor=4,
                    equipment={"head": {"id": "minecraft:red_mushroom_block", "count": 1}},
                    drop_chances={"head": 0.0},
                    attributes={"follow_range": 20, "knockback_resistance": 0.3})
