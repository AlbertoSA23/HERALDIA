"""Mine entrance blueprints: each size (small, medium, large) joins the surface, the mouth, the descent and its
gallery in a single template per style and variant (see construction.py for the coordinates).

  small    descent of 14 to the gallery (3 x 2 junctions, storeroom and vein).
  medium   descent of 16 to a gallery of 5 x 3 junctions (storeroom, vein, dining hall and the spider room, with a
           small spawner).
  large    descent of 20 and the tower shaft (spiral staircase) to a network of 7 x 4 junctions (storeroom, powder magazine,
           dining hall, vein) and, via another ramp of 12, to the deep level (3 x 2): the rich vein room and the spider room
           with its small spawner.
"""
import random
from core import Template, B
from uniques._common import pieces
from . import surface as area
from .construction import Construction, STEP, HEIGHT

# size -> (descent depth, junctions on each side, rows, rooms, courtyard (x, z), air above the courtyard)
SIZES = {
    "pequena": dict(hondo=14, ni=1, nj=2, salas=("filon", "almacen"), patio=(6, 8)),
    "mediana": dict(hondo=16, ni=2, nj=3, salas=("aranas", "filon", "almacen", "comedor"), patio=(11, 16)),
    "grande": dict(hondo=20, ni=3, nj=4, salas=("filon", "almacen", "polvorin", "comedor"), patio=(15, 22),
                   hondo2=12, salas2=("aranas", "tesoro")),
}
WELL = (8, -12)                  # axis of the tower shaft (large), unmirrored


def construct(size, style, variant, pal, name):
    """Complete build; returns the build (with its template in o.t, not normalized)."""
    d = SIZES[size]
    m = 1 if variant == "a" else -1
    rng = random.Random(f"heraldia:minas/{size}/{style}/{variant}")
    o = Construction(Template(name), pal, rng)
    e = area.Mirror(o, m)
    px, pz = d["patio"]
    area.courtyard(o, -px, px, -pz, -1)
    area.mouth(o)
    area.sign(o, -3, -1, size)
    # descent: flat stretch below the mouth, ramp and flat stretch to the first junction
    o.corridor((0, 0), (0, 2), 1, tracks=True, frames=False)
    zf, feet = o.ramp(0, 2, 1, d["hondo"])
    z0 = zf + 5
    o.corridor((0, zf + 1), (0, z0 - 1), feet, tracks=True, frames=False)
    pos, rooms = o.red(0, z0, feet, d["ni"], d["nj"], d["salas"], extra=0.25 if size != "pequena" else 0.15)
    for kind, (cx, cz) in rooms.items():
        furnish(o, kind, cx, cz, feet, size)
    finish = pos[(0, d["nj"] - 1)]
    if size == "pequena":
        small_courtyard(o, e)
    elif size == "mediana":
        medium_courtyard(o, e)
        o.t.entity(0, feet, zf + 3, {"id": "minecraft:minecart"})
    else:
        large_courtyard(o, e)
        well(o, m, feet, z0)
        o.t.entity(0, feet, zf + 3, {"id": "minecraft:minecart"})
        # deep level: the trunk's track continues down another ramp from its last junction
        nx, nz = finish
        zf2, feet2 = o.ramp(nx, nz, feet, d["hondo2"])
        z2 = zf2 + 5
        o.corridor((nx, zf2 + 1), (nx, z2 - 1), feet2, tracks=True, frames=False)
        pos2, rooms2 = o.red(nx, z2, feet2, 1, 2, d["salas2"], extra=0.3)
        for kind, (cx, cz) in rooms2.items():
            furnish(o, kind, cx, cz, feet2, size)
    o.lining()
    o.veins(0.05)
    for kind, x0, x1, z0_, z1, p in o.rooms:
        if kind in ("filon", "tesoro"):
            vein_room(o, x0, x1, z0_, z1, p)
    o.shell()
    return o


