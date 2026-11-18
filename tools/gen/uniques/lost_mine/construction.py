"""Construction of Hondavena's Lost Mine colony in a single coordinate system
(design in docs/unicas/lost_mine.md).

x from west to east, z from north to south; y = 0 is the floor layer of the great cavern (feet at y = 1), which in the world is at
y = FLOOR_Y. Everything that is dug out (air or water) is recorded with its lining (floor, wall, ceiling); at the end, `forro()` places
that lining on every face that looks onto what was dug and `casco()` surrounds it with solid rock (2 more blocks). Nothing is
written outside the shell: the template leaves the terrain (structure_void), so the colony is not a box and a vanilla cave that
passes nearby only sees irregular rock. The shaft rises along the EJE column up to the top face (y = YTOP); above that continue
the shaft pieces and the headframe (surface.py), which the structure type heraldia:mina places in Java.
"""
import math, zlib
from core import B
from .._common import pieces
from .._common.pieces import spawner, chest, guardian, text

SID = "mina_perdida"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
FLOOR_Y = 20                    # world y of the cavern floor layer (see docs: why this height)
YTOP = 26                    # top face of the colony: the shaft starts here
AXIS = (44, 7)                # axis of the master shaft (x, z)
DEEPER = -12                  # below this layer (world y < 8) the shell is deepslate

# gran caverna: superelipse
CX, CZ, RX, RZ, EXP = 44, 36, 27, 21, 6
LAKE = (44, 49, 13, 5)       # center and radii of the lake (superellipse of exponent 4)
CHASM = (75, 79, 25, 47)      # x0, x1, z0, z1 of the chasm (y -15 .. 8)
F_CHASM, F_DEEP, F_FLOODED = -15, -10, -5   # feet: chasm bottom, mother lode, walkway of the flooded sector

COB, MCOB, CDS = "cobblestone", "mossy_cobblestone", "cobbled_deepslate"
SB, CSB, CRSB = "stone_bricks", "chiseled_stone_bricks", "cracked_stone_bricks"
PL, LOG, SLOG = "spruce_planks", "spruce_log", "stripped_spruce_log"
DT = "deepslate_tiles"
# linings (floor, wall, ceiling): never natural blocks (`#base_stone_overworld`, dirt, gravel...), so that no
# springs, lichen, moss or clay pools from the lush caves come out inside
HOST_ROCK = ("roca", "roca", "roca")              # cavern and galleries: pick-hewn stone (mixed cobblestone)
CONSTRUCTION = (SB, SB, SB)
HOUSE = (PL, SB, PL)
FOUNDATION = (DT, "bricks", DT)
DEEP = (DT, CDS, CDS)
WELL = (PL, PL, PL)
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


def noise(x, z, noise_scale, salt=0):
    """Smooth value noise in [-1, 1] (bilinear over a grid with step `noise_scale`)."""
    gx, gz = x / noise_scale, z / noise_scale
    x0, z0 = math.floor(gx), math.floor(gz)
    fx, fz = gx - x0, gz - z0
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    v = lambda a, b: h(salt, a, b) * 2 - 1
    top = v(x0, z0) * (1 - fx) + v(x0 + 1, z0) * fx
    floor_bottom = v(x0, z0 + 1) * (1 - fx) + v(x0 + 1, z0 + 1) * fx
    return top * (1 - fz) + floor_bottom * fz


def superellipse(x, z, cx, cz, rx, rz, e):
    return (abs(x - cx) / rx) ** e + (abs(z - cz) / rz) ** e


def host_rock(x, y, z):
    """Pick-hewn stone of the cavern walls: cobblestone with veins of cobbled deepslate."""
    return CDS if noise(x + y, z - y, 5, 7) > 0.45 else COB


