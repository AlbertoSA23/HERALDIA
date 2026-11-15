"""Planos de planta por nivel (celdas alcanzables a pie con los puzles resueltos) y renders isométricos del Salón del
Jarl. Uso: python3 tools/gen/unicas/salon_jarl/planos.py [carpeta]   (por defecto docs/unicas/salon_jarl)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from core import Template                     # noqa: E402
from pack import Registry                     # noqa: E402
from lint import bname, passable              # noqa: E402
from render import render                     # noqa: E402
import unicas.salon_jarl as M                 # noqa: E402
from unicas.salon_jarl.obra import W, D, F1, F2   # noqa: E402

LEVELS = [(F2, "Túmulo, nivel bajo: cámara del jarl y tesoro", 10, 40, 44, 73),
          (F1, "Túmulo, nivel alto: galerías, osario, ofrendas, runas", 10, 64, 28, 73),
          (1, "Planta baja: patio, casa larga y talleres", 0, W - 1, 0, D - 1),
          (5, "Adarve, sala de la puerta y torres", 0, W - 1, 0, D - 1),
          (10, "Atalayas de las torres", 0, W - 1, 0, D - 1)]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_", "tnt": "!",
        "campfire": "F", "redstone_wire": "r", "redstone_wall_torch": "i", "chiseled_tuff": "R",
        "red_wall_banner": "b", "black_wall_banner": "b"}


def plans(blocks, cells):
    g = lambda x, y, z: blocks.get((x, y, z))
    feet = {}
    for (x, y, z) in cells:
        feet.setdefault((x, z), set()).add(y)
    out = ["Leyenda: · alcanzable a pie (puzles resueltos)  # muro  C cofre  T tonel  G generador  D dispensador",
           "         P pistón  L palanca  r redstone  i antorcha de redstone  R piedra rúnica  H escalera de mano",
           "         ^ cable trampa  _ placa  ! dinamita (bajo el suelo)  F hoguera  b tapiz",
           "         x de oeste a este, z de norte a sur (la puerta del recinto está al norte, z = 0)", ""]
    for lv, title, x0, x1, z0, z1 in LEVELS:
        out.append(f"== {title} (pies a y = {lv}) ==")
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
    o = M.REPORT["obra"]
    blocks = M.REPORT["abierto"]
    with open(os.path.join(dest, "planos.txt"), "w", encoding="utf-8") as f:
        f.write(plans(blocks, o.cells) + "\n")
    sup = reg.templates["unicas/salon_jarl/salon"]
    render(sup, os.path.join(dest, "salon.png"), scale=3)
    render(sup, os.path.join(dest, "salon_sur.png"), scale=3, flip=True)
    render(sup, os.path.join(dest, "corte_planta_baja.png"), scale=3, cut_y=5)
    crypt = Template("corte")                    # el túmulo sin la roca de relleno
    crypt.blocks = {p: v for p, v in o.t.blocks.items() if p[1] < 0 and bname(v[0]) not in ("stone", "dirt", "air")}
    crypt.normalize()
    render(crypt, os.path.join(dest, "tumulo.png"), scale=4)
    render(crypt, os.path.join(dest, "tumulo_corte_alto.png"), scale=4, cut_y=F1 + 2 - min(p[1] for p in o.t.blocks))
    print("planos y renders en", os.path.abspath(dest))


if __name__ == "__main__":
    main()
