"""Galleon puzzles and traps checked with the shared simulator (unicas/_comun/redstone.py)."""
from core import parse_state
from .._common import redstone

N6 = tuple(redstone.D6.values())
add = redstone.add


def wire_ends(t, p):
    """Hooks at the ends of the trap wire that passes through p."""
    axis = (0, 0, 1) if "north=true" in t.get(*p) else (1, 0, 0)
    out = []
    for sign in (1, -1):
        q = p
        for _ in range(42):
            q = add(q, tuple(sign * a for a in axis))
            b = redstone.bn(t.get(*q))
            if b != "tripwire":
                if b == "tripwire_hook":
                    out.append(q)
                break
    return out


def check(t, scenarios):
    """Placed state is stable and, for each scenario (actions -> expected effects), the effect occurs."""
    errs, _ = redstone.check_static(t)
    errs = [f"redstone: {e}" for e in errs]
    for name, acts, expects in scenarios:
        inputs = {}
        for kind, p in acts:
            if kind == "palanca":
                inputs[p] = parse_state(t.get(*p))[1]["powered"] != "true"
            elif kind == "pisar":
                inputs[p] = True
            elif kind == "cable":
                ends = wire_ends(t, p)
                if len(ends) != 2:
                    errs.append(f"redstone {name}: wire {p} does not end in two hooks")
                inputs.update({h: True for h in ends})
        sim = redstone.Sim(t, inputs)
        for kind, p in expects:
            want = kind in ("abierta", "dispara", "tnt")
            if sim.powered(p) != want:
                errs.append(f"redstone {name}: {kind} at {p} is not met")
    return errs
