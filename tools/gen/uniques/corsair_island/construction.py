"""Construction of the Corsair's island in a single coordinate system (see docs/unicas/corsair_island.md).

x from west to east (0..W-1), z from north to south (0..D-1); y = 0 is the first layer above the water (the sea reaches y = -1)
and the template goes down to BASE, whose row is extended down to the floor when placed (HastaElSueloProcessor). The islet
brings its own rock, sand and palm trees: to the north and east, a hill with cliffs where the fort rises; to the south and
west, beaches, the harbor with the pier and the brigantine, the tavern, the warehouses, the gallows and the point's lighthouse. Under
the hill, the sea caves (the hidden cove, the map room, the armory, the dungeons and the treasure chamber).
"""
import math, zlib
from core import Template
from .._common import pieces
from .._common.pieces import spawner, chest, text

SID = "isla_corsario"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
W, D = 112, 110
BASE = -18                      # bottom row of the template (extended down to the floor)
CX, CZ, RX, RZ = 56, 48, 42, 37  # islet: superellipse (exponent 3) with a wavy coast
PLAT = 7                        # fort floor (feet at 8)
HILL = (75, 28, 22, 19)         # fort plateau: center and semi-axes (superellipse of exponent 4)
TREES = 3                     # no grass (or trees) within this many blocks of the build
FORT = (60, 84, 24, 45)       # fort enclosure on the plateau: x0, x1, z0, z1 (walls included)
TOWN = (24, 66, 52, 78)       # harbor esplanade (floor at y = 1): x0, x1, z0, z1

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
    """Deterministic randomness in [0, 1) from the coordinates."""
    return zlib.crc32(",".join(map(str, a)).encode()) % 1000 / 1000.0


def form(x, z):
    """Normalized distance to the coast (< 1 inside the islet)."""
    dx, dz = (x - CX) / RX, (z - CZ) / RZ
    a = math.atan2(dz, dx)
    w = 1 + 0.07 * math.sin(3 * a + 3.93) + 0.045 * math.sin(5 * a + 2.1) + 0.03 * math.sin(9 * a + 0.3)
    return (abs(dx) ** 2.4 + abs(dz) ** 2.4) ** (1 / 2.4) / w


def outside_hill(x, z):
    """Blocks (approx.) from the edge of the hill plateau; 0 inside."""
    hx, hz, rx, rz = HILL
    d = ((abs(x - hx) / rx) ** 4 + (abs(z - hz) / rz) ** 4) ** 0.25
    return max(0, int(round((d - 1) * min(rx, rz))))


def floor(x, z):
    """Height of the islet's surface block at (x, z), or None if it is sea."""
    d = form(x, z)
    if d > 1:
        return None
    low = 0 if d > 0.86 else 1
    px0, px1, pz0, pz1 = TOWN
    if px0 <= x <= px1 and pz0 <= z <= pz1 and d <= 0.86:
        low = 1                                   # the harbor esplanade, level
    e = outside_hill(x, z)
    hill = PLAT - (e * 3 + 1) // 2 if e else PLAT
    return max(low, hill)


def bed(x, z):
    """Top of the underwater slope (y < 0) off the coast, or None far from the islet."""
    d = form(x, z)
    if d <= 1:
        return None
    k = (d - 1) * RX          # blocks (approx.) from the coast
    if k > 9:
        return None
    return max(BASE, -2 - int(k * 1.8))


