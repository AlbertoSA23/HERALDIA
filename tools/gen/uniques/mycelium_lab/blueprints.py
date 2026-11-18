"""Planos de planta por nivel (celdas alcanzables a pie con los puzles resueltos) y renders isométricos del Laboratorio
del micólogo. Uso: python3 tools/gen/uniques/mycelium_lab/blueprints.py [carpeta]
(por defecto docs/unicas/laboratorio_micelio)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from core import Template                     # noqa: E402
from pack import Registry                     # noqa: E402
from lint import bname, passable              # noqa: E402
from render import render                     # noqa: E402
import uniques.mycelium_lab as M        # noqa: E402
from uniques.mycelium_lab.construction import W, D, F1, F2, CAP, LOW   # noqa: E402

LEVELS = [(F2, "Galerías, nivel bajo: galería de la luz, capullos, experimentos, reactivos, cepa madre y tesoro",
           8, 58, 16, 60),
          (F1, "Galerías, nivel alto: criaderos, laboratorio, cepario, pasillo del cable trampa y criadero abandonado",
           8, 61, 7, 33),
          (1, "El jardín: champiñones, invernadero, destilería y corral", 0, W - 1, 0, D - 1),
          (LOW, "Pasarela baja y dormitorio de los ayudantes (sombrero pequeño)", 2, 40, 20, 40),
          (CAP, "Casa del micólogo (sombrero grande), pasarela alta y secadero", 20, 60, 5, 46)]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_",
        "redstone_wire": "r", "redstone_wall_torch": "i", "polished_andesite": "R", "brewing_stand": "A",
        "red_wall_banner": "b", "brown_wall_banner": "b", "water": "~", "spruce_stairs": "/", "farmland": "=",
        "soul_sand": "=", "iron_bars": "|", "spruce_fence": "+", "spruce_door": "d"}


def floor_plans(blocks, cells):
    g = lambda x, y, z: blocks.get((x, y, z))
    feet = {}
    for (x, y, z) in cells:
        feet.setdefault((x, z), set()).add(y)
    out = ["Leyenda: · alcanzable a pie (puzles resueltos)  # muro  C cofre  T tonel  G generador  D dispensador",
           "         P pistón  L palanca  r redstone  i antorcha de redstone  R frasco de reactivo  / escalera",
           "         ^ cable trampa  _ placa  b tapiz  A alambique  ~ agua  = bancal  | barrotes  + valla  d puerta",
           "         H escalera de mano; x de oeste a este, z de norte a sur (la entrada está al norte, z = 0)", ""]
    for lv, title, x0, x1, z0, z1 in LEVELS:
        out.append(f"== {title} (pies a y = {lv}) ==")
        out.append("    " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                ch = " "
                for y in (lv, lv + 1, lv - 1):
                    st = g(x, y, z)
                    if st and bname(st) in MARK and (y != lv - 1 or bname(st) in ("water", "farmland", "soul_sand")):
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
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "..", "docs", "unicas",
                                                                 "laboratorio_micelio")
    os.makedirs(dest, exist_ok=True)
    reg = Registry()
    M.build(reg)
    o = M.REPORT["obra"]
    blocks = M.REPORT["abierto"]
    with open(os.path.join(dest, "planos.txt"), "w", encoding="utf-8") as f:
        f.write(floor_plans(blocks, o.cells) + "\n")
    area = reg.templates["unicas/laboratorio_micelio/jardin"]
    render(area, os.path.join(dest, "jardin.png"), scale=3)
    render(area, os.path.join(dest, "jardin_sur.png"), scale=3, flip=True)
    low = Template("sin_sombreros")              # el jardín cortado bajo los sombreros
    low.blocks = {p: v for p, v in area.blocks.items() if p[1] <= 8}
    low.normalize()
    render(low, os.path.join(dest, "jardin_corte.png"), scale=3)
    under = Template("corte")                    # las galerías sin la roca de relleno
    under.blocks = {p: v for p, v in o.t.blocks.items() if p[1] < 0 and bname(v[0]) not in ("stone", "dirt", "air")}
    y0 = min(p[1] for p in under.blocks)
    under.normalize()
    render(under, os.path.join(dest, "galerias.png"), scale=4)
    render(under, os.path.join(dest, "galerias_corte_alto.png"), scale=4, cut_y=F1 + 2 - y0)
    render(under, os.path.join(dest, "galerias_corte_bajo.png"), scale=4, cut_y=F2 + 2 - y0)
    print("planos y renders en", os.path.abspath(dest))


if __name__ == "__main__":
    main()
