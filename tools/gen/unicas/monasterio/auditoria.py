"""Comprobaciones propias del monasterio: redstone coherente al colocarse, puzles con su solución, trampas,
nada flotando, proporción de ruinas, cofres y enemigos. Uso a mano para planos y renders:
    python3 -m unicas.monasterio.auditoria --docs ../../docs/unicas/monasterio   (desde tools/gen)
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


def vista_abierta(t):
    v = copy.copy(t)
    v.blocks = dict(t.blocks)
    for pos, st in getattr(t, "abiertos", {}).items():
        v.blocks[pos] = (st, None)
    v.audit_view = None
    return v


# ------------------------------------------------------------------ redstone (simulador común: unicas/_comun/redstone.py)
def comprobar_redstone(t):
    from .._comun import redstone
    errs, _ = redstone.check_static(t)
    for nombre, c in getattr(t, "circuitos", {}).items():
        if "levers" in c:
            errs += redstone.check_puzzle(t, nombre, c["levers"], c["solucion"], c["salida"], c["abre_si"])
    c = t.circuitos.get("cable")
    if c:
        for h in c["ganchos"]:
            f = props(t.get(*h))["facing"]
            wall = (h[0] - HOR[f][0], h[1], h[2] - HOR[f][2])
            if bid(t.get(*wall)) in (None, "air") or not any(
                    (wall[0] + d[0], wall[1] + d[1], wall[2] + d[2]) in [tuple(x) for x in c["dispensadores"]] for d in DIRS6):
                errs.append(f"gancho {h}: sin muro o sin dispensador junto al bloque que activa")
    for p in t.circuitos.get("losas", {}).get("losas", []):
        below = t.get(p[0], p[1] - 1, p[2])
        if bid(below) != "dispenser" or props(below)["facing"] != "up":
            errs.append(f"losa {p} sin dispensador hacia arriba debajo")
    return errs


# ------------------------------------------------------------------ resto
def flotantes(t):
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


def ruinas(t):
    cells = lambda rects: {(x, z) for x0, z0, x1, z1 in rects for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}
    r, h = cells(t.ruinas), cells(t.huella)
    return len(r) / len(r | h)


def comprobar(t):
    from .botin import LOOT
    errs = comprobar_redstone(t)
    fl = flotantes(t)
    if fl:
        errs.append(f"{len(fl)} bloques flotando, p. ej. {fl[:5]} {[t.get(*p) for p in fl[:3]]}")
    f = ruinas(t)
    if not 0.15 <= f <= 0.20:
        errs.append(f"proporción de ruinas {f:.1%} fuera del 15-20 %")
    for pos, tabla in t.cofres:
        if tabla not in LOOT:
            errs.append(f"cofre {pos} con tabla inexistente {tabla}")
        if not (t.blocks.get(pos) or (None, None))[1]:
            errs.append(f"cofre {pos} sobrescrito")
    spawners = [p for p, (st, _) in t.blocks.items() if bid(st) == "spawner"]
    if len(spawners) < 3:
        errs.append("faltan generadores de monstruos")
    if not any(e[3].get("CustomName") for e in t.entities):
        errs.append("falta el guardián")
    if "premium" not in [tb for _, tb in t.cofres]:
        errs.append("falta el cofre premium")
    return errs


# ------------------------------------------------------------------ planos y renders
NIVELES = [(6, "Relicario y catacumbas"), (14, "Cuevas: gruta, ermitas, osario, archivo"), (19, "Despensa secreta"),
           (25, "T0 atrio y bodega"), (30, "Cripta"), (31, "T1 huerto y refectorio"), (37, "T2 claustro, iglesia"),
           (44, "Desván: escritorio oculto"), (59, "Campanario")]


def plano(v, cells, y):
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


def documentar(t, outdir):
    import lint, render
    from core import Template
    v = vista_abierta(t)
    cells = set(lint.walk(v))
    os.makedirs(outdir, exist_ok=True)
    txt = ["Planos del monasterio por nivel (y = altura de los pies). Leyenda: . alcanzable a pie desde la entrada,",
           "/ escalera alcanzable, # muro u objeto, C cofre, D puerta, H escala, L palanca, T trampa, S generador.",
           "La entrada está arriba (z = 0); x crece hacia la derecha. Vista con las puertas secretas abiertas.", ""]
    for y, nombre in NIVELES:
        txt += [f"== y = {y}: {nombre} ==", *plano(v, cells, y), ""]
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
    from . import obra
    t = obra.construir()
    print("\n".join(comprobar(t)) or "auditoría propia: OK")
    if "--docs" in sys.argv:
        print("celdas alcanzables:", documentar(t, sys.argv[sys.argv.index("--docs") + 1]))
