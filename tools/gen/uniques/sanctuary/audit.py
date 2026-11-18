"""Finishing and audit of the Druid sanctuary: resting state of the redstone, puzzles and traps, walkthrough with
the puzzles closed and solved, supports, light of the spawners, state of preservation; and split into the two pieces.

preparar(obra) returns (clearing, roots, errors, report). If there are errors, build() passes them to reg.warnings and the
build fails. Both pieces are audited here whole (without the generic per-template audit, which does not see the
tree staircase that crosses from one to the other).
"""
from core import Template
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.pieces import connect
from .._common.walkthrough import (lint_view, nearby_flag, floating_blocks, light, light_generator, View, strict_walk, no_return, processor,
                                damaged_surface, open_up)
from .construction import W, D, CRYPT, SID

ENTRANCE = (36, 0, 0)
NS = f"heraldia:unicas/{SID}/"
N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

# Wear spread around (with the hand-made ruin, 15-20 % of the visible surface); nothing that holds up a mechanism.
DECAY = [("cobblestone", 0.3, "mossy_cobblestone"), ("stone_bricks", 0.12, "cracked_stone_bricks"),
         ("stone_bricks", 0.1, "mossy_stone_bricks"), ("mud_bricks", 0.1, "packed_mud"), ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)
FLOOR = ("dirt_path", "grass_block", "cobblestone", "mossy_cobblestone", "packed_mud", "farmland", "stone_bricks",
         "stone", "birch_wood", "water")


def prepare(construction):
    t = construction.t
    fix_supports(t)
    connect(t)
    errs = []
    rs.wire_shapes(t)                     # resting state: what the game would compute after updating
    for _ in range(3):
        rs.set_wire_power(t); rs.set_torches(t); rs.set_repeaters(t)
    e, _ = rs.check_static(t)
    errs += e
    m = construction.mech
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    m["abiertas"] = set(m["sol"]["puerta"]) | {m["puerta_archivo"]["door"]}

    # puzzle 1: the season stones (16 combinations; opens when the pistons are left without a signal)
    soln = m["sol"]
    errs += rs.check_puzzle(t, "sol", m["palancas"], m["solucion"], soln["pistones"], opens_if="sin_potencia")
    fine = {p: v for p, v in zip(m["palancas"], m["solucion"])}
    open_sol = open_up(t, rs.Sim(t, fine))
    for p in soln["puerta"]:
        if bn(open_sol.get(p)) != "air":
            errs.append(f"the sun combination does not open the door at {p}")
    # puzzle 2: the archive's secret bookshelf
    arc = m["puerta_archivo"]
    open_arc = open_up(t, rs.Sim(t, {arc["lever"]: True}))
    for p in (arc["door"], (arc["door"][0], arc["door"][1] + 1, arc["door"][2])):
        if bn(open_arc.get(p)) != "air":
            errs.append(f"the lever does not open the archive door at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the archive door is not closed at generation at {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"the trap wire does not activate the dispenser {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispenser with a signal at rest {p}")
    for p in m["flechas"]:
        if not any(rs.Sim(t, {plate_pos: True}).powered(p) for plate_pos in m["placas"]):
            errs.append(f"no plate activates the dispenser {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispenser with a signal at rest {p}")

    # walkthrough: public (puzzles closed) and solved (both puzzles open)
    trap = {p: None for p, st in blocks.items() if bn(st) == "tripwire"}
    resolved_map = dict(open_sol)
    for p, st in open_arc.items():
        if blocks.get(p) != st:
            resolved_map[p] = st
    for p in set(blocks) - set(open_arc):
        resolved_map.pop(p, None)
    pub = lint_view(t.blocks, trap, ENTRANCE)
    cells_pub = set(lint.walk(pub))
    soln_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in resolved_map.items()}
    solv = lint_view(soln_blocks, trap, ENTRANCE)
    cells = set(lint.walk(solv))
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        errs.append(f"{msg} en {pos}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {pos}")
    free = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in construction.hidden if free(q) or q in m["abiertas"]]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"hidden area reachable without solving the puzzles {p}")
    for p in [q for q in construction.hidden_alcove if free(q)]:
        if p not in cells_pub:
            errs.append(f"the archdruid's alcove cannot be reached behind the tapestry {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"spawner unreachable {p}")
    for p in m["palancas"] + [arc["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"lever unreachable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"unreachable chest {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} chests (15-25 required)")
    # strict walkthrough (no falls of more than one block) and return to the entrance from anywhere
    v = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap}, floor_y=0)   # outside the disc, the terrain
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D), water=True)   # you swim out of the ditch and the pond
    for c in no_return(edges, start)[:10]:
        errs.append(f"cell with no way back to the entrance {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"chest unreachable without jumps {p}")
    # light: the spawners, in the dark (block light 0 where monsters appear)
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"{mob} spawner with light nearby {p}")
    # nothing loose: everything attached by faces to the clearing floor or to the bottom of the underground
    fl = floating_blocks(blocks, (0, CRYPT[4]))
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]}")
    # natural blocks in view inside the underground (springs and lichen): the lining must cover them
    for p, st in blocks.items():
        if p[1] < 0 and st in ("minecraft:stone", "minecraft:dirt"):
            if any(blocks.get((p[0] + a, p[1] + b, p[2] + c)) == "minecraft:air" for a, b, c in N6):
                errs.append(f"natural rock in view in the underground {p}")
                break
    # nothing grows in the clearing: no grass, no soil, no moss with nothing on top
    soil = ("grass_block", "dirt", "podzol", "moss_block", "rooted_dirt", "coarse_dirt", "mud")
    for (x, y, z), st in blocks.items():
        if y == 0 and bn(st) in soil and construction.clear(x, z) and lint.passable(blocks.get((x, 1, z))) \
                and bn(blocks.get((x, 1, z))) in ("air", None):
            errs.append(f"fertile ground uncovered in the clearing {(x, y, z)}")
            break
    surf, damaged = state(t, construction.ruin)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"damaged surface {damaged:.1%} outside 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # split into pieces and place the jigsaws last
    area, sub = Template(f"unicas/{SID}/claro"), Template(f"unicas/{SID}/raices")
    for p, val in t.blocks.items():
        (area if p[1] >= 0 else sub).blocks[p] = val
    for x, y, z, n in t.entities:
        (area if y >= 0 else sub).entities.append((x, y, z, n))
    area.jigsaw(*ENTRANCE, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
               final_state="grass_block[snowy=false]")
    jx, jy, jz = m["jig"]
    area.jigsaw(jx, jy, jz, "down_north", NS + "arriba", NS + "abajo", NS + "raices", final_state=t.get(jx, jy, jz))
    sub.jigsaw(jx, jy - 1, jz, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty",
               final_state=t.get(jx, jy - 1, jz))
    for p in (area, sub):
        p.no_generic_audit = True
    return area, sub, errs, construction.report


def state(t, ruined):
    """Fraction of the clearing's visible surface that is damaged (walkthrough.damaged_surface): neither trodden ground
    nor moss carpets count."""
    blocks = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0 and bn(st) != "moss_carpet"}
    return damaged_surface(blocks, ruined, DECAY, (-1, W, -1, D), FLOOR)
