"""Obra de una entrada a mina (tools/gen/mines): primitivas de excavación, forro, casco, rampa con vías y galería.

Coordenadas de diseño: x hacia el este, y hacia arriba, z hacia el sur. La boca está en x = 0, z = 0; la capa y = 0 es
el suelo del patio (los pies, en y = 1). El patio queda delante (z < 0) y la galería bajo el monte (z > 0). Lo excavado
no es una caja: cada celda excavada lleva su forro (suelo, muro y techo de obra, sin bloques naturales: dentro no nacen
manantiales ni liquen) y dos capas de casco alrededor; fuera, nada (structure_void), así que el terreno y las cuevas
vanilla se quedan como estaban. Lo mismo que la Mina perdida (LESSONS, «Estructura subterránea sin caja»).
"""
import zlib
from uniques._common import pieces

N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
DV = pieces.DIRV
HEIGHT = 3                       # celdas de aire de un túnel (los pies en el suelo + 1 .. + 3)
STEP = 8                       # distancia entre cruces de la galería
SAMPLES_MAX = 12             # muestras de techo para el Java
HULL_MOUTH = 4                 # junto a la boca (z < 4) el casco no sube por encima de y = 6: no asoma sobre el patio


def h(*a):
    """Azar determinista en [0, 1) por posición (mismo resultado en cada generación)."""
    return (zlib.crc32(repr(a).encode()) & 0xFFFF) / 65536.0


