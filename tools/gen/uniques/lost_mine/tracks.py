"""Tracks of the loading dock in the Lost Mine: the switch puzzle (design in docs/unicas/lost_mine.md).

A minecart waits on the exit ramp (an unpowered powered rail against the wall: with the start lever it shoots off
to the west). The track passes two switches (T junctions), each with a lever; depending on their state, the minecart ends
up in the spoil heap, on the dead-end track of the foundry or, through a 1 x 1 slit in the north wall (too narrow for
a person), at the weighing platform: a detector rail whose supporting block turns off the inverter torch that holds up the gate of
the mother lode (two extended sticky pistons, like `pieces.lever_door`). Only "switch 1 north, switch 2 east"
reaches the platform; the hint is in the foreman's hidden office.

Switch rule (26.3, `RailState.place`, read from the bytecode): a normal rail with three neighbours that can connect to
it (T junction) curves according to the signal: with no signal the last of NW, NE, SW, SE that has both its neighbours wins; with
a signal, the last of SE, SW, NE, NW. A north-south T with a branch to the east becomes SE without a signal and NE with one; an east-west T
with a branch to the south becomes SE without a signal and SW with one. `spire_shape` computes this and `traverse` follows the minecart.
"""
from core import parse_state

DV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
# shape -> {side: dy} (dy = 1 if the track rises one block on that side)
SHAPES = {"north_south": {"north": 0, "south": 0}, "east_west": {"east": 0, "west": 0},
          "ascending_east": {"west": 0, "east": 1}, "ascending_west": {"east": 0, "west": 1},
          "ascending_north": {"south": 0, "north": 1}, "ascending_south": {"north": 0, "south": 1},
          "south_east": {"south": 0, "east": 0}, "south_west": {"south": 0, "west": 0},
          "north_west": {"north": 0, "west": 0}, "north_east": {"north": 0, "east": 0}}
RAILS = ("rail", "powered_rail", "detector_rail", "activator_rail")
Y = 1                                    # footings of the loading dock

# layout (x, z) of the loading dock; the switches and the levers
OUTPUT, CAP = (100, 36), (101, 36)      # exit ramp (powered rail against the east wall)
START = (100, 35)                     # floor lever next to the exit
SWITCH1, LEVER1 = (89, 36), (88, 36)    # north-south T with a branch to the east (where the minecart arrives from)
SWITCH2, LEVER2 = (89, 30), (89, 29)    # east-west T with a branch to the south (where it arrives from)
SPOIL_HEAP, SMELTER = (89, 44), (83, 30)
DOOR_COL = (92, 24)                        # mother lode gate (lower block at y = 1), in the north wall
SEESAW = (96, 2, 24)                    # detector rail, inside the wall
SOLUTION = (True, False)                 # switch 1 with a signal (north), switch 2 without a signal (east)


def spire_shape(neighbors, with_signal):
    """Shape the game gives a rail with those neighbours ({'north', ...}) and that signal (RailState.place)."""
    n, s, w, e = ("north" in neighbors, "south" in neighbors, "west" in neighbors, "east" in neighbors)
    form = None
    if (n or s) and not w and not e:
        form = "north_south"
    if (w or e) and not n and not s:
        form = "east_west"
    se, sw, ne, nw = s and e, s and w, n and e, n and w
    if se and not n and not w:
        form = "south_east"
    if sw and not n and not e:
        form = "south_west"
    if nw and not s and not e:
        form = "north_west"
    if ne and not s and not w:
        form = "north_east"
    if form is None:
        order = ((se, "south_east"), (sw, "south_west"), (ne, "north_east"), (nw, "north_west")) if with_signal else \
                ((nw, "north_west"), (ne, "north_east"), (sw, "south_west"), (se, "south_east"))
        for ok, f in order:
            if ok:
                form = f
    return form


def is_rail(st):
    return st is not None and parse_state(st)[0].replace("minecraft:", "") in RAILS


def form(st):
    return parse_state(st)[1]["shape"]


