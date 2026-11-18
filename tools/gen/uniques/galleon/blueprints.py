"""Planos de planta en texto (celdas alcanzables a pie) y renders isométricos del galeón.

Uso (desde tools/gen): python3 unicas/galeon/planos.py <registros mcmeta> <carpeta de salida>
"""
import os, sys

LEVELS = [(-7, "Cámara del tesoro"), (-5, "Cueva y galería"), (-4, "Bodega"), (1, "Playa, campamento y cubierta de cañones"),
          (5, "Cubierta principal"), (9, "Castillo de proa"), (10, "Alcázar y camarote"), (15, "Toldilla"), (23, "Cofa")]
CH = [("chest", "C"), ("barrel", "B"), ("_door", "D"), ("ladder", "H"), ("_stairs", "/"), ("spawner", "S"),
      ("lever", "L"), ("pressure_plate", "T"), ("tripwire", "T"), ("_bed", "b"), ("suspicious", "A"), ("bell", "c")]


def main():
    sys.path.insert(0, os.getcwd())
    from validate import load_registries
    load_registries(sys.argv[1])
    from pack import Registry
    from lint import walk, resolved, bname, passable
    from render import render
    import uniques.galleon as g
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    reg = Registry()
    o = g.build(reg)
    t = o.t
    v = resolved(t)
    cells = walk(t)
    sx, sy, sz = t.size()
    y_sea = g.STRUCTURE["json"]["anchor"][1]
    lines = ["Galeón varado: planos por nivel (y = altura de los pies; 0 = nivel del mar). Filas: Z de proa (arriba) a popa;",
             "columnas: X de tierra (izquierda) a mar. '.' celda alcanzable a pie desde la entrada; '#' muro o bloque;",
             "C cofre, B barril, D puerta, H escala, / escalera, S generador, L palanca, T trampa, b cama, A arena sospechosa, c campana.",
             f"Superficie dañada (auditoría): {o.damage:.1%}.", ""]
    for yl, title in LEVELS:
        y = y_sea + yl
        rows = []
        for z in range(sz):
            row = []
            for x in range(sx):
                st = v.get(x, y, z)
                c = " "
                if st is not None and bname(st) not in ("air", "structure_void"):
                    c = "#" if not passable(st) else ","
                    for k, ch in CH:
                        if k in bname(st):
                            c = ch
                if (x, y, z) in cells and c in (" ", ","):
                    c = "."
                row.append(c)
            rows.append("".join(row).rstrip())
        nz = [i for i, r in enumerate(rows) if r.strip()]
        if not nz:
            continue
        n_reach = sum(1 for c in cells if c[1] == y)
        lines += [f"== y {yl:+d}: {title} ({n_reach} celdas alcanzables) ==", *rows[nz[0]:nz[-1] + 1], ""]
    with open(os.path.join(out, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    render(t, os.path.join(out, "exterior.png"), scale=3)
    render(t, os.path.join(out, "corte_cubierta_canones.png"), scale=3, cut_y=y_sea + 3)
    render(t, os.path.join(out, "corte_bodega_cueva.png"), scale=3, cut_y=y_sea - 2)
    print("planos y renders en", out)


if __name__ == "__main__":
    main()
