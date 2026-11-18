"""Cathedral's own audit (condition for generating): walkthrough from the entrance with the mechanisms
open, access to chests, doors, stairs, levers and spawners; rooms without access; floating blocks;
light in the covered surface areas; static consistency of the redstone; proportion of ruin."""
from collections import deque
from lint import passable as _passable, top_height as _top, bname, prop, climbable, FACE
from .base import s

START = (-1, 0, 30)
FURNITURE = {"bookshelf", "chest", "barrel", "spawner", "note_block", "dispenser", "smooth_quartz", "gold_block",
             "cartography_table", "spruce_planks", "chiseled_stone_bricks", "water_cauldron", "bone_block", "polished_diorite"}
EXTRA_PASS = {"lever", "tripwire", "redstone_wire", "tripwire_hook", "redstone_wall_torch", "redstone_torch"}


def passable(st):
    return _passable(st) or bname(st) in EXTRA_PASS


def top_height(st):
    if st is not None and bname(st) in EXTRA_PASS:
        return None
    return _top(st)


def opened(c):
    """View of the model with the mechanisms activated: piston doors open and trapdoors open."""
    over = {}
    for m in c.mech:
        if m["tipo"] == "puerta de pistones":
            for p in m["puerta"]:
                over[p] = "minecraft:air"
        elif m["tipo"] == "trampilla":
            p = m["trampilla"]
            over[p] = c.t.get(*p).replace("open=false", "open=true")
    blocks = c.t.blocks

    def g(x, y, z):
        p = (x, y, z)
        if p in over:
            return over[p]
        b = blocks.get(p)
        return b[0] if b else None
    return g


is_ladder = climbable


def walk(c, g):
    xs = [p[0] for p in c.t.blocks]; zs = [p[2] for p in c.t.blocks]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)

    def surf(x, y, z, mdx, mdz):
        st = g(x, y, z)
        h = top_height(st)
        if st is not None and bname(st).endswith("_stairs") and "half=bottom" in st:
            fx, fz = FACE[prop(st, "facing")]
            return (y + 0.5 if (mdx, mdz) == (fx, fz) else y + 1.0, y + 1.0)
        if h is not None and h <= 0.6:
            return (y + h, y + h)
        if h is not None:
            return None
        below = g(x, y - 1, z)
        if below is None:
            return (float(y), float(y)) if y == 0 else None
        hb = top_height(below)
        if hb is None:
            return (float(y), float(y)) if is_ladder(g, x, y - 1, z) or bname(below) == "water" else None
        if hb != 1.0 or (bname(below).endswith("_stairs") and "half=bottom" in below):
            return None
        return (float(y), float(y))

    def headroom(x, y, z, sv):
        top = sv + 1.8
        cy = y + 1 if sv >= y + 1 else y + 1
        while cy < top:
            st = g(x, cy, z)
            if not passable(st):
                low = cy + (0.5 if ("half=top" in st or "type=top" in st) else 0.0)
                if low < top:
                    return False
            cy += 1
        return True

    seen = {START: 0.0}
    q = deque([START])
    while q:
        x, y, z = q.popleft()
        sv = seen[(x, y, z)]
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if not (x0 - 2 <= nx <= x1 + 2 and z0 - 2 <= nz <= z1 + 2):
                continue
            for ny in range(y + 2, y - 5, -1):
                r = surf(nx, ny, nz, dx, dz)
                if r is None:
                    continue
                enter, stand = r
                if enter - sv > 0.6 or stand > sv + 1.01:
                    break
                cell = (nx, ny if stand < ny + 1 else ny + 1, nz)
                if headroom(cell[0], cell[1], nz, stand) and cell not in seen:
                    seen[cell] = stand
                    q.append(cell)
                break
        lad = is_ladder(g, x, y, z) or is_ladder(g, x, y - 1, z)
        if lad:
            for ny in (y + 1, y - 1):
                st = g(x, ny, z)
                if (is_ladder(g, x, ny, z) or (is_ladder(g, x, y, z) and passable(st))) and (x, ny, z) not in seen:
                    seen[(x, ny, z)] = float(ny)
                    q.append((x, ny, z))
    return seen


