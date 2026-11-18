"""Finishing and audit of the Corsair's island: redstone resting state, puzzles and traps, walkthrough with
the puzzles closed and solved (also swimming through the cove), supports, generator light, the sea not entering
the rooms below water level, watertight water, nothing floating, cave lining and state of wear.

preparar(obra) returns (normalized template, errors, report). If there are errors, build() passes them to reg.warnings and the
compilation fails. The whole template is audited here (without the generic per-template audit).
"""
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.walkthrough import (lint_view, nearby_flag, floating_blocks, light, light_generator, View, strict_walk, no_return, processor,
                                damaged_surface, open_up)
from .construction import W, D, BASE, SID, N6, TREES

ENTRANCE = (44, 0, 80)        # the beach at the foot of the pier (lint.walk enters from above)
DY = -BASE + 2               # lint.walk takes any empty cell with y < 0 as floor: it is audited shifted
LIGHT_MAX = 11                 # the generators carry custom_spawn_rules with block light up to 11

# Wear spread out (with the hand-made ruin, 15-20 % of the build in view); nothing that supports a mechanism.
DECAY = [("stone_bricks", 0.19, "cracked_stone_bricks"), ("stone_bricks", 0.16, "mossy_stone_bricks"),
         ("cobblestone", 0.22, "mossy_cobblestone"), ("spruce_planks", 0.12, "stripped_spruce_wood"),
         ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)
PLANT = ("jungle_log", "jungle_leaves", "cocoa", "short_grass")


def with_sea(blocks, nbt=True):
    """Copy with the sea around it (water in every empty cell below water level inside the box): the walkthrough
    swims and does not step on a virtual floor."""
    out = dict(blocks)
    water = ("minecraft:water", None) if nbt else "minecraft:water"
    for x in range(-1, W + 1):
        for z in range(-1, D + 1):
            for y in range(BASE, 0):
                out.setdefault((x, y, z), water)
    return out


