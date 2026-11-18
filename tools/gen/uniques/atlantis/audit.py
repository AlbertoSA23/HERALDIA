"""Audit of the whole Atlantis plan (condition for generating).

Checks: watertightness of the dry zones, supports, reachability without breaking blocks, valid items in the
fixed chests and proportion of surface in good condition. Returns a list of warnings; empty = fit.
"""
from collections import deque
import validate
from . import urban_layout as U
from .world import block_name

NEIGHBORS = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0))
AQUATIC_BLOCKS = ("water", "bubble_column", "kelp", "kelp_plant", "seagrass", "tall_seagrass")
# Blocks that water tears away if it enters their cell: they count as air for watertightness.
LAVABLES = ("redstone_wire", "redstone_wall_torch", "redstone_torch", "lever", "stone_pressure_plate", "cyan_carpet", "azalea",
            "torch", "wall_torch")
THIN = LAVABLES + ("ladder", "warped_wall_sign", "cyan_wall_banner", "iron_bars", "warped_fence", "dark_oak_fence", "sea_pickle")
FREE_STEP = ("air", "warped_door", "iron_door", "ladder", "warped_trapdoor", "warped_wall_sign", "cyan_wall_banner", "sea_pickle") + LAVABLES


def is_water(st):
    return st is not None and (block_name(st) in AQUATIC_BLOCKS or "waterlogged=true" in st)


def is_dry(st):
    return st is not None and block_name(st) in ("air",) + LAVABLES


def solid(st):
    """Full block that supports and does not let anything through (sufficient approximation for the city's materials)."""
    if st is None:
        return False
    b = block_name(st)
    if b in AQUATIC_BLOCKS or b in FREE_STEP or b in THIN:
        return False
    return not any(k in b for k in ("_stairs", "_slab", "_door", "_fence", "_sign", "_banner", "_bed", "coral_fan", "lectern",
                                    "chest", "decorated_pot", "armor", "anvil", "grindstone", "stonecutter"))


def walkable(st):
    return st is not None and (is_water(st) or block_name(st) in FREE_STEP)


def watertightness(m, out):
    n = 0
    for (x, y, z), (st, _) in m.blocks.items():
        if not is_dry(st):
            continue
        for dx, dy, dz in NEIGHBORS:
            v = m.get(x + dx, y + dy, z + dz)
            if v is None or (dy >= 0 and is_water(v)):
                n += 1
                if n <= 12:
                    out.append(f"fuga: {block_name(st)} en {(x, y, z)} toca {block_name(v) if v else 'terreno natural'} en {(x + dx, y + dy, z + dz)}")
    if n > 12:
        out.append(f"fuga: {n} en total")


def supports(m, out):
    behind = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
    failures = {}
    def failing(what, pos):
        failures.setdefault(what, []).append(pos)
    for (x, y, z), (st, _) in m.blocks.items():
        b = block_name(st)
        beneath = m.get(x, y - 1, z)
        if b in ("ladder", "warped_wall_sign", "cyan_wall_banner", "redstone_wall_torch") or b == "lever" and "face=wall" in st:
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            dx, dz = behind[f]
            if not solid(m.get(x + dx, y, z + dz)):
                failing(b + " sin pared detrás", (x, y, z))
        elif b.endswith("_door") and "half=lower" in st or b in ("redstone_wire", "stone_pressure_plate", "cyan_carpet", "decorated_pot",
                                                                  "lectern", "azalea", "sea_pickle", "seagrass", "spawner") and b != "spawner":
            if not (solid(beneath) or b == "cyan_carpet" and beneath and "trapdoor" in beneath or b == "stone_pressure_plate" and beneath and "dispenser" in beneath):
                failing(b + " sin apoyo", (x, y, z))
        elif b in ("sand", "gravel") and not solid(beneath):
            failing(b + " sin suelo (caería)", (x, y, z))
        elif b in ("kelp", "kelp_plant") and not (solid(beneath) or block_name(beneath) == "kelp_plant"):
            failing("alga sin base", (x, y, z))
        elif b == "kelp_plant" and block_name(m.get(x, y + 1, z)) not in ("kelp", "kelp_plant"):
            failing("alga cortada", (x, y, z))
        elif b.endswith("_bed") and not solid(beneath):
            failing("cama sin suelo", (x, y, z))
        elif b in CORALS and not solid(beneath):
            failing("coral sin apoyo", (x, y, z))
        elif b == "bubble_column":
            if block_name(beneath) not in ("bubble_column", "soul_sand", "magma_block"):
                failing("columna de burbujas sin base", (x, y, z))
    for what, ps in failures.items():
        out.append(f"{what}: {len(ps)}, p. ej. {ps[:3]}")


