"""Obra de una entrada a mina (tools/gen/minas): primitivas de excavación, forro, casco, rampa con vías y galería.

Coordenadas de diseño: x hacia el este, y hacia arriba, z hacia el sur. La boca está en x = 0, z = 0; la capa y = 0 es
el suelo del patio (los pies, en y = 1). El patio queda delante (z < 0) y la galería bajo el monte (z > 0). Lo excavado
no es una caja: cada celda excavada lleva su forro (suelo, muro y techo de obra, sin bloques naturales: dentro no nacen
manantiales ni liquen) y dos capas de casco alrededor; fuera, nada (structure_void), así que el terreno y las cuevas
vanilla se quedan como estaban. Lo mismo que la Mina perdida (LESSONS, «Estructura subterránea sin caja»).
"""
import zlib
from unicas._comun import piezas

N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
DV = piezas.DIRV
ALTO = 3                       # celdas de aire de un túnel (los pies en el suelo + 1 .. + 3)
PASO = 8                       # distancia entre cruces de la galería
MUESTRAS_MAX = 12             # muestras de techo para el Java
CASCO_BOCA = 4                 # junto a la boca (z < 4) el casco no sube por encima de y = 6: no asoma sobre el patio


def h(*a):
    """Azar determinista en [0, 1) por posición (mismo resultado en cada generación)."""
    return (zlib.crc32(repr(a).encode()) & 0xFFFF) / 65536.0


