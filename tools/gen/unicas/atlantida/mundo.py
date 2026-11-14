"""Plano de la ciudad en vóxeles: se construye entero y luego se corta en teselas (plantillas)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core import Template, parse_state, state_str
import validate
from . import urbanismo as U

_norm = {}
GIRO = ["north", "east", "south", "west"]


def norm(state):
    s = _norm.get(state)
    if s is None:
        s = _norm[state] = state_str(*parse_state(state))
    return s


def nombre(state):
    return state.split("[")[0].replace("minecraft:", "") if state else None


def girar(state, k):
    """Gira un estado k cuartos de vuelta en sentido horario visto desde arriba (norte -> este)."""
    if k % 4 == 0 or "[" not in state:
        return state
    bid, props = parse_state(state)
    if props.get("facing") in GIRO:
        props["facing"] = GIRO[(GIRO.index(props["facing"]) + k) % 4]
    if "axis" in props and props["axis"] in ("x", "z") and k % 2:
        props["axis"] = "z" if props["axis"] == "x" else "x"
    if "rotation" in props:
        props["rotation"] = str((int(props["rotation"]) + 4 * k) % 16)
    lados = {d: props[d] for d in GIRO if d in props}          # paneles, vallas, redstone
    for d, v in lados.items():
        props[GIRO[(GIRO.index(d) + k) % 4]] = v
    return state_str(bid, props)


def anegable(state):
    """El bloque admite la propiedad waterlogged (según los registros de 26.3)."""
    if not validate.BLOCKS:
        raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        validate.load_registries(os.environ.get("MCMETA_SUMMARY") or os.path.join(raiz, "build", "mcmeta-summary"))
    b = validate.BLOCKS.get(nombre(state))
    return bool(b) and "waterlogged" in b[0]


class Mundo:
    def __init__(self):
        self.blocks = {}      # (x, y, z) -> (estado, nbt | None)
        self.entities = []    # (x, y, z, nbt)
        self.marcas = {}      # nombre -> lista de celdas (para auditoría, planos y prueba de humo)
        self.sitios = []      # (nombre, x1, y1, z1, x2, y2, z2, ruinoso): cajas de lo construido

    # --- básico ---
    def set(self, x, y, z, state, nbt=None):
        self.blocks[(x, y, z)] = (norm(state), nbt)

    def get(self, x, y, z):
        """Estado final de la celda: lo construido o, si no hay nada, lo que deja la pieza base."""
        b = self.blocks.get((x, y, z))
        return b[0] if b else U.base(x, y, z)

    def built(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None

    def fill(self, x1, y1, z1, x2, y2, z2, state):
        s = (norm(state), None)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.blocks[(x, y, z)] = s

    def entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))

    def marca(self, nombre_, x, y, z):
        self.marcas.setdefault(nombre_, []).append((x, y, z))

    def sitio(self, nombre_, x1, y1, z1, x2, y2, z2, ruinoso=False):
        self.sitios.append((nombre_, min(x1, x2), min(y1, y2), min(z1, z2), max(x1, x2), max(y1, y2), max(z1, z2), ruinoso))

    # --- agua ---
    def sanear_algas(self):
        """Quita las algas que han quedado sin base y remata las cortadas (otro elemento pisó parte del tallo)."""
        cambio = True
        while cambio:
            cambio = False
            for (x, y, z), (st, _) in list(self.blocks.items()):
                b = nombre(st)
                if b not in ("kelp", "kelp_plant"):
                    continue
                bajo = nombre(self.get(x, y - 1, z))
                if bajo != "kelp_plant" and (bajo in (None, "water", "air", "barrel", "chest", "spawner", "seagrass", "sea_pickle", "kelp")
                                             or any(k in bajo for k in ("_slab", "_stairs", "_fence", "_door", "coral"))):
                    del self.blocks[(x, y, z)]
                    cambio = True
                elif b == "kelp_plant" and nombre(self.get(x, y + 1, z)) not in ("kelp", "kelp_plant"):
                    self.blocks[(x, y, z)] = (norm("kelp[age=25]"), None)
                    cambio = True

    def anegar(self):
        """Pone waterlogged a cada bloque anegable según su entorno: anegado si toca agua y no toca aire."""
        cambios = {}
        for (x, y, z), (st, nbt) in self.blocks.items():
            if st.startswith("minecraft:water") or st == "minecraft:air" or not anegable(st):
                continue
            bid, props = parse_state(st)
            if "waterlogged" in props:
                continue
            vecinos = [self.get(x + a, y + b, z + c) for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
            agua = any(v and (v.startswith("minecraft:water") or "waterlogged=true" in v) for v in vecinos)
            aire = any(v == "minecraft:air" for v in vecinos)
            props["waterlogged"] = "true" if agua and not aire else "false"
            cambios[(x, y, z)] = (state_str(bid, props), nbt)
        self.blocks.update(cambios)

    # --- teselas ---
    def teselas(self, prefijo):
        """[(Template normalizada, (x, y, z) de su esquina mínima en el plano)], ordenadas."""
        grupos = {}
        for pos, v in self.blocks.items():
            grupos.setdefault((pos[0] // U.TESELA, pos[2] // U.TESELA), ([], []))[0].append((pos, v))
        for x, y, z, n in self.entities:
            grupos.setdefault((x // U.TESELA, z // U.TESELA), ([], []))[1].append((x, y, z, n))
        out = []
        for (tx, tz) in sorted(grupos):
            bl, en = grupos[(tx, tz)]
            name = f"{prefijo}/t_{'m' if tx < 0 else 'p'}{abs(tx)}_{'m' if tz < 0 else 'p'}{abs(tz)}"
            t = Template(name)
            t.blocks = dict(bl)
            t.entities = list(en)
            x0, y0, z0, *_ = t.bounds()
            t.normalize()
            t.sin_auditoria_generica = True   # la auditoría se hace sobre el plano entero (auditoria.py)
            out.append((t, (x0, y0, z0)))
        return out


class Vista:
    """Sistema local de un edificio: origen (ox, oz), altura oy y giro en cuartos de vuelta horarios.

    Local: u hacia la derecha, v hacia el fondo; la fachada es la cara v = 0 y mira al «norte» local.
    """

    def __init__(self, m, ox, oz, giro=0, oy=0):
        self.m, self.ox, self.oz, self.giro, self.oy = m, ox, oz, giro % 4, oy

    def p(self, u, v):
        g = self.giro
        if g == 0:
            return self.ox + u, self.oz + v
        if g == 1:
            return self.ox - v, self.oz + u
        if g == 2:
            return self.ox - u, self.oz - v
        return self.ox + v, self.oz - u

    def set(self, u, y, v, state, nbt=None):
        x, z = self.p(u, v)
        self.m.set(x, self.oy + y, z, girar(norm(state), self.giro), nbt)

    def get(self, u, y, v):
        x, z = self.p(u, v)
        return self.m.get(x, self.oy + y, z)

    def fill(self, u1, y1, v1, u2, y2, v2, state):
        s = (girar(norm(state), self.giro), None)
        for u in range(min(u1, u2), max(u1, u2) + 1):
            for v in range(min(v1, v2), max(v1, v2) + 1):
                x, z = self.p(u, v)
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.m.blocks[(x, self.oy + y, z)] = s

    def air(self, *c):
        self.fill(*c, "air")

    def water(self, *c):
        self.fill(*c, "water")

    def shell(self, u1, y1, v1, u2, y2, v2, wall, floor=None, roof=None):
        """Caja hueca: muros, suelo y techo; el interior no se toca."""
        floor, roof = floor or wall, roof or wall
        for u in range(u1, u2 + 1):
            for v in range(v1, v2 + 1):
                self.set(u, y1, v, floor)
                self.set(u, y2, v, roof)
                if u in (u1, u2) or v in (v1, v2):
                    for y in range(y1 + 1, y2):
                        self.set(u, y, v, wall)

    def disco(self, cu, cv, r, y1, y2, state, hueco=None):
        """Cilindro macizo de radio r (o anillo si hueco = radio interior)."""
        for u in range(cu - r, cu + r + 1):
            for v in range(cv - r, cv + r + 1):
                d = math.hypot(u - cu, v - cv)
                if d <= r + 0.3 and (hueco is None or d > hueco + 0.3):
                    self.fill(u, y1, v, u, y2, v, state)

    def cupula(self, cu, cv, r, y0, state, nervio=None, cada=4):
        """Semiesfera hueca de radio r apoyada en y0; nervio = material de los meridianos."""
        for u in range(cu - r, cu + r + 1):
            for v in range(cv - r, cv + r + 1):
                for y in range(0, r + 1):
                    d = math.sqrt((u - cu) ** 2 + (v - cv) ** 2 + y * y)
                    if r - 1 < d <= r:
                        es_nervio = nervio and (u == cu or v == cv or abs(u - cu) == abs(v - cv) or y % cada == 0 and False)
                        self.set(u, y0 + y, v, nervio if es_nervio else state)

    def quitar(self, u1, y1, v1, u2=None, y2=None, v2=None):
        """Borra lo construido (vuelve a lo que deja la pieza base: agua sobre el suelo)."""
        u2, y2, v2 = (u1 if u2 is None else u2), (y1 if y2 is None else y2), (v1 if v2 is None else v2)
        for u in range(min(u1, u2), max(u1, u2) + 1):
            for v in range(min(v1, v2), max(v1, v2) + 1):
                x, z = self.p(u, v)
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.m.blocks.pop((x, self.oy + y, z), None)

    def built(self, u, y, v):
        x, z = self.p(u, v)
        return self.m.built(x, self.oy + y, z)

    def mira(self, d):
        """Dirección del mundo que corresponde a la dirección local d."""
        return GIRO[(GIRO.index(d) + self.giro) % 4]

    def entity(self, u, y, v, nbt):
        x, z = self.p(u, v)
        self.m.entity(x, self.oy + y, z, nbt)

    def marca(self, nombre_, u, y, v):
        x, z = self.p(u, v)
        self.m.marca(nombre_, x, self.oy + y, z)

    def sitio(self, nombre_, u1, y1, v1, u2, y2, v2, ruinoso=False):
        (x1, z1), (x2, z2) = self.p(u1, v1), self.p(u2, v2)
        self.m.sitio(nombre_, x1, self.oy + y1, z1, x2, self.oy + y2, z2, ruinoso)

    def caja(self, u1, v1, u2, v2):
        (x1, z1), (x2, z2) = self.p(u1, v1), self.p(u2, v2)
        return min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2)