def traverse(get, start, direction, switches=None, steps=200):
    """Follows a minecart from `start` (x, y, z) moving towards `direction`. `switches` {pos: shape} replaces the
    shape of the switches. Returns (last position, path) or raises ValueError if it derails."""
    switches = switches or {}
    p, d, road = start, direction, [start]
    for _ in range(steps):
        st = get(*p)
        f = switches.get(p) or form(st)
        sides = SHAPES[f]
        entrance = OPP[d]
        if p != start and entrance not in sides:
            raise ValueError(f"the minecart derails at {p} (shape {f}, enters from {entrance})")
        output = [l for l in sides if l != entrance][0] if p != start else d
        dx, dz = DV[output]
        next_unique = None
        for dy in (sides.get(output, 0), 0, -1):
            q = (p[0] + dx, p[1] + dy, p[2] + dz)
            if is_rail(get(*q)):
                next_unique = q
                break
        if next_unique is None:
            return p, road
        p, d = next_unique, output
        road.append(p)
    raise ValueError("the minecart never stops")


def trace(o):
    """Places the tracks, levers, signs, minecart and gate in the build `o`; returns the mechanisms."""
    s, y = o.s, Y
    rail = o.rail
    # exit: unpowered powered rail against the wall (buffer stop), a normal insulating rail and two powered rails with a redstone block
    # underneath (always on) so the empty minecart travels far
    rail(*_p(OUTPUT), "east_west", "powered_rail", False)
    s(START[0], y, START[1], "lever[face=floor,facing=west,powered=false]")
    for x in range(SWITCH1[0] + 1, OUTPUT[0]):
        if x in (97, 98, 93):
            rail(x, y, 36, "east_west", "powered_rail", True)
            s(x, y - 1, 36, "redstone_block")
        else:
            rail(x, y, 36, "east_west")
    # switch 1 (north-south T with a branch to the east) and its floor lever to the west
    rail(*_p(SWITCH1), spire_shape({"north", "south", "east"}, False))
    s(LEVER1[0], y, LEVER1[1], "lever[face=floor,facing=east,powered=false]")
    # south branch, to the spoil heap
    for z in range(SWITCH1[1] + 1, SPOIL_HEAP[1] + 1):
        if z == 40:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    s(SPOIL_HEAP[0], y, SPOIL_HEAP[1] + 1, "gravel")                    # the spoil heap acts as a buffer stop
    s(SPOIL_HEAP[0] + 1, y, SPOIL_HEAP[1] + 1, "gravel")
    s(SPOIL_HEAP[0], y + 1, SPOIL_HEAP[1] + 1, "gravel")
    # north branch, to switch 2
    for z in range(SWITCH2[1] + 1, SWITCH1[1]):
        if z == 33:
            rail(89, y, z, "north_south", "powered_rail", True)
            s(89, y - 1, z, "redstone_block")
        else:
            rail(89, y, z, "north_south")
    rail(*_p(SWITCH2), spire_shape({"east", "west", "south"}, False))
    s(LEVER2[0], y, LEVER2[1], "lever[face=floor,facing=south,powered=false]")
    # dead-end track of the foundry (to the west), with a barrel as a buffer stop
    for x in range(SMELTER[0], SWITCH2[0]):
        if x == 86:
            rail(x, y, 30, "east_west", "powered_rail", True)
            s(x, y - 1, 30, "redstone_block")
        else:
            rail(x, y, 30, "east_west")
    o.barrel(SMELTER[0] - 1, y, 30, "east")
    # to the weighing platform: east, curve to the north, ramp and slit in the north wall
    for x in range(SWITCH2[0] + 1, 96):
        if x == 92:
            rail(x, y, 30, "east_west", "powered_rail", True)
            s(x, y - 1, 30, "redstone_block")
        else:
            rail(x, y, 30, "east_west")
    rail(96, y, 30, "north_west")
    rail(96, y, 29, "north_south", "powered_rail", True)
    s(96, y - 1, 29, "redstone_block")
    rail(96, y, 28, "north_south")
    rail(96, y, 27, "ascending_north")
    s(96, y, 26, "cobblestone")                                         # support of the high track
    rail(96, y + 1, 26, "north_south")
    rail(96, y + 1, 25, "north_south")                                  # in the slit (wall above and below)
    rail(*SEESAW, "north_south", "detector_rail", False)
    # the gate: piston_door towards the east, inverter torch on the weighing platform's support
    px, pz = DOOR_COL
    from .._common import pieces
    door = [(px, y, pz), (px, y + 1, pz)]
    pieces.piston_door(s, door, (1, 0), "west", "cobblestone")
    torch = (px + 3, y, pz)
    support = (SEESAW[0], SEESAW[1] - 1, SEESAW[2])
    assert support == (torch[0] + 1, y, pz)
    s(*torch, "redstone_wall_torch[facing=west,lit=true]")
    s(torch[0], y + 1, pz, "cobblestone")                            # charged by the torch: the piston above
    s(*support, "cobblestone")
    for p in door:                                                     # niche in front of the gate
        o.carve(p[0], p[1], p[2] + 1, ("roca", "roca", "roca"))
    o.carved.pop((96, y, 26), None)
    o.carved.pop((96, y + 1, 26), None)
    # signs on pillars next to the levers and at the end of each branch
    for (x, z, f, pillar, key, lines) in (
            (87, 36, "east", True, "aguja1", [("Aguja 1", "Switch 1")]),
            (89, 28, "south", True, "aguja2", [("Aguja 2", "Switch 2")]),
            (100, 35, "west", False, "arranque", [("Arranque", "Start")]),        # on the east wall
            (90, 45, "west", True, "escombrera", [("Escombrera", "Spoil heap")]),
            (82, 31, "east", False, "via_muerta", [("A la fundición", "To the foundry"), ("(vía muerta)", "(dead end)")])):
        dx, dz = DV[f]
        if pillar:                                    # 2-high brick pillar that holds up the sign
            for dy in (0, 1):
                s(x - dx, y + dy, z - dz, "stone_bricks")
                o.carved.pop((x - dx, y + dy, z - dz), None)
        o.sign(x, y + 1, z, f, key, lines)
    o.sign(px, y + 3, pz + 1, "south", "compuerta", [("Cámara del", "Lode"), ("filón: se abre", "chamber: opens"),
                                                     ("con el peso", "with the weight"), ("del mineral", "of the ore")])
    o.t.entity(OUTPUT[0], y, OUTPUT[1], {"id": "minecraft:minecart"})
    for pos in door:
        o.carved.pop(pos, None)
    return {"salida": _p(OUTPUT), "arranque": (START[0], y, START[1]), "agujas": [_p(SWITCH1), _p(SWITCH2)],
            "palancas": [(LEVER1[0], y, LEVER1[1]), (LEVER2[0], y, LEVER2[1])], "bascula": SEESAW,
            "apoyo": support, "antorcha": torch, "puerta": door,
            "pistones": [(px + 2, y, pz), (px + 2, y + 1, pz)], "solucion": SOLUTION,
            "destinos": {"escombrera": _p(SPOIL_HEAP), "fundicion": _p(SMELTER), "bascula": SEESAW}}