def near(cells, x, y, z, r=1):
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            for dy in (-1, 0, 1):
                if abs(dx) + abs(dz) <= r and (x + dx, y + dy, z + dz) in cells:
                    return True
    return False


def access(c, g, cells):
    out = []
    for (pos, tbl, site) in c.chests:
        if not near(cells, *pos):
            out.append(f"chest unreachable ({site}) at {pos}")
    for (pos, mob) in c.spawners:
        if not near(cells, *pos, r=3):
            out.append(f"{mob} spawner unreachable at {pos}")
    for (x, y, z), (st, _) in c.t.blocks.items():
        b = bname(st)
        if b.endswith("_door") and prop(st, "half") == "lower":
            dx, dz = (0, 1) if prop(st, "facing") in ("north", "south") else (1, 0)
            a = any((x + dx, y + k, z + dz) in cells for k in (0, -1))
            bb = any((x - dx, y + k, z - dz) in cells for k in (0, -1))
            if not (a and bb):
                out.append(f"door without exit or access at {(x, y, z)}")
        elif b in ("lever", "bell", "lectern"):
            if not any(near(cells, x, y - k, z, r=2) for k in range(0, 5)):
                out.append(f"{b} unreachable at {(x, y, z)}")
        elif b == "ladder" and (x, y, z) not in cells:
            out.append(f"ladder unreachable at {(x, y, z)}")
    for (x, y, z) in c.flights:
        st = g(x, y, z)
        ok = (x, y, z) in cells or (x, y + 1, z) in cells
        if not ok:
            out.append(f"step unreachable at {(x, y, z)} ({bname(st)})")
    return out


def standable_covered(c, g):
    """Cells where a standing player fits, with a ceiling above (rooms), to detect those with no access."""
    res = set()
    for (x, y, z), (st, _) in c.t.blocks.items():
        if bname(st) != "air" or (x, y, z) in c.ruin:
            continue
        below = g(x, y - 1, z)
        if below is None or top_height(below) != 1.0 or bname(below).endswith(("_stairs", "_log")) or \
                bname(below) in FURNITURE:
            continue
        if not (passable(g(x, y + 1, z))):
            continue
        if any(g(x, yy, z) is not None and not passable(g(x, yy, z)) for yy in range(y + 2, y + 12)):
            res.add((x, y, z))
    return res


def floating(c):
    """Components of blocks (6-neighborhood) that do not touch the ground (y <= 0): they would float."""
    solid = {p for p, (st, _) in c.t.blocks.items() if bname(st) != "air"}
    seen, out = set(), []
    for p in solid:
        if p in seen:
            continue
        comp, q, grounded = [], deque([p]), False
        seen.add(p)
        while q:
            x, y, z = q.popleft()
            comp.append((x, y, z))
            if y <= 0:
                grounded = True
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + d[0], y + d[1], z + d[2])
                if n in solid and n not in seen:
                    seen.add(n)
                    q.append(n)
        if not grounded:
            out.append(f"{len(comp)} blocks floating near {min(comp)} ({bname(c.t.get(*min(comp)))})")
    return out


LIGHT = {"lantern": 15, "soul_lantern": 10, "torch": 14, "wall_torch": 14, "redstone_torch": 7, "redstone_wall_torch": 7,
         "glowstone": 15, "sea_lantern": 15, "lava": 15}


def opaque(st):
    if st is None:
        return False
    b = bname(st)
    if b in ("air", "water") or passable(st) or "pane" in b or "glass" in b or b.endswith(("_slab", "_stairs", "_wall", "_fence",
                                                                                             "_leaves", "_bars", "_trapdoor")):
        return False
    return top_height(st) == 1.0


