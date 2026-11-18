"""Planos de planta por nivel (celdas alcanzables a pie con los puzles resueltos) y renders isométricos de la Mina
perdida. Uso: python3 tools/gen/uniques/lost_mine/blueprints.py [carpeta]   (por defecto docs/unicas/mina_perdida)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from core import Template                     # noqa: E402
from lint import bname, passable              # noqa: E402
from render import render                     # noqa: E402
import uniques.lost_mine as M               # noqa: E402
from uniques.lost_mine.construction import F_CHASM, F_DEEP, F_FLOODED   # noqa: E402

LEVELS = [(1, "La gran caverna (pies a y = 1): estación del pozo, almacén, fundición, casas, talleres, lago, sima, "
              "cargadero, frente viejo y sector derrumbado", -1, 104, -1, 78),
          (-4, "La bajada al sector inundado", 0, 20, 58, 78),
          (F_FLOODED, "El sector inundado (pasarela y agua)", 0, 20, 60, 78),
          (F_DEEP, "El filón madre y la cámara del tesoro (pies a y = -10)", 76, 104, -2, 26),
          (F_CHASM, "El fondo de la sima (pies a y = -15)", 70, 84, 22, 50)]
MARK = {"chest": "C", "barrel": "T", "spawner": "G", "dispenser": "D", "sticky_piston": "P", "piston_head": "P",
        "lever": "L", "ladder": "H", "tripwire_hook": "^", "tripwire": "^", "stone_pressure_plate": "_",
        "redstone_wall_torch": "i", "water": "~", "rail": "=", "powered_rail": "+", "detector_rail": "B",
        "spruce_fence": "|", "spruce_door": "d", "blast_furnace": "F", "anvil": "A", "tnt": "!", "bookshelf": "E"}


def floor_plans(blocks, cells):
    g = lambda x, y, z: blocks.get((x, y, z))
    feet = {}
    for (x, y, z) in cells:
        feet.setdefault((x, z), set()).add(y)
    out = ["Leyenda: · alcanzable a pie (puzles resueltos)  # roca o muro  C cofre  T tonel  G generador  D dispensador",
           "         P pistón  L palanca  i antorcha de redstone  = vía  + vía propulsora  B báscula (raíl detector)",
           "         ^ cable trampa  _ placa  ! dinamita  ~ agua  | barandilla  d puerta  F alto horno  A yunque",
           "         E estantería  H escalera de mano; x de oeste a este, z de norte a sur (el pozo baja en x 44, z 7)", ""]
    for lv, title, x0, x1, z0, z1 in LEVELS:
        out.append(f"== {title} ==")
        out.append("    " + "".join(str(x // 10 % 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)))
        for z in range(z0, z1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                ch = " "
                for y in (lv, lv + 1, lv - 1):
                    st = g(x, y, z)
                    if st and bname(st) in MARK and (y != lv - 1 or bname(st) in ("water", "tnt")):
                        ch = MARK[bname(st)]
                        break
                else:
                    if any(lv - 1 <= f <= lv + 1 for f in feet.get((x, z), ())):
                        ch = "·"
                    elif g(x, lv, z) is not None and (not passable(g(x, lv, z)) or not passable(g(x, lv + 1, z))):
                        ch = "#"
                row.append(ch)
            out.append(f"{z:3d} " + "".join(row).rstrip())
        out.append("")
    return "\n".join(out)


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "..", "docs", "unicas", "mina_perdida")
    os.makedirs(dest, exist_ok=True)
    tpls, meta, errors, _, rep = M.dataset()
    o = rep["obra"]
    sx, sy, sz = rep["desplazamiento"]
    blocks = rep["abierto"]
    with open(os.path.join(dest, "planos.txt"), "w", encoding="utf-8") as f:
        f.write(floor_plans(blocks, o.cells) + "\n")
    col, cast = tpls[0], tpls[1]
    render(cast, os.path.join(dest, "castillete.png"), scale=6)
    cavity = Template("corte")                      # la colonia sin la roca del casco ni el forro del techo
    for p, v in col.blocks.items():
        q = (p[0] + sx, p[1] + sy, p[2] + sz)
        b = bname(v[0])
        if q in o.hull or b in ("air", "cave_air"):
            continue
        if q not in o.carved and any((q[0], q[1] - k, q[2]) in o.carved for k in (1,)) and q[1] > 2:
            continue                               # techo: se quita para ver dentro
        cavity.blocks[p] = v
    cavity.normalize()
    render(cavity, os.path.join(dest, "colonia.png"), scale=3)
    render(cavity, os.path.join(dest, "colonia_corte.png"), scale=3, cut_y=1 + 5 - sy - min(p[1] for p in col.blocks))
    print("planos y renders en", os.path.abspath(dest), "; avisos:", len(errors))


if __name__ == "__main__":
    main()
