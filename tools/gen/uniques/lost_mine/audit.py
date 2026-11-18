"""Finishing and audit of the Lost Mine: redstone resting state, the needle puzzle (the minecart only
reaches the weighbridge with the right combination), the hatch and the secret office, the traps, the walkthrough with
the puzzles closed and solved (also strict, with no drops of more than one block and swimming), generator light,
the linings (no natural block in view inside), the closed shell (no dug-out gap touches the outside of the
template), the state of wear and the headframe.

preparar(obra, castillete) returns (errors, report); the errors go to reg.warnings and the compilation fails.
"""
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.pieces import connect, open_stairwells
from .._common.walkthrough import (lint_view, nearby_flag, floating_blocks, light, light_generator, View, strict_walk, no_return, processor,
                                expectation, open_up)
from . import tracks
from .construction import N6, NATURAL, SID

# Wear spread out; with the hand-made ruin, 15-20 % of the surface in view. Nothing that supports a mechanism
# falls: they only change appearance (mossy cobblestone and cracked brick conduct and get dragged just the same).
DECAY = [("stone_bricks", 0.25, "cracked_stone_bricks"), ("stone_bricks", 0.12, "mossy_stone_bricks"),
         ("cobblestone", 0.22, "mossy_cobblestone")]
PROCESSOR = processor(DECAY)
INTERIOR_NATURAL = tuple(b for b in NATURAL if b not in ("gravel", "sand"))   # rubble and lake bed: accepted


def prepare(construction, cast):
    t = construction.t
    fix_supports(t)
    connect(t)
    open_stairwells(t)
    errs = []
    rs.wire_shapes(t)
    e, _ = rs.check_static(t)
    errs += e
    m = construction.mech
    v = m["vias"]
    blocks = {p: st for p, (st, _) in t.blocks.items()}

    # puzzle 1: the needles; the weighbridge opens the hatch and nothing else opens it
    errs += tracks.check(t, v)
    for p in v["agujas"] + [v["bascula"], v["salida"]]:
        if not tracks.is_rail(blocks.get(p)):
            errs.append(f"missing track at {p}")
    sim_bas = rs.Sim(t, {v["bascula"]: True})
    open_bas = open_up(t, sim_bas)
    for p in v["puerta"]:
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the hatch is not closed when generated at {p}")
        if bn(open_bas.get(p)) != "air":
            errs.append(f"the minecart on the weighbridge does not open the hatch at {p}")
    for lv in v["palancas"] + [v["arranque"]]:
        if not all(rs.Sim(t, {lv: True}).powered(p) for p in v["pistones"]):
            errs.append(f"lever {lv} touches the hatch circuit")
    # puzzle 2: the foreman's office bookshelf
    desc_es = m["puerta_despacho"]
    open_des = open_up(t, rs.Sim(t, {desc_es["lever"]: True}))
    for p in (desc_es["door"], (desc_es["door"][0], desc_es["door"][1] + 1, desc_es["door"][2])):
        if bn(open_des.get(p)) != "air":
            errs.append(f"the lever does not open the office at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the office panel is not closed when generated at {p}")
    # traps: trap wire and plate over the dynamite, no signal at rest
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    idle = rs.Sim(t)
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"the trap wire does not activate dispenser {p}")
        if idle.powered(p):
            errs.append(f"dispenser with signal at rest {p}")
    if not rs.Sim(t, {m["placa_tnt"]: True}).powered(m["tnt"]):
        errs.append("the plate does not ignite the dynamite")
    if idle.powered(m["tnt"]):
        errs.append("dynamite with signal at rest")

    # walkthrough: public (puzzles closed) and solved (hatch and office open)
    trap = {p: None for p, st in blocks.items() if bn(st) == "tripwire"}
    resolved_map = dict(open_bas)
    for p, st in open_des.items():
        if blocks.get(p) != st:
            resolved_map[p] = st
    for p in set(blocks) - set(open_des):
        resolved_map.pop(p, None)
    entrance = (m["entrada"][0] + 2, 0, m["entrada"][2] + 3)
    pub = lint_view(t.blocks, trap, entrance)
    cells_pub = set(lint.walk(pub, extra_ground=False))
    soln_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in resolved_map.items()}
    solv = lint_view(soln_blocks, trap, entrance)
    cells = set(lint.walk(solv, extra_ground=False))
    submerged = {p for p, _ in construction.chests if "waterlogged=true" in blocks[p]}      # reached by diving (walking)
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        if pos in submerged or (msg.startswith("cadena sin enganche") and pos[1] == construction_top(construction)):
            continue                     # the shaft chain continues in the section above
        errs.append(f"{msg} en {pos}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {pos}")
    free = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in construction.hidden if free(q)]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"hidden area reachable without solving the puzzles {p}")
    for p in [q for q in construction.hidden_alcove if free(q)]:
        if p not in cells_pub:
            errs.append(f"the stash is not reachable behind the tapestry {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"spawner unreachable {p}")
    for p in v["palancas"] + [v["arranque"], desc_es["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"lever unreachable {p}")
    for p, _ in construction.chests:
        if p not in submerged and not nearby_flag(cells, p):
            errs.append(f"unreachable chest {p}")
    n_chests = len(construction.chests) + len(cast.chests)
    if not 15 <= n_chests <= 25:
        errs.append(f"{n_chests} chests (15-25 required)")
    # strict walkthrough (no drops of more than one block, swimming) and return to the entrance from anywhere
    x0, y0, z0, x1, y1, z1 = t.bounds()
    vv = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap})
    start = (entrance[0], 1, entrance[2])
    seen, edges = strict_walk(vv, start, (x0, x1, z0, z1), water=True)
    for c in no_return(edges, start)[:10]:
        errs.append(f"cell with no way back to the entrance {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p, 2):
            errs.append(f"chest unreachable without jumps {p}")
    if not any(c[0] == m["entrada"][0] and c[2] == m["entrada"][2] and c[1] >= 20 for c in seen):
        errs.append("the shaft ladder cannot be climbed all the way up")
    # light: the generators in the dark
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"{mob} generator with light nearby {p} ({light_generator(lv, p)})")
    # lining: no natural block faces a dry dug-out cell (springs, lichen, moss, clay)
    seen_all = 0
    for p, st in blocks.items():
        if bn(st) in INTERIOR_NATURAL:
            for (a, b, c) in N6:
                q = (p[0] + a, p[1] + b, p[2] + c)
                if q in construction.carved and bn(blocks.get(q)) in ("air", "water"):
                    seen_all += 1
                    if seen_all <= 3:
                        errs.append(f"natural block in view inside at {p} ({bn(st)})")
                    break
    # closed shell: no dug-out cell (nor what is in it) touches an unwritten cell
    open_ones = 0
    for p in construction.carved:
        for (a, b, c) in N6:
            q = (p[0] + a, p[1] + b, p[2] + c)
            if q not in t.blocks and not (q[1] > construction_top(construction) and abs(p[0] - m["eje"][0]) <= 2
                                           and abs(p[2] - m["eje"][2]) <= 2):
                open_ones += 1
                if open_ones <= 3:
                    errs.append(f"the shell does not close near {p}")
    # nothing loose: everything joined by faces to the shell
    fl = floating_blocks(blocks, (y0,))
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]}")
    surf, damaged = state(t, construction)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"damaged surface {damaged:.1%} outside 15-20 %")
    errs += audit_headframe(cast)
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map, "cofres": n_chests,
                   "celdas": len(cells), "celdas_publicas": len(cells_pub)}
    return errs, construction.report


