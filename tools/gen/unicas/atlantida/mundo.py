"""Plano de la ciudad en vóxeles: se construye entero y luego se corta en teselas (plantillas)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core import Template, parse_state, state_str
from . import urbanismo as U

_norm = {}


def norm(state):
    s = _norm.get(state)
    if s is None:
        s = _norm[state] = state_str(*parse_state(state))
    return s


class Mundo:
    def __init__(self):
        self.blocks = {}      # (x, y, z) -> (estado, nbt | None)
        self.entities = []    # (x, y, z, nbt)
        self.marcas = {}      # nombre -> lista de celdas (para auditoría, planos y prueba de humo)

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

    def air(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, "air")

    def water(self, x1, y1, z1, x2, y2, z2):
        self.fill(x1, y1, z1, x2, y2, z2, "water")

    def shell(self, x1, y1, z1, x2, y2, z2, wall, floor=None, roof=None):
        """Caja hueca: muros, suelo y techo; el interior no se toca."""
        floor, roof = floor or wall, roof or wall
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                self.set(x, y1, z, floor)
                self.set(x, y2, z, roof)
                if x in (x1, x2) or z in (z1, z2):
                    for y in range(y1 + 1, y2):
                        self.set(x, y, z, wall)

    def entity(self, x, y, z, nbt):
        self.entities.append((x, y, z, nbt))

    def marca(self, nombre, x, y, z):
        self.marcas.setdefault(nombre, []).append((x, y, z))

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
