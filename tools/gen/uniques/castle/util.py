"""Castle's own utilities: canvas with shortcuts, corner door (on top of _common.pieces.piston_door).
The walkthrough is in _comun/walkthrough.py."""
from core import Template, parse_state
import lint
from .._common.pieces import piston_door

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}

class Canvas(Template):
    """Template with drawing shortcuts."""

    def box(self, x1, y1, z1, x2, y2, z2, wall, floor=None, ceil=None):
        """Hollow room: optional walls, floor and ceiling; the interior is left with explicit air."""
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
    """1 x 2 secret door in the side wall (side=-1 west, +1 east) of the first row (z=c) of a room, in the
    corner: the pistons (piston_door) sit inside the north wall and retract the door into the corner block, which cannot
    be seen from either side. A torch on the block (a, L-1, c-2) powers the lower piston and, through the block
    it powers above, the upper one; powering that block opens it. With input_floor, a lever on the corner floor and
    cross-shaped dust under the wall. Requires solid walls 3 thick to the north and on that side."""
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
