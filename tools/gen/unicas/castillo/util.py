"""Utilidades propias del castillo: lienzo con atajos, puerta de rincón (sobre _comun.piezas.piston_door) y recorrido a pie
de ida y vuelta (pendiente de pasar a _comun/recorrido.py cuando exista)."""
from collections import deque
from core import Template, parse_state
import lint
from .._comun.piezas import piston_door

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}

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


def hidden_door(put, a, c, L, side, door_block, input_floor=True):
    """Puerta secreta de 1 x 2 en el muro lateral (side=-1 oeste, +1 este) de la primera fila (z=c) de una sala, en el
    rincón: los pistones (piston_door) quedan dentro del muro norte y retiran la puerta al bloque del rincón, que no
    se ve desde ningún lado. Una antorcha sobre el bloque (a, L-1, c-2) alimenta el pistón de abajo y, por el bloque
    que potencia encima, el de arriba; potenciar ese bloque abre. Con input_floor, palanca en el suelo del rincón y
    polvo en cruz bajo el muro. Requiere muros macizos de 3 al norte y a ese lado."""
    dx = a + side
    piston_door(put, [(dx, L, c), (dx, L + 1, c)], (0, -1), "south", door_block)
    info = {"door": [(dx, L, c), (dx, L + 1, c)], "corner": [(dx, L, c - 1), (dx, L + 1, c - 1)],
            "input_block": (a, L - 1, c - 2), "torch": (a, L, c - 2), "s_block": (a, L + 1, c - 2)}
    put(a, L, c - 2, "redstone_torch[lit=true]")
    if input_floor:
        put(a, L - 1, c - 1, "redstone_wire[east=side,north=side,power=0,south=side,west=side]")
        put(a, L, c, "lever[face=floor,facing=north,powered=false]")
        info["lever"] = (a, L, c)
    return info


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