class Construction:
    def __init__(self):
        from core import Template
        self.t = Template(f"unicas/{SID}/obra")
        self.carved = {}           # celda excavada -> forro (suelo, muro, techo)
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # cells reachable only by solving a puzzle
        self.hidden_alcove = []    # cells behind the tapestry (no puzzle)
        self.mech = {}             # mechanisms for the audit and the server test
        self.ruin = set()          # hand-damaged positions
        self.signs = []
        self.cavern = set()        # (x, z) columns of the great cavern
        self.lake = set()          # (x, z) columns of the lake
        self.hull = set()          # shell rock (not lining)

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

    def chest(self, x, y, z, facing, tbl, kind="chest", waterlogged=False):
        chest(self.t.set, x, y, z, facing, LOOT + tbl, kind, waterlogged=waterlogged)
        self.chests.append(((x, y, z), tbl))

    def spawner(self, x, y, z, mob):
        spawner(self.t.set, x, y, z, mob, potentials=True)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=True, waterlogged=False))

    def stand(self, x, y, z, soul=False):
        self.s(x, y, z, S("soul_lantern" if soul else "lantern", hanging=False, waterlogged=False))

    def door(self, x, y, z, facing, hinge="left", kind="spruce_door"):
        pieces.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="brown"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="brown"):
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="spruce"):
        """Translatable sign: `lines` = [(es, en)] (the keys go to LANG with the suffix .1, .2...)."""
        self.signs.append((key, lines))
        pieces.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
                    wood=wood)

    def sign_post(self, x, y, z, rotation, key, lines, wood="spruce"):
        """Standing sign (rotation 0-15; 0 faces south) on the ground."""
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
        self.cavern_room()
        self.station()
        self.warehouse()
        self.smelter()
        self.houses()
        self.workshops()
        self.lake_and_dock()
        self.chasm()
        self.loading_dock()
        self.old_face()
        self.mother_lode()
        self.collapsed_sector()
        self.lining()
        self.shell()
        # what goes inside walls and floors (mechanisms, veins, ornaments) after the shell
        self.furnish()
        self.lining()
        self.shell()
        self.t.blocks = {p: v for p, v in self.t.blocks.items() if p[1] <= YTOP}
        return self

    # ------------------------------------------------------------ lining and shell
    def lining(self):
        """Places the lining in every unwritten cell that touches a dug-out one (by its face: floor, wall or ceiling)."""
        for (x, y, z), pal in list(self.carved.items()):
            if self.get(x, y, z) not in ("minecraft:air", "minecraft:water", "minecraft:cave_air") and \
                    not self.get(x, y, z).startswith("minecraft:water"):
                continue
            for (dx, dy, dz) in N6:
                p = (x + dx, y + dy, z + dz)
                if p in self.t.blocks:
                    continue
                mat = pal[0] if dy == -1 else pal[2] if dy == 1 else pal[1]
                self.s(*p, host_rock(*p) if mat == "roca" else mat)

    def shell(self, thickness=2):
        """Two layers of solid rock (6-neighbors) around everything written next to a dug-out cell."""
        frontier = set()
        for (x, y, z) in self.carved:
            for (dx, dy, dz) in N6:
                p = (x + dx, y + dy, z + dz)
                if p in self.t.blocks and p not in self.carved:
                    frontier.add(p)
        for _ in range(thickness):
            nxt = set()
            for (x, y, z) in frontier:
                for (dx, dy, dz) in N6:
                    p = (x + dx, y + dy, z + dz)
                    if p not in self.t.blocks:
                        nxt.add(p)
            for p in nxt:
                self.s(*p, "deepslate" if p[1] < DEEPER else "stone")
                self.hull.add(p)
            frontier = nxt

    # ------------------------------------------------------------ the great cavern
    def roof(self, x, z):
        e = superellipse(x, z, CX, CZ, RX, RZ, 2)
        return 5 + int(round(11 * math.sqrt(max(0.0, 1 - min(e, 1.0))) + 1.2 * noise(x, z, 6, 3)))

    def cavern_room(self):
        for x in range(CX - RX - 2, CX + RX + 3):
            for z in range(CZ - RZ - 2, CZ + RZ + 3):
                if superellipse(x, z, CX, CZ, RX, RZ, EXP) > 1 + 0.08 * noise(x, z, 4, 1):
                    continue
                self.cavern.add((x, z))
                for y in range(1, self.roof(x, z) + 1):
                    self.carve(x, y, z, HOST_ROCK)
        # cavern floor: trodden cobblestone; polished andesite plaza around the master pillar
        for (x, z) in self.cavern:
            d = math.hypot(x - CX, z - CZ)
            self.s(x, 0, z, "polished_andesite" if 3 < d <= 8.5 else (CDS if h(x, z, 4) < 0.2 else COB))
        # master pillar: rock the miners left to hold up the vault
        for x in range(CX - 3, CX + 4):
            for z in range(CZ - 3, CZ + 4):
                d = math.hypot(x - CX, z - CZ)
                if d <= 2.6:
                    for y in range(1, self.roof(x, z) + 1):
                        self.s(x, y, z, SB if y <= 2 else (CSB if y == 3 else host_rock(x, y, z)))
                        self.carved.pop((x, y, z), None)
        for (dx, dz) in ((0, -6), (0, 6), (-6, 0), (6, 0)):
            self.hang(CX + dx, self.roof(CX + dx, CZ + dz) - 4, CZ + dz)
        self.sign(CX, 2, CZ - 3, "north", "pilar", [("Hondavena", "Hondavena"), ("Colonia minera", "Mining colony"),
                                                    ("de la Corona", "of the Crown")])
        self.sign(CX, 2, CZ + 3, "south", "lago", [("Al sur:", "South:"), ("el lago y", "the lake and"),
                                                   ("el embarcadero", "the landing")])
        self.sign(CX + 3, 2, CZ, "east", "puente", [("Al este:", "East:"), ("el puente y", "the bridge and"),
                                                    ("el cargadero", "the loading bay")])
        self.sign(CX - 3, 2, CZ, "west", "casas", [("Al oeste:", "West:"), ("las casas", "the miners'"),
                                                   ("de los mineros", "houses")])
        # loose cave-ins beside the walls (ruin) and lanterns on the roads
        for (x, z) in ((22, 26), (66, 44), (25, 50), (60, 22), (36, 18), (52, 54), (30, 52), (63, 33)):
            for (a, b, y) in ((0, 0, 1), (1, 0, 1), (0, 1, 1), (0, 0, 2)):
                if (x + a, z + b) in self.cavern:
                    self.ruin_set(x + a, y, z + b, "cobblestone" if (a + b + y) % 2 else "gravel")
        for (x, z) in ((47, 20), (34, 30), (56, 30), (34, 42), (56, 42), (44, 44), (30, 22), (64, 26)):
            self.hang(x, self.roof(x, z) - 3, z)

    def boundary(self, z, side):
        """x of the first column of the cavern in row z, from the west or the east."""
        xs = [x for (x, zz) in self.cavern if zz == z]
        return min(xs) if side == "west" else max(xs)

    # ------------------------------------------------------------ shaft station (north)
    def station(self):
        ex, ez = AXIS
        self.room(43, 51, 3, 12, 1, 5, CONSTRUCTION)
        self.room(ex - 1, ex + 1, ez - 1, ez + 1, 6, YTOP, WELL)          # the master shaft
        self.room(45, 49, 13, 17, 1, 4, CONSTRUCTION)                            # to the cavern
        for y in range(1, YTOP + 1):
            self.s(ex - 1, y, ez, S("ladder", facing="east", waterlogged=False))
        for y in range(2, YTOP + 1):
            self.s(ex, y, ez, S("iron_chain", axis="y", waterlogged=False))
        self.s(ex, 1, ez, "cauldron")                                    # the winch bucket, at the bottom
        for y in range(8, YTOP + 1, 4):                                  # wooden frames of the shaft
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
        for z in range(13, 20):                                          # minecart track toward the plaza
            if (47, z) in self.cavern or z <= 17:
                self.rail(47, 1, z, "north_south")
        self.ruin_set(47, 1, 18, "air")                                  # un tramo arrancado

    # ------------------------------------------------------------ warehouse (northwest)
    def warehouse(self):
        self.room(24, 36, 5, 12, 1, 4, CONSTRUCTION)
        self.room(28, 32, 13, 18, 1, 3, CONSTRUCTION)
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

    # ------------------------------------------------------------ smelter (northeast)
    def smelter(self):
        self.room(54, 68, 3, 12, 1, 6, FOUNDATION)
        self.room(58, 62, 13, 19, 1, 4, FOUNDATION)
        for x in (56, 59, 62, 65):
            self.s(x, 1, 3, S("blast_furnace", facing="south", lit=False), {"id": "minecraft:blast_furnace"})
            self.s(x, 2, 3, "bricks")
        for x in range(55, 68):                                          # brick hood over the furnaces
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

    # ------------------------------------------------------------ miners' houses (west)
    def facade(self, zd, half, side):
        """x of the (straight) facade for the house in row zd, with a porch to the cavern."""
        rows = range(zd - half, zd + half + 1)
        if side == "west":
            fx = min(self.boundary(z, "west") for z in rows) - 1
            for z in rows:
                for x in range(fx + 1, self.boundary(z, "west")):
                    for y in range(1, 5):
                        self.carve(x, y, z, HOST_ROCK)
        else:
            fx = max(self.boundary(z, "east") for z in rows) + 1
            for z in rows:
                for x in range(self.boundary(z, "east") + 1, fx):
                    for y in range(1, 5):
                        self.carve(x, y, z, HOST_ROCK)
        return fx

    def house(self, zd, key, tbl=None, collapsed=False):
        fx = self.facade(zd, 3, "west")
        x1, x2 = fx - 7, fx - 1
        self.room(x1, x2, zd - 3, zd + 2, 1, 4, HOUSE)
        for z in range(zd - 3, zd + 3):                       # stone brick facade with door and window
            for y in range(1, 5):
                self.s(fx, y, z, SB)
        self.door(fx, 1, zd, "east", "left")
        self.s(fx, 2, zd + 2, S("glass_pane"))
        self.s(fx, 2, zd - 2, S("glass_pane"))
        self.bed(x1, 1, zd - 3, "west", "brown" if zd % 2 else "gray")
        if not collapsed:
            self.s(x1, 1, zd + 2, "furnace[facing=east,lit=false]", {"id": "minecraft:furnace"})
            self.s(x1 + 2, 1, zd + 2, "crafting_table")
        self.hang(x1 + 3, 4, zd)
        if tbl:
            self.chest(x1, 1, zd - 1, "east", tbl)
        self.s(x1 + 4, 1, zd + 2, slab("spruce", "top"))
        self.s(x1 + 5, 1, zd + 2, slab("spruce", "top"))
        self.s(x1 + 4, 2, zd + 2, S("flower_pot"))
        if collapsed:                                        # sunken ceiling in the back half
            for (x, z) in ((x1, zd + 2), (x1 + 1, zd + 2), (x1, zd + 1), (x1 + 1, zd + 1), (x1 + 2, zd + 2)):
                self.ruin_set(x, 1, z, "gravel" if (x + z) % 2 else COB)
            self.ruin_set(x1, 2, zd + 2, "gravel")
            for (x, z) in ((x1, zd + 1), (x1 + 1, zd + 2)):
                self.ruin_set(x, 5, z, "air")                 # the ceiling that fell
                self.carved[(x, 5, z)] = HOUSE
        return fx, x1, x2

    def houses(self):
        self.house(19, "a", "vivienda")
        fx, x1, x2 = self.foreman_house(29)
        self.house(39, "c", "vivienda")
        self.house(48, "d", "vivienda", collapsed=True)
        self.sign(self.facade_x[29] + 1, 3, 31, "east", "capataz", [("Casa del", "Foreman's"), ("capataz", "house")])

    def foreman_house(self, zd):
        """Foreman's house: wider; behind the bookshelf with a lever on the west wall, his office (puzzle 2)."""
        fx = self.facade(zd, 4, "west")
        self.facade_x = {zd: fx}
        x1, x2 = fx - 8, fx - 1
        self.room(x1, x2, zd - 4, zd + 3, 1, 4, HOUSE)
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
        self.s(x1 + 4, 1, zd, slab("spruce", "top"))                     # table with two chairs
        self.s(x1 + 4, 1, zd - 1, stair("spruce", "south"))
        self.s(x1 + 4, 1, zd + 1, stair("spruce", "north"))
        self.hang(x1 + 4, 4, zd - 2)
        self.hang(x1 + 4, 4, zd + 2)
        # secret door: in the west wall (two thick) a panel retracts to the north inside the wall; the
        # lever, in a bookshelf set into the corner (pieces.lever_door)
        wall = x1 - 2
        rec = pieces.lever_door(self.s, (wall, 1, zd), "north", "east", SB, SB)
        self.s(x1 - 1, 1, rec["lever"][2], "bookshelf")                 # the lever's block is a bookshelf
        for y in (1, 2):
            self.carved[(x1 - 1, y, zd)] = HOUSE
        self.mech["puerta_despacho"] = rec
        ox1, ox2 = wall - 6, wall - 1
        self.room(ox1, ox2, zd - 2, zd + 2, 1, 4, HOUSE)                  # despacho oculto
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

    # ------------------------------------------------------------ smithy and carpentry (east)
    def workshop(self, zd, key, tbl):
        fx = self.facade(zd, 3, "east")
        x1, x2 = fx + 1, fx + 7
        self.room(x1, x2, zd - 3, zd + 2, 1, 4, CONSTRUCTION)
        for z in range(zd - 3, zd + 3):
            for y in range(1, 5):
                self.s(fx, y, z, SB)
        self.carve(fx, 1, zd, CONSTRUCTION)
        self.carve(fx, 2, zd, CONSTRUCTION)
        self.carve(fx, 1, zd - 1, CONSTRUCTION)
        self.carve(fx, 2, zd - 1, CONSTRUCTION)
        self.chest(x2, 1, zd + 2, "west", tbl)
        self.hang(x1 + 3, 4, zd)
        return x1, x2

    def workshops(self):
        x1, x2 = self.workshop(20, "herreria", "herreria")
        self.s(x1 + 2, 1, 17, S("anvil", facing="north"))
        self.s(x1 + 4, 1, 17, S("smithing_table"))
        self.s(x2, 1, 17, S("blast_furnace", facing="west", lit=False), {"id": "minecraft:blast_furnace"})
        self.s(x2, 1, 18, S("grindstone", face="floor", facing="west"))
        self.s(x2, 1, 20, S("lava_cauldron"))
        self.sign(x1, 3, 18, "east", "herreria", [("Herrería", "Smithy")])
        x1, x2 = self.workshop(52, "carpinteria", "carpinteria")
        for z in (49, 50):
            self.f(x2, 1, z, x2, 2, z, S(SLOG, axis="x"))
        self.s(x1 + 2, 1, 49, "crafting_table")
        self.s(x1 + 3, 1, 49, S("stonecutter", facing="south"))
        self.s(x1 + 5, 1, 49, "fletching_table")
        self.barrel(x2, 1, 51, "west")
        self.sign(x1, 3, 50, "east", "carpinteria", [("Carpintería", "Carpentry"), ("Entibos y", "Props and"),
                                                     ("traviesas", "sleepers")])

    # ------------------------------------------------------------ underground lake and jetty (south)
    def lake_and_dock(self):
        lx, lz, rx, rz = LAKE
        for x in range(lx - rx, lx + rx + 1):
            for z in range(lz - rz, lz + rz + 1):
                if superellipse(x, z, lx, lz, rx, rz, 4) <= 1 and (x, z) in self.cavern:
                    self.lake.add((x, z))
                    self.carve(x, 0, z, HOST_ROCK)
                    for y in (-3, -2, -1):
                        self.carve(x, y, z, ("gravel" if h(x, z, 5) < 0.5 else "sand", "roca", "roca"), "water")
        # the dock: planks flush with the floor, piles down to the bottom
        for x in (43, 44, 45):
            for z in range(43, 50):
                if (x, z) in self.lake:
                    self.s(x, 0, z, PL)
                    self.carved.pop((x, 0, z), None)
        for (x, z) in ((43, 46), (45, 46), (43, 49), (45, 49)):
            for y in (-3, -2, -1):
                self.s(x, y, z, S(LOG, axis="y"))
                self.carved.pop((x, y, z), None)
        for x in (43, 45):
            self.s(x, 1, 49, "spruce_fence")
            self.stand(x, 2, 49)
        self.ruin_set(45, 0, 47, "air")                                  # a loose plank
        self.carved[(45, 0, 47)] = HOST_ROCK
        self.chest(43, 1, 43, "east", "embarcadero")
        self.barrel(45, 1, 43)
        self.t.entity(47, -1, 47, {"id": "minecraft:oak_boat", "PersistenceRequired": B(1)})
        self.mech["barca"] = (47, -1, 47)
        self.sign_post(44, 1, 42, 8, "embarcadero", [("Embarcadero", "Landing"), ("Prohibido", "No swimming")])
        # the boat shed on the south shore and, behind the tapestry, the stash
        self.room(40, 48, 58, 63, 1, 4, HOUSE)
        for x in range(42, 47):
            for z in range(self.cz_sur(x), 58):
                for y in range(1, 4):
                    self.carve(x, y, z, HOST_ROCK)
        self.barrel(40, 1, 63)
        self.barrel(48, 1, 63)
        self.s(41, 1, 63, "crafting_table")
        for x in (40, 48):
            self.f(x, 1, 59, x, 1, 61, S(SLOG, axis="z"))
        self.hang(44, 4, 61)
        self.banner(44, 3, 63, "north", "blue")                         # tapestry covering the passage to the stash
        for y in (1, 2):
            self.carve(44, y, 64, HOUSE)
        self.room(41, 47, 65, 69, 1, 3, HOUSE)
        self.chest(41, 1, 69, "east", "alijo")
        self.barrel(47, 1, 69)
        self.s(47, 1, 65, S("candle", candles=1, lit=False, waterlogged=False))
        self.hidden_alcove += [(x, 1, z) for x in range(41, 48) for z in range(65, 70)]

    def cz_sur(self, x):
        return max(z for (xx, z) in self.cavern if xx == x) + 1

    # ------------------------------------------------------------ the chasm and the suspension bridge (east)
    def chasm(self):
        x0, x1, z0, z1 = CHASM
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                top = 8 - (1 if h(x, z, 11) < 0.3 else 0)
                for y in range(F_CHASM, top + 1):
                    self.carve(x, y, z, HOST_ROCK)
        for z in range(34, 39):                                          # ledge from the cavern
            for x in range(self.boundary(z, "east") + 1, x0):
                for y in range(1, 5):
                    self.carve(x, y, z, HOST_ROCK)
        for x in range(x0, x1 + 1):                                      # the bridge: 3 wide, railings
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
        for (x, z) in ((x0 + 1, 35), (x0 + 3, 37)):                      # missing planks and railing, off the path
            self.ruin_set(x, 0, z, "air")
            self.ruin_set(x, 1, z, "air")
        for y in range(F_CHASM, 2):                                       # ladder to the bottom
            self.s(x1, y, 38, S("ladder", facing="west", waterlogged=False))
        self.hang(73, 4, 36)
        self.sign(x0 - 1, 2, 34, "south", "sima", [("La Sima", "The Chasm"), ("Puente para", "Bridge for"),
                                                   ("uno a uno", "one at a time")])
        # bottom of the chasm: bones of those who fell, skeleton spawner and a chest
        y = F_CHASM
        self.spawner(77, y, 29, "skeleton")
        self.chest(76, y, 45, "north", "sima")
        for (x, z) in ((75, 31), (79, 33), (76, 40), (78, 27)):
            self.s(x, y, z, S("bone_block", axis="x" if (x + z) % 2 else "z"))
        self.s(78, y, 42, S("skeleton_skull", rotation=4))
        for (x, z, yy) in ((75, 26, y + 2), (79, 46, y + 1), (79, 30, y + 3)):
            self.s(x, yy, z, "cobweb")
        self.ruin_set(78, y, 44, "rail[shape=east_west,waterlogged=false]")   # a track fallen from the bridge

    # ------------------------------------------------------------ loading dock: the needle puzzle (east)
    def loading_dock(self):
        from . import tracks
        self.room(80, 81, 35, 37, 1, 3, HOST_ROCK)                           # gallery from the bridge to the loading dock
        self.room(82, 100, 26, 46, 1, 6, HOST_ROCK)
        for x in (83, 88, 94, 99):                                       # entibos de madera
            for z in (26, 46):
                self.f(x, 1, z, x, 5, z, S(LOG, axis="y"))
        # trap 1: trap wire at the gallery mouth (hooks on the jambs, dispensers above)
        pieces.tripwire_trap(self.s, (81, 35), (81, 37), 1, "z", [((81, 2, 35), "south"), ((81, 2, 37), "north")],
                             arrows=16)
        self.mech["ganchos"] = [(81, 1, 35), (81, 1, 37)]
        self.mech["dispensadores"] = [(81, 2, 35), (81, 2, 37)]
        for z in (35, 37):
            self.carved.pop((81, 2, z), None)
        v = tracks.trace(self)
        self.mech["vias"] = v
        self.chest(82, 1, 44, "east", "cargadero")
        self.barrel(82, 1, 45, "east")
        for (x, z) in ((99, 44), (100, 44), (100, 45)):
            self.s(x, 1, z, "raw_iron_block" if x == 100 else "coal_block")
        self.hang(86, 6, 40)
        self.hang(95, 6, 33)
        self.hang(86, 6, 30)

    # ------------------------------------------------------------ the old face (southeast): zombies and veins
    def old_face(self):
        self.room(89, 91, 47, 59, 1, 3, HOST_ROCK)
        self.room(84, 100, 60, 72, 1, 5, HOST_ROCK)
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

    # ------------------------------------------------------------ the mother lode (under the loading dock)
    def mother_lode(self):
        # passage behind the hatch and a staircase of 11 steps heading north
        for x in (91, 92, 93):
            self.carve(x, 1, 23, CONSTRUCTION)
            self.carve(x, 2, 23, CONSTRUCTION)
            self.carve(x, 3, 23, CONSTRUCTION)
        for k in range(11):
            z, y = 22 - k, -k
            for x in (91, 92, 93):
                self.s(x, y, z, stair("stone_brick", "south"))
                for yy in range(y + 1, y + 5):
                    self.carve(x, yy, z, CONSTRUCTION)
        self.room(84, 101, 1, 11, -10, -3, DEEP)
        self.room(80, 83, 4, 8, -10, -6, DEEP)                          # treasure chamber, to the west
        y = F_DEEP
        # the lode: gold veins and a column of raw gold in the center
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
        self.t.entity(94, y, 4, foreman())
        self.hidden += [(x, y, z) for x in range(84, 102) for z in range(1, 12)] + \
                       [(x, y, z) for x in range(80, 84) for z in range(4, 9)]
        self.mech["guardian"] = (94, y, 4)

    # ------------------------------------------------------------ sector derrumbado e inundado (suroeste)
    def collapsed_sector(self):
        # old gallery: from the southwest corner of the cavern heading west
        for z in range(52, 59):
            for x in (24, 25, 26):
                if (x, z) not in self.cavern:
                    for y in (1, 2, 3):
                        self.carve(x, y, z, HOST_ROCK)
        self.room(4, 26, 58, 60, 1, 3, HOST_ROCK)
        for x in (12, 17, 22):                                           # entibos, uno roto
            for z in (58, 60):
                if not (x == 17 and z == 60):
                    self.f(x, 1, z, x, 2, z, S(LOG, axis="y"))
            for z in (58, 59, 60):
                if not (x == 17 and z == 60):
                    self.s(x, 3, z, S(LOG, axis="z"))
                    self.carved.pop((x, 3, z), None)
        self.ruin_set(17, 1, 60, S(LOG, axis="x"))                      # the fallen timbering
        for x in range(9, 26):
            if x not in (14, 15, 20):
                self.rail(x, 1, 59, "east_west")
        for (x, z) in ((14, 58), (15, 58), (14, 60), (15, 60), (16, 58)):
            self.ruin_set(x, 1, z, "gravel")                             # the cave-in: leaves a passage through the center
        self.ruin_set(14, 2, 58, "gravel")
        for (x, y, z) in ((10, 3, 58), (19, 3, 60), (23, 2, 58)):
            self.s(x, y, z, "cobweb")
        # trap 2: the forgotten charge (plate over dynamite), with cracked tiles as a warning
        pieces.tnt_trap(self.s, 21, 1, 59, warn=[(20, 0, 59), (22, 0, 59)])
        self.carved.pop((21, 1, 59), None)
        self.mech["placa_tnt"] = (21, 1, 59)
        self.mech["tnt"] = (21, -1, 59)
        # the cave-in: chamber with cave spiders
        self.room(1, 7, 51, 57, 1, 4, HOST_ROCK)
        self.spawner(3, 1, 53, "cave_spider")
        self.chest(7, 1, 51, "south", "derrumbe")
        for (x, y, z) in ((1, 4, 51), (5, 4, 57), (7, 3, 55), (4, 1, 51), (1, 1, 55)):
            self.s(x, y, z, "cobweb")
        for (x, z) in ((1, 57), (2, 57), (1, 56)):
            self.ruin_set(x, 1, z, "gravel")
        # descent to the flooded sector (6 steps heading south) and the waterlogged gallery
        for k in range(6):
            z, y = 61 + k, -k
            for x in (9, 10):
                self.s(x, y, z, stair("cobblestone", "north"))
                for yy in range(y + 1, y + 5):
                    self.carve(x, yy, z, HOST_ROCK)
        self.room(4, 16, 67, 76, -8, -2, HOST_ROCK)
        for x in range(4, 17):
            for z in range(67, 77):
                for y in (-8, -7, -6):
                    self.carve(x, y, z, ("gravel", "roca", "roca"), "water")
        for x in range(4, 17):                                           # plank walkway over the water
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
    def furnish(self):
        """Ore veins in the walls of the old face and the lode (in view, as in a mine in use)."""
        veins = [("coal_ore", 0.35), ("iron_ore", 0.25), ("copper_ore", 0.2), ("gold_ore", 0.08),
                 ("redstone_ore", 0.07), ("lapis_ore", 0.05)]
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if not (84 <= x <= 101 and 59 <= z <= 73 and 0 <= y <= 6) or (x, y, z) in self.carved:
                continue
            if not st.startswith("minecraft:cobble"):
                continue
            if noise(x + 2 * y, z, 3, 21) > 0.35:
                r = h(x, y, z, 22)
                access = 0.0
                for b, p in veins:
                    access += p
                    if r < access:
                        self.s(x, y, z, b)
                        break
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if 83 <= x <= 102 and 0 <= z <= 12 and -11 <= y <= -2 and (x, y, z) not in self.carved \
                    and st == "minecraft:cobbled_deepslate" and h(x, y, z, 23) < 0.18:
                self.s(x, y, z, "deepslate_gold_ore" if h(x, y, z, 24) < 0.5 else "deepslate_iron_ore")


# ------------------------------------------------------------------ guardian
def foreman():
    """Tizón, the last foreman: a vindicator (the game provides his axe) with a miner's helmet and leather apron."""
    return guardian("vindicator", K + "guardian", "Tizón, el último capataz", 70, armor=6,
                    equipment={"head": {"id": "minecraft:iron_helmet", "count": 1},
                               "chest": {"id": "minecraft:leather_chestplate", "count": 1,
                                         "components": {"minecraft:dyed_color": 6704179}}},
                    drop_chances={"head": 0.0, "chest": 0.0},
                    attributes={"follow_range": 24, "knockback_resistance": 0.4})
