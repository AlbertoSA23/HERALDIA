"""Lighthouse-specific checks: puzzle and trap redstone, watertight cave, ruin and walkthrough.

`run(t)` returns the list of errors (the generator fails if it is not empty).
`python3 -m uniques.lighthouse.checks <folder>` (from tools/gen) writes floor plans and renders into <folder>.
"""
import itertools
from core import parse_state, state_str
from lint import walk, bname
from uniques._common import redstone

D6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def settle(t):
    """Writes the circuit's stable state into the template: shape and power of the dust and torches."""
    redstone.wire_shapes(t)
    sim = redstone.Sim(t)
    for p, lit in sim.torch.items():
        b, pr = parse_state(t.get(*p))
        pr["lit"] = str(lit).lower()
        t.set(*p, state_str(b, pr))
    redstone.set_wire_power(t)


def redstone_issues(t):
    from uniques.lighthouse.blueprint import LEVERS, REST, VAULT_DOOR
    errs, _ = redstone.check_static(t)
    out = list(errs)
    for k, p in LEVERS.items():
        if parse_state(t.get(*p))[1]["powered"] != str(REST[k]).lower():
            out.append(f"lever {k} is not in its resting position")
    door = lambda sim: sim.powered(VAULT_DOOR)
    good = {"A": False, "B": True, "C": False}
    for combo in itertools.product((False, True), repeat=3):
        cfg = dict(zip("ABC", combo))
        opens = door(redstone.Sim(t, {LEVERS[k]: cfg[k] for k in cfg}))
        if opens != (cfg == good):
            out.append(f"office puzzle: with {cfg} the door {'opens' if opens else 'does not open'}")
    hatch, lever = (15, 16, 16), (16, 17, 16)
    for on in (False, True):
        if redstone.Sim(t, {lever: on}).powered(hatch) != on:
            out.append(f"cellar puzzle: with the lever {'up' if on else 'down'} the trapdoor does not respond")
    sim = redstone.Sim(t, {(14, 9, 19): True, (16, 9, 19): True})
    for d in ((14, 10, 19), (16, 10, 19)):
        if not sim.powered(d):
            out.append(f"the trap wire does not fire dispenser {d}")
    if not redstone.Sim(t, {(37, 9, 39): True}).powered((37, 7, 39)):
        out.append("the plate does not ignite the TNT")
    return out


def sealing_issues(t):
    """No air cell below the summit touches the void (natural terrain) except at the cave mouth."""
    from uniques.lighthouse.blueprint import TOP
    out = []
    for (x, y, z), (st, _) in t.blocks.items():
        if y >= TOP or bname(st) not in ("air", "water") or (19 <= x <= 25 and z >= 41):
            continue
        if bname(st) == "water" and z > 40:
            continue
        for v in D6:
            if add((x, y, z), v) not in t.blocks:
                out.append(f"the cave opens to the outside at {(x, y, z)}")
                break
    return out[:5]


NATURAL = ("stone", "andesite", "tuff", "diorite", "dirt", "grass_block", "gravel", "water", "air")
RUIN_PROB = {"stone_bricks": 0.22, "cobblestone": 0.25, "white_terracotta": 0.22, "red_terracotta": 0.20,
             "spruce_planks": 0.15, "glass_pane": 0.10}
RUIN_SPOTS = 2 + 4 + 3 + 2 + 2 + 8 + 2 + 6   # panes, roof, railing, gallery, corridor, cave-in, bars, cobwebs


def ruin_share(t):
    """Estimated share of the visible built surface with ruin details."""
    vis, alt = 0, 0.0
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in NATURAL or any(w in b for w in ("lantern", "torch", "chain", "wire", "lever", "sign", "candle")):
            continue
        if any(t.get(*add(p, v)) in (None, "minecraft:air") for v in D6):
            vis += 1
            alt += RUIN_PROB.get(b, 0.0)
    return (alt + RUIN_SPOTS) / (vis + RUIN_SPOTS)


def access_points(t):
    """Cells the player has to reach (with the puzzles solved)."""
    from uniques.lighthouse.blueprint import LEVERS
    pts = {"cellar lever": (16, 17, 16), "premium chest": (18, 10, 4), "cave mouth": (22, 9, 40)}
    pts.update({f"lever {k}": p for k, p in LEVERS.items()})
    return pts


def run(t):
    out = redstone_issues(t) + sealing_issues(t)
    share = ruin_share(t)
    if not 0.15 <= share <= 0.20:
        out.append(f"estimated ruined surface {share:.0%}, outside 15-20 %")
    cells = walk(t)
    for name, (x, y, z) in access_points(t).items():
        if not any((x + dx, y + dy, z + dz) in cells for dx, dy, dz in itertools.product((-1, 0, 1), (-1, 0, 1), (-1, 0, 1))):
            out.append(f"{name} {(x, y, z)} is not reachable on foot")
    return out


# ------------------------------------------------------------------ floor plans and renders
SYMBOL = {"chest": "C", "barrel": "b", "spawner": "S", "ladder": "H", "lever": "P", "tnt": "T", "tripwire": "t",
          "dispenser": "d", "lectern": "A", "iron_trapdoor": "=", "bookshelf": "L"}


def floor_plans(t, out_dir):
    import os
    from uniques.lighthouse.blueprint import X, Z
    from render import render
    os.makedirs(out_dir, exist_ok=True)
    cells = walk(t)
    levels = ((9, "cave (sea level)"), (17, "cellar"), (22, "summit: house and lighthouse base"),
              (39, "guard room"), (44, "lantern and gallery"))
    lines = ["Lighthouse floor plans. North up (z=0, entrance); the sea to the south.",
             "· reachable on foot (with the puzzles solved)  # wall/rock  ~ water  D door  C chest  b barrel",
             "S spawner  H ladder  P lever  = trapdoor  T TNT  t tripwire  d dispenser",
             "A lectern  L bookshelf  / step", ""]
    for y, title in levels:
        lines.append(f"== y={y}: {title}")
        for z in range(Z):
            row = ""
            for x in range(X):
                st = t.get(x, y, z)
                b = bname(st) if st else None
                ch = next((c for k, c in SYMBOL.items() if b == k), None)
                if ch is None and b and b.endswith("_door"):
                    ch = "D"
                if ch is None and b and b.endswith("_stairs"):
                    ch = "/"
                if ch is None:
                    if b == "water" or bname(t.get(x, y - 1, z) or "") == "water" and b in (None, "air"):
                        ch = "~"
                    elif (x, y, z) in cells:
                        ch = "·"
                    elif b and b != "air" and redstone.conductor(st) or b in ("glass_pane", "iron_bars", "spruce_fence"):
                        ch = "#"
                    else:
                        ch = " "
                row += ch
            lines.append(row.rstrip())
        lines.append("")
    with open(os.path.join(out_dir, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    render(t, os.path.join(out_dir, "exterior.png"), scale=3)

    class Cut:
        pass
    cut = Cut()
    cut.blocks = {p: v for p, v in t.blocks.items() if p[1] <= 13 and not (p[1] >= 9 and p[2] >= 40)}
    render(cut, os.path.join(out_dir, "cueva.png"), scale=3)


if __name__ == "__main__":
    import sys
    from uniques.lighthouse.blueprint import make
    t = make()
    print("\n".join(run(t)) or "no errors", f"ruina {ruin_share(t):.1%}")
    floor_plans(t, sys.argv[1])
