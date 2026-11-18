"""The Herald's House ("La Casa del Heraldo"): the world-spawn town (template, blueprint for the Java side, texts).

Like the wave arena (arena_waves.py) it is not a world-generation structure: the mod places it once per world, at the
spawn of a new world (casa_heraldo.generar_en_mundos_nuevos) or where an operator confirms it in a world that already
exists (/heraldia herald place), with this template (heraldia:casa_heraldo/casa). A 96 x 96 walled town:
  - an outer wall with four corner towers and a gate in the middle of each side; the roads cross at the plaza and
    leave through the gates (the Java side carries them on through the protection ring, with a signpost at the end);
  - the plaza: the bell (the villagers' meeting point) under a stone frame, the well and the job board of the villages
    (board.piece: the lectern with its book and the bailiff who pays for deliveries, reused as it is);
  - the inn and the guest house (the beds, reached on the flat), the chapel, the stable, two gardens and a farm, and six
    shops, each with the workstation of the villager who lives in it (beds within 48 blocks of every workstation:
    see LESSONS, villager POIs);
  - the market: eight empty stalls players can rent (market.*, off by default) and the market office with the return
    barrels, where whatever was in a reclaimed stall is kept for its tenant;
  - the Nether portal: an obsidian frame, built and not lit, under a pavilion (only an operator can light it).
Only materials that do not burn for the buildings (stone, brick, crimson wood: fire from lightning does not spread);
the gardens and the farm are plants. heraldia/casa_heraldo.json tells the Java side where everything is (positions
relative to the template's minimum corner); errors() checks that the template keeps those promises (generation fails
otherwise). The dock (heraldia:casa_heraldo/muelle) is a second template, placed by the Java side only if there is water
in front of a gate.
"""
from core import Template, NS, B, F, villager
import board
from themes import THEMES
from uniques._common import pieces

TEMPLATE = "casa_heraldo/casa"
DOCK = "casa_heraldo/muelle"
VERSION = 1
N = 96                     # side of the (square) template
C = N // 2                 # center column (48)
FLOOR = 4                  # y of the ground layer: it goes at terrain height (y 0-3 is the foundation)
HEIGHT = FLOOR + 17        # y = 0 .. 20 (the office roof)
WALL_TOP = FLOOR + 5
ROAD = (C - 2, C + 2)      # the two roads are 5 wide (46..50)
PLAZA = (38, 58)
TOWER = 7
THEME = next(th for th in THEMES if th["id"] == "llanuras_castellana")
STYLE, FAMILY = THEME["id"], THEME["family"]   # how the villagers' conversations see the town (dialogue/Dialogue)
DOCK_SIZE = (5, 16)        # width (x) and length (z, out over the water) of the dock

# materials (none burns: crimson and warped wood are fireproof)
WALL, TRIM, PAVE, PAVE2 = "stone_bricks", "polished_andesite", "stone_bricks", "polished_andesite"
FLOORING, ROOF, ROOF_FULL = "crimson_planks", "brick_stairs", "bricks"
DOOR, FENCE, GATE, WOOD_SLAB = "crimson_door", "crimson_fence", "crimson_fence_gate", "crimson_slab"
LANTERN = "lantern[hanging=true]"

BELL = (C, FLOOR + 3, C)                   # hanging from the frame's beam
SPAWN = (C, FLOOR + 1, C + 4)              # plaza, south of the bell: the world spawn and where players are moved to
GATES = {"north": (C, 0), "south": (C, N - 1), "west": (0, C), "east": (N - 1, C)}
PORTAL = ((80, FLOOR + 1, 84), (83, FLOOR + 5, 84))   # obsidian frame (min, max corner): 4 wide, 5 tall
BOARD = (42, FLOOR + 1, 41)                # the job board's lectern (the bailiff behind it, at z + 1)
WELL = (52, 56, 52, 56)                    # x0, x1, z0, z1
STALL_W = 5
STALL_X = (6, 12, 18, 24)                  # west x of each stall in a row
STALL_ROWS = ((64, "south"), (76, "north"))  # (north z of the row, side the counter faces)
RETURNS = 12                               # return barrels in the office


def _buildings():
    """(name, x0, z0, x1, z1, door side, door coordinate along the wall, extra) of each building."""
    return [
        ("posada", 24, 26, 42, 36, "south", 33, None),
        ("hostal", 54, 26, 70, 36, "south", 62, None),
        ("capilla", 60, 8, 74, 22, "south", 67, None),
        ("herreria", 24, 38, 34, 44, "east", 41, ["blast_furnace", "smithing_table", "grindstone"]),
        ("carniceria", 24, 52, 34, 58, "east", 55, ["smoker", "cauldron"]),
        ("biblioteca", 62, 38, 72, 44, "west", 41, ["lectern"]),
        ("cartografo", 62, 52, 72, 58, "west", 55, ["cartography_table"]),
        ("taller", 54, 64, 64, 72, "west", 68, ["fletching_table", "stonecutter"]),
        ("oficina", 34, 82, 44, 92, "north", 39, None),
    ]


PROFESSION = {"blast_furnace": "armorer", "smithing_table": "toolsmith", "grindstone": "weaponsmith",
              "smoker": "butcher", "cauldron": "leatherworker", "lectern": "librarian",
              "cartography_table": "cartographer", "fletching_table": "fletcher", "stonecutter": "mason",
              "brewing_stand": "cleric", "composter": "farmer"}


def text(key):
    return pieces.text(f"{NS}.casa_heraldo.{key}", TEXTS[key][0])


