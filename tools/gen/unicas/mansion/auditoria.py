"""Acabado y auditoría de la mansión: conexiones, estados de reposo, recorrido a pie, apoyos y mecanismos.

preparar(obra) devuelve (casa, sotano, errores). Si hay errores, build() los pasa a reg.warnings y la compilación falla.
"""
from collections import deque
from core import Template
import lint
from pack import fix_supports
from .redstone import Circuit, name, props, conductor, HOR, add

ENTRADA = (30, 0, 0)
JIG_ABAJO = (30, 0, 35)
NS = "heraldia:unicas/mansion/"


def regla(block, prob, out):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


# Ruina repartida (15-20 % de la superficie a la vista); nada que sostenga un mecanismo o un recorrido.
DEGRADACION = {"processor_type": "minecraft:rule", "rules": [
    regla("deepslate_bricks", 0.4, "cracked_deepslate_bricks"),
    regla("deepslate_tiles", 0.15, "cracked_deepslate_tiles"),
    regla("cobblestone", 0.4, "mossy_cobblestone"),
    regla("stone_bricks", 0.35, "mossy_stone_bricks"),
    regla("gray_stained_glass_pane", 0.3, "air"),
    regla("glass_pane", 0.3, "air"),
    regla("grass_block", 0.1, "podzol"),
    regla("tuff_bricks", 0.1, "tuff"),
    regla("polished_deepslate", 0.2, "cobbled_deepslate"),
    regla("deepslate_tile_stairs", 0.04, "air"),
]}


# ------------------------------------------------------------------ acabado
def fam(st):
    n = name(st) or ""
    if n.endswith("_pane") or n == "iron_bars":
        return "pane"
    if n.endswith("_fence"):
        return "fence"
    if n.endswith("_wall") and "torch" not in n and "banner" not in n:
        return "wall"
    return None


def conectar(t):
    for p, (st, nbt) in list(t.blocks.items()):
        f = fam(st)
        if not f:
            continue
        pr = props(st)
        con = {}
        for d in HOR:
            q = t.get(*add(p, d))
            fq = fam(q)
            nq = name(q) or ""
            ok = fq == f or (conductor(q) and "spawner" not in nq) or (f != "pane" and nq.endswith("fence_gate"))
            con[d] = ok
        if f == "wall":
            for d in HOR:
                pr[d] = "low" if con[d] else "none"
            straight = (con["north"] and con["south"] and not con["east"] and not con["west"]) or \
                       (con["east"] and con["west"] and not con["north"] and not con["south"])
            pr["up"] = "false" if straight and t.get(*add(p, "up")) in (None, "minecraft:air") else "true"
        else:
            for d in HOR:
                pr[d] = str(con[d]).lower()
        t.blocks[p] = ("minecraft:" + name(st) + "[" + ",".join(f"{k}={v}" for k, v in sorted(pr.items())) + "]", nbt)


# ------------------------------------------------------------------ vistas para el recorrido
def vista(blocks, cambios=None):
    v = Template("vista")
    v.blocks = dict(blocks)
    for p, st in (cambios or {}).items():
        if st is None:
            v.blocks.pop(p, None)
        else:
            v.blocks[p] = (st, None)
    v.jigsaw(*ENTRADA, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    return v


def near(cells, p, r=1, dys=(-1, 0, 1, 2)):
    x, y, z = p
    return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
               if abs(dx) + abs(dz) <= r for dy in dys)


def flotantes(blocks):
    solid = {p for p, (st, _) in blocks.items() if name(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] in (0, -7)}
    q = deque(seen)
    while q:
        p = q.popleft()
        for d in ("north", "south", "east", "west", "up", "down"):
            n = add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


