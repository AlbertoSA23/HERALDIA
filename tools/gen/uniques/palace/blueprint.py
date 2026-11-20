"""Plan of the Oriental palace: a single rigid piece of 81 x 123, symmetric about x = 40.

Template coordinates: x east, z south (the gate is at z = 0), y = 0 base, y = 1 paving, feet at y = 2.
See docs/unicas/palace.md for the walkthrough and the function of each room.
"""
import math, random
from core import Template, parse_state, state_str, B
import filler_loot
from .._common import pieces

W, D, CX = 81, 123, 40
NAME = "unicas/palacio/palacio"
L = "heraldia:unicas/palacio/"

# --- materiales
PAVE, AXIS, FOUND = "stone_bricks", "polished_andesite", "stone_bricks"
RED, BAND, COL = "red_terracotta", "warped_planks", "stripped_mangrove_log[axis=y]"
MARBLE, MTOP, MST, MSLAB, BALUS = "quartz_bricks", "smooth_quartz", "smooth_quartz_stairs", "smooth_quartz_slab", "diorite_wall"
LATTICE, DOOR, CEIL, FLOOR = "dark_oak_fence", "mangrove_door", "dark_oak_planks", "smooth_stone"
DUNGEON = "deepslate_bricks"
ROOF = {"amarillo": ("bamboo_mosaic_stairs", "bamboo_mosaic_slab", "bamboo_mosaic"),
        "verde": ("prismarine_brick_stairs", "prismarine_brick_slab", "prismarine_bricks")}

_SWAP = {"east": "west", "west": "east", "left": "right", "right": "left",
         "outer_left": "outer_right", "outer_right": "outer_left", "inner_left": "inner_right", "inner_right": "inner_left"}


def mirror_state(st):
    """State mirrored about the axis x = 40 (east <-> west)."""
    bid, p = parse_state(st)
    q = {}
    for k, v in p.items():
        if k in ("east", "west"):
            q["west" if k == "east" else "east"] = v
        elif k in ("facing", "hinge", "shape"):
            q[k] = _SWAP.get(v, v)
        elif k == "rotation":
            q[k] = str((16 - int(v)) % 16)
        else:
            q[k] = v
    return state_str(bid, q)