def light(c, cells):
    g = lambda x, y, z: c.t.get(x, y, z)
    lv, q = {}, deque()
    for (x, y, z), (st, _) in c.t.blocks.items():
        b = bname(st)
        v = LIGHT.get(b, 0)
        if b == "candle" and "lit=true" in st:
            v = 3 * int(prop(st, "candles"))
        if v:
            lv[(x, y, z)] = v
            q.append((x, y, z))
    while q:
        p = q.popleft()
        v = lv[p] - 1
        if v <= 0:
            continue
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if opaque(g(*n)) or lv.get(n, 0) >= v:
                continue
            if g(*n) is None and not (-10 < n[1] < 80):
                continue
            lv[n] = v
            q.append(n)
    dark = []
    doors = {q for m in c.mech for q in m.get("puerta", [])}
    for (x, y, z) in cells:
        if y < 1 or (x, y, z) in doors:
            continue
        covered = all(any(opaque(g(x + a, yy, z + b)) for yy in range(y + 2, 80))
                      for (a, b) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
        if covered and lv.get((x, y, z), 0) == 0:
            dark.append((x, y, z))
    return dark, lv


def redstone(c):
    """Static consistency when placed (without block updates): closed rest state and open solution."""
    out = []
    g = c.t.get
    for m in c.mech:
        if m["tipo"] == "puerta de pistones":
            for p in m["pistones"]:
                if "extended=true" not in (g(*p) or ""):
                    out.append(f"{m['sitio']}: piston not extended at {p}")
            for p in m["cabezas"]:
                if bname(g(*p)) != "piston_head":
                    out.append(f"{m['sitio']}: missing piston head at {p}")
            for p in m["puerta"]:
                if bname(g(*p)) in ("air", None):
                    out.append(f"{m['sitio']}: gap in the door {p}")
            for p in m["antorchas"]:
                if "lit=true" not in g(*p):
                    out.append(f"{m['sitio']}: torch off at {p}")
            for (lp, bp) in m["palancas"] + m["falsas"]:
                if "powered=false" not in g(*lp) or bname(g(*bp)) in ("air", None) or not opaque(g(*bp)):
                    out.append(f"{m['sitio']}: lever {lp} badly attached")
            for (p, pw) in m["polvo"]:
                if pw <= 0 or f"power={pw}" not in g(*p) or not opaque(g(p[0], p[1] - 1, p[2])):
                    out.append(f"{m['sitio']}: dust without signal or support at {p}")
            first = m["polvo"][0][0] if m["polvo"] else m["pistones"][1]
            pu = m["pistones"][1]
            if m["polvo"] and (abs(first[0] - pu[0]) + abs(first[2] - pu[2]) != 1 or first[1] != pu[1]):
                out.append(f"{m['sitio']}: the dust does not reach the upper piston")
            # solution: with the correct ones activated the torches turn off; the fake one feeds the line if activated
            line = {p for (p, _) in m["polvo"]}
            segment, everything = {first}, [first]          # continuous run of dust that reaches the piston (the torches cut it)
            while everything:
                p = everything.pop()
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (p[0] + d[0], p[1], p[2] + d[1])
                    if n in line and n not in segment:
                        segment.add(n)
                        everything.append(n)
            for (lp, bp) in m["falsas"]:
                if not any(abs(bp[0] - p[0]) + abs(bp[2] - p[2]) == 1 and bp[1] == p[1] for p in segment):
                    out.append(f"{m['sitio']}: the fake lever {lp} does not power the stretch that reaches the piston")
            for (lp, bp) in m["palancas"]:
                t = (2 * bp[0] - lp[0], bp[1], 2 * bp[2] - lp[2])
                if t not in m["antorchas"]:
                    out.append(f"{m['sitio']}: the lever {lp} turns off no torch")
                if any(abs(bp[0] - p[0]) + abs(bp[2] - p[2]) == 1 and bp[1] == p[1] for p in line):
                    out.append(f"{m['sitio']}: the block of the lever {lp} touches the line")
        elif m["tipo"] == "trampilla":
            if "open=false" not in g(*m["trampilla"]) or "powered=false" not in g(*m["palanca"]):
                out.append("altar trapdoor: inconsistent initial state")
            a, t = m["apoyo"], m["trampilla"]
            if abs(a[0] - t[0]) + abs(a[1] - t[1]) + abs(a[2] - t[2]) != 1 or not opaque(g(*a)):
                out.append("altar trapdoor: the lever does not power it")
        else:
            for p in m["dispensadores"]:
                if bname(g(*p)) != "dispenser" or "triggered=false" not in g(*p):
                    out.append(f"{m['sitio']}: dispenser {p} misconfigured")
                fx, fz = FACE[prop(g(*p), "facing")]
                if g(p[0] + fx, p[1], p[2] + fz) not in (None, "minecraft:air") and bname(g(p[0] + fx, p[1], p[2] + fz)) not in (
                        "tripwire", "stone_pressure_plate") and not bname(g(p[0] + fx, p[1], p[2] + fz)).endswith("_sign"):
                    out.append(f"{m['sitio']}: the dispenser {p} fires into a block")
            src = m.get("ganchos", []) + [m[k] for k in ("placa", "apoyo") if k in m]
            for p in m["dispensadores"]:
                if not any(abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) == 1 for q in src):
                    out.append(f"{m['sitio']}: the dispenser {p} is not next to the hook or the plate")
    return out