# ------------------------------------------------------------------ preparar
def preparar(obra):
    t = obra.t
    fix_supports(t)
    conectar(t)
    errs = []
    circ = Circuit({p: st for p, (st, _) in t.blocks.items()})
    for p, st in circ.rest_states().items():
        t.blocks[p] = (st, t.blocks[p][1])
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    circ = Circuit(blocks)
    errs += circ.check_rest()
    m = obra.mech
    # escenarios
    out = circ.solve({m["palanca_biblioteca"]})
    abierta = circ.retract(out)
    for p in m["puerta_secreta"]:
        if p in abierta and name(abierta[p]) != "air":
            errs.append(f"la palanca no abre la estantería en {p}")
    for p in m["puerta_secreta"]:
        if p not in blocks or name(blocks[p]) != "bookshelf":
            errs.append(f"estantería secreta ausente en {p}")
    pal = m["palancas"]
    ok = 0
    for mask in range(16):
        on = {pal[i] for i in range(4) if mask >> i & 1}
        o = circ.solve(on)[m["puerta_camara"]]
        want = mask == 0b1001
        if o != want:
            errs.append(f"combinación {mask:04b}: puerta {'abierta' if o else 'cerrada'}")
        ok += o
    o = circ.solve(set(m["ganchos"]))
    for p in m["dispensadores"]:
        if not o[p]:
            errs.append(f"el cable trampa no activa el dispensador {p}")
    o = circ.solve({m["placa"]})
    if not all(o[p] for p in m["tnt"][:1]):
        errs.append("la placa no ceba la dinamita")
    if not circ.solve({m["boton"]})[m["puerta_almacen"]]:
        errs.append("el botón no abre la puerta del almacén")
    # recorrido a pie: público (sin mecanismos) y resuelto (estantería abierta, puertas de hierro abiertas)
    trampa = {p: None for p, st in blocks.items() if name(st) in ("tripwire", "tripwire_hook")}
    hierro = {p: "minecraft:stone" for p, st in blocks.items() if name(st) == "iron_door"}
    pub = vista(t.blocks, {**trampa, **hierro})
    cells_pub = set(lint.walk(pub))
    res_blocks = {p: (st, t.blocks[p][1] if p in t.blocks else None) for p, st in abierta.items()}
    sol = vista(res_blocks, trampa)
    cells = set(lint.walk(sol))
    for msg, pos in lint.access_issues(sol):
        errs.append(f"{msg} en {pos}")
    for p in obra.hidden:
        if p not in cells:
            errs.append(f"zona oculta inalcanzable {p}")
        if p in cells_pub:
            errs.append(f"zona oculta alcanzable sin mecanismos {p}")
    for p, st in blocks.items():
        n = name(st)
        y = p[1]
        if n == "spawner" or n == "lever" or n == "stone_button":
            if not near(cells, p, 1, (-2, -1, 0, 1)):
                errs.append(f"{n} inalcanzable {p}")
        elif n.endswith("_stairs") and not n.startswith("deepslate_tile") and not (n.startswith("stone_brick") and y >= 11) \
                and props(st).get("half") == "bottom":
            if not near(cells, p, 1, (0, 1)):
                errs.append(f"escalera inalcanzable {p} {n}")
    for p, _ in obra.chests:
        if not near(cells, p, 1, (-1, 0, 1)):
            errs.append(f"cofre inalcanzable {p}")
    for msg, pos in lint.support_issues(sol):
        errs.append(f"{msg} en {pos}")
    fl = flotantes(t.blocks)
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]}")
    obra.cells, obra.cells_pub = cells, cells_pub
    # partir en piezas y poner los jigsaws al final
    casa, sotano = Template(NS[9:] + "casa"), Template(NS[9:] + "sotano")
    for p, v in t.blocks.items():
        (casa if p[1] >= 0 else sotano).blocks[p] = v
    for x, y, z, n in t.entities:
        (casa if y >= 0 else sotano).entities.append((x, y, z, n))
    casa.jigsaw(*ENTRADA, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    casa.jigsaw(*JIG_ABAJO, "down_north", NS + "arriba", NS + "abajo", NS + "sotano", final_state="cobbled_deepslate")
    x, y, z = JIG_ABAJO
    sotano.jigsaw(x, y - 1, z, "up_north", NS + "abajo", "minecraft:empty", "minecraft:empty", final_state="tuff_bricks")
    obra.casa, obra.sotano = casa, sotano
    return casa, sotano, errs
