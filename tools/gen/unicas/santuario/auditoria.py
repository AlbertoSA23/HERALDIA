"""Acabado y auditoría del Santuario druídico: estado de reposo de la redstone, puzles y trampas, recorrido a pie con
los puzles cerrados y resueltos, apoyos, luz de los generadores, estado de conservación; y partición en las dos piezas.

preparar(obra) devuelve (claro, raices, errores, informe). Si hay errores, build() los pasa a reg.warnings y la
compilación falla. Las dos piezas se auditan aquí enteras (sin la auditoría genérica por plantilla, que no ve la
escalera del árbol que cruza de una a otra).
"""
from core import Template
import lint
from pack import fix_supports
from .._comun import redstone as rs
from .._comun.redstone import bn
from .._comun.piezas import connect
from .._comun.recorrido import (vista_lint, cerca, flotantes, luz, luz_generador, Vista, andar, sin_vuelta, procesador,
                                superficie_danada, abrir)
from .obra import W, D, CRYPT, SID

ENTRADA = (36, 0, 0)
NS = f"heraldia:unicas/{SID}/"
N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

# Desgaste repartido (con la ruina hecha a mano, 15-20 % de la superficie a la vista); nada que sostenga un mecanismo.
DECAY = [("cobblestone", 0.3, "mossy_cobblestone"), ("stone_bricks", 0.12, "cracked_stone_bricks"),
         ("stone_bricks", 0.1, "mossy_stone_bricks"), ("mud_bricks", 0.1, "packed_mud"), ("glass_pane", 0.3, "air")]
PROCESADOR = procesador(DECAY)
SUELO = ("dirt_path", "grass_block", "cobblestone", "mossy_cobblestone", "packed_mud", "farmland", "stone_bricks",
         "stone", "birch_wood", "water")


