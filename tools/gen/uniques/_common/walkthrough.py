"""Common walkthrough checks for the unique structures (use: from uniques._common import recorrido).

- `View`: blocks of one or several templates in common coordinates, with a virtual floor and "solved" states.
- `strict_walk`: strict walkthrough (no falls of more than one block, stair steps, ladders that do not
  pass through closed trapdoors) and `no_return`: reached cells from which there is no way back to the entrance.
- `lint_view`: template with changes (mechanisms open or closed) and an entrance to use `lint.walk` and
  `lint.access_issues` on several joined pieces.
- `nearby_flag`, `floating_blocks` (blocks not connected to the ground) and `light` (propagated block light) for chests and spawners.
Stricter than lint.walk, which allows falling up to 4 blocks and going down ladders through closed trapdoors.
"""
from collections import deque
from lint import passable, top_height, bname, prop
from core import parse_state

FACE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
H4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
D6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
NONFULL = ("_stairs", "_slab", "_wall", "_fence", "iron_bars", "_pane", "trapdoor", "_door", "chest", "lantern",
           "iron_chain", "ladder", "torch", "carpet", "lever", "button", "pressure_plate", "tripwire", "comparator",
           "repeater", "bed", "banner", "pot", "cobweb", "dead_bush", "spawner", "candle", "piston_head", "grindstone",
           "lectern", "composter", "jigsaw", "frame")
LIGHT = {"lantern": 15, "torch": 14, "wall_torch": 14, "redstone_torch": 7, "redstone_wall_torch": 7, "glowstone": 15,
       "sea_lantern": 15, "jack_o_lantern": 15, "soul_lantern": 10, "soul_torch": 10, "soul_wall_torch": 10,
       "campfire": 15, "shroomlight": 15}


def is_full(st):
    """Solid block, opaque for light and support purposes (approximation by name)."""
    if st is None:
        return False
    b = st.split("[")[0].replace("minecraft:", "")
    return b not in ("air", "cave_air") and not any(k in b for k in NONFULL)


class View:
    """blocks: {pos: state}; resuelto: {pos: state} overlaid; suelo_y: virtual grass layer where there is nothing."""

    def __init__(self, blocks, resolved_map=None, floor_y=None):
        self.b = dict(blocks)
        for p, st in (resolved_map or {}).items():
            self.b[p] = st if ":" in st else "minecraft:" + st
        self.floor_y = floor_y

    def get(self, x, y, z):
        st = self.b.get((x, y, z))
        if st is None and y == self.floor_y:
            return "minecraft:grass_block"
        if st is not None and bname(st) == "air":
            return None
        return st