class Construction:
    def __init__(self):
        self.t = Template(NAME)
        self.lint_open = {}      # state of the open mechanisms (for the walkthrough audit)
        self.secret = []          # positions reachable only by solving a puzzle
        self.mech = []            # redstone mechanisms for the audit
        self.protect = set()      # cells the ruin cannot touch
        self.chests = []          # (pos, tabla)

    # ---------------------------------------------------------------- primitivas
    def s(self, x, y, z, st, nbt=None, sym=False):
        self.t.set(x, y, z, st, nbt)
        if sym and x != W - 1 - x:
            self.t.set(W - 1 - x, y, z, mirror_state(st), nbt)

    def f(self, x1, y1, z1, x2, y2, z2, st, sym=False):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.s(x, y, z, st, sym=sym)

    def air(self, *a, sym=False):
        self.f(*a, "air", sym=sym)

    def put(self, sym):
        return lambda x, y, z, st, nbt=None: self.s(x, y, z, st, nbt, sym=sym)

    def chest(self, x, y, z, facing, tbl, sym=False, kind="chest"):
        pieces.chest(self.put(sym), x, y, z, facing, L + tbl, kind=kind)
        self.chests.append(((x, y, z), tbl))
        if sym:
            self.chests.append(((W - 1 - x, y, z), tbl))

    def barrel(self, x, y, z, tbl, sym=False, facing="up"):
        pieces.chest(self.put(sym), x, y, z, facing, L + tbl, kind="barrel")
        self.chests.append(((x, y, z), tbl))
        if sym:
            self.chests.append(((W - 1 - x, y, z), tbl))

    def door(self, x, y, z, facing, sym=False, kind=DOOR, hinge="left"):
        self.s(x, y, z, f"{kind}[facing={facing},half=lower,hinge={hinge},open=false,powered=false]", sym=sym)
        self.s(x, y + 1, z, f"{kind}[facing={facing},half=upper,hinge={hinge},open=false,powered=false]", sym=sym)

    def lantern(self, x, y, z, sym=False):
        self.s(x, y, z, "lantern[hanging=true,waterlogged=false]", sym=sym)

    def ladder(self, x, y1, y2, z, facing, sym=False):
        for y in range(y1, y2 + 1):
            self.s(x, y, z, f"ladder[facing={facing},waterlogged=false]", sym=sym)

    def ring(self, x0, z0, x1, z1, y, st, sym=False):
        for x in range(x0, x1 + 1):
            self.s(x, y, z0, st, sym=sym); self.s(x, y, z1, st, sym=sym)
        for z in range(z0, z1 + 1):
            self.s(x0, y, z, st, sym=sym); self.s(x1, y, z, st, sym=sym)

    def walls(self, x0, z0, x1, z1, y0, y1, st, sym=False):
        for y in range(y0, y1 + 1):
            self.ring(x0, z0, x1, z1, y, st, sym=sym)

    def roof(self, x0, z0, x1, z1, y, kind, ov=2, rings=None, sym=False, ceiling=True):
        """Four-sided stepped roof over the rectangle of walls, with an eave of `ov` blocks.
        `rings` limits the number of courses (lower eave of a double-eave roof)."""
        st, slab, full = ROOF[kind]
        if ceiling:
            self.f(x0, y, z0, x1, y, z1, CEIL, sym=sym)
        a0, b0, a1, b1 = x0 - ov, z0 - ov, x1 + ov, z1 + ov
        k = 0
        while True:
            c0, d0, c1, d1, yy = a0 + k, b0 + k, a1 - k, b1 - k, y + k
            if rings is not None and k >= rings:
                break
            if c1 - c0 < 2 or d1 - d0 < 2:
                self.f(c0, yy - 1, d0, c1, yy, d1, full, sym=sym)
                self.f(c0, yy + 1, d0, c1, yy + 1, d1, f"{slab}[type=bottom,waterlogged=false]", sym=sym)
                break
            if k > 0:      # solid roof under each course: nothing rests on a single edge
                cells = [(x, z) for x in range(c0, c1 + 1) for z in (d0, d1)] + \
                        [(x, z) for z in range(d0, d1 + 1) for x in (c0, c1)]
                for (x, z) in cells:
                    for y2 in range(y, yy):
                        if self.t.get(x, y2, z) in (None, "minecraft:air"):
                            self.s(x, y2, z, full, sym=sym)
            for x in range(c0 + 1, c1):
                self.s(x, yy, d0, f"{st}[facing=south,half=bottom,shape=straight,waterlogged=false]", sym=sym)
                self.s(x, yy, d1, f"{st}[facing=north,half=bottom,shape=straight,waterlogged=false]", sym=sym)
            for z in range(d0 + 1, d1):
                self.s(c0, yy, z, f"{st}[facing=east,half=bottom,shape=straight,waterlogged=false]", sym=sym)
                self.s(c1, yy, z, f"{st}[facing=west,half=bottom,shape=straight,waterlogged=false]", sym=sym)
            for x, z, fc, sh in ((c0, d0, "south", "outer_left"), (c1, d0, "south", "outer_right"),
                                 (c0, d1, "north", "outer_right"), (c1, d1, "north", "outer_left")):
                self.s(x, yy, z, f"{st}[facing={fc},half=bottom,shape={sh},waterlogged=false]", sym=sym)
                if k == 0:   # raised eave tips
                    self.s(x, yy + 1, z, f"{slab}[type=bottom,waterlogged=false]", sym=sym)
            k += 1

    def plinth(self, x0, z0, x1, z1, y=2, sym=False):
        self.f(x0, y, z0, x1, y, z1, MARBLE, sym=sym)
        self.f(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, MTOP, sym=sym)

    def stairs_row(self, xa, xb, y, z, facing, st=MST, sym=False):
        for x in range(xa, xb + 1):
            self.s(x, y, z, f"{st}[facing={facing},half=bottom,shape=straight,waterlogged=false]", sym=sym)

    def stairs_col(self, x, y, za, zb, facing, st=MST, sym=False):
        for z in range(za, zb + 1):
            self.s(x, y, z, f"{st}[facing={facing},half=bottom,shape=straight,waterlogged=false]", sym=sym)

    def tree(self, x, z, h=4, sym=False):
        """Cerezo en un parterre de hierba."""
        self.f(x - 1, 1, z - 1, x + 1, 1, z + 1, "grass_block[snowy=false]", sym=sym)
        for y in range(2, 2 + h):
            self.s(x, y, z, "cherry_log[axis=y]", sym=sym)
        top = 1 + h
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                for dy in range(-1, 3):
                    r = dx * dx + dz * dz + (dy * dy * 2)
                    if r <= 10 and not (dx == 0 and dz == 0 and dy <= 0):
                        self.s(x + dx, top + dy, z + dz, "cherry_leaves[distance=1,persistent=true,waterlogged=false]", sym=sym)
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.s(x + dx, 2, z + dz, "pink_petals[facing=north,flower_amount=3]", sym=sym)

    def stone_lantern(self, x, z, sym=False):
        self.s(x, 2, z, "stone_brick_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]", sym=sym)
        self.s(x, 3, z, "chiseled_stone_bricks", sym=sym)
        self.s(x, 4, z, "lantern[hanging=false,waterlogged=false]", sym=sym)

    # ---------------------------------------------------------------- redstone
    def piston_door(self, piston, facing, door_blocks, mat, lever=None, attached=None, label=""):
        """Closed sticky piston door (extended and powered). `piston` is the list of bases;
        each one pushes its door block towards `facing`. The open state is recorded for auditing."""
        dx, dz = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}[facing]
        pieces.piston_door(self.put(False), door_blocks, (-dx, -dz), facing, mat)
        for (x, y, z) in piston:
            self.lint_open[(x, y, z)] = f"sticky_piston[extended=false,facing={facing}]"
            self.lint_open[(x + dx, y, z + dz)] = mat
            self.lint_open[(x + 2 * dx, y, z + 2 * dz)] = "air"
            self.protect |= {(x, y, z), (x + dx, y, z + dz), (x + 2 * dx, y, z + 2 * dz)}
        self.mech.append(dict(kind="puerta", label=label, pistons=list(piston), facing=facing, door=door_blocks))

    def lever(self, x, y, z, facing, powered, label=""):
        """Lever on the face of a wall; `facing` is where it sticks out (the support block is behind)."""
        self.s(x, y, z, f"lever[face=wall,facing={facing},powered={'true' if powered else 'false'}]")
        self.protect.add((x, y, z))
        self.mech.append(dict(kind="palanca", label=label, pos=(x, y, z), facing=facing, powered=powered))

    def dispenser(self, x, y, z, facing, arrows=8, triggered=False):
        items = [{"Slot": B(0), "id": "minecraft:arrow", "count": arrows}] if arrows else []
        self.s(x, y, z, f"dispenser[facing={facing},triggered={'true' if triggered else 'false'}]",
               {"id": "minecraft:dispenser", "Items": items})
        self.protect.add((x, y, z))

    def tripwire(self, z, x0, x1, y=2, label=""):
        """Tripwire across a north-south corridor between the walls x0 and x1 (hooks at x0+1 and x1-1)."""
        pieces.tripwire_trap(self.put(False), (x0 + 1, z), (x1 - 1, z), y, "x",
                             [((x0, y + 1, z), "east"), ((x1, y + 1, z), "west")])
        self.protect |= {(x, yy, z) for x in range(x0, x1 + 1) for yy in (y, y + 1)}
        self.mech.append(dict(kind="cable", label=label, z=z, x0=x0, x1=x1, y=y))


