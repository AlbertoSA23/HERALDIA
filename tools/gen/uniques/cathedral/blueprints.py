"""Text floor plans (reachable cells) and isometric renders of the cathedral.

python3 -m uniques.cathedral.planos <folder>   (from tools/gen)"""
import os, sys
from lint import bname
from .audit import passable, top_height

LEVELS = [(-7, "Crypt, ossuaries and treasure chamber (feet at -7)"), (1, "Planta baja (pies en 1)"),
          (9, "Library and closet (feet at 9)"), (12, "Triforium, gallery and high walkways (feet at 12)"),
          (17, "Terraces over the side aisles (feet at 17)"), (28, "Gutter, facade terrace and attic (feet at 28)"),
          (40, "Campanario (pies en 40)"), (56, "Tower roofs (feet at 56)")]
MARK = {"chest": "C", "barrel": "C", "spawner": "G", "lever": "L", "ladder": "H", "sticky_piston": "P", "piston_head": "P",
        "tripwire": "T", "tripwire_hook": "T", "stone_pressure_plate": "T", "dispenser": "D", "iron_trapdoor": "Z", "bell": "B"}


def floor_plan(c, y, cells, x0=-2, x1=118, z0=2, z1=89):
    rows = []
    for z in range(z0, z1 + 1):
        row = []
        for x in range(x0, x1 + 1):
            ch = " "
            for yy in (y, y + 1, y - 1):
                b = bname(c.t.get(x, yy, z))
                if b in MARK:
                    ch = MARK[b]
                    break
            else:
                st = c.t.get(x, y, z)
                if (x, y, z) in cells or (x, y + 1, z) in cells and False:
                    ch = "."
                elif any((x, yy, z) in cells for yy in (y - 1, y + 1)):
                    ch = ","
                elif st is not None and bname(st) != "air" and not passable(st):
                    ch = "#"
                elif bname(st).endswith("_door") if st else False:
                    ch = "|"
                elif st is not None and bname(st) == "air":
                    ch = "o" if (c.t.get(x, y - 1, z) and top_height(c.t.get(x, y - 1, z)) == 1.0) else " "
            row.append(ch)
        rows.append("".join(row).rstrip())
    return "\n".join(rows).rstrip("\n")


def write(c, folder):
    os.makedirs(folder, exist_ok=True)
    out = ["Cathedral floor plans by level. Legend: '.' cell reachable on foot (at that height), ',' reachable half a block",
           "or one block up/down (stairs), '#' wall or block, 'o' floor with unreachable ceiling, 'C' chest, 'G' spawner,",
           "'L' lever, 'P' piston, 'T' trap (wire or plate), 'D' dispenser, 'H' ladder, 'Z' trapdoor, 'B' bell.",
           "x grows to the right (west facade on the left), z downward (north up).", ""]
    for y, title in LEVELS:
        out += [f"== {title} ==", floor_plan(c, y, c.audit_cells), ""]
    with open(os.path.join(folder, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def renders(c, folder):
    from render import render
    from core import Template
    t = Template("r")
    t.blocks = {p: v for p, v in c.t.blocks.items() if p[1] >= 0}
    render(t, os.path.join(folder, "exterior.png"), scale=3)
    render(t, os.path.join(folder, "fachada.png"), scale=3, flip=True)
    t2 = Template("r2")
    t2.blocks = {(x, y + 8, z): v for (x, y, z), v in c.t.blocks.items() if y < 0 or (y <= 1 and False)}
    render(t2, os.path.join(folder, "cripta.png"), scale=4)
    t3 = Template("r3")
    t3.blocks = {p: v for p, v in c.t.blocks.items() if 0 <= p[1]}
    render(t3, os.path.join(folder, "corte_planta_baja.png"), scale=3, cut_y=6)


if __name__ == "__main__":
    from . import model
    from .audit import audit
    c = model()
    for p in audit(c, verbose=True):
        print(p[:300])
    write(c, sys.argv[1])
    if len(sys.argv) > 2:
        renders(c, sys.argv[1])