class Construction:
    def __init__(self, t, pal, rng):
        self.t, self.p, self.r = t, pal, rng
        self.carved = set()        # celdas de aire bajo tierra: llevan forro y casco
        self.surface = set()    # celdas del patio (aire explícito, suelo, edificios): sin forro ni casco
        self.cofres = []           # (pos, tabla)
        self.tracks = []             # tramos de vía: (inicio, sentido) para la auditoría
        self.nodes = []            # cruces de la galería (x, y del suelo, z)
        self.rooms = []            # (tipo, x0, x1, z0, z1, y del suelo)
        self.roof = []            # (x, z, y del casco más alto) de muestra para el Java (terreno encima)
        self.generators = []
        self.descent = None         # (x, y de los pies, z) al pie de la escalera de caracol (grande)

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

    def cofre(self, x, y, z, facing, tbl, kind="chest"):
        pieces.chest(self.s, x, y, z, facing, f"heraldia:minas/{tbl}", kind=kind)
        self.cofres.append(((x, y, z), tbl))

    def trunk(self, axis):
        return f"{self.p['tronco']}[axis={axis}]"

    # ------------------------------------------------------------ marcos (entibado)
    def frame(self, x, y, z, axis, lantern=False):
        """Cuadro de entibado en el plano del muro de un túnel de 3 de ancho con los pies en y: postes de tronco en los
        dos muros y viga en el techo (enrasados con el forro; el paso queda libre) y, si se pide, un farol colgado de
        la viga en el centro."""
        if axis == "z":                         # el túnel va de norte a sur: postes al este y al oeste
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

    # ------------------------------------------------------------ túneles
    def corridor(self, a, b, y, tracks=False, frames=True, start=0):
        """Túnel recto de 3 de ancho entre a = (x, z) y b (mismo x o mismo z), con los pies en y; marcos cada 4 (sin
        tocar los cruces) y, si se pide, vía por el centro."""
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
        """Bajada hacia el sur desde (x, z0) con los pies en y0: `largo` celdas que bajan un bloque cada una, vía por el
        centro (raíles en cuesta) y escalones a los dos lados (se sube andando sin saltar). Devuelve (z final, pies)."""
        for k in range(1, length + 1):
            z, feet = z0 + k, y0 - k
            for w in (-1, 0, 1):
                for yy in range(feet, feet + HEIGHT + 1):     # una fila más: la cabeza al pasar de un peldaño al otro
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

    # ------------------------------------------------------------ galería (red de túneles con cruces y salas)
    def red(self, x0, z0, feet, ni, nj, rooms, extra=0.2, trunk_tracks=True):
        """Red de túneles en una malla de (2 ni + 1) x nj cruces cada PASO bloques, con el primero (0, 0) en (x0, z0):
        un árbol al azar (determinista) más algunos lazos, y salas en los extremos. `salas`: tipos de sala, en orden
        (las primeras van en los cruces más lejanos). Devuelve {cruce: (x, z)} y la sala de cada tipo."""
        r = self.r
        nodes = [(i, j) for j in range(nj) for i in range(-ni, ni + 1)]
        pos = {n: (x0 + n[0] * STEP, z0 + n[1] * STEP) for n in nodes}
        neighbors = lambda n: [m for m in ((n[0] + 1, n[1]), (n[0] - 1, n[1]), (n[0], n[1] + 1), (n[0], n[1] - 1)) if m in pos]
        # árbol: búsqueda en profundidad al azar desde el cruce de llegada
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
        # el tronco: la columna i = 0 lleva vía hasta el último cruce
        trunk = {frozenset(((0, j), (0, j + 1))) for j in range(nj - 1)}
        edges |= trunk
        for e in sorted(edges, key=lambda e: sorted(e)):
            a, b = sorted(e)
            self.corridor(pos[a], pos[b], feet)
        if trunk_tracks:                  # después de excavar los cruces (si no, un túnel de través borra la vía)
            for z in range(pos[(0, 0)][1] - 1, pos[(0, nj - 1)][1] + 1):   # desde el túnel que llega (z0 - 1)
                self.rail(x0, feet, z, "north_south")
        for n in nodes:
            self.nodes.append((pos[n][0], feet - 1, pos[n][1]))
        # salas en los cruces con una sola arista (los más lejanos primero), luego en cualquiera
        degree = {n: sum(1 for e in edges if n in e) for n in nodes}
        far = lambda n: -(abs(n[0]) + n[1]) - r.random() * 0.5
        foliage = sorted((n for n in nodes if n != (0, 0) and n[0] != 0 and degree[n] == 1), key=far)
        remainder = sorted((n for n in nodes if n != (0, 0) and n[0] != 0 and n not in foliage), key=far)
        chosen_items = {}
        for kind, n in zip(rooms, foliage + remainder):
            chosen_items[kind] = pos[n]
        return pos, chosen_items

    def room(self, kind, cx, cz, feet, rx=3, rz=2, height=4):
        """Sala de (2 rx + 1) x (2 rz + 1) con los pies en `pies` y `alto` de aire; postes de tronco en las esquinas."""
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

    # ------------------------------------------------------------ forro y casco
    def lining(self):
        """Forro de obra en cada celda sin escribir que toca una excavada: suelo, muro o techo según la cara."""
        p = self.p
        for (x, y, z) in sorted(self.carved):
            for dx, dy, dz in N6:
                q = (x + dx, y + dy, z + dz)
                if q in self.t.blocks:
                    continue
                lst = p["suelo"] if dy == -1 else p["techo"] if dy == 1 else p["muro"]
                self.s(*q, self.mat(lst, *q))

    def shell(self, thickness=2):
        """Dos capas de roca (6-vecinos) alrededor de todo lo escrito junto a lo excavado (menos el patio)."""
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
        """Vetas de mineral en los muros de las galerías (solo en el forro de muro, no en el suelo ni en el techo)."""
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
        """Telarañas en rincones altos (pegadas al techo o a un muro) de una zona: no tapan el paso a la altura de la
        cabeza en el centro de los túneles."""
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
        """Puntos (x, z, y más alta del casco) sobre la galería para que el Java mire que el monte la cubre."""
        height = {}
        for (x, y, z) in self.carved:
            if z >= 4:
                height[(x, z)] = max(height.get((x, z), -999), y)
        pts = {}
        for (x, y, z) in self.nodes:
            if (x, z) in height:
                pts[(x, z)] = height[(x, z)] + 3       # techo (1) y casco (2)
        for kind, x0, x1, z0, z1, feet in self.rooms:
            for x, z in ((x0, z0), (x1, z1)):
                if (x, z) in height:
                    pts[(x, z)] = height[(x, z)] + 3
        pts = sorted(pts.items())
        if len(pts) > SAMPLES_MAX:      # cada muestra cuesta una columna del terreno al buscar sitio: repartidas
            step = len(pts) / SAMPLES_MAX
            pts = [pts[int(k * step)] for k in range(SAMPLES_MAX)]
        return pts

