"""Text floor plans (cells reachable on foot) and isometric renders of the galleon.

Usage (from tools/gen): python3 unicas/galeon/blueprints.py <mcmeta registries> <output folder>
"""
import os, sys

LEVELS = [(-7, "Treasure chamber"), (-5, "Cave and gallery"), (-4, "Bodega"), (1, "Beach, camp and gun deck"),
          (5, "Cubierta principal"), (9, "Castillo de proa"), (10, "Quarterdeck and cabin"), (15, "Toldilla"), (23, "Cofa")]
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
    lines = ["Stranded Galleon: floor plans by level (y = feet height; 0 = sea level). Rows: Z from bow (top) to stern;",
             "columns: X from land (left) to sea. '.' cell reachable on foot from the entrance; '#' wall or block;",
             "C chest, B barrel, D door, H ladder, / stairs, S generator, L lever, T trap, b bed, A suspicious sand, c bell.",
             f"Damaged surface (audit): {o.damage:.1%}.", ""]
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
        lines += [f"== y {yl:+d}: {title} ({n_reach} reachable cells) ==", *rows[nz[0]:nz[-1] + 1], ""]
    with open(os.path.join(out, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    render(t, os.path.join(out, "exterior.png"), scale=3)
    render(t, os.path.join(out, "corte_cubierta_canones.png"), scale=3, cut_y=y_sea + 3)
    render(t, os.path.join(out, "corte_bodega_cueva.png"), scale=3, cut_y=y_sea - 2)
    print("floor plans and renders in", out)


if __name__ == "__main__":
    main()
