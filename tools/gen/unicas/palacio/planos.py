"""Planos de planta en texto (celdas alcanzables con los puzles resueltos) y renders isométricos del palacio.

Uso: python3 -m unicas.palacio.planos  (desde tools/gen)  -> docs/unicas/palacio/
"""
import os, sys
from lint import bname, passable
from . import palacio, auditoria
from render import render

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs", "unicas", "palacio")
LEVELS = [(2, "planta baja (patios) e interior de la plataforma"), (3, "edificios sobre zócalo y jardín"),
          (8, "salón del trono (pies a 8)"), (10, "pabellón de la Puerta del Mediodía"),
          (13, "pagoda, piso 3"), (23, "pagoda, piso 5 (cofre)")]
SYM = [("chest", "C"), ("barrel", "C"), ("trapped_chest", "T"), ("spawner", "S"), ("lever", "L"), ("piston", "P"),
       ("dispenser", "D"), ("tripwire", "t"), ("pressure_plate", "t"), ("ladder", "H"), ("_door", "d"), ("water", "~"),
       ("lectern", "a"), ("_bed", "b")]


def plan(t, cells, y):
    x0, _, z0, x1, _, z1 = t.bounds()
    rows = []
    for z in range(z0, z1 + 1):
        r = []
        for x in range(x0, x1 + 1):
            st = t.get(x, y, z)
            b = bname(st) if st else "air"
            ch = next((c for k, c in SYM if k in b), None)
            if ch is None:
                if (x, y, z) in cells:
                    ch = "."
                elif not passable(st) and b != "air":
                    ch = "#"
                else:
                    ch = " "
            r.append(ch)
        rows.append("".join(r).rstrip())
    return "\n".join(rows)


def main():
    o, good, errs = palacio()
    if errs:
        print("auditoría:", errs)
        return 1
    _, cells = auditoria.check_walk(o)
    os.makedirs(OUT, exist_ok=True)
    ratio = auditoria.ruin_ratio(good, o.t)
    head = ("Leyenda: . alcanzable (pies a esta altura, puzles resueltos)  # macizo  C cofre/barril  T cofre trampa  "
            "S generador  L palanca  P pistón  D dispensador  t cable/placa  H escalera de mano  d puerta  ~ agua  "
            "a atril  b cama\nNorte (puerta) arriba; x de oeste a este.\n")
    with open(os.path.join(OUT, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write(f"Palacio oriental: {len(cells)} celdas alcanzables, ruina {ratio[0]:.1%} de la superficie.\n{head}")
        for y, title in LEVELS:
            f.write(f"\n=== y = {y}: {title} ===\n{plan(o.t, cells, y)}\n")
    render(o.t, os.path.join(OUT, "iso.png"), scale=3)
    render(o.t, os.path.join(OUT, "iso_corte_y5.png"), scale=3, cut_y=5)
    print("ok", len(cells), f"{ratio[0]:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
