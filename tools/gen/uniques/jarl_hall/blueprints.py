"""Floor plans by level (cells reachable on foot with the puzzles solved) and isometric renders of Jarl's
Hall. Usage: python3 tools/gen/uniques/jarl_hall/blueprints.py [folder]   (default docs/unicas/salon_jarl)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from core import Template                     # noqa: E402
from pack import Registry                     # noqa: E402
from lint import bname, passable              # noqa: E402
from render import render                     # noqa: E402
import uniques.jarl_hall as M                 # noqa: E402
from uniques.jarl_hall.construction import W, D, F1, F2   # noqa: E402

LEVELS = [(F2, "Barrow, lower level: jarl's chamber and treasure", 10, 40, 44, 73),
          (F1, "Barrow, upper level: galleries, ossuary, offerings, runes", 10, 64, 28, 73),
          (1, "Ground floor: courtyard, longhouse and workshops", 0, W - 1, 0, D - 1),
          (5, "Wall walk, gatehouse and towers", 0, W - 1, 0, D - 1),
          (10, "Tower lookouts", 0, W - 1, 0, D - 1)]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_", "tnt": "!",
        "campfire": "F", "redstone_wire": "r", "redstone_wall_torch": "i", "chiseled_tuff": "R",
        "red_wall_banner": "b", "black_wall_banner": "b"}


def floor_plans(blocks, cells):
    g = lambda x, y, z: blocks.get((x, y, z))
    feet = {}
    for (x, y, z) in cells:
        feet.setdefault((x, z), set()).add(y)
    out = ["Legend: · reachable on foot (puzzles solved)  # wall  C chest  T barrel  G spawner  D dispenser",
           "         P piston  L lever  r redstone  i redstone torch  R runestone  H ladder",
           "         ^ trap wire  _ plate  ! dynamite (under the floor)  F bonfire  b tapestry",
           "         x from west to east, z from north to south (the enclosure gate is on the north, z = 0)", ""]
    for lv, title, x0, x1, z0, z1 in LEVELS:
        out.append(f"== {title} (feet at y = {lv}) ==")
        out.append("    " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                ch = " "
                for y in (lv, lv + 1, lv - 2):
                    st = g(x, y, z)
                    if st and bname(st) in MARK and (y != lv - 2 or bname(st) == "tnt"):
                        ch = MARK[bname(st)]
                        break
                else:
                    if any(lv - 1 <= f <= lv + 1 for f in feet.get((x, z), ())):
                        ch = "·"
                    elif not passable(g(x, lv, z)) or not passable(g(x, lv + 1, z)):
                        ch = "#"
                row.append(ch)
            out.append(f"{z:3d} " + "".join(row).rstrip())
        out.append("")
    return "\n".join(out)


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "..", "docs", "unicas", "salon_jarl")
    os.makedirs(dest, exist_ok=True)
    reg = Registry()
    M.build(reg)
    o = M.REPORT["construction"]
    blocks = M.REPORT["abierto"]
    with open(os.path.join(dest, "planos.txt"), "w", encoding="utf-8") as f:
        f.write(floor_plans(blocks, o.cells) + "\n")
    area = reg.templates["unicas/salon_jarl/salon"]
    render(area, os.path.join(dest, "salon.png"), scale=3)
    render(area, os.path.join(dest, "salon_sur.png"), scale=3, flip=True)
    render(area, os.path.join(dest, "corte_planta_baja.png"), scale=3, cut_y=5)
    crypt = Template("corte")                    # the barrow without the filler rock
    crypt.blocks = {p: v for p, v in o.t.blocks.items() if p[1] < 0 and bname(v[0]) not in ("stone", "dirt", "air")}
    crypt.normalize()
    render(crypt, os.path.join(dest, "tumulo.png"), scale=4)
    render(crypt, os.path.join(dest, "tumulo_corte_alto.png"), scale=4, cut_y=F1 + 2 - min(p[1] for p in o.t.blocks))
    print("floor plans and renders in", os.path.abspath(dest))


if __name__ == "__main__":
    main()
