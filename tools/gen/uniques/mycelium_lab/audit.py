"""Finishing and audit of the Mycologist's laboratory: resting state of the redstone, puzzles and traps, walkthrough
with the puzzles closed and solved, supports, light of the spawners, state of preservation; and split into the two
pieces.

preparar(obra) returns (garden, galleries, errors, report). If there are errors, build() passes them to reg.warnings and the
build fails. Both pieces are audited here whole (without the generic per-template audit, which does not see the
spiral staircase that crosses from one to the other).
"""
from core import Template
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.pieces import connect
from .._common.walkthrough import (lint_view, nearby_flag, floating_blocks, light, light_generator, View, strict_walk, no_return, processor,
                                damaged_surface, open_up)
from .construction import W, D, TUNNELS, SID, N6

ENTRANCE = (32, 0, 0)
NS = f"heraldia:unicas/{SID}/"

# Wear spread around (with the hand-made ruin, 15-20 % of the visible surface); nothing that holds up a mechanism.
DECAY = [("stone_bricks", 0.18, "cracked_stone_bricks"), ("stone_bricks", 0.15, "mossy_stone_bricks"),
         ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)
FLOOR = ("dirt_path", "mycelium", "stone_bricks", "mossy_stone_bricks", "coarse_dirt", "soul_sand", "farmland", "water",
         "spruce_planks", "grass_block", "end_stone")


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
    m["abiertas"] = set(m["reactivos"]["puerta"]) | {m["puerta_cepario"]["door"]}

    # puzzle 1: the five reagents (32 combinations; opens when the pistons are left without a signal)
    rea = m["reactivos"]
    errs += rs.check_puzzle(t, "reactivos", m["palancas"], m["solucion"], rea["pistones"], opens_if="sin_potencia")
    fine = {p: v for p, v in zip(m["palancas"], m["solucion"])}
    open_rea = open_up(t, rs.Sim(t, fine))
    for p in rea["puerta"]:
        if bn(open_rea.get(p)) != "air":
            errs.append(f"the cure does not open the reagent door at {p}")
    # puzzle 2: the stem panel of the strain vault
    stocks_door = m["puerta_cepario"]
    open_cep = open_up(t, rs.Sim(t, {stocks_door["lever"]: True}))
    for p in (stocks_door["door"], (stocks_door["door"][0], stocks_door["door"][1] + 1, stocks_door["door"][2])):
        if bn(open_cep.get(p)) != "air":
            errs.append(f"the lever does not open the strain vault at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the strain vault door is not closed at generation at {p}")
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
    resolved_map = dict(open_rea)
    for p, st in open_cep.items():
        if blocks.get(p) != st:
            resolved_map[p] = st
    for p in set(blocks) - set(open_cep):
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
            errs.append(f"the mycologist's alcove cannot be reached behind the tapestry {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"generador inalcanzable {p}")
    for p in m["palancas"] + [stocks_door["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"unreachable chest {p}")
    for p in construction.animals:
        if p not in cells_pub:
            errs.append(f"mooshroom outside the pen or trapped {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} chests (15-25 required)")
    # strict walkthrough (no falls of more than one block) and return to the entrance from anywhere
    v = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap}, floor_y=0)   # outside the disc, the terrain
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D), water=True)   # you swim out of the greenhouse ditch
    for c in no_return(edges, start)[:10]:
        errs.append(f"cell with no way back to the entrance {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"chest unreachable without jumps {p}")
    # light: the spawners, in the dark (block light 0 where monsters appear)
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"{mob} spawner with light nearby {p} ({light_generator(lv, p)})")
    # nothing loose: everything attached by faces to the garden floor or to the bottom of the underground
    fl = floating_blocks(blocks, (0, TUNNELS[4]))
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]}")
    # natural blocks in view inside the underground (springs and lichen): the lining must cover them
    for p, st in blocks.items():
        if p[1] < 0 and st in ("minecraft:stone", "minecraft:dirt"):
            if any(blocks.get((p[0] + a, p[1] + b, p[2] + c)) == "minecraft:air" for a, b, c in N6):
                errs.append(f"natural rock in view in the underground {p}")
                break
    # giant mushrooms do not grow in the garden: no uncovered mycelium or soil inside the courtyard
    soil = ("grass_block", "dirt", "podzol", "mycelium", "moss_block", "rooted_dirt", "coarse_dirt", "mud")
    for (x, y, z), st in blocks.items():
        if y == 0 and bn(st) in soil and construction.courtyard(x, z) and bn(blocks.get((x, 1, z))) in ("air", None) \
                and not construction.roofed(x, z):
            errs.append(f"fertile ground uncovered in the garden {(x, y, z)}")
            break
    surf, damaged = state(t, construction.ruin)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"damaged surface {damaged:.1%} outside 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # split into pieces and place the jigsaws last
    area, sub = Template(f"unicas/{SID}/jardin"), Template(f"unicas/{SID}/galerias")
    for p, val in t.blocks.items():
        (area if p[1] >= 0 else sub).blocks[p] = val
    for x, y, z, n in t.entities:
        (area if y >= 0 else sub).entities.append((x, y, z, n))
    area.jigsaw(*ENTRANCE, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
               final_state=t.get(*ENTRANCE))
    jx, jy, jz = m["jig"]
    area.jigsaw(jx, jy, jz, "down_north", NS + "arriba", NS + "abajo", NS + "galerias", final_state=t.get(jx, jy, jz))
    sub.jigsaw(jx, jy - 1, jz, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty",
               final_state=t.get(jx, jy - 1, jz))
    for p in (area, sub):
        p.no_generic_audit = True
    return area, sub, errs, construction.report


def state(t, ruined):
    """Fraction of the garden's visible surface that is damaged (walkthrough.damaged_surface): neither trodden ground
    nor loose mushrooms count."""
    blocks = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0 and bn(st) not in ("red_mushroom", "brown_mushroom")}
    return damaged_surface(blocks, ruined, DECAY, (-1, W, -1, D), FLOOR)