def reachable(m):
    """Cells that a player reaches from the open sea by swimming, walking, jumping one block and by ladders,
    opening doors and trapdoors, without breaking anything. Only explored within the boxes of the sites (+1)."""
    bucket = {}
    for (_, x1, y1, z1, x2, y2, z2, _) in m.sites:
        box = (x1 - 1, y1 - 1, z1 - 1, x2 + 1, y2 + 1, z2 + 1)
        for cx in range(box[0] >> 4, (box[3] >> 4) + 1):
            for cz in range(box[2] >> 4, (box[5] >> 4) + 1):
                bucket.setdefault((cx, cz), []).append(box)

    def inside(x, y, z):
        for c in bucket.get((x >> 4, z >> 4), ()):
            if c[0] <= x <= c[3] and c[1] <= y <= c[4] and c[2] <= z <= c[5]:
                return True
        return False

    seen, queue = set(), deque()
    for (_, x1, y1, z1, x2, y2, z2, _) in m.sites:           # seeds: open water in the outer layer of each box
        if y2 <= U.FLOOR:
            continue
        for x in range(x1 - 1, x2 + 2):
            for z in range(z1 - 1, z2 + 2):
                edge_block = x in (x1 - 1, x2 + 1) or z in (z1 - 1, z2 + 1)
                for y in ((range(max(y1, U.FLOOR + 1), y2 + 2)) if edge_block else (y2 + 1,)):
                    if y > U.ROOF:
                        continue
                    if (x, y, z) not in m.blocks and U.base(x, y, z) == "minecraft:water" and (x, y, z) not in seen:
                        seen.add((x, y, z))
                        queue.append((x, y, z))
    get = m.get
    while queue:
        x, y, z = queue.popleft()
        st = get(x, y, z)
        nothing = is_water(st) or block_name(st) == "ladder"
        steps = list(NEIGHBORS[:4]) + [(0, -1, 0)]
        for dx, dy, dz in steps + ([(0, 1, 0)] if nothing else []):
            p = (x + dx, y + dy, z + dz)
            if p not in seen and inside(*p) and walkable(get(*p)):
                seen.add(p)
                queue.append(p)
        if not nothing:
            upward = get(x, y + 1, z)
            if walkable(upward):
                if is_water(upward) or block_name(upward) == "ladder" or block_name(upward) == "warped_trapdoor":
                    p = (x, y + 1, z)
                    if p not in seen and inside(*p):
                        seen.add(p)
                        queue.append(p)
                for dx, _, dz in NEIGHBORS[:4]:                 # one-block jump
                    p = (x + dx, y + 1, z + dz)
                    if p not in seen and inside(*p) and walkable(get(*p)) and not walkable(get(x + dx, y, z + dz)):
                        seen.add(p)
                        queue.append(p)
    return seen


def accesses(m, out, seen):
    for mark in ("seca", "cofre", "premium", "vestibulo", "jefe", "camara_academia", "camara_arsenal", "arena", "oculta", "generador"):
        wrong = []
        for (x, y, z) in m.marks.get(mark, ()):
            nearby_flag = [(x, y, z)] + [(x + a, y + b, z + c) for a, b, c in NEIGHBORS]
            if not any(p in seen for p in nearby_flag):
                wrong.append((x, y, z))
        if wrong:
            out.append(f"{mark} inaccesible: {len(wrong)}, p. ej. {wrong[:4]}")


CORALS = ("brain_coral", "bubble_coral", "fire_coral", "horn_coral", "tube_coral")
# the same that lint.access_issues demands in the other templates: none of this may be left outside the walkthrough
ACCESSIBLE = ("ladder", "cyan_bed", "chest", "trapped_chest", "barrel", "lectern", "lever")


def accessible_blocks(m, out, seen):
    """Ladders, beds, chests, barrels, lecterns and levers, and both faces of each door, reachable."""
    wrong = {}
    for (x, y, z), (st, _) in m.blocks.items():
        b = block_name(st)
        if b.endswith("_door") and "half=lower" in st:
            f = st.split("facing=")[1].split(",")[0].rstrip("]")
            dx, dz = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[f]
            if (x + dx, y, z + dz) not in seen or (x - dx, y, z - dz) not in seen:
                wrong.setdefault("puerta sin salida o sin acceso", []).append((x, y, z))
        elif b in ACCESSIBLE and not any(p in seen for p in [(x, y, z)] + [(x + a, y + c, z + d) for a, c, d in NEIGHBORS]):
            wrong.setdefault(b + " inaccesible", []).append((x, y, z))
    for what, ps in wrong.items():
        out.append(f"{what}: {len(ps)}, p. ej. {ps[:3]}")


def jigsaws(tiles, out):
    """No later block has overwritten a jigsaw (the same check as lint.support_issues)."""
    for t in tiles:
        for j in t.jigsaws:
            if block_name(t.get(*j["pos"]) or "air") != "jigsaw":
                out.append(f"jigsaw sobrescrito en {t.name} {j['pos']}")


def items(m, out):
    for (x, y, z), (st, nbt) in m.blocks.items():
        for it in (nbt or {}).get("Items", ()):
            if it["id"].replace("minecraft:", "") not in validate.ITEMS:
                out.append(f"objeto inexistente {it['id']} en {(x, y, z)}")
            if not 0 <= int(it["Slot"]) < 27:
                out.append(f"hueco de cofre fuera de rango en {(x, y, z)}")


def state(m):
    """Percentage of the street-level built surface that is in ruins (lots, districts and wall)."""
    ruin_piece = total = 0
    for (n, x1, y1, z1, x2, y2, z2, r) in m.sites:
        if y2 <= U.FLOOR or n in ("nudo", "barco"):
            continue
        a = (x2 - x1 + 1) * (z2 - z1 + 1)
        total += a
        ruin_piece += a if r else 0
    return 100.0 * ruin_piece / max(total, 1)


def audit_it(m):
    out = []
    watertightness(m, out)
    supports(m, out)
    seen = reachable(m)
    accesses(m, out, seen)
    accessible_blocks(m, out, seen)
    items(m, out)
    pct = state(m)
    if not 15.0 <= pct <= 20.0:
        out.append(f"superficie en ruinas {pct:.1f} % (debe quedar entre 15 y 20)")
    m.reachable = seen
    m.ruin_pct = pct
    return out
