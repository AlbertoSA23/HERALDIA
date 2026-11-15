"""Comprobaciones comunes de recorrido para las estructuras únicas (uso: from unicas._comun import recorrido).

- `Vista`: bloques de una o varias plantillas en coordenadas comunes, con suelo virtual y estados "resueltos".
- `andar`: recorrido a pie estricto (sin caídas de más de un bloque, peldaños de escalera, escaleras de mano que no
  atraviesan trampillas cerradas) y `sin_vuelta`: celdas alcanzadas desde las que no se vuelve a la entrada.
- `vista_lint`: plantilla con cambios (mecanismos abiertos o cerrados) y una entrada para usar `lint.walk` y
  `lint.access_issues` sobre varias piezas unidas.
- `cerca`, `flotantes` (bloques sin unión con el suelo) y `luz` (luz de bloque propagada) para cofres y generadores.
Más estricto que lint.walk, que permite caer hasta 4 bloques y bajar escaleras de mano a través de trampillas cerradas.
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
LUZ = {"lantern": 15, "torch": 14, "wall_torch": 14, "redstone_torch": 7, "redstone_wall_torch": 7, "glowstone": 15,
       "sea_lantern": 15, "jack_o_lantern": 15, "soul_lantern": 10, "soul_torch": 10, "soul_wall_torch": 10,
       "campfire": 15, "shroomlight": 15}


def is_full(st):
    """Bloque macizo y opaco a efectos de luz y de apoyo (aproximación por nombre)."""
    if st is None:
        return False
    b = st.split("[")[0].replace("minecraft:", "")
    return b not in ("air", "cave_air") and not any(k in b for k in NONFULL)


class Vista:
    """blocks: {pos: estado}; resuelto: {pos: estado} superpuesto; suelo_y: capa de hierba virtual donde no hay nada."""

    def __init__(self, blocks, resuelto=None, suelo_y=None):
        self.b = dict(blocks)
        for p, st in (resuelto or {}).items():
            self.b[p] = st if ":" in st else "minecraft:" + st
        self.suelo_y = suelo_y

    def get(self, x, y, z):
        st = self.b.get((x, y, z))
        if st is None and y == self.suelo_y:
            return "minecraft:grass_block"
        if st is not None and bname(st) == "air":
            return None
        return st


def andar(v, start, limites, agua=False):
    """Recorrido desde start. limites = (x0, x1, z0, z1). Devuelve ({celda: altura de los pies}, {celda: [vecinas]}).
    Con agua=True se nada: en el agua se sube y se baja en vertical, se sale subiendo hasta 1,1 y se puede caer al
    agua desde hasta 4 bloques (sin agua, el agua es paso libre sin flotación, como antes)."""
    g = v.get
    x0, x1, z0, z1 = limites

    def wet(x, y, z):
        return agua and bname(g(x, y, z)) == "water"

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
            for ny in (y + 1, y, y - 1, y - 2) + ((y - 3, y - 4, y - 5) if agua else ()):
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


def sin_vuelta(edges, start, exentas=()):
    """Celdas alcanzadas desde las que no se puede volver a start (grafo inverso). exentas: columnas (x, z) ignoradas."""
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
    return [c for c in edges if c not in ok and (c[0], c[2]) not in exentas]


def vista_lint(blocks, cambios=None, entrada=(0, 0, 0)):
    """Template para lint.walk/access_issues: blocks {pos: (estado, nbt)}, cambios {pos: estado o None (quitar)} y
    un jigsaw de entrada en `entrada`."""
    from core import Template
    v = Template("vista")
    v.blocks = dict(blocks)
    for p, st in (cambios or {}).items():
        if st is None:
            v.blocks.pop(p, None)
        else:
            v.blocks[p] = (st, None)
    v.jigsaw(*entrada, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="cobblestone")
    return v


def cerca(cells, p, r=1):
    x, y, z = p
    return any((x + a, y + b, z + c) in cells for a in range(-r, r + 1) for c in range(-r, r + 1)
               for b in (-1, 0, 1) if abs(a) + abs(c) <= r)


def flotantes(blocks, suelos):
    """Bloques no-aire sin unión (por caras) con algún bloque de las capas y de `suelos`."""
    solid = {p for p, st in blocks.items() if bname(st) != "air"}
    seen = {p for p in solid if p[1] in suelos}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for a, c, d in D6:
            n = (x + a, y + c, z + d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


def luz(blocks):
    """Luz de bloque aproximada: se propaga por celdas no macizas perdiendo 1 por paso."""
    lv, q = {}, deque()
    for p, st in blocks.items():
        n = LUZ.get(bname(st))
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


def luz_generador(lv, p, rango=4):
    """Luz máxima en el volumen donde aparecen los monstruos de un generador en p."""
    x, y, z = p
    return max([lv.get((x + a, y + b, z + c), 0) for a in range(-rango, rango + 1)
                for c in range(-rango, rango + 1) for b in (-1, 0, 1)])


# ------------------------------------------------------------------ lint.walk en plantillas con sótano
DY = 20     # lint.walk toma cualquier celda vacía con y < 0 como suelo natural: se audita una copia desplazada


def shifted(t):
    """Copia de la plantilla desplazada DY bloques hacia arriba (para lint.walk / lint.access_issues)."""
    from core import Template
    s = Template(t.name)
    s.blocks = {(x, y + DY, z): v for (x, y, z), v in t.blocks.items()}
    s.jigsaws = [dict(j, pos=(j["pos"][0], j["pos"][1] + DY, j["pos"][2])) for j in t.jigsaws]
    return s


def walk(t):
    """lint.walk sobre una plantilla con sótano en y < 0; devuelve las celdas en las coordenadas originales."""
    import lint
    return {(x, y - DY, z) for (x, y, z) in lint.walk(shifted(t))}


# ------------------------------------------------------------------ estado de conservación (Salón del Jarl, Santuario)
N6 = D6


def regla(block, prob, out):
    """Regla de un procesador `minecraft:rule`: `block` pasa a `out` con probabilidad `prob` (output_state en cadena)."""
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block,
                                "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


def procesador(decay):
    """Procesador de reglas a partir de [(bloque, probabilidad, salida)] (en orden: la primera que acierta)."""
    return {"processor_type": "minecraft:rule", "rules": [regla(b, p, o) for b, p, o in decay]}


def esperanza(st, decay):
    """Probabilidad de que el procesador `decay` cambie el bloque `st`."""
    b, left, out = bname(st), 1.0, 0.0
    for blk, p, _ in decay:
        if blk == b:
            out += left * p
            left *= 1 - p
    return out


def abrir(t, sim):
    """Bloques (pos -> estado) tras recoger los pistones sin señal (redstone.retract), con aire explícito donde estaba
    la puerta (si no, lint.walk toma la celda vacía del subsuelo por suelo natural)."""
    from . import redstone as rs
    b = rs.retract(t, sim)
    for p in t.blocks:
        b.setdefault(p, "minecraft:air")
    return b


def superficie_danada(blocks, ruined, decay, limites, suelo=()):
    """(superficie, fracción dañada) de los bloques `blocks` {pos: estado} (y >= 0) con una cara al aire exterior, que
    llega desde el cielo dentro de `limites` (x0, x1, z0, z1): la ruina hecha a mano (`ruined`, también lo que ya es
    aire) más lo que se espera del procesador `decay`. Los bloques de la capa y = 0 cuyo nombre está en `suelo` no
    cuentan (el suelo pisado)."""
    from .redstone import conductor
    x0, x1, z0, z1 = limites
    y1 = max(p[1] for p in blocks) + 1

    def libre(p):
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
            if libre(n):
                out.add(n)
                q.append(n)
    expuesto = lambda p: any((p[0] + d[0], p[1] + d[1], p[2] + d[2]) in out for d in N6)
    surf, bad = 0, 0.0
    for p, st in blocks.items():
        if bname(st) == "air" or not expuesto(p):
            continue
        if p[1] == 0 and bname(st) in suelo:
            continue
        surf += 1
        bad += 1.0 if p in ruined else esperanza(st, decay)
    near = sum(1 for p in ruined if p[1] >= 0 and blocks.get(p) and bname(blocks[p]) == "air" and expuesto(p))
    return surf, (bad + near) / max(surf, 1)
