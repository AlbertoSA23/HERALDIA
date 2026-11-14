"""Planos de planta en texto y renders isométricos de la mansión (docs/unicas/mansion/).

Uso (desde tools/gen): python3 -m unicas.mansion.planos
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core import Template
import render
from .obra import Obra
from . import auditoria
from .._comun.redstone import name

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "docs", "unicas", "mansion")
NIVELES = [("Sótano (pies y=-5)", -5), ("Planta baja (y=2; cripta del panteón)", 2), ("Primera (y=8; capilla del panteón y=6)", 8),
           ("Segunda (y=13)", 13), ("Buhardilla (y=18)", 18), ("Mirador del torreón (y=24)", 24)]
LEYENDA = """Leyenda: . alcanzable a pie desde la verja   : alcanzable solo con los mecanismos abiertos
# muro u obstáculo   C cofre/barril   P puerta   E escalera   L escala   S generador   R palanca/botón
T trampa (cable, dispensador, placa, dinamita)   G guardián   ~ vacío (patio, hueco del vestíbulo)
Norte arriba; x crece hacia la derecha (0..61), z hacia abajo (0..71)."""


def celda(t, cells, pub, x, y, z):
    sts = [t.get(x, yy, z) for yy in (y - 1, y, y + 1)]
    ns = [name(s) or "" for s in sts]
    if any(n == "spawner" for n in ns[1:]):
        return "S"
    if any(n in ("tripwire", "tripwire_hook", "dispenser", "stone_pressure_plate") for n in ns[1:]) or ns[0] == "tnt" \
            or name(t.get(x, y - 2, z)) == "tnt":
        return "T"
    if any(n in ("chest", "barrel") for n in ns[1:]):
        return "C"
    if any(n in ("lever", "stone_button") for n in ns[1:]):
        return "R"
    if ns[1].endswith("_door"):
        return "P"
    if ns[1] == "ladder":
        return "L"
    k = (x, y, z)
    if k in cells or (x, y + 1, z) in cells:
        if any(n.endswith("_stairs") for n in ns[:2]):
            return "E"
        return "." if (k in pub or (x, y + 1, z) in pub) else ":"
    if any(n not in ("", "air", "cobweb") for n in ns[1:]):
        return "#"
    return " " if ns[0] in ("", "air") else "~"


def main():
    obra = Obra().build()
    casa, sotano, errs = auditoria.preparar(obra)
    if errs:
        print("\n".join(errs))
        return 1
    os.makedirs(OUT, exist_ok=True)
    t = obra.t
    g = {(x, y, z) for x, y, z, n in t.entities if "wither" in str(n.get("id"))}
    lines = ["# Mansión encantada: planos por nivel", "", "Generado por `tools/gen/unicas/mansion/planos.py` a partir de la",
             "misma obra que se audita. " + LEYENDA.replace("\n", "\n"), ""]
    for title, y in NIVELES:
        lines += ["## " + title, "", "```"]
        for z in range(72):
            row = "".join("G" if (x, y, z) in g else celda(t, obra.cells, obra.cells_pub, x, y, z) for x in range(62))
            if row.strip():
                lines.append(f"{z:2d} {row.rstrip()}")
        lines += ["```", ""]
    with open(os.path.join(OUT, "planos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    n = sum(1 for p in obra.cells)
    print(f"planos: {n} celdas alcanzables ({len(obra.cells_pub)} sin mecanismos)")
    render.render(casa, os.path.join(OUT, "exterior.png"), scale=3)
    render.render(casa, os.path.join(OUT, "exterior_sur.png"), scale=3, flip=True)
    cut = Template("corte")
    cut.blocks = {p: v for p, v in t.blocks.items() if p[1] <= 6 and X(p)}
    render.render(cut, os.path.join(OUT, "corte_planta_baja.png"), scale=4)
    cut.blocks = {(x, y + 7, z): v for (x, y, z), v in t.blocks.items() if -7 <= y < -1}
    render.render(cut, os.path.join(OUT, "corte_sotano.png"), scale=4)
    return 0


def X(p):
    x, y, z = p
    return 0 <= x <= 61 and 8 <= z <= 44


if __name__ == "__main__":
    sys.exit(main())
