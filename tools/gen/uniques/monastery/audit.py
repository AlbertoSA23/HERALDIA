"""The monastery's own checks: redstone coherent when placed, puzzles with their solution, traps,
nothing floating, ruin proportion, chests and enemies. Manual use for floor plans and renders:
    python3 -m uniques.monasterio.auditoria --docs ../../docs/unicas/monasterio   (from tools/gen)
"""
import copy, os
from collections import deque
from core import parse_state

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
HOR = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1)}
OPP = {"east": "west", "west": "east", "north": "south", "south": "north", "up": "down", "down": "up"}


def bid(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


def props(st):
    return parse_state(st)[1]


def open_view(t):
    v = copy.copy(t)
    v.blocks = dict(t.blocks)
    for pos, st in getattr(t, "open_items", {}).items():
        v.blocks[pos] = (st, None)
    v.audit_view = None
    return v


# ------------------------------------------------------------------ redstone (common simulator: unicas/_comun/redstone.py)
def check_redstone(t):
    from .._common import redstone
    errs, _ = redstone.check_static(t)
    for name, c in getattr(t, "circuits", {}).items():
        if "levers" in c:
            errs += redstone.check_puzzle(t, name, c["levers"], c["solucion"], c["salida"], c["abre_si"])
    c = t.circuits.get("cable")
    if c:
        for h in c["ganchos"]:
            f = props(t.get(*h))["facing"]
            wall = (h[0] - HOR[f][0], h[1], h[2] - HOR[f][2])
            if bid(t.get(*wall)) in (None, "air") or not any(
                    (wall[0] + d[0], wall[1] + d[1], wall[2] + d[2]) in [tuple(x) for x in c["dispensadores"]] for d in DIRS6):
                errs.append(f"hook {h}: no wall or no dispenser next to the block it activates")
    for p in t.circuits.get("losas", {}).get("losas", []):
        below = t.get(p[0], p[1] - 1, p[2])
        if bid(below) != "dispenser" or props(below)["facing"] != "up":
            errs.append(f"slab {p} has no upward-facing dispenser below")
    return errs


# ------------------------------------------------------------------ resto
def floating_blocks(t):
    solid = {p for p, (st, _) in t.blocks.items() if bid(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] == 0}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for d in DIRS6:
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


def ruins(t):
    cells = lambda rects: {(x, z) for x0, z0, x1, z1 in rects for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}
    r, h = cells(t.ruins), cells(t.footprint)
    return len(r) / len(r | h)


def check(t):
    from .chest_loot import LOOT
    errs = check_redstone(t)
    fl = floating_blocks(t)
    if fl:
        errs.append(f"{len(fl)} floating blocks, e.g. {fl[:5]} {[t.get(*p) for p in fl[:3]]}")
    f = ruins(t)
    if not 0.15 <= f <= 0.20:
        errs.append(f"ruin proportion {f:.1%} outside 15-20 %")
    for pos, tbl in t.chest_list:
        if tbl not in LOOT:
            errs.append(f"chest {pos} with nonexistent table {tbl}")
        if not (t.blocks.get(pos) or (None, None))[1]:
            errs.append(f"chest {pos} overwritten")
    spawners = [p for p, (st, _) in t.blocks.items() if bid(st) == "spawner"]
    if len(spawners) < 3:
        errs.append("monster spawners missing")
    if not any(e[3].get("CustomName") for e in t.entities):
        errs.append("guardian missing")
    if "premium" not in [tb for _, tb in t.chest_list]:
        errs.append("premium chest missing")
    return errs


# ------------------------------------------------------------------ floor plans and renders
LEVELS = [(6, "Relicario y catacumbas"), (14, "Cuevas: gruta, ermitas, osario, archivo"), (19, "Despensa secreta"),
           (25, "T0 atrio y bodega"), (30, "Crypt"), (31, "T1 huerto y refectorio"), (37, "T2 claustro, iglesia"),
           (44, "Loft: hidden desk"), (59, "Campanario")]


def blueprint(v, cells, y):
    xs = [p[0] for p in v.blocks]; zs = [p[2] for p in v.blocks]
    out = []
    for z in range(min(zs), max(zs) + 1):
        row = []
        for x in range(min(xs), max(xs) + 1):
            st = v.get(x, y, z)
            b = bid(st) or ""
            if "chest" in b or (b == "barrel" and (v.blocks.get((x, y, z)) or (0, None))[1]):
                c = "C"
            elif b == "spawner":
                c = "S"
            elif "door" in b and "trap" not in b:
                c = "D"
            elif b == "ladder":
                c = "H"
            elif b in ("lever",):
                c = "L"
            elif "dispenser" in b or "pressure_plate" in b or "tripwire" in b:
                c = "T"
            elif (x, y, z) in cells or (x, y - 1, z) in cells:
                c = "/" if "stairs" in b or "stairs" in (bid(v.get(x, y - 1, z)) or "") else "."
            elif b in ("", "air"):
                c = " "
            else:
                c = "#"
            row.append(c)
        out.append("".join(row).rstrip())
    return out


def document(t, outdir):
    import lint, render
    from core import Template
    v = open_view(t)
    cells = set(lint.walk(v))
    os.makedirs(outdir, exist_ok=True)
    txt = ["Monastery floor plans by level (y = feet height). Legend: . reachable on foot from the entrance,",
           "/ reachable stairs, # wall or object, C chest, D door, H ladder, L lever, T trap, S spawner.",
           "The entrance is at the top (z = 0); x grows to the right. View with the secret doors open.", ""]
    for y, name in LEVELS:
        txt += [f"== y = {y}: {name} ==", *blueprint(v, cells, y), ""]
    with open(os.path.join(outdir, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt))
    ext = Template("ext")
    ext.blocks = {p: b for p, b in t.blocks.items() if p[1] >= 18}
    render.render(ext, os.path.join(outdir, "exterior.png"), scale=3, flip=True)
    rocks = {"stone", "andesite", "tuff", "cobblestone", "diorite", "grass_block", "coarse_dirt", "air", "moss_block"}
    cue = Template("cue")
    cue.blocks = {p: b for p, b in t.blocks.items() if p[1] <= 23 and bid(b[0]) not in rocks}
    render.render(cue, os.path.join(outdir, "cuevas.png"), scale=3)
    return len(cells)


if __name__ == "__main__":
    import sys
    from . import construction
    t = construction.construct()
    print("\n".join(check(t)) or "own audit: OK")
    if "--docs" in sys.argv:
        print("reachable cells:", document(t, sys.argv[sys.argv.index("--docs") + 1]))