def common_redstone(c):
    """Common simulator (_comun/redstone.py): stable placed state and, per piston door, that only the solution
    opens it (the 2^n lever combinations, fake ones included)."""

    from .._common.redstone import check_static, check_puzzle
    from core import Template
    t = Template("redstone")
    zone = set()
    for m in c.mech:
        for k in ("pistones", "cabezas", "antorchas", "puerta", "ganchos", "cable", "dispensadores"):
            zone.update(m.get(k, []))
        zone.update(p for p, _ in m.get("polvo", []))
        zone.update(p for pair in m.get("palancas", []) + m.get("falsas", []) for p in pair)
        zone.update(m[k] for k in ("trampilla", "palanca", "placa", "apoyo") if k in m)
    near = {(x + a, y + b, z + d) for (x, y, z) in zone for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)
            for d in (-2, -1, 0, 1, 2)}
    t.blocks = {p: c.t.blocks[p] for p in near if p in c.t.blocks}
    errs, _ = check_static(t)
    for m in c.mech:
        if m["tipo"] == "puerta de pistones":
            levers = [lp for lp, _ in m["palancas"]] + [lp for lp, _ in m["falsas"]]
            soln = [True] * len(m["palancas"]) + [False] * len(m["falsas"])
            errs += check_puzzle(t, m["sitio"], levers, soln, m["pistones"], opens_if="sin_potencia")
    return errs


def ruin_share(c):
    """Proportion of the exterior surface with damage (explicit or expected from the processors)."""
    from . import PROCESSORS
    probs = {}
    for r in PROCESSORS["processors"][0]["rules"]:
        b = r["input_predicate"]["block"]
        probs[b] = probs.get(b, 0) + r["input_predicate"]["probability"]
    g = c.t.get
    exposed, dmg = 0, 0.0
    for (x, y, z), (st, _) in c.t.blocks.items():
        if y < 0 or bname(st) == "air":
            continue
        if any(g(x + a, y + b, z + d) is None for (a, b, d) in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1))):
            exposed += 1
            dmg += probs.get("minecraft:" + bname(st), 0.0)
    explicit = sum(1 for p in c.ruin if p[1] >= 0)
    return (dmg + explicit) / max(1, exposed + explicit)


def clusters(cells):
    cells, out = set(cells), []
    while cells:
        p = cells.pop(); comp, q = [p], [p]
        while q:
            x, y, z = q.pop()
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                n = (x + d[0], y + d[1], z + d[2])
                if n in cells:
                    cells.discard(n); comp.append(n); q.append(n)
        out.append(comp)
    return sorted(out, key=len, reverse=True)


def audit(c, verbose=False):
    g = opened(c)
    cells = walk(c, g)
    probs = access(c, g, cells)
    rooms = standable_covered(c, g)
    lost = sorted(rooms - set(cells))
    for comp in [k for k in clusters(lost) if len(k) >= 3]:
        probs.append(f"unreachable room: {len(comp)} cells between {min(comp)} and {max(comp)}")
    probs += floating(c)
    dark, _ = light(c, set(cells))
    if dark:
        probs.append(f"{len(dark)} covered cells in darkness on the surface, e.g. {sorted(dark)[:8]}")
    probs += redstone(c)
    probs += common_redstone(c)
    share = ruin_share(c)
    if not 0.15 <= share <= 0.20:
        probs.append(f"ruin share {share:.1%} outside 15-20 %")
    c.audit_cells, c.audit_share = cells, share
    if verbose:
        print(f"reachable cells {len(cells)}, rooms {len(rooms)}, ruin {share:.1%}")
    return probs
