"""Auditoría y acabado comunes para estructuras de varias piezas.

regla(): regla de procesador aleatoria; conectar(): conexiones de cristales, rejas, vallas y muros según los vecinos;
vista(): plantilla para lint.walk con cambios y una entrada; near(): ¿hay celda alcanzable junto a p?;
flotantes(): bloques no conectados con el suelo (capas `suelos`).
"""
from collections import deque
from core import Template
from .redstone import name, props, conductor, HOR, add


def regla(block, prob, out):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


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
def vista(blocks, cambios=None, entrada=(0, 0, 0)):
    v = Template("vista")
    v.blocks = dict(blocks)
    for p, st in (cambios or {}).items():
        if st is None:
            v.blocks.pop(p, None)
        else:
            v.blocks[p] = (st, None)
    v.jigsaw(*entrada, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    return v


def near(cells, p, r=1, dys=(-1, 0, 1, 2)):
    x, y, z = p
    return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
               if abs(dx) + abs(dz) <= r for dy in dys)


def flotantes(blocks, suelos=(0,)):
    solid = {p for p, (st, _) in blocks.items() if name(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] in suelos}
    q = deque(seen)
    while q:
        p = q.popleft()
        for d in ("north", "south", "east", "west", "up", "down"):
            n = add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


