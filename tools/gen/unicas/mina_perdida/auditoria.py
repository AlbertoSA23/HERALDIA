"""Acabado y auditoría de la Mina perdida: estado de reposo de la redstone, el puzle de las agujas (la vagoneta solo
llega a la báscula con la combinación buena), la compuerta y el despacho secreto, las trampas, el recorrido a pie con
los puzles cerrados y resueltos (también estricto, sin caídas de más de un bloque y nadando), la luz de los generadores,
los forros (ningún bloque natural a la vista dentro), el casco cerrado (ningún hueco excavado toca el exterior de la
plantilla), el estado de conservación y el castillete.

preparar(obra, castillete) devuelve (errores, informe); los errores pasan a reg.warnings y la compilación falla.
"""
import lint
from pack import fix_supports
from .._comun import redstone as rs
from .._comun.redstone import bn
from .._comun.piezas import connect, open_stairwells
from .._comun.recorrido import (vista_lint, cerca, flotantes, luz, luz_generador, Vista, andar, sin_vuelta, procesador,
                                esperanza, abrir)
from . import vias
from .obra import N6, NATURAL, SID

# Desgaste repartido; con la ruina hecha a mano, 15-20 % de la superficie a la vista. Nada que sostenga un mecanismo
# se cae: solo cambian de aspecto (el adoquín musgoso y el ladrillo agrietado conducen y se dejan arrastrar igual).
DECAY = [("stone_bricks", 0.25, "cracked_stone_bricks"), ("stone_bricks", 0.12, "mossy_stone_bricks"),
         ("cobblestone", 0.22, "mossy_cobblestone")]
PROCESADOR = procesador(DECAY)
INTERIOR_NATURAL = tuple(b for b in NATURAL if b not in ("gravel", "sand"))   # escombro y lecho del lago: aceptados


def preparar(obra, cast):
    t = obra.t
    fix_supports(t)
    connect(t)
    open_stairwells(t)
    errs = []
    rs.wire_shapes(t)
    e, _ = rs.check_static(t)
    errs += e
    m = obra.mech
    v = m["vias"]
    blocks = {p: st for p, (st, _) in t.blocks.items()}

    # puzle 1: las agujas; la báscula abre la compuerta y nada más la abre
    errs += vias.comprobar(t, v)
    for p in v["agujas"] + [v["bascula"], v["salida"]]:
        if not vias.es_rail(blocks.get(p)):
            errs.append(f"falta la vía en {p}")
    sim_bas = rs.Sim(t, {v["bascula"]: True})
    abierto_bas = abrir(t, sim_bas)
    for p in v["puerta"]:
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la compuerta no está cerrada al generarse en {p}")
        if bn(abierto_bas.get(p)) != "air":
            errs.append(f"la vagoneta en la báscula no abre la compuerta en {p}")
    for lv in v["palancas"] + [v["arranque"]]:
        if not all(rs.Sim(t, {lv: True}).powered(p) for p in v["pistones"]):
            errs.append(f"la palanca {lv} toca el circuito de la compuerta")
    # puzle 2: la estantería del despacho del capataz
    des = m["puerta_despacho"]
    abierto_des = abrir(t, rs.Sim(t, {des["lever"]: True}))
    for p in (des["door"], (des["door"][0], des["door"][1] + 1, des["door"][2])):
        if bn(abierto_des.get(p)) != "air":
            errs.append(f"la palanca no abre el despacho en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"el panel del despacho no está cerrado al generarse en {p}")
    # trampas: cable trampa y placa sobre la dinamita, sin señal en reposo
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    reposo = rs.Sim(t)
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
        if reposo.powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    if not rs.Sim(t, {m["placa_tnt"]: True}).powered(m["tnt"]):
        errs.append("la placa no prende la dinamita")
    if reposo.powered(m["tnt"]):
        errs.append("dinamita con señal en reposo")

    # recorrido: público (puzles cerrados) y resuelto (compuerta y despacho abiertos)
    trampa = {p: None for p, st in blocks.items() if bn(st) == "tripwire"}
    resuelto = dict(abierto_bas)
    for p, st in abierto_des.items():
        if blocks.get(p) != st:
            resuelto[p] = st
    for p in set(blocks) - set(abierto_des):
        resuelto.pop(p, None)
    entrada = (m["entrada"][0] + 2, 0, m["entrada"][2] + 3)
    pub = vista_lint(t.blocks, trampa, entrada)
    cells_pub = set(lint.walk(pub, extra_ground=False))
    sol_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in resuelto.items()}
    solv = vista_lint(sol_blocks, trampa, entrada)
    cells = set(lint.walk(solv, extra_ground=False))
    sumergidos = {p for p, _ in obra.chests if "waterlogged=true" in blocks[p]}      # se llega buceando (andar)
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        if pos in sumergidos or (msg.startswith("cadena sin enganche") and pos[1] == obra_top(obra)):
            continue                     # la cadena del pozo sigue en el tramo de encima
        errs.append(f"{msg} en {pos}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {pos}")
    libre = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in obra.hidden if libre(q)]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin resolver los puzles {p}")
    for p in [q for q in obra.hidden_alcove if libre(q)]:
        if p not in cells_pub:
            errs.append(f"el alijo no se alcanza tras el tapiz {p}")
    for p, mob in obra.spawners:
        if not cerca(cells, p):
            errs.append(f"generador inalcanzable {p}")
    for p in v["palancas"] + [v["arranque"], des["lever"]]:
        if not cerca(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in obra.chests:
        if p not in sumergidos and not cerca(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    n_cofres = len(obra.chests) + len(cast.chests)
    if not 15 <= n_cofres <= 25:
        errs.append(f"{n_cofres} cofres (se piden 15-25)")
    # recorrido estricto (sin caídas de más de un bloque, nadando) y vuelta a la entrada desde cualquier sitio
    x0, y0, z0, x1, y1, z1 = t.bounds()
    vv = Vista({p: st for p, (st, _) in sol_blocks.items() if p not in trampa})
    start = (entrada[0], 1, entrada[2])
    seen, edges = andar(vv, start, (x0, x1, z0, z1), agua=True)
    for c in sin_vuelta(edges, start)[:10]:
        errs.append(f"celda sin vuelta a la entrada {c}")
    for p, _ in obra.chests:
        if not cerca(set(seen), p, 2):
            errs.append(f"cofre inalcanzable sin saltos {p}")
    if not any(c[0] == m["entrada"][0] and c[2] == m["entrada"][2] and c[1] >= 20 for c in seen):
        errs.append("no se sube por la escalera del pozo hasta arriba")
    # luz: los generadores, a oscuras
    lv = luz(blocks)
    for p, mob in obra.spawners:
        if luz_generador(lv, p) > 0:
            errs.append(f"generador de {mob} con luz cerca {p} ({luz_generador(lv, p)})")
    # forro: ningún bloque natural da a una celda excavada seca (manantiales, liquen, musgo, arcilla)
    vistos = 0
    for p, st in blocks.items():
        if bn(st) in INTERIOR_NATURAL:
            for (a, b, c) in N6:
                q = (p[0] + a, p[1] + b, p[2] + c)
                if q in obra.carved and bn(blocks.get(q)) in ("air", "water"):
                    vistos += 1
                    if vistos <= 3:
                        errs.append(f"bloque natural a la vista dentro en {p} ({bn(st)})")
                    break
    # casco cerrado: ninguna celda excavada (ni lo que hay en ella) toca una celda sin escribir
    abiertas = 0
    for p in obra.carved:
        for (a, b, c) in N6:
            q = (p[0] + a, p[1] + b, p[2] + c)
            if q not in t.blocks and not (q[1] > obra_top(obra) and abs(p[0] - m["eje"][0]) <= 2
                                           and abs(p[2] - m["eje"][2]) <= 2):
                abiertas += 1
                if abiertas <= 3:
                    errs.append(f"el casco no cierra junto a {p}")
    # nada suelto: todo unido por caras al casco
    fl = flotantes(blocks, (y0,))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    surf, damaged = estado(t, obra)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"superficie dañada {damaged:.1%} fuera de 15-20 %")
    errs += auditar_castillete(cast)
    obra.cells, obra.cells_pub = cells, cells_pub
    obra.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resuelto, "cofres": n_cofres,
                   "celdas": len(cells), "celdas_publicas": len(cells_pub)}
    return errs, obra.report


