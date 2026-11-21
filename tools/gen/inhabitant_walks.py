"""How far the inhabitants of the medium structures walk to their beds: a report, not a check.

Usage: python3 tools/gen/inhabitant_walks.py
For every medium-structure template with inhabitant villagers, the longest walk to a bed from a walkable cell of the
template within 16 blocks of it in a straight line (mediums/_inhabitants.worst_walk). The game claims a bed only if its
path search reaches it (LESSONS, "26.3 villagers only look for a path 16 blocks away"); a template where a bed is near
in a straight line and far on foot is where a villager can end up unable to get home. No limit is applied: see
worst_walk for why.
"""
import mediums
from mediums import _inhabitants as inh
from pack import Registry


def rows():
    reg = Registry()
    for mid, _ in mediums.modules():
        mediums.build(reg, mid)
    out = []
    for name, t in sorted(reg.templates.items()):
        living = [n for *_, n in t.entities if n["id"] == "minecraft:villager" and inh.is_inhabitant(n)]
        if name.startswith("medianas/") and living:
            steps, cell, bed = inh.worst_walk(t)
            out.append((steps, name, len(living), cell, bed))
    return sorted(out, reverse=True)


if __name__ == "__main__":
    rs = rows()
    for steps, name, n, cell, bed in rs:
        print(f"{steps:3d} steps  {name:40s} {n} villagers  from {cell} to the bed at {bed}")
    for lim in (16, 24, 32):
        print(f"more than {lim} steps: {sum(1 for r in rs if r[0] > lim)} of {len(rs)} templates")
