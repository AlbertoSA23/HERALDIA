"""Floor plans (cells reachable on foot) and isometric renders of the wizard tower.

Usage: python3 tools/gen/uniques/wizard_tower/blueprints.py  -> writes docs/unicas/torre_mago/{plantas.txt,exterior.png,cortes.png}
Plan legend: + reachable on foot · # solid or obstacle · , passable but not walkable · . unreachable air
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from PIL import Image
from pack import Registry
from lint import walk, passable, bname
from render import render
import uniques.wizard_tower as m

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
OUT = os.path.join(ROOT, "docs", "unicas", "torre_mago")
NAMES = {"B2": "Basement 2 · treasure chamber", "B1": "Basement 1 · failed experiments", "f0": "Foyer and terrace",
         "f1": "Biblioteca (planta baja)", "f2": "Library gallery and hidden study", "f3": "Laboratorio de pociones",
         "f4": "Sala de encantamientos", "f5": "Invernadero", "f6": "Wizard's bedroom", "f7": "Observatorio"}


def main():
    os.makedirs(OUT, exist_ok=True)
    reg = Registry()
    m.build(reg)
    t = reg.templates[f"{m.NSP}/torre"]
    seen = walk(t)
    x0, y0, z0, x1, y1, z1 = t.bounds()
    lines = [__doc__.splitlines()[3], "North is up; the entrance is on the north edge. Axes: x to the right, z downwards.", ""]
    for key, y in m.FEET.items():
        lines.append(f"== {NAMES[key]} (feet at y={y}) ==")
        for z in range(z0, z1 + 1):
            row = ""
            for x in range(x0, x1 + 1):
                st = t.get(x, y, z)
                row += "+" if (x, y, z) in seen else " " if st is None else "." if bname(st) == "air" else "," if passable(st) else "#"
            if row.strip():
                lines.append(f"{z - m.OZ:4d} {row.rstrip()}")
        lines.append("")
    with open(os.path.join(OUT, "plantas.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    tmp = os.path.join(OUT, "_t.png")
    render(t, os.path.join(OUT, "exterior.png"), scale=3)
    cuts = []
    for key in ("B2", "B1", "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7"):
        render(t, tmp, scale=2, cut_y=m.FEET[key] + 2)
        im = Image.open(tmp)
        cuts.append(im.crop(im.getbbox()))
    os.remove(tmp)
    w = max(i.width for i in cuts); h = max(i.height for i in cuts)
    sheet = Image.new("RGB", (w * 5, h * 2), (245, 245, 240))
    for k, im in enumerate(cuts):
        sheet.paste(im, ((k % 5) * w, (k // 5) * h))
    sheet.save(os.path.join(OUT, "cortes.png"))
    print("planos en", OUT)


if __name__ == "__main__":
    main()
