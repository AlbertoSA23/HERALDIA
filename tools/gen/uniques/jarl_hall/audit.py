"""Acabado y auditoría del Salón del Jarl: estado de reposo de la redstone, puzles y trampas, recorrido a pie con los
puzles cerrados y resueltos, apoyos, luz de los generadores, estado de conservación; y partición en las dos piezas.

preparar(obra) devuelve (superficie, tumulo, errores, informe). Si hay errores, build() los pasa a reg.warnings y la
compilación falla. Las dos piezas se auditan aquí enteras (sin la auditoría genérica por plantilla, que no ve la
escalera que cruza de una a otra).
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


# Desgaste repartido (con la ruina hecha a mano, 15-20 % de la superficie a la vista); nada que sostenga un mecanismo.
DECAY = [("cobblestone", 0.35, "mossy_cobblestone"), ("stone_bricks", 0.12, "cracked_stone_bricks"),
         ("stone_bricks", 0.08, "mossy_stone_bricks"), ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)


# ------------------------------------------------------------------ preparar
def prepare(construction):
    t = construction.t
    fix_supports(t)
    connect(t)
    errs = []
    rs.wire_shapes(t)                     # estado de reposo: lo que el juego calcularía tras actualizarse
    for _ in range(3):
        rs.set_wire_power(t); rs.set_torches(t); rs.set_repeaters(t)
    e, _ = rs.check_static(t)
    errs += e
    m = construction.mech
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    m["abiertas"] = set(m["runas"]["puerta"]) | {m["puerta_escaldo"]["door"]}

    # puzle 1: el muro de las runas (16 combinaciones; abre cuando los pistones quedan sin señal)
    runes = m["runas"]
    errs += rs.check_puzzle(t, "runas", m["palancas"], m["solucion"], runes["pistones"], opens_if="sin_potencia")
    soln = {p: v for p, v in zip(m["palancas"], m["solucion"])}
    open_runes = open_up(t, rs.Sim(t, soln))
    for p in runes["puerta"]:
        if bn(open_runes.get(p)) != "air":
            errs.append(f"la combinación de las runas no abre la puerta en {p}")
    # puzle 2: puerta secreta de la cámara del escaldo
    noise_scale = m["puerta_escaldo"]
    open_esc = open_up(t, rs.Sim(t, {noise_scale["lever"]: True}))
    for p in ((noise_scale["door"]), (noise_scale["door"][0], noise_scale["door"][1] + 1, noise_scale["door"][2])):
        if bn(open_esc.get(p)) != "air":
            errs.append(f"la palanca no abre la puerta del escaldo en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la puerta del escaldo no está cerrada al generarse en {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    for placa in m["placas"]:
        if not any(rs.Sim(t, {placa: True}).powered(q) for q in m["tnt"]):
            errs.append(f"la placa {placa} no ceba la dinamita")

    # recorrido: público (puzles cerrados) y resuelto (los dos puzles abiertos)
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
            errs.append(f"zona oculta alcanzable sin resolver los puzles {p}")
    for p in [q for q in construction.hidden_alcove if free(q)]:
        if p not in cells_pub:
            errs.append(f"la alcoba del jarl no se alcanza tras el tapiz {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p):
            errs.append(f"generador inalcanzable {p}")
    for p in m["palancas"] + [noise_scale["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} cofres (se piden 15-25)")
    # recorrido estricto (sin caídas de más de un bloque) y vuelta a la entrada desde cualquier sitio
    v = View({p: st for p, (st, _) in soln_blocks.items() if p not in trap})
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D))
    for c in no_return(edges, start)[:10]:
        errs.append(f"celda sin vuelta a la entrada {c}")
    # luz: los generadores, a oscuras (luz de bloque 0 donde aparecen los monstruos)
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > 0:
            errs.append(f"generador de {mob} con luz cerca {p}")
    # nada suelto: todo unido por caras al suelo del recinto o al fondo del túmulo
    fl = floating_blocks(blocks, (0, CRYPT[4]))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    # naturales a la vista dentro del túmulo (manantiales y liquen): el forro debe cubrirlos
    for p, st in blocks.items():
        if p[1] < 0 and st in ("minecraft:stone", "minecraft:dirt"):
            if any(blocks.get((p[0] + a, p[1] + b, p[2] + c)) == "minecraft:air" for a, b, c in N6):
                errs.append(f"roca natural a la vista en la cripta {p}")
                break
    surf, damaged = state(t, construction.ruin)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"superficie dañada {damaged:.1%} fuera de 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    construction.report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # partir en piezas y poner los jigsaws al final
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


# ------------------------------------------------------------------ estado de conservación
def state(t, ruined):
    """Fracción de la superficie a la vista del salón que está dañada (recorrido.superficie_danada); el suelo del
    patio no cuenta."""
    blocks = {p: st for p, (st, _) in t.blocks.items() if p[1] >= 0}
    return damaged_surface(blocks, ruined, DECAY, (-1, W, -1, D), ("dirt_path", "gravel", "packed_mud"))