class Construction:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/isla")
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # cells reachable only by solving a puzzle
        self.secret = []           # cells of hidden rooms without a puzzle (tapestries, niches)
        self.mech = {}             # mechanisms for the simulator and the server test
        self.ruin = set()          # hand-damaged positions (state of wear)
        self.signs = []
        self.ground = {}           # (x, z) -> height of the islet's surface block
        self.lining = set()        # wall cells of the caves (cannot be natural rock)
        self.water = set()          # template water (cove, channel)
        self.road = set()        # (x, z) cells of the islet's roads
        self.natural = {}          # rock, sand and grass of the islet as they come out of islote() (they do not count as build)

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

    def spawner(self, x, y, z, mob, light=None):
        spawner(self.t.set, x, y, z, mob, potentials=True, light=light)
        self.spawners.append(((x, y, z), mob))

    def hang(self, x, y, z):
        self.s(x, y, z, S("lantern", hanging=True, waterlogged=False))

    def lamp(self, x, y, z):
        self.s(x, y, z, S("lantern", hanging=False, waterlogged=False))

    def door(self, x, y, z, facing, hinge="left", kind="spruce_door"):
        pieces.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="black"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="red"):
        """Bed with the head toward `facing` (the head at x, z; the foot behind)."""
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="spruce"):
        """Translatable sign: `lines` = [(es, en)] (the keys go to LANG with the suffix .1, .2...)."""
        self.signs.append((key, lines))
        pieces.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
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
        """Flight of n steps rising toward d from feet y0 (the first step at y0). Clears `air` blocks above
        each step and fills the support below down to y0 - 1."""
        dx, dz = DV[d]
        sx, sz = (dz != 0, dx != 0)
        for w in range(width):
            for i in range(n):
                X, Y, Z = x + dx * i + sx * w, y0 + i, z + dz * i + sz * w
                self.s(X, Y, Z, stairs(mat, d))
                self.a(X, Y + 1, Z, X, Y + air, Z)
                self.f(X, y0 - 1, Z, X, Y - 1, Z, support) if Y - 1 >= y0 - 1 else None

    def host_rock(self, x, y, z):
        return ROCK[int(h(x, y, z) * len(ROCK))]

    # ------------------------------------------------------------ islote
    def islet(self):
        """Islet rock from BASE up to the surface, sand on the beaches, grass inland, stone on the hill
        and a sand and gravel slope under the water around it."""
        for x in range(W):
            for z in range(D):
                g = floor(x, z)
                if g is not None:
                    self.ground[(x, z)] = g
                    d = form(x, z)
                    e = outside_hill(x, z)
                    for y in range(BASE, g + 1):
                        self.s(x, y, z, self.host_rock(x, y, z))
                    if g == 0 and e > 1:
                        top = "sand"
                        for y in range(-3, 1):
                            self.s(x, y, z, "sand" if y > -3 else "sandstone")
                    elif e == 0 or g >= 3:
                        top = None                      # the hill: rock, and grass only on the plateau
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
                top = bed(x, z)
                if top is None:
                    continue
                for y in range(BASE, top + 1):
                    self.s(x, y, z, self.host_rock(x, y, z))
                self.s(x, top, z, "sand" if h(x, z, 3) < 0.7 else "gravel")
                if self.get(x, top - 1, z) and top - 1 >= BASE:
                    self.s(x, top - 1, z, "sandstone" if h(x, z, 4) < 0.5 else self.host_rock(x, top - 1, z))

    def islet_end(self):
        """Remembers the natural state of each islet cell (so it is not counted as build in the state of wear)."""
        self.natural = {p: st for p, (st, _) in self.t.blocks.items()}

    def build(self):
        from . import fort, caves, harbor
        self.islet()
        self.islet_end()
        fort.construct(self)
        harbor.construct(self)
        caves.Caves(self).construct()
        self.no_trees()
        pieces.connect(self.t)
        return self

    def construction_columns(self):
        """Columns (x, z) with build above the islet's ground (not counting the palm trees)."""
        out = set()
        for (x, y, z), (st, _) in self.t.blocks.items():
            g = self.ground.get((x, z))
            if g is not None and y > g and self.natural.get((x, y, z)) != st and \
                    not any(k in st for k in ("jungle_", "cocoa", ":air")):
                out.add((x, z))
        return out

    def no_trees(self):
        """The oceans have their oaks (trees_water) and their grass: they grow on the islet's grass. Within
        TREES blocks of the build the ground is trampled dirt (path dirt), where nothing grows: no tree
        covers a door or grows against a wall; in the rest of the island, the grass may yield an oak."""
        cols = self.construction_columns()
        r = TREES
        for (x, z), g in self.ground.items():
            st = self.get(x, g, z)
            if st != "minecraft:grass_block[snowy=false]":
                continue
            if any((x + a, z + b) in cols for a in range(-r, r + 1) for b in range(-r, r + 1)):
                self.s(x, g, z, "dirt_path")
