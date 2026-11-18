"""Pieces of the unique structures of the Nether and the End (T44: Ash Citadel and Sanctum of the Void): the keep with the entrance
trap, the guardian's hall, the treasure chamber behind an iron door with buttons and the upper floor with the
library; the corner towers (or chapels) and the hidden room behind a piston door with a lever. Each unique
structure supplies the outside (walls and courtyard, or the platform and its pillars) and its palette. It is not a unique structure (it starts with "_":
uniques.modules() does not discover it).

Template coordinates: y = 0 is the floor; everything at x, z >= 0 (Registry.add shifts nothing, so the positions
of the open door, lint_open, remain valid)."""
from uniques._common import pieces

SIDE = 15          # keep of 15 x 15
HEIGHT = 11          # top of the keep's battlements (floor at 0, slab at 5, roof at 10)


def _put(t):
    return lambda x, y, z, st, nbt=None: t.set(x, y, z, st, nbt)


def box(t, x0, y0, z0, x1, y1, z1, wall, corner_block=None):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge_block = x in (x0, x1) or z in (z0, z1)
                if edge_block:
                    t.set(x, y, z, corner_block if corner_block and x in (x0, x1) and z in (z0, z1) else wall)
                else:
                    t.set(x, y, z, "air")


def battlements(t, x0, z0, x1, z1, y, merlon):
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x in (x0, x1) or z in (z0, z1)) and (x + z) % 2 == 0:
                t.set(x, y, z, merlon)


def lantern(t, x, y, z, hanging=True):
    t.set(x, y, z, f"soul_lantern[hanging={'true' if hanging else 'false'},waterlogged=false]")


def great_tower(t, p, kx, kz, place_chest, guardian):
    """Keep of 15 x 15 with its NW corner at (kx, kz): front at the north (3 wide), corridor with the plate trap and
    arrows, guardian's hall, partition with the iron door (buttons on both sides) and the treasure chamber with the
    premium chest to the south; ladder to the upper floor (library and barracks). `cofre(t, x, y, z, facing, tabla,
    kind)` places a container of the unique structure; `guardian` is the NBT of its guardian."""
    put = _put(t)
    x1, z1 = kx + SIDE - 1, kz + SIDE - 1
    cx = kx + 7
    t.fill(kx, 0, kz, x1, 0, z1, p["piso"])
    box(t, kx, 1, kz, x1, 9, z1, p["muro"], p["esquina"])
    t.fill(kx + 1, 5, kz + 1, x1 - 1, 5, z1 - 1, p["forjado"])
    t.fill(kx, 10, kz, x1, 10, z1, p["forjado"])
    battlements(t, kx, kz, x1, z1, HEIGHT, p["almena"])
    for x in (kx, x1):
        for z in (kz, z1):
            lantern(t, x, HEIGHT + 1, z, hanging=False) if (x + z) % 2 == 0 else None
    # portada
    for x in range(cx - 1, cx + 2):
        for y in (1, 2, 3):
            t.set(x, y, kz, "air")
    # corridor with the trap (dispensers on the sides of the plate) and the guard rooms on the sides
    for z in range(kz + 1, kz + 5):
        for y in range(1, 5):
            t.set(cx - 2, y, z, p["muro"])
            t.set(cx + 2, y, z, p["muro"])
    pieces.plate_trap(put, [(cx, 1, kz + 3)], "east", plate="polished_blackstone_pressure_plate")
    for x in range(kx + 1, x1):
        if not cx - 1 <= x <= cx + 1:
            for y in range(1, 5):
                t.set(x, y, kz + 5, p["muro"])
    for x in (kx + 3, x1 - 3):
        pieces.door(put, x, 1, kz + 5, "north", p["puerta"])
    place_chest(t, kx + 1, 1, kz + 1, "south", "cuartel", "barrel")
    place_chest(t, x1 - 1, 1, kz + 1, "south", "cuartel", "chest")
    lantern(t, kx + 3, 4, kz + 2)
    lantern(t, x1 - 3, 4, kz + 2)
    # guardian's hall
    t.entity(cx, 1, kz + 8, guardian)
    for x in (kx + 3, x1 - 3):
        t.set(x, 1, kz + 8, p["columna"])
        for y in (2, 3, 4):
            t.set(x, y, kz + 8, p["columna"])
        lantern(t, x, 4, kz + 7)
    # partition, iron door with buttons and treasure chamber
    for x in range(kx + 1, x1):
        for y in range(1, 5):
            t.set(x, y, kz + 11, p["muro"])
    pieces.door(put, cx, 1, kz + 11, "south", "iron_door")
    t.set(cx - 1, 2, kz + 10, "stone_button[face=wall,facing=north,powered=false]")
    t.set(cx - 1, 2, kz + 12, "stone_button[face=wall,facing=south,powered=false]")
    place_chest(t, cx, 1, z1 - 1, "north", "premium", "chest")
    for x in (cx - 2, cx + 2):
        t.set(x, 1, z1 - 1, p["tesoro"])
    lantern(t, cx, 4, kz + 12)
    # ladder to the upper floor, against the west wall of the hall
    for y in range(1, 6):
        t.set(kx + 1, y, kz + 8, "ladder[facing=east,waterlogged=false]")
    # upper floor: library to the south (bookshelves and the chest), barracks to the north; arrow slits
    for x in range(kx + 1, x1):
        if x not in (cx,):
            t.set(x, 6, z1 - 1, "bookshelf")
            t.set(x, 7, z1 - 1, "bookshelf")
    place_chest(t, cx, 6, z1 - 1, "north", "biblioteca", "chest")
    t.set(x1 - 1, 6, kz + 8, "lectern[facing=west,has_book=false,powered=false]")
    place_chest(t, x1 - 1, 6, kz + 1, "south", "cuartel", "barrel")
    for x in range(kx + 3, x1 - 2, 4):
        lantern(t, x, 9, kz + 4)
        lantern(t, x, 9, z1 - 4)
    for z in range(kz + 3, z1 - 1, 4):
        t.set(kx, 7, z, "iron_bars")
        t.set(x1, 7, z, "iron_bars")
    return {"centro": (cx, kz + 8)}