def strict_walk(v, start, limits, water=False):
    """Walkthrough from start. limites = (x0, x1, z0, z1). Returns ({cell: feet height}, {cell: [neighbors]}).
    With agua=True you swim: in water you go up and down vertically, you get out by rising up to 1.1 and you can fall into
    water from up to 4 blocks (without agua, water is free passage without buoyancy, as before)."""
    g = v.get
    x0, x1, z0, z1 = limits

    def wet(x, y, z):
        return water and bname(g(x, y, z)) == "water"

    def surf(x, y, z, mdx, mdz):
        st = g(x, y, z)
        if wet(x, y, z) or (wet(x, y - 1, z) and passable(st)):
            return (float(y), float(y))
        h = top_height(st)
        if st is not None and bname(st).endswith("_stairs") and "half=bottom" in st:
            fx, fz = FACE[prop(st, "facing")]
            return (y + 0.5 if (mdx, mdz) == (fx, fz) else y + 1.0, y + 1.0)
        if h is not None and h <= 0.6:
            return (y + h, y + h)
        if h is not None:
            return None
        below = g(x, y - 1, z)
        if below is None:
            return None
        hb = top_height(below)
        if hb is None:
            return (float(y), float(y)) if bname(below) == "ladder" else None
        if hb != 1.0 or (bname(below).endswith("_stairs") and "half=bottom" in below):
            return None
        return (float(y), float(y))

    def headroom(x, y, z, s):
        top = s + 1.8
        cy = y + 1
        while cy < top:
            st = g(x, cy, z)
            if not passable(st):
                low = cy + (0.5 if ("half=top" in st or "type=top" in st) else 0.0)
                if low < top:
                    return False
            cy += 1
        return True

    seen = {start: float(start[1])}
    edges = {}
    q = deque([start])
    while q:
        x, y, z = q.popleft()
        s = seen[(x, y, z)]
        out = []
        swim = wet(x, y, z) or wet(x, y - 1, z)
        for dx, dz in H4:
            nx, nz = x + dx, z + dz
            if not (x0 <= nx <= x1 and z0 <= nz <= z1):
                continue
            for ny in (y + 1, y, y - 1, y - 2) + ((y - 3, y - 4, y - 5) if water else ()):
                r = surf(nx, ny, nz, dx, dz)
                if r is None:
                    continue
                enter, stand = r
                into_water = wet(nx, ny, nz) or wet(nx, ny - 1, nz)
                if enter - s > (1.1 if swim else 0.6) or stand > s + (1.11 if swim else 1.01) or \
                        stand < s - (4.01 if into_water else 1.01):
                    continue
                if not headroom(nx, ny, nz, stand):
                    continue
                out.append(((nx, ny if stand < ny + 1 else ny + 1, nz), stand))
                break
        here = g(x, y, z)
        if wet(x, y, z) or wet(x, y - 1, z):
            for ny in (y + 1, y - 1):
                if wet(x, ny, z) or (ny > y and passable(g(x, ny, z))):
                    out.append(((x, ny, z), float(ny)))
        if bname(here) == "ladder" or (bname(g(x, y - 1, z)) == "ladder" and passable(here)):
            for ny in (y + 1, y - 1):
                st = g(x, ny, z)
                if bname(st) == "ladder" or (bname(here) == "ladder" and passable(st)):
                    out.append(((x, ny, z), float(ny)))
        edges[(x, y, z)] = [c for c, _ in out]
        for c, st in out:
            if c not in seen:
                seen[c] = st
                q.append(c)
    return seen, edges


def no_return(edges, start, exempt=()):
    """Reached cells from which start cannot be reached again (inverse graph). exentas: columns (x, z) ignored."""
    rev = {}
    for a, bs in edges.items():
        for b in bs:
            rev.setdefault(b, []).append(a)
    ok = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        for a in rev.get(c, ()):
            if a not in ok:
                ok.add(a)
                q.append(a)
    return [c for c in edges if c not in ok and (c[0], c[2]) not in exempt]