class Obra:
    def __init__(self, t, pal, rng):
        self.t, self.p, self.r = t, pal, rng
        self.carved = set()        # celdas de aire bajo tierra: llevan forro y casco
        self.superficie = set()    # celdas del patio (aire explícito, suelo, edificios): sin forro ni casco
        self.cofres = []           # (pos, tabla)
        self.vias = []             # tramos de vía: (inicio, sentido) para la auditoría
        self.nodos = []            # cruces de la galería (x, y del suelo, z)
        self.salas = []            # (tipo, x0, x1, z0, z1, y del suelo)
        self.techo = []            # (x, z, y del casco más alto) de muestra para el Java (terreno encima)
        self.generadores = []
        self.bajada = None         # (x, y de los pies, z) al pie de la escalera de caracol (grande)

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def mat(self, lista, x, y, z, sal=0):
        return lista[int(h(x, y, z, sal) * len(lista)) % len(lista)]

    def hueco(self, x, y, z):
        self.s(x, y, z, "air")
        self.carved.add((x, y, z))

    def caja(self, x0, x1, y0, y1, z0, z1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.hueco(x, y, z)

    def farol(self, x, y, z, colgado=True):
        self.s(x, y, z, f"lantern[hanging={'true' if colgado else 'false'},waterlogged=false]")

    def rail(self, x, y, z, shape):
        self.s(x, y, z, f"rail[shape={shape},waterlogged=false]")

    def cofre(self, x, y, z, facing, tabla, kind="chest"):
        piezas.chest(self.s, x, y, z, facing, f"heraldia:minas/{tabla}", kind=kind)
        self.cofres.append(((x, y, z), tabla))

    def tronco(self, axis):
        return f"{self.p['tronco']}[axis={axis}]"

    # ------------------------------------------------------------ marcos (entibado)
    def marco(self, x, y, z, eje, farol=False):
        """Cuadro de entibado en el plano del muro de un túnel de 3 de ancho con los pies en y: postes de tronco en los
        dos muros y viga en el techo (enrasados con el forro; el paso queda libre) y, si se pide, un farol colgado de
        la viga en el centro."""
        if eje == "z":                         # el túnel va de norte a sur: postes al este y al oeste
            for yy in range(y, y + ALTO):
                self.s(x - 2, yy, z, self.tronco("y"))
                self.s(x + 2, yy, z, self.tronco("y"))
            for xx in range(x - 2, x + 3):
                self.s(xx, y + ALTO, z, self.tronco("x"))
        else:
            for yy in range(y, y + ALTO):
                self.s(x, yy, z - 2, self.tronco("y"))
                self.s(x, yy, z + 2, self.tronco("y"))
            for zz in range(z - 2, z + 3):
                self.s(x, y + ALTO, zz, self.tronco("z"))
        if farol:
            self.farol(x, y + ALTO - 1, z)

    # ------------------------------------------------------------ túneles
    def corredor(self, a, b, y, vias=False, marcos=True, desde=0):
        """Túnel recto de 3 de ancho entre a = (x, z) y b (mismo x o mismo z), con los pies en y; marcos cada 4 (sin
        tocar los cruces) y, si se pide, vía por el centro."""
        (ax, az), (bx, bz) = a, b
        eje = "z" if ax == bx else "x"
        n = abs(bz - az) if eje == "z" else abs(bx - ax)
        sx, sz = (0, 1 if bz > az else -1) if eje == "z" else (1 if bx > ax else -1, 0)
        for k in range(n + 1):
            x, z = ax + sx * k, az + sz * k
            for w in (-1, 0, 1):
                for yy in range(y, y + ALTO):
                    self.hueco(x + (w if eje == "z" else 0), yy, z + (w if eje == "x" else 0))
        for k in range(n + 1):
            x, z = ax + sx * k, az + sz * k
            if marcos and 2 <= k <= n - 2 and (k - 2) % 4 == 0:
                self.marco(x, y, z, eje, farol=(k // 4) % 2 == 1)
        if vias:
            shape = "north_south" if eje == "z" else "east_west"
            for k in range(desde, n + 1 - desde):
                self.rail(ax + sx * k, y, az + sz * k, shape)
        return eje

    def rampa(self, x, z0, y0, largo, marcos=True):
        """Bajada hacia el sur desde (x, z0) con los pies en y0: `largo` celdas que bajan un bloque cada una, vía por el
        centro (raíles en cuesta) y escalones a los dos lados (se sube andando sin saltar). Devuelve (z final, pies)."""
        for k in range(1, largo + 1):
            z, pies = z0 + k, y0 - k
            for w in (-1, 0, 1):
                for yy in range(pies, pies + ALTO + 1):     # una fila más: la cabeza al pasar de un peldaño al otro
                    self.hueco(x + w, yy, z)
                self.s(x + w, pies - 1, z, f"{self.p['escalon_piedra']}[facing=north,half=bottom,shape=straight,waterlogged=false]"
                       if w else self.mat(self.p["suelo"], x, pies - 1, z))
            self.rail(x, pies, z, "ascending_north")
            if marcos and k % 4 == 2:
                for yy in range(pies, pies + ALTO + 1):
                    self.s(x - 2, yy, z, self.tronco("y"))
                    self.s(x + 2, yy, z, self.tronco("y"))
                for xx in range(x - 2, x + 3):
                    self.s(xx, pies + ALTO + 1, z, self.tronco("x"))
                if k % 8 == 6:
                    self.farol(x, pies + ALTO, z)
        return z0 + largo, y0 - largo

    # ------------------------------------------------------------ galería (red de túneles con cruces y salas)
    def red(self, x0, z0, pies, ni, nj, salas, extra=0.2, vias_tronco=True):
        """Red de túneles en una malla de (2 ni + 1) x nj cruces cada PASO bloques, con el primero (0, 0) en (x0, z0):
        un árbol al azar (determinista) más algunos lazos, y salas en los extremos. `salas`: tipos de sala, en orden
        (las primeras van en los cruces más lejanos). Devuelve {cruce: (x, z)} y la sala de cada tipo."""
        r = self.r
        nodos = [(i, j) for j in range(nj) for i in range(-ni, ni + 1)]
        pos = {n: (x0 + n[0] * PASO, z0 + n[1] * PASO) for n in nodos}
        vecinos = lambda n: [m for m in ((n[0] + 1, n[1]), (n[0] - 1, n[1]), (n[0], n[1] + 1), (n[0], n[1] - 1)) if m in pos]
        # árbol: búsqueda en profundidad al azar desde el cruce de llegada
        arbol, vistos, pila = set(), {(0, 0)}, [(0, 0)]
        while pila:
            n = pila[-1]
            libres = [m for m in vecinos(n) if m not in vistos]
            if not libres:
                pila.pop()
                continue
            m = r.choice(libres)
            vistos.add(m)
            arbol.add(frozenset((n, m)))
            pila.append(m)
        aristas = set(arbol)
        for n in nodos:
            for m in vecinos(n):
                e = frozenset((n, m))
                if e not in aristas and r.random() < extra / 2:
                    aristas.add(e)
        # el tronco: la columna i = 0 lleva vía hasta el último cruce
        tronco = {frozenset(((0, j), (0, j + 1))) for j in range(nj - 1)}
        aristas |= tronco
        for e in sorted(aristas, key=lambda e: sorted(e)):
            a, b = sorted(e)
            self.corredor(pos[a], pos[b], pies)
        if vias_tronco:                  # después de excavar los cruces (si no, un túnel de través borra la vía)
            for z in range(pos[(0, 0)][1] - 1, pos[(0, nj - 1)][1] + 1):   # desde el túnel que llega (z0 - 1)
                self.rail(x0, pies, z, "north_south")
        for n in nodos:
            self.nodos.append((pos[n][0], pies - 1, pos[n][1]))
        # salas en los cruces con una sola arista (los más lejanos primero), luego en cualquiera
        grado = {n: sum(1 for e in aristas if n in e) for n in nodos}
        lejos = lambda n: -(abs(n[0]) + n[1]) - r.random() * 0.5
        hojas = sorted((n for n in nodos if n != (0, 0) and n[0] != 0 and grado[n] == 1), key=lejos)
        resto = sorted((n for n in nodos if n != (0, 0) and n[0] != 0 and n not in hojas), key=lejos)
        elegidos = {}
        for tipo, n in zip(salas, hojas + resto):
            elegidos[tipo] = pos[n]
        return pos, elegidos

    def sala(self, tipo, cx, cz, pies, rx=3, rz=2, alto=4):
        """Sala de (2 rx + 1) x (2 rz + 1) con los pies en `pies` y `alto` de aire; postes de tronco en las esquinas."""
        self.caja(cx - rx, cx + rx, pies, pies + alto - 1, cz - rz, cz + rz)
        for dx in (-rx, rx):
            for dz in (-rz, rz):
                for yy in range(pies, pies + alto):
                    self.s(cx + dx, yy, cz + dz, self.tronco("y"))
        for xx in range(cx - rx, cx + rx + 1):
            for dz in (-rz, rz):
                self.s(xx, pies + alto, cz + dz, self.tronco("x"))
        self.salas.append((tipo, cx - rx, cx + rx, cz - rz, cz + rz, pies))
        self.farol(cx, pies + alto - 1, cz)

    # ------------------------------------------------------------ forro y casco
    def forro(self):
        """Forro de obra en cada celda sin escribir que toca una excavada: suelo, muro o techo según la cara."""
        p = self.p
        for (x, y, z) in sorted(self.carved):
            for dx, dy, dz in N6:
                q = (x + dx, y + dy, z + dz)
                if q in self.t.blocks:
                    continue
                lista = p["suelo"] if dy == -1 else p["techo"] if dy == 1 else p["muro"]
                self.s(*q, self.mat(lista, *q))

    def casco(self, grosor=2):
        """Dos capas de roca (6-vecinos) alrededor de todo lo escrito junto a lo excavado (menos el patio)."""
        frontera = {q for (x, y, z) in self.carved for dx, dy, dz in N6
                    for q in [(x + dx, y + dy, z + dz)] if q in self.t.blocks and q not in self.carved
                    and q not in self.superficie}
        for _ in range(grosor):
            nueva = set()
            for (x, y, z) in frontera:
                for dx, dy, dz in N6:
                    q = (x + dx, y + dy, z + dz)
                    if q not in self.t.blocks and not (q[2] < CASCO_BOCA and q[1] > 6):
                        nueva.add(q)
            for q in sorted(nueva):
                self.s(*q, self.p["casco_hondo"] if q[1] < -24 else self.p["casco"])
            frontera = nueva

    def vetas(self, prob=0.06):
        """Vetas de mineral en los muros de las galerías (solo en el forro de muro, no en el suelo ni en el techo)."""
        for (x, y, z) in sorted(self.carved):
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y, z + dz)
                st = self.t.get(*q)
                if q in self.carved or q in self.superficie or st is None or st.split("[")[0].replace("minecraft:", "") \
                        not in self.p["muro"] or q[1] > -3:
                    continue
                if h(*q, 91) < prob:
                    self.s(*q, self.mat(self.p["vetas"], *q, 5))

    def telarañas(self, x0, x1, z0, z1, pies, n, alto=ALTO):
        """Telarañas en rincones altos (pegadas al techo o a un muro) de una zona: no tapan el paso a la altura de la
        cabeza en el centro de los túneles."""
        hechas = 0
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                y = pies + alto - 1
                if hechas >= n or (x, y, z) not in self.carved or self.t.get(x, y, z) != "minecraft:air":
                    continue
                junto = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y, z + dz) not in self.carved)
                if junto >= 2 and h(x, y, z, 17) < 0.5:
                    self.s(x, y, z, "cobweb")
                    hechas += 1

    def muestras_techo(self):
        """Puntos (x, z, y más alta del casco) sobre la galería para que el Java mire que el monte la cubre."""
        alto = {}
        for (x, y, z) in self.carved:
            if z >= 4:
                alto[(x, z)] = max(alto.get((x, z), -999), y)
        pts = {}
        for (x, y, z) in self.nodos:
            if (x, z) in alto:
                pts[(x, z)] = alto[(x, z)] + 3       # techo (1) y casco (2)
        for tipo, x0, x1, z0, z1, pies in self.salas:
            for x, z in ((x0, z0), (x1, z1)):
                if (x, z) in alto:
                    pts[(x, z)] = alto[(x, z)] + 3
        pts = sorted(pts.items())
        if len(pts) > MUESTRAS_MAX:      # cada muestra cuesta una columna del terreno al buscar sitio: repartidas
            paso = len(pts) / MUESTRAS_MAX
            pts = [pts[int(k * paso)] for k in range(MUESTRAS_MAX)]
        return pts

