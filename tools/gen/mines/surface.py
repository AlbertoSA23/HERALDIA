"""Surface of the mine entrances: courtyard on its foundation, mouth with its timbering and what lies in front depending on the size
(small: mouth with tracks, minecart and lanterns; medium: camp with the foreman's cabin, the pile of ore, the
cargo minecart and the smelter; large: complex with the hoist tower and its pulley over the shaft, tracks and office).

Everything is written with `Mirror`, which mirrors the courtyard in x in variant b (states with an east or west side too),
so the same build comes out with the buildings on one side or the other. The mouth and the tracks in the center (x = 0) do not change."""
from uniques._common import pieces

FLIP = {"east": "west", "west": "east"}


def _flip_state(st):
    if "[" not in st:
        return st
    base, props = st[:-1].split("[", 1)
    out = []
    for kv in props.split(","):
        k, v = kv.split("=")
        if k == "facing":
            v = FLIP.get(v, v)
        elif k == "shape" and ("east" in v or "west" in v) and v != "east_west":
            v = "_".join(FLIP.get(w, w) for w in v.split("_"))
        elif k == "hinge":
            v = {"left": "right", "right": "left"}[v]
        elif k in ("east", "west"):
            k = FLIP[k]
        out.append(f"{k}={v}")
    return f"{base}[{','.join(out)}]"


class Mirror:
    """Writing of the courtyard (everything goes to the build's surface) with a mirror in x if m = -1."""

    def __init__(self, o, m):
        self.o, self.m = o, m

    def s(self, x, y, z, st, nbt=None):
        p = (self.m * x, y, z)
        self.o.s(*p, st if self.m == 1 else _flip_state(st), nbt)
        self.o.surface.add(p)

    def x(self, x):
        return self.m * x

    def face(self, f):
        return f if self.m == 1 else FLIP.get(f, f)


def courtyard(o, x0, x1, z0, z1, air_block=6, foundation=4):
    """Courtyard floor at y = 0 over `foundation` layers of build (on a slope it sticks out like a retaining wall) and explicit
    air above (whatever was in the terrain does not poke through)."""
    p = o.p
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge_block = x in (x0, x1) or z in (z0, z1)
            o.s(x, 0, z, o.mat(p["cimiento"] if edge_block else p["patio"], x, 0, z))
            for y in range(-foundation, 0):
                o.s(x, y, z, o.mat(p["cimiento"], x, y, z, 3))
            for y in range(1, air_block + 1):
                o.s(x, y, z, "air")
            for y in range(-foundation, air_block + 1):
                o.surface.add((x, y, z))


def mouth(o):
    """Mouth facade at z = 0: 7 x 5 built wall with the tunnel opening (3 x 3), log posts and lintel, and
    step finials; the lanterns at the sides on fence posts."""
    p = o.p
    for x in range(-3, 4):
        for y in range(1, 6):
            if abs(x) <= 1 and y <= 3:
                continue
            if abs(x) == 2 and y <= 3:
                st = o.trunk("y")
            elif y == 4:
                st = o.trunk("x")
            else:
                st = o.mat(p["muro"], x, y, 0)
            o.s(x, y, 0, st)
            o.surface.add((x, y, 0))
    for x, f in ((-3, "east"), (3, "west")):
        o.s(x, 5, -1, f"{p['madera']}_stairs[facing={f},half=bottom,shape=straight,waterlogged=false]")
    for x in (-4, 4):
        post(o, x, -1)


def post(o, x, z, height=2):
    """Fence post with a standing lantern on top."""
    for y in range(1, height + 1):
        o.s(x, y, z, f"{o.p['madera']}_fence")
    o.lantern(x, height + 1, z, hanging=False)


def tracks(o, z0, z1, x=0):
    """Straight track from north to south along x from z0 to z1 (inclusive), flush with the courtyard."""
    for z in range(min(z0, z1), max(z0, z1) + 1):
        rail(o.s, o, x, z, "north_south")


def rail(put, o, x, z, shape):
    """Courtyard rail on a solid foundation block (a rail is not supported on a dirt path or a slab:
    at the first update from a neighbor it would pop off)."""
    put(x, 0, z, o.mat(o.p["cimiento"], x, 0, z, 5))
    put(x, 1, z, f"rail[shape={shape},waterlogged=false]")


def heap(e, x0, z0, width, back):
    """Pile of ore in the courtyard: increasingly narrow layers of gravel, stone and ores."""
    o = e.o
    for layer in range(3):
        for x in range(x0 + layer, x0 + width - layer):
            for z in range(z0 + layer, z0 + back - layer):
                corner_block = x in (x0 + layer, x0 + width - layer - 1) and z in (z0 + layer, z0 + back - layer - 1)
                if layer < 2 and corner_block:
                    continue
                e.s(x, 1 + layer, z, o.mat(o.p["mineral"], x, layer, z, 11))