def stairs(facing, mat=ROOF, half="bottom"):
    return f"{mat}[facing={facing},half={half},shape=straight]"


# ------------------------------------------------------------------ pieces
def gable(t, x0, z0, x1, z1, ytop):
    """Brick gable roof with the ridge along x over walls x0..x1, z0..z1 that end at ytop; gable ends filled."""
    k = 0
    while True:
        za, zb, y = z0 - 1 + k, z1 + 1 - k, ytop + 1 + k
        if za > zb:
            break
        for x in range(x0 - 1, x1 + 2):
            if za == zb:
                t.set(x, y, za, ROOF_FULL)
            else:
                t.set(x, y, za, stairs("south"))
                t.set(x, y, zb, stairs("north"))
        if za < zb - 1:
            for z in range(za + 1, zb):
                for x in (x0, x1):
                    t.set(x, y, z, WALL)
        k += 1


def building(t, name, x0, z0, x1, z1, side, along, stations):
    """Walls, floor, flat ceiling, gable roof, windows, door with its sign, light; returns the door's outer cell."""
    top = FLOOR + 5
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            t.set(x, FLOOR, z, TRIM if edge else FLOORING)
            for y in range(FLOOR + 1, top):
                t.set(x, y, z, ("polished_deepslate" if corner else WALL) if edge else "air")
            t.set(x, top, z, WALL)
    gable(t, x0, z0, x1, z1, top)
    # windows every 3 blocks on the long walls, away from the corners and the door
    for x in range(x0 + 2, x1 - 1, 3):
        for z in (z0, z1):
            if not (side in ("north", "south") and abs(x - along) <= 1):
                t.set(x, FLOOR + 2, z, "glass_pane")
                t.set(x, FLOOR + 3, z, "glass_pane")
    for z in range(z0 + 2, z1 - 1, 3):
        for x in (x0, x1):
            if not (side in ("east", "west") and abs(z - along) <= 1):
                t.set(x, FLOOR + 2, z, "glass_pane")
    # door (facing outwards) and the name sign above it, outside
    dx, dz = pieces.DIRV[side]
    door_x, door_z = {"north": (along, z0), "south": (along, z1), "west": (x0, along), "east": (x1, along)}[side]
    t.set(door_x, FLOOR, door_z, TRIM)
    t.set(door_x, FLOOR + 1, door_z, f"{DOOR}[facing={side},half=lower,hinge=left,open=false]")
    t.set(door_x, FLOOR + 2, door_z, f"{DOOR}[facing={side},half=upper,hinge=left,open=false]")
    pieces.sign(t.set, door_x + dx, FLOOR + 3, door_z + dz, side, [text(f"edificio.{name}")], wood="crimson")
    # light: lanterns hanging from the ceiling, one every 6 blocks
    for x in range(x0 + 3, x1 - 1, 6):
        for z in range(z0 + 3, z1 - 1, 5):
            t.set(x, top - 1, z, LANTERN)
    # workstations against the wall opposite the door, spread out
    cells = []
    if stations:
        inner = [(x, z1 - 1) for x in range(x0 + 2, x1 - 1, 2)] if side != "south" else \
            [(x, z0 + 1) for x in range(x0 + 2, x1 - 1, 2)]
        if side in ("east", "west"):
            wx = x0 + 1 if side == "east" else x1 - 1
            inner = [(wx, z) for z in range(z0 + 1, z1, 2)]
        for st, (x, z) in zip(stations, inner):
            state = {"blast_furnace": "blast_furnace[facing=" + side + ",lit=false]",
                     "smoker": "smoker[facing=" + side + ",lit=false]",
                     "grindstone": "grindstone[face=floor,facing=" + side + "]",
                     "lectern": "lectern[facing=" + side + ",has_book=false,powered=false]",
                     "stonecutter": "stonecutter[facing=" + side + "]"}.get(st, st)
            t.set(x, FLOOR + 1, z, state)
            cells.append((st, x, z))
    return (door_x + dx, door_z + dz), cells


def inn_beds(t, x0, z0, x1, z1, per_side):
    """Beds along the north wall (heads against it) with a lantern-free aisle; returns the bed foot cells."""
    feet = []
    for i in range(per_side):
        x = x0 + 2 + 2 * i
        if x >= x1 - 1:
            break
        t.set(x, FLOOR + 1, z0 + 1, "red_bed[facing=north,part=head,occupied=false]")
        t.set(x, FLOOR + 1, z0 + 2, "red_bed[facing=north,part=foot,occupied=false]")
        feet.append((x, z0 + 3))
    return feet


