"""Utilidades del castillo: geometría, escalera de caracol, puertas secretas de pistones y recorrido a pie."""
from collections import deque
from core import Template, parse_state, state_str
import lint

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


class Lienzo(Template):
    """Plantilla con atajos de dibujo."""

    def box(self, x1, y1, z1, x2, y2, z2, wall, floor=None, ceil=None):
        """Sala hueca: muros, suelo y techo opcionales; el interior queda con aire explícito."""
        self.fill(x1, y1, z1, x2, y2, z2, wall)
        self.air(x1 + 1, y1 + (1 if floor else 0), z1 + 1, x2 - 1, y2 - (1 if ceil else 0), z2 - 1)
        if floor:
            self.fill(x1 + 1, y1, z1 + 1, x2 - 1, y1, z2 - 1, floor)
        if ceil:
            self.fill(x1 + 1, y2, z1 + 1, x2 - 1, y2, z2 - 1, ceil)

    def door(self, x, y, z, facing, kind="spruce", hinge="left", open_=False):
        o = str(open_).lower()
        self.set(x, y, z, f"{kind}_door[facing={facing},half=lower,hinge={hinge},open={o},powered=false]")
        self.set(x, y + 1, z, f"{kind}_door[facing={facing},half=upper,hinge={hinge},open={o},powered=false]")

    def opening(self, x, y, z, h=2):
        for k in range(h):
            self.set(x, y + k, z, "air")


def circle(cx, cz, r):
    r2 = r * r
    R = int(r) + 1
    return [(cx + dx, cz + dz) for dx in range(-R, R + 1) for dz in range(-R, R + 1) if dx * dx + dz * dz <= r2]


# ---------------------------------------------------------------- escalera de caracol de losas
RING = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def spiral(put, nx, nz, s0, s1, phase, slab, newel):
    """Caracol de 3 x 3 alrededor de un machón en (nx, nz): cada peldaño sube media altura.
    put(x, y, z, estado). Devuelve [(i, x, z, altura de los pies)]."""
    steps = []
    n = int(round((s1 - s0) * 2))
    for i in range(n + 1):
        s = s0 + 0.5 * i
        dx, dz = RING[(i + phase) % 8]
        x, z = nx + dx, nz + dz
        if s == int(s):
            put(x, int(s) - 1, z, f"{slab}[type=top,waterlogged=false]")
        else:
            put(x, int(s - 0.5), z, f"{slab}[type=bottom,waterlogged=false]")
        steps.append((i, x, z, s))
    return steps


# ---------------------------------------------------------------- puerta secreta de pistones
def hidden_door(put, a, c, L, side, door_block, input_floor=True):
    """Puerta de 1 x 2 en el muro lateral (side=-1 oeste, +1 este) de la primera fila (z=c) de una sala,
    que dos pistones pegajosos extendidos retiran hacia el norte (al rincón) cuando se apaga la antorcha.
    En reposo todo es estable: antorcha encendida, pistones extendidos, palanca y polvo apagados.
    Requiere muros macizos de 3 al norte (z=c-3..c-1) y a ese lado. Devuelve las posiciones clave."""
    dx = a + side
    info = {"door": [(dx, L, c), (dx, L + 1, c)], "corner": [(dx, L, c - 1), (dx, L + 1, c - 1)],
            "input_block": (a, L - 1, c - 2), "torch": (a, L, c - 2), "s_block": (a, L + 1, c - 2)}
    for y in (L, L + 1):
        put(dx, y, c - 2, "sticky_piston[extended=true,facing=south]")
        put(dx, y, c - 1, "piston_head[facing=south,short=false,type=sticky]")
        put(dx, y, c, door_block)
    put(a, L, c - 2, "redstone_torch[lit=true]")
    if input_floor:
        put(a, L - 1, c - 1, "redstone_wire[east=side,north=side,power=0,south=side,west=side]")
        put(a, L, c, "lever[face=floor,facing=north,powered=false]")
        info["lever"] = (a, L, c)
    return info