def shed(e, x0, z0, x1, z1, door, tbl, bed=True):
    """Plank cabin with log corners, gable roof (ridge from east to west), door in the wall
    `door` (west or east, in unmirrored coordinates) and inside a bed, a table, a workbench, a lantern and the
    chest `tbl`."""
    o, p = e.o, e.o.p
    for y in range(1, 4):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge_block = x in (x0, x1) or z in (z0, z1)
                corner_block = x in (x0, x1) and z in (z0, z1)
                e.s(x, y, z, o.trunk("y") if corner_block else p["tablas"] if edge_block else "air")
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            e.s(x, 0, z, p["tablas"])
    cz = (z0 + z1) // 2
    px = x0 if door == "west" else x1
    pieces.door(e.s, px, 1, cz, door, kind=f"{p['madera']}_door")
    e.s(px + (-1 if door == "west" else 1), 0, cz, p["tablas"])
    for x in ((x0 + x1) // 2,):
        e.s(x, 2, z0, "glass_pane[north=false,south=false,east=true,west=true,waterlogged=false]")
        e.s(x, 2, z1, "glass_pane[north=false,south=false,east=true,west=true,waterlogged=false]")
    other_one = x1 - 1 if door == "west" else x0 + 1
    if bed:
        e.s(other_one, 1, z0 + 1, f"{p['cama']}_bed[facing=north,occupied=false,part=head]")
        e.s(other_one, 1, z0 + 2, f"{p['cama']}_bed[facing=north,occupied=false,part=foot]")
    e.s(other_one, 1, z1 - 1, "crafting_table")
    side = "east" if door == "west" else "west"
    cx = (x0 + x1) // 2
    pieces.chest(e.s, cx, 1, z0 + 1, "south", f"heraldia:minas/{tbl}")
    o.chest_list.append(((e.x(cx), 1, z0 + 1), tbl))
    e.s(cx, 1, z1 - 1, f"{p['madera']}_fence")
    e.s(cx, 2, z1 - 1, f"{p['madera']}_pressure_plate[powered=false]")
    e.s(cx + (1 if side == "east" else -1), 1, z1 - 1, f"{p['madera']}_stairs[facing={side},half=bottom,shape=straight,waterlogged=false]")
    e.s(cx, 3, cz, "lantern[hanging=true,waterlogged=false]")
    # gable roof along x, with one block of overhang
    za, zb, y = z0 - 1, z1 + 1, 4
    while za <= zb:
        for x in range(x0 - 1, x1 + 2):
            if za == zb:
                e.s(x, y, za, f"{p['madera']}_slab[type=bottom,waterlogged=false]")
            else:
                e.s(x, y, za, f"{p['madera']}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
                e.s(x, y, zb, f"{p['madera']}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
        for x in (x0, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                e.s(x, y, z, p["tablas"])
        for x in range(x0 + 1, x1):
            for z in range(max(za + 1, z0), min(zb - 1, z1) + 1):
                e.s(x, y, z, "air")
        za, zb, y = za + 1, zb - 1, y + 1


def smelter(e, x0, z0, tbl):
    """Small smelter: brick bench with the blast furnace and the furnace, chimney with its smoking campfire, anvil, a
    cauldron and the barrel with what was smelted."""
    o = e.o
    for x in (x0, x0 + 1):
        for z in range(z0, z0 + 4):
            for y in (1, 2):
                e.s(x, y, z, "bricks")
    e.s(x0 + 1, 1, z0 + 1, "blast_furnace[facing=east,lit=false]")
    e.s(x0 + 1, 1, z0 + 2, "furnace[facing=east,lit=false]")
    for y in range(3, 6):
        e.s(x0, y, z0 + 1, "bricks")
    e.s(x0, 6, z0 + 1, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    e.s(x0 + 3, 1, z0, "anvil[facing=north]")
    e.s(x0 + 3, 1, z0 + 3, "cauldron")
    pieces.chest(e.s, x0 + 2, 1, z0 + 3, "up", f"heraldia:minas/{tbl}", kind="barrel")
    o.chest_list.append(((e.x(x0 + 2), 1, z0 + 3), tbl))


def sign(o, x, z, size):
    """Mine sign on the facade (against the mouth wall, facing the courtyard)."""
    pieces.sign(o.s, x, 2, z, "north", [pieces.text(f"heraldia.minas.cartel.{size}.{i}", fb)
                                       for i, fb in ((1, SIGNS[size][0][0]), (2, SIGNS[size][1][0]))], wood=o.p["madera"])


SIGNS = {"pequena": (("Boca de mina", "Mine adit"), ("Ojo con el grisú", "Mind the firedamp")),
            "mediana": (("Poblado minero", "Mining camp"), ("Solo personal", "Staff only")),
            "grande": (("Minas reales", "Royal mines"), ("Pozo y galerías", "Shaft & galleries"))}


def tower(e, cx, cz, height=14):
    """Log hoist tower over the shaft (5 x 5 with the axis at cx, cz): four legs, two rings of beams,
    the frame at the top, the axle beam and the pulley (a vertical log wheel with its fence spokes) and the chain
    that goes down the shaft."""
    o, p = e.o, e.o.p
    xs, zs = (cx - 2, cx + 2), (cz - 2, cz + 2)
    for x in xs:
        for z in zs:
            for y in range(1, height + 1):
                e.s(x, y, z, o.trunk("y"))
    for y in (6, 11, height + 1):
        for x in range(cx - 2, cx + 3):
            for z in zs:
                e.s(x, y, z, o.trunk("x"))
        for z in range(cz - 1, cz + 2):
            for x in xs:
                e.s(x, y, z, o.trunk("z"))
    for x in range(cx - 1, cx + 2):
        e.s(x, height + 1, cz, o.trunk("x"))
    hub = height + 4
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            r2 = dx * dx + dy * dy
            if 4 <= r2 <= 6:
                e.s(cx + dx, hub + dy, cz, o.trunk("z"))
            elif r2 in (1, 2) and (dx == 0 or dy == 0):
                e.s(cx + dx, hub + dy, cz, f"{p['madera']}_fence")
    e.s(cx, hub, cz, o.trunk("z"))
    for y in range(hub - 3 + 1, height + 1):      # wheel support on the axle beam
        e.s(cx, y, cz, o.trunk("y"))
    for y in range(2, height + 1):
        e.s(cx + 1, y, cz, "iron_chain[axis=y,waterlogged=false]")
