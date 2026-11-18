"""Finishing and audit of Jarl's Hall: redstone resting state, puzzles and traps, walkthrough with the
puzzles closed and solved, supports, generator light, state of wear; and splitting into the two pieces.

preparar(obra) returns (surface, barrow, errors, report). If there are errors, build() passes them to reg.warnings and the
compilation fails. The two pieces are audited here whole (without the generic per-template audit, which does not see the
staircase that crosses from one to the other).
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


# Wear spread out (with the hand-made ruin, 15-20 % of the surface in view); nothing that supports a mechanism.
DECAY = [("cobblestone", 0.35, "mossy_cobblestone"), ("stone_bricks", 0.12, "cracked_stone_bricks"),
         ("stone_bricks", 0.08, "mossy_stone_bricks"), ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)


# ------------------------------------------------------------------ preparar
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
    m["abiertas"] = set(m["runas"]["puerta"]) | {m["puerta_escaldo"]["door"]}

    # puzzle 1: the rune wall (16 combinations; opens when the pistons are left without signal)
    runes = m["runas"]
    errs += rs.check_puzzle(t, "runas", m["palancas"], m["solucion"], runes["pistones"], opens_if="sin_potencia")
    soln = {p: v for p, v in zip(m["palancas"], m["solucion"])}
    open_runes = open_up(t, rs.Sim(t, soln))
    for p in runes["puerta"]:
        if bn(open_runes.get(p)) != "air":
            errs.append(f"the rune combination does not open the door at {p}")
    # puzzle 2: secret door of the skald's chamber
    noise_scale = m["puerta_escaldo"]
    open_esc = open_up(t, rs.Sim(t, {noise_scale["lever"]: True}))
    for p in ((noise_scale["door"]), (noise_scale["door"][0], noise_scale["door"][1] + 1, noise_scale["door"][2])):
        if bn(open_esc.get(p)) != "air":
            errs.append(f"the lever does not open the skald's door at {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"the skald's door is not closed when generated at {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"the trap wire does not activate dispenser {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispenser with signal at rest {p}")
    for plate_pos in m["placas"]:
        if not any(rs.Sim(t, {plate_pos: True}).powered(q) for q in m["tnt"]):
            errs.append(f"plate {plate_pos} does not prime the dynamite")

    # walkthrough: public (puzzles closed) and solved (both puzzles open)
    trap = {p: None for p, st in blocks.items() if bn(st) in ("tripwire",)}
    resolved_map = dict(open_runes)
    for p, st in open_esc.items():
        if blocks.get(p) != st:
            resolved_map[p] = st
    for p in set(blocks) - set(open_esc):
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
            errs.append(f"the jarl's alcove is not reachable behind the tapestry {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"spawner unreachable {p}")
    for p in m["palancas"] + [noise_scale["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"lever unreachable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"unreachable chest {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} chests (15-25 required)")
    # strict walkthrough (no drops of more than one block) and return to the entrance from anywhere
    v = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap})
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D))
    for c in no_return(edges, start)[:10]:
        errs.append(f"cell with no way back to the entrance {c}")
    # light: the generators in the dark (block light 0 where the monsters spawn)
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"{mob} generator with light nearby {p}")
    # nothing loose: everything joined by faces to the enclosure floor or to the bottom of the barrow
    fl = floating_blocks(blocks, (0, CRYPT[4]))
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]}")
    # natural things in view inside the barrow (springs and lichen): the lining must cover them
    for p, st in blocks.items():
        if p[1] < 0 and st in ("minecraft:stone", "minecraft:dirt"):
            if any(blocks.get((p[0] + a, p[1] + b, p[2] + c)) == "minecraft:air" for a, b, c in N6):
                errs.append(f"natural rock in view in the crypt {p}")
                break
    surf, damaged = state(t, construction.ruin)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"damaged surface {damaged:.1%} outside 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # split into pieces and place the jigsaws at the end
    area, tomb = Template(f"unicas/{SID}/salon"), Template(f"unicas/{SID}/tumulo")
    for p, val in t.blocks.items():
        (area if p[1] >= 0 else tomb).blocks[p] = val
    for x, y, z, n in t.entities:
        (area if y >= 0 else tomb).entities.append((x, y, z, n))
    area.jigsaw(*ENTRANCE, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="gravel")
    jx, jy, jz = m["jig"]
    area.jigsaw(jx, jy, jz, "down_north", NS + "arriba", NS + "abajo", NS + "tumulo", final_state=t.get(jx, jy, jz))
    tomb.jigsaw(jx, jy - 1, jz, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty",
               final_state=t.get(jx, jy - 1, jz))
    for p in (area, tomb):
        p.no_generic_audit = True
    return area, tomb, errs, construction.report


# ------------------------------------------------------------------ state of wear
def state(t, ruined):
    """Fraction of the hall's surface in view that is damaged (walkthrough.damaged_surface); the courtyard
    floor does not count."""
    blocks = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0}
    return damaged_surface(blocks, ruined, DECAY, (-1, W, -1, D), ("dirt_path", "gravel", "packed_mud"))
