"""Simulación sencilla de redstone: palancas, antorchas (de suelo y de pared) y polvo plano.

Sirve para comprobar que un circuito colocado en una plantilla está en su estado estable (nada depende de una
actualización de bloque que no ocurre al generar) y qué consumidores reciben señal con cada posición de palancas.
No modela pistones, repetidores ni comparadores.
"""
from core import parse_state
from lint import bname

D6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
DIR = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
NOT_CONDUCTOR = ("air", "water", "glass", "_pane", "lever", "torch", "redstone_wire", "door", "trapdoor", "_slab",
                 "_stairs", "lantern", "chain", "bars", "fence", "sign", "ladder", "cobweb", "tripwire", "plate")


def add(p, d, k=1):
    return (p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k)


def conductor(st):
    return st is not None and not any(w in bname(st) for w in NOT_CONDUCTOR)


def props(st):
    return parse_state(st)[1]


def attached(pos, st):
    b, p = bname(st), props(st)
    if b == "lever":
        return add(pos, {"floor": DIR["down"], "ceiling": DIR["up"]}.get(p["face"]) or tuple(-c for c in DIR[p["facing"]]))
    if b == "redstone_torch":
        return add(pos, DIR["down"])
    if b == "redstone_wall_torch":
        return add(pos, tuple(-c for c in DIR[p["facing"]]))
    return None


def simulate(t, levers):
    """Estado estable con las palancas dadas {pos: encendida}. Devuelve (antorchas, polvo, consumidores alimentados)."""
    g = lambda p: t.get(*p)
    torches = {p: props(st)["lit"] == "true" for p, (st, _) in t.blocks.items() if "redstone" in st and "torch" in st}
    dusts = [p for p, (st, _) in t.blocks.items() if bname(st) == "redstone_wire"]
    for _ in range(64):
        strong = {attached(p, g(p)) for p, on in levers.items() if on}
        strong |= {add(p, DIR["up"]) for p, lit in torches.items() if lit}
        strong = {p for p in strong if conductor(g(p))}
        sources = {p for p, on in levers.items() if on} | {p for p, lit in torches.items() if lit}
        power = {d: 15 if any(add(d, v) in sources or add(d, v) in strong for v in D6) else 0 for d in dusts}
        for _ in range(16):
            for d in dusts:
                for v in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
                    n = add(d, v)
                    if n in power:
                        power[d] = max(power[d], power[n] - 1)
        weak = set()
        for d in dusts:
            if power[d]:
                weak.add(add(d, DIR["down"]))
                for name, v in DIR.items():
                    if name in ("up", "down"):
                        continue
                    if props(g(d)).get(name) == "side" and conductor(g(add(d, v))):
                        weak.add(add(d, v))
        new = {p: attached(p, g(p)) not in strong | weak for p in torches}
        if new == torches:
            break
        torches = new
    else:
        raise RuntimeError("el circuito oscila")

    def fed(pos):
        for v in D6:
            n = add(pos, v)
            st = g(n)
            if n in strong or n in weak or levers.get(n):
                return True
            if torches.get(n) and attached(n, st) != pos:
                return True
            if st and bname(st) == "redstone_wire" and power[n]:
                name = [k for k, w in DIR.items() if w == tuple(-c for c in v)][0]
                if props(st).get(name) == "side":
                    return True
        return False
    return torches, power, fed
