"""Coast templates in design coordinates: x across (0 on the axis), z towards the sea (the shore, the anchor, at
z = 0), y = 0 the bottom row.

Lighthouse (y = 0, the platform flush with the highest terrain of the footprint): the 15 x 20 platform on land (z = -20..-1),
the 7 x 7 tower next to the shore (z = -8..-2) 28 blocks tall, the keeper's house at the back and the 3 x 11 pier
over the water (z = 0..10) with piles every 3 blocks. The light: a lit redstone lamp on a redstone block
in the centre of the lantern (y = 22-23), with glowstone on top: always on, no circuits.

Shipwreck (the 9 x 31 galleon, keel at y = 0, hold y = 2-4, deck y = 5, stern castle with the cabin y = 6-8,
main mast up to y = 17): run aground (a) with the bow on the beach (z = -14..16, `sea_row` 1) or half-sunk (b) in
shallow water (z = 8..38, `sea_row` 4, with the hold flooded). Split in half (z from 15 to 17 from the
bow): no deck and with the starboard side open. Below `sea_row` there is no air in the template: what is not
hull is left unplaced (the water or sand of the site stays)."""
from types import SimpleNamespace
from core import Template, B, F, NS, adult, anchored
from mediums import _common as c
from uniques._common import pieces

WIDTH = 7                     # half of the lighthouse platform (x = -7..7)
DEPTH = 20                    # lighthouse land (z = -20..-1)
DOCK = 10                   # the pier reaches z = 10
TOWER_Z = -5                  # centre of the tower
WALL_HEIGHT = 21                # the tower shaft: y = 1..21
TUNNEL = 22                  # gallery floor (y = 22) and the lantern on top (y = 23-24)
HULL_LENGTH = 31


def _table(t, x, y, z, wood):
    t.set(x, y, z, f"{wood}_fence")
    t.set(x, y + 1, z, f"{wood}_pressure_plate[powered=false]")


# ------------------------------------------------------------------ faro
def ring_cells(is_square):
    """dentro(dx, dz, r): the footprint of radius r of the tower, square or octagonal (corners cut; r = 1, 3 x 3)."""
    if is_square:
        return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r
    return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r and (r <= 1 or abs(dx) + abs(dz) <= 2 * r - 1)