def _p(xz):
    return (xz[0], Y, xz[1])


def check(t, v):
    """Puzzle errors: every lever combination takes the minecart to its destination and only the right one to the weighing platform."""
    import itertools
    errs = []
    get = t.get
    neighbors = {}
    for a in v["agujas"]:
        neighbors[a] = {d for d, (dx, dz) in DV.items() if is_rail(get(a[0] + dx, a[1], a[2] + dz))}
        if len(neighbors[a]) != 3:
            errs.append(f"switch {a} is not a T junction ({sorted(neighbors[a])})")
        if form(get(*a)) != spire_shape(neighbors[a], False):
            errs.append(f"switch {a} is not in its no-signal shape")
    for p in v["palancas"]:
        nearby_flag = [a for a in v["agujas"] if abs(a[0] - p[0]) + abs(a[2] - p[2]) == 1]
        if len(nearby_flag) != 1:
            errs.append(f"lever {p} is not next to exactly one switch")
    arrive = []
    for combo in itertools.product((False, True), repeat=2):
        switches = {a: spire_shape(neighbors[a], c) for a, c in zip(v["agujas"], combo)}
        try:
            finish, _ = traverse(get, v["salida"], "west", switches)
        except ValueError as e:
            errs.append(f"agujas {combo}: {e}")
            continue
        if finish == v["bascula"]:
            arrive.append(combo)
        elif finish not in v["destinos"].values():
            errs.append(f"switches {combo}: the minecart ends up at {finish}, outside the destinations")
    if arrive != [v["solucion"]]:
        errs.append(f"combinations {arrive} reach the weighing platform (only {v['solucion']} was expected)")
    return errs