def preparar(obra):
    t = obra.t
    fix_supports(t)
    connect(t)
    errs = []
    rs.wire_shapes(t)                     # estado de reposo: lo que el juego calcularía tras actualizarse
    for _ in range(3):
        rs.set_wire_power(t); rs.set_torches(t); rs.set_repeaters(t)
    e, _ = rs.check_static(t)
    errs += e
    m = obra.mech
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    m["abiertas"] = set(m["sol"]["puerta"]) | {m["puerta_archivo"]["door"]}

    # puzle 1: las piedras de las estaciones (16 combinaciones; abre cuando los pistones quedan sin señal)
    sol = m["sol"]
    errs += rs.check_puzzle(t, "sol", m["palancas"], m["solucion"], sol["pistones"], abre_si="sin_potencia")
    buena = {p: v for p, v in zip(m["palancas"], m["solucion"])}
    abierto_sol = abrir(t, rs.Sim(t, buena))
    for p in sol["puerta"]:
        if bn(abierto_sol.get(p)) != "air":
            errs.append(f"la combinación del sol no abre la puerta en {p}")
    # puzle 2: la estantería secreta del archivo
    arc = m["puerta_archivo"]
    abierto_arc = abrir(t, rs.Sim(t, {arc["lever"]: True}))
    for p in (arc["door"], (arc["door"][0], arc["door"][1] + 1, arc["door"][2])):
        if bn(abierto_arc.get(p)) != "air":
            errs.append(f"la palanca no abre la puerta del archivo en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la puerta del archivo no está cerrada al generarse en {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    for p in m["flechas"]:
        if not any(rs.Sim(t, {placa: True}).powered(p) for placa in m["placas"]):
            errs.append(f"ninguna placa activa el dispensador {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispensador con señal en reposo {p}")

    # recorrido: público (puzles cerrados) y resuelto (los dos puzles abiertos)
    trampa = {p: None for p, st in blocks.items() if bn(st) == "tripwire"}
    resuelto = dict(abierto_sol)
    for p, st in abierto_arc.items():
        if blocks.get(p) != st:
            resuelto[p] = st
    for p in set(blocks) - set(abierto_arc):
        resuelto.pop(p, None)
    pub = vista_lint(t.blocks, trampa, ENTRADA)
    cells_pub = set(lint.walk(pub))
    sol_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in resuelto.items()}
    solv = vista_lint(sol_blocks, trampa, ENTRADA)
    cells = set(lint.walk(solv))
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        errs.append(f"{msg} en {pos}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {pos}")
    libre = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in obra.hidden if libre(q) or q in m["abiertas"]]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin resolver los puzles {p}")
    for p in [q for q in obra.hidden_alcove if libre(q)]:
        if p not in cells_pub:
            errs.append(f"la alcoba del archidruida no se alcanza tras el tapiz {p}")
    for p, mob in obra.spawners:
        if not cerca(cells, p):
            errs.append(f"generador inalcanzable {p}")
    for p in m["palancas"] + [arc["lever"]]:
        if not cerca(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in obra.chests:
        if not cerca(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    if not 15 <= len(obra.chests) <= 25:
        errs.append(f"{len(obra.chests)} cofres (se piden 15-25)")
    # recorrido estricto (sin caídas de más de un bloque) y vuelta a la entrada desde cualquier sitio
    v = Vista({p: st for p, (st, _) in sol_blocks.items() if p not in trampa}, suelo_y=0)   # fuera del disco, el terreno
    start = (ENTRADA[0], 1, ENTRADA[2])
    seen, edges = andar(v, start, (-1, W, -1, D), agua=True)   # se sale nadando de la acequia y del estanque
    for c in sin_vuelta(edges, start)[:10]:
        errs.append(f"celda sin vuelta a la entrada {c}")
    for p, _ in obra.chests:
        if not cerca(set(seen), p):
            errs.append(f"cofre inalcanzable sin saltos {p}")
    # luz: los generadores, a oscuras (luz de bloque 0 donde aparecen los monstruos)
    lv = luz(blocks)
    for p, mob in obra.spawners:
        if luz_generador(lv, p) > 0:
            errs.append(f"generador de {mob} con luz cerca {p}")
    # nada suelto: todo unido por caras al suelo del claro o al fondo del subsuelo
    fl = flotantes(blocks, (0, CRYPT[4]))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    # naturales a la vista dentro del subsuelo (manantiales y liquen): el forro debe cubrirlos
    for p, st in blocks.items():
        if p[1] < 0 and st in ("minecraft:stone", "minecraft:dirt"):
            if any(blocks.get((p[0] + a, p[1] + b, p[2] + c)) == "minecraft:air" for a, b, c in N6):
                errs.append(f"roca natural a la vista en el subsuelo {p}")
                break
    # en el claro no nace nada: ni hierba, ni tierra, ni musgo sin algo encima
    soil = ("grass_block", "dirt", "podzol", "moss_block", "rooted_dirt", "coarse_dirt", "mud")
    for (x, y, z), st in blocks.items():
        if y == 0 and bn(st) in soil and obra.claro(x, z) and lint.passable(blocks.get((x, 1, z))) \
                and bn(blocks.get((x, 1, z))) in ("air", None):
            errs.append(f"suelo fértil descubierto en el claro {(x, y, z)}")
            break
    surf, damaged = estado(t, obra.ruin)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"superficie dañada {damaged:.1%} fuera de 15-20 %")
    obra.cells, obra.cells_pub = cells, cells_pub
    obra.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resuelto}

    # partir en piezas y poner los jigsaws al final
    sup, sub = Template(f"unicas/{SID}/claro"), Template(f"unicas/{SID}/raices")
    for p, val in t.blocks.items():
        (sup if p[1] >= 0 else sub).blocks[p] = val
    for x, y, z, n in t.entities:
        (sup if y >= 0 else sub).entities.append((x, y, z, n))
    sup.jigsaw(*ENTRADA, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
               final_state="grass_block[snowy=false]")
    jx, jy, jz = m["jig"]
    sup.jigsaw(jx, jy, jz, "down_north", NS + "arriba", NS + "abajo", NS + "raices", final_state=t.get(jx, jy, jz))
    sub.jigsaw(jx, jy - 1, jz, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty",
               final_state=t.get(jx, jy - 1, jz))
    for p in (sup, sub):
        p.sin_auditoria_generica = True
    return sup, sub, errs, obra.report


def estado(t, ruined):
    """Fracción de la superficie a la vista del claro que está dañada (recorrido.superficie_danada): ni el suelo pisado
    ni las alfombras de musgo cuentan."""
    blocks = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0 and bn(st) != "moss_carpet"}
    return superficie_danada(blocks, ruined, DECAY, (-1, W, -1, D), SUELO)
