"""Acabado y auditoría de la Isla del corsario: estado de reposo de la redstone, puzles y trampas, recorrido a pie con
los puzles cerrados y resueltos (también nadando por la ensenada), apoyos, luz de los generadores, el mar que no entra en
las salas bajo el nivel del agua, agua sin fugas, nada flotando, forro de las cuevas y estado de conservación.

preparar(obra) devuelve (plantilla normalizada, errores, informe). Si hay errores, build() los pasa a reg.warnings y la
compilación falla. La plantilla se audita entera aquí (sin la auditoría genérica por plantilla).
"""
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.walkthrough import (lint_view, nearby_flag, floating_blocks, light, light_generator, View, strict_walk, no_return, processor,
                                damaged_surface, open_up)
from .construction import W, D, BASE, SID, N6, TREES

ENTRANCE = (44, 0, 80)        # la playa al pie del muelle (lint.walk entra por encima)
DY = -BASE + 2               # lint.walk toma por suelo cualquier celda vacía con y < 0: se audita desplazado
LIGHT_MAX = 11                 # los generadores llevan custom_spawn_rules con luz de bloque hasta 11

# Desgaste repartido (con la ruina hecha a mano, 15-20 % de la obra a la vista); nada que sostenga un mecanismo.
DECAY = [("stone_bricks", 0.19, "cracked_stone_bricks"), ("stone_bricks", 0.16, "mossy_stone_bricks"),
         ("cobblestone", 0.22, "mossy_cobblestone"), ("spruce_planks", 0.12, "stripped_spruce_wood"),
         ("glass_pane", 0.3, "air")]
PROCESSOR = processor(DECAY)
PLANT = ("jungle_log", "jungle_leaves", "cocoa", "short_grass")