def construction_top(construction):
    from .construction import YTOP
    return YTOP


def state(t, construction):
    """Damaged fraction of the surface in view (block faces looking onto a dry dug-out cell, not counting
    floors, which only face upward): hand-made ruin + what is expected from the processor."""
    blocks = t.blocks
    surf, bad = 0, 0.0
    views = set()
    for p in construction.carved:
        if bn(blocks.get(p, (None,))[0]) != "air":
            continue
        for (a, b, c) in N6:
            if b == 1:
                continue                         # the block below (floor) does not count
            views.add((p[0] + a, p[1] + b, p[2] + c))
    for q in views:
        st = blocks.get(q, (None,))[0]
        if st is None or bn(st) in ("air", "water", "cave_air"):
            continue
        surf += 1
        bad += 1.0 if q in construction.ruin else expectation(st, DECAY)
    near = sum(1 for p in construction.ruin if bn(blocks.get(p, (None,))[0]) in ("air", "water"))
    return surf, (bad + near) / max(surf, 1)


def audit_headframe(c):
    """The headframe: the chest and the shaft ladder are reached on foot from outside the footprint."""
    from .surface import FOOTPRINT
    errs = []
    x0, x1, z0, z1 = FOOTPRINT
    v = View({p: st for p, (st, _) in c.t.blocks.items()}, floor_y=0)
    start = (x0 - 1, 1, 0)
    seen, edges = strict_walk(v, start, (x0 - 2, x1 + 2, z0 - 2, z1 + 2))
    for p, _ in c.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"headframe: unreachable chest {p}")
    if not any(bn(c.t.get(x, y - 1, z)) == "ladder" or bn(c.t.get(x, y, z)) == "ladder" for (x, y, z) in seen
               if (x, z) == (-1, 0)):
        errs.append("headframe: the shaft ladder is not reachable")
    for msg, pos in lint.door_pair_issues(c.t):
        errs.append(f"castillete: {msg} en {pos}")
    return errs