def prepare(construction):
    t = construction.t
    fix_supports(t)
    errs = []
    rs.wire_shapes(t)
    for _ in range(3):
        rs.set_wire_power(t); rs.set_torches(t); rs.set_repeaters(t)
    e, _ = rs.check_static(t)
    errs += e
    m = construction.mech
    blocks = {p: st for p, (st, _) in t.blocks.items()}

    # puzzle 1: the compass rose (16 combinations; opens when the pistons are left without signal)
    rose = m["rosa"]
    errs += rs.check_puzzle(t, "rosa", m["palancas"], m["solucion"], rose["pistones"], opens_if="sin_potencia")
    fine = dict(zip(m["palancas"], m["solucion"]))
    open_rose = open_up(t, rs.Sim(t, fine))
    for p in m["puerta_rosa"]:
        if bn(open_rose.get(p)) != "air":
            errs.append(f"the rose does not open the treasure door at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the treasure door is not closed when generated at {p}")
    # puzzle 2: the powder magazine (lever next to the armorer)
    sb = m["santabarbara"]
    open_sb = open_up(t, rs.Sim(t, {sb["lever"]: True}))
    for p in (sb["door"], (sb["door"][0], sb["door"][1] + 1, sb["door"][2])):
        if bn(open_sb.get(p)) != "air":
            errs.append(f"the lever does not open the powder magazine at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the powder magazine is not closed when generated at {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores_cable"]:
        if not sim.powered(p):
            errs.append(f"the trap wire does not activate dispenser {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispenser with signal at rest {p}")
    for p in m["flechas"]:
        if not any(rs.Sim(t, {plate_pos: True}).powered(p) for plate_pos in m["placas"]):
            errs.append(f"no plate activates dispenser {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispenser with signal at rest {p}")
    for p in m["canones"]:
        if rs.Sim(t).powered(p):
            errs.append(f"cannon with signal {p}")

    # walkthrough: public (puzzles closed) and solved (both open)
    trap = {p: None for p, st in blocks.items() if bn(st) == "tripwire"}
    resolved_map = dict(open_rose)
    for p, st in open_sb.items():
        if blocks.get(p) != st:
            resolved_map[p] = st
    for p in set(blocks) - set(open_sb):
        resolved_map.pop(p, None)
    up = lambda d: {(x, y + DY, z): v for (x, y, z), v in d.items()}
    down = lambda c: {(x, y - DY, z) for (x, y, z) in c}
    entrance = (ENTRANCE[0], ENTRANCE[1] + DY, ENTRANCE[2])
    pub = lint_view(up(with_sea(t.blocks)), up(trap), entrance)
    cells_pub = down(lint.walk(pub))
    soln_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in resolved_map.items()}
    solv = lint_view(up(with_sea(soln_blocks)), up(trap), entrance)
    cells = down(lint.walk(solv))
    ax, az = m["ancla"]
    solv.blocks[(ax, BASE - 1 + DY, az)] = ("minecraft:sand", None)     # the floor under the anchor (the chain holds it)
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        errs.append(f"{msg} en {(pos[0], pos[1] - DY, pos[2])}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {(pos[0], pos[1] - DY, pos[2])}")
    free = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in construction.hidden if free(q)]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"hidden area reachable without solving the puzzles {p}")
    for p in [q for q in construction.secret if free(q)]:
        if p not in cells_pub:
            errs.append(f"the hideout is not reachable behind the tapestry {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p, 2):
            errs.append(f"spawner unreachable {p}")
    for p in m["palancas"] + [sb["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"lever unreachable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"unreachable chest {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} chests (15-25 required)")
    # strict walkthrough (no drops of more than one block, swimming in the cove) and return to the entrance
    v = View(with_sea({p: st for p, (st, _) in soln_blocks.items() if p not in trap}, nbt=False))
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D), water=True)
    for c in no_return(edges, start)[:10]:
        errs.append(f"cell with no way back to the entrance {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"chest unreachable without jumps {p}")
    # generator light
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > LIGHT_MAX:
            errs.append(f"{mob} generator with too much light {p} ({light_generator(lv, p)})")
    # nothing loose: everything joined by faces to the bottom row (which extends down to the floor)
    fl = floating_blocks(blocks, (BASE,))
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]} {[blocks[p] for p in fl[:3]]}")
    # the sea does not enter: all air below water level has its 6 neighbors in the template; watertight water
    for p, st in blocks.items():
        b = bn(st)
        if p[1] < 0 and b == "air":
            for d in N6:
                if (p[0] + d[0], p[1] + d[1], p[2] + d[2]) not in blocks:
                    errs.append(f"air below the sea open to the outside at {p}")
                    break
        if b == "water":
            for d in N6:
                if d[1] != 1 and bn(blocks.get((p[0] + d[0], p[1] + d[1], p[2] + d[2]))) == "air":
                    errs.append(f"loose water at {p}")
                    break
        if b in ("sand", "gravel") and p[1] > BASE and bn(blocks.get((p[0], p[1] - 1, p[2]))) in ("air", "water", None):
            errs.append(f"{b} without support at {p}")
    # lining: no cave face looks onto natural rock
    for p in construction.lining:
        if blocks.get(p) in ("minecraft:stone", "minecraft:andesite", "minecraft:tuff", "minecraft:dirt"):
            errs.append(f"natural rock in view in the caves {p}")
            break
    # no tree or bush against the build: no grass within construction.TREES blocks (the oceans have oaks)
    cols = construction.construction_columns()
    for (x, z), g in construction.ground.items():
        if bn(blocks.get((x, g, z))) == "grass_block" and any(
                (x + a, z + b) in cols for a in range(-TREES, TREES + 1) for b in range(-TREES, TREES + 1)):
            errs.append(f"grass (a tree may grow) next to the build at {(x, g, z)}")
            break
    surf, damaged = state(construction, blocks)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"damaged surface {damaged:.1%} outside 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # final template (coordinates >= 0): the BASE row becomes row 0
    t.name = f"unicas/{SID}/isla"
    report["desplazamiento"] = t.bounds()[:3]       # minimum corner of the build: the template's (0, 0, 0)
    t.normalize()
    t.no_generic_audit = True
    return t, errs, report


def state(construction, blocks):
    """Damaged fraction of the build in view (walkthrough.damaged_surface) not counting the natural islet, the trodden floor
    (roads, cobbled courtyard: the islet's surface layer), vegetation or what lies under water."""
    construction_b = {p: st for p, st in blocks.items()
              if p[1] >= 0 and construction.natural.get(p) != st and bn(st) not in PLANT
              and construction.ground.get((p[0], p[2])) != p[1]}
    return damaged_surface(construction_b, construction.ruin, DECAY, (0, W, 0, D))
