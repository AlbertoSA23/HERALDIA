"""Simulador mínimo de redstone (sin polvo) para comprobar los puzles y trampas del galeón.

Componentes: palanca, antorcha (de pie o de pared), placa de presión, gancho de cable, bloque macizo, pistón,
puerta de hierro, dispensador y TNT. Comprueba que el estado colocado es estable y que cada acción tiene su efecto.
"""
from core import parse_state

N6 = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
BACK = {"north": (0, 0, 1), "south": (0, 0, -1), "east": (-1, 0, 0), "west": (1, 0, 0)}


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def nm(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


MECH = ("sticky_piston", "piston", "iron_door", "dispenser", "tnt")
SOLID_NO = ("air", "redstone_wall_torch", "redstone_torch", "lever", "stone_pressure_plate", "tripwire_hook", "tripwire",
            "piston_head", "iron_door", "spruce_door", "water", "ladder", "glass_pane", "lantern")


def attached(p, st):
    b, pr = parse_state(st)
    b = nm(b)
    if b == "redstone_torch" or b.endswith("pressure_plate"):
        return add(p, (0, -1, 0))
    if b == "lever" and pr.get("face") != "wall":
        return add(p, (0, -1, 0) if pr["face"] == "floor" else (0, 1, 0))
    return add(p, BACK[pr["facing"]])


class Sim:
    def __init__(self, blocks):
        self.b = blocks          # {pos: estado}
        self.levers = {p: "powered=true" in s for p, s in blocks.items() if nm(s) == "lever"}
        self.torches = {p: "lit=true" in s for p, s in blocks.items() if nm(s) in ("redstone_torch", "redstone_wall_torch")}
        self.pressed, self.hooks = set(), set()

    def solid(self, p):
        s = self.b.get(p)
        return s is not None and nm(s) not in SOLID_NO and not nm(s).endswith(("_stairs", "_slab", "_fence", "_carpet"))

    def strong(self, p):
        for q, on in self.levers.items():
            if on and attached(q, self.b[q]) == p:
                return True
        if self.torches.get(add(p, (0, -1, 0))):
            return True
        if add(p, (0, 1, 0)) in self.pressed:
            return True
        return any(attached(h, self.b[h]) == p for h in self.hooks)

    def settle(self):
        for _ in range(32):
            new = {p: not self.strong(attached(p, self.b[p])) for p in self.torches}
            if new == self.torches:
                return True
            self.torches = new
        return False

    def source_at(self, n, target):
        if self.torches.get(n) and attached(n, self.b[n]) != target:
            return True
        if self.levers.get(n) or n in self.pressed or n in self.hooks:
            return True
        return self.solid(n) and self.strong(n)

    def active(self, p):
        if any(self.source_at(add(p, d), p) for d in N6):
            return True
        s = self.b[p]
        if nm(s) in ("sticky_piston", "piston"):        # cuasiconectividad
            up = add(p, (0, 1, 0))
            return any(self.source_at(add(up, d), up) for d in N6 if add(up, d) != p)
        if nm(s) == "iron_door":
            other = add(p, (0, 1, 0) if "half=lower" in s else (0, -1, 0))
            return any(self.source_at(add(other, d), other) for d in N6 if add(other, d) != p)
        return False


def wire_ends(blocks, p):
    """Ganchos en los extremos del cable que pasa por p."""
    s = blocks[p]
    axis = (0, 0, 1) if "north=true" in s else (1, 0, 0)
    out = []
    for sign in (1, -1):
        q = p
        for _ in range(42):
            q = add(q, tuple(sign * a for a in axis))
            if nm(blocks.get(q)) == "tripwire_hook":
                out.append(q)
                break
            if nm(blocks.get(q)) != "tripwire":
                break
    return out


def check(blocks, escenarios):
    errs = []
    sim = Sim(blocks)
    if not sim.settle():
        return ["redstone: el circuito colocado oscila"]
    for p, lit in sim.torches.items():
        if lit != ("lit=true" in blocks[p]):
            errs.append(f"redstone: antorcha {p} colocada {'encendida' if not lit else 'apagada'} y debería estar al revés")
    for p, s in blocks.items():
        if nm(s) in MECH or (nm(s) == "iron_door" and "half=lower" in s):
            on = sim.active(p)
            if nm(s).endswith("piston") and on != ("extended=true" in s):
                errs.append(f"redstone: pistón {p} no coincide con su alimentación")
            if nm(s) == "iron_door" and "half=lower" in s and on:
                errs.append(f"redstone: puerta {p} recibe señal al colocarse")
            if nm(s) in ("dispenser", "tnt") and on:
                errs.append(f"redstone: {nm(s)} {p} se activa al colocarse")
    for name, acts, expects in escenarios:
        s2 = Sim(blocks)
        for kind, p in acts:
            if kind == "palanca":
                s2.levers[p] = not s2.levers[p]
            elif kind == "pisar":
                s2.pressed.add(p)
            elif kind == "cable":
                ends = wire_ends(blocks, p)
                if len(ends) != 2:
                    errs.append(f"redstone {name}: el cable {p} no acaba en dos ganchos")
                s2.hooks.update(ends)
        if not s2.settle():
            errs.append(f"redstone {name}: oscila")
            continue
        for kind, p in expects:
            on = s2.active(p)
            want = kind in ("abierta", "dispara", "tnt")
            if kind == "retraido":
                want = False
            if on != want:
                errs.append(f"redstone {name}: {kind} en {p} no se cumple")
    return errs
