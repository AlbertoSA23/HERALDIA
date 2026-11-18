"""Aqueduct's own audit on the complete assembled structure (global coordinates).

Walkthrough with the puzzles closed and solved, nothing floating, simulated redstone, ruin percentage and
floor plans. `python3 -m uniques.aqueduct.auditoria <folder>` (from tools/gen) writes floor plans and renders."""
import os, sys
from collections import deque
from core import Template, parse_state
import lint
from uniques._common import redstone as R


def name(st):
    return R.bn(st) or "air"

ENTRANCE = (47, 0, 98)          # outside the south door


def variant(o, mode):
    """Copy of the global template in a puzzle state: 'cerrado', 'p1' (castellum open) or 'resuelto'."""
    t = Template("acueducto/" + mode)
    t.blocks = dict(o.t.blocks)
    r = o.red

    def put(p, st):
        t.blocks[p] = (st, None)
    if mode in ("p1", "resuelto"):
        for p in r["puerta_1"]:
            x, y, z = p
            put((x, y, z), "minecraft:air")
            put((x, y, z + 1), "minecraft:chiseled_sandstone")
            put((x, y, z + 2), "minecraft:sticky_piston[extended=false,facing=north]")
    if mode != "resuelto":
        for p in r["puerta_2"]:
            put(p, "minecraft:stone")          # the iron door cannot be opened by hand
        put(r["reja"], o.t.blocks[r["reja"]][0])
    else:
        put(r["reja"], "minecraft:ladder[facing=north,waterlogged=false]")
        put(r["trampilla_favissa"], "minecraft:ladder[facing=south,waterlogged=false]")
    x0, y0, z0, x1, y1, z1 = o.t.bounds()
    for x in range(x0 - 1, x1 + 2):          # explicit natural ground under what has no subsurface
        for z in range(z0 - 1, z1 + 2):
            for y in range(y0 - 1, 0):
                if (x, y, z) not in t.blocks:
                    t.blocks[(x, y, z)] = ("minecraft:dirt", None)
    t.jigsaws = [dict(pos=ENTRANCE, name="heraldia:entrance", orientation="north_up")]
    return t


def reachable(t):
    return lint.walk(t)


def floating_blocks(o):
    """Blocks not connected to the ground (y <= 0) by a chain of neighbors."""
    b = {p for p, (st, _) in o.t.blocks.items() if name(st) != "air"}
    seen = {p for p in b if p[1] <= 0}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in b and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(b - seen)


def redstone(o):
    """Checks puzzles and traps with the common simulator; returns the list of failures."""
    r = o.red
    errs, sim = R.check_static(o.t)
    A, I, T = r["palanca_A"], r["palanca_I"], r["palanca_T"]
    for a in (0, 1):
        for i in (0, 1):
            for tt in (0, 1):
                s = R.Sim(o.t, {A: bool(a), I: bool(i), T: bool(tt)})
                p1, p2 = s.powered(r["piston_1"]), s.powered(r["piston_2"])
                if p1 != p2:
                    errs.append(f"puzzle 1: the pistons do not move together ({a}{i}{tt})")
                if p1 != (not (a and not i and tt)):
                    errs.append(f"puzle 1: AQVA={a} IGNIS={i} TERRA={tt} -> {'cerrada' if p1 else 'abierta'}")
    mechs = r["dispensadores_1"] + r["dispensadores_28"] + r["dispensadores_30"] + r["puerta_2"] + [r["reja"]]
    errs += [f"{p} receives a signal without anyone activating it" for p in mechs if sim.powered(p)]
    checks = [({r["gancho_O"]: True, r["gancho_E"]: True}, r["dispensadores_1"]),
              ({r["placa_28"]: True}, r["dispensadores_28"]), ({r["placa_30"]: True}, r["dispensadores_30"]),
              ({r["placa_ofrenda"]: True}, r["puerta_2"][:1]), ({r["boton"]: True}, r["puerta_2"][:1]),
              ({r["palanca_reja"]: True}, [r["reja"]])]
    for inp, outs in checks:
        s = R.Sim(o.t, inp)
        errs += [f"{list(inp)} no activa {p}" for p in outs if not s.powered(p)]
    return errs


def stabilize(o):
    """Stable shape and signal level of the dust, computed like the game (everything off)."""
    R.wire_shapes(o.t)
    R.set_wire_power(o.t)