# ------------------------------------------------------------------ patios
def small_courtyard(o, e):
    area.tracks(o, -6, -1)
    o.s(0, 1, -7, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(0, 1, -4, {"id": "minecraft:minecart"})
    pieces.chest(e.s, -4, 1, -5, "up", "heraldia:minas/boca", kind="barrel")
    o.chest_list.append(((e.x(-4), 1, -5), "boca"))
    area.heap(e, 3, -7, 3, 3)
    area.post(o, e.x(-4), -7)
    e.s(-3, 1, -7, "grindstone[face=floor,facing=north]")
    o.tracks.append(((0, 1, -6), "south", None))


def medium_courtyard(o, e):
    area.tracks(o, -12, -1)
    o.s(0, 1, -13, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(0, 1, -9, {"id": "minecraft:chest_minecart", "LootTable": "heraldia:minas/vagoneta"})
    o.chest_list.append(((0, 1, -9), "vagoneta"))
    area.shed(e, 4, -14, 9, -8, "west", "capataz")
    area.heap(e, -9, -14, 5, 5)
    area.smelter(e, -9, -7, "fundicion")
    for x, z in ((-3, -12), (3, -12), (-10, -15), (10, -2)):
        area.post(o, e.x(x), z)
    o.tracks.append(((0, 1, -12), "south", None))


def large_courtyard(o, e):
    # main track to the bend, branch toward the tower and the loading dock with its buffer stop
    area.tracks(o, -16, -1)
    area.rail(o.s, o, 0, -17, "south_east" if e.m == 1 else "south_west")
    for x in range(1, 12):
        area.rail(e.s, o, x, -17, "east_west")
    e.s(12, 1, -17, "barrel[facing=north,open=false]", {"id": "minecraft:barrel"})
    o.t.entity(e.x(5), 1, -17, {"id": "minecraft:chest_minecart", "LootTable": "heraldia:minas/vagoneta"})
    o.chest_list.append(((e.x(5), 1, -17), "vagoneta"))
    o.t.entity(0, 1, -8, {"id": "minecraft:minecart"})
    area.tower(e, *WELL)
    area.shed(e, -13, -20, -7, -14, "east", "capataz")
    area.smelter(e, -13, -9, "fundicion")
    area.heap(e, 11, -22 + 1, 4, 3)
    for x, z in ((-3, -14), (3, -14), (-14, -2), (14, -2), (-5, -20), (5, -20)):
        area.post(o, e.x(x), z)
    o.tracks.append(((0, 1, -16), "south", None))


def well(o, m, feet, z0):
    """Vertical tower shaft: 3 x 3 opening around a log pillar with a spiral staircase from the
    courtyard (the last step at y = 0, flush) to the gallery, railing at the curb (except the exit to the north) and,
    below, a tunnel to the junction (m, 0) of the network."""
    cx, cz = m * WELL[0], WELL[1]
    ring = [(cx + dx, cz + dz) for dx, dz in pieces.RING8]
    n = 1 - feet                         # steps from the gallery feet (feet) to y = 0
    for (x, z) in ring:
        for y in range(feet, 1):
            o.cavity(x, y, z)
    for y in range(feet - 1, 1):
        o.s(cx, y, cz, o.trunk("y"))
    pieces.spiral_continuous(o.s, ring, feet, n, f"{o.p['escalon_piedra']}", start=6, under=True)
    for (x, z) in ring:                  # the curb: the steps at the top in the courtyard belong to the build, not the courtyard
        o.surface.discard((x, 0, z))
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if max(abs(dx), abs(dz)) == 2 and (dx, dz) != (0, -2) and abs(dx) + abs(dz) != 4:
                o.s(cx + dx, 1, cz + dz, f"{o.p['madera']}_fence")
    o.descent = (cx, feet, cz)
    # exit to the south through cell (0, 1) of the ring and tunnel to the network
    o.corridor((cx, cz + 2), (cx, z0), feet, frames=True)


# ------------------------------------------------------------------ salas
def furnish(o, kind, cx, cz, feet, size):
    """Room of its type at the junction (cx, cz): furniture in the four slots next to the north and south walls (cx ± 2), which
    never block the arrival of a tunnel (through the center of each side)."""
    o.room(kind, cx, cz, feet)
    cavities = [(cx - 2, cz - 2, "south"), (cx + 2, cz - 2, "south"), (cx - 2, cz + 2, "north"), (cx + 2, cz + 2, "north")]
    tbl = {"tesoro": "filon"}.get(kind, "galeria")
    x, z, f = cavities[0]
    o.place_chest(x, feet, z, f, tbl)
    remainder = cavities[1:]
    if kind == "almacen":
        for x, z, f in remainder:
            o.s(x, feet, z, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
            o.s(x, feet + 1, z, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    elif kind == "comedor":
        x, z, f = remainder[0]
        o.s(x, feet, z, "crafting_table")
        x, z, f = remainder[1]
        o.s(x, feet, z, f"{o.p['madera']}_fence")
        o.s(x, feet + 1, z, f"{o.p['madera']}_pressure_plate[powered=false]")
        x, z, f = remainder[2]
        o.s(x, feet, z, "furnace[facing=north,lit=false]")
    elif kind == "polvorin":
        for x, z, f in remainder:
            o.s(x, feet, z, "tnt[unstable=false]")
        o.s(cx + 2, feet + 1, cz - 2, "tnt[unstable=false]")
    elif kind in ("filon", "tesoro"):
        x, z, f = remainder[0]
        o.s(x, feet, z, "grindstone[face=floor,facing=south]")
        x, z, f = remainder[2]
        o.s(x, feet, z, f"{o.p['madera']}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    elif kind == "aranas":
        o.cobwebs(cx - 3, cx + 3, cz - 2, cz + 2, feet, 6, height=4)
        # small spawner (few spiders, close and slow) on a pedestal next to the south wall
        o.s(cx, feet, cz + 2, o.mat(o.p["muro"], cx, feet, cz))
        pieces.spawner(o.s, cx, feet + 1, cz + 2, "cave_spider", potentials=True, light=11)
        st, nbt = o.t.blocks[(cx, feet + 1, cz + 2)]
        nbt.update({"SpawnCount": 2, "MaxNearbyEntities": 3, "RequiredPlayerRange": 12, "SpawnRange": 3,
                    "MinSpawnDelay": 300, "MaxSpawnDelay": 700, "Delay": 20})
        o.generators.append((cx, feet + 1, cz + 2))


def vein_room(o, x0, x1, z0, z1, feet):
    """Walls of the vein room studded with ore (more than the veins of the tunnels)."""
    from .construction import h
    for x in range(x0 - 1, x1 + 2):
        for z in range(z0 - 1, z1 + 2):
            for y in range(feet, feet + 4):
                st = o.t.get(x, y, z)
                if (x, y, z) in o.carved or st is None or st.split("[")[0].replace("minecraft:", "") not in o.p["muro"]:
                    continue
                if h(x, y, z, 33) < 0.35:
                    o.s(x, y, z, o.mat(o.p["vetas_ricas"], x, y, z, 7))
