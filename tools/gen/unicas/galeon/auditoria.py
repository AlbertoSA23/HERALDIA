"""Comprobaciones propias del galeón (además de lint.py). Cualquier error impide generar."""
from collections import deque
from lint import resolved, walk, bname
from . import circuitos

N6 = circuitos.N6


def auditar(o, sea):
    """sea: y de la plantilla que queda al nivel del mar (pies de la playa en sea + 1)."""
    t = o.t
    v = resolved(t)
    blocks = {p: s for p, (s, _) in v.blocks.items()}
    errs = []
    # 1. el mar no entra: todo aire bajo el nivel del mar está rodeado por bloques de la plantilla
    for p, s in blocks.items():
        b = bname(s)
        if p[1] < sea and b == "air":
            for d in N6:
                if circuitos.add(p, d) not in blocks:
                    errs.append(f"aire bajo el mar abierto al exterior en {p}")
                    break
        if b == "water":
            for d in N6:
                if d[1] != 1 and bname(blocks.get(circuitos.add(p, d))) in (None, "air"):
                    errs.append(f"agua suelta en {p}")
                    break
        if b in ("sand", "gravel", "suspicious_sand") and bname(blocks.get(circuitos.add(p, (0, -1, 0)))) in (None, "air"):
            errs.append(f"{b} sin apoyo en {p}")
    # 2. nada flotando: todo bloque está unido (caras) a algo que llega al suelo
    solid = {p for p, s in blocks.items() if bname(s) not in ("air", "structure_void")}
    seen = set()
    q = deque(p for p in solid if p[1] <= sea)
    seen.update(q)
    while q:
        p = q.popleft()
        for d in N6:
            n = circuitos.add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    loose = sorted(solid - seen)
    if loose:
        errs.append(f"{len(loose)} bloques flotando, p. ej. {loose[:5]} {[blocks[p] for p in loose[:3]]}")
    # 3. redstone
    errs += circuitos.check(blocks, o.circuitos)
    # 4. recorrido: palancas, generadores y arena sospechosa al alcance
    cells = walk(t)
    for p, s in blocks.items():
        b = bname(s)
        if b in ("lever", "spawner", "suspicious_sand", "bell", "tripwire"):
            x, y, z = p
            if not any((x + dx, y + dy, z + dz) in cells for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (-1, 0, 1, 2)):
                errs.append(f"{b} fuera del recorrido en {p}")
    # 5. estado: 80-85 % en buen estado
    planks = sum(1 for p in o.superficie if bname(blocks.get(p)) == "dark_oak_planks")
    dmg = (len(o.ruina & o.superficie) + 0.10 * planks) / max(1, len(o.superficie))
    o.dano = dmg
    if not 0.15 <= dmg <= 0.20:
        errs.append(f"superficie dañada {dmg:.1%}, fuera de 15-20 %")
    return errs
