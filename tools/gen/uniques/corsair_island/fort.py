"""The corsair's fort on the hill plateau: wall with a wall walk, bastion with cannons facing north,
the corsair's house, the barracks, the cistern, the flagpole and the tower of the descent to the caves."""
from .construction import S, slab, stairs, h, FORT, PLAT, SB, COB, PL, LOG, DV
from .._common import pieces

Y = PLAT + 1                 # feet in the courtyard
TOP = Y + 4                  # top of the rampart (block); feet of the wall walk at TOP + 1
GATE = (71, 72)              # gate of the south wall (x)
BASTION = [(66, 24), (64, 19), (72, 13), (80, 19), (78, 24)]   # bastion polygon (x, z)


def inside(poly, x, z):
    """Point in polygon (even-odd) over the cell centers."""
    px, pz, c = x + 0.5, z + 0.5, False
    n = len(poly)
    for i in range(n):
        (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % n]
        if (z1 > pz) != (z2 > pz) and px < x1 + (pz - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def construct(o):
    x0, x1, z0, z1 = FORT
    courtyard(o, x0, x1, z0, z1)
    city_wall(o, x0, x1, z0, z1)
    bulwark(o)
    house(o)
    barracks(o)
    cistern(o, 74, 39)
    flag(o, 66, 41)
    o.mech["bajada"] = descent(o)


def courtyard(o, x0, x1, z0, z1):
    """Cobbled courtyard (gravel and stone) at the plateau height; nothing fertile where vegetation could grow."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            o.s(x, PLAT, z, "gravel" if h(x, z, 11) < 0.55 else ("cobblestone" if h(x, z, 12) < 0.6 else "andesite"))
            o.s(x, PLAT - 1, z, "stone")
            o.a(x, Y, z, x, Y + 8, z)


def city_wall(o, x0, x1, z0, z1):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            outer = x in (x0, x1) or z in (z0, z1)
            inner = not outer and (x in (x0 + 1, x1 - 1) or z in (z0 + 1, z1 - 1))
            if outer:
                o.f(x, PLAT, z, x, TOP + 1, z, SB)
                o.s(x, PLAT, z, COB)
                corner = x in (x0, x1) and z in (z0, z1)
                if corner or (x + z) % 2 == 0:
                    if not corner and h(x, z, 41) < 0.22:
                        o.ruin.add((x, TOP + 2, z))           # fallen merlon
                    else:
                        o.s(x, TOP + 2, z, SB)                 # almenas
            elif inner:
                o.f(x, PLAT, z, x, TOP, z, SB)
    # gate: two-wide arch in the south wall, double spruce door
    for x in GATE:
        o.a(x, Y, z1 - 1, x, Y + 2, z1)
    pieces.double_door(o.s, GATE[0], Y, z1, "south", "east", kind="spruce_door")
    o.s(GATE[0] - 1, Y + 2, z1 + 1, S("wall_torch", facing="south"))
    o.s(GATE[1] + 1, Y + 2, z1 + 1, S("wall_torch", facing="south"))
    o.sign(GATE[1] + 1, Y + 1, z1 + 1, "south", "fuerte", [("Fuerte de", "Fort of"), ("Roque Salitre", "Roque Salitre"),
                                                             ("No se admiten", "No flags but"), ("otras banderas", "the black one")])
    # stairs up to the wall walk (west and east), 5 steps heading north against the wall
    for x in (x0 + 2, x1 - 2):
        o.flight(x, z1 - 4, Y, "north", 5, mat="stone_brick", support=SB)
    # passage from the wall walk to the bastion (no merlon on the north wall)
    for x in (71, 72, 73):
        o.a(x, TOP + 1, z0, x, TOP + 3, z0)


def bulwark(o):
    """Five-sided bastion to the north, solid up to the platform (at wall-walk height) and with a parapet,
    four cannons on its faces and a powder store."""
    cells = [(x, z) for x in range(60, 86) for z in range(10, FORT[2]) if inside(BASTION, x, z)]
    cs = set(cells)
    for (x, z) in cells:
        g = o.ground.get((x, z))
        y0 = g if g is not None else -1
        for y in range(min(y0, PLAT), TOP + 1):
            o.s(x, y, z, SB if y > PLAT else COB)
        edge_block = any((x + a, z + b) not in cs and z + b < FORT[2] for a in (-1, 0, 1) for b in (-1, 0, 1))
        if edge_block:
            o.s(x, TOP + 1, z, SB)
            if (x + z) % 2 == 0:
                o.s(x, TOP + 2, z, SB)
        else:
            o.a(x, TOP + 1, z, x, TOP + 4, z)
    # cannons: dispensers (decorative, empty) on the parapet, facing outward, with trapdoor wheels
    o.mech["canones"] = []
    for (x, z, f) in ((68, 17, "north"), (76, 17, "north"), (66, 20, "west"), (78, 20, "east")):
        dx, dz = DV[f]
        bx, bz = x + dx, z + dz       # parapet cell where the muzzle goes
        if (bx, bz) not in cs:
            bx, bz = x, z
        o.s(bx, TOP + 1, bz, S("dispenser", facing=f, triggered=False), {"id": "minecraft:dispenser"})
        o.a(bx, TOP + 2, bz, bx, TOP + 2, bz)
        o.mech["canones"].append((bx, TOP + 1, bz))
    o.s(72, TOP + 1, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.chest(71, TOP + 1, 21, "south", "polvorin")
    o.s(73, TOP + 1, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})


def house(o):
    """The corsair's house (against the north wall, to the west): ground floor with the captains' table and the fireplace,
    and upstairs the corsair's bedroom. Spruce walls with posts, stone base and gable roof."""
    x0, x1, z0, z1 = 62, 70, 26, 33
    yt = Y + 4                  # floor slab (feet above at yt + 1)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            o.s(x, PLAT, z, COB if edge else PL)
            for y in range(Y, yt + 5):
                if edge:
                    o.s(x, y, z, LOG if corner else (COB if y == Y else PL))
                else:
                    o.s(x, y, z, "air")
            if not edge:
                o.s(x, yt, z, PL)
    # gable roof along x (ridge at z = 29.5)
    for i in range(5):
        for x in range(x0 - 1, x1 + 2):
            o.s(x, yt + 4 + i, z0 - 1 + i, stairs("dark_oak", "south"))
            o.s(x, yt + 4 + i, z1 + 1 - i, stairs("dark_oak", "north"))
            if 0 < i:
                for z in range(z0 - 1 + i + 1, z1 + 1 - i):
                    if x in (x0, x1):
                        o.s(x, yt + 4 + i, z, PL)       # hastiales
    # ventanas
    for z in (28, 31):
        for y in (Y + 1, yt + 2):
            o.s(x0, y, z, S("glass_pane"))
            o.s(x1, y, z, S("glass_pane"))
    for x in (64, 68):
        o.s(x, yt + 2, z1, S("glass_pane"))
    o.door(66, Y, z1, "south")
    # ground floor: long table with chairs, fireplace to the east and the cartography table
    for x in range(64, 68):
        o.table(x, Y, 30)
        o.chair(x, Y, 29, "north")
        o.chair(x, Y, 31, "south")
    o.s(69, Y, 30, "campfire[facing=west,lit=true,signal_fire=false,waterlogged=false]")
    o.f(69, Y + 1, 30, 69, yt + 6, 30, "bricks")
    o.s(69, Y, 28, "cartography_table")
    o.chest(69, Y, 32, "west", "casa")
    o.hang(66, yt - 1, 30)
    # staircase to the upper floor against the north wall: rises east from the northwest corner (feet 8 to feet 13)
    o.flight(64, 27, Y, "east", 5, mat="spruce", support=PL)
    for x in range(64, 68):
        o.a(x, yt, 27, x, yt, 27)
        o.s(x, yt + 1, 28, "spruce_fence")
    # upper floor: the corsair's bedroom
    yy = yt + 1
    o.s(63, yy, 31, S("black_bed", facing="south", part="foot", occupied=False))
    o.s(63, yy, 32, S("black_bed", facing="south", part="head", occupied=False))
    o.chest(64, yy, 32, "north", "corsario")
    o.s(68, yy, 32, "lectern[facing=north,has_book=false,powered=false]")
    o.s(66, yy, 32, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.banner(66, yy + 2, 32, "north", "black")
    o.hang(65, yy + 3, 30)


def barracks(o):
    """Crew barracks (east of the courtyard): bunks, armorer and the game table."""
    x0, x1, z0, z1 = 75, 82, 26, 32
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            o.s(x, PLAT, z, COB if edge else PL)
            for y in range(Y, Y + 4):
                o.s(x, y, z, (LOG if x in (x0, x1) and z in (z0, z1) else (COB if y == Y else PL)) if edge else "air")
            o.s(x, Y + 4, z, slab("spruce") if edge else PL)
    o.door(78, Y, z1, "south")
    for x in (76, 80):
        o.s(x, Y + 1, z1, S("glass_pane"))
    for z in (28, 30):
        o.s(x1, Y + 1, z, S("glass_pane"))
    for x in (76, 78, 80):
        o.bed(x, Y, 28, "north", "brown")
    o.chest(81, Y, 27, "west", "cuartel")
    o.s(76, Y, 31, "crafting_table")
    o.hang(78, Y + 3, 29)


def cistern(o, x, z):
    """Courtyard cistern: stone curb, water and a small roof on posts."""
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            o.s(x + a, PLAT, z + b, SB)
            if a or b:
                o.s(x + a, Y, z + b, SB)
    o.s(x, PLAT, z, "water")
    o.s(x, PLAT - 1, z, SB)
    for (a, b) in ((-1, -1), (1, 1)):
        o.f(x + a, Y + 1, z + b, x + a, Y + 2, z + b, "spruce_fence")
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            o.s(x + a, Y + 3, z + b, slab("spruce"))
    o.s(x, Y + 2, z, S("iron_chain", axis="y"))
    o.s(x, Y + 1, z, S("lantern", hanging=True, waterlogged=False))


def flag(o, x, z):
    o.s(x, PLAT, z, SB)
    o.f(x, Y, z, x, Y + 7, z, "spruce_fence")
    o.s(x + 1, Y + 6, z, "black_wool")
    o.s(x + 2, Y + 6, z, "black_wool")
    o.s(x + 1, Y + 5, z, "black_wool")
    o.s(x + 2, Y + 5, z, "white_wool")


def descent(o):
    """Tower of the descent to the caves (southeast corner of the courtyard): a straight staircase that goes down to the guardroom."""
    x0, x1, z0, z1 = 77, 82, 37, 43
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            for y in range(Y, Y + 4):
                o.s(x, y, z, SB if edge else "air")
            o.s(x, Y + 4, z, SB)
            if edge:
                o.s(x, Y + 5, z, SB if (x + z) % 2 == 0 else "air")
    o.door(79, Y, z0, "north")
    o.hang(79, Y + 3, 40)
    # staircase going down to the south from the courtyard (feet 8) to the caves (feet 1): 7 steps at x = 80
    return dict(x=80, z_top=38)
