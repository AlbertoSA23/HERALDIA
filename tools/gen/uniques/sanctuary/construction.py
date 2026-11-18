"""Construction of the Druid sanctuary in a single coordinate system (see docs/unicas/sanctuary.md).

x from west to east (0..71), z from north to south (0..71; the entrance is to the north, z = 0); y = 0 is the ground layer of the
clearing (feet at y = 1). The sacred tree is in the centre (pier of its staircase at TX, TZ). What lies below
y = 0 (the druids' roots and galleries) is another piece, which fills its whole box. Everything is built in a "build"
that is later split into two templates (audit.prepare).
"""
import math, zlib
from core import Template, B
from .._common import pieces
from .._common.pieces import spawner, chest, guardian, text

SID = "santuario"
LOOT = f"heraldia:unicas/{SID}/"
K = f"heraldia.{SID}."
W = D = 72
C = 35.5                      # centre of the clearing (disc of radius R)
R, R_LIGHT = 36, 30           # ground disc; inside R_LIGHT, trodden ground (outside, grass where the forest grows)
TX, TZ = 36, 36               # pier of the tree staircase
AIR_H = 6                     # explicit air above the clearing (the terrain does not poke out between the cabins)

# feet of the levels of the tree staircase (every 6): low underground, high underground, ground, landings and the crown
F2, F1, TOP = -11, -5, 19
CRYPT = (12, 60, 4, 66, -14, -1)        # box of the underground piece: x0, x1, z0, z1, y0, y1
NATURAL = ("minecraft:dirt", "minecraft:stone")

LOG, SLOG, WOOD, PL = "birch_log", "stripped_birch_log", "birch_wood", "birch_planks"
LEAVES = "birch_leaves[distance=1,persistent=true,waterlogged=false]"
COB, SB, CSB, MSB = "cobblestone", "stone_bricks", "chiseled_stone_bricks", "mossy_stone_bricks"
MUD, PMUD, EXISTS = "mud_bricks", "packed_mud", "hay_block[axis=y]"

OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


def stair(m, facing, half="bottom"):
    return S(f"{m}_stairs", facing=facing, half=half, shape="straight", waterlogged=False)


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