def wire_line(put, cells):
    """Polvo apagado por una lista de celdas consecutivas (con cambios de altura de 1); estados de conexión correctos."""
    pos = list(cells)
    for k, (x, y, z) in enumerate(pos):
        conn = {"north": "none", "south": "none", "east": "none", "west": "none"}
        for nb in (pos[k - 1] if k else None, pos[k + 1] if k + 1 < len(pos) else None):
            if nb is None:
                continue
            ddx, ddy, ddz = nb[0] - x, nb[1] - y, nb[2] - z
            d = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(ddx, ddz)]
            conn[d] = "up" if ddy > 0 else "side"
        used = [d for d, v in conn.items() if v != "none"]
        if len(used) == 1:
            conn[OPP[used[0]]] = "side"
        put(x, y, z, "redstone_wire[" + ",".join(f"{d}={conn[d]}" for d in ("east", "north")) + ",power=0," +
            ",".join(f"{d}={conn[d]}" for d in ("south", "west")) + "]")


# ---------------------------------------------------------------- recorrido a pie (grafo dirigido)
NOCOLLIDE = ("tripwire", "lever", "redstone_wire", "redstone_torch", "redstone_wall_torch", "tripwire_hook",
             "stone_pressure_plate", "light_weighted_pressure_plate")


def bn(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


def passable(st):
    return st is None or bn(st) in NOCOLLIDE or lint.passable(st)


def walk_graph(blocks, start, bounds):
    """Celdas de pie alcanzables desde start y celdas desde las que se vuelve a start, sin saltar ni romper.
    Subir: como mucho media altura (o escalera de mano o agua); bajar: hasta 1 bloque."""
    g = lambda x, y, z: blocks.get((x, y, z))
    x0, y0, z0, x1, y1, z1 = bounds

    def stand(x, y, z):
        """Altura de los pies si se puede estar en la celda (x,y,z), si no None."""
        st = g(x, y, z)
        b = bn(st)
        if b == "water":
            return float(y)
        if not passable(st):
            h = lint.top_height(st)
            if h is not None and h <= 0.6 and not (b.endswith("_stairs") and "half=top" in st):
                return y + h
            return None
        below = g(x, y - 1, z)
        bb = bn(below)
        if bb in ("ladder", "water"):
            return float(y)
        if below is None or passable(below):
            return None
        hb = lint.top_height(below)
        if hb is None or hb < 0.99 or hb > 1.01:
            return None
        return float(y)

    def head_ok(x, y, z, s):
        top = s + 1.8
        cy = y
        while cy < top:
            st = g(x, cy, z)
            if cy == y and not passable(st) and s > y:
                cy += 1
                continue
            if not passable(st) and bn(st) != "water":
                low = cy + (0.5 if ("half=top" in st or "type=top" in st) else 0.0)
                if low < top:
                    return False
            cy += 1
        return True

    def climb(x, y, z):
        return bn(g(x, y, z)) in ("ladder", "water")

    def nbrs(c):
        x, y, z = c
        s = S[c]
        out = []
        for ddx, ddz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + ddx, z + ddz
            if not (x0 <= nx <= x1 and z0 <= nz <= z1):
                continue
            for ny in range(y + 1, y - 3, -1):
                ns = stand(nx, ny, nz)
                if ns is None:
                    continue
                st = g(nx, ny, nz)
                if st and bn(st).endswith("_stairs") and "half=bottom" in st:
                    fx, fz = DIRV[parse_state(st)[1]["facing"]]
                    enter = ny + 0.5 if (ddx, ddz) == (fx, fz) else ny + 1.0
                    ns = ny + 1.0
                    if (ddx, ddz) == (-fx, -fz):
                        enter = ny + 1.0
                    if enter - s > 0.6 or s - ns > 1.01:
                        continue
                else:
                    swim = bn(g(x, y, z)) == "water" or bn(g(x, y - 1, z)) == "water"
                    if ns - s > (1.1 if swim else 0.6) or s - ns > 1.01:
                        continue
                if not head_ok(nx, ny, nz, ns):
                    continue
                out.append((nx, ny, nz, ns))
                break
        for ny in (y + 1, y - 1):
            if climb(x, y, z) or climb(x, ny, z) or (ny == y - 1 and climb(x, y - 1, z)):
                ns = stand(x, ny, z)
                if ns is not None or climb(x, ny, z):
                    out.append((x, ny, z, float(ny) if ns is None else ns))
        return out

    S = {}
    adj = {}
    sx, sy, sz = start
    S[start] = stand(sx, sy, sz) or float(sy)
    q = deque([start])
    while q:
        c = q.popleft()
        adj[c] = []
        for nx, ny, nz, ns in nbrs(c):
            n = (nx, ny, nz)
            adj[c].append(n)
            if n not in S:
                S[n] = ns
                q.append(n)
    rev = {}
    for c, ns in adj.items():
        for n in ns:
            rev.setdefault(n, []).append(c)
    back = {start}
    q = deque([start])
    while q:
        c = q.popleft()
        for p in rev.get(c, ()):
            if p not in back:
                back.add(p)
                q.append(p)
    return S, back


FULL_END = ("_planks", "_bricks", "bricks", "_log", "stone", "cobblestone", "_wood", "bookshelf", "_tiles", "andesite",
            "deepslate", "_block", "terracotta", "calcite", "tuff", "granite", "diorite")


def is_full(st):
    b = bn(st)
    return b is not None and not passable(st) and b.endswith(FULL_END) and not b.endswith(("_slab", "_stairs", "_wall"))


def connect(t):
    """Pone las conexiones de vallas, barrotes y paneles según sus vecinos."""
    from core import parse_state as ps, state_str as ss
    for (x, y, z), (st, nbt) in list(t.blocks.items()):
        b = bn(st)
        fence = b.endswith("_fence")
        bars = b == "iron_bars" or b.endswith("_pane")
        if not (fence or bars):
            continue
        bid, props = ps(st)
        for d, (dx, dz) in DIRV.items():
            n = t.get(x + dx, y, z + dz)
            nb = bn(n)
            ok = False
            if n:
                if fence:
                    ok = nb.endswith("_fence") or is_full(n) or (nb.endswith("_fence_gate") and
                                                                ps(n)[1].get("facing") in (("north", "south") if dx else ("east", "west")))
                else:
                    ok = nb == "iron_bars" or nb.endswith("_pane") or is_full(n) or nb.endswith("_wall")
            props[d] = "true" if ok else "false"
        t.blocks[(x, y, z)] = (ss(bid, props), nbt)


# ---------------------------------------------------------------- generadores y guardianes
def spawner(t, x, y, z, mob, required_range=16, spawn_range=4):
    """Generador de monstruos de un solo tipo."""
    t.set(x, y, z, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": "minecraft:" + mob}},
                               "SpawnRange": spawn_range, "RequiredPlayerRange": required_range})


def guardian(mob, key, fallback, equipment, health=60.0, attack=5.0, knockback=0.4, follow=24.0, drop=0.1, extra=None):
    """NBT de un guardián (formato 26.3): nombre traducible, equipo, atributos moderados y persistente.
    equipment = {"mainhand": "iron_sword", "head": "iron_helmet", ...}."""
    from core import F, B
    n = {"id": "minecraft:" + mob, "PersistenceRequired": B(1), "CanPickUpLoot": B(0),
         "CustomName": {"translate": key, "fallback": fallback}, "Health": F(health),
         "attributes": [{"id": "minecraft:max_health", "base": float(health)},
                        {"id": "minecraft:attack_damage", "base": float(attack)},
                        {"id": "minecraft:knockback_resistance", "base": float(knockback)},
                        {"id": "minecraft:follow_range", "base": float(follow)}],
         "equipment": {slot: {"id": "minecraft:" + item, "count": 1} for slot, item in equipment.items()},
         "drop_chances": {slot: F(drop * 2 if slot == "mainhand" else drop) for slot in equipment}}
    n.update(extra or {})
    return n
