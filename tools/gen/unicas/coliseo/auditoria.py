"""Auditoría propia del Coliseo (condición para generar) y planos/renders para docs/unicas/coliseo/.

Comprueba sobre el mundo completo (pieza principal + hipogeo):
  - recorrido a pie desde fuera, sin saltos ni caídas de más de un bloque, y que desde cada celda se puede volver;
  - con los puzles resueltos: cofres, palanca, marco, trampillas, escaleras y guardián al alcance;
  - con los puzles sin resolver: los cofres ocultos y la cámara del tesoro no se alcanzan;
  - nada flotando (todo bloque unido al suelo de su pieza), luz de bloque 0 alrededor de los generadores;
  - estados de redstone coherentes al generarse; jigsaws intactos y alineados; porcentaje de ruina.
Uso: python3 tools/gen/unicas/coliseo/auditoria.py [--planos]
"""
import os, sys
from collections import deque

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lint import passable, top_height, bname, prop, support_issues
from unicas.coliseo import plano
from unicas.coliseo.plano import CX, CZ, NX, NZ, COLS, is_full

FACE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
H4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Vista:
    """Mundo con suelo virtual fuera de la estructura y, opcionalmente, los puzles resueltos."""

    def __init__(self, o, solved):
        self.b = {p: v[0] for p, v in o.t.blocks.items()}
        if solved:
            for p, st in o.solved.items():
                self.b[p] = "minecraft:" + st if ":" not in st else st

    def get(self, x, y, z):
        st = self.b.get((x, y, z))
        if st is None and y == -1:
            return "minecraft:grass_block"
        if st is not None and bname(st) == "air":
            return None
        return st


def walker(v, start):
    g = v.get

    def surf(x, y, z, mdx, mdz):
        st = g(x, y, z)
        h = top_height(st)
        if st is not None and bname(st).endswith("_stairs") and "half=bottom" in st:
            fx, fz = FACE[prop(st, "facing")]
            return (y + 0.5 if (mdx, mdz) == (fx, fz) else y + 1.0, y + 1.0)
        if h is not None and h <= 0.6:
            return (y + h, y + h)
        if h is not None:
            return None
        below = g(x, y - 1, z)
        if below is None:
            return None
        hb = top_height(below)
        if hb is None:
            return (float(y), float(y)) if bname(below) == "ladder" else None
        if hb != 1.0 or (bname(below).endswith("_stairs") and "half=bottom" in below):
            return None
        return (float(y), float(y))

    def headroom(x, y, z, s):
        top = s + 1.8
        cy = y + 1
        while cy < top:
            st = g(x, cy, z)
            if not passable(st):
                low = cy + (0.5 if ("half=top" in st or "type=top" in st) else 0.0)
                if low < top:
                    return False
            cy += 1
        return True

    seen = {start: float(start[1])}
    edges = {}
    q = deque([start])
    while q:
        x, y, z = q.popleft()
        s = seen[(x, y, z)]
        out = []
        for dx, dz in H4:
            nx, nz = x + dx, z + dz
            if not (-2 <= nx <= NX + 1 and -2 <= nz <= NZ + 1):
                continue
            for ny in (y + 1, y, y - 1, y - 2):
                r = surf(nx, ny, nz, dx, dz)
                if r is None:
                    continue
                enter, stand = r
                if enter - s > 0.6 or stand > s + 1.01 or stand < s - 1.01:
                    continue
                if not headroom(nx, ny, nz, stand):
                    continue
                out.append(((nx, ny if stand < ny + 1 else ny + 1, nz), stand))
                break
        here = g(x, y, z)
        if bname(here) == "ladder" or (bname(g(x, y - 1, z)) == "ladder" and passable(here)):
            for ny in (y + 1, y - 1):
                st = g(x, ny, z)
                if bname(st) == "ladder" or (bname(here) == "ladder" and passable(st)):
                    out.append(((x, ny, z), float(ny)))
        edges[(x, y, z)] = [c for c, _ in out]
        for c, st in out:
            if c not in seen:
                seen[c] = st
                q.append(c)
    return seen, edges


def back_reach(edges, start):
    rev = {}
    for a, bs in edges.items():
        for b in bs:
            rev.setdefault(b, []).append(a)
    ok = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        for a in rev.get(c, ()):
            if a not in ok:
                ok.add(a)
                q.append(a)
    return ok


def near(cells, p, r=1):
    x, y, z = p
    return any((x + a, y + b, z + c) in cells for a in range(-r, r + 1) for c in range(-r, r + 1)
               for b in (-1, 0, 1) if abs(a) + abs(c) <= r)


START = (CX + 43, 0, CZ)
LIGHT = {"lantern": 15, "torch": 14, "wall_torch": 14, "redstone_torch": 7, "redstone_wall_torch": 7, "glowstone": 15}


