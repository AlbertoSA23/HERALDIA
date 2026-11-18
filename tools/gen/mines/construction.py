"""Build of a mine entrance (tools/gen/mines): excavation, lining, shell, ramp with tracks and gallery primitives.

Design coordinates: x to the east, y up, z to the south. The mouth is at x = 0, z = 0; layer y = 0 is
the courtyard floor (the feet at y = 1). The courtyard lies in front (z < 0) and the gallery under the mountain (z > 0). What is excavated
is not a box: each excavated cell carries its lining (floor, wall and ceiling of built material, no natural blocks: no
springs or lichen spawn inside) and two layers of shell around it; outside, nothing (structure_void), so the terrain and the vanilla
caves stay as they were. The same as the Lost Mine (LESSONS, "Estructura subterránea sin caja").
"""
import zlib
from uniques._common import pieces

N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
DV = pieces.DIRV
HEIGHT = 3                       # air cells of a tunnel (the feet on the floor + 1 .. + 3)
STEP = 8                       # distance between gallery junctions
SAMPLES_MAX = 12             # ceiling samples for the Java side
HULL_MOUTH = 4                 # next to the mouth (z < 4) the shell does not rise above y = 6: it does not poke out over the courtyard


def h(*a):
    """Deterministic randomness in [0, 1) per position (same result on every generation)."""
    return (zlib.crc32(repr(a).encode()) & 0xFFFF) / 65536.0


