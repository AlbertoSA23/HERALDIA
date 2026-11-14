"""Recorrido común para auditar estructuras de varias piezas: vistas para lint.walk, alcance y bloques flotantes.

vista(): plantilla con cambios (mecanismos abiertos o cerrados) y una entrada para lint.walk; near(): ¿hay una celda
alcanzable junto a p?; flotantes(): bloques sin conexión con las capas de suelo indicadas.
"""
from collections import deque
from core import Template
from .redstone import bn, add, D6



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
    solid = {p for p, (st, _) in blocks.items() if bn(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] in suelos}
    q = deque(seen)
    while q:
        p = q.popleft()
        for v in D6.values():
            n = add(p, v)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