def light_map(o):
    b = o.t.blocks
    lv = {}
    q = deque()
    for p, (st, _) in b.items():
        n = LIGHT.get(bname(st))
        if n and "lit=false" not in st:
            lv[p] = n
            q.append(p)
    while q:
        p = q.popleft()
        n = lv[p] - 1
        if n <= 0:
            continue
        x, y, z = p
        for a, c, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            np_ = (x + a, y + c, z + d)
            st = b.get(np_, (None,))[0]
            if st is None or is_full(st):
                continue
            if lv.get(np_, 0) < n:
                lv[np_] = n
                q.append(np_)
    return lv


def floating(o):
    b = o.t.blocks
    solid = {p for p, (st, _) in b.items() if bname(st) not in ("air",)}
    seeds = [p for p in solid if p[1] in (0, plano.HYP[4])]
    seen = set(seeds)
    q = deque(seeds)
    while q:
        x, y, z = q.popleft()
        for a, c, d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + a, y + c, z + d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


def ruin_ratio(o):
    intact = plano.construir(ruina=False)[0].t.blocks
    cur = o.t.blocks
    def exposed(p):
        x, y, z = p
        st = intact[p][0]
        if y < 0 or bname(st) == "air":
            return False
        c = COLS.get((x - CX, z - CZ))
        if c is None or c.r < 0 and y > 0:
            return False
        up = intact.get((x, y + 1, z), (None,))[0]
        if up is None or bname(up) == "air":
            top = all(bname(intact.get((x, yy, z), ("minecraft:air",))[0]) == "air" for yy in range(y + 1, 28))
            if top:
                return True
        if c.r >= 22:
            for a, d in H4:
                cn = COLS.get((x - CX + a, z - CZ + d))
                n = intact.get((x + a, y, z + d), (None,))[0]
                if (cn is None or cn.r > c.r) and (n is None or bname(n) == "air"):
                    return True
        return False
    exp = [p for p in intact if exposed(p)]
    dmg = sum(1 for p in exp if cur.get(p, ("minecraft:air",))[0] != intact[p][0])
    return dmg, len(exp)


def auditar(o, main, hyp, report=None):
    msgs = []
    P = o.P
    # jigsaws
    for t in (main, hyp):
        for m, pos in support_issues(t):
            msgs.append(f"{t.name}: {m} en {pos}")
    jm, jh = main.jigsaws[0]["pos"], hyp.jigsaws[0]["pos"]
    if (jm[0], jm[1] - 1, jm[2]) != jh:
        msgs.append(f"jigsaws desalineados {jm} {jh}")
    # recorrido con puzles resueltos
    vs = Vista(o, True)
    seen, edges = walker(vs, START)
    cells = set(seen)
    back = back_reach(edges, START)
    noret = [c for c in cells if c not in back and (c[0], c[2]) not in o.ruined]
    if noret:
        msgs.append(f"{len(noret)} celdas sin vuelta a la entrada, p. ej. {sorted(noret)[:5]}")
    for label, table, p in o.feat["cofre"]:
        if not near(cells, P(*p)):
            msgs.append(f"cofre inaccesible: {label} {p}")
    for kind in ("palanca", "marco", "guardian", "puzle", "trampa", "escalera", "puerta"):
        for label, p in o.feat[kind]:
            if not near(cells, P(*p), 2):
                msgs.append(f"{kind} inaccesible: {label} {p}")
    for p, (st, _) in o.t.blocks.items():
        if bname(st) == "ladder" and p not in cells:
            msgs.append(f"escalera de mano inaccesible en {p}")
        if bname(st) in ("barrel",) and not near(cells, p):
            msgs.append(f"barril inaccesible en {p}")
    # con los puzles cerrados lo oculto no se alcanza
    seen_c, _ = walker(Vista(o, False), START)
    hidden = [f for f in o.feat["cofre"] if "oculto" in f[0] or f[1] == "premium"]
    for label, table, p in hidden:
        if near(set(seen_c), P(*p)):
            msgs.append(f"cofre oculto alcanzable sin resolver puzles: {label}")
    # nada flotando
    fl = floating(o)
    if fl:
        msgs.append(f"{len(fl)} bloques flotando, p. ej. {[(p, o.t.blocks[p][0]) for p in fl[:4]]}")
    # luz en los generadores
    lv = light_map(o)
    for label, mob, p in o.feat["generador"]:
        x, y, z = P(*p)
        mx = max([lv.get((x + a, y + b, z + c), 0) for a in range(-4, 5) for c in range(-4, 5) for b in (-1, 0, 1)])
        if mx > 0:
            msgs.append(f"luz {mx} junto al generador {label}")
    # redstone coherente
    for p, (st, _) in o.t.blocks.items():
        b = bname(st)
        if b == "sticky_piston" and "extended=true" in st:
            f = prop(st, "facing")
            d = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}[f]
            h = o.t.get(p[0] + d[0], p[1], p[2] + d[2])
            if not h or "piston_head" not in h or f"facing={f}" not in h:
                msgs.append(f"pistón extendido sin cabeza en {p}")
        if b in ("lever", "comparator", "stone_pressure_plate", "tripwire_hook", "tripwire") and "powered=true" in st:
            msgs.append(f"{b} encendido al generarse en {p}")
        if b == "dispenser" and "triggered=true" in st:
            msgs.append(f"dispensador disparado en {p}")
    # ruina
    dmg, tot = ruin_ratio(o)
    pct = 100.0 * dmg / tot
    if not 15.0 <= pct <= 20.0:
        msgs.append(f"ruina {pct:.1f} % de la superficie (objetivo 15-20 %)")
    if report is not None:
        report.update(seen=seen, closed=seen_c, ruina=(dmg, tot, pct), luz=lv)
    return msgs


