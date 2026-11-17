"""Construcción de la colonia de la Mina perdida de Hondavena en un único sistema de coordenadas
(diseño en docs/unicas/mina_perdida.md).

x de oeste a este, z de norte a sur; y = 0 es la capa de suelo de la gran caverna (pies a y = 1), que en el mundo queda
a y = PISO. Todo lo que se excava (aire o agua) se registra con su forro (suelo, muro, techo); al acabar, `forro()` pone
ese forro en cada cara que da a lo excavado y `casco()` lo rodea de roca maciza (2 bloques más). Fuera del casco no se
escribe nada: la plantilla deja el terreno (structure_void), así que la colonia no es una caja y una cueva vanilla que
pase cerca solo ve roca irregular. El pozo sube por la columna EJE hasta la cara superior (y = YTOP); por encima siguen
las piezas del pozo y el castillete (superficie.py), que coloca el tipo de estructura heraldia:mina en Java.
"""
import math, zlib
from core import B
from .._comun import piezas
from .._comun.piezas import spawner, chest, guardian, text

SID = "mina_perdida"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
PISO = 20                    # y del mundo de la capa de suelo de la caverna (ver docs: por qué esta altura)
YTOP = 26                    # cara superior de la colonia: aquí empieza el pozo
EJE = (44, 7)                # eje del pozo maestro (x, z)
HONDO = -12                  # por debajo de esta capa (y del mundo < 8) el casco es de pizarra abismal

# gran caverna: superelipse
CX, CZ, RX, RZ, EXP = 44, 36, 27, 21, 6
LAGO = (44, 49, 13, 5)       # centro y radios del lago (superelipse de exponente 4)
SIMA = (75, 79, 25, 47)      # x0, x1, z0, z1 de la sima (y -15 .. 8)
F_SIMA, F_HONDO, F_INUND = -15, -10, -5   # pies: fondo de la sima, filón madre, pasarela del sector inundado

COB, MCOB, CDS = "cobblestone", "mossy_cobblestone", "cobbled_deepslate"
SB, CSB, CRSB = "stone_bricks", "chiseled_stone_bricks", "cracked_stone_bricks"
PL, LOG, SLOG = "spruce_planks", "spruce_log", "stripped_spruce_log"
DT = "deepslate_tiles"
# forros (suelo, muro, techo): nunca bloques naturales (`#base_stone_overworld`, tierra, grava...), para que dentro no
# salgan manantiales, liquen, musgo ni charcas de arcilla de las cuevas exuberantes
ROCA = ("roca", "roca", "roca")              # caverna y galerías: piedra labrada a pico (adoquín variado)
OBRA = (SB, SB, SB)
CASA = (PL, SB, PL)
FUND = (DT, "bricks", DT)
HOND = (DT, CDS, CDS)
POZO = (PL, PL, PL)
NATURAL = ("stone", "deepslate", "tuff", "andesite", "granite", "diorite", "dirt", "gravel", "sand", "clay", "calcite",
           "grass_block", "moss_block", "rooted_dirt", "coarse_dirt", "mud", "dripstone_block")

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def stair(m, facing, half="bottom"):
    return S(f"{m}_stairs", facing=facing, half=half, shape="straight", waterlogged=False)


def slab(m, typ="bottom"):
    return S(f"{m}_slab", type=typ, waterlogged=False)


def h(*a):
    """Azar determinista en [0, 1)."""
    return zlib.crc32(",".join(map(str, a)).encode()) % 10007 / 10007.0


def ruido(x, z, esc, sal=0):
    """Ruido de valor suave en [-1, 1] (bilineal sobre una malla de paso `esc`)."""
    gx, gz = x / esc, z / esc
    x0, z0 = math.floor(gx), math.floor(gz)
    fx, fz = gx - x0, gz - z0
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    v = lambda a, b: h(sal, a, b) * 2 - 1
    top = v(x0, z0) * (1 - fx) + v(x0 + 1, z0) * fx
    bot = v(x0, z0 + 1) * (1 - fx) + v(x0 + 1, z0 + 1) * fx
    return top * (1 - fz) + bot * fz


def superelipse(x, z, cx, cz, rx, rz, e):
    return (abs(x - cx) / rx) ** e + (abs(z - cz) / rz) ** e


def roca(x, y, z):
    """Piedra labrada a pico de las paredes de la caverna: adoquín con vetas de adoquín de pizarra."""
    return CDS if ruido(x + y, z - y, 5, 7) > 0.45 else COB