def with_sea(blocks, nbt=True):
    """Copia con el mar alrededor (agua en toda celda vacía bajo el nivel del agua dentro de la caja): el recorrido
    nada y no pisa un fondo virtual."""
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

    # puzle 1: la rosa de los vientos (16 combinaciones; abre cuando los pistones quedan sin señal)
    rose = m["rosa"]
    errs += rs.check_puzzle(t, "rosa", m["palancas"], m["solucion"], rose["pistones"], opens_if="sin_potencia")
    fine = dict(zip(m["palancas"], m["solucion"]))
    open_rose = open_up(t, rs.Sim(t, fine))
    for p in m["puerta_rosa"]:
        if bn(open_rose.get(p)) != "air":
            errs.append(f"la rosa no abre la puerta del tesoro en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la puerta del tesoro no está cerrada al generarse en {p}")
    # puzle 2: la santabárbara (palanca junto al armero)
    sb = m["santabarbara"]
    open_sb = open_up(t, rs.Sim(t, {sb["lever"]: True}))
    for p in (sb["door"], (sb["door"][0], sb["door"][1] + 1, sb["door"][2])):
        if bn(open_sb.get(p)) != "air":
            errs.append(f"la palanca no abre la santabárbara en {p}")
        if bn(blocks.get(p)) in ("air", None):
            errs.append(f"la santabárbara no está cerrada al generarse en {p}")
    # trampas
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores_cable"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    for p in m["flechas"]:
        if not any(rs.Sim(t, {plate_pos: True}).powered(p) for plate_pos in m["placas"]):
            errs.append(f"ninguna placa activa el dispensador {p}")
        if rs.Sim(t).powered(p):
            errs.append(f"dispensador con señal en reposo {p}")
    for p in m["canones"]:
        if rs.Sim(t).powered(p):
            errs.append(f"cañón con señal {p}")

    # recorrido: público (puzles cerrados) y resuelto (los dos abiertos)
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
    solv.blocks[(ax, BASE - 1 + DY, az)] = ("minecraft:sand", None)     # el fondo bajo el ancla (la cadena la sujeta)
    for msg, pos in lint.access_issues(solv) + lint.support_issues(solv):
        errs.append(f"{msg} en {(pos[0], pos[1] - DY, pos[2])}")
    for msg, pos in lint.door_pair_issues(solv) + lint.stair_headroom_issues(solv):
        errs.append(f"{msg} en {(pos[0], pos[1] - DY, pos[2])}")
    free = lambda p: lint.passable(blocks.get(p)) and not lint.passable(blocks.get((p[0], p[1] - 1, p[2])))
    for p in [q for q in construction.hidden if free(q)]:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin resolver los puzles {p}")
    for p in [q for q in construction.secret if free(q)]:
        if p not in cells_pub:
            errs.append(f"el escondite no se alcanza tras el tapiz {p}")
    for p, mob in construction.spawners:
        if not nearby_flag(cells, p, 2):
            errs.append(f"generador inalcanzable {p}")
    for p in m["palancas"] + [sb["lever"]]:
        if not nearby_flag(cells_pub, p):
            errs.append(f"palanca inalcanzable {p}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    if not 15 <= len(construction.chests) <= 25:
        errs.append(f"{len(construction.chests)} cofres (se piden 15-25)")
    # recorrido estricto (sin caídas de más de un bloque, nadando en la ensenada) y vuelta a la entrada
    v = View(with_sea({p: st for p, (st, _) in soln_blocks.items() if p not in trap}, nbt=False))
    start = (ENTRANCE[0], 1, ENTRANCE[2])
    seen, edges = strict_walk(v, start, (-1, W, -1, D), water=True)
    for c in no_return(edges, start)[:10]:
        errs.append(f"celda sin vuelta a la entrada {c}")
    for p, _ in construction.chests:
        if not nearby_flag(set(seen), p):
            errs.append(f"cofre inalcanzable sin saltos {p}")
    # luz de los generadores
    lv = light(blocks)
    for p, mob in construction.spawners:
        if light_generator(lv, p) > LIGHT_MAX:
            errs.append(f"generador de {mob} con demasiada luz {p} ({light_generator(lv, p)})")
    # nada suelto: todo unido por caras a la fila inferior (que se prolonga hasta el fondo)
    fl = floating_blocks(blocks, (BASE,))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]} {[blocks[p] for p in fl[:3]]}")
    # el mar no entra: todo aire bajo el nivel del agua tiene sus 6 vecinas en la plantilla; agua sin fugas
    for p, st in blocks.items():
        b = bn(st)
        if p[1] < 0 and b == "air":
            for d in N6:
                if (p[0] + d[0], p[1] + d[1], p[2] + d[2]) not in blocks:
                    errs.append(f"aire bajo el mar abierto al exterior en {p}")
                    break
        if b == "water":
            for d in N6:
                if d[1] != 1 and bn(blocks.get((p[0] + d[0], p[1] + d[1], p[2] + d[2]))) == "air":
                    errs.append(f"agua suelta en {p}")
                    break
        if b in ("sand", "gravel") and p[1] > BASE and bn(blocks.get((p[0], p[1] - 1, p[2]))) in ("air", "water", None):
            errs.append(f"{b} sin apoyo en {p}")
    # forro: ninguna cara de las cuevas da a roca natural
    for p in construction.lining:
        if blocks.get(p) in ("minecraft:stone", "minecraft:andesite", "minecraft:tuff", "minecraft:dirt"):
            errs.append(f"roca natural a la vista en las cuevas {p}")
            break
    # ningún árbol ni mata contra la obra: sin hierba a menos de obra.ARBOLES bloques (los océanos tienen robles)
    cols = construction.construction_columns()
    for (x, z), g in construction.ground.items():
        if bn(blocks.get((x, g, z))) == "grass_block" and any(
                (x + a, z + b) in cols for a in range(-TREES, TREES + 1) for b in range(-TREES, TREES + 1)):
            errs.append(f"hierba (puede nacer un árbol) junto a la obra en {(x, g, z)}")
            break
    surf, damaged = state(construction, blocks)
    if not 0.15 <= damaged <= 0.20:
        errs.append(f"superficie dañada {damaged:.1%} fuera de 15-20 %")
    construction.cells, construction.cells_pub = cells, cells_pub
    report = {"superficie": surf, "danada": damaged, "luz": lv, "abierto": resolved_map}

    # plantilla final (coordenadas >= 0): la fila BASE pasa a ser la 0
    t.name = f"unicas/{SID}/isla"
    report["desplazamiento"] = t.bounds()[:3]       # esquina mínima de la obra: la (0, 0, 0) de la plantilla
    t.normalize()
    t.no_generic_audit = True
    return t, errs, report


def state(construction, blocks):
    """Fracción dañada de la obra a la vista (recorrido.superficie_danada) sin contar el islote natural, el suelo pisado
    (caminos, patio empedrado: la capa de la superficie del islote), la vegetación ni lo que queda bajo el agua."""
    construction_b = {p: st for p, st in blocks.items()
              if p[1] >= 0 and construction.natural.get(p) != st and bn(st) not in PLANT
              and construction.ground.get((p[0], p[2])) != p[1]}
    return damaged_surface(construction_b, construction.ruin, DECAY, (0, W, 0, D))
