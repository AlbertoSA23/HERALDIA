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

from lint import passable, bname, support_issues
from unicas.coliseo import plano
from unicas.coliseo.plano import CX, CZ, NX, NZ, COLS
from unicas._comun import recorrido as R, redstone

H4 = R.H4
START = (CX + 43, 0, CZ)
LIMITES = (-2, NX + 1, -2, NZ + 1)


def vista(o, solved):
    return R.Vista({p: v[0] for p, v in o.t.blocks.items()}, o.solved if solved else None, suelo_y=-1)


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
    seen, edges = R.andar(vista(o, True), START, LIMITES)
    cells = set(seen)
    noret = R.sin_vuelta(edges, START, o.ruined)
    if noret:
        msgs.append(f"{len(noret)} celdas sin vuelta a la entrada, p. ej. {sorted(noret)[:5]}")
    for label, table, p in o.feat["cofre"]:
        if not R.cerca(cells, P(*p)):
            msgs.append(f"cofre inaccesible: {label} {p}")
    for kind in ("palanca", "marco", "guardian", "puzle", "trampa", "escalera", "puerta"):
        for label, p in o.feat[kind]:
            if not R.cerca(cells, P(*p), 2):
                msgs.append(f"{kind} inaccesible: {label} {p}")
    for p, (st, _) in o.t.blocks.items():
        if bname(st) == "ladder" and p not in cells:
            msgs.append(f"escalera de mano inaccesible en {p}")
        if bname(st) in ("barrel",) and not R.cerca(cells, p):
            msgs.append(f"barril inaccesible en {p}")
    # con los puzles cerrados lo oculto no se alcanza
    seen_c, _ = R.andar(vista(o, False), START, LIMITES)
    hidden = [f for f in o.feat["cofre"] if "oculto" in f[0] or f[1] == "premium"]
    for label, table, p in hidden:
        if R.cerca(set(seen_c), P(*p)):
            msgs.append(f"cofre oculto alcanzable sin resolver puzles: {label}")
    # nada flotando
    fl = R.flotantes({p: v[0] for p, v in o.t.blocks.items()}, (0, plano.HYP[4]))
    if fl:
        msgs.append(f"{len(fl)} bloques flotando, p. ej. {[(p, o.t.blocks[p][0]) for p in fl[:4]]}")
    # luz en los generadores
    lv = R.luz({p: v[0] for p, v in o.t.blocks.items()})
    for label, mob, p in o.feat["generador"]:
        mx = R.luz_generador(lv, P(*p))
        if mx > 0:
            msgs.append(f"luz {mx} junto al generador {label}")
    # redstone: estados estables al generarse (simulación común) y la palanca del puzle 2 abre la puerta
    errs, _ = redstone.check_static(o.t)
    msgs += errs
    lever = P(*o.feat["palanca"][0][1])
    sim = redstone.Sim(o.t, {lever: True})
    door = P(*o.feat["puzle"][1][1]) if "pistones" in o.feat["puzle"][1][0] else P(*o.feat["puzle"][0][1])
    for (x, y, z), (st, _) in o.t.blocks.items():
        if bname(st) == "sticky_piston" and abs(x - door[0]) + abs(z - door[2]) <= 2 and sim.powered((x, y, z)):
            msgs.append(f"con la palanca encendida el pistón {(x, y, z)} sigue con señal")
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
