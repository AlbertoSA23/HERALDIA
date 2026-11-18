"""Atlantis plan: layout, lots and districts."""
import math
from . import urban_layout as U
from . import things as C
from . import buildings as E
from .world import World, View

S = U.FLOOR
STEP = 24                 # grid of lots
CORE = 96               # radius reserved for the acropolis
CARDINAL, DIAGONAL = 230, 156
ZONES = {                 # special districts: center and reserved radius
    "agora": (0, -CARDINAL, 60), "termas": (CARDINAL, 0, 60), "puerto": (0, CARDINAL, 60), "academia": (-CARDINAL, 0, 60),
    "artesanos": (DIAGONAL, -DIAGONAL, 34), "arsenal": (DIAGONAL, DIAGONAL, 50), "jardines": (-DIAGONAL, DIAGONAL, 50),
    "anfiteatro": (-DIAGONAL, -DIAGONAL, 50),
}


def free(x, z, middle):
    """The lot centered at (x, z) with medium half-side does not overlap avenues, core, wall or special districts."""
    r = math.hypot(x, z)
    if r < CORE + middle or r > U.RADIUS - U.WALL - U.ROUND - middle * 1.5:
        return False
    if abs(x) < U.AVENUE + 4 + middle or abs(z) < U.AVENUE + 4 + middle:
        return False
    return all(math.hypot(x - cx, z - cz) >= rad + middle for cx, cz, rad in ZONES.values() if rad)


def turn_to_center(x, z):
    """Rotation so that the facade faces the nearest avenue (toward the dominant axis)."""
    if abs(x) >= abs(z):
        return 3 if x > 0 else 1
    return 0 if z > 0 else 2


def centered_view(m, x, z, w, d, turn):
    v = View(m, 0, 0, turn, S)
    du, dv = v.p((w - 1) // 2, (d - 1) // 2)
    return View(m, x - du, z - dv, turn, S)


def plots(m):
    """Neighborhoods: symmetric orthogonal grid; the type depends on |x|, |z| (symmetry), the detail on x, z."""
    n, middle = 0, STEP // 2
    for i in range(-16, 16):
        for j in range(-16, 16):
            x, z = i * STEP + middle, j * STEP + middle
            if not free(x, z, 8):
                continue
            kind = U.dispersion(i if i >= 0 else -i - 1, j if j >= 0 else -j - 1, 11) % 100
            salt = U.dispersion(i, j, 12) % 1000
            turn = turn_to_center(x, z)
            ruinous = x < 0 and z > 0 or z > 0 and abs(x) < 110        # toward the gardens and the harbor: more ruin
            w, d = 11 + 2 * (salt % 3), 11 + 2 * (salt // 3 % 2)
            if kind < (21 if ruinous else 5):
                E.ruin_piece(centered_view(m, x, z, w, d, turn), w, d, salt, place_chest="menor" if salt % 6 == 0 else None)
            elif kind < 58:
                E.house(centered_view(m, x, z, w, d, turn), w, d, True, salt, place_chest="menor" if salt % 3 == 0 else None)
            elif kind < 76:
                v = centered_view(m, x, z, w, d, turn)
                E.house(v, w, d, False, salt, place_chest="menor" if salt % 5 == 0 else None, name="casa_inundada")
                if salt % 4 == 1:
                    C.generator(v, 1, 1, d - 2, "drowned", trident=salt % 8 == 1)
                elif salt % 4 == 2:
                    v.entity(w // 2, 2, d // 2, C.drowned(salt % 3 == 0))
            elif kind < 88:
                E.tower(centered_view(m, x, z, 11, 11, turn), 5, salt, place_chest="media")
            else:
                E.small_plaza(centered_view(m, x, z, 9, 9, turn), 9, salt)
                if salt % 2:
                    m.entity(x, S + 3, z + 6, C.guardian())
            n += 1
    return n


def construct():
    from . import districts as D
    from . import acropolis as A
    m = World()
    m.plot_count = plots(m)
    for name, (cx, cz, _) in ZONES.items():
        turn = {"agora": 2, "termas": 3, "puerto": 0, "academia": 1}.get(name, turn_to_center(cx, cz))
        D.DISTRICTS[name](View(m, cx, cz, turn, S))
    v = View(m, 0, 0, 0, 0)
    A.temple(v)
    finish = A.vestibule(v)
    segments = A.tunnels(v)
    A.populate_galleries(v, segments)
    A.chambers(v, finish)
    m.clean_algae()
    m.flood()
    return m