# ==================================================================== construction
def construct():
    o = Construction()
    t = o.t
    # ---- base, paving and flight of stairs
    o.f(0, 0, 1, W - 1, 0, D - 1, FOUND)
    o.f(0, 1, 2, W - 1, 1, D - 1, PAVE)
    o.stairs_row(34, 46, 0, 0, "south")
    o.stairs_row(34, 46, 1, 1, "south")
    o.f(37, 1, 2, 43, 1, 27, AXIS)

    city_wall(o)
    noon_door(o)
    outer_courtyard(o)
    harmony_door(o)
    library_treasury(o)
    platform_and_hall(o)
    below_the_hall(o)
    garden_wall(o)
    garden(o)
    pagoda(o)
    pavilions(o)
    return o


def city_wall(o):
    """Perimeter wall 3 thick: stone base, red body and yellow coping."""
    st, slab, full = ROOF["amarillo"]

    def segment(x0, z0, x1, z1, axis):
        o.f(x0, 2, z0, x1, 3, z1, PAVE)
        o.f(x0, 4, z0, x1, 8, z1, RED)
        if axis == "x":      # wall running from west to east (north and south faces)
            for x in range(x0, x1 + 1):
                o.s(x, 9, z0, f"{st}[facing=south,half=bottom,shape=straight,waterlogged=false]")
                o.s(x, 9, z0 + 1, full)
                o.s(x, 9, z1, f"{st}[facing=north,half=bottom,shape=straight,waterlogged=false]")
                o.s(x, 10, z0 + 1, f"{slab}[type=bottom,waterlogged=false]")
        else:
            for z in range(z0, z1 + 1):
                o.s(x0, 9, z, f"{st}[facing=east,half=bottom,shape=straight,waterlogged=false]")
                o.s(x0 + 1, 9, z, full)
                o.s(x1, 9, z, f"{st}[facing=west,half=bottom,shape=straight,waterlogged=false]")
                o.s(x0 + 1, 10, z, f"{slab}[type=bottom,waterlogged=false]")
    segment(3, 2, W - 4, 4, "x")
    segment(3, D - 3, W - 4, D - 1, "x")
    segment(0, 2, 2, D - 1, "z")
    segment(W - 3, 2, W - 1, D - 1, "z")
    for x0 in (0, W - 3):        # esquinas: remate macizo
        for z0 in (2, D - 3):
            o.f(x0, 9, z0, x0 + 2, 9, z0 + 2, full)
            o.s(x0 + 1, 10, z0 + 1, f"{slab}[type=bottom,waterlogged=false]")


def noon_door(o):
    """Monumental gate: 17 x 7 solid mass with a central passage, guard bodies and upper pavilion."""
    o.f(32, 2, 2, 48, 3, 8, PAVE)
    o.f(32, 4, 2, 48, 8, 8, RED)
    o.f(32, 9, 2, 48, 9, 8, AXIS)
    for x in range(32, 49):                       # pretil
        for z in (2, 8):
            o.s(x, 10, z, "stone_brick_wall[east=low,north=none,south=none,up=false,waterlogged=false,west=low]")
    for z in range(3, 8):
        for x in (32, 48):
            o.s(x, 10, z, "stone_brick_wall[east=none,north=low,south=low,up=false,waterlogged=false,west=none]")
    for x, z in ((32, 2), (48, 2), (32, 8), (48, 8)):
        o.s(x, 10, z, "stone_brick_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]")
    # paso
    o.air(39, 2, 2, 41, 5, 8)
    for z in range(2, 9):
        o.s(39, 5, z, "stone_brick_stairs[facing=west,half=top,shape=straight,waterlogged=false]")
        o.s(41, 5, z, "stone_brick_stairs[facing=east,half=top,shape=straight,waterlogged=false]")
    # cuerpos de guardia
    o.air(33, 2, 3, 37, 5, 7, sym=True)
    o.f(33, 1, 3, 37, 1, 7, "spruce_planks", sym=True)
    o.door(38, 2, 5, "west", sym=True)
    o.ladder(33, 2, 9, 4, "east", sym=True)
    o.chest(35, 2, 7, "north", "guardia", sym=True)
    o.s(37, 2, 3, "crafting_table", sym=True)
    o.lantern(35, 5, 4, sym=True)
    o.lantern(40, 4, 5)
    # upper pavilion
    for x in (34, 37, 40, 43, 46):
        for z in (3, 7):
            o.f(x, 10, z, x, 13, z, COL)
    for z in (5,):
        o.f(34, 10, z, 34, 13, z, COL, sym=True)
    for x in (35, 36, 38, 39, 41, 42, 44, 45):
        for z in (3, 7):
            o.s(x, 10, z, LATTICE)
    o.ring(34, 3, 46, 7, 13, BAND)
    o.roof(34, 3, 46, 7, 14, "amarillo", ov=2)
    o.barrel(36, 10, 4, "torre")
    o.lantern(37, 13, 5, sym=True)