def stall(t, x0, zn, faces, number):
    """A 5 x 5 market stall: floor, four posts, a slab roof, the counter on the open side and a sign with its number.
    Returns (editable box, sign position): the 3 x 3 x 3 inside behind the counter is what the tenant may use."""
    z_counter = zn if faces == "north" else zn + STALL_W - 1
    z_back = zn + STALL_W - 1 if faces == "north" else zn
    for x in range(x0, x0 + STALL_W):
        for z in range(zn, zn + STALL_W):
            t.set(x, FLOOR, z, TRIM if x in (x0, x0 + STALL_W - 1) or z in (zn, zn + STALL_W - 1) else "smooth_stone")
            for y in range(FLOOR + 1, FLOOR + 4):
                t.set(x, y, z, "air")
            t.set(x, FLOOR + 4, z, f"{WOOD_SLAB}[type=bottom]")
    for x in (x0, x0 + STALL_W - 1):
        for z in (zn, zn + STALL_W - 1):
            t.fill(x, FLOOR + 1, z, x, FLOOR + 3, z, FENCE)
    for x in range(x0 + 1, x0 + STALL_W - 1):
        t.set(x, FLOOR + 1, z_counter, f"{WOOD_SLAB}[type=top]")
        t.set(x, FLOOR + 1, z_back, WALL)
        t.set(x, FLOOR + 2, z_back, WALL)
    # sign on the counter, facing the lane (standing sign: rotation 8 = north, 0 = south)
    sx, sz = x0 + 1, z_counter
    t.set(sx, FLOOR + 2, sz, f"crimson_sign[rotation={8 if faces == 'north' else 0}]",
          {"id": "minecraft:sign", "is_waxed": B(1),
           "front_text": {"messages": [text("puesto"), {"text": f"#{number}"}, text("se_alquila"), {"text": ""}],
                          "color": "black", "has_glowing_text": B(0)},
           "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})
    zi0, zi1 = (zn + 1, zn + 3)
    box = [[x0 + 1, FLOOR + 1, zi0], [x0 + 3, FLOOR + 3, zi1]]
    return box, [sx, FLOOR + 2, sz]


def portal(t):
    (ax, ay, az), (bx, by, bz) = PORTAL
    for x in range(ax, bx + 1):
        for y in range(ay, by + 1):
            edge = x in (ax, bx) or y in (ay, by)
            t.set(x, y, az, "obsidian" if edge else "air")
    # pavilion: a platform, four pillars and a flat roof, open on every side
    for x in range(ax - 4, bx + 5):
        for z in range(az - 4, az + 5):
            t.set(x, FLOOR, z, "polished_blackstone_bricks" if (x + z) % 2 else "polished_blackstone")
            edge = x in (ax - 4, bx + 4) and z in (az - 4, az + 4)
            if edge:
                t.fill(x, FLOOR + 1, z, x, FLOOR + 6, z, "polished_blackstone_bricks")
            t.set(x, FLOOR + 7, z, "polished_blackstone_brick_slab[type=bottom]")
    for x, z in ((ax - 3, az - 3), (bx + 3, az - 3), (ax - 3, az + 3), (bx + 3, az + 3)):
        t.set(x, FLOOR + 6, z, LANTERN)
    pieces.sign(t.set, ax - 1, FLOOR + 2, az, "west", [text("portal.cartel1"), text("portal.cartel2")], wood="crimson")


def well(t):
    x0, x1, z0, z1 = WELL
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            inner = x0 < x < x1 and z0 < z < z1
            for y in range(1, FLOOR + 1):
                t.set(x, y, z, "water" if inner else "stone_bricks")
            t.set(x, FLOOR + 1, z, "air" if inner else "stone_brick_wall")
            t.set(x, FLOOR + 4, z, "stone_brick_slab[type=bottom]")
            if x in (x0, x1) and z in (z0, z1):
                t.fill(x, FLOOR + 1, z, x, FLOOR + 3, z, "stone_bricks")
    t.set(C + 6, FLOOR + 3, C + 6, LANTERN)


def bell(t):
    x, y, z = BELL
    for px in (x - 1, x + 1):
        t.fill(px, FLOOR + 1, z, px, FLOOR + 3, z, "stone_brick_wall")
    for px in (x - 1, x, x + 1):
        t.set(px, FLOOR + 4, z, "chiseled_stone_bricks")
    t.set(x, y, z, "bell[attachment=ceiling,facing=north]")


def plaza(t):
    a, b = PLAZA
    for x in range(a, b + 1):
        for z in range(a, b + 1):
            t.set(x, FLOOR, z, PAVE if (x + z) % 2 else PAVE2)
    for x, z in ((a + 1, a + 1), (b - 1, a + 1), (a + 1, b - 1), (b - 1, b - 1)):
        t.set(x, FLOOR + 1, z, "stone_brick_wall")
        t.set(x, FLOOR + 2, z, "lantern[hanging=false]")
    for x0 in (a + 4, b - 6):       # benches along the north and south edges
        for z, facing in ((a + 1, "north"), (b - 1, "south")):
            for x in range(x0, x0 + 3):
                t.set(x, FLOOR + 1, z, f"stone_brick_stairs[facing={facing},half=bottom,shape=straight]")
    t.set(C, FLOOR, C, "chiseled_stone_bricks")


def job_board(t):
    """The villages' job board (board.piece), reused as it is: lectern with the book and the bailiff behind it."""
    b = board.piece(THEME, f"{TEMPLATE}_tablon")
    bx, by, bz = BOARD
    for (x, y, z), (st, nbt) in b.blocks.items():
        if st.startswith("minecraft:jigsaw"):
            st, nbt = "minecraft:air", None
        t.set(bx + x, by + y, bz + z, st, nbt)
    for x, y, z, nbt in b.entities:
        t.entity(bx + x, by + y, bz + z, nbt)


def roads(t):
    for x in range(1, N - 1):
        for z in range(ROAD[0], ROAD[1] + 1):
            t.set(x, FLOOR, z, PAVE if z in (ROAD[0], ROAD[1]) else "dirt_path")
            t.set(z, FLOOR, x, PAVE if z in (ROAD[0], ROAD[1]) else "dirt_path")
    # lamp posts along the roads, outside the paving
    for d in range(10, N - 10, 12):
        if PLAZA[0] - 2 <= d <= PLAZA[1] + 2:
            continue
        for x, z in ((ROAD[0] - 1, d), (ROAD[1] + 1, d), (d, ROAD[0] - 1), (d, ROAD[1] + 1)):
            t.fill(x, FLOOR + 1, z, x, FLOOR + 2, z, FENCE)
            t.set(x, FLOOR + 3, z, "lantern[hanging=false]")


def gates(t):
    """Gaps in the wall, a lintel with two lanterns and, inside, a signpost naming where the road goes."""
    for side, (gx, gz) in GATES.items():
        for k in range(ROAD[0], ROAD[1] + 1):
            x, z = (k, gz) if side in ("north", "south") else (gx, k)
            t.set(x, FLOOR, z, PAVE)
            for y in range(FLOOR + 1, FLOOR + 5):
                t.set(x, y, z, "air")
        for k in (ROAD[0], ROAD[1]):
            x, z = (k, gz) if side in ("north", "south") else (gx, k)
            t.set(x, FLOOR + 4, z, LANTERN)
        # signpost on a fence post, just inside, to the right of the road
        dx, dz = pieces.DIRV[side]
        ix, iz = gx - dx * 2, gz - dz * 2
        px, pz = (ROAD[1] + 1, iz) if side in ("north", "south") else (ix, ROAD[1] + 1)
        t.set(px, FLOOR + 1, pz, FENCE)
        rot = {"north": 8, "south": 0, "west": 4, "east": 12}[side]   # readable from inside the town
        t.set(px, FLOOR + 2, pz, f"crimson_sign[rotation={rot}]",
              {"id": "minecraft:sign", "is_waxed": B(1),
               "front_text": {"messages": [text("puerta." + side), text("hacia_mundo"), {"text": ""}, {"text": ""}],
                              "color": "black", "has_glowing_text": B(0)},
               "back_text": {"messages": [text("camino.cartel"), {"text": ""}, {"text": ""}, {"text": ""}],
                             "color": "black", "has_glowing_text": B(0)}})


def walls(t):
    for i in range(N):
        for x, z in ((i, 0), (i, N - 1), (0, i), (N - 1, i)):
            t.fill(x, 0, z, x, WALL_TOP, z, WALL)
            if i % 2 == 0:
                t.set(x, WALL_TOP + 1, z, "stone_brick_wall")
    for cx, cz in ((0, 0), (N - TOWER, 0), (0, N - TOWER), (N - TOWER, N - TOWER)):
        for x in range(cx, cx + TOWER):
            for z in range(cz, cz + TOWER):
                t.fill(x, 0, z, x, FLOOR + 9, z, WALL)
                if x in (cx, cx + TOWER - 1) or z in (cz, cz + TOWER - 1):
                    if (x + z) % 2 == 0:
                        t.set(x, FLOOR + 10, z, "stone_brick_wall")
        t.set(cx + 3, FLOOR + 10, cz + 3, "stone_brick_wall")
        t.set(cx + 3, FLOOR + 11, cz + 3, "lantern[hanging=false]")


def garden(t, x0, z0, x1, z1, seed):
    flowers = ["poppy", "dandelion", "cornflower", "oxeye_daisy", "azure_bluet", "allium", "red_tulip", "lily_of_the_valley"]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if (x - x0) % 4 == 0 or (z - z0) % 4 == 0:
                t.set(x, FLOOR, z, "dirt_path")
            else:
                t.set(x, FLOOR, z, "grass_block[snowy=false]")
                t.set(x, FLOOR + 1, z, flowers[(x * 7 + z * 3 + seed) % len(flowers)])


def farm(t, x0, z0, x1, z1):
    """Wheat on farmland around a water channel (covered at its ends), the farmer's composter at the edge."""
    cz = (z0 + z1) // 2
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x in (x0, x1) or z in (z0, z1):
                t.set(x, FLOOR, z, "dirt_path")
            elif z == cz:
                t.set(x, FLOOR, z, "water")
                t.set(x, FLOOR - 1, z, "stone_bricks")
            else:
                t.set(x, FLOOR, z, "farmland[moisture=7]")
                t.set(x, FLOOR + 1, z, "wheat[age=7]" if (x + z) % 3 else "wheat[age=4]")
    t.set(x0, FLOOR + 1, z0, "composter[level=0]")
    return (x0, z0)


def stable(t, x0, z0, x1, z1):
    """Fenced paddock with a roofed shelter (hay, a water trough) and two horses."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.set(x, FLOOR, z, "grass_block[snowy=false]")
            if x in (x0, x1) or z in (z0, z1):
                t.set(x, FLOOR + 1, z, FENCE)
    gx = (x0 + x1) // 2
    t.set(gx, FLOOR + 1, z1, f"{GATE}[facing=south,in_wall=false,open=false,powered=false]")
    for x in range(x0 + 1, x0 + 6):
        for z in range(z0 + 1, z0 + 5):
            t.set(x, FLOOR + 4, z, f"{WOOD_SLAB}[type=bottom]")
    for x, z in ((x0 + 1, z0 + 4), (x0 + 5, z0 + 4)):
        t.fill(x, FLOOR + 1, z, x, FLOOR + 3, z, FENCE)
    t.set(x0 + 1, FLOOR + 1, z0 + 1, "hay_block[axis=y]")
    t.set(x0 + 2, FLOOR + 1, z0 + 1, "hay_block[axis=y]")
    t.set(x0 + 4, FLOOR + 1, z0 + 1, "water_cauldron[level=3]")
    t.set(x0 + 3, FLOOR + 3, z0 + 2, LANTERN)
    for i, variant in enumerate((0, 1026)):
        t.entity(x0 + 4 + 3 * i, FLOOR + 1, z0 + 7, {"id": "minecraft:horse", "PersistenceRequired": B(1), "Variant": variant})


def chapel(t, x0, z0, x1, z1):
    """Inside: pews, an altar with candles, stained glass and the cleric's brewing stand."""
    cx = (x0 + x1) // 2
    t.set(cx, FLOOR + 1, z0 + 2, "chiseled_stone_bricks")
    t.set(cx - 1, FLOOR + 1, z0 + 2, "stone_brick_stairs[facing=east,half=top,shape=straight]")
    t.set(cx + 1, FLOOR + 1, z0 + 2, "stone_brick_stairs[facing=west,half=top,shape=straight]")
    t.set(cx, FLOOR + 2, z0 + 2, "candle[candles=3,lit=false]")
    for z in range(z0 + 5, z1 - 2, 2):
        for x in list(range(x0 + 2, cx - 1)) + list(range(cx + 2, x1 - 1)):
            t.set(x, FLOOR + 1, z, f"{'crimson_stairs'}[facing=south,half=bottom,shape=straight]")
    for x in range(x0 + 2, x1 - 1, 3):
        t.set(x, FLOOR + 2, z0, "yellow_stained_glass_pane")
        t.set(x, FLOOR + 3, z0, "yellow_stained_glass_pane")
    t.set(x1 - 1, FLOOR + 1, z0 + 1, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]")
    return [("brewing_stand", x1 - 1, z0 + 1)]


def office(t, x0, z0, x1, z1):
    """The market office: the return barrels in two rows on the east wall and a counter."""
    out = []
    for i in range(RETURNS):
        z = z0 + 2 + i % 6
        y = FLOOR + 1 + i // 6
        t.set(x1 - 1, y, z, "barrel[facing=west,open=false]", {"id": "minecraft:barrel"})
        out.append([x1 - 1, y, z])
    pieces.sign(t.set, x1 - 2, FLOOR + 3, z0 + 1, "west", [text("devolucion.cartel1"), text("devolucion.cartel2")],
                wood="crimson")
    return out


def path(t, a, b):
    """Dirt path (2 wide) from cell a to cell b: first along x, then along z."""
    (ax, az), (bx, bz) = a, b
    for x in range(min(ax, bx), max(ax, bx) + 1):
        for z in (az, az + 1):
            if t.get(x, FLOOR, z) in ("minecraft:grass_block[snowy=false]", None):
                t.set(x, FLOOR, z, "dirt_path")
    for z in range(min(az, bz), max(az, bz) + 1):
        for x in (bx, bx + 1):
            if t.get(x, FLOOR, z) in ("minecraft:grass_block[snowy=false]", None):
                t.set(x, FLOOR, z, "dirt_path")


# ------------------------------------------------------------------ the whole town
def construct():
    t = Template(TEMPLATE)
    t.villagers, t.beds, t.stalls, t.returns = [], [], [], []
    for x in range(N):
        for z in range(N):
            t.fill(x, 0, z, x, FLOOR - 1, z, "stone")
            t.set(x, FLOOR, z, "grass_block[snowy=false]")
            t.fill(x, FLOOR + 1, z, x, HEIGHT - 1, z, "air")
    roads(t)
    plaza(t)
    bell(t)
    well(t)
    stations = []
    doors = {}
    for name, x0, z0, x1, z1, side, along, extra in _buildings():
        door, cells = building(t, name, x0, z0, x1, z1, side, along, extra)
        doors[name] = door
        stations += cells
        if name == "posada":
            t.beds += inn_beds(t, x0, z0, x1, z1, 8)
        elif name == "hostal":
            t.beds += inn_beds(t, x0, z0, x1, z1, 6)
        elif name == "capilla":
            stations += chapel(t, x0, z0, x1, z1)
        elif name == "oficina":
            t.returns = office(t, x0, z0, x1, z1)
    stable(t, 10, 8, 22, 20)
    garden(t, 26, 8, 42, 22, 0)
    for z0, z1 in ((38, ROAD[0] - 2), (ROAD[1] + 2, 58)):
        garden(t, 8, z0, 20, z1, 3)
        garden(t, 76, z0, 88, z1, 5)
    stations.append(("composter",) + farm(t, 76, 8, 88, 22))
    # the stalls and the market lane between their two rows
    number = 1
    for zn, faces in STALL_ROWS:
        for x0 in STALL_X:
            box, sign = stall(t, x0, zn, faces, number)
            t.stalls.append({"id": number, "caja": box, "cartel": sign})
            number += 1
    for x in range(STALL_X[0], ROAD[0]):
        for z in range(STALL_ROWS[0][0] + STALL_W, STALL_ROWS[1][0]):
            t.set(x, FLOOR, z, "dirt_path" if (x + z) % 3 else "coarse_dirt")
    garden(t, 66, 62, 88, 72, 1)
    portal(t)
    job_board(t)
    walls(t)
    gates(t)
    # paths from each door to the nearest road
    for name, (dx, dz) in doors.items():
        rx = ROAD[0] - 1 if dx < C else ROAD[1] + 1
        path(t, (dx, dz), (rx, dz))
    # the villagers: each one next to its workstation (it claims it at once; a bed is within 48 blocks)
    taken = set()
    for st, x, z in stations:
        prof = PROFESSION[st]
        sx, sz = _free_beside(t, x, z, taken)
        taken.add((sx, sz))
        n = villager(prof, THEME["vtype"])
        n["Rotation"] = [F(0.0), F(0.0)]
        t.entity(sx, FLOOR + 1, sz, n)
        t.villagers.append((prof, sx, sz))
    golem = {"id": "minecraft:iron_golem", "PlayerCreated": B(0), "PersistenceRequired": B(1)}
    t.entity(C + 6, FLOOR + 1, C - 6, golem)
    return t


def _free_beside(t, x, z, taken):
    for dx, dz in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        if (x + dx, z + dz) not in taken and t.is_free(x + dx, FLOOR + 1, z + dz) and t.is_free(x + dx, FLOOR + 2, z + dz):
            return x + dx, z + dz
    raise SystemExit(f"casa_heraldo: no free cell beside the workstation at {x} {z}")


def dock():
    """Dock out over the water (along +z): a slab deck on posts down to y = 0 of the template (the Java side
    places it with y = 1 at the water's surface), with a railing and lanterns."""
    w, length = DOCK_SIZE
    t = Template(DOCK)
    for x in range(w):
        for z in range(length):
            t.set(x, 1, z, "stone_brick_slab[type=top]" if 0 < x < w - 1 else TRIM)
            if x in (0, w - 1) and z % 4 == 0:
                t.set(x, 0, z, "stone_bricks")
                t.set(x, 2, z, "stone_brick_wall")
                t.set(x, 3, z, "lantern[hanging=false]")
            elif x in (0, w - 1):
                t.set(x, 2, z, "stone_brick_wall")
    t.set(w // 2, 2, length - 1, "stone_brick_wall")
    return t


def dataset(t=None):
    """What the Java side reads (heraldia/casa_heraldo.json): positions relative to the template's minimum corner."""
    t = t or construct()
    w, length = DOCK_SIZE
    return {
        "version": VERSION,
        "plantilla": f"{NS}:{TEMPLATE}",
        "tamano": [N, HEIGHT, N],
        "suelo": FLOOR,
        "aparicion": list(SPAWN),
        "campana": list(BELL),
        "puertas": {side: list(p) for side, p in GATES.items()},
        "camino": [ROAD[0] - C, ROAD[1] - C],
        "portal": [list(PORTAL[0]), list(PORTAL[1])],
        "puestos": t.stalls,
        "devolucion": t.returns,
        "muelle": {"plantilla": f"{NS}:{DOCK}", "tamano": [w, 4, length]},
        "estilo": STYLE,
    }


# ------------------------------------------------------------------ audit
def _name(st):
    return (st or "minecraft:air").split("[")[0].removeprefix("minecraft:")


FLAMMABLE = ("oak_", "spruce_", "birch_", "jungle_", "acacia_", "dark_oak_", "mangrove_", "cherry_", "bamboo", "pale_oak_",
             "wool", "carpet", "bookshelf", "leaves", "log", "tnt")


def errors(t=None):
    """[] if the template keeps what casa_heraldo.json promises."""
    t = t or construct()
    d = dataset(t)
    e = []
    if t.size() != (N, HEIGHT, N):
        e.append(f"casa_heraldo: size {t.size()} instead of {(N, HEIGHT, N)}")
    for (x, y, z), (st, _) in t.blocks.items():
        n = _name(st)
        if any(n.startswith(f) or n.endswith(f) for f in FLAMMABLE) and n != "hay_block":
            e.append(f"casa_heraldo: {n} burns ({x} {y} {z})")
    if _name(t.get(*BELL)) != "bell":
        e.append("casa_heraldo: no bell where the blueprint says")
    if _name(t.get(BELL[0], BELL[1] + 1, BELL[2])) in ("air", "lantern"):
        e.append("casa_heraldo: the bell hangs from nothing")
    sx, sy, sz = SPAWN
    if not (t.is_free(sx, sy, sz) and t.is_free(sx, sy + 1, sz)) or t.is_free(sx, sy - 1, sz):
        e.append("casa_heraldo: the spawn point is not a free spot on the ground")
    (ax, ay, az), (bx, by, bz) = PORTAL
    if bx - ax + 1 < 4 or by - ay + 1 < 5:
        e.append("casa_heraldo: the portal frame is smaller than a Nether portal's minimum (4 x 5)")
    for x in range(ax, bx + 1):
        for y in range(ay, by + 1):
            edge = x in (ax, bx) or y in (ay, by)
            if edge and (x, y) not in ((ax, ay), (bx, ay), (ax, by), (bx, by)) and _name(t.get(x, y, az)) != "obsidian":
                e.append(f"casa_heraldo: portal frame broken at {x} {y} {az}")
            if not edge and not t.is_free(x, y, az):
                e.append(f"casa_heraldo: the portal's inside is not empty at {x} {y} {az}")
    if not any(_name(st) == "lectern" and nbt and "Book" in nbt for st, nbt in t.blocks.values()):
        e.append("casa_heraldo: the job board's lectern has no book")
    if len(t.stalls) < 8:
        e.append("casa_heraldo: fewer than 8 market stalls")
    for s in t.stalls:
        (x0, y0, z0), (x1, y1, z1) = s["caja"]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    if not t.is_free(x, y, z):
                        e.append(f"casa_heraldo: stall {s['id']} is not empty at {x} {y} {z}")
        if "sign" not in _name(t.get(*s["cartel"])):
            e.append(f"casa_heraldo: stall {s['id']} has no sign")
    if len(t.returns) != RETURNS or any(_name(t.get(*p)) != "barrel" for p in t.returns):
        e.append("casa_heraldo: the return barrels are not where the blueprint says")
    for side, (gx, gz) in GATES.items():
        for y in range(FLOOR + 1, FLOOR + 4):
            if not t.is_free(gx, y, gz):
                e.append(f"casa_heraldo: the {side} gate is closed")
    beds = sum(1 for st, _ in t.blocks.values() if _name(st) == "red_bed" and "part=head" in st)
    if beds < len(t.villagers) + 2:
        e.append(f"casa_heraldo: {beds} beds for {len(t.villagers)} villagers (and two spare for children)")
    for prof, x, z in t.villagers:
        if min(max(abs(x - bx_), abs(z - bz_)) for bx_, bz_ in t.beds) > 40:
            e.append(f"casa_heraldo: the {prof} has no bed within 40 blocks")
    if len({(x, z) for _, x, z in t.villagers}) != len(t.villagers):
        e.append("casa_heraldo: two villagers start on the same cell")
    if len({p for p, _, _ in t.villagers}) != len(t.villagers):
        e.append("casa_heraldo: two villagers share a profession (one workstation each)")
    return e


# ------------------------------------------------------------------ texts
TEXTS = {
    "nombre": ("La Casa del Heraldo", "The Herald's House"),
    "edificio.posada": ("Posada", "Inn"),
    "edificio.hostal": ("Hostal", "Guest House"),
    "edificio.capilla": ("Capilla", "Chapel"),
    "edificio.herreria": ("Herrería", "Smithy"),
    "edificio.carniceria": ("Carnicería", "Butcher"),
    "edificio.biblioteca": ("Biblioteca", "Library"),
    "edificio.cartografo": ("Cartógrafo", "Cartographer"),
    "edificio.taller": ("Taller", "Workshop"),
    "edificio.oficina": ("Mercado", "Market Office"),
    "puerta.north": ("Puerta Norte", "North Gate"),
    "puerta.south": ("Puerta Sur", "South Gate"),
    "puerta.west": ("Puerta Oeste", "West Gate"),
    "puerta.east": ("Puerta Este", "East Gate"),
    "hacia_mundo": ("Al mundo", "To the world"),
    "camino.cartel": ("Casa del Heraldo", "Herald's House"),
    "camino.cartel2": ("%s bloques", "%s blocks"),
    "puesto": ("Puesto", "Stall"),
    "se_alquila": ("Se alquila", "For rent"),
    "cerrado": ("Cerrado", "Closed"),
    "portal.cartel1": ("Portal al Nether", "Nether Portal"),
    "portal.cartel2": ("Solo un operador", "Operators only"),
    "devolucion.cartel1": ("Devoluciones", "Returned"),
    "devolucion.cartel2": ("de los puestos", "stall items"),
    # chat
    "prohibido": ("La Casa del Heraldo está protegida: aquí no se puede construir ni cambiar nada",
                  "The Herald's House is protected: nothing can be built or changed here"),
    "portal.prohibido": ("Solo un operador puede encender el portal de la Casa del Heraldo",
                         "Only an operator can light the Herald's House portal"),
    "tablon": ("Tablón de encargos de la Casa del Heraldo:", "The Herald's House job board:"),
    "info": ("La Casa del Heraldo está en %s %s %s", "The Herald's House is at %s %s %s"),
    "no_existe": ("Este mundo aún no tiene Casa del Heraldo (un operador la coloca con /heraldia herald place)",
                  "This world has no Herald's House yet (an operator places it with /heraldia herald place)"),
    "desactivada": ("La Casa del Heraldo está desactivada (casa_heraldo.activado)",
                    "The Herald's House is disabled (casa_heraldo.activado)"),
    "ya_existe": ("Este mundo ya tiene su Casa del Heraldo, en %s %s %s", "This world already has its Herald's House, at %s %s %s"),
    "trabajando": ("La Casa del Heraldo se está construyendo; espera a que termine", "The Herald's House is being built; wait for it to finish"),
    "buscando": ("Buscando sitio cerca del spawn…", "Looking for a site near spawn…"),
    "sin_sitio": ("No hay sitio a menos de %s bloques del spawn sin la arena ni otra estructura; prueba /heraldia herald place here",
                  "No site within %s blocks of spawn clear of the arena and other structures; try /heraldia herald place here"),
    "propuesta": ("Sitio propuesto: centro en %s %s %s (96 × 96, protección hasta %s bloques alrededor). Las columnas de luz "
                  "marcan las esquinas: todo lo que haya dentro del cuadrado se sustituye.",
                  "Proposed site: centre at %s %s %s (96 × 96, protected up to %s blocks around). The columns of light mark "
                  "the corners: everything inside the square is replaced."),
    "propuesta.confirmar": ("Para construirla: %s", "To build it: %s"),
    "sin_propuesta": ("No hay ninguna propuesta: usa antes %s", "There is no proposal: use %s first"),
    "colocando": ("Construyendo la Casa del Heraldo en %s %s %s…", "Building the Herald's House at %s %s %s…"),
    "colocada": ("La Casa del Heraldo está lista en %s %s %s", "The Herald's House is ready at %s %s %s"),
    "spawn": ("El spawn del mundo no se ha movido. Para que los jugadores aparezcan en la plaza: %s",
              "The world spawn has not moved. To have players appear on the plaza: %s"),
    # the market
    "mercado.desactivado": ("Los puestos del mercado no se alquilan en este servidor", "Market stalls are not for rent on this server"),
    "mercado.libre": ("Puesto %s: libre. Entrada %s esmeraldas y %s de alquiler cada %s días. %s",
                      "Stall %s: free. Entry %s emeralds and %s rent every %s days. %s"),
    "mercado.alquilar": ("[Alquilar]", "[Rent it]"),
    "mercado.ocupado": ("Puesto %s: de %s, pagado durante %s días más", "Stall %s: %s's, paid for %s more days"),
    "mercado.tuyo": ("Puesto %s: tuyo, pagado durante %s días más. %s %s", "Stall %s: yours, paid for %s more days. %s %s"),
    "mercado.pagar": ("[Pagar %s]", "[Pay %s]"),
    "mercado.dejar": ("[Dejarlo]", "[Give it up]"),
    "mercado.vencido": ("Puesto %s: el alquiler venció; queda libre en cuanto se recojan sus cosas",
                        "Stall %s: the rent ran out; it is free as soon as its things are collected"),
    "mercado.sin_esmeraldas": ("Hacen falta %s esmeraldas (llevas %s)", "You need %s emeralds (you have %s)"),
    "mercado.alquilado": ("El puesto %s es tuyo hasta dentro de %s días. Paga antes con /heraldia herald stall pay %s",
                          "Stall %s is yours for %s days. Pay before then with /heraldia herald stall pay %s"),
    "mercado.pagado": ("Puesto %s pagado: es tuyo %s días más", "Stall %s paid: it is yours for %s more days"),
    "mercado.tope": ("Puedes pagar como mucho %s periodos por adelantado", "You can pay at most %s periods in advance"),
    "mercado.ya_tienes": ("Ya tienes el puesto %s: solo uno por jugador", "You already have stall %s: one per player"),
    "mercado.no_es_tuyo": ("Ese puesto no es tuyo", "That stall is not yours"),
    "mercado.no_existe": ("No hay ningún puesto %s", "There is no stall %s"),
    "mercado.aviso": ("Tu puesto %s del mercado de la Casa del Heraldo vence en %s días: /heraldia herald stall pay %s",
                      "Your stall %s at the Herald's House market is due in %s days: /heraldia herald stall pay %s"),
    "mercado.gracia": ("El alquiler de tu puesto %s venció: tienes %s días para pagar o lo pierdes (/heraldia herald stall pay %s)",
                       "The rent on your stall %s ran out: you have %s days to pay or you lose it (/heraldia herald stall pay %s)"),
    "mercado.perdido": ("Has perdido el puesto %s por no pagar. Tus cosas están en el barril de devoluciones de la "
                        "oficina del mercado, en %s %s %s (solo tú puedes abrirlo)",
                        "You lost stall %s for not paying. Your things are in the return barrel of the market office, at "
                        "%s %s %s (only you can open it)"),
    "mercado.dejado": ("Has dejado el puesto %s. Tus cosas están en el barril de devoluciones, en %s %s %s",
                       "You gave up stall %s. Your things are in the return barrel, at %s %s %s"),
    "mercado.desalojado": ("Un operador ha desalojado el puesto %s. Tus cosas están en el barril de devoluciones, en %s %s %s",
                           "An operator has cleared stall %s. Your things are in the return barrel, at %s %s %s"),
    "mercado.devolucion_llena": ("Los barriles de devoluciones están llenos: el puesto %s sigue cerrado hasta que un operador "
                                 "vacíe alguno", "The return barrels are full: stall %s stays closed until an operator empties one"),
    "mercado.barril_ajeno": ("Ese barril de devoluciones guarda las cosas de otro jugador", "That return barrel holds another player's things"),
    "mercado.pendiente": ("Tienes cosas en el barril de devoluciones del mercado, en %s %s %s",
                          "You have things in the market's return barrel, at %s %s %s"),
    "mercado.lista": ("Puestos del mercado:", "Market stalls:"),
    "mercado.linea_libre": ("  %s: libre", "  %s: free"),
    "mercado.linea": ("  %s: %s, %s días", "  %s: %s, %s days"),
}
# signs: what has to fit on a sign line in each language (key, bold, worst-case arguments)
SIGN = [("puesto", False, []), ("se_alquila", False, []), ("cerrado", False, []),
        ("portal.cartel1", False, []), ("portal.cartel2", False, []), ("devolucion.cartel1", False, []),
        ("devolucion.cartel2", False, []), ("hacia_mundo", False, []), ("camino.cartel", False, []),
        ("camino.cartel2", False, ["150"])] + [(f"puerta.{s}", False, []) for s in GATES] + \
       [(f"edificio.{b[0]}", False, []) for b in _buildings()]


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{NS}.casa_heraldo.{k}"], out["en_us"][f"{NS}.casa_heraldo.{k}"] = es, en
    return out


def text_errors(translations=None):
    """[] if every sign line fits (90 px) in each language. `translations`: {code: texts} of the other languages."""
    import languages
    base = lang()
    e = []
    for code, texts in [("es_es", base["es_es"]), ("en_us", base["en_us"])] + list((translations or {}).items()):
        for k, bold, args in SIGN:
            s = languages.format_text(texts[f"{NS}.casa_heraldo.{k}"], args)
            if languages.sign_width(s, bold) > languages.SIGN_WIDTH:
                e.append(f"casa_heraldo: {code}: the sign line {k} does not fit: «{s}»")
    return e


def write(out, jdump):
    """Writes the two templates and heraldia/casa_heraldo.json; returns the texts. Fails if the template does not keep
    what it promises."""
    t = construct()
    e = errors(t) + text_errors()
    if e:
        raise SystemExit("\n".join(e))
    t.save(out)
    dock().save(out)
    jdump(out, f"{NS}/casa_heraldo.json", dataset(t))
    return lang()