def _lighthouse(variant, p, name):
    """The platform and the tower: shaft (r = 3) from y = 1 to 21 with a hollow interior (r = 2), the guard room at y = 12,
    the gallery (r = 4, y = 22) with a railing and the walkway over the wall, and the glazed lantern (r = 2) with the light."""
    t = Template(name)
    inside = ring_cells(variant == "b")
    m, foundation = p["madera"], p["cimiento"]
    # platform (y = 0) and air above: the terrain of the footprint is left clear
    for x in range(-WIDTH, WIDTH + 1):
        for z in range(-DEPTH, 0):
            t.set(x, 0, z, foundation[(x * 7 + z * 3 + x * z) % len(foundation)])
            for y in range(1, 5):
                t.set(x, y, z, "air")
            if p["nieve"] and (x * 5 + z * 11) % 7 == 0:
                t.set(x, 1, z, "snow[layers=1]")
    for dx in range(-4, 5):
        for dz in range(-4, 5):
            x, z = dx, TOWER_Z + dz
            if inside(dx, dz, 3) and not inside(dx, dz, 2):            # shaft wall
                for y in range(1, WALL_HEIGHT + 1):
                    corner_block = variant == "b" and abs(dx) == 3 and abs(dz) == 3
                    if y == 1:
                        st = p["zocalo"]
                    elif corner_block:
                        st = f"{p['esquina']}[axis=y]" if p["esquina"].endswith(("_log", "_wood")) else p["esquina"]
                    elif variant == "a":
                        st = p["banda"] if y in (7, 8, 15, 16) else p["muro"]
                    else:
                        st = p["banda"] if (y // 3) % 2 == 1 else p["muro"]
                    t.set(x, y, z, f"{st}[axis=y]" if st.endswith("_wood") else st)
            elif inside(dx, dz, 2):                                     # hollow interior with the guard room floor
                t.set(x, 0, z, foundation[0])
                for y in range(1, TUNNEL):
                    t.set(x, y, z, "air")
                t.set(x, 11, z, f"{m}_planks")
            if not inside(dx, dz, 4):
                continue
            # gallery, railing, walkway and lantern
            if (dx, dz) != (0, 2):
                t.set(x, TUNNEL, z, p["zocalo"])
            if not inside(dx, dz, 3):
                t.set(x, TUNNEL + 1, z, f"{m}_fence")
            elif not inside(dx, dz, 2) or inside(dx, dz, 1) or (dx, dz) == (0, 2):
                for y in (TUNNEL + 1, TUNNEL + 2):
                    t.set(x, y, z, "air")
            else:
                for y in (TUNNEL + 1, TUNNEL + 2):
                    t.set(x, y, z, "glass_pane")
            if inside(dx, dz, 2):                                       # lantern roof
                t.set(x, TUNNEL + 3, z, p["zocalo"] if inside(dx, dz, 1) else f"{p['losa']}[type=bottom,waterlogged=false]")
    # windows on three faces (the sea one, the south, has the ladder inside)
    for y in (5, 9, 14, 18):
        for dx, dz in ((3, 0), (-3, 0), (0, -3)):
            t.set(dx, y, TOWER_Z + dz, "glass_pane")
    # door to the north (towards the house) and ladder against the south wall, from the ground floor to the gallery
    c.door(t, 0, 1, TOWER_Z - 3, "south", f"{m}_door")
    for y in range(1, TUNNEL + 1):
        t.set(0, y, TOWER_Z + 2, "ladder[facing=north,waterlogged=false]")
    # the light: redstone block under the lamp (always lit) and glowstone on top; the lightning rod at the top
    t.set(0, TUNNEL, TOWER_Z, "redstone_block")
    t.set(0, TUNNEL + 1, TOWER_Z, "redstone_lamp[lit=true]")
    t.set(0, TUNNEL + 2, TOWER_Z, "glowstone")
    t.set(0, TUNNEL + 4, TOWER_Z, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    if p["nieve"]:
        for dx, dz in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            t.set(dx, TUNNEL + 4, TOWER_Z + dz, "snow[layers=2]")
    # inside: ground floor with barrels and a lantern; guard room (y = 12) with the chest and the cartography table
    t.set(-2, 1, TOWER_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    t.set(2, 1, TOWER_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    c.lantern(t, 2, 1, TOWER_Z + 1, hanging=False)
    pieces.chest(c.put(t), -2, 12, TOWER_Z, "east", f"{NS}:costa/faro")
    t.set(2, 12, TOWER_Z, "cartography_table")
    c.lantern(t, 0, 21, TOWER_Z, hanging=True)
    c.lantern(t, 0, 10, TOWER_Z, hanging=True)
    return t


def _house(t, p, side):
    """Keeper's house of 7 x 6 at the back of the platform (side -1: west; 1: east), with the door to the south."""
    m, house = p["madera"], p["casa"]
    x0, x1 = (-6, 0) if side < 0 else (0, 6)
    z0, z1 = -18, -13
    c.box(t, x0, 1, z0, x1, 3, z1, house, corner_block=f"{p['tronco']}[axis=y]")
    t.fill(x0, 0, z0, x1, 0, z1, p["cimiento"][0])
    t.fill(x0, 4, z0, x1, 4, z1, f"{m}_planks")
    c.roof_tiles(t, x0, z0, x1, z1, 5, p["teja"], p["cumbrera"], house)
    door = (x0 + x1) // 2
    c.door(t, door, 1, z1, "north", f"{m}_door")
    c.window(t, x0, 2, -15)
    c.window(t, x1, 2, -15)
    c.window(t, door, 2, z0)
    # bed, table with chair, furnace and the keeper's barrel
    c.bed(t, x0 + 1, z0 + 1, "north", p["cama"])
    _table(t, x1 - 2, 1, z0 + 2, m)
    t.set(x1 - 1, 1, z0 + 2, f"{m}_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    t.set(x1 - 1, 1, z0 + 1, "furnace[facing=west,lit=false]")
    pieces.chest(c.put(t), x0 + 1, 1, z1 - 1, "east", f"{NS}:costa/faro", kind="barrel")
    c.lantern(t, door, 3, z0 + 3)
    # path from the door to the tower
    for z in range(z1 + 1, TOWER_Z - 3):
        t.set(door, 0, z, p["cimiento"][1])
    if door != 0:
        for x in range(min(door, 0), max(door, 0) + 1):
            t.set(x, 0, TOWER_Z - 4, p["cimiento"][1])
    return door


def _pier(t, p):
    """Pier of 3 x 11 (z = 0..10) at platform height, on piles every 3 blocks (they go down to the bottom)."""
    m = p["madera"]
    for z in range(-1, DOCK + 1):
        for x in (-1, 0, 1):
            t.set(x, 0, z, f"{m}_planks")
        if z >= 0 and (z % 3 == 0 or z == DOCK):
            for x in (-1, 1):
                t.set(x, 0, z, f"{p['tronco']}[axis=y]")
    for x in (-1, 0, 1):
        t.set(x, 1, DOCK, f"{m}_fence")
    t.set(-1, 1, DOCK - 1, f"{m}_fence")
    t.set(1, 1, DOCK - 1, f"{m}_fence")
    c.lantern(t, 1, 2, DOCK, hanging=False)
    t.set(-1, 1, 4, f"{m}_fence")                    # bolardo


def offers():
    """Keeper's trades: buys cod and dried kelp, sells empty maps, a compass and a spyglass."""
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.offer({"id": "minecraft:cod", "count": 12}, em(1), 12),
            c.offer({"id": "minecraft:dried_kelp_block", "count": 6}, em(1), 12),
            c.offer(em(2), {"id": "minecraft:map", "count": 1}, 6),
            c.offer(em(4), {"id": "minecraft:compass", "count": 1}, 3),
            c.offer(em(6), {"id": "minecraft:spyglass", "count": 1}, 2)]


def lighthouse(variant, p, name):
    t = _lighthouse(variant, p, name)
    side = -1 if variant == "a" else 1
    door = _house(t, p, side)
    _pier(t, p)
    if variant == "a":                               # the keeper, next to his door
        n = {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
             "CustomName": pieces.text(f"{NS}.costa.farero", "Farero"), "CustomNameVisible": B(1),
             "VillagerData": {"profession": "minecraft:cartographer", "level": 2, "type": f"minecraft:{p['aldeano']}"},
             "Xp": 10, "Rotation": [F(0.0), F(0.0)], "Offers": {"Recipes": offers()}}
        t.entity(door, 1, -11, n)
    o = SimpleNamespace(t=t, anchor_point=(0, 0), sea_row=None, light=(0, TUNNEL + 1, TOWER_Z),
                        land=(-WIDTH, -DEPTH, WIDTH, -1), sea=(-1, 2, 1, DOCK), tunnel=TUNNEL, tower=TOWER_Z)
    return o


# ------------------------------------------------------------------ naufragio
def sleeve(s):
    """Half beam of the hull at s blocks from the bow (0) towards the stern (HULL_LENGTH - 1)."""
    return (0, 1, 2, 2, 3)[s] if s < 5 else 4 if s < 27 else 3


def _galleon(t, p, z0, sea_row, sunken):
    """The hull with the bow at z0 and the stern at z0 + HULL_LENGTH - 1. No air is placed below fila_mar."""
    m, trunk, band = p["madera"], p["tronco"], p["banda"]
    board = f"{m}_planks"
    air_block = lambda x, y, z: t.set(x, y, z, "air") if y > sea_row else None
    broken = lambda s: 15 <= s <= 17
    for s in range(HULL_LENGTH):
        z, h = z0 + s, sleeve(s)
        # keel and bottom
        t.set(0, 0, z, f"{trunk}[axis=z]")
        for x in range(-max(h - 2, 0), max(h - 2, 0) + 1):
            if x:
                t.set(x, 0, z, board)
        # sides (y = 1 one block further in: the curve of the hull) and hold floor
        for x in range(-h, h + 1):
            if abs(x) == max(h - 1, 0) and h > 0:
                t.set(x, 1, z, board)
            elif abs(x) < h - 1:
                t.set(x, 1, z, board)
        for y in range(2, 5):
            for x in range(-h, h + 1):
                if abs(x) == h:
                    if not (broken(s) and x > 0):               # starboard open at the break
                        t.set(x, y, z, band if y == 3 else board)
                elif not broken(s):
                    air_block(x, y, z)
        # deck (y = 5) and gunwale (y = 6)
        for x in range(-h, h + 1):
            if broken(s) and x >= -1:
                continue
            if (x, s) in ((0, 9), (0, 10)):
                air_block(x, 5, z)                                 # hatch open to the hold
            else:
                t.set(x, 5, z, board)
        if 8 <= s <= 21 and not broken(s) and s not in (14, 18):
            for x in (-h, h):
                t.set(x, 6, z, f"{m}_fence")
    # forecastle (y = 6) with its gunwale and a step up from the deck
    for s in range(1, 8):
        for x in range(-sleeve(s), sleeve(s) + 1):
            t.set(x, 6, z0 + s, board)
        for x in (-sleeve(s), sleeve(s)):
            if sleeve(s):
                t.set(x, 7, z0 + s, f"{m}_fence")
    t.set(0, 6, z0 + 8, f"{m}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    for s in range(-3, 1):                                     # bowsprit
        t.set(0, 6, z0 + s, f"{trunk}[axis=z]")
    # sterncastle: the cabin (y = 6-8) with its door to the bow and the roof with gunwale (y = 9-10)
    for s in range(22, HULL_LENGTH):
        z, h = z0 + s, sleeve(s)
        for x in range(-h, h + 1):
            edge_block = abs(x) == h or s in (22, HULL_LENGTH - 1)
            for y in range(6, 9):
                t.set(x, y, z, board if edge_block else "air")
            t.set(x, 9, z, board)
            if abs(x) == h or s == HULL_LENGTH - 1:
                t.set(x, 10, z, f"{m}_fence")
    c.door(t, 0, 6, z0 + 22, "south", f"{m}_door")
    for s in (25, 28):
        for x in (-sleeve(s), sleeve(s)):
            t.set(x, 7, z0 + s, "glass_pane")
    pieces.chest(c.put(t), -2, 6, z0 + 28, "east", f"{NS}:costa/camarote")
    _table(t, 2, 6, z0 + 26, m)
    t.set(2, 6, z0 + 27, f"{m}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    c.lantern(t, 0, 8, z0 + 26, hanging=True)
    # main mast (y = 1..17) with the yard and the torn sail; the stump of the mizzen, broken at y = 9
    for y in range(1, 18):
        t.set(0, y, z0 + 12, f"{trunk}[axis=y]")
    for x in range(-4, 5):
        t.set(x, 15, z0 + 13, f"{trunk}[axis=x]")
    for x in range(-3, 4):
        for y in range(8, 15):
            if (x * 3 + y * 5) % 7 != 0 and not (y < 10 and (x + y) % 3 == 0):
                t.set(x, y, z0 + 13, p["vela"])
    for y in range(1, 10):
        t.set(0, y, z0 + 20, f"{trunk}[axis=y]")
    t.set(0, 10, z0 + 20, f"stripped_{trunk}[axis=y]")
    # in the hold: the chest (under water in the half-sunk one) and some barrels
    pieces.chest(c.put(t), 2, 2, z0 + 6, "west", f"{NS}:costa/bodega", waterlogged=sunken)
    if not sunken:
        t.set(-2, 2, z0 + 6, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
        t.set(-2, 2, z0 + 10, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    if p["nieve"]:
        for s in range(9, 22):
            for x in range(-sleeve(s) + 1, sleeve(s)):
                if not broken(s) and (x * 7 + s * 3) % 5 == 0 and t.get(x, 6, z0 + s) is None \
                        and "planks" in (t.get(x, 5, z0 + s) or ""):
                    t.set(x, 6, z0 + s, "snow[layers=1]")


def shipwreck(variant, p, name):
    t = Template(name)
    sunken = variant == "b"
    if sunken:
        z0, row = 8, 4
    else:
        z0, row = -14, 1
    _galleon(t, p, z0, row, sunken)
    if sunken:                                       # the drowned of the flooded hold, anchored and adult
        n = {"id": "minecraft:drowned", "PersistenceRequired": B(1), "Rotation": [F(180.0), F(0.0)]}
        t.entity(-2, 2, z0 + 4, anchored(adult(n), always=True))
        land, sea = (-2, -6, 2, -2), (-4, z0, 4, z0 + HULL_LENGTH - 1)
    else:
        land, sea = (-3, z0, 3, -3), (-3, 3, 3, z0 + HULL_LENGTH - 1)
    return SimpleNamespace(t=t, anchor_point=(0, 0), sea_row=row, light=None, land=land, sea=sea, bow=z0)


def construct(kind, variant, palette, name):
    return (lighthouse if kind == "faro" else shipwreck)(variant, palette, name)