def outer_courtyard(o):
    # river of golden water with balustrade and three arched bridges
    o.f(8, 1, 15, 72, 1, 17, "water[level=0]")
    bridges = [(36, 44), (23, 27), (53, 57)]
    inbridge = lambda x: any(a <= x <= b for a, b in bridges)
    for x in range(7, 74):
        if inbridge(x):
            continue
        for z in (14, 18):
            o.s(x, 2, z, "stone_brick_wall[east=low,north=none,south=none,up=false,waterlogged=false,west=low]")
    for z in range(14, 19):
        o.s(7, 2, z, "stone_brick_wall[east=none,north=low,south=low,up=false,waterlogged=false,west=none]", sym=True)
    for a, b in bridges:
        mat = MTOP if a == 36 else AXIS
        o.stairs_row(a, b, 2, 14, "south", st=MST if a == 36 else "polished_andesite_stairs")
        o.stairs_row(a, b, 2, 18, "north", st=MST if a == 36 else "polished_andesite_stairs")
        o.f(a, 2, 15, b, 2, 17, mat)
        for z in range(14, 19):
            for x in (a, b):
                o.s(x, 3, z, f"{BALUS}[east=none,north=low,south=low,up={'true' if z in (14, 18) else 'false'},waterlogged=false,west=none]")
    for x, z in ((12, 16), (30, 15), (48, 17), (66, 16), (20, 17), (60, 15)):
        o.s(x, 2, z, "lily_pad")
    o.tree(12, 9, sym=True)
    o.tree(12, 23, sym=True)
    for z in (11, 23):
        o.stone_lantern(35, z, sym=True)


def harmony_door(o):
    """Intermediate wall with the gate-hall of Supreme Harmony (central passage and two rooms)."""
    st, slab, full = ROOF["amarillo"]
    o.f(3, 2, 28, W - 4, 3, 30, PAVE)
    o.f(3, 4, 28, W - 4, 8, 30, RED)
    for x in range(3, W - 3):
        o.s(x, 9, 28, f"{st}[facing=south,half=bottom,shape=straight,waterlogged=false]")
        o.s(x, 9, 29, full)
        o.s(x, 9, 30, f"{st}[facing=north,half=bottom,shape=straight,waterlogged=false]")
        o.s(x, 10, 29, f"{slab}[type=bottom,waterlogged=false]")
    o.air(28, 2, 25, 52, 10, 33)
    o.plinth(27, 25, 53, 33)
    o.f(37, 2, 25, 43, 2, 33, AXIS)
    o.stairs_row(37, 43, 2, 24, "south")
    o.stairs_row(37, 43, 2, 34, "north")
    # salas laterales
    o.walls(28, 26, 36, 32, 3, 7, RED, sym=True)
    for z in (26, 32):
        o.f(31, 4, z, 33, 5, z, LATTICE, sym=True)
    o.f(29, 2, 27, 35, 2, 31, "spruce_planks", sym=True)
    o.door(36, 3, 29, "east", sym=True)
    o.chest(30, 3, 31, "north", "guardia")
    o.barrel(50, 3, 31, "almacen")
    o.barrel(50, 3, 27, "almacen")
    o.s(30, 3, 27, "red_bed[facing=west,occupied=false,part=head]")
    o.s(31, 3, 27, "red_bed[facing=west,occupied=false,part=foot]")
    o.s(48, 3, 31, "smoker[facing=north,lit=false]")
    o.lantern(32, 7, 29, sym=True)
    # central passage with columns
    for x in (28, 31, 34, 37, 43, 46, 49, 52):
        for z in (26, 32):
            o.f(x, 3, z, x, 7, z, COL)
    o.ring(28, 26, 52, 32, 8, BAND)
    o.f(37, 8, 27, 43, 8, 31, CEIL)
    o.lantern(40, 7, 29)
    o.roof(28, 26, 52, 32, 9, "amarillo", ov=2)


