"""Floor plans by level (cells reachable on foot) and isometric renders of the ice fortress.

Usage: python3 tools/gen/uniques/ice_fortress/blueprints.py [folder]   (default docs/unicas/fortaleza_hielo)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from pack import Registry                     # noqa: E402
from lint import walk, bname, passable        # noqa: E402
from render import render                     # noqa: E402
import uniques.ice_fortress as F            # noqa: E402

LEVELS = [(1, "Treasure chamber"), (6, "Criptas"), (11, "Courtyard and ground floor"), (20, "Adarve"), (26, "Atalayas")]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_",
        "powder_snow": "~", "campfire": "F", "redstone_wire": "r"}


def floor_plans(t, cells):
    feet = {}
    for (x, y, z), s in cells.items():
        feet.setdefault((x, z), set()).add(int(s + 0.01))
    out = ["Legend: · reachable on foot (secret doors open)  # wall  C chest  T barrel  G spawner  D dispenser",
           "         P piston  L lever  H ladder  ^ trap wire  _ plate  ~ powder snow  F bonfire  r redstone",
           "         x from west to east, z from north to south (the entrance is on the north, z = 0)", ""]
    for lv, title in LEVELS:
        out.append(f"== {title} (feet at y = {lv}) ==")
        for z in range(0, F.construct.D):
            row = []
            for x in range(F.construct.W):
                ch = " "
                for y in (lv, lv + 1):
                    st = t.get(x, y, z)
                    if st and bname(st) in MARK:
                        ch = MARK[bname(st)]
                        break
                else:
                    if any(lv - 1 <= f <= lv + 1 for f in feet.get((x, z), ())):
                        ch = "·"
                    elif not passable(t.get(x, lv, z)) or not passable(t.get(x, lv + 1, z)):
                        ch = "#"
                row.append(ch)
            out.append(f"{z:3d} " + "".join(row).rstrip())
        out.append("")
    return "\n".join(out)


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "..", "docs", "unicas", "fortaleza_hielo")
    os.makedirs(dest, exist_ok=True)
    reg = Registry()
    F.build(reg)
    t = reg.templates["unicas/fortaleza_hielo/fortaleza"]
    view = t.lint_view
    cells = walk(view)
    with open(os.path.join(dest, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write(floor_plans(view, cells) + "\n")
    render(t, os.path.join(dest, "fortaleza.png"), scale=3)
    render(t, os.path.join(dest, "corte_planta_baja.png"), scale=3, cut_y=15)
    render(t, os.path.join(dest, "corte_criptas.png"), scale=3, cut_y=9)
    print(f"{len(cells)} reachable cells; estimated damaged surface {F.REPORT['damaged']:.1%}; warnings: {reg.warnings}")


if __name__ == "__main__":
    main()