class Obra:
    def __init__(self):
        from core import Template
        self.t = Template(f"unicas/{SID}/obra")
        self.carved = {}           # celda excavada -> forro (suelo, muro, techo)
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # celdas que solo se alcanzan resolviendo un puzle
        self.hidden_alcove = []    # celdas tras el tapiz (sin puzle)
        self.mech = {}             # mecanismos para la auditoría y la prueba de servidor
        self.ruin = set()          # posiciones dañadas a mano
        self.signs = []
        self.cavern = set()        # columnas (x, z) de la gran caverna
        self.lago = set()          # columnas (x, z) del lago
        self.hull = set()          # roca del casco (no forro)

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def f(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def carve(self, x, y, z, pal, st="air"):
        self.s(x, y, z, st)
        self.carved[(x, y, z)] = pal

    def room(self, x1, x2, z1, z2, y1, y2, pal):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.carve(x, y, z, pal)

    def chest(self, x, y, z, facing, tabla, kind="chest", waterlogged=False):
        chest(self.t.set, x, y, z, facing, LOOT + tabla, kind, waterlogged=waterlogged)
        self.chests.append(((x, y, z), tabla))

    def spawner(self, x, y, z, mob):
        spawner(self.t.set, x, y, z, mob, potentials=True)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=True, waterlogged=False))

    def stand(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=False, waterlogged=False))

    def door(self, x, y, z, facing, hinge="left", kind="spruce_door"):
        piezas.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="brown"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="brown"):
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="spruce"):
        """Cartel traducible: `lines` = [(es, en)] (las claves van a LANG con el sufijo .1, .2...)."""
        self.signs.append((key, lines))
        piezas.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
                    wood=wood)

    def sign_post(self, x, y, z, rotation, key, lines, wood="spruce"):
        """Cartel de pie (rotación 0-15; 0 mira al sur) sobre el suelo."""
        self.signs.append((key, lines))
        msgs = [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)]
        msgs += [{"text": ""}] * (4 - len(msgs))
        self.s(x, y, z, S(f"{wood}_sign", rotation=rotation, waterlogged=False),
               {"id": "minecraft:sign", "is_waxed": B(1),
                "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
                "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})

    def ruin_set(self, x, y, z, st="air"):
        self.s(x, y, z, st)
        self.ruin.add((x, y, z))

    def barrel(self, x, y, z, facing="up"):
        self.s(x, y, z, S("barrel", facing=facing, open=False), {"id": "minecraft:barrel"})

    def rail(self, x, y, z, shape, kind="rail", powered=None):
        p = {"shape": shape, "waterlogged": False}
        if powered is not None:
            p = {"powered": powered, "shape": shape, "waterlogged": False}
        self.s(x, y, z, S(kind, **p))

    # ------------------------------------------------------------ obra completa
    def build(self):
        self.caverna()
        self.estacion()
        self.almacen()
        self.fundicion()
        self.casas()
        self.talleres()
        self.lago_y_embarcadero()
        self.sima()
        self.cargadero()
        self.frente_viejo()
        self.filon_madre()
        self.sector_derrumbado()
        self.forro()
        self.casco()
        # lo que va dentro de muros y suelos (mecanismos, vetas, adornos) después del casco
        self.amueblar()
        self.forro()
        self.casco()
        self.t.blocks = {p: v for p, v in self.t.blocks.items() if p[1] <= YTOP}
        return self

    # ------------------------------------------------------------ forro y casco
    def forro(self):
        """Pone el forro en cada celda sin escribir que toca una excavada (por su cara: suelo, muro o techo)."""
        for (x, y, z), pal in list(self.carved.items()):
            if self.get(x, y, z) not in ("minecraft:air", "minecraft:water", "minecraft:cave_air") and \
                    not self.get(x, y, z).startswith("minecraft:water"):
                continue
            for (dx, dy, dz) in N6:
                p = (x + dx, y + dy, z + dz)
                if p in self.t.blocks:
                    continue
                mat = pal[0] if dy == -1 else pal[2] if dy == 1 else pal[1]
                self.s(*p, roca(*p) if mat == "roca" else mat)

    def casco(self, grosor=2):
        """Dos capas de roca maciza (6-vecinos) alrededor de todo lo escrito junto a una celda excavada."""
        frontier = set()
        for (x, y, z) in self.carved:
            for (dx, dy, dz) in N6:
                p = (x + dx, y + dy, z + dz)
                if p in self.t.blocks and p not in self.carved:
                    frontier.add(p)
        for _ in range(grosor):
            nxt = set()
            for (x, y, z) in frontier:
                for (dx, dy, dz) in N6:
                    p = (x + dx, y + dy, z + dz)
                    if p not in self.t.blocks:
                        nxt.add(p)
            for p in nxt:
                self.s(*p, "deepslate" if p[1] < HONDO else "stone")
                self.hull.add(p)
            frontier = nxt

    # ------------------------------------------------------------ la gran caverna
    def techo(self, x, z):
        e = superelipse(x, z, CX, CZ, RX, RZ, 2)
        return 5 + int(round(11 * math.sqrt(max(0.0, 1 - min(e, 1.0))) + 1.2 * ruido(x, z, 6, 3)))

    def caverna(self):
        for x in range(CX - RX - 2, CX + RX + 3):
            for z in range(CZ - RZ - 2, CZ + RZ + 3):
                if superelipse(x, z, CX, CZ, RX, RZ, EXP) > 1 + 0.08 * ruido(x, z, 4, 1):
                    continue
                self.cavern.add((x, z))
                for y in range(1, self.techo(x, z) + 1):
                    self.carve(x, y, z, ROCA)
        # suelo de la caverna: adoquín pisado; plaza de andesita pulida alrededor del pilar maestro
        for (x, z) in self.cavern:
            d = math.hypot(x - CX, z - CZ)
            self.s(x, 0, z, "polished_andesite" if 3 < d <= 8.5 else (CDS if h(x, z, 4) < 0.2 else COB))
        # pilar maestro: roca que los mineros dejaron para sostener la bóveda
        for x in range(CX - 3, CX + 4):
            for z in range(CZ - 3, CZ + 4):
                d = math.hypot(x - CX, z - CZ)
                if d <= 2.6:
                    for y in range(1, self.techo(x, z) + 1):
                        self.s(x, y, z, SB if y <= 2 else (CSB if y == 3 else roca(x, y, z)))
                        self.carved.pop((x, y, z), None)
        for (dx, dz) in ((0, -6), (0, 6), (-6, 0), (6, 0)):
            self.hang(CX + dx, self.techo(CX + dx, CZ + dz) - 4, CZ + dz)
        self.sign(CX, 2, CZ - 3, "north", "pilar", [("Hondavena", "Hondavena"), ("Colonia minera", "Mining colony"),
                                                    ("de la Corona", "of the Crown")])
        self.sign(CX, 2, CZ + 3, "south", "lago", [("Al sur:", "South:"), ("el lago y", "the lake and"),
                                                   ("el embarcadero", "the landing")])
        self.sign(CX + 3, 2, CZ, "east", "puente", [("Al este:", "East:"), ("el puente y", "the bridge and"),
                                                    ("el cargadero", "the loading bay")])
        self.sign(CX - 3, 2, CZ, "west", "casas", [("Al oeste:", "West:"), ("las casas", "the miners'"),
                                                   ("de los mineros", "houses")])
        # derrumbes sueltos junto a las paredes (ruina) y faroles en los caminos
        for (x, z) in ((22, 26), (66, 44), (25, 50), (60, 22), (36, 18), (52, 54), (30, 52), (63, 33)):
            for (a, b, y) in ((0, 0, 1), (1, 0, 1), (0, 1, 1), (0, 0, 2)):
                if (x + a, z + b) in self.cavern:
                    self.ruin_set(x + a, y, z + b, "cobblestone" if (a + b + y) % 2 else "gravel")
        for (x, z) in ((47, 20), (34, 30), (56, 30), (34, 42), (56, 42), (44, 44), (30, 22), (64, 26)):
            self.hang(x, self.techo(x, z) - 3, z)

    def boundary(self, z, side):
        """x de la primera columna de la caverna en la fila z, desde el oeste o el este."""
        xs = [x for (x, zz) in self.cavern if zz == z]
        return min(xs) if side == "west" else max(xs)

    # ------------------------------------------------------------ estación del pozo (norte)
    def estacion(self):
        ex, ez = EJE
        self.room(43, 51, 3, 12, 1, 5, OBRA)
        self.room(ex - 1, ex + 1, ez - 1, ez + 1, 6, YTOP, POZO)          # el pozo maestro
        self.room(45, 49, 13, 17, 1, 4, OBRA)                            # a la caverna
        for y in range(1, YTOP + 1):
            self.s(ex - 1, y, ez, S("ladder", facing="east", waterlogged=False))
        for y in range(2, YTOP + 1):
            self.s(ex, y, ez, S("iron_chain", axis="y", waterlogged=False))
        self.s(ex, 1, ez, "cauldron")                                    # la cubeta del malacate, en el fondo
        for y in range(8, YTOP + 1, 4):                                  # marcos de madera del pozo
            for d in (-1, 0, 1):
                for (px, pz, ax) in ((ex + d, ez - 2, "x"), (ex + d, ez + 2, "x"), (ex - 2, ez + d, "z"), (ex + 2, ez + d, "z")):
                    self.s(px, y, pz, S(SLOG, axis=ax))
        self.mech["eje"] = (ex, YTOP, ez)
        self.mech["entrada"] = (ex - 1, 1, ez)
        self.chest(51, 1, 4, "west", "estacion")
        self.barrel(51, 1, 5, "west")
        self.barrel(51, 2, 5, "west")
        self.s(51, 1, 6, "crafting_table")
        self.sign(46, 2, 3, "south", "pozo", [("Pozo maestro", "Master shaft"), ("Bajada: 1 hora", "Descent: 1 hour"),
                                              ("Sin farol", "No lamp,"), ("no se baja", "no descent")])
        for z in (9, 11):
            self.s(43, 1, z, slab("spruce", "top"))
        self.hang(47, 5, 8)
        self.hang(47, 4, 15)
        for y in (1, 2, 3):
            for x in (44, 50):
                self.s(x, y, 13, S(LOG, axis="y"))
        for x in range(44, 51):
            self.s(x, 4, 13, S(LOG, axis="x"))
        for z in range(13, 20):                                          # vía de las vagonetas hacia la plaza
            if (47, z) in self.cavern or z <= 17:
                self.rail(47, 1, z, "north_south")
        self.ruin_set(47, 1, 18, "air")                                  # un tramo arrancado

    # ------------------------------------------------------------ almacén (noroeste)
    def almacen(self):
        self.room(24, 36, 5, 12, 1, 4, OBRA)
        self.room(28, 32, 13, 18, 1, 3, OBRA)
        for x in range(25, 36, 2):
            self.barrel(x, 1, 5, "south")
            if x % 4 == 1:
                self.barrel(x, 2, 5, "south")
        for z in (7, 9, 11):
            self.s(24, 1, z, "hay_block[axis=x]")
        self.s(36, 1, 7, "smithing_table")
        self.chest(36, 1, 8, "west", "almacen")
        self.chest(36, 1, 11, "west", "almacen")
        self.hang(30, 4, 8)
        self.sign(26, 2, 12, "north", "almacen", [("Almacén", "Storehouse"), ("Víveres y", "Stores and"),
                                                  ("herramientas", "tools")])

    # ------------------------------------------------------------ fundición (noreste)
    def fundicion(self):
        self.room(54, 68, 3, 12, 1, 6, FUND)
        self.room(58, 62, 13, 19, 1, 4, FUND)
        for x in (56, 59, 62, 65):
            self.s(x, 1, 3, S("blast_furnace", facing="south", lit=False), {"id": "minecraft:blast_furnace"})
            self.s(x, 2, 3, "bricks")
        for x in range(55, 68):                                          # campana de ladrillo sobre los hornos
            self.s(x, 4, 3, "bricks")
            self.s(x, 5, 3, "bricks")
            self.s(x, 4, 4, stair("brick", "north", "top"))
        for x in (57, 64):
            self.s(x, 1, 3, S("lava_cauldron"))
        self.s(60, 1, 7, S("anvil", facing="east"))
        self.s(62, 1, 7, S("grindstone", face="floor", facing="north"))
        for (x, z) in ((55, 10), (55, 11), (56, 11), (55, 9)):
            self.s(x, 1, z, "coal_block")
        self.s(55, 2, 11, "coal_block")
        for (x, z, b) in ((67, 10, "raw_iron_block"), (67, 11, "raw_iron_block"), (66, 11, "raw_copper_block"),
                          (67, 9, "raw_copper_block")):
            self.s(x, 1, z, b)
        self.chest(68, 1, 6, "west", "fundicion")
        self.barrel(68, 1, 7, "west")
        self.hang(64, 4, 8)
        self.hang(58, 6, 9)
        self.sign(56, 2, 12, "north", "fundicion", [("Fundición", "Foundry"), ("Hierro y cobre", "Iron and copper"),
                                                    ("de Hondavena", "of Hondavena")])

    # ------------------------------------------------------------ casas de los mineros (oeste)
    def fachada(self, zd, half, side):
        """x de la fachada (recta) para la casa de la fila zd, con porche hasta la caverna."""
        rows = range(zd - half, zd + half + 1)
        if side == "west":
            fx = min(self.boundary(z, "west") for z in rows) - 1
            for z in rows:
                for x in range(fx + 1, self.boundary(z, "west")):
                    for y in range(1, 5):
                        self.carve(x, y, z, ROCA)
        else:
            fx = max(self.boundary(z, "east") for z in rows) + 1
            for z in rows:
                for x in range(self.boundary(z, "east") + 1, fx):
                    for y in range(1, 5):
                        self.carve(x, y, z, ROCA)
        return fx

    def casa(self, zd, key, tabla=None, derrumbada=False):
        fx = self.fachada(zd, 3, "west")
        x1, x2 = fx - 7, fx - 1
        self.room(x1, x2, zd - 3, zd + 2, 1, 4, CASA)
        for z in range(zd - 3, zd + 3):                       # fachada de ladrillo de piedra con puerta y ventana
            for y in range(1, 5):
                self.s(fx, y, z, SB)
        self.door(fx, 1, zd, "east", "left")
        self.s(fx, 2, zd + 2, S("glass_pane"))
        self.s(fx, 2, zd - 2, S("glass_pane"))
        self.bed(x1, 1, zd - 3, "west", "brown" if zd % 2 else "gray")
        if not derrumbada:
            self.s(x1, 1, zd + 2, "furnace[facing=east,lit=false]", {"id": "minecraft:furnace"})
            self.s(x1 + 2, 1, zd + 2, "crafting_table")
        self.hang(x1 + 3, 4, zd)
        if tabla:
            self.chest(x1, 1, zd - 1, "east", tabla)
        self.s(x1 + 4, 1, zd + 2, slab("spruce", "top"))
        self.s(x1 + 5, 1, zd + 2, slab("spruce", "top"))
        self.s(x1 + 4, 2, zd + 2, S("flower_pot"))
        if derrumbada:                                        # techo hundido en la mitad del fondo
            for (x, z) in ((x1, zd + 2), (x1 + 1, zd + 2), (x1, zd + 1), (x1 + 1, zd + 1), (x1 + 2, zd + 2)):
                self.ruin_set(x, 1, z, "gravel" if (x + z) % 2 else COB)
            self.ruin_set(x1, 2, zd + 2, "gravel")
            for (x, z) in ((x1, zd + 1), (x1 + 1, zd + 2)):
                self.ruin_set(x, 5, z, "air")                 # el techo que cayó
                self.carved[(x, 5, z)] = CASA
        return fx, x1, x2

    def casas(self):
        self.casa(19, "a", "vivienda")
        fx, x1, x2 = self.casa_capataz(29)
        self.casa(39, "c", "vivienda")
        self.casa(48, "d", "vivienda", derrumbada=True)
        self.sign(self.fachada_x[29] + 1, 3, 31, "east", "capataz", [("Casa del", "Foreman's"), ("capataz", "house")])

    def casa_capataz(self, zd):
        """Casa del capataz: más ancha; tras la estantería con palanca del muro oeste, su despacho (puzle 2)."""
        fx = self.fachada(zd, 4, "west")
        self.fachada_x = {zd: fx}
        x1, x2 = fx - 8, fx - 1
        self.room(x1, x2, zd - 4, zd + 3, 1, 4, CASA)
        for z in range(zd - 4, zd + 4):
            for y in range(1, 5):
                self.s(fx, y, z, SB)
        self.door(fx, 1, zd, "east", "left")
        for z in (zd - 2, zd + 2):
            self.s(fx, 2, z, S("glass_pane"))
        self.bed(x1 + 1, 1, zd + 3, "south", "red")
        self.s(x1 + 2, 1, zd + 3, S("candle", candles=2, lit=False, waterlogged=False))
        self.chest(x2, 1, zd - 4, "south", "capataz")
        for x in range(x1 + 3, x1 + 6):
            self.s(x, 1, zd + 3, "bookshelf")
        self.s(x1 + 4, 1, zd, slab("spruce", "top"))                     # mesa con dos sillas
        self.s(x1 + 4, 1, zd - 1, stair("spruce", "south"))
        self.s(x1 + 4, 1, zd + 1, stair("spruce", "north"))
        self.hang(x1 + 4, 4, zd - 2)
        self.hang(x1 + 4, 4, zd + 2)
        # puerta secreta: en el muro oeste (de dos de grueso) un panel se recoge hacia el norte por dentro del muro; la
        # palanca, en una estantería empotrada en el rincón (piezas.lever_door)
        wall = x1 - 2
        rec = piezas.lever_door(self.s, (wall, 1, zd), "north", "east", SB, SB)
        self.s(x1 - 1, 1, rec["lever"][2], "bookshelf")                 # el bloque de la palanca es una estantería
        for y in (1, 2):
            self.carved[(x1 - 1, y, zd)] = CASA
        self.mech["puerta_despacho"] = rec
        ox1, ox2 = wall - 6, wall - 1
        self.room(ox1, ox2, zd - 2, zd + 2, 1, 4, CASA)                  # despacho oculto
        self.chest(ox1, 1, zd - 2, "east", "despacho")
        self.s(ox1, 1, zd + 2, S("lectern", facing="east", has_book=False, powered=False))
        for z in range(zd - 1, zd + 2):
            self.s(ox1, 1, z, "bookshelf")
            self.s(ox1, 2, z, "bookshelf")
        self.s(ox1 + 2, 1, zd, slab("spruce", "top"))
        self.s(ox1 + 2, 2, zd, S("candle", candles=3, lit=False, waterlogged=False))
        self.hang(ox1 + 3, 4, zd, soul=True)
        self.sign(ox2 - 1, 2, zd - 2, "south", "vias", [("A la báscula:", "Weighbridge:"),
                                                        ("aguja 1, norte;", "switch 1, north;"),
                                                        ("aguja 2, este.", "switch 2, east."),
                                                        ("— Tizón", "— Tizon")])
        self.hidden += [(x, 1, z) for x in range(ox1, ox2 + 1) for z in range(zd - 2, zd + 3)]
        return fx, x1, x2

    # ------------------------------------------------------------ herrería y carpintería (este)
    def taller(self, zd, key, tabla):
        fx = self.fachada(zd, 3, "east")
        x1, x2 = fx + 1, fx + 7
        self.room(x1, x2, zd - 3, zd + 2, 1, 4, OBRA)
        for z in range(zd - 3, zd + 3):
            for y in range(1, 5):
                self.s(fx, y, z, SB)
        self.carve(fx, 1, zd, OBRA)
        self.carve(fx, 2, zd, OBRA)
        self.carve(fx, 1, zd - 1, OBRA)
        self.carve(fx, 2, zd - 1, OBRA)
        self.chest(x2, 1, zd + 2, "west", tabla)
        self.hang(x1 + 3, 4, zd)
        return x1, x2

    def talleres(self):
        x1, x2 = self.taller(20, "herreria", "herreria")
        self.s(x1 + 2, 1, 17, S("anvil", facing="north"))
        self.s(x1 + 4, 1, 17, S("smithing_table"))
        self.s(x2, 1, 17, S("blast_furnace", facing="west", lit=False), {"id": "minecraft:blast_furnace"})
        self.s(x2, 1, 18, S("grindstone", face="floor", facing="west"))
        self.s(x2, 1, 20, S("lava_cauldron"))
        self.sign(x1, 3, 18, "east", "herreria", [("Herrería", "Smithy")])
        x1, x2 = self.taller(52, "carpinteria", "carpinteria")
        for z in (49, 50):
            self.f(x2, 1, z, x2, 2, z, S(SLOG, axis="x"))
        self.s(x1 + 2, 1, 49, "crafting_table")
        self.s(x1 + 3, 1, 49, S("stonecutter", facing="south"))
        self.s(x1 + 5, 1, 49, "fletching_table")
        self.barrel(x2, 1, 51, "west")
        self.sign(x1, 3, 50, "east", "carpinteria", [("Carpintería", "Carpentry"), ("Entibos y", "Props and"),
                                                     ("traviesas", "sleepers")])

    # ------------------------------------------------------------ lago subterráneo y embarcadero (sur)
    def lago_y_embarcadero(self):
        lx, lz, rx, rz = LAGO
        for x in range(lx - rx, lx + rx + 1):
            for z in range(lz - rz, lz + rz + 1):
                if superelipse(x, z, lx, lz, rx, rz, 4) <= 1 and (x, z) in self.cavern:
                    self.lago.add((x, z))
                    self.carve(x, 0, z, ROCA)
                    for y in (-3, -2, -1):
                        self.carve(x, y, z, ("gravel" if h(x, z, 5) < 0.5 else "sand", "roca", "roca"), "water")
        # el muelle: tablas a ras del suelo, pilotes hasta el fondo
        for x in (43, 44, 45):
            for z in range(43, 50):
                if (x, z) in self.lago:
                    self.s(x, 0, z, PL)
                    self.carved.pop((x, 0, z), None)
        for (x, z) in ((43, 46), (45, 46), (43, 49), (45, 49)):
            for y in (-3, -2, -1):
                self.s(x, y, z, S(LOG, axis="y"))
                self.carved.pop((x, y, z), None)
        for x in (43, 45):
            self.s(x, 1, 49, "spruce_fence")
            self.stand(x, 2, 49)
        self.ruin_set(45, 0, 47, "air")                                  # una tabla suelta
        self.carved[(45, 0, 47)] = ROCA
        self.chest(43, 1, 43, "east", "embarcadero")
        self.barrel(45, 1, 43)
        self.t.entity(47, -1, 47, {"id": "minecraft:oak_boat", "PersistenceRequired": B(1)})
        self.mech["barca"] = (47, -1, 47)
        self.sign_post(44, 1, 42, 8, "embarcadero", [("Embarcadero", "Landing"), ("Prohibido", "No swimming")])
        # el cobertizo de las barcas en la orilla sur y, tras el tapiz, el alijo
        self.room(40, 48, 58, 63, 1, 4, CASA)
        for x in range(42, 47):
            for z in range(self.cz_sur(x), 58):
                for y in range(1, 4):
                    self.carve(x, y, z, ROCA)
        self.barrel(40, 1, 63)
        self.barrel(48, 1, 63)
        self.s(41, 1, 63, "crafting_table")
        for x in (40, 48):
            self.f(x, 1, 59, x, 1, 61, S(SLOG, axis="z"))
        self.hang(44, 4, 61)
        self.banner(44, 3, 63, "north", "blue")                         # tapiz que tapa el paso al alijo
        for y in (1, 2):
            self.carve(44, y, 64, CASA)
        self.room(41, 47, 65, 69, 1, 3, CASA)
        self.chest(41, 1, 69, "east", "alijo")
        self.barrel(47, 1, 69)
        self.s(47, 1, 65, S("candle", candles=1, lit=False, waterlogged=False))
        self.hidden_alcove += [(x, 1, z) for x in range(41, 48) for z in range(65, 70)]

    def cz_sur(self, x):
        return max(z for (xx, z) in self.cavern if xx == x) + 1

    # ------------------------------------------------------------ la sima y el puente colgante (este)
    def sima(self):
        x0, x1, z0, z1 = SIMA
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                top = 8 - (1 if h(x, z, 11) < 0.3 else 0)
                for y in range(F_SIMA, top + 1):
                    self.carve(x, y, z, ROCA)
        for z in range(34, 39):                                          # cornisa desde la caverna
            for x in range(self.boundary(z, "east") + 1, x0):
                for y in range(1, 5):
                    self.carve(x, y, z, ROCA)
        for x in range(x0, x1 + 1):                                      # el puente: 3 de ancho, barandillas
            for z in (35, 36, 37):
                self.s(x, 0, z, PL if z == 36 else S("spruce_slab", type="top", waterlogged=False))
            for z in (35, 37):
                if not (x == x1 and z == 37):
                    self.s(x, 1, z, "spruce_fence")
            if x in (x0, x0 + 2, x1):
                for z in (35, 37):
                    if not (x == x1 and z == 37):
                        for y in range(2, 9):
                            self.s(x, y, z, S("iron_chain", axis="y", waterlogged=False))
        for (x, z) in ((x0 + 1, 35), (x0 + 3, 37)):                      # tablas y barandilla que faltan, fuera del paso
            self.ruin_set(x, 0, z, "air")
            self.ruin_set(x, 1, z, "air")
        for y in range(F_SIMA, 2):                                       # escalera de mano al fondo
            self.s(x1, y, 38, S("ladder", facing="west", waterlogged=False))
        self.hang(73, 4, 36)
        self.sign(x0 - 1, 2, 34, "south", "sima", [("La Sima", "The Chasm"), ("Puente para", "Bridge for"),
                                                   ("uno a uno", "one at a time")])
        # fondo de la sima: huesos de los que cayeron, generador de esqueletos y un cofre
        y = F_SIMA
        self.spawner(77, y, 29, "skeleton")
        self.chest(76, y, 45, "north", "sima")
        for (x, z) in ((75, 31), (79, 33), (76, 40), (78, 27)):
            self.s(x, y, z, S("bone_block", axis="x" if (x + z) % 2 else "z"))
        self.s(78, y, 42, S("skeleton_skull", rotation=4))
        for (x, z, yy) in ((75, 26, y + 2), (79, 46, y + 1), (79, 30, y + 3)):
            self.s(x, yy, z, "cobweb")
        self.ruin_set(78, y, 44, "rail[shape=east_west,waterlogged=false]")   # una vía caída del puente

    # ------------------------------------------------------------ cargadero: el puzle de las agujas (este)
    def cargadero(self):
        from . import vias
        self.room(80, 81, 35, 37, 1, 3, ROCA)                           # galería del puente al cargadero
        self.room(82, 100, 26, 46, 1, 6, ROCA)
        for x in (83, 88, 94, 99):                                       # entibos de madera
            for z in (26, 46):
                self.f(x, 1, z, x, 5, z, S(LOG, axis="y"))
        # trampa 1: cable trampa en la boca de la galería (ganchos en las jambas, dispensadores encima)
        piezas.tripwire_trap(self.s, (81, 35), (81, 37), 1, "z", [((81, 2, 35), "south"), ((81, 2, 37), "north")],
                             arrows=16)
        self.mech["ganchos"] = [(81, 1, 35), (81, 1, 37)]
        self.mech["dispensadores"] = [(81, 2, 35), (81, 2, 37)]
        for z in (35, 37):
            self.carved.pop((81, 2, z), None)
        v = vias.trazar(self)
        self.mech["vias"] = v
        self.chest(82, 1, 44, "east", "cargadero")
        self.barrel(82, 1, 45, "east")
        for (x, z) in ((99, 44), (100, 44), (100, 45)):
            self.s(x, 1, z, "raw_iron_block" if x == 100 else "coal_block")
        self.hang(86, 6, 40)
        self.hang(95, 6, 33)
        self.hang(86, 6, 30)

    # ------------------------------------------------------------ el frente viejo (sureste): zombis y vetas
    def frente_viejo(self):
        self.room(89, 91, 47, 59, 1, 3, ROCA)
        self.room(84, 100, 60, 72, 1, 5, ROCA)
        for z in range(48, 72):
            if z in (52, 53):
                self.ruin_set(90, 1, z, "air")                          # traviesas arrancadas
            else:
                self.rail(90, 1, z, "north_south")
        for z in (50, 55, 60):
            for x in (89, 91):
                self.f(x, 1, z, x, 3, z, S(LOG, axis="y"))
            for x in (89, 90, 91):
                self.s(x, 4, z, S(LOG, axis="x"))
                self.carved.pop((x, 4, z), None)
        self.spawner(97, 1, 70, "zombie")
        self.chest(85, 1, 71, "north", "frente")
        for (x, z) in ((84, 62), (85, 61), (99, 63), (100, 66), (86, 72), (95, 72)):
            self.ruin_set(x, 1, z, "gravel" if (x + z) % 3 else COB)
        self.s(92, 1, 71, "cobweb")
        self.s(84, 5, 60, "cobweb")
        self.sign(92, 2, 46, "north", "frente", [("Frente viejo", "Old face"), ("Cerrado por", "Closed after"),
                                                 ("el derrumbe", "the collapse")])

    # ------------------------------------------------------------ el filón madre (bajo el cargadero)
    def filon_madre(self):
        # paso tras la compuerta y escalera de 11 peldaños hacia el norte
        for x in (91, 92, 93):
            self.carve(x, 1, 23, OBRA)
            self.carve(x, 2, 23, OBRA)
            self.carve(x, 3, 23, OBRA)
        for k in range(11):
            z, y = 22 - k, -k
            for x in (91, 92, 93):
                self.s(x, y, z, stair("stone_brick", "south"))
                for yy in range(y + 1, y + 5):
                    self.carve(x, yy, z, OBRA)
        self.room(84, 101, 1, 11, -10, -3, HOND)
        self.room(80, 83, 4, 8, -10, -6, HOND)                          # cámara del tesoro, al oeste
        y = F_HONDO
        # el filón: vetas de oro y una columna de oro en bruto en el centro
        for yy in range(y, y + 4):
            for (x, z) in ((92, 6), (93, 6), (92, 7)):
                self.s(x, yy, z, "raw_gold_block" if (x + yy) % 2 else "deepslate_gold_ore")
                self.carved.pop((x, yy, z), None)
        for (x, z) in ((86, 2), (99, 3), (100, 9), (87, 10)):
            self.s(x, y, z, "amethyst_block")
            self.s(x, y + 1, z, S("amethyst_cluster", facing="up", waterlogged=False))
        self.chest(101, y, 10, "west", "filon")
        self.chest(80, y, 6, "east", "premium")
        self.s(80, y, 5, "gold_block")
        self.s(80, y, 7, "gold_block")
        self.s(80, y + 1, 5, S("candle", candles=3, lit=False, waterlogged=False))
        for (x, z) in ((83, 4), (83, 8)):
            self.f(x, y, z, x, y + 3, z, S("deepslate_tile_wall"))
        for (x, z) in ((86, 4), (98, 4), (86, 9), (98, 9)):
            self.hang(x, y + 6, z, soul=True)
        self.hang(81, y + 3, 6, soul=True)
        self.t.entity(94, y, 4, capataz())
        self.hidden += [(x, y, z) for x in range(84, 102) for z in range(1, 12)] + \
                       [(x, y, z) for x in range(80, 84) for z in range(4, 9)]
        self.mech["guardian"] = (94, y, 4)

    # ------------------------------------------------------------ sector derrumbado e inundado (suroeste)
    def sector_derrumbado(self):
        # galería vieja: de la esquina suroeste de la caverna hacia el oeste
        for z in range(52, 59):
            for x in (24, 25, 26):
                if (x, z) not in self.cavern:
                    for y in (1, 2, 3):
                        self.carve(x, y, z, ROCA)
        self.room(4, 26, 58, 60, 1, 3, ROCA)
        for x in (12, 17, 22):                                           # entibos, uno roto
            for z in (58, 60):
                if not (x == 17 and z == 60):
                    self.f(x, 1, z, x, 2, z, S(LOG, axis="y"))
            for z in (58, 59, 60):
                if not (x == 17 and z == 60):
                    self.s(x, 3, z, S(LOG, axis="z"))
                    self.carved.pop((x, 3, z), None)
        self.ruin_set(17, 1, 60, S(LOG, axis="x"))                      # el entibo caído
        for x in range(9, 26):
            if x not in (14, 15, 20):
                self.rail(x, 1, 59, "east_west")
        for (x, z) in ((14, 58), (15, 58), (14, 60), (15, 60), (16, 58)):
            self.ruin_set(x, 1, z, "gravel")                             # el derrumbe: deja un paso por el centro
        self.ruin_set(14, 2, 58, "gravel")
        for (x, y, z) in ((10, 3, 58), (19, 3, 60), (23, 2, 58)):
            self.s(x, y, z, "cobweb")
        # trampa 2: la carga olvidada (placa sobre dinamita), con baldosas agrietadas de aviso
        piezas.tnt_trap(self.s, 21, 1, 59, warn=[(20, 0, 59), (22, 0, 59)])
        self.carved.pop((21, 1, 59), None)
        self.mech["placa_tnt"] = (21, 1, 59)
        self.mech["tnt"] = (21, -1, 59)
        # el derrumbe: cámara con arañas de cueva
        self.room(1, 7, 51, 57, 1, 4, ROCA)
        self.spawner(3, 1, 53, "cave_spider")
        self.chest(7, 1, 51, "south", "derrumbe")
        for (x, y, z) in ((1, 4, 51), (5, 4, 57), (7, 3, 55), (4, 1, 51), (1, 1, 55)):
            self.s(x, y, z, "cobweb")
        for (x, z) in ((1, 57), (2, 57), (1, 56)):
            self.ruin_set(x, 1, z, "gravel")
        # bajada al sector inundado (6 peldaños hacia el sur) y la galería anegada
        for k in range(6):
            z, y = 61 + k, -k
            for x in (9, 10):
                self.s(x, y, z, stair("cobblestone", "north"))
                for yy in range(y + 1, y + 5):
                    self.carve(x, yy, z, ROCA)
        self.room(4, 16, 67, 76, -8, -2, ROCA)
        for x in range(4, 17):
            for z in range(67, 77):
                for y in (-8, -7, -6):
                    self.carve(x, y, z, ("gravel", "roca", "roca"), "water")
        for x in range(4, 17):                                           # pasarela de tablas sobre el agua
            for z in (67, 68):
                if not (x in (13, 14) and z == 68):
                    self.s(x, -6, z, PL)
                    self.carved.pop((x, -6, z), None)
        self.ruin_set(13, -6, 68, "water")
        self.ruin_set(14, -6, 68, "water")
        self.chest(12, -8, 75, "north", "inundada", waterlogged=True)
        self.carved.pop((12, -8, 75), None)
        for (x, z) in ((6, 73), (7, 74), (15, 71)):
            self.ruin_set(x, -8, z, "gravel")
            self.carved.pop((x, -8, z), None)
        self.sign(11, 2, 60, "north", "inundada", [("¡Peligro!", "Danger!"), ("Galería", "Flooded"),
                                                   ("inundada", "gallery")])

    # ------------------------------------------------------------ mobiliario dentro de muros
    def amueblar(self):
        """Vetas de mineral en los muros del frente viejo y del filón (a la vista, como en una mina en uso)."""
        vetas = [("coal_ore", 0.35), ("iron_ore", 0.25), ("copper_ore", 0.2), ("gold_ore", 0.08),
                 ("redstone_ore", 0.07), ("lapis_ore", 0.05)]
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if not (84 <= x <= 101 and 59 <= z <= 73 and 0 <= y <= 6) or (x, y, z) in self.carved:
                continue
            if not st.startswith("minecraft:cobble"):
                continue
            if ruido(x + 2 * y, z, 3, 21) > 0.35:
                r = h(x, y, z, 22)
                acc = 0.0
                for b, p in vetas:
                    acc += p
                    if r < acc:
                        self.s(x, y, z, b)
                        break
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if 83 <= x <= 102 and 0 <= z <= 12 and -11 <= y <= -2 and (x, y, z) not in self.carved \
                    and st == "minecraft:cobbled_deepslate" and h(x, y, z, 23) < 0.18:
                self.s(x, y, z, "deepslate_gold_ore" if h(x, y, z, 24) < 0.5 else "deepslate_iron_ore")


# ------------------------------------------------------------------ guardián
def capataz():
    """Tizón, el último capataz: un vindicador (su hacha la pone el juego) con casco de minero y mandil de cuero."""
    return guardian("vindicator", K + "guardian", "Tizón, el último capataz", 70, armor=6,
                    equipment={"head": {"id": "minecraft:iron_helmet", "count": 1},
                               "chest": {"id": "minecraft:leather_chestplate", "count": 1,
                                         "components": {"minecraft:dyed_color": 6704179}}},
                    drop_chances={"head": 0.0, "chest": 0.0},
                    attributes={"follow_range": 24, "knockback_resistance": 0.4})
