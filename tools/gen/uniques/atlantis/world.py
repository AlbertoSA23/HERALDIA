"""Plano de la ciudad en vóxeles: se construye entero y luego se corta en teselas (plantillas)."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core import Template, parse_state, state_str
import validate
from . import urban_layout as U

_norm = {}
TURN = ["north", "east", "south", "west"]


def norm(state):
    s = _norm.get(state)
    if s is None:
        s = _norm[state] = state_str(*parse_state(state))
    return s


def block_name(state):
    return state.split("[")[0].replace("minecraft:", "") if state else None


def rotate(state, k):
    """Gira un estado k cuartos de vuelta en sentido horario visto desde arriba (norte -> este)."""
    if k % 4 == 0 or "[" not in state:
        return state
    bid, props = parse_state(state)
    if props.get("facing") in TURN:
        props["facing"] = TURN[(TURN.index(props["facing"]) + k) % 4]
    if "axis" in props and props["axis"] in ("x", "z") and k % 2:
        props["axis"] = "z" if props["axis"] == "x" else "x"
    if "rotation" in props:
        props["rotation"] = str((int(props["rotation"]) + 4 * k) % 16)
    sides = {d: props[d] for d in TURN if d in props}          # paneles, vallas, redstone
    for d, v in sides.items():
        props[TURN[(TURN.index(d) + k) % 4]] = v
    return state_str(bid, props)


def floodable(state):
    """El bloque admite la propiedad waterlogged (según los registros de 26.3)."""
    if not validate.BLOCKS:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        validate.load_registries(os.environ.get("MCMETA_SUMMARY") or os.path.join(root, "build", "mcmeta-summary"))
    b = validate.BLOCKS.get(block_name(state))
    return bool(b) and "waterlogged" in b[0]


class World:
    def __init__(self):
        self.blocks = {}      # (x, y, z) -> (estado, nbt | None)
        self.entities = []    # (x, y, z, nbt)
        self.marks = {}      # nombre -> lista de celdas (para auditoría, planos y prueba de humo)
        self.sites = []      # (nombre, x1, y1, z1, x2, y2, z2, ruinoso): cajas de lo construido

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

    def mark(self, name_, x, y, z):
        self.marks.setdefault(name_, []).append((x, y, z))

    def site(self, name_, x1, y1, z1, x2, y2, z2, ruinous=False):
        self.sites.append((name_, min(x1, x2), min(y1, y2), min(z1, z2), max(x1, x2), max(y1, y2), max(z1, z2), ruinous))

    # --- agua ---
    def clean_algae(self):
        """Quita las algas que han quedado sin base y remata las cortadas (otro elemento pisó parte del tallo)."""
        change = True
        while change:
            change = False
            for (x, y, z), (st, _) in list(self.blocks.items()):
                b = block_name(st)
                if b not in ("kelp", "kelp_plant"):
                    continue
                beneath = block_name(self.get(x, y - 1, z))
                if beneath != "kelp_plant" and (beneath in (None, "water", "air", "barrel", "chest", "spawner", "seagrass", "sea_pickle", "kelp")
                                             or any(k in beneath for k in ("_slab", "_stairs", "_fence", "_door", "coral"))):
                    del self.blocks[(x, y, z)]
                    change = True
                elif b == "kelp_plant" and block_name(self.get(x, y + 1, z)) not in ("kelp", "kelp_plant"):
                    self.blocks[(x, y, z)] = (norm("kelp[age=25]"), None)
                    change = True

    def flood(self):
        """Pone waterlogged a cada bloque anegable según su entorno: anegado si toca agua y no toca aire."""
        changes = {}
        for (x, y, z), (st, nbt) in self.blocks.items():
            if st.startswith("minecraft:water") or st == "minecraft:air" or not floodable(st):
                continue
            bid, props = parse_state(st)
            if "waterlogged" in props:
                continue
            neighbors = [self.get(x + a, y + b, z + c) for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
            water = any(v and (v.startswith("minecraft:water") or "waterlogged=true" in v) for v in neighbors)
            air_block = any(v == "minecraft:air" for v in neighbors)
            props["waterlogged"] = "true" if water and not air_block else "false"
            changes[(x, y, z)] = (state_str(bid, props), nbt)
        self.blocks.update(changes)

    # --- teselas ---
    def tiles(self, prefix):
        """[(Template normalizada, (x, y, z) de su esquina mínima en el plano)], ordenadas."""
        groups = {}
        for pos, v in self.blocks.items():
            groups.setdefault((pos[0] // U.TILE, pos[2] // U.TILE), ([], []))[0].append((pos, v))
        for x, y, z, n in self.entities:
            groups.setdefault((x // U.TILE, z // U.TILE), ([], []))[1].append((x, y, z, n))
        out = []
        for (tx, tz) in sorted(groups):
            bl, en = groups[(tx, tz)]
            name = f"{prefix}/t_{'m' if tx < 0 else 'p'}{abs(tx)}_{'m' if tz < 0 else 'p'}{abs(tz)}"
            t = Template(name)
            t.blocks = dict(bl)
            t.entities = list(en)
            x0, y0, z0, *_ = t.bounds()
            t.normalize()
            t.no_generic_audit = True   # la auditoría se hace sobre el plano entero (auditoria.py)
            out.append((t, (x0, y0, z0)))
        return out


class View:
    """Sistema local de un edificio: origen (ox, oz), altura oy y giro en cuartos de vuelta horarios.

    Local: u hacia la derecha, v hacia el fondo; la fachada es la cara v = 0 y mira al «norte» local.
    """

    def __init__(self, m, ox, oz, turn=0, oy=0):
        self.m, self.ox, self.oz, self.turn, self.oy = m, ox, oz, turn % 4, oy

    def p(self, u, v):
        g = self.turn
        if g == 0:
            return self.ox + u, self.oz + v
        if g == 1:
            return self.ox - v, self.oz + u
        if g == 2:
            return self.ox - u, self.oz - v
        return self.ox + v, self.oz - u

    def set(self, u, y, v, state, nbt=None):
        x, z = self.p(u, v)
        self.m.set(x, self.oy + y, z, rotate(norm(state), self.turn), nbt)

    def get(self, u, y, v):
        x, z = self.p(u, v)
        return self.m.get(x, self.oy + y, z)

    def fill(self, u1, y1, v1, u2, y2, v2, state):
        s = (rotate(norm(state), self.turn), None)
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

    def disk(self, cu, cv, r, y1, y2, state, cavity=None):
        """Cilindro macizo de radio r (o anillo si hueco = radio interior)."""
        for u in range(cu - r, cu + r + 1):
            for v in range(cv - r, cv + r + 1):
                d = math.hypot(u - cu, v - cv)
                if d <= r + 0.3 and (cavity is None or d > cavity + 0.3):
                    self.fill(u, y1, v, u, y2, v, state)

    def dome(self, cu, cv, r, y0, state, rib=None, each=4):
        """Semiesfera hueca de radio r apoyada en y0; nervio = material de los meridianos."""
        for u in range(cu - r, cu + r + 1):
            for v in range(cv - r, cv + r + 1):
                for y in range(0, r + 1):
                    d = math.sqrt((u - cu) ** 2 + (v - cv) ** 2 + y * y)
                    if r - 1 < d <= r:
                        is_rib = rib and (u == cu or v == cv or abs(u - cu) == abs(v - cv) or y % each == 0 and False)
                        self.set(u, y0 + y, v, rib if is_rib else state)

    def remove(self, u1, y1, v1, u2=None, y2=None, v2=None):
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

    def facing(self, d):
        """Dirección del mundo que corresponde a la dirección local d."""
        return TURN[(TURN.index(d) + self.turn) % 4]

    def entity(self, u, y, v, nbt):
        x, z = self.p(u, v)
        self.m.entity(x, self.oy + y, z, nbt)

    def mark(self, name_, u, y, v):
        x, z = self.p(u, v)
        self.m.mark(name_, x, self.oy + y, z)

    def site(self, name_, u1, y1, v1, u2, y2, v2, ruinous=False):
        (x1, z1), (x2, z2) = self.p(u1, v1), self.p(u2, v2)
        self.m.site(name_, x1, self.oy + y1, z1, x2, self.oy + y2, z2, ruinous)

    def box(self, u1, v1, u2, v2):
        (x1, z1), (x2, z2) = self.p(u1, v1), self.p(u2, v2)
        return min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2)