def obra_top(obra):
    from .obra import YTOP
    return YTOP


def estado(t, obra):
    """Fracción dañada de la superficie a la vista (caras de bloques que dan a una celda excavada seca, sin contar los
    suelos, que solo dan hacia arriba): ruina hecha a mano + lo que se espera del procesador."""
    blocks = t.blocks
    surf, bad = 0, 0.0
    vistas = set()
    for p in obra.carved:
        if bn(blocks.get(p, (None,))[0]) != "air":
            continue
        for (a, b, c) in N6:
            if b == 1:
                continue                         # el bloque de debajo (suelo) no cuenta
            vistas.add((p[0] + a, p[1] + b, p[2] + c))
    for q in vistas:
        st = blocks.get(q, (None,))[0]
        if st is None or bn(st) in ("air", "water", "cave_air"):
            continue
        surf += 1
        bad += 1.0 if q in obra.ruin else esperanza(st, DECAY)
    near = sum(1 for p in obra.ruin if bn(blocks.get(p, (None,))[0]) in ("air", "water"))
    return surf, (bad + near) / max(surf, 1)


def auditar_castillete(c):
    """El castillete: se llega a pie al cofre y a la escalera del pozo desde fuera de la huella."""
    from .superficie import HUELLA
    errs = []
    x0, x1, z0, z1 = HUELLA
    v = Vista({p: st for p, (st, _) in c.t.blocks.items()}, suelo_y=0)
    start = (x0 - 1, 1, 0)
    seen, edges = andar(v, start, (x0 - 2, x1 + 2, z0 - 2, z1 + 2))
    for p, _ in c.chests:
        if not cerca(set(seen), p):
            errs.append(f"castillete: cofre inalcanzable {p}")
    if not any(bn(c.t.get(x, y - 1, z)) == "ladder" or bn(c.t.get(x, y, z)) == "ladder" for (x, y, z) in seen
               if (x, z) == (-1, 0)):
        errs.append("castillete: no se llega a la escalera del pozo")
    for msg, pos in lint.door_pair_issues(c.t):
        errs.append(f"castillete: {msg} en {pos}")
    return errs
