"""Comprobaciones propias del monasterio: redstone coherente al colocarse, puzles con su solución, trampas,
nada flotando, proporción de ruinas, cofres y enemigos. Uso a mano para planos y renders:
    python3 -m unicas.monasterio.auditoria --docs ../../docs/unicas/monasterio   (desde tools/gen)
"""
import copy, itertools, os
from collections import deque
from core import parse_state

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
HOR = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1)}
OPP = {"east": "west", "west": "east", "north": "south", "south": "north", "up": "down", "down": "up"}
COMPONENTS = ("lever", "redstone_wall_torch", "redstone_torch", "redstone_wire", "sticky_piston", "piston", "piston_head",
              "redstone_lamp", "iron_door")


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


# ------------------------------------------------------------------ redstone
def simular(t, palancas):
    """Estado estable de los circuitos con las palancas dadas {pos: bool}. Devuelve (polvo, potenciados, antorchas)."""
    g = lambda p: (t.blocks.get(p) or (None,))[0]
    red = {p: st for p, (st, _) in t.blocks.items() if bid(st) in COMPONENTS}
    lever_on = {p: palancas.get(p, props(st)["powered"] == "true") for p, st in red.items() if bid(st) == "lever"}
    torches = {p: props(st)["lit"] == "true" for p, st in red.items() if "torch" in bid(st)}

    def add(p, d):
        return (p[0] + d[0], p[1] + d[1], p[2] + d[2])

    def attached(p, st):
        f = props(st)["facing"]
        return add(p, HOR[OPP[f]])

    def conductor(p):
        st = g(p)
        b = bid(st)
        return st is not None and b not in ("air",) and b not in COMPONENTS and "glass" not in b

    for _ in range(40):
        strong = set()
        for p, on in lever_on.items():
            if on:
                strong.add(attached(p, red[p]))
        for p, lit in torches.items():
            if lit:
                strong.add(add(p, (0, 1, 0)))
        dust = {p: 0 for p, st in red.items() if bid(st) == "redstone_wire"}
        q = deque()
        for p in dust:
            src = 0
            for d in DIRS6:
                n = add(p, d)
                if n in strong and conductor(n):
                    src = 15
                if n in lever_on and lever_on[n]:
                    src = 15
                if n in torches and torches[n] and attached(n, red[n]) != p:
                    src = 15
            if src:
                dust[p] = src
                q.append(p)
        while q:
            p = q.popleft()
            for d in HOR.values():
                n = add(p, d)
                if n in dust and dust[n] < dust[p] - 1:
                    dust[n] = dust[p] - 1
                    q.append(n)
        weak = set()
        for p, pw in dust.items():
            if pw:
                weak.add(add(p, (0, -1, 0)))
                for k, d in HOR.items():
                    if props(red[p]).get(k, "none") != "none":
                        weak.add(add(p, d))

        def powered_block(n):
            return conductor(n) and (n in strong or n in weak)

        new = {p: not powered_block(attached(p, red[p])) for p in torches}
        if new == torches:
            break
        torches = new
    else:
        raise RuntimeError("el circuito no se estabiliza")

    def powered(p):
        for d in DIRS6:
            n = add(p, d)
            if powered_block(n) or (n in lever_on and lever_on[n]):
                return True
            if n in torches and torches[n] and attached(n, red[n]) != p:
                return True
        for k, d in HOR.items():
            n = add(p, d)
            if n in dust and dust[n] and props(red[n]).get(OPP[k], "none") != "none":
                return True
        return False

    comp = {p: powered(p) for p, st in red.items() if bid(st) in ("sticky_piston", "piston", "redstone_lamp", "iron_door")}
    return dust, comp, torches


def comprobar_redstone(t):
    errs = []
    dust, comp, torches = simular(t, {})
    for p, pw in dust.items():
        if int(props(t.get(*p))["power"]) != pw:
            errs.append(f"polvo en {p} colocado con {props(t.get(*p))['power']}, debería tener {pw}")
    for p, lit in torches.items():
        if (props(t.get(*p))["lit"] == "true") != lit:
            errs.append(f"antorcha en {p} con estado incoherente al colocarse")
    for p, on in comp.items():
        st, b = t.get(*p), bid(t.get(*p))
        placed = {"sticky_piston": "extended", "piston": "extended", "redstone_lamp": "lit", "iron_door": "open"}[b]
        if (props(st)[placed] == "true") != on:
            errs.append(f"{b} en {p}: {placed}={props(st)[placed]} pero {'recibe' if on else 'no recibe'} señal al colocarse")
    for nombre, c in getattr(t, "circuitos", {}).items():
        if "levers" not in c:
            continue
        for combo in itertools.product((False, True), repeat=len(c["levers"])):
            _, comp, _ = simular(t, dict(zip(c["levers"], combo)))
            señal = all(comp[p] for p in c["salida"])
            abre = señal if c["abre_si"] == "con_potencia" else not any(comp[p] for p in c["salida"])
            if abre != (combo == tuple(c["solucion"])):
                errs.append(f"puzle {nombre}: con palancas {combo} {'abre' if abre else 'no abre'}")
    c = t.circuitos.get("cable")
    if c:
        for h in c["ganchos"]:
            st = t.get(*h)
            f = props(st)["facing"]
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
