"""The palace's own checks (besides lint.py): redstone, puzzles, walkthrough, supports and ruin.

Each function returns a list of error texts; build() dumps them into reg.warnings, so
generation fails if any does not pass."""
from collections import deque
from core import parse_state
import lint
from lint import bname, passable
from .ruins import wear_probability
from .._common import redstone

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
VEC = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1), "up": (0, 1, 0), "down": (0, -1, 0)}


def check_redstone(o):
    """With the common model (_common.redstone): stable placed state and effect of each lever, wire and plate."""
    t, errs = o.t, list(redstone.check_static(o.t)[0])
    mech = o.mech
    levers = {m["label"]: m for m in mech if m["kind"] == "palanca"}
    groups = {}
    for m in mech:
        if m["kind"] == "puerta":
            groups.setdefault(m["label"].split(" ")[0], []).append(m)
    pistons = lambda ms: [p for m in ms for p in m["pistons"]]
    for g, ms in groups.items():
        own = [lv["pos"] for name, lv in levers.items() if name.split(" ")[0] == g]
        if not own:
            errs.append(f"door {g} has no lever")
            continue
        sim = redstone.Sim(t, {p: False for p in own})
        errs += [f"door {g}: piston {p} still powered with the levers off" for p in pistons(ms) if sim.powered(p)]
        if len(own) > 1:
            for lv in own:
                if not any(redstone.Sim(t, {lv: False}).powered(p) for p in pistons(ms)):
                    errs.append(f"door {g}: it opens completely with a single lever {lv}")
        errs += [f"door {g}: the gap {d} is not free when open" for m in ms for d in m["door"] if o.lint_open.get(d) != "air"]
    for m in mech:
        if m["kind"] == "cable":
            z, x0, x1, y = m["z"], m["x0"], m["x1"], m["y"]
            sim = redstone.Sim(t, {(x0 + 1, y, z): True, (x1 - 1, y, z): True})
            for d in ((x0, y + 1, z), (x1, y + 1, z)):
                if bname(t.get(*d)) != "dispenser" or not sim.powered(d):
                    errs.append(f"wire {m['label']}: the dispenser {d} is not activated")
        elif m["kind"] == "placa":
            sim = redstone.Sim(t, {m["plate"]: True})
            errs += [f"plate {m['label']}: dispenser {d} does not activate" for d in m["disp"]
                     if bname(t.get(*d)) != "dispenser" or not sim.powered(d)]
        elif m["kind"] == "senuelo":
            sim = redstone.Sim(t, {m["lever"]: True, **{lv["pos"]: False for lv in levers.values() if lv["pos"] != m["lever"]}})
            if not sim.powered(m["disp"]):
                errs.append("decoy lever has no effect")
            if any(sim.powered(p) for ms in groups.values() for p in pistons(ms)):
                errs.append("the decoy lever powers a door")
    # each trap dispenser fires towards a free cell
    for p, (st, _) in t.blocks.items():
        if bname(st) == "dispenser":
            f = parse_state(st)[1]["facing"]
            q = (p[0] + VEC[f][0], p[1] + VEC[f][1], p[2] + VEC[f][2])
            if not passable(t.get(*q)) and bname(t.get(*q)) != "stone_pressure_plate":
                errs.append(f"dispenser {p} fires into a wall")
    return errs


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def near(cells, p, r=1):
    x, y, z = p
    return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
               for dy in (-1, 0, 1) if abs(dx) + abs(dz) <= r)


class Closed:
    """View of the template without the mechanisms open (everything closed, as generated)."""
    def __init__(self, t):
        self.__dict__.update(t.__dict__)
        self.lint_open = {}
        self.get = t.get
        self.bounds = t.bounds


def check_walk(o):
    t, errs = o.t, []
    opened = set(lint.walk(t))
    closed = set(lint.walk(Closed(t)))
    for p in o.secret:
        if near(closed, p):
            errs.append(f"{p} is reached without solving any puzzle")
        if not near(opened, p):
            errs.append(f"{p} is not reached even with the puzzles solved")
    for (p, tbl) in o.chests:
        if not near(opened, p):
            errs.append(f"chest {tbl} {p} inaccessible")
    for m in o.mech:
        if m["kind"] == "palanca" and not near(opened, m["pos"]):
            errs.append(f"lever {m['label']} unreachable")
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in ("trapped_chest", "stone_button", "loom", "smoker") and not near(opened, p):
            errs.append(f"{b} {p} inaccesible")
    if not near(opened, o.guardian, r=0):
        errs.append("the guardian is not in a reachable cell")
    return errs, opened


def check_floating(o):
    """Nothing floating: every block (water included) attached by faces to the base y = 0."""
    t = o.t
    solid = {p for p, (st, _) in t.blocks.items() if bname(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] == 0}
    q = deque(seen)
    while q:
        p = q.popleft()
        for d in DIRS6:
            n = add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    loose = sorted(solid - seen)
    return [f"{len(loose)} bloques flotando, p. ej. {loose[:5]} ({t.get(*loose[0])})"] if loose else []


def exposed(t, keys):
    out = set()
    for p in keys:
        st = t.get(*p)
        if st is None or bname(st) == "air":
            continue
        for d in DIRS6:
            n = t.get(*add(p, d))
            if n is None or passable(n) or bname(n) == "air":
                if add(p, d)[1] >= 0:
                    out.add(p)
                    break
    return out


def ruin_ratio(good, ruined):
    """Fraction of the exposed surface in ruin: blocks removed or changed by the ruin, plus the
    expected wear of the processor on what remains."""
    exp_good = exposed(good, good.blocks)
    changed = sum(1 for p in exp_good if ruined.get(*p) != good.get(*p))
    # rubble, ivy and moss added: each one covers one face of the surface
    added = sum(1 for p, (st, _) in ruined.blocks.items() if bname(st) not in ("air", "jigsaw", "iron_chain")
                and good.get(*p) in (None, "minecraft:air"))
    wear = sum(wear_probability(ruined.get(*p)) for p in exp_good if ruined.get(*p) == good.get(*p))
    return (changed + added + wear) / max(1, len(exp_good)), len(exp_good), changed + added, wear


def check_ruin(good, ruined):
    r, n, c, w = ruin_ratio(good, ruined)
    if not 0.15 <= r <= 0.20:
        return [f"ruin {r:.1%} outside 15-20 % (surface {n}, removed/changed {c}, wear {w:.0f})"]
    return []
