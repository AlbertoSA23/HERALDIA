"""Writes the per-level floor plans and the renders of the citadel: python3 -m uniques.ciudadela.documentar <folder>."""
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
print(f"audit: {len(errs)} errors; ruin {ratio:.1%} of {n} surface blocks; "
      f"{len(cells)} reachable cells; size {pl.t.size()}")
for e in errs:
    print("  ", e)
