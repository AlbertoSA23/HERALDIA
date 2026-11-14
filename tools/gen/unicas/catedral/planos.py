"""Planos de planta en texto (celdas alcanzables) y renders isométricos de la catedral.

python3 -m unicas.catedral.planos <carpeta>   (desde tools/gen)"""
import os, sys
from lint import bname
from .auditoria import passable, top_height

LEVELS = [(-7, "Cripta, osarios y cámara del tesoro (pies en -7)"), (1, "Planta baja (pies en 1)"),
          (9, "Biblioteca y gabinete (pies en 9)"), (12, "Triforio, tribuna y pasarelas altas (pies en 12)"),
          (17, "Terrazas sobre los colaterales (pies en 17)"), (28, "Canalón, terraza de la fachada y desván (pies en 28)"),
          (40, "Campanario (pies en 40)"), (56, "Azoteas de las torres (pies en 56)")]
MARK = {"chest": "C", "barrel": "C", "spawner": "G", "lever": "L", "ladder": "H", "sticky_piston": "P", "piston_head": "P",
        "tripwire": "T", "tripwire_hook": "T", "stone_pressure_plate": "T", "dispenser": "D", "iron_trapdoor": "Z", "bell": "B"}


def plan(c, y, cells, x0=-2, x1=118, z0=2, z1=89):
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
    out = ["Planos de la catedral por nivel. Leyenda: '.' celda alcanzable a pie (a esa altura), ',' alcanzable medio bloque",
           "o un bloque arriba/abajo (escaleras), '#' muro o bloque, 'o' suelo con techo no alcanzable, 'C' cofre, 'G' generador,",
           "'L' palanca, 'P' pistón, 'T' trampa (cable o placa), 'D' dispensador, 'H' escalera de mano, 'Z' trampilla, 'B' campana.",
           "x crece hacia la derecha (fachada oeste a la izquierda), z hacia abajo (norte arriba).", ""]
    for y, title in LEVELS:
        out += [f"== {title} ==", plan(c, y, c.audit_cells), ""]
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
    from .auditoria import audit
    c = model()
    for p in audit(c, verbose=True):
        print(p[:300])
    write(c, sys.argv[1])
    if len(sys.argv) > 2:
        renders(c, sys.argv[1])
