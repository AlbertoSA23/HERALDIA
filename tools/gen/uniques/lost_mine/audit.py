"""Acabado y auditoría de la Mina perdida: estado de reposo de la redstone, el puzle de las agujas (la vagoneta solo
llega a la báscula con la combinación buena), la compuerta y el despacho secreto, las trampas, el recorrido a pie con
los puzles cerrados y resueltos (también estricto, sin caídas de más de un bloque y nadando), la luz de los generadores,
los forros (ningún bloque natural a la vista dentro), el casco cerrado (ningún hueco excavado toca el exterior de la
plantilla), el estado de conservación y el castillete.

preparar(obra, castillete) devuelve (errores, informe); los errores pasan a reg.warnings y la compilación falla.
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

# Desgaste repartido; con la ruina hecha a mano, 15-20 % de la superficie a la vista. Nada que sostenga un mecanismo
# se cae: solo cambian de aspecto (el adoquín musgoso y el ladrillo agrietado conducen y se dejan arrastrar igual).
DECAY = [("stone_bricks", 0.25, "cracked_stone_bricks"), ("stone_bricks", 0.12, "mossy_stone_bricks"),
         ("cobblestone", 0.22, "mossy_cobblestone")]
PROCESSOR = processor(DECAY)
INTERIOR_NATURAL = tuple(b for b in NATURAL if b not in ("gravel", "sand"))   # escombro y lecho del lago: aceptados


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

    # puzle 1: las agujas; la báscula abre la compuerta y nada más la abre
    errs += tracks.check(t, v)
    for p in v["agujas"] + [v["bascula"], v["salida"]]:
        if not tracks.is_rail(blocks.get(p)):
            errs.append(f"falta la vía en {p}")
    sim_bas = rs.Sim(t, {v["bascula"]: True})
    open_bas = open_up(t, sim_bas)
    for p in v["puerta"]:
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la compuerta no está cerrada al generarse en {p}")
        if bn(open_bas.get(p)) != "air":
            errs.append(f"la vagoneta en la báscula no abre la compuerta en {p}")
    for lv in v["palancas"] + [v["arranque"]]:
        if not all(rs.Sim(t, {lv: True}).powered(p) for p in v["pistones"]):
            errs.append(f"la palanca {lv} toca el circuito de la compuerta")
    # puzle 2: la estantería del despacho del capataz
    desc_es = m["puerta_despacho"]
    open_des = open_up(t, rs.Sim(t, {desc_es["lever"]: True}))
    for p in (desc_es["door"], (desc_es["door"][0], desc_es["door"][1] + 1, desc_es["door"][2])):
        if bn(open_des.get(p)) != "air":
            errs.append(f"la palanca no abre el despacho en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"el panel del despacho no está cerrado al generarse en {p}")
    # trampas: cable trampa y placa sobre la dinamita, sin señal en reposo
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    idle = rs.Sim(t)
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
        if idle.powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    if not rs.Sim(t, {m["placa_tnt"]: True}).powered(m["tnt"]):
        errs.append("la placa no prende la dinamita")
    if idle.powered(m["tnt"]):
        errs.append("dinamita con señal en reposo")

    # recorrido: público (puzles cerrados) y resuelto (compuerta y despacho abiertos)
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
    submerged = {p for p, _ in construction.chests if "waterlogged=true" in blocks[p]}      # se llega buceando (andar)
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        if pos in submerged or (msg.startswith("cadena sin enganche") and pos[1] == construction_top(construction)):
            continue                     # la cadena del pozo sigue en el tramo de encima
        errs.append(f"{msg} en {pos}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {pos}")
    free = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in construction.hidden if free(q)]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin resolver los puzles {p}")
    for p in [q for q in construction.hidden_alcove if free(q)]:
        if p not in cells_pub:
            errs.append(f"el alijo no se alcanza tras el tapiz {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"generador inalcanzable {p}")
    for p in v["palancas"] + [v["arranque"], desc_es["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in construction.chests:
        if p not in submerged and not nearby_flag(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    n_chests = len(construction.chests) + len(cast.chests)
    if not 15 <= n_chests <= 25:
        errs.append(f"{n_chests} cofres (se piden 15-25)")
    # recorrido estricto (sin caídas de más de un bloque, nadando) y vuelta a la entrada desde cualquier sitio
    x0, y0, z0, x1, y1, z1 = t.bounds()
    vv = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap})
    start = (entrance[0], 1, entrance[2])
    seen, edges = strict_walk(vv, start, (x0, x1, z0, z1), water=True)
    for c in no_return(edges, start)[:10]:
        errs.append(f"celda sin vuelta a la entrada {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p, 2):
            errs.append(f"cofre inalcanzable sin saltos {p}")
    if not any(c[0] == m["entrada"][0] and c[2] == m["entrada"][2] and c[1] >= 20 for c in seen):
        errs.append("no se sube por la escalera del pozo hasta arriba")
    # luz: los generadores, a oscuras
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"generador de {mob} con luz cerca {p} ({light_generator(lv, p)})")
    # forro: ningún bloque natural da a una celda excavada seca (manantiales, liquen, musgo, arcilla)
    seen_all = 0
    for p, st in blocks.items():
        if bn(st) in INTERIOR_NATURAL:
            for (a, b, c) in N6:
                q = (p[0] + a, p[1] + b, p[2] + c)
                if q in construction.carved and bn(blocks.get(q)) in ("air", "water"):
                    seen_all += 1
                    if seen_all <= 3:
                        errs.append(f"bloque natural a la vista dentro en {p} ({bn(st)})")
                    break
    # casco cerrado: ninguna celda excavada (ni lo que hay en ella) toca una celda sin escribir
    open_ones = 0
    for p in construction.carved:
        for (a, b, c) in N6:
            q = (p[0] + a, p[1] + b, p[2] + c)
            if q not in t.blocks and not (q[1] > construction_top(construction) and abs(p[0] - m["eje"][0]) <= 2
                                           and abs(p[2] - m["eje"][2]) <= 2):
                open_ones += 1
                if open_ones <= 3:
                    errs.append(f"el casco no cierra junto a {p}")
    # nada suelto: todo unido por caras al casco
    fl = floating_blocks(blocks, (y0,))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    surf, damaged = state(t, construction)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"superficie dañada {damaged:.1%} fuera de 15-20 %")
    errs += audit_headframe(cast)
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map, "cofres": n_chests,
                   "celdas": len(cells), "celdas_publicas": len(cells_pub)}
    return errs, construction.report


def construction_top(construction):
    from .construction import YTOP
    return YTOP


def state(t, construction):
    """Fracción dañada de la superficie a la vista (caras de bloques que dan a una celda excavada seca, sin contar los
    suelos, que solo dan hacia arriba): ruina hecha a mano + lo que se espera del procesador."""
    blocks = t.blocks
    surf, bad = 0, 0.0
    views = set()
    for p in construction.carved:
        if bn(blocks.get(p, (None,))[0]) != "air":
            continue
        for (a, b, c) in N6:
            if b == 1:
                continue                         # el bloque de debajo (suelo) no cuenta
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
    """El castillete: se llega a pie al cofre y a la escalera del pozo desde fuera de la huella."""
    from .surface import FOOTPRINT
    errs = []
    x0, x1, z0, z1 = FOOTPRINT
    v = View({p: st for p, (st, _) in c.t.blocks.items()}, floor_y=0)
    start = (x0 - 1, 1, 0)
    seen, edges = strict_walk(v, start, (x0 - 2, x1 + 2, z0 - 2, z1 + 2))
    for p, _ in c.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"castillete: cofre inalcanzable {p}")
    if not any(bn(c.t.get(x, y - 1, z)) == "ladder" or bn(c.t.get(x, y, z)) == "ladder" for (x, y, z) in seen
               if (x, z) == (-1, 0)):
        errs.append("castillete: no se llega a la escalera del pozo")
    for msg, pos in lint.door_pair_issues(c.t):
        errs.append(f"castillete: {msg} en {pos}")
    return errs
