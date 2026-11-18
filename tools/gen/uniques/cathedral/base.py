"""Utilities of the cathedral model: materials, states and symmetry."""
import math
from core import parse_state, state_str

SB, CSB, CRK, MSB = "stone_bricks", "chiseled_stone_bricks", "cracked_stone_bricks", "mossy_stone_bricks"
PA, PD, SM = "polished_andesite", "polished_diorite", "smooth_stone"
ROOF, ROOFS = "deepslate_tiles", "deepslate_tile_stairs"
WALLB = "stone_brick_wall"
ZC = 30                       # axis of symmetry (z)
AX, AZ = 89, 30               # center of the apse

GLASS = ["blue_stained_glass_pane", "red_stained_glass_pane", "purple_stained_glass_pane", "light_blue_stained_glass_pane"]

MIRROR = {"north": "south", "south": "north"}
HINGE = {"left": "right", "right": "left"}
SHAPE = {"inner_left": "inner_right", "inner_right": "inner_left", "outer_left": "outer_right", "outer_right": "outer_left"}


def s(name, **p):
    """Block state: s('oak_stairs', facing='east', half='bottom')."""
    return state_str("minecraft:" + name, {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in p.items()})


def mirror_state(st):
    bid, p = parse_state(st)
    q = dict(p)
    for k, v in p.items():
        if k == "facing" and v in MIRROR:
            q[k] = MIRROR[v]
        elif k == "hinge":
            q[k] = HINGE[v]
        elif k == "shape" and v in SHAPE:
            q[k] = SHAPE[v]
        elif k in ("north", "south"):
            q["south" if k == "north" else "north"] = v
    return state_str(bid, q)


def stairs(mat, facing, half="bottom"):
    return s(mat + "_stairs" if not mat.endswith("_stairs") else mat, facing=facing, half=half)


def slab(mat, typ="bottom"):
    return s(mat + "_slab", type=typ)


def polar(x, z):
    """Distance and angle (degrees, -180..180) relative to the center of the apse."""
    dx, dz = x - AX, z - AZ
    return math.hypot(dx, dz), math.degrees(math.atan2(dz, dx))


def angdist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)
