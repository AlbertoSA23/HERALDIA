"""Escribe los planos por nivel y los renders de la ciudadela: python3 -m unicas.ciudadela.documentar <carpeta>."""
import os, sys
from lint import walk
from . import dataset
from .audit import blueprint_text, renders, ruin_ratio

pl, meta, errs = dataset()
dest = sys.argv[1]
os.makedirs(dest, exist_ok=True)
cells = walk(pl.t)
with open(os.path.join(dest, "planos.txt"), "w", encoding="utf-8") as f:
    f.write(blueprint_text(pl, cells) + "\n")
renders(pl, os.path.join(dest, "niveles.png"))
ratio, n = ruin_ratio(pl)
print(f"auditoría: {len(errs)} errores; ruina {ratio:.1%} de {n} bloques de superficie; "
      f"{len(cells)} celdas alcanzables; tamaño {pl.t.size()}")
for e in errs:
    print("  ", e)