def library_treasury(o):
    """Library (west) and treasury (east): the same outside, different inside."""
    o.plinth(3, 35, 18, 57, sym=True)
    o.walls(4, 36, 17, 56, 3, 7, RED, sym=True)
    o.f(5, 2, 37, 16, 2, 55, "spruce_planks", sym=True)
    for z in (43, 50):
        o.f(17, 4, z - 1, 17, 5, z + 1, LATTICE, sym=True)
    for x in (8, 13):
        o.f(x - 1, 4, 56, x + 1, 5, 56, LATTICE, sym=True)
        o.f(x - 1, 4, 36, x + 1, 5, 36, LATTICE, sym=True)
    for (x, z) in ((4, 36), (17, 36), (4, 56), (17, 56), (17, 46 - 2), (17, 46 + 2)):
        o.f(x, 3, z, x, 7, z, COL, sym=True)
    o.door(17, 3, 46, "east", sym=True)
    o.stairs_col(19, 2, 45, 47, "west", sym=True)
    o.roof(4, 36, 17, 56, 8, "verde", ov=1, sym=True)
    # ---- library: bookshelves, lecterns, secret study behind the book wall (z = 41)
    o.f(5, 3, 43, 5, 5, 55, "bookshelf")
    o.f(5, 3, 46, 5, 4, 46, "air")         # hueco de lectura
    o.f(6, 3, 55, 15, 5, 55, "bookshelf")
    o.f(9, 3, 55, 12, 4, 55, "air")
    o.s(10, 3, 54, "lectern[facing=north,has_book=false,powered=false]")
    o.s(11, 3, 54, "lectern[facing=north,has_book=false,powered=false]")
    o.chest(16, 3, 54, "west", "biblioteca")
    o.s(8, 3, 48, "spruce_planks"); o.s(8, 3, 49, "spruce_planks")
    o.s(8, 4, 48, "candle[candles=2,lit=false,waterlogged=false]")
    o.s(7, 3, 48, "spruce_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
    o.s(9, 3, 49, "spruce_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    o.lantern(10, 7, 48)
    o.lantern(10, 7, 38)
    o.f(5, 3, 41, 16, 7, 41, "bookshelf")
    o.f(7, 3, 42, 8, 7, 42, "bookshelf")      # columns of books (the left one hides the pistons)
    o.f(10, 3, 42, 11, 7, 42, "bookshelf")
    o.piston_door([(7, 3, 41), (7, 4, 41)], "east", [(9, 3, 41), (9, 4, 41)], "bookshelf", label="biblioteca")
    o.lever(7, 4, 43, "south", True, label="biblioteca")
    o.chest(5, 3, 38, "east", "biblioteca_secreta")
    o.secret.append((5, 3, 38))
    o.s(16, 3, 38, "lectern[facing=west,has_book=false,powered=false]")
    o.f(13, 3, 37, 15, 3, 37, "spruce_planks")
    o.s(14, 4, 37, "candle[candles=3,lit=false,waterlogged=false]")
    o.s(5, 3, 37, "bookshelf"); o.s(5, 4, 37, "bookshelf")
    # ---- treasury: barrels, vault with iron door and trapped chest
    o.f(64, 3, 41, 75, 7, 41, "polished_andesite")
    o.f(69, 3, 42, 70, 7, 42, "polished_andesite")
    o.f(72, 3, 42, 73, 7, 42, "polished_andesite")
    o.door(71, 3, 41, "north", kind="iron_door")
    o.s(71, 4, 42, "stone_button[face=wall,facing=west,powered=false]")     # on the face of the column, next to the door
    o.s(70, 4, 40, "stone_button[face=wall,facing=north,powered=false]")
    o.barrel(64, 3, 55, "tesoreria_menor")
    o.barrel(75, 3, 55, "tesoreria_menor")
    o.f(66, 3, 55, 73, 3, 55, "spruce_planks")
    o.s(68, 4, 55, "candle[candles=1,lit=false,waterlogged=false]")
    o.lantern(70, 7, 48)
    o.lantern(70, 7, 38)
    o.chest(71, 3, 37, "south", "tesoreria", kind="trapped_chest")
    o.s(71, 3, 38, "stone_pressure_plate[powered=false]")
    o.dispenser(70, 3, 38, "east")
    o.dispenser(72, 3, 38, "west")
    o.protect |= {(71, 3, 37), (71, 3, 38)}
    o.mech.append(dict(kind="placa", label="tesoreria", plate=(71, 3, 38), disp=[(70, 3, 38), (72, 3, 38)]))
    for x in (65, 77 - 3):
        o.s(x, 3, 37, "decorated_pot[cracked=false,facing=south,waterlogged=false]")


def platform_and_hall(o):
    """Three-tier platform, flights of steps on the axis and throne hall with a double eave."""
    o.f(22, 2, 36, 58, 3, 76, MARBLE)
    o.f(24, 4, 38, 56, 5, 74, MARBLE)
    o.f(26, 6, 40, 54, 7, 72, MARBLE)
    o.f(23, 3, 37, 57, 3, 75, MTOP)
    o.f(25, 5, 39, 55, 5, 73, MTOP)
    o.f(27, 7, 41, 53, 7, 71, MTOP)
    for (x0, z0, x1, z1, y) in ((22, 36, 58, 76, 4), (24, 38, 56, 74, 6), (26, 40, 54, 72, 8)):
        for x in range(x0, x1 + 1):
            for z in (z0, z1):
                if not 35 <= x <= 45:
                    o.s(x, y, z, f"{BALUS}[east=low,north=none,south=none,up={'true' if x in (x0, x1, 34, 46) else 'false'},waterlogged=false,west=low]")
        for z in range(z0 + 1, z1):
            for x in (x0, x1):
                o.s(x, y, z, f"{BALUS}[east=none,north=low,south=low,up=false,waterlogged=false,west=none]")
    o.f(37, 1, 31, 43, 1, 33, AXIS)
    o.f(37, 1, 77, 43, 1, 79, AXIS)
    for k in range(6):
        zf, zb = 34 + k, 78 - k
        o.f(36, 1, zf, 44, 1 + k, zf, MARBLE)
        o.f(36, 1, zb, 44, 1 + k, zb, MARBLE)
        o.stairs_row(36, 38, 2 + k, zf, "south", sym=True)
        o.stairs_row(36, 38, 2 + k, zb, "north", sym=True)
        o.f(39, 2 + k, zf, 41, 2 + k, zf, "chiseled_quartz_block")       # dragon ramp
        o.f(39, 2 + k, zb, 41, 2 + k, zb, "chiseled_quartz_block")
        for x in (35, 45):
            o.s(x, 2 + k, zf, MARBLE); o.s(x, 2 + k, zb, MARBLE)
    # ---- hall
    o.f(28, 7, 46, 52, 7, 66, FLOOR)
    for x in (27, 30, 33, 36, 44, 47, 50, 53):
        for z in (45, 67):
            o.f(x, 8, z, x, 12, z, COL)
    for z in (48, 51, 54, 57, 60, 63):
        o.f(27, 8, z, 27, 12, z, COL, sym=True)
    o.ring(27, 45, 53, 67, 13, BAND)
    o.walls(29, 47, 51, 65, 8, 16, RED)
    o.f(29, 8, 63, 51, 16, 65, RED)          # muro trasero de tres
    o.air(39, 8, 47, 41, 11, 47)             # portada central
    for x in (31, 32, 35, 36, 44, 45, 48, 49):
        o.f(x, 9, 47, x, 12, 47, LATTICE)
    for z in (50, 51, 55, 56):
        o.f(29, 9, z, 29, 12, z, LATTICE, sym=True)
    for z in (49, 52, 55, 58, 61):
        o.f(29, 8, z, 29, 16, z, COL, sym=True)
    for x in (34,):
        for z in (50, 53):
            o.f(x, 8, z, x, 16, z, COL, sym=True)
    o.f(30, 17, 48, 50, 17, 62, CEIL)
    for x in range(31, 50, 4):
        for z in range(49, 62, 4):
            o.s(x, 17, z, "cyan_terracotta")
    o.roof(27, 45, 53, 67, 13, "amarillo", ov=1, rings=3, ceiling=False)
    o.roof(29, 47, 51, 65, 17, "amarillo", ov=2, ceiling=False)
    # dais and throne
    o.f(36, 8, 55, 44, 8, 58, MTOP)
    o.stairs_row(38, 42, 8, 54, "south")
    o.s(40, 9, 57, "smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    o.s(39, 9, 57, "bamboo_mosaic_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
    o.s(41, 9, 57, "bamboo_mosaic_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    o.f(35, 8, 59, 45, 13, 59, RED)          # biombo
    o.f(38, 9, 59, 42, 12, 59, "yellow_glazed_terracotta[facing=north]")
    o.s(37, 9, 56, "yellow_banner[rotation=8]"); o.s(43, 9, 56, "yellow_banner[rotation=8]")
    o.s(37, 9, 55, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    o.s(43, 9, 55, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    for x, z in ((34, 52), (46, 52), (40, 50), (34, 58), (46, 58)):
        o.lantern(x, 15, z)
    # rear corridor: twin columns; the left one hides the secret door, the right one is a decoy
    o.f(38, 8, 62, 39, 16, 62, RED)
    o.f(41, 8, 62, 42, 16, 62, RED)
    o.piston_door([(38, 8, 63), (38, 9, 63)], "east", [(40, 8, 63), (40, 9, 63)], RED, label="trono")
    o.lever(38, 9, 61, "north", True, label="trono")
    o.dispenser(38, 8, 62, "north", arrows=0, triggered=True)
    # the throne column's dispenser is only a block of the secret door's circuit (its lever keeps it powered): left
    # empty on purpose, or the circuit would spit its loot out each time the door is worked
    filler_loot.leave_empty(o.t, 38, 8, 62, "palace: redstone part of the secret door, not storage")
    o.lever(42, 9, 61, "north", False, label="senuelo")
    o.dispenser(42, 8, 62, "north", arrows=6)
    o.mech.append(dict(kind="senuelo", label="senuelo", lever=(42, 9, 61), disp=(42, 8, 62)))
    o.air(40, 8, 64, 40, 9, 64)               # hidden cupboard in the rear wall
    o.chest(31, 8, 62, "east", "salon")
    o.s(49, 8, 62, "decorated_pot[cracked=false,facing=west,waterlogged=false]")
    o.lantern(33, 16, 61, sym=True)


def below_the_hall(o):
    """Interior of the platform (not a basement: it is above the base). Antechamber, trap corridor,
    warriors' room (spawners) and treasure chamber under the throne."""
    o.f(27, 1, 41, 53, 6, 71, DUNGEON)
    o.f(28, 1, 42, 52, 1, 70, "polished_deepslate")
    rooms = [(37, 60, 43, 64), (29, 61, 35, 63), (29, 44, 31, 63), (33, 42, 47, 47), (34, 50, 46, 58)]
    for x0, z0, x1, z1 in rooms:
        o.air(x0, 2, z0, x1, 5, z1)
    o.air(36, 2, 62, 36, 3, 62)                # antechamber -> corridor
    o.air(32, 2, 44, 32, 3, 45)                # corridor -> warriors' room
    o.air(40, 2, 49, 40, 3, 49)                # passage of the chamber (2-thick wall)
    o.lantern(40, 5, 61)
    o.ladder(40, 2, 7, 64, "north")            # shaft from the hall's cupboard
    # traps: two wires with facing dispensers
    o.tripwire(56, 28, 32, label="pasillo sur")
    o.tripwire(50, 28, 32, label="pasillo norte")
    # warriors' room: terracotta statues and two spawners, no light
    for x in (34, 36, 38, 42, 44, 46):
        o.f(x, 2, 42, x, 3, 42, "terracotta")
        o.s(x, 4, 42, "brown_terracotta")
    pieces.spawner(o.s, 35, 2, 45, "zombie")
    pieces.spawner(o.s, 45, 2, 45, "skeleton")
    o.protect |= {(35, 2, 45), (45, 2, 45)}
    # two-lever lock: low block to the west, high one to the east
    o.f(38, 2, 47, 39, 5, 47, DUNGEON)
    o.f(41, 2, 47, 42, 5, 47, DUNGEON)
    o.piston_door([(38, 2, 48)], "east", [(40, 2, 48)], DUNGEON, label="camara (bajo)")
    o.piston_door([(42, 3, 48)], "west", [(40, 3, 48)], DUNGEON, label="camara (alto)")
    o.lever(37, 2, 47, "north", True, label="camara (bajo)")
    o.lever(43, 3, 47, "north", True, label="camara (alto)")
    # treasure chamber
    o.f(34, 1, 50, 46, 1, 58, "polished_blackstone_bricks")
    o.f(38, 1, 52, 42, 1, 56, "yellow_glazed_terracotta[facing=north]")
    o.chest(40, 2, 58, "north", "premium")
    o.chest(34, 2, 54, "east", "boveda")
    o.chest(46, 2, 54, "west", "boveda")
    o.secret += [(40, 2, 58), (34, 2, 54), (46, 2, 54), (30, 2, 62)]
    for x, z in ((34, 50), (46, 50), (34, 58), (46, 58)):
        o.s(x, 2, z, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    o.lantern(37, 5, 54, sym=True)
    o.t.entity(40, 2, 53, GUARDIAN)
    o.guardian = (40, 2, 53)


GUARDIAN = pieces.guardian(
    "vindicator", "heraldia.palacio.guardian", "Comandante de la Guardia Imperial", 40,
    equipment={"mainhand": {"id": "minecraft:iron_axe", "count": 1},
               "chest": {"id": "minecraft:chainmail_chestplate", "count": 1},
               "head": {"id": "minecraft:golden_helmet", "count": 1}},
    drop_chances={"mainhand": 0.0, "chest": 0.0, "head": 0.0})


def garden_wall(o):
    """Garden wall with a moon gate on the axis and two wicket gates."""
    st, slab, full = ROOF["amarillo"]
    o.f(3, 2, 80, W - 4, 3, 82, PAVE)
    o.f(3, 4, 80, W - 4, 8, 82, RED)
    for x in range(3, W - 3):
        o.s(x, 9, 80, f"{st}[facing=south,half=bottom,shape=straight,waterlogged=false]")
        o.s(x, 9, 81, full)
        o.s(x, 9, 82, f"{st}[facing=north,half=bottom,shape=straight,waterlogged=false]")
        o.s(x, 10, 81, f"{slab}[type=bottom,waterlogged=false]")
    for x in range(34, 47):
        for y in range(2, 10):
            r = math.hypot(x - CX, y - 5)
            for z in (80, 81, 82):
                if r <= 3.5:
                    o.s(x, y, z, "air")
                elif r <= 4.5:
                    o.s(x, y, z, MARBLE)
    o.air(20, 2, 80, 20, 3, 82, sym=True)
    o.door(20, 2, 81, "south", sym=True)


def garden(o):
    o.f(3, 1, 83, W - 4, 1, D - 4, "grass_block[snowy=false]")
    o.f(38, 1, 83, 42, 1, 87, AXIS)
    o.f(38, 1, 103, 42, 1, 105, AXIS)
    o.f(17, 1, 90, 26, 1, 92, AXIS, sym=True)
    o.f(17, 1, 110, 33, 1, 112, AXIS, sym=True)
    o.f(19, 1, 80, 21, 1, 92, AXIS, sym=True)
    # estanque
    o.f(26, 1, 87, 54, 1, 103, "mossy_cobblestone")
    o.f(27, 1, 88, 53, 1, 102, "water[level=0]")
    for x, z in ((26, 90), (26, 99), (30, 87), (50, 87), (30, 103), (50, 103)):
        o.s(x, 2, z, "mossy_cobblestone", sym=True)
    for x, z in ((30, 91), (33, 99), (47, 92), (50, 100), (29, 96), (35, 89)):
        o.s(x, 2, z, "lily_pad")
    # bridge and lake pavilion
    o.f(38, 2, 88, 42, 2, 102, "spruce_planks")
    o.stairs_row(38, 42, 2, 87, "south", st="spruce_stairs")
    o.stairs_row(38, 42, 2, 103, "north", st="spruce_stairs")
    o.f(35, 2, 93, 45, 2, 97, "spruce_planks")
    for z in list(range(88, 93)) + list(range(98, 103)):
        o.s(38, 3, z, "spruce_fence[east=false,north=true,south=true,waterlogged=false,west=false]", sym=True)
    for x in range(35, 46):
        for z in (93, 97):
            if not 39 <= x <= 41:
                o.s(x, 3, z, "spruce_fence[east=true,north=false,south=false,waterlogged=false,west=true]")
    for z in range(94, 97):
        o.s(35, 3, z, "spruce_fence[east=false,north=true,south=true,waterlogged=false,west=false]", sym=True)
    for x, z in ((35, 93), (35, 97)):
        o.f(x, 3, z, x, 6, z, COL, sym=True)
    o.roof(35, 93, 45, 97, 7, "verde", ov=1)
    o.barrel(36, 3, 95, "jardin", facing="east")
    o.s(44, 3, 95, "spruce_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    o.lantern(40, 6, 95)
    # trees, bamboo and lanterns
    for x, z in ((8, 101), (24, 86), (22, 115)):
        o.tree(x, z, sym=True)
    for x0, z0 in ((19, 96), (29, 114)):
        rng = random.Random(x0 * 31 + z0)
        for dx in range(4):
            for dz in range(4):
                if rng.random() < 0.55:
                    h = rng.randint(3, 5)
                    for y in range(2, 2 + h):
                        leaves = "large" if y == 1 + h else ("small" if y == h else "none")
                        o.s(x0 + dx, y, z0 + dz, f"bamboo[age=0,leaves={leaves},stage=0]", sym=True)
    for z in (84, 104):
        o.stone_lantern(36, z, sym=True)


def pagoda(o):
    """Five-storey pagoda with a central pillar; alternating ladders on the pillar."""
    o.plinth(34, 105, 46, 117)
    o.stairs_row(38, 42, 2, 104, "south")
    stories = [(36, 107, 44, 115, 3, 6), (36, 107, 44, 115, 8, 11), (37, 108, 43, 114, 13, 16),
             (37, 108, 43, 114, 18, 21), (38, 109, 42, 113, 23, 26)]
    for i, (x0, z0, x1, z1, y0, y1) in enumerate(stories):
        o.walls(x0, z0, x1, z1, y0, y1, RED)
        for (x, z) in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            o.f(x, y0, z, x, y1, z, COL)
        mx, mz = (x0 + x1) // 2, (z0 + z1) // 2
        for (x, z) in ((mx, z0), (mx, z1), (x0, mz), (x1, mz)):
            if not (i == 0 and z == z0):
                o.f(x, y0 + 1, z, x, y0 + 2, z, LATTICE)
        o.f(x0, y1 + 1, z0, x1, y1 + 1, z1, CEIL)        # floor slab (floor of the next storey)
        if i < 4:
            st, slab, full = ROOF["verde"]
            for (a0, b0, a1, b1, yy) in ((x0 - 2, z0 - 2, x1 + 2, z1 + 2, y1), (x0 - 1, z0 - 1, x1 + 1, z1 + 1, y1 + 1)):
                for x in range(a0 + 1, a1):
                    o.s(x, yy, b0, f"{st}[facing=south,half=bottom,shape=straight,waterlogged=false]")
                    o.s(x, yy, b1, f"{st}[facing=north,half=bottom,shape=straight,waterlogged=false]")
                for z in range(b0 + 1, b1):
                    o.s(a0, yy, z, f"{st}[facing=east,half=bottom,shape=straight,waterlogged=false]")
                    o.s(a1, yy, z, f"{st}[facing=west,half=bottom,shape=straight,waterlogged=false]")
                for x, z, fc, sh in ((a0, b0, "south", "outer_left"), (a1, b0, "south", "outer_right"),
                                     (a0, b1, "north", "outer_right"), (a1, b1, "north", "outer_left")):
                    o.s(x, yy, z, f"{st}[facing={fc},half=bottom,shape={sh},waterlogged=false]")
            for x, z in ((x0 - 2, z0 - 2), (x1 + 2, z0 - 2), (x0 - 2, z1 + 2), (x1 + 2, z1 + 2)):
                o.s(x, y1 + 1, z, f"{slab}[type=bottom,waterlogged=false]")
            o.ring(x0 - 1, z0 - 1, x1 + 1, z1 + 1, y1, full)       # eave support
    o.f(37, 2, 108, 43, 2, 114, "spruce_planks")
    o.f(40, 3, 111, 40, 26, 111, COL)                      # pilar central
    o.door(40, 3, 107, "north")
    o.ladder(40, 3, 7, 112, "south")
    o.ladder(40, 8, 12, 110, "north")
    o.ladder(39, 13, 17, 111, "west")
    o.ladder(41, 18, 22, 111, "east")
    o.roof(38, 109, 42, 113, 27, "verde", ov=2, ceiling=False)
    o.f(40, 32, 111, 40, 33, 111, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    # contents of each storey
    o.s(40, 3, 114, "yellow_glazed_terracotta[facing=north]")
    o.s(40, 4, 114, "candle[candles=4,lit=false,waterlogged=false]")
    o.s(38, 3, 114, "decorated_pot[cracked=false,facing=north,waterlogged=false]", sym=True)
    o.lantern(38, 6, 109, sym=True)
    o.f(37, 8, 114, 38, 9, 114, "bookshelf", sym=True)
    o.lantern(38, 11, 112, sym=True)
    o.s(38, 13, 113, "decorated_pot[cracked=false,facing=north,waterlogged=false]", sym=True)
    o.lantern(41, 16, 113)
    o.s(38, 18, 109, "bookshelf", sym=True)
    o.lantern(39, 21, 113)
    o.chest(39, 23, 110, "south", "pagoda")
    o.s(39, 23, 112, "candle[candles=3,lit=false,waterlogged=false]")
    o.lantern(41, 26, 110)


def pavilions(o):
    """Four concubines' pavilions (two per side), doors towards the axis."""
    for z0 in (86, 106):
        z1, zc = z0 + 10, z0 + 5
        o.plinth(4, z0 - 1, 16, z1 + 1, sym=True)
        o.walls(5, z0, 15, z1, 3, 6, RED, sym=True)
        for (x, z) in ((5, z0), (15, z0), (5, z1), (15, z1), (15, zc - 2), (15, zc + 2)):
            o.f(x, 3, z, x, 6, z, COL, sym=True)
        o.f(6, 2, z0 + 1, 14, 2, z1 - 1, "spruce_planks", sym=True)
        o.f(8, 4, z0, 12, 5, z0, LATTICE, sym=True)
        o.f(8, 4, z1, 12, 5, z1, LATTICE, sym=True)
        o.door(15, 3, zc, "east", sym=True)
        o.stairs_col(17, 2, zc - 1, zc + 1, "west", sym=True)
        o.roof(5, z0, 15, z1, 7, "verde", ov=1, sym=True)
        o.s(6, 3, zc, "pink_bed[facing=west,occupied=false,part=head]", sym=True)
        o.s(7, 3, zc, "pink_bed[facing=west,occupied=false,part=foot]", sym=True)
        o.chest(6, 3, z1 - 1, "east", "pabellon", sym=True)
        o.s(6, 3, z0 + 1, "loom[facing=east]", sym=True)
        o.s(14, 3, z0 + 1, "potted_cherry_sapling", sym=True)
        o.s(14, 3, z1 - 1, "potted_azalea_bush", sym=True)
        o.f(9, 2, zc - 1, 11, 2, zc + 1, "pink_wool", sym=True)
        o.lantern(10, 6, zc, sym=True)
