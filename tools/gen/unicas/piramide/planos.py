"""Planos de planta por nivel (celdas alcanzables a pie) y renders isométricos del Templo-pirámide.

Uso: python3 tools/gen/unicas/piramide/planos.py [--solo-texto] [--nivel COTA]
Escribe docs/unicas/piramide/planos.txt y docs/unicas/piramide/*.png.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, GEN)
from core import Template                       # noqa: E402
from lint import bname, passable                # noqa: E402
from unicas.piramide import obra, auditoria     # noqa: E402

OUT = os.path.join(os.path.dirname(GEN), "..", "docs", "unicas", "piramide")
LEVELS = [(1, "Exterior y Sala del Cenote"), (4, "Plataformas laterales"), (7, "Juego de pelota (lo alto de los taludes)"),
          (12, "Rellano: Cámara de las Ofrendas y Cámara tapiada"), (24, "Cima: templo"),
          (-6, "Galerías del inframundo"), (-14, "Cenote y Cámara sumergida"), (-24, "Tumba y Cámara del Tesoro")]
LEGEND = (". alcanzable a pie   # muro o macizo   ~ agua   C cofre   S generador   G guardián   L palanca\n"
          "d dispensador   _ placa   - cable trampa   t trampilla   e peldaño   T tapiado   P puerta secreta   o otro")


def char(o, cells, x, y, z):
    st = o.get(x, y, z)
    below = o.get(x, y - 1, z)
    b = bname(st) if st else None
    if (x, y, z) in o.sealed:
        return "T"
    if (x, y, z) in o.puzzle:
        return "P"
    if b in ("chest",):
        return "C"
    if b == "spawner":
        return "S"
    if b == "lever":
        return "L"
    if b == "dispenser" or bname(below) == "dispenser" and b and "plate" in b:
        return "d"
    if b and "pressure_plate" in b:
        return "_"
    if b in ("tripwire", "tripwire_hook"):
        return "-"
    if b == "iron_trapdoor" or bname(below) == "iron_trapdoor":
        return "t"
    if any((x, yy, z) in cells for yy in (y, y - 1)):
        if b and b.endswith("_stairs") or below and bname(below).endswith("_stairs"):
            return "e"
        return "."
    if b == "water" or bname(below) == "water":
        return "~"
    if st is None or b == "air":
        return " "
    if passable(st):
        return "o"
    return "#"


def plan(o, cells, y, title):
    pts = [p for p in o.t.blocks if p[1] in (y, y - 1)]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    z0, z1 = min(p[2] for p in pts), max(p[2] for p in pts)
    guard = {(p[0], p[2]) for p in o.marks.get("guardian", []) if p[1] == y}
    rows = [f"== Cota {y}: {title} (x {x0}..{x1} de oeste a este, z {z0}..{z1} de norte a sur)"]
    for z in range(z0, z1 + 1):
        rows.append("".join("G" if (x, z) in guard else char(o, cells, x, y, z) for x in range(x0, x1 + 1)).rstrip())
    return "\n".join(rows)


def shell(o, ymax=-1):
    """Vista del subsuelo: solo lo que rodea a las salas (el macizo de roca se omite)."""
    t = Template("subsuelo_vista")
    for (x, y, z), v in o.t.blocks.items():
        if y > ymax or bname(v[0]) == "air":
            continue
        if bname(v[0]) == "stone" and not any((x + a, y + b, z + c) in o.carved
                                               for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
            continue
        t.blocks[(x, y, z)] = v
    t.normalize()
    return t


def main():
    only_text = "--solo-texto" in sys.argv
    lv = [int(sys.argv[sys.argv.index("--nivel") + 1])] if "--nivel" in sys.argv else None
    o = obra.build_all()
    wear = auditoria.tune_wear(o)
    issues, stats, cells = auditoria.audit(o, wear)
    os.makedirs(OUT, exist_ok=True)
    text = [f"Templo-pirámide: planos de planta generados por planos.py. {LEGEND}",
            "Auditoría: " + ", ".join(f"{k}={v}" for k, v in stats.items()) + (f"; {len(issues)} PROBLEMAS" if issues else "; sin problemas"), ""]
    for y, title in LEVELS:
        if lv and y not in lv:
            continue
        text += [plan(o, cells, y, title), ""]
    if lv:
        print("\n".join(text))
        for m, p in issues[:20]:
            print(m, p)
        return
    with open(os.path.join(OUT, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(text))
    if not only_text:
        import render
        sup = Template("sup")
        sup.blocks = {p: v for p, v in o.t.blocks.items() if p[1] >= 0}
        render.render(sup, os.path.join(OUT, "exterior.png"), scale=4)
        render.render(sup, os.path.join(OUT, "exterior_sur.png"), scale=4, flip=True)
        render.render(shell(o), os.path.join(OUT, "subsuelo.png"), scale=5)
    print(stats, len(issues), "problemas")


if __name__ == "__main__":
    main()
