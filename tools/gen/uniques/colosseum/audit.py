"""Colosseum's own audit (condition for generating) and floor plans/renders for docs/unicas/coliseo/.

Checks on the complete world (main piece + hypogeum):
  - walkthrough on foot from outside, without jumps or falls of more than one block, and from each cell you can return;
  - with the puzzles solved: chests, lever, frame, trapdoors, stairs and guardian within reach;
  - with the puzzles unsolved: the hidden chests and the treasure chamber are not reached;
  - nothing floating (every block joined to the ground of its piece), block light 0 around the spawners;
  - consistent redstone states when generated; jigsaws intact and aligned; ruin percentage.
Use: python3 tools/gen/uniques/colosseum/audit.py [--blueprints]
"""
import os, sys
from collections import deque

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lint import passable, bname, support_issues
from uniques.colosseum import blueprint
from uniques.colosseum.blueprint import CX, CZ, NX, NZ, COLS
from uniques._common import walkthrough as R, redstone

H4 = R.H4
START = (CX + 43, 0, CZ)
LIMITS = (-2, NX + 1, -2, NZ + 1)


def view(o, solved):
    return R.View({p: v[0] for p, v in o.t.blocks.items()}, o.solved if solved else None, floor_y=-1)


def ruin_ratio(o):
    intact = blueprint.construct(ruin_piece=False)[0].t.blocks
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


def audit_it(o, main, hyp, report=None):
    msgs = []
    P = o.P
    # jigsaws
    for t in (main, hyp):
        for m, pos in support_issues(t):
            msgs.append(f"{t.name}: {m} en {pos}")
    jm, jh = main.jigsaws[0]["pos"], hyp.jigsaws[0]["pos"]
    if (jm[0], jm[1] - 1, jm[2]) != jh:
        msgs.append(f"jigsaws desalineados {jm} {jh}")
    # walkthrough with the puzzles solved
    seen, edges = R.strict_walk(view(o, True), START, LIMITS)
    cells = set(seen)
    noret = R.no_return(edges, START, o.ruined)
    if noret:
        msgs.append(f"{len(noret)} cells with no way back to the entrance, e.g. {sorted(noret)[:5]}")
    for label, table, p in o.feat["cofre"]:
        if not R.nearby_flag(cells, P(*p)):
            msgs.append(f"unreachable chest: {label} {p}")
    for kind in ("palanca", "marco", "guardian", "puzle", "trampa", "escalera", "puerta"):
        for label, p in o.feat[kind]:
            if not R.nearby_flag(cells, P(*p), 2):
                msgs.append(f"{kind} inaccesible: {label} {p}")
    for p, (st, _) in o.t.blocks.items():
        if bname(st) == "ladder" and p not in cells:
            msgs.append(f"escalera de mano inaccesible en {p}")
        if bname(st) in ("barrel",) and not R.nearby_flag(cells, p):
            msgs.append(f"barril inaccesible en {p}")
    # with the puzzles closed, the hidden parts are not reached
    seen_c, _ = R.strict_walk(view(o, False), START, LIMITS)
    hidden = [f for f in o.feat["cofre"] if "oculto" in f[0] or f[1] == "premium"]
    for label, table, p in hidden:
        if R.nearby_flag(set(seen_c), P(*p)):
            msgs.append(f"hidden chest reachable without solving puzzles: {label}")
    # nada flotando
    fl = R.floating_blocks({p: v[0] for p, v in o.t.blocks.items()}, (0, blueprint.HYP[4]))
    if fl:
        msgs.append(f"{len(fl)} floating blocks, e.g. {[(p, o.t.blocks[p][0]) for p in fl[:4]]}")
    # light at the spawners
    lv = R.light({p: v[0] for p, v in o.t.blocks.items()})
    for label, mob, p in o.feat["generador"]:
        mx = R.light_generator(lv, P(*p))
        if mx > 0:
            msgs.append(f"light {mx} next to spawner {label}")
    # redstone: stable states when generated (common simulation) and the puzzle 2 lever opens the door
    errs, _ = redstone.check_static(o.t)
    msgs += errs
    lever = P(*o.feat["palanca"][0][1])
    sim = redstone.Sim(o.t, {lever: True})
    door = P(*o.feat["puzle"][1][1]) if "pistones" in o.feat["puzle"][1][0] else P(*o.feat["puzle"][0][1])
    for (x, y, z), (st, _) in o.t.blocks.items():
        if bname(st) == "sticky_piston" and abs(x - door[0]) + abs(z - door[2]) <= 2 and sim.powered((x, y, z)):
            msgs.append(f"with the lever on, piston {(x, y, z)} still has a signal")
    # ruina
    dmg, tot = ruin_ratio(o)
    pct = 100.0 * dmg / tot
    if not 15.0 <= pct <= 20.0:
        msgs.append(f"ruin {pct:.1f} % of the surface (target 15-20 %)")
    if report is not None:
        report.update(seen=seen, closed=seen_c, ruin_piece=(dmg, tot, pct), light=lv)
    return msgs


# ------------------------------------------------------------------ floor plans and renders
LEVELS = [(-13, "Hipogeo H2 (oculto)"), (-6, "Hipogeo H1"), (1, "Planta baja G1 y arena"), (5, "Podio y palcos"),
          (8, "Galería G2"), (11, "Pasillo I"), (19, "Terraza superior")]


def blueprints(o, rep, outdir):
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
    out = ["Planos del Coliseo en ruinas (generados por auditoria.py --blueprints)",
           "Leyenda: '.' celda alcanzable a pie a esa altura, ',' alcanzable 1-2 bloques más arriba o abajo,",
           "'#' bloque sólido a la altura del cuerpo, 'H' escalera de mano, C cofre, S generador, T trampa, P puzle,",
           "G guardián. Norte arriba; x crece hacia la derecha. Puzles resueltos.", ""]
    for y, name in LEVELS:
        out.append(f"== {name}: pisa en y={y} ==")
        for z in range(-1, NZ + 1):
            row = []
            for x in range(-1, NX + 1):
                if y < 0 and not (blueprint.HYP[0] - 1 <= x - CX <= blueprint.HYP[1] + 1 and blueprint.HYP[2] - 1 <= z - CZ <= blueprint.HYP[3] + 1):
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
    o, main, hyp, offs = blueprint.construct()
    rep = {}
    msgs = audit_it(o, main, hyp, rep)
    d, t, pct = rep["ruin_piece"]
    print(f"celdas alcanzables: {len(rep['seen'])}; ruina {d}/{t} = {pct:.1f} %")
    for m in msgs:
        print("AVISO:", m)
    if "--blueprints" in sys.argv:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        outdir = os.path.join(root, "docs", "unicas", "coliseo")
        os.makedirs(outdir, exist_ok=True)
        blueprints(o, rep, outdir)
        renders(main, hyp, outdir)
        print("floor plans and renders in", outdir)
    sys.exit(1 if msgs else 0)
