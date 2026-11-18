"""Galleon-specific checks (in addition to lint.py). Any error prevents generation."""
from collections import deque
from lint import resolved, walk, bname
from . import circuits

N6 = circuits.N6


def audit_it(o, sea):
    """sea: y of the template at sea level (beach feet at sea + 1)."""
    t = o.t
    v = resolved(t)
    blocks = {p: s for p, (s, _) in v.blocks.items()}
    errs = []
    # 1. the sea does not enter: all air below sea level is surrounded by template blocks
    for p, s in blocks.items():
        b = bname(s)
        if p[1] < sea and b == "air":
            for d in N6:
                if circuits.add(p, d) not in blocks:
                    errs.append(f"air below the sea open to the outside at {p}")
                    break
        if b == "water":
            for d in N6:
                if d[1] != 1 and bname(blocks.get(circuits.add(p, d))) in (None, "air"):
                    errs.append(f"agua suelta en {p}")
                    break
        if b in ("sand", "gravel", "suspicious_sand") and bname(blocks.get(circuits.add(p, (0, -1, 0)))) in (None, "air"):
            errs.append(f"{b} without support at {p}")
    # 2. nothing floating: every block is joined (faces) to something that reaches the ground
    solid = {p for p, s in blocks.items() if bname(s) not in ("air", "structure_void")}
    seen = set()
    q = deque(p for p in solid if p[1] <= sea)
    seen.update(q)
    while q:
        p = q.popleft()
        for d in N6:
            n = circuits.add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    loose = sorted(solid - seen)
    if loose:
        errs.append(f"{len(loose)} floating blocks, e.g. {loose[:5]} {[blocks[p] for p in loose[:3]]}")
    # 3. redstone
    errs += circuits.check(t, o.circuits)
    # 4. walkthrough: levers, generators and suspicious sand within reach
    cells = walk(t)
    for p, s in blocks.items():
        b = bname(s)
        if b in ("lever", "spawner", "suspicious_sand", "bell", "tripwire"):
            x, y, z = p
            if not any((x + dx, y + dy, z + dz) in cells for dx in (-1, 0, 1) for dz in (-1, 0, 1) for dy in (-1, 0, 1, 2)):
                errs.append(f"{b} outside the walkthrough at {p}")
    # 5. estado: 80-85 % en buen estado
    planks = sum(1 for p in o.surface if bname(blocks.get(p)) == "dark_oak_planks")
    dmg = (len(o.ruin_piece & o.surface) + 0.10 * planks) / max(1, len(o.surface))
    o.damage = dmg
    if not 0.15 <= dmg <= 0.20:
        errs.append(f"damaged surface {dmg:.1%}, outside 15-20 %")
    return errs
