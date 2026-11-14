"""Planos de planta por nivel (celdas alcanzables a pie) y renders isométricos de la fortaleza de hielo.

Uso: python3 tools/gen/unicas/fortaleza_hielo/planos.py [carpeta]   (por defecto docs/unicas/fortaleza_hielo)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from pack import Registry                     # noqa: E402
from lint import walk, bname, passable        # noqa: E402
from render import render                     # noqa: E402
import unicas.fortaleza_hielo as F            # noqa: E402

LEVELS = [(1, "Cámara del tesoro"), (6, "Criptas"), (11, "Patio y planta baja"), (20, "Adarve"), (26, "Atalayas")]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_",
        "powder_snow": "~", "campfire": "F", "redstone_wire": "r"}


def plans(t, cells):
    feet = {}
    for (x, y, z), s in cells.items():
        feet.setdefault((x, z), set()).add(int(s + 0.01))
    out = ["Leyenda: · alcanzable a pie (puertas secretas abiertas)  # muro  C cofre  T tonel  G generador  D dispensador",
           "         P pistón  L palanca  H escalera de mano  ^ cable trampa  _ placa  ~ nieve polvo  F hoguera  r redstone",
           "         x de oeste a este, z de norte a sur (la entrada está al norte, z = 0)", ""]
    for lv, title in LEVELS:
        out.append(f"== {title} (pie a y = {lv}) ==")
        for z in range(0, F.construir.D):
            row = []
            for x in range(F.construir.W):
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
        f.write(plans(view, cells) + "\n")
    render(t, os.path.join(dest, "fortaleza.png"), scale=3)
    render(t, os.path.join(dest, "corte_planta_baja.png"), scale=3, cut_y=15)
    render(t, os.path.join(dest, "corte_criptas.png"), scale=3, cut_y=9)
    print(f"{len(cells)} celdas alcanzables; superficie dañada estimada {F.REPORT['damaged']:.1%}; avisos: {reg.warnings}")


if __name__ == "__main__":
    main()
