"""Atlantis redstone mechanisms (always dry: water tears away dust and torches)."""
from . import buildings as E

SOLID = "prismarine_bricks"


def combination(v, u0, y, vm, pattern, name, solid=SOLID):
    """Combination door. Levers on the north face of the wall v = vm, at height y (the feet go at y - 1).

    patron = list of 4 booleans (True = the lever must end up pulled). Behind the wall there is a sealed cavity:
    each lever that must be pulled has a torch behind it (lit while the lever is off) and each
    one that must stay off, dust; everything feeds into a common line that is "something is wrong". An inverter torch at the
    end lights only if nothing is wrong and opens the iron door, set back one block behind the wall opening
    at u0 + 9. Initial states consistent with all levers off (there are no updates during generation).
    It occupies u0 - 1 .. u0 + 10, v = vm .. vm + 3, y - 2 .. y + 2. Returns the cell (u, y - 1, v) behind the door.
    """
    assert len(pattern) == 4 and any(pattern)
    v.fill(u0 - 1, y - 2, vm, u0 + 10, y + 2, vm + 3, solid)
    for i, required in enumerate(pattern):
        u = u0 + 2 * i
        v.set(u, y, vm - 1, "lever[face=wall,facing=north,powered=false]")
        if required:
            v.set(u, y, vm + 1, "redstone_wall_torch[facing=south,lit=true]")
        else:
            v.set(u, y, vm + 1, "redstone_wire[north=side,south=side,east=none,west=none,power=0]")
    for u in range(u0, u0 + 8):
        branch = (u - u0) % 2 == 0
        v.set(u, y, vm + 2, f"redstone_wire[east=side,west={'none' if u == u0 else 'side'},north={'side' if branch else 'none'},south=none,power=0]")
    v.set(u0 + 8, y, vm + 1, "redstone_wall_torch[facing=north,lit=false]")       # inverter, on the block (u0 + 8, y, vm + 2)
    pu = u0 + 9
    v.air(pu, y - 1, vm, pu, y, vm)                                               # opening in the wall
    v.set(pu, y - 1, vm + 1, "iron_door[facing=north,half=lower,hinge=left,open=false,powered=false]")
    v.set(pu, y, vm + 1, "iron_door[facing=north,half=upper,hinge=left,open=false,powered=false]")
    v.air(pu, y - 1, vm + 2, pu, y, vm + 3)                                       # passage behind the door
    v.mark("puerta_" + name, pu, y, vm + 1)
    for i in range(4):
        v.mark("palanca_" + name, u0 + 2 * i, y, vm - 1)
    for u in range(u0, u0 + 9):                                                   # solid blocks over each component:
        for w in (vm + 1, vm + 2):                                                # the smoke test "touches" them to propagate
            v.mark("toque_" + name, u, y + 1, w)                               # as a player would when activating
    return pu, y - 1, vm + 3


def arrow_trap(v, u, y, w, side):
    """Pressure plate next to an arrow dispenser embedded in the wall (lado = 'east' or 'west' of the corridor)."""
    du = 1 if side == "east" else -1
    from . import things as C
    C.dispenser(v, u + du, y, w, "west" if side == "east" else "east", "arrow", 24)
    v.set(u, y, w, "stone_pressure_plate[powered=false]")
    v.mark("trampa", u, y, w)


def water_trap(v, u, y, w, side):
    """Like the arrow one, but the dispenser pours a bucket of water: the corridor floods."""
    du = 1 if side == "east" else -1
    from . import things as C
    C.dispenser(v, u + du, y, w, "west" if side == "east" else "east", "water_bucket", 1)
    v.set(u, y, w, "stone_pressure_plate[powered=false]")
    v.mark("trampa", u, y, w)


def bomb_chest(v, u, y, w, facing, tbl):
    """Trapped chest over TNT: opening it ignites it."""
    from . import things as C
    v.set(u, y - 1, w, "tnt[unstable=false]")
    C.place_chest(v, u, y, w, facing, tbl, kind="trapped_chest")
    v.mark("trampa", u, y, w)