class Construction:
    def __init__(self):
        self.t = Template(f"unicas/{SID}/obra")
        self.chests = []           # (pos, tabla)
        self.spawners = []         # (pos, mob)
        self.hidden = []           # cells reachable only by solving a puzzle
        self.hidden_alcove = []    # cells behind the tapestry (reachable without a puzzle)
        self.mech = {}             # mechanisms for the simulator and the server test
        self.ruin = set()          # hand-damaged positions (state of preservation)
        self.carved = {}           # underground air cells -> (floor, wall, ceiling)
        self.signs = []

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

    def door(self, x, y, z, facing, hinge="left", kind="birch_door"):
        pieces.door(self.s, x, y, z, facing, kind, hinge)

    def banner(self, x, y, z, facing, color="green"):
        self.s(x, y, z, S(f"{color}_wall_banner", facing=facing))

    def bed(self, x, y, z, facing, color="green"):
        """Bed with the head towards `facing` (the head at x, z; the foot behind)."""
        dx, dz = DV[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="head", occupied=False))
        self.s(x - dx, y, z - dz, S(f"{color}_bed", facing=facing, part="foot", occupied=False))

    def sign(self, x, y, z, facing, key, lines, wood="birch"):
        """Translatable sign: `lines` = [(es, en)] (the keys go to LANG with the suffix .1, .2...)."""
        self.signs.append((key, lines))
        pieces.sign(self.s, x, y, z, facing, [text(f"{K}cartel.{key}.{i + 1}", es) for i, (es, _) in enumerate(lines)],
                    wood=wood)

    def ruin_set(self, x, y, z, st="air"):
        self.s(x, y, z, st)
        self.ruin.add((x, y, z))

    # ------------------------------------------------------------ construction
    def build(self):
        self.ground()
        self.avenue()
        self.tree()
        self.stone_circle()
        self.hut(13, 23, 0)
        self.hut(10, 36, 1)
        self.hut(13, 49, 2)
        self.archdruid()
        self.garden()
        self.pond()
        self.observatory()
        self.roots()
        self.crypt()
        self.clearing_air()
        self.moss()
        self.weather()
        self.loose_debris()
        return self

    def loose_debris(self):
        """What the ruin leaves loose (leaves or hay between two gaps) has fallen too."""
        from .._common.walkthrough import floating_blocks
        for _ in range(3):
            area = {p: st for p, (st, _) in self.t.blocks.items() if p[1] >= 0}
            fl = floating_blocks(area, (0,))
            if not fl:
                break
            for p in fl:
                self.ruin_set(*p)

    # ============================================================ superficie
    def clear(self, x, z):
        return dist(x, z, C, C) <= R_LIGHT

    def ground(self):
        """Clearing floor: path dirt (nothing grows on it); outside R_LIGHT, grass where the forest grows."""
        for x in range(W):
            for z in range(D):
                d = dist(x, z, C, C)
                if d <= R:
                    self.s(x, 0, z, "dirt_path" if d <= R_LIGHT else "grass_block[snowy=false]")

    def avenue(self):
        """Mossy stone path from the entrance to the tree."""
        for z in range(0, 32):
            for x in range(35, 38):
                if dist(x, z, C, C) <= R:
                    self.s(x, 0, z, COB if h(x, z, 1) < 0.6 else "mossy_cobblestone")
        self.mech["jig"] = (36, 0, 20)

    # ------------------------------------------------------------ the sacred tree
    def trunk_cell(self, x, z, r=4.5):
        return dist(x, z, TX, TZ) <= r

    def tree(self):
        """Sacred birch: 9-wide hollow trunk with a spiral staircase from the galleries to the crown."""
        top = 30
        for x in range(TX - 5, TX + 6):
            for z in range(TZ - 5, TZ + 6):
                for y in range(0, top + 1):
                    r = 4.5 if y < 24 else (3.5 if y < 27 else 2.5)
                    if self.trunk_cell(x, z, r):
                        self.s(x, y, z, S(LOG, axis="y"))
        # stairwell: 3 x 3 ring from the bottom of the underground to the crown
        for y in range(F2, TOP + 3):
            for x in range(TX - 1, TX + 2):
                for z in range(TZ - 1, TZ + 2):
                    if y < 0:
                        self.room(x, x, z, z, y, y, PL, WOOD, WOOD)
                    else:
                        self.s(x, y, z, "air")
        pieces.spiral_stair(self.s, TX, TZ, [F2, F1, 1, 7, 13], "birch_stairs", S(LOG, axis="y"), PL,
                            newel_top=TOP + 2)
        for (dx, dz) in pieces.RING[:2]:            # landing arriving at the crown
            self.s(TX + dx, TOP - 1, TZ + dz, PL)
        # light in the trunk: glowing mushrooms on the wall of the hollow (only above the ground)
        for f in (1, 7, 13):
            self.s(TX - 2, f + 2, TZ, "shroomlight")
            self.s(TX + 2, f + 4, TZ, "shroomlight")
        # door to the clearing (north) and to the crown platform
        for (f, z1) in ((1, 32), (TOP, 32)):
            for z in range(z1, TZ - 1):
                self.a(TX, f, z, TX, f + 1, z)
            self.door(TX, f, z1, "north")
        self.platform()
        self.canopy()

    def platform(self):
        """Plank platform around the trunk, under the crown, with railing and brackets."""
        y = TOP - 1
        cells = [(x, z) for (x, z) in disc(TX, TZ, 8.5) if not self.trunk_cell(x, z)]
        inside = set(cells) | {(x, z) for (x, z) in disc(TX, TZ, 4.5)}
        for (x, z) in cells:
            self.s(x, y, z, PL)
            edge = any((x + a, z + b) not in inside for a in (-1, 0, 1) for b in (-1, 0, 1))
            if edge:
                self.s(x, y + 1, z, "birch_fence")
            else:
                for yy in (y + 1, y + 2, y + 3):
                    if self.free(x, yy, z):
                        self.s(x, yy, z, "air")
        for k in range(8):                           # brackets under the platform
            ang = math.radians(22.5 + 45 * k)
            for r in (5, 6, 7):
                x, z = round(TX + r * math.cos(ang)), round(TZ + r * math.sin(ang))
                axis = "x" if abs(math.cos(ang)) > abs(math.sin(ang)) else "z"
                self.s(x, y - 1, z, S(LOG, axis=axis))
                if r == 5:
                    self.s(x, y - 2, z, S(LOG, axis=axis))
        for (x, z) in ((TX - 6, TZ - 2), (TX + 6, TZ + 2), (TX - 2, TZ + 6), (TX + 2, TZ - 6)):
            self.hang(x, y + 3, z)
        self.chest(TX + 5, y + 1, TZ, "east", "copa")

    def canopy(self):
        """Crown of persistent leaves (they do not dry out) above the platform, with branches inside."""
        cy, rx, ry = 26, 10.5, 5.5
        for x in range(TX - 11, TX + 12):
            for z in range(TZ - 11, TZ + 12):
                for y in range(TOP + 3, cy + 6):
                    q = ((x - TX) ** 2 + (z - TZ) ** 2) / rx ** 2 + ((y - cy) / ry) ** 2
                    if q <= 1 and self.free(x, y, z):
                        self.s(x, y, z, LEAVES)
        for k in range(6):                           # ramas
            ang = math.radians(60 * k + 15)
            y = 24 + (k % 2) * 2
            for r in range(4, 9):
                x, z = round(TX + r * math.cos(ang)), round(TZ + r * math.sin(ang))
                axis = "x" if abs(math.cos(ang)) > abs(math.sin(ang)) else "z"
                self.s(x, y, z, S(LOG, axis=axis))

    def roots(self):
        """Roots that spread at the foot of the trunk and sink into the ground (none to the north, where the door is)."""
        for k in range(8):
            ang = math.radians(45 * k)
            if k == 6:                               # north: the path to the door
                continue
            for r, ys in ((5, (1, 2)), (6, (1,)), (7, (0,))):
                x, z = round(TX + r * math.cos(ang)), round(TZ + r * math.sin(ang))
                for y in ys:
                    self.s(x, y, z, WOOD)

    # ------------------------------------------------------------ stone circle
    def stone_circle(self):
        """Twelve menhirs around the tree; two have fallen."""
        self.menhirs = []
        for k in range(12):
            ang = math.radians(15 + 30 * k)
            x, z = round(TX + 13 * math.cos(ang)), round(TZ + 13 * math.sin(ang))
            hgt = 3 + (k % 2)
            if k in (2, 8):                           # fallen outwards
                dx, dz = round(math.cos(ang)), round(math.sin(ang))
                for i in range(3):
                    self.ruin_set(x + i * dx, 1, z + i * dz, "stone" if i < 2 else "andesite")
                continue
            for y in range(1, hgt + 1):
                self.s(x, y, z, "stone" if y < hgt else "andesite")
            self.s(x, 0, z, "stone")
            self.menhirs.append((x, z))

    # ------------------------------------------------------------ cabins
    def hut_shell(self, cx, cz, R_, door):
        """Round cabin: cobblestone base, adobe walls with birch posts and a solid conical thatch roof."""
        for (x, z) in disc(cx, cz, R_ + 1):
            d = dist(x, z, cx, cz)
            if d <= R_:
                self.s(x, 0, z, PMUD)
            if R_ - 1 < d <= R_:
                ang = math.degrees(math.atan2(z - cz, x - cx)) % 45
                post = ang < 8 or ang > 37
                for y in (1, 2, 3):
                    self.s(x, y, z, S(SLOG, axis="y") if post else (COB if y == 1 else MUD))
            elif d <= R_ - 1:
                for y in (1, 2, 3):
                    self.s(x, y, z, "air")
        for k in range(6):                            # roof: solid cone, each course over the one below
            for (x, z) in disc(cx, cz, R_ + 1 - k):
                self.s(x, 4 + k, z, EXISTS)
            if R_ + 1 - k < 1:
                break
        dx, dz = DV[door]
        r = int(R_)
        self.door(cx + dx * r, 1, cz + dz * r, door)
        for side in ("north", "south", "east", "west"):            # windows in the straight sections
            if side not in (door, OPP[door]):
                sx, sz = DV[side]
                self.s(cx + sx * r, 2, cz + sz * r, "glass_pane")
        self.hang(cx, 3, cz)

    def hut(self, cx, cz, i):
        """A druid's cabin (door to the east, towards the tree): bed, chest, barrel and something of his trade."""
        self.hut_shell(cx, cz, 3.5, "east")
        self.bed(cx - 2, 1, cz, "west", ("green", "lime", "brown")[i])
        self.chest(cx, 1, cz - 2, "south", "cabana")
        self.s(cx, 1, cz + 2, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        self.s(cx - 1, 1, cz + 2, ("potted_allium", "potted_lily_of_the_valley", "potted_azure_bluet")[i])
        self.s(cx + 1, 1, cz - 2, ("crafting_table", S("water_cauldron", level=3), S("composter", level=0))[i])
        if i == 2:                                    # the south cabin has its roof partly caved in
            for (x, y, z), (st, _) in list(self.t.blocks.items()):
                if "hay_block" in st and x >= cx and z >= cz - 1 and y >= 5 and (x, z) != (cx, cz) and h(x, y, z, 4) < 0.8:
                    self.ruin_set(x, y, z)
            self.ruin_set(cx + 1, 1, cz + 1, EXISTS)

    def archdruid(self):
        """Archdruid's cabin (door to the west): larger; behind the green tapestry, his hidden alcove."""
        cx, cz = 55, 21
        self.hut_shell(cx, cz, 4.5, "west")
        self.bed(cx, 1, cz - 3, "north", "white")
        self.chest(cx - 3, 1, cz - 1, "east", "cabana")
        self.s(cx, 1, cz + 3, S("lectern", facing="north", has_book=False, powered=False))
        self.s(cx + 2, 1, cz + 2, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]")
        self.s(cx - 2, 1, cz + 2, "potted_birch_sapling")
        # alcove: 1 x 2 passage in the east wall covered by the tapestry, and a 2 x 3 room with no other exit
        self.a(cx + 4, 1, cz, cx + 4, 2, cz)
        self.banner(cx + 3, 3, cz, "west", "green")
        for x in range(cx + 5, cx + 8):
            for z in range(cz - 2, cz + 3):
                wall = x == cx + 7 or z in (cz - 2, cz + 2)
                self.s(x, 0, z, PMUD)
                for y in (1, 2, 3):
                    self.s(x, y, z, (COB if y == 1 else MUD) if wall else "air")
                self.s(x, 4, z, EXISTS)
        self.chest(cx + 6, 1, cz, "west", "archidruida")
        self.s(cx + 5, 1, cz + 1, "potted_lily_of_the_valley")
        self.hang(cx + 5, 3, cz)
        self.hidden_alcove = [(x, 1, z) for x in (cx + 5, cx + 6) for z in (cz - 1, cz, cz + 1)]

    # ------------------------------------------------------------ garden, pond, observatory
    def garden(self):
        """Fenced herb garden: crop beds watered by two ditches, flowers and beehives."""
        x1, x2, z1, z2 = 20, 32, 54, 61
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x in (x1, x2) or z in (z1, z2):
                    self.s(x, 1, z, "birch_fence")
        self.s(26, 1, z1, S("birch_fence_gate", facing="north", in_wall=False, open=False, powered=False))
        crops = {56: "wheat[age=7]", 57: "carrots[age=7]", 59: "beetroots[age=3]", 60: "potatoes[age=7]"}
        flowers = ["allium", "azure_bluet", "lily_of_the_valley", "cornflower", "oxeye_daisy", "poppy"]
        for x in range(x1 + 1, x2):
            if x == 26:                              # sendero central
                continue
            for z in range(z1 + 1, z2):
                if z == 58:
                    self.s(x, 0, z, "water[level=0]")
                elif z == 55:
                    if x in (22, 30):
                        self.s(x, 1, z, S("beehive", facing="south", honey_level=5), {"id": "minecraft:beehive"})
                    elif x == 25:
                        self.chest(x, 1, z, "east", "jardin", kind="barrel")
                    else:
                        self.s(x, 0, z, "grass_block[snowy=false]")
                        self.s(x, 1, z, flowers[(x + z) % len(flowers)])
                else:
                    self.s(x, 0, z, "farmland[moisture=7]")
                    self.s(x, 1, z, crops[z])
        for z in range(z1 + 1, z2):
            self.s(26, 0, z, "dirt_path")

    def pond(self):
        """Stone pond raised one block, with lily pads."""
        x1, x2, z1, z2 = 44, 52, 50, 57
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x in (x1, x2) or z in (z1, z2):
                    self.s(x, 1, z, MSB if h(x, z, 7) < 0.4 else SB)
                    self.s(x, 0, z, SB)
                else:
                    self.s(x, 0, z, SB)
                    self.s(x, 1, z, "water[level=0]")
        for (x, z) in ((46, 52), (49, 55), (50, 52)):
            self.s(x, 2, z, "lily_pad")

    def observatory(self):
        """Observatory of aligned stones: a dais with its gnomon and three stones to the east (the sunrises)."""
        cx, cz = 58, 40
        for (x, z) in disc(cx, cz, 4.5):
            d = dist(x, z, cx, cz)
            self.s(x, 1, z, SB if d <= 3.5 else slab("stone_brick"))
        self.f(cx, 2, cz, cx, 4, cz, SB)
        self.s(cx, 5, cz, CSB)
        self.sign(cx - 1, 3, cz, "west", "gnomon", [("Enciende los", "Light the"), ("solsticios;", "solstices;"),
                                                    ("deja a oscuras", "leave dark"), ("los equinoccios.", "the equinoxes.")])
        self.chest(cx + 2, 2, cz - 2, "west", "observatorio")
        for (x, z, key, lines) in ((64, 35, "verano", [("Sol de", "Midsummer"), ("verano", "sun")]),
                                   (65, 40, "equinoccio", [("Sol de los", "Equinox"), ("equinoccios", "sun")]),
                                   (64, 45, "invierno", [("Sol de", "Midwinter"), ("invierno", "sun")])):
            self.s(x, 0, z, "stone")
            self.f(x, 1, z, x, 3, z, "stone")
            self.sign(x - 1, 2, z, "west", key, lines)

    # ------------------------------------------------------------ surface finishes
    def clearing_air(self):
        for x in range(W):
            for z in range(D):
                if not self.clear(x, z):
                    continue
                for y in range(1, AIR_H + 1):
                    if self.get(x, y, z) is None:
                        self.s(x, y, z, "air")

    def moss(self):
        """Moss carpets in patches over the path dirt of the clearing."""
        for x in range(W):
            for z in range(D):
                if self.get(x, 0, z) == "minecraft:dirt_path" and self.get(x, 1, z) == "minecraft:air" \
                        and h(x // 4, z // 4, 3) * 0.6 + h(x, z, 9) * 0.4 < 0.5:
                    self.s(x, 1, z, "moss_carpet")

    def weather(self):
        """The tree withers: gaps in the crown; and weathering on the cabins and fences."""
        for (x, y, z), (st, _) in list(self.t.blocks.items()):
            if "birch_leaves" not in st:
                continue
            exposed = any(self.free(x + a, y + b, z + c) for a, b, c in
                          ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))
            if exposed and h(x // 3, y // 3, z // 3, 13) < 0.42 and h(x, y, z, 6) < 0.9:
                self.ruin_set(x, y, z)
        for (x, y, z), (st, _) in list(self.t.blocks.items()):     # bark peeled off the trunk
            if st == "minecraft:birch_log[axis=y]" and 2 <= y <= 21 and dist(x, z, TX, TZ) > 3.5 \
                    and h(x // 2, y // 3, z // 2, 17) < 0.3:
                self.ruin_set(x, y, z, S(SLOG, axis="y"))
        for (x, z) in ((20, 57), (32, 59), (24, 61), (29, 54)):     # cerca rota
            self.ruin_set(x, 1, z)
        for (x, z) in ((44, 53), (52, 55)):                          # cracked pond wall
            self.ruin_set(x, 1, z, "cracked_stone_bricks")

    # ============================================================ subsuelo
    def room(self, x1, x2, z1, z2, y1, y2, floor=SB, wall=COB, ceil=SB):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                for y in range(y1, y2 + 1):
                    self.s(x, y, z, "air")
                    self.carved[(x, y, z)] = (floor, wall, ceil)

    def lining(self, default=(SB, COB, SB)):
        """Lines the rock faces that face the underground air (no springs or lichen)."""
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
        U, L = (F1, F1 + 3), (F2, F2 + 3)
        ROOT = ("rooted_dirt", WOOD, "rooted_dirt")
        TIMBER = (PL, S(SLOG, axis="y"), PL)
        HERB = (MUD, MUD, PL)
        self.room(36, 36, 31, 34, F1, F1 + 1, *ROOT)       # from the tree to the root hall
        self.room(28, 44, 20, 30, *U, *ROOT)               # root hall
        self.room(27, 27, 25, 25, F1, F1 + 1, *TIMBER)        # library door
        self.room(16, 26, 20, 30, *U, *TIMBER)                # biblioteca
        self.room(45, 45, 25, 25, F1, F1 + 1, *HERB)       # herbarium door
        self.room(46, 56, 20, 30, *U, *HERB)               # herbolario
        self.room(36, 37, 14, 19, F1, F1 + 2)              # trap wire corridor
        self.room(30, 44, 6, 13, *U, PMUD, COB, SB)        # ossuary of the faithful
        self.room(38, 43, 35, 35, F2, F2 + 1)              # from the tree to the offerings hall
        self.room(44, 54, 30, 40, *L)                      # offerings hall
        self.room(44, 45, 41, 45, F2, F2 + 2)              # corridor to the sun chamber
        self.room(40, 45, 46, 59, *L)                      # sun chamber
        OSC = ("deepslate_tiles", "cobbled_deepslate", "deepslate_tiles")
        self.room(24, 35, 42, 56, F2, F2 + 4, *OSC)        # rite chamber (guardian)
        self.room(29, 30, 57, 58, F2, F2 + 2, *TIMBER)        # passage to the treasure
        self.room(26, 33, 59, 64, *L, *TIMBER)                # treasure chamber
        self.lining()
        self.root_hall()
        self.library()
        self.herbalist()
        self.trap_corridor()
        self.ossuary()
        self.offerings()
        self.sun_chamber()
        self.rite_chamber()
        self.treasury()
        self.lining()                                      # whatever the mechanisms have opened

    def root_hall(self):
        y = F1
        for (x, z) in ((31, 23), (41, 23), (31, 28), (41, 28), (36, 25)):
            self.f(x, y, z, x, y + 3, z, WOOD)
        for (x, z) in ((29, 21), (33, 22), (39, 27), (43, 24), (30, 29), (38, 21), (34, 29), (42, 29)):
            self.s(x, y + 3, z, "hanging_roots[waterlogged=false]")
        self.spawner(32, y, 21, "spider")
        for (x, yy, z) in ((28, y + 3, 20), (44, y + 3, 20), (33, y + 3, 21), (31, y, 20)):
            self.s(x, yy, z, "cobweb")
        self.chest(43, y, 30, "north", "raices")
        self.door(27, y, 25, "west")
        self.door(45, y, 25, "east")

    def library(self):
        y = F1
        for z in range(22, 29):                            # bookshelves of the west wall
            for yy in (y, y + 1, y + 2):
                self.s(16, yy, z, "bookshelf")
        for x in (16, 17, 18, 25, 26):                     # and of the north (without covering the niche or the lever)
            for yy in (y, y + 1):
                self.s(x, yy, 20, "bookshelf")
        for x in range(18, 25):                            # and of the south
            if x != 21:
                for yy in (y, y + 1):
                    self.s(x, yy, 30, "bookshelf")
        self.chest(25, y, 30, "north", "biblioteca")       # its sheet of the Chronicle of the Heralds
        self.s(21, y, 30, S("lectern", facing="north", has_book=False, powered=False))
        for z in (24, 26):                                 # mesa de lectura
            self.s(21, y, z, slab("birch", "top"))
        self.s(21, y, 25, slab("birch", "top"))
        self.s(21, y + 1, 25, S("candle", candles=3, lit=False, waterlogged=False))
        self.hang(18, y + 3, 22)
        self.hang(18, y + 3, 28)
        self.sign(26, y + 1, 24, "west", "biblioteca", [("Aquí se guarda", "Here lies all"), ("lo que el bosque", "the forest has"),
                                                       ("ha contado.", "ever told.")])
        # secret door (puzzle 2): a section of bookshelf retracts; the lever, at ground level next to it
        rec = pieces.lever_door(self.s, (20, y, 18), "east", "south", "bookshelf", PL)
        self.mech["puerta_archivo"] = rec
        self.room(20, 20, 17, 17, y, y + 1, *(PL, S(SLOG, axis="y"), PL))
        self.room(17, 24, 11, 16, y, y + 2, *(PL, S(SLOG, axis="y"), PL))   # archivo (oculto)
        self.chest(18, y, 11, "south", "secreto")
        for x in (17, 19, 22, 23, 24):
            self.s(x, y, 11, "bookshelf")
            self.s(x, y + 1, 11, "bookshelf")
        self.s(24, y, 16, S("lectern", facing="west", has_book=False, powered=False))
        self.s(17, y, 16, S("candle", candles=2, lit=False, waterlogged=False))
        self.hang(21, y + 2, 13, soul=True)
        self.hidden += [(x, y, z) for x in range(17, 25) for z in range(12, 16)]

    def herbalist(self):
        y = F1
        for (x, z) in ((56, 23), (56, 27)):
            self.s(x, y, z, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]")
        for (x, z) in ((56, 24), (56, 26)):
            self.s(x, y, z, S("water_cauldron", level=3))
        self.s(56, y, 25, S("composter", level=4))
        self.chest(56, y, 21, "west", "herbolario")
        self.chest(56, y, 29, "west", "herbolario", kind="barrel")
        for x in (48, 50, 52, 54):
            self.s(x, y, 20, S("barrel", facing="up"), {"id": "minecraft:barrel"})
            self.s(x, y + 1, 20, ("potted_allium", "potted_brown_mushroom", "potted_fern", "potted_red_mushroom")[(x // 2) % 4])
        for x in range(48, 55):                            # mesa larga de secar hierbas
            self.s(x, y, 30, slab("birch", "top"))
        for x in (49, 53):
            self.s(x, y + 1, 30, "potted_azure_bluet" if x == 49 else "potted_oxeye_daisy")
        self.hang(54, y + 3, 22)
        self.hang(54, y + 3, 28)

    def trap_corridor(self):
        y = F1
        self.a(35, y, 16, 35, y + 1, 16)
        self.a(38, y, 16, 38, y + 1, 16)
        pieces.tripwire_trap(self.s, (35, 16), (38, 16), y, "x", [((35, y + 1, 16), "east"), ((38, y + 1, 16), "west")],
                             arrows=16)
        self.mech["ganchos"] = [(35, y, 16), (38, y, 16)]
        self.mech["dispensadores"] = [(35, y + 1, 16), (38, y + 1, 16)]

    def ossuary(self):
        y = F1
        self.spawner(37, y, 9, "zombie")
        self.chest(31, y, 7, "south", "osario")
        for (x, z) in ((30, 6), (44, 6), (30, 13), (44, 13), (33, 6), (41, 6)):
            self.s(x, y, z, "bone_block[axis=y]")
            self.s(x, y + 1, z, "bone_block[axis=y]")
            if (x + z) % 2:
                self.s(x, y + 2, z, S("skeleton_skull", rotation=8, powered=False))
        for (x, z) in ((34, 8), (40, 11), (42, 8), (32, 11)):
            self.s(x, y, z, "bone_block[axis=x]")
        for (x, z) in ((35, 7), (43, 10)):
            self.s(x, y, z, S("skeleton_skull", rotation=(x + z) % 16, powered=False))
        self.sign(38, y + 1, 13, "north", "osario", [("Los fieles", "The faithful"), ("descansan al pie", "rest at the foot"),
                                                     ("del árbol.", "of the tree.")])

    def offerings(self):
        y = F2
        self.spawner(47, y, 32, "skeleton")
        self.chest(45, y, 40, "north", "raices")
        for (x, z) in ((44, 30), (54, 30), (54, 40), (50, 30)):
            self.s(x, y, z, S("decorated_pot", cracked=True, facing="south", waterlogged=False))
        for z in (33, 37):
            self.s(54, y, z, "mossy_cobblestone")
            self.s(54, y + 1, z, S("candle", candles=4, lit=False, waterlogged=False))
        # greed: the offerings chest at the back of a niche with plates (trap 2: arrows from the sides)
        self.a(55, y, 35, 56, y + 1, 35)
        pieces.plate_trap(self.s, [(55, y, 35), (56, y, 35)], "north", arrows=16)
        self.chest(57, y, 35, "west", "ofrendas")
        self.mech["placas"] = [(55, y, 35), (56, y, 35)]
        self.mech["flechas"] = [(55, y, 34), (55, y, 36), (56, y, 34), (56, y, 36)]

    def sun_chamber(self):
        """Sun chamber (puzzle 1): four season stones with their lever; only the solstices lit (summer
        and winter) and the equinoxes off open the door. The false levers feed the line directly."""
        y = F2
        for z in range(46, 60):                            # face of the seasons wall
            for yy in range(y, y + 4):
                self.s(39, yy, z, SB)
        rec = pieces.combo_door(self.s, (37, y, 48), "z", 1,
                                [((40, y + 1, 54), (39, y + 1, 54)), ((40, y + 1, 58), (39, y + 1, 58))],
                                name="sol", block=MSB)
        for z in (52, 56):                                 # false levers: dust from the stone's block to the line
            self.s(40, y + 1, z, S("lever", face="wall", facing="east", powered=False))
            self.s(38, y + 1, z, "redstone_wire[east=side,north=none,south=none,west=side,power=0]")
        for z in (52, 54, 56, 58):
            for yy in (y, y + 1, y + 2):
                self.s(39, yy, z, CSB)
        names = {52: ("primavera", ("Piedra de", "Stone of"), ("la primavera", "spring")),
                 54: ("verano", ("Piedra del", "Stone of"), ("verano", "summer")),
                 56: ("otono", ("Piedra del", "Stone of"), ("otoño", "autumn")),
                 58: ("invierno", ("Piedra del", "Stone of"), ("invierno", "winter"))}
        for z, (key, l1, l2) in names.items():
            self.sign(40, y + 2, z, "east", "piedra_" + key, [l1, l2])
        self.a(39, y, 48, 38, y + 1, 48)
        self.a(36, y, 48, 36, y + 1, 48)
        for x in (36, 38, 39):
            self.carved[(x, y, 48)] = (SB, COB, SB)
            self.carved[(x, y + 1, 48)] = (SB, COB, SB)
        self.mech["sol"] = rec
        self.mech["palancas"] = [(40, y + 1, z) for z in (52, 54, 56, 58)]
        self.mech["solucion"] = (False, True, False, True)
        self.hang(43, y + 3, 50, soul=True)
        self.hang(43, y + 3, 56, soul=True)
        for z in (47, 59):
            self.banner(45, y + 2, z, "west", "yellow")

    def rite_chamber(self):
        """Rite chamber: the archdruid Cadoc, el Marchito, next to the black stump of the first tree."""
        y = F2
        cx, cz = 29, 49
        self.f(cx, y, cz, cx + 1, y + 1, cz + 1, S("stripped_dark_oak_log", axis="y"))   # stump
        for (x, z) in disc(cx + 0.5, cz + 0.5, 4.2):
            d = dist(x, z, cx + 0.5, cz + 0.5)
            if 3.4 < d <= 4.2 and (x + z) % 2 == 0:
                self.s(x, y, z, "mossy_cobblestone")
        for (x, z) in ((cx, cz - 1), (cx + 1, cz + 2)):
            self.s(x, y, z, S("candle", candles=3, lit=True, waterlogged=False))
        for z in (44, 54):
            self.banner(24, y + 3, z, "east", "black")
            self.banner(35, y + 3, z, "west", "black")
        self.hang(27, y + 4, 45, soul=True)
        self.hang(32, y + 4, 53, soul=True)
        self.chest(25, y, 43, "south", "ritual")
        self.t.entity(cx - 2, y, cz + 3, archdruid())
        self.hidden += [(x, y, z) for x in range(25, 35) for z in range(43, 56)]

    def treasury(self):
        y = F2
        self.chest(29, y, 64, "north", "premium")
        self.s(30, y, 64, "gold_block")
        self.s(30, y + 1, 64, S("candle", candles=3, lit=True, waterlogged=False))
        self.s(28, y, 64, S("barrel", facing="up"), {"id": "minecraft:barrel"})
        for (x, z) in ((26, 59), (33, 59), (26, 64), (33, 64)):
            self.s(x, y, z, S("decorated_pot", cracked=False, facing="north", waterlogged=False))
        for x in (26, 33):
            self.f(x, y, 61, x, y + 3, 61, S(SLOG, axis="y"))
        self.hang(29, y + 3, 61, soul=True)
        self.hidden += [(x, y, z) for x in range(27, 33) for z in range(60, 64)] + [(29, y, 57), (30, y, 58)]


# ------------------------------------------------------------------ guardian
def archdruid():
    """The archdruid Cadoc, el Marchito: an evoker (his vexes are his only escort); no other reinforcements."""
    return guardian("evoker", K + "guardian", "Archidruida Cadoc, el Marchito", 50, armor=4,
                    attributes={"follow_range": 20, "knockback_resistance": 0.3},
                    extra={"CanJoinRaid": B(0), "PatrolLeader": B(0)})
