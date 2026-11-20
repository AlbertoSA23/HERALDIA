"""The door rule (the owner's, mandatory): every door has CLEAR free, walkable blocks straight out in front of it, no
door faces another building's wall (nothing within FACE blocks in front, 3 wide), no two buildings closer than GAP
blocks, and every door has a path to a street.

Two levels, because what "another building" is depends on what is being checked:
  - footprint_errors(buildings): a layout of known buildings (footprints and doors), such as the Herald's House:
    the whole rule, exactly. herald_house.placement_errors uses it (and adds the walk to a street, which needs the
    template) and generation fails on any error.
  - template_report(t): any single template with doors (village houses, medium structures, uniques). A template
    holds one building (or a few pieces of one), so "another building's wall" and "the distance between buildings"
    are decided when the jigsaw assembles the village, not in the template: those two parts cannot be checked here.
    What can: each door that opens to the outside (exactly one of its sides open to the sky inside the template) has
    CLEAR free, walkable blocks on that side, or reaches the template's edge (the street beyond it is not known);
    and no wall (two solid blocks high) stands within FACE blocks straight out of it, inside the template. Report
    mode only (registry_report): it does not fail generation.
"""
import sys

import lint

CLEAR, FACE, GAP = 3, 8, 4
OPEN_DIR = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


# ------------------------------------------------------------------ a layout of known buildings
def _inside(r, x, z):
    return r[0] <= x <= r[2] and r[1] <= z <= r[3]


def footprint_errors(buildings):
    """buildings: [(name, (x0, z0, x1, z1), [(side, x, z), ...] doors)]; the rectangles may include overhangs.
    Returns the messages of every broken part of the rule (spacing, room in front, facing a wall)."""
    e = []
    for i, (a, ra, _) in enumerate(buildings):
        for b, rb, _ in buildings[i + 1:]:
            gap = max(rb[0] - ra[2], ra[0] - rb[2], rb[1] - ra[3], ra[1] - rb[3]) - 1
            if gap < GAP:
                e.append(f"{a} and {b} are {max(gap, 0)} blocks apart (at least {GAP})")
    for name, _, doors in buildings:
        others = [(o, r) for o, r, _ in buildings if o != name]
        for side, x, z in doors:
            dx, dz = OPEN_DIR[side]
            for k in range(1, CLEAR + 1):
                hit = [o for o, r in others if _inside(r, x + dx * k, z + dz * k)]
                if hit:
                    e.append(f"the door of {name} at {x} {z} opens onto {hit[0]} {k} blocks out")
                    break
            faced = set()
            for k in range(1, FACE + 1):
                for w in (-1, 0, 1):
                    cx, cz = x + dx * k + w * (dz != 0), z + dz * k + w * (dx != 0)
                    for o, r in others:
                        if o not in faced and _inside(r, cx, cz):
                            faced.add(o)
                            e.append(f"the door of {name} at {x} {z} faces the wall of {o} {k} blocks away")
    return e


# ------------------------------------------------------------------ any template
def _name(st):
    return (st or "minecraft:air").split("[")[0].removeprefix("minecraft:")


def doors_of(t):
    """The doors of a template: [(x, y, z, axis_sides)] with the lower half's position and its two sides."""
    out = []
    for (x, y, z), (st, _) in t.blocks.items():
        n = _name(st)
        if n.endswith("_door") and "half=lower" in st:
            f = lint.prop(st, "facing")
            out.append((x, y, z, (f, OPP[f])))
    return out


def _sky(g, x, y, z, top):
    return all(lint.passable(g(x, yy, z)) for yy in range(y + 2, top + 1))


def template_report(t):
    """[message] of the doors of one template that break what can be checked of the rule inside it (see above)."""
    v = lint.resolved(t)
    g = v.get
    if not v.blocks:
        return []
    x0, y0, z0, x1, y1, z1 = v.bounds()
    inb = lambda x, z: x0 <= x <= x1 and z0 <= z <= z1
    out = []
    for x, y, z, sides in doors_of(t):
        open_sides = [s for s in sides if inb(x + OPEN_DIR[s][0], z + OPEN_DIR[s][1])
                      and _sky(g, x + OPEN_DIR[s][0], y, z + OPEN_DIR[s][1], y1)]
        if len(open_sides) != 1:
            continue                                   # an inner door, or one under a porch on both sides
        dx, dz = OPEN_DIR[open_sides[0]]
        for k in range(1, CLEAR + 1):
            cx, cz = x + dx * k, z + dz * k
            if not inb(cx, cz) or g(cx, y - 1, cz) is None and g(cx, y, cz) is None:
                break                                  # the template ends (or leaves the cell to whatever joins it:
                #                                        a street jigsaw, structure void): what is beyond is not known
            below = g(cx, y - 1, cz)
            free = lint.passable(g(cx, y, cz)) and lint.passable(g(cx, y + 1, cz))
            if free and below is not None and lint.top_height(below) == 0.5:
                break                                  # a step down (stair or slab) to the street: a way out
            if not (free and (lint.top_height(below) == 1.0 or y - 1 < y0)):
                out.append(f"door at {x} {y} {z}: {cx} {y} {cz} ({k} out) is not free and walkable")
                break
        else:
            for k in range(CLEAR + 1, FACE + 1):
                for w in (-1, 0, 1):
                    cx, cz = x + dx * k + w * (dz != 0), z + dz * k + w * (dx != 0)
                    if inb(cx, cz) and all(lint.solid_full(g(cx, yy, cz)) for yy in (y, y + 1)):
                        out.append(f"door at {x} {y} {z}: a wall {k} blocks in front of it ({cx} {cz})")
                        break
                else:
                    continue
                break
    return out


def registry_report(reg, only=None):
    """{template: [messages]} of every template with doors (report mode: nothing fails)."""
    out = {}
    for n, t in reg.templates.items():
        if only and not only(n):
            continue
        r = template_report(t)
        if r:
            out[n] = r
    return out


def main():
    """python3 tools/gen/doors.py: the report over every generated template with doors (and the Herald's House)."""
    import collections
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pack import build_all
    reg = build_all()
    rep = registry_report(reg)
    with_doors = [n for n, t in reg.templates.items() if doors_of(t)]
    kinds = collections.Counter(n.split("/")[0] if not n.startswith(("unicas/", "medianas/")) else "/".join(n.split("/")[:2])
                                for n in rep)
    print(f"{len(with_doors)} templates with doors; {len(rep)} break the rule ({sum(len(v) for v in rep.values())} doors)")
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")
    for n, v in sorted(rep.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(f"{n}: {len(v)}: {v[0]}")
    # mandatory: the Herald's House and the huts by its roads (their templates and their places beside the four roads)
    import herald_house
    import spawn_roads
    import herald_grounds
    t = herald_house.construct()
    must = herald_house.placement_errors(t.blds, t, herald_house.walk_cells(t)) + spawn_roads.errors()
    must += herald_grounds.errors()
    print(f"mandatory (the Herald's House, its roadside huts and the houses around it): {len(must)} errors")
    for m in must:
        print(f"  {m}")
    return 1 if must else 0


if __name__ == "__main__":
    sys.exit(main())
