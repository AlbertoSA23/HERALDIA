"""Utilidades propias del castillo: lienzo con atajos, puerta de rincón (sobre _comun.piezas.piston_door).
El recorrido a pie está en _comun/recorrido.py."""
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