class Construction:
    def __init__(self, t, pal, rng):
        self.t, self.p, self.r = t, pal, rng
        self.carved = set()        # underground air cells: they carry lining and shell
        self.surface = set()    # courtyard cells (explicit air, floor, buildings): no lining or shell
        self.chest_list = []           # (pos, tabla)
        self.tracks = []             # track stretches: (start, direction) for the audit
        self.nodes = []            # gallery junctions (x, floor y, z)
        self.rooms = []            # (type, x0, x1, z0, z1, floor y)
        self.roof = []            # sample (x, z, highest shell y) for the Java side (terrain above)
        self.generators = []
        self.descent = None         # (x, feet y, z) at the foot of the spiral staircase (large)

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def mat(self, lst, x, y, z, salt=0):
        return lst[int(h(x, y, z, salt) * len(lst)) % len(lst)]

    def cavity(self, x, y, z):
        self.s(x, y, z, "air")
        self.carved.add((x, y, z))

    def box(self, x0, x1, y0, y1, z0, z1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.cavity(x, y, z)

    def lantern(self, x, y, z, hanging=True):
        self.s(x, y, z, f"lantern[hanging={'true' if hanging else 'false'},waterlogged=false]")

    def rail(self, x, y, z, shape):
        self.s(x, y, z, f"rail[shape={shape},waterlogged=false]")

    def place_chest(self, x, y, z, facing, tbl, kind="chest"):
        pieces.chest(self.s, x, y, z, facing, f"heraldia:minas/{tbl}", kind=kind)
        self.chest_list.append(((x, y, z), tbl))

    def trunk(self, axis):
        return f"{self.p['tronco']}[axis={axis}]"

    # ------------------------------------------------------------ marcos (entibado)
    def frame(self, x, y, z, axis, lantern=False):
        """Timber frame in the plane of the wall of a 3-wide tunnel with the feet at y: log posts on both
        walls and a beam on the ceiling (flush with the lining; the passage stays clear) and, if requested, a lantern hanging from
        the beam in the center."""
        if axis == "z":                         # the tunnel runs north to south: posts to the east and west
            for yy in range(y, y + HEIGHT):
                self.s(x - 2, yy, z, self.trunk("y"))
                self.s(x + 2, yy, z, self.trunk("y"))
            for xx in range(x - 2, x + 3):
                self.s(xx, y + HEIGHT, z, self.trunk("x"))
        else:
            for yy in range(y, y + HEIGHT):
                self.s(x, yy, z - 2, self.trunk("y"))
                self.s(x, yy, z + 2, self.trunk("y"))
            for zz in range(z - 2, z + 3):
                self.s(x, y + HEIGHT, zz, self.trunk("z"))
        if lantern:
            self.lantern(x, y + HEIGHT - 1, z)

    # ------------------------------------------------------------ tunnels
    def corridor(self, a, b, y, tracks=False, frames=True, start=0):
        """Straight 3-wide tunnel between a = (x, z) and b (same x or same z), with the feet at y; frames every 4 (without
        touching the junctions) and, if requested, track through the center."""
        (ax, az), (bx, bz) = a, b
        axis = "z" if ax == bx else "x"
        n = abs(bz - az) if axis == "z" else abs(bx - ax)
        sx, sz = (0, 1 if bz > az else -1) if axis == "z" else (1 if bx > ax else -1, 0)
        for k in range(n + 1):
            x, z = ax + sx * k, az + sz * k
            for w in (-1, 0, 1):
                for yy in range(y, y + HEIGHT):
                    self.cavity(x + (w if axis == "z" else 0), yy, z + (w if axis == "x" else 0))
        for k in range(n + 1):
            x, z = ax + sx * k, az + sz * k
            if frames and 2 <= k <= n - 2 and (k - 2) % 4 == 0:
                self.frame(x, y, z, axis, lantern=(k // 4) % 2 == 1)
        if tracks:
            shape = "north_south" if axis == "z" else "east_west"
            for k in range(start, n + 1 - start):
                self.rail(ax + sx * k, y, az + sz * k, shape)
        return axis

    def ramp(self, x, z0, y0, length, frames=True):
        """Descent to the south from (x, z0) with the feet at y0: `length` cells that each go down one block, track through the
        center (sloped rails) and steps on both sides (it can be climbed on foot without jumping). Returns (final z, feet)."""
        for k in range(1, length + 1):
            z, feet = z0 + k, y0 - k
            for w in (-1, 0, 1):
                for yy in range(feet, feet + HEIGHT + 1):     # one more row: the head when passing from one step to the next
                    self.cavity(x + w, yy, z)
                self.s(x + w, feet - 1, z, f"{self.p['escalon_piedra']}[facing=north,half=bottom,shape=straight,waterlogged=false]"
                       if w else self.mat(self.p["suelo"], x, feet - 1, z))
            self.rail(x, feet, z, "ascending_north")
            if frames and k % 4 == 2:
                for yy in range(feet, feet + HEIGHT + 1):
                    self.s(x - 2, yy, z, self.trunk("y"))
                    self.s(x + 2, yy, z, self.trunk("y"))
                for xx in range(x - 2, x + 3):
                    self.s(xx, feet + HEIGHT + 1, z, self.trunk("x"))
                if k % 8 == 6:
                    self.lantern(x, feet + HEIGHT, z)
        return z0 + length, y0 - length

    # ------------------------------------------------------------ gallery (network of tunnels with junctions and rooms)
    def red(self, x0, z0, feet, ni, nj, rooms, extra=0.2, trunk_tracks=True):
        """Network of tunnels on a mesh of (2 ni + 1) x nj junctions every STEP blocks, with the first (0, 0) at (x0, z0):
        a random (deterministic) tree plus some loops, and rooms at the ends. `rooms`: room types, in order
        (the first ones go at the farthest junctions). Returns {junction: (x, z)} and the room of each type."""
        r = self.r
        nodes = [(i, j) for j in range(nj) for i in range(-ni, ni + 1)]
        pos = {n: (x0 + n[0] * STEP, z0 + n[1] * STEP) for n in nodes}
        neighbors = lambda n: [m for m in ((n[0] + 1, n[1]), (n[0] - 1, n[1]), (n[0], n[1] + 1), (n[0], n[1] - 1)) if m in pos]
        # tree: random depth-first search from the arrival junction
        tree, seen_all, stack = set(), {(0, 0)}, [(0, 0)]
        while stack:
            n = stack[-1]
            free_cells = [m for m in neighbors(n) if m not in seen_all]
            if not free_cells:
                stack.pop()
                continue
            m = r.choice(free_cells)
            seen_all.add(m)
            tree.add(frozenset((n, m)))
            stack.append(m)
        edges = set(tree)
        for n in nodes:
            for m in neighbors(n):
                e = frozenset((n, m))
                if e not in edges and r.random() < extra / 2:
                    edges.add(e)
        # the trunk: column i = 0 carries track to the last junction
        trunk = {frozenset(((0, j), (0, j + 1))) for j in range(nj - 1)}
        edges |= trunk
        for e in sorted(edges, key=lambda e: sorted(e)):
            a, b = sorted(e)
            self.corridor(pos[a], pos[b], feet)
        if trunk_tracks:                  # after excavating the junctions (otherwise a crossing tunnel erases the track)
            for z in range(pos[(0, 0)][1] - 1, pos[(0, nj - 1)][1] + 1):   # from the tunnel that arrives (z0 - 1)
                self.rail(x0, feet, z, "north_south")
        for n in nodes:
            self.nodes.append((pos[n][0], feet - 1, pos[n][1]))
        # rooms at junctions with a single edge (the farthest first), then at any
        degree = {n: sum(1 for e in edges if n in e) for n in nodes}
        far = lambda n: -(abs(n[0]) + n[1]) - r.random() * 0.5
        foliage = sorted((n for n in nodes if n != (0, 0) and n[0] != 0 and degree[n] == 1), key=far)
        remainder = sorted((n for n in nodes if n != (0, 0) and n[0] != 0 and n not in foliage), key=far)
        chosen_items = {}
        for kind, n in zip(rooms, foliage + remainder):
            chosen_items[kind] = pos[n]
        return pos, chosen_items

    def room(self, kind, cx, cz, feet, rx=3, rz=2, height=4):
        """Room of (2 rx + 1) x (2 rz + 1) with the feet at `feet` and `height` of air; log posts at the corners."""
        self.box(cx - rx, cx + rx, feet, feet + height - 1, cz - rz, cz + rz)
        for dx in (-rx, rx):
            for dz in (-rz, rz):
                for yy in range(feet, feet + height):
                    self.s(cx + dx, yy, cz + dz, self.trunk("y"))
        for xx in range(cx - rx, cx + rx + 1):
            for dz in (-rz, rz):
                self.s(xx, feet + height, cz + dz, self.trunk("x"))
        self.rooms.append((kind, cx - rx, cx + rx, cz - rz, cz + rz, feet))
        self.lantern(cx, feet + height - 1, cz)

    # ------------------------------------------------------------ lining and shell
    def lining(self):
        """Built lining in every unwritten cell that touches an excavated one: floor, wall or ceiling depending on the face."""
        p = self.p
        for (x, y, z) in sorted(self.carved):
            for dx, dy, dz in N6:
                q = (x + dx, y + dy, z + dz)
                if q in self.t.blocks:
                    continue
                lst = p["suelo"] if dy == -1 else p["techo"] if dy == 1 else p["muro"]
                self.s(*q, self.mat(lst, *q))

    def shell(self, thickness=2):
        """Two layers of rock (6-neighbors) around everything written next to the excavated (except the courtyard)."""
        border = {q for (x, y, z) in self.carved for dx, dy, dz in N6
                    for q in [(x + dx, y + dy, z + dz)] if q in self.t.blocks and q not in self.carved
                    and q not in self.surface}
        for _ in range(thickness):
            new_one = set()
            for (x, y, z) in border:
                for dx, dy, dz in N6:
                    q = (x + dx, y + dy, z + dz)
                    if q not in self.t.blocks and not (q[2] < HULL_MOUTH and q[1] > 6):
                        new_one.add(q)
            for q in sorted(new_one):
                self.s(*q, self.p["casco_hondo"] if q[1] < -24 else self.p["casco"])
            border = new_one

    def veins(self, prob=0.06):
        """Ore veins in the gallery walls (only in the wall lining, not in the floor or the ceiling)."""
        for (x, y, z) in sorted(self.carved):
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y, z + dz)
                st = self.t.get(*q)
                if q in self.carved or q in self.surface or st is None or st.split("[")[0].replace("minecraft:", "") \
                        not in self.p["muro"] or q[1] > -3:
                    continue
                if h(*q, 91) < prob:
                    self.s(*q, self.mat(self.p["vetas"], *q, 5))

    def cobwebs(self, x0, x1, z0, z1, feet, n, height=HEIGHT):
        """Cobwebs in high corners (against the ceiling or a wall) of an area: they do not block the passage at head height in
        the center of the tunnels."""
        done_list = 0
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                y = feet + height - 1
                if done_list >= n or (x, y, z) not in self.carved or self.t.get(x, y, z) != "minecraft:air":
                    continue
                beside = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y, z + dz) not in self.carved)
                if beside >= 2 and h(x, y, z, 17) < 0.5:
                    self.s(x, y, z, "cobweb")
                    done_list += 1

    def roof_samples(self):
        """Points (x, z, highest shell y) over the gallery so the Java side can check the mountain covers it."""
        height = {}
        for (x, y, z) in self.carved:
            if z >= 4:
                height[(x, z)] = max(height.get((x, z), -999), y)
        pts = {}
        for (x, y, z) in self.nodes:
            if (x, z) in height:
                pts[(x, z)] = height[(x, z)] + 3       # ceiling (1) and shell (2)
        for kind, x0, x1, z0, z1, feet in self.rooms:
            for x, z in ((x0, z0), (x1, z1)):
                if (x, z) in height:
                    pts[(x, z)] = height[(x, z)] + 3
        pts = sorted(pts.items())
        if len(pts) > SAMPLES_MAX:      # each sample costs one terrain column when searching for a site: spread out
            step = len(pts) / SAMPLES_MAX
            pts = [pts[int(k * step)] for k in range(SAMPLES_MAX)]
        return pts