def audit_it(o):
    errs = []
    if not 0.15 <= o.ruin_piece / o.area <= 0.20:
        errs.append(f"ruin {o.ruin_piece}/{o.area} = {o.ruin_piece / o.area:.1%} outside 15-20 %")
    errs += [f"flotando: {p} {o.t.get(*p)}" for p in floating_blocks(o)[:10]]
    errs += redstone(o)
    res = variant(o, "resuelto")
    access = [i for i in lint.access_issues(res) + lint.support_issues(res) if i[1] != ENTRANCE]
    errs += [f"{m} {p}" for m, p in access[:20]]
    cells = reachable(res)
    near = lambda p, rr=1: any((p[0] + dx, p[1] + dy, p[2] + dz) in cells for dx in range(-rr, rr + 1)
                               for dz in range(-rr, rr + 1) for dy in (-1, 0, 1) if abs(dx) + abs(dz) <= rr)
    for p, (st, _) in o.t.blocks.items():
        n = name(st)
        if n in ("lever", "stone_button", "spawner") and not near(p, 2 if n == "spawner" else 1):
            errs.append(f"{n} inaccesible {p}")
    for x, y, z, nbt in o.t.entities:
        if not near((x, y, z)):
            errs.append(f"unreachable guardian {(x, y, z)}")
    prem = o.red["premium"]
    p1 = reachable(variant(o, "p1"))
    closed = reachable(variant(o, "cerrado"))
    if any(c[1] < 0 and 64 <= c[0] <= 92 and -5 <= c[2] <= 44 for c in closed):
        errs.append("the sewers are reached without solving puzzle 1")
    for state_name, cs in (("cerrado", closed), ("p1", p1)):
        if any(abs(c[0] - prem[0]) + abs(c[2] - prem[2]) <= 1 and abs(c[1] - prem[1]) <= 1 for c in cs):
            errs.append(f"the premium chest is reached with the puzzles in state {state_name}")
    return errs, (closed, res, cells)


LEVELS = [("ciudad", 1, (-1, 5, 96, 98)), ("castellum_p1", 8, (72, -12, 86, 4)),
           ("castellum_azotea", 15, (72, -12, 86, 4)), ("templo_y_caldarium", 4, (40, 24, 92, 46)),
           ("cloacas", -8, (64, -5, 92, 44)), ("cisterna", -7, (33, 42, 63, 60))]


def blueprints(o, closed, cells, out):
    os.makedirs(out, exist_ok=True)
    marks = {"chest": "C", "barrel": "B", "spawner": "G", "_door": "P", "ladder": "E", "_stairs": "e",
             "lever": "L", "pressure_plate": "T", "tripwire": "T", "dispenser": "D", "water": "~", "piston": "M"}
    for label, y, (x0, z0, x1, z1) in LEVELS:
        lines = [f"# {label}: feet at y = {y}. · reachable on foot from the south door; or only with the puzzles solved;",
                 "# C chest, B barrel, G spawner, P door, E ladder, e step, L lever,",
                 "# T trap plate or tripwire, D dispenser, M piston, ~ water, # wall. North up; x from left to right.", ""]
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                ch = None
                for yy in (y, y - 1):
                    n = name(o.t.get(x, yy, z))
                    for k, m in marks.items():
                        if k in n and ch is None:
                            ch = m
                if ch is None:
                    c = next(((x, yy, z) for yy in (y, y - 1, y + 1) if (x, yy, z) in cells), None)
                    if c:
                        ch = "·" if c in closed else "o"
                    elif name(o.t.get(x, y, z)) != "air" and o.t.get(x, y, z):
                        ch = "#"
                    else:
                        ch = " "
                row += ch
            lines.append(row.rstrip())
        with open(os.path.join(out, f"plano_{label}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def renders(o, out):
    import render
    full = Template("r")
    full.blocks = {p: v for p, v in o.t.blocks.items() if p[1] >= 0}
    full.normalize()
    render.render(full, os.path.join(out, "render_conjunto.png"), scale=2)
    city = Template("c")
    city.blocks = {p: v for p, v in o.t.blocks.items() if 0 <= p[1] <= 5 and p[2] >= -12}
    city.normalize()
    render.render(city, os.path.join(out, "render_ciudad_sin_tejados.png"), scale=3)


if __name__ == "__main__":
    from . import world
    o = world()
    errs, (closed, res, cells) = audit_it(o)
    print("\n".join(errs) or "audit OK", f"ruina {o.ruin_piece / o.area:.1%}")
    blueprints(o, closed, cells, sys.argv[1])
    renders(o, sys.argv[1])