def lint_view(blocks, changes=None, entrance=(0, 0, 0)):
    """Template for lint.walk/access_issues: blocks {pos: (state, nbt)}, cambios {pos: state or None (remove)} and
    an entrance jigsaw at `entrance`."""
    from core import Template
    v = Template("vista")
    v.blocks = dict(blocks)
    for p, st in (changes or {}).items():
        if st is None:
            v.blocks.pop(p, None)
        else:
            v.blocks[p] = (st, None)
    v.jigsaw(*entrance, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    return v


def nearby_flag(cells, p, r=1):
    x, y, z = p
    return any((x + a, y + b, z + c) in cells for a in range(-r, r + 1) for c in range(-r, r + 1)
               for b in (-1, 0, 1) if abs(a) + abs(c) <= r)


def floating_blocks(blocks, floors):
    """Non-air blocks without a connection (by faces) to any block of the layers and of `floors`."""
    solid = {p for p, st in blocks.items() if bname(st) != "air"}
    seen = {p for p in solid if p[1] in floors}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for a, c, d in D6:
            n = (x + a, y + c, z + d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


def light(blocks):
    """Approximate block light: propagates through non-solid cells losing 1 per step."""
    lv, q = {}, deque()
    for p, st in blocks.items():
        n = LIGHT.get(bname(st))
        if n and "lit=false" not in st:
            lv[p] = n
            q.append(p)
    while q:
        p = q.popleft()
        n = lv[p] - 1
        if n <= 0:
            continue
        for a, c, d in D6:
            np_ = (p[0] + a, p[1] + c, p[2] + d)
            st = blocks.get(np_)
            if st is None or is_full(st):
                continue
            if lv.get(np_, 0) < n:
                lv[np_] = n
                q.append(np_)
    return lv


def light_generator(lv, p, span=4):
    """Maximum light in the volume where a spawner's monsters appear at p."""
    x, y, z = p
    return max([lv.get((x + a, y + b, z + c), 0) for a in range(-span, span + 1)
                for c in range(-span, span + 1) for b in (-1, 0, 1)])


# ------------------------------------------------------------------ lint.walk on templates with a basement
DY = 20     # lint.walk takes any empty cell with y < 0 as natural ground: a shifted copy is audited


def shifted(t):
    """Copy of the template shifted DY blocks upward (for lint.walk / lint.access_issues)."""
    from core import Template
    s = Template(t.name)
    s.blocks = {(x, y + DY, z): v for (x, y, z), v in t.blocks.items()}
    s.jigsaws = [dict(j, pos=(j["pos"][0], j["pos"][1] + DY, j["pos"][2])) for j in t.jigsaws]
    return s


def walk(t):
    """lint.walk on a template with a basement at y < 0; returns the cells in the original coordinates."""
    import lint
    return {(x, y - DY, z) for (x, y, z) in lint.walk(shifted(t))}


# ------------------------------------------------------------------ state of preservation (Jarl's Hall, Sanctuary)
N6 = D6


def rule_def(block, prob, out):
    """Rule of a `minecraft:rule` processor: `block` becomes `out` with probability `prob` (output_state as a string)."""
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block,
                                "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


def processor(decay):
    """Rule processor from [(block, probability, output)] (in order: the first that succeeds)."""
    return {"processor_type": "minecraft:rule", "rules": [rule_def(b, p, o) for b, p, o in decay]}


def expectation(st, decay):
    """Probability that the `decay` processor changes the block `st`."""
    b, left, out = bname(st), 1.0, 0.0
    for blk, p, _ in decay:
        if blk == b:
            out += left * p
            left *= 1 - p
    return out


def open_up(t, sim):
    """Blocks (pos -> state) after retracting the pistons without a signal (redstone.retract), with explicit air where
    the door was (otherwise lint.walk takes the empty subsurface cell as natural ground)."""
    from . import redstone as rs
    b = rs.retract(t, sim)
    for p in t.blocks:
        b.setdefault(p, "minecraft:air")
    return b


def damaged_surface(blocks, ruined, decay, limits, floor=()):
    """(surface, damaged fraction) of the blocks `blocks` {pos: state} (y >= 0) with a face to the outside air, which
    is reached from the sky within `limits` (x0, x1, z0, z1): the hand-made ruin (`ruined`, also what is already
    air) plus what is expected from the `decay` processor. Blocks of the y = 0 layer whose name is in `floor` do not
    count (the trodden ground)."""
    from .redstone import conductor
    x0, x1, z0, z1 = limits
    y1 = max(p[1] for p in blocks) + 1

    def free(p):
        st = blocks.get(p)
        return st is None or passable(st) or not conductor(st)
    out, q = set(), deque()
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            out.add((x, y1, z))
            q.append((x, y1, z))
    while q:
        p = q.popleft()
        for d in N6:
            n = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if n in out or not (x0 <= n[0] <= x1 and 0 <= n[1] <= y1 and z0 <= n[2] <= z1):
                continue
            if free(n):
                out.add(n)
                q.append(n)
    exposed = lambda p: any((p[0] + d[0], p[1] + d[1], p[2] + d[2]) in out for d in N6)
    surf, bad = 0, 0.0
    for p, st in blocks.items():
        if bname(st) == "air" or not exposed(p):
            continue
        if p[1] == 0 and bname(st) in floor:
            continue
        surf += 1
        bad += 1.0 if p in ruined else expectation(st, decay)
    near = sum(1 for p in ruined if p[1] >= 0 and blocks.get(p) and bname(blocks[p]) == "air" and exposed(p))
    return surf, (bad + near) / max(surf, 1)
