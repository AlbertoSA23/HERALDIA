"""Text floor plans (cells reachable with the puzzles solved) and isometric renders of the palace.

Usage: python3 -m uniques.palace.planos  (from tools/gen)  -> docs/unicas/palacio/
"""
import os, sys
from lint import bname, passable
from . import palace, audit
from render import render

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs", "unicas", "palacio")
LEVELS = [(2, "ground floor (courtyards) and interior of the platform"), (3, "buildings on the base and garden"),
          (8, "throne hall (feet at 8)"), (10, "Midday Gate pavilion"),
          (13, "pagoda, piso 3"), (23, "pagoda, floor 5 (chest)")]
SYM = [("chest", "C"), ("barrel", "C"), ("trapped_chest", "T"), ("spawner", "S"), ("lever", "L"), ("piston", "P"),
       ("dispenser", "D"), ("tripwire", "t"), ("pressure_plate", "t"), ("ladder", "H"), ("_door", "d"), ("water", "~"),
       ("lectern", "a"), ("_bed", "b")]


def floor_plan(t, cells, y):
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
    o, good, errs = palace()
    if errs:
        print("audit:", errs)
        return 1
    _, cells = audit.check_walk(o)
    os.makedirs(OUT, exist_ok=True)
    ratio = audit.ruin_ratio(good, o.t)
    head = ("Legend: . reachable (feet at this height, puzzles solved)  # solid  C chest/barrel  T trapped chest  "
            "S spawner  L lever  P piston  D dispenser  t wire/plate  H ladder  d door  ~ water  "
            "a lectern  b bed\nNorth (gate) at the top; x from west to east.\n")
    with open(os.path.join(OUT, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write(f"Oriental palace: {len(cells)} reachable cells, ruin {ratio[0]:.1%} of the surface.\n{head}")
        for y, title in LEVELS:
            f.write(f"\n=== y = {y}: {title} ===\n{floor_plan(o.t, cells, y)}\n")
    render(o.t, os.path.join(OUT, "iso.png"), scale=3)
    render(o.t, os.path.join(OUT, "iso_corte_y5.png"), scale=3, cut_y=5)
    print("ok", len(cells), f"{ratio[0]:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