# ------------------------------------------------------------------ planos y renders
LEVELS = [(-13, "Hipogeo H2 (oculto)"), (-6, "Hipogeo H1"), (1, "Planta baja G1 y arena"), (5, "Podio y palcos"),
          (8, "Galería G2"), (11, "Pasillo I"), (19, "Terraza superior")]


def planos(o, rep, outdir):
    seen = rep["seen"]
    cells = set(seen)
    marks = {}
    for label, t, p in o.feat["cofre"]:
        marks[o.P(*p)] = "C"
    for label, m, p in o.feat["generador"]:
        marks[o.P(*p)] = "S"
    for label, p in o.feat["trampa"]:
        marks[o.P(*p)] = "T"
    for label, p in o.feat["puzle"] + o.feat["palanca"] + o.feat["marco"]:
        marks[o.P(*p)] = "P"
    for label, p in o.feat["guardian"]:
        marks[o.P(*p)] = "G"
    out = ["Planos del Coliseo en ruinas (generados por auditoria.py --planos)",
           "Leyenda: '.' celda alcanzable a pie a esa altura, ',' alcanzable 1-2 bloques más arriba o abajo,",
           "'#' bloque sólido a la altura del cuerpo, 'H' escalera de mano, C cofre, S generador, T trampa, P puzle,",
           "G guardián. Norte arriba; x crece hacia la derecha. Puzles resueltos.", ""]
    for y, name in LEVELS:
        out.append(f"== {name}: pisa en y={y} ==")
        for z in range(-1, NZ + 1):
            row = []
            for x in range(-1, NX + 1):
                if y < 0 and not (plano.HYP[0] - 1 <= x - CX <= plano.HYP[1] + 1 and plano.HYP[2] - 1 <= z - CZ <= plano.HYP[3] + 1):
                    row.append(" ")
                    continue
                ch = " "
                for yy in (y, y - 1):
                    if (x, yy, z) in marks:
                        ch = marks[(x, yy, z)]
                if ch == " ":
                    st = o.t.blocks.get((x, y, z), (None,))[0]
                    if st and bname(st) == "ladder":
                        ch = "H"
                    elif (x, y, z) in cells:
                        ch = "."
                    elif any((x, y + d, z) in cells for d in (-2, -1, 1, 2)):
                        ch = ","
                    elif st and not passable(st):
                        ch = "#"
                row.append(ch)
            line = "".join(row).rstrip()
            out.append(line)
        out.append("")
    with open(os.path.join(outdir, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def renders(main, hyp, outdir):
    from render import render
    from core import Template
    render(main, os.path.join(outdir, "coliseo.png"), scale=3)
    cut = Template("corte")
    cut.blocks = {p: v for p, v in main.blocks.items() if p[1] <= 6}
    render(cut, os.path.join(outdir, "coliseo_planta_baja.png"), scale=3)
    h = Template("hipogeo")
    h.blocks = {p: v for p, v in hyp.blocks.items() if bname(v[0]) not in ("stone",) and p[1] <= -3}
    render(h, os.path.join(outdir, "hipogeo.png"), scale=4)


if __name__ == "__main__":
    o, main, hyp, offs = plano.construir()
    rep = {}
    msgs = auditar(o, main, hyp, rep)
    d, t, pct = rep["ruina"]
    print(f"celdas alcanzables: {len(rep['seen'])}; ruina {d}/{t} = {pct:.1f} %")
    for m in msgs:
        print("AVISO:", m)
    if "--planos" in sys.argv:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        outdir = os.path.join(root, "docs", "unicas", "coliseo")
        os.makedirs(outdir, exist_ok=True)
        planos(o, rep, outdir)
        renders(main, hyp, outdir)
        print("planos y renders en", outdir)
    sys.exit(1 if msgs else 0)
