"""Acabado y auditoría de la mansión: conexiones, estados de reposo, recorrido a pie, apoyos y mecanismos.

preparar(obra) devuelve (casa, sotano, errores). Si hay errores, build() los pasa a reg.warnings y la compilación falla.
"""
from core import Template
import lint
from pack import fix_supports
from .._common import redstone as rs
from .._common.redstone import bn
from .._common.pieces import connect
from .._common.walkthrough import lint_view as view, nearby_flag, floating_blocks

ENTRANCE = (30, 0, 0)
JIG_BELOW = (30, 0, 35)
NS = "heraldia:unicas/mansion/"


def rule_def(block, prob, out):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


# Ruina repartida (15-20 % de la superficie a la vista); nada que sostenga un mecanismo o un recorrido.
DEGRADATION = {"processor_type": "minecraft:rule", "rules": [
    rule_def("deepslate_bricks", 0.4, "cracked_deepslate_bricks"),
    rule_def("deepslate_tiles", 0.15, "cracked_deepslate_tiles"),
    rule_def("cobblestone", 0.4, "mossy_cobblestone"),
    rule_def("stone_bricks", 0.35, "mossy_stone_bricks"),
    rule_def("gray_stained_glass_pane", 0.3, "air"),
    rule_def("glass_pane", 0.3, "air"),
    rule_def("grass_block", 0.1, "podzol"),
    rule_def("tuff_bricks", 0.1, "tuff"),
    rule_def("polished_deepslate", 0.2, "cobbled_deepslate"),
    rule_def("deepslate_tile_stairs", 0.04, "air"),
]}


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
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    m = construction.mech
    # escenarios
    is_open = rs.retract(t, rs.Sim(t, {m["palanca_biblioteca"]: True}))
    for p in m["puerta_secreta"]:
        if p in is_open and bn(is_open[p]) != "air":
            errs.append(f"la palanca no abre la estantería en {p}")
        if bn(blocks.get(p)) != "bookshelf":
            errs.append(f"estantería secreta ausente en {p}")
    errs += rs.check_puzzle(t, "cámara", m["palancas"], (True, False, False, True), [m["puerta_camara"]])
    sim = rs.Sim(t, {p: True for p in m["ganchos"]})
    for p in m["dispensadores"]:
        if not sim.powered(p):
            errs.append(f"el cable trampa no activa el dispensador {p}")
    if not rs.Sim(t, {m["placa"]: True}).powered(m["tnt"][0]):
        errs.append("la placa no ceba la dinamita")
    if not rs.Sim(t, {m["boton"]: True}).powered(m["puerta_almacen"]):
        errs.append("el botón no abre la puerta del almacén")
    # recorrido a pie: público (sin mecanismos) y resuelto (estantería abierta, puertas de hierro abiertas)
    trap = {p: None for p, st in blocks.items() if bn(st) in ("tripwire", "tripwire_hook")}
    iron = {p: "minecraft:stone" for p, st in blocks.items() if bn(st) == "iron_door"}
    pub = view(t.blocks, {**trap, **iron}, ENTRANCE)
    cells_pub = set(lint.walk(pub))
    res_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in is_open.items()}
    soln = view(res_blocks, trap, ENTRANCE)
    cells = set(lint.walk(soln))
    for msg, pos in lint.access_issues(soln):
        errs.append(f"{msg} en {pos}")
    for p in construction.hidden:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin mecanismos {p}")
    for p, st in blocks.items():
        n = bn(st)
        y = p[1]
        if n == "spawner" or n == "lever" or n == "stone_button":
            if not nearby_flag(cells, p):
                errs.append(f"{n} inalcanzable {p}")
        elif n.endswith("_stairs") and not n.startswith("deepslate_tile") and not (n.startswith("stone_brick") and y >= 11) \
                and "half=bottom" in st:
            if not nearby_flag(cells, p):
                errs.append(f"escalera inalcanzable {p} {n}")
    for p, _ in construction.chests:
        if not nearby_flag(cells, p):
            errs.append(f"cofre inalcanzable {p}")
    for msg, pos in lint.support_issues(soln):
        errs.append(f"{msg} en {pos}")
    fl = floating_blocks({p: st for p, (st, _) in t.blocks.items()}, (0, -7))
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    construction.cells, construction.cells_pub = cells, cells_pub
    # partir en piezas y poner los jigsaws al final
    house, basement = Template(NS[9:] + "casa"), Template(NS[9:] + "sotano")
    for p, v in t.blocks.items():
        (house if p[1] >= 0 else basement).blocks[p] = v
    for x, y, z, n in t.entities:
        (house if y >= 0 else basement).entities.append((x, y, z, n))
    house.jigsaw(*ENTRANCE, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    house.jigsaw(*JIG_BELOW, "down_north", NS + "arriba", NS + "abajo", NS + "sotano", final_state="cobbled_deepslate")
    x, y, z = JIG_BELOW
    basement.jigsaw(x, y - 1, z, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty", final_state="tuff_bricks")
    construction.house, construction.basement = house, basement
    return house, basement, errs
