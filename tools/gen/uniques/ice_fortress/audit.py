"""Fortress-specific checks: redstone at rest and when triggered, open view for the walkthrough,
block light (ice that melts, dark generators), snow peaks and state of wear."""
import copy
from collections import deque
from core import parse_state, state_str
from lint import bname, passable, top_height
from .._common import redstone

N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
HOR = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
MECH = ("piston", "sticky_piston", "dispenser", "dropper", "iron_door", "iron_trapdoor", "redstone_lamp")


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def props(st):
    return parse_state(st)[1]


def conductor(st):
    return st is not None and not passable(st) and top_height(st) == 1.0 and not any(
        k in st for k in ("stairs", "slab", "chest", "spawner", "lantern", "campfire", "glass", "barrel", "dispenser",
                          "piston", "lever", "redstone", "fence", "_wall", "pane", "bars", "bed", "skull", "pot",
                          "lectern", "cauldron", "grindstone", "lightning_rod", "smoker", "crafting"))


class _View:
    def __init__(self, blocks):
        self.blocks = blocks

    def get(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None


def simulate(blocks, extra_on=()):
    """Returns (dust power, {mechanism: powered}) with the shared simulator (_common.redstone.Sim).
    extra_on: positions of pressed plates or hooks."""
    sim = redstone.Sim(_View(blocks), {p: True for p in extra_on})
    return dict(sim.wire), {p: sim.powered(p) for p, (st, _) in blocks.items() if bname(st) in MECH}


def check_redstone(t):
    errs = []
    blocks = t.blocks
    dust, powered = simulate(blocks)
    for p, v in dust.items():
        if int(props(blocks[p][0])["power"]) != v:
            errs.append(("dust with stored power different from the computed one", p))
    for p, on in powered.items():
        st = blocks[p][0]
        b, pr = bname(st), props(st)
        if "piston" in b:
            if (pr["extended"] == "true") != on:
                errs.append(("extended piston unpowered or the other way around", p))
            if pr["extended"] == "true":
                h = blocks.get(add(p, HOR[pr["facing"]]), (None,))[0]
                if bname(h) != "piston_head" or props(h)["facing"] != pr["facing"] or \
                        props(h)["type"] != ("sticky" if b == "sticky_piston" else "normal"):
                    errs.append(("extended piston without its head", p))
        elif b in ("dispenser", "dropper"):
            if on or pr["triggered"] != "false":
                errs.append(("dispensador alimentado en reposo", p))
    # each trap fires at least one dispenser
    for p, (st, _) in blocks.items():
        if bname(st) in ("tripwire_hook", "stone_pressure_plate"):
            if props(st).get("powered") != "false":
                errs.append(("trampa armada en estado pulsado", p))
            _, pw = simulate(blocks, extra_on={p})
            if not any(v and bname(blocks[q][0]) == "dispenser" for q, v in pw.items()):
                errs.append(("trap that fires no dispenser", p))
    return errs


def opened(t):
    """View of the template with all levers off and the pistons retracted (secret doors open)."""
    v = copy.copy(t)
    v.blocks = dict(t.blocks)
    v.jigsaws = t.jigsaws
    for p, (st, n) in list(v.blocks.items()):
        if bname(st) == "lever":
            v.blocks[p] = (st.replace("powered=true", "powered=false"), n)
    _, powered = simulate(v.blocks)
    moved = []
    for p, on in powered.items():
        st = v.blocks[p][0]
        if bname(st) == "sticky_piston" and not on and "extended=true" in st:
            d = HOR[props(st)["facing"]]
            head, front = add(p, d), add(p, (2 * d[0], 2 * d[1], 2 * d[2]))
            v.blocks[p] = (st.replace("extended=true", "extended=false"), None)
            v.blocks[head] = v.blocks[front]
            v.blocks[front] = ("minecraft:air", None)
            moved.append(front)
    return v, moved


# ------------------------------------------------------------------ luz
LIGHT = {"lantern": 15, "campfire": 15, "soul_lantern": 10, "soul_campfire": 10, "torch": 14, "wall_torch": 14,
         "glowstone": 15, "sea_lantern": 15}


def opaque(st):
    return conductor(st) or bname(st) in ("spawner",) and False


def block_light(t):
    lvl = {}
    q = deque()
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        e = LIGHT.get(b, 0)
        if b == "candle" and "lit=true" in st:
            e = 3 * int(props(st)["candles"])
        if b == "campfire" and "lit=false" in st:
            e = 0
        if e:
            lvl[p] = e
            q.append(p)
    while q:
        p = q.popleft()
        for d in N6:
            n = add(p, d)
            st = t.get(*n)
            if st is None or opaque(st):
                continue
            if lvl.get(n, 0) < lvl[p] - 1:
                lvl[n] = lvl[p] - 1
                q.append(n)
    return lvl


def check_light(t):
    errs, lvl = [], block_light(t)
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in ("ice", "snow") and lvl.get(p, 0) > 11:
            errs.append((b + " that melts in the light", p))
        if b == "spawner":
            near = max(lvl.get(add(p, (dx, dy, dz)), 0) for dx in range(-4, 5) for dy in range(0, 3) for dz in range(-4, 5))
            if near > 0:
                errs.append(("generator with block light nearby", p))
        if b == "snow_block" and (t.get(p[0], p[1] + 1, p[2]) in (None, "minecraft:air")):
            errs.append(("snow block as a peak (ice spikes spawn)", p))
    return errs, lvl


# ------------------------------------------------------------------ state of wear
DECAY = {"stone_bricks": 0.2, "stone_brick_wall": 0.3, "polished_diorite": 0.2}


def condition(t, ruined):
    """Estimate of the damaged surface in view: processor (expected value) + hand-made ruins."""
    g = t.get
    seen, q = set(), deque()
    x0, y0, z0, x1, y1, z1 = t.bounds()
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            q.append((x, y1, z))
            seen.add((x, y1, z))
    while q:                                         # outside air, from the sky
        p = q.popleft()
        for d in N6:
            n = add(p, d)
            if n in seen or not (x0 <= n[0] <= x1 and y0 <= n[1] <= y1 and z0 <= n[2] <= z1):
                continue
            if passable(g(*n)) or not conductor(g(*n)):
                seen.add(n)
                q.append(n)
    surf, bad = 0, 0.0
    for p, (st, _) in t.blocks.items():
        if passable(st) or not any(add(p, d) in seen for d in N6):
            continue
        surf += 1
        bad += DECAY.get(bname(st), 0.0)
    nearby = sum(1 for p in ruined if any(add(p, d) in seen for d in N6) or p in seen)
    return surf, (bad + nearby) / max(surf, 1)
