"""Planos de planta en texto (celdas alcanzables) y renders isométricos del castillo en docs/unicas/castillo/.
Uso: python3 tools/gen/uniques/castle/blueprints.py --registries build/mcmeta-summary"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

LEVELS = [(6, "Patio y planta baja (pies a y=6)"), (15, "Planta alta de la torre del homenaje (y=15)"),
          (17, "Adarve y plantas altas de las torres (y=17)"), (22, "Azotea de la torre del homenaje (y=22)"),
          (25, "Terrazas de las torres (y=25)"), (-13, "Mazmorra (y=-13, 19 bajo el patio)")]
SYM = {"chest": "C", "barrel": "B", "spawner": "S", "lever": "!", "ladder": "H", "water": "~", "sticky_piston": "p",
       "tripwire": "t", "dispenser": "d", "stone_pressure_plate": "x", "tnt": "x"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registries", default="build/mcmeta-summary")
    a = ap.parse_args()
    from validate import load_registries
    load_registries(a.registries)
    from pack import build_all
    import uniques.castle as c
    from uniques.castle.util import bn, passable
    from render import render
    reg = build_all()
    assert not reg.warnings, reg.warnings
    L = c.LAST
    ok, blocks = L["res"]["ok"], L["res"]["opened"]
    out = os.path.join(ROOT, "docs", "unicas", "castillo")
    os.makedirs(out, exist_ok=True)
    txt = ["# Planos del castillo (generados por planos.py)", "",
           "Leyenda: `.` celda a la que se llega a pie (y se vuelve), `#` muro u obstáculo, `~` agua, `C` cofre, `B` barril,",
           "`S` generador, `!` palanca, `H` escalera de mano, `D` puerta, `p` pistón, `t` cable trampa, `d` dispensador,",
           "`x` placa y dinamita. Norte arriba; la puerta del castillo está al sur. Recorrido con las salas secretas abiertas.", ""]
    for y, title in LEVELS:
        zs = range(0, 100) if y >= 0 else range(14, 70)
        xs = range(0, 100) if y >= 0 else range(26, 74)
        txt += [f"## {title}", "", "```"]
        for z in zs:
            row = ""
            for x in xs:
                st = blocks.get((x, y, z)) or blocks.get((x, y - 1, z)) if False else blocks.get((x, y, z))
                b = bn(st)
                ch = " "
                for k, s in SYM.items():
                    if b == k or (k == "chest" and b == "chest"):
                        ch = s
                if ch == " ":
                    if b and b.endswith("_door"):
                        ch = "D"
                    elif (x, y, z) in ok:
                        ch = "."
                    elif st and not passable(st):
                        ch = "#"
                row += ch
            txt.append(row.rstrip())
        txt += ["```", ""]
    with open(os.path.join(out, "planos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt))
    render(L["t"], os.path.join(out, "castillo_iso.png"), scale=2)
    render(L["t"], os.path.join(out, "castillo_corte_y14.png"), scale=2, cut_y=14)
    render(L["d"], os.path.join(out, "mazmorra_corte.png"), scale=4, cut_y=8)
    print("escrito en", out)


if __name__ == "__main__":
    main()