def tower(t, p, x0, z0, height, door, merlon=True):
    """Tower (or chapel) of 5 x 5 with its NW corner at (x0, z0): walls up to `height`, roof and battlements; `door` (x, z,
    facing) in one of its walls; arrow slits made of bars."""
    put = _put(t)
    x1, z1 = x0 + 4, z0 + 4
    t.fill(x0, 0, z0, x1, 0, z1, p["piso"])
    box(t, x0, 1, z0, x1, height, z1, p["muro"], p["esquina"])
    t.fill(x0, height + 1, z0, x1, height + 1, z1, p["forjado"])
    if merlon:
        battlements(t, x0, z0, x1, z1, height + 2, p["almena"])
    for x, z in ((x0 + 2, z0), (x0 + 2, z1), (x0, z0 + 2), (x1, z0 + 2)):
        if (x, z) != (door[0], door[1]):
            t.set(x, 3, z, "iron_bars")
    lantern(t, x0 + 2, height, z0 + 2)
    if door[2]:
        pieces.door(put, door[0], 1, door[1], door[2], p["puerta"])


def hidden(t, p, x0, z0):
    """Tower of 5 x 5 (NW at (x0, z0)) with no visible door: it is entered through its west wall by a piston door that
    the lever of the outer buttress opens (pieces.lever_door). Returns the state with the door open."""
    tower(t, p, x0, z0, 7, (x0, z0 + 2, None))
    # buttress north of the NW corner (outside), where the torch and the lever go
    for y in (1, 2, 3):
        t.set(x0, y, z0 - 1, p["muro"])
        t.set(x0 - 1, y, z0 - 1, p["muro"])
    rec = pieces.lever_door(_put(t), (x0, 1, z0 + 2), "north", "west", p["muro"], p["muro"])
    return rec["opened"]
