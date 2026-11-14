"""Redstone común: forma de los cables y evaluación estática de la señal con las reglas del juego (uso: from unicas._comun import redstone).

Al generar no hay actualizaciones de bloque: lo que se coloca debe ser ya un estado estable. Este módulo calcula
lo que el juego calcularía (conexiones de cada cable, potencia, antorchas, pistones, puertas, dispensadores, TNT)
y permite simular entradas (palancas, ganchos, placas) para comprobar los puzles y las trampas.
"""
from core import parse_state, state_str

H4 = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
D6 = dict(H4, up=(0, 1, 0), down=(0, -1, 0))
OPP = {"north": "south", "south": "north", "west": "east", "east": "west", "up": "down", "down": "up"}
NON_CONDUCTOR = ("air", "glass", "slab", "stairs", "fence", "_wall", "bars", "pane", "torch", "lever", "rail", "carpet",
                 "door", "lantern", "chain", "banner", "redstone_wire", "tripwire", "ladder", "bed", "campfire",
                 "cauldron", "anvil", "grindstone", "brewing_stand", "lectern", "plate", "piston", "spawner", "lava",
                 "water", "cobweb", "chest", "barrel", "dispenser", "tnt", "leaves", "pot", "button")


def bn(s):
    return s.split("[")[0].replace("minecraft:", "") if s else ""


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def conductor(s):
    b = bn(s)
    return bool(b) and not any(k in b for k in NON_CONDUCTOR)


def attached_dir(s):
    """Dirección (desde el componente) del bloque al que está sujeto."""
    b, p = parse_state(s)
    b = bn(b)
    if b in ("redstone_torch",):
        return "down"
    if b == "redstone_wall_torch" or b == "tripwire_hook":
        return OPP[p["facing"]]
    if b == "lever" or b.endswith("_button"):
        return {"floor": "down", "ceiling": "up"}.get(p["face"]) or OPP[p["facing"]]
    return None


def is_source_connectable(s, d_from_wire):
    b = bn(s)
    return b in ("redstone_torch", "redstone_wall_torch", "lever", "tripwire_hook", "redstone_block") \
        or b.endswith("pressure_plate") or b.endswith("_button")


def wire_links(get, pos):
    """Cables vecinos de un cable: {dirección: posición}, incluidos los que suben o bajan un bloque."""
    out = {}
    for d, v in H4.items():
        n = add(pos, v)
        up, dn = add(n, (0, 1, 0)), add(n, (0, -1, 0))
        if bn(get(*n)) == "redstone_wire":
            out[d] = n
        elif bn(get(*up)) == "redstone_wire" and not conductor(get(*add(pos, (0, 1, 0)))):
            out[d] = up
        elif bn(get(*dn)) == "redstone_wire" and not conductor(get(*n)):
            out[d] = dn
    return out


def wire_connections(get, pos):
    """Conexiones que el juego calcula para un cable (también los que suben o bajan un peldaño)."""
    links = wire_links(get, pos)
    c = {}
    for d, v in H4.items():
        n = get(*add(pos, v))
        c[d] = d in links or (n is not None and is_source_connectable(n, d))
    ns_empty = not c["north"] and not c["south"]
    ew_empty = not c["east"] and not c["west"]
    if ns_empty:
        c["east"] = c["west"] = True
    if ew_empty:
        c["north"] = c["south"] = True
    return c


def wire_shapes(t):
    for pos, (s, nbt) in list(t.blocks.items()):
        if bn(s) == "redstone_wire":
            c = wire_connections(t.get, pos)
            _, p = parse_state(s)
            up = {d for d, q in wire_links(t.get, pos).items() if q[1] > pos[1]}
            p.update({d: ("up" if d in up else "side" if v else "none") for d, v in c.items()})
            p.setdefault("power", "0")
            t.blocks[pos] = (state_str("minecraft:redstone_wire", p), nbt)


class Sim:
    """Evaluación estática: entradas fijas (palancas, ganchos, placas) y punto fijo de cables y antorchas."""

    def __init__(self, t, inputs=None):
        self.get0 = t.get
        self.blocks = t.blocks
        self.inputs = inputs or {}            # pos -> powered (bool) para palancas, ganchos y placas
        self.torch = {}
        self.wire = {}
        self.conn = {}
        self.links = {}
        for pos, (s, _) in t.blocks.items():
            b = bn(s)
            if b in ("redstone_torch", "redstone_wall_torch"):
                self.torch[pos] = True
            elif b == "redstone_wire":
                self.wire[pos] = 0
                self.conn[pos] = wire_connections(t.get, pos)
                self.links[pos] = list(wire_links(t.get, pos).values())
        self.solve()

    def get(self, *p):
        return self.get0(*p)

    def src_on(self, pos):
        s = self.get(*pos)
        b = bn(s)
        if pos in self.inputs:
            return self.inputs[pos]
        if b in ("lever", "tripwire_hook") or b.endswith("pressure_plate") or b.endswith("_button"):
            return parse_state(s)[1].get("powered") == "true"
        return False

    def direct(self, n, target, wires=True):
        """Señal fuerte que el componente en n da al bloque target."""
        s = self.get(*n)
        b = bn(s)
        if b in ("lever", "tripwire_hook") or b.endswith("_button"):
            return 15 if self.src_on(n) and add(n, D6[attached_dir(s)]) == target else 0
        if b.endswith("pressure_plate"):
            return 15 if self.src_on(n) and target == add(n, D6["down"]) else 0
        if b in ("redstone_torch", "redstone_wall_torch"):
            return 15 if self.torch[n] and target == add(n, D6["up"]) else 0
        if b == "redstone_wire":
            return self.weak(n, target) if wires else 0
        return 0

    def weak(self, n, target, wires=True):
        """Señal que n da a la posición vecina target (lo que lee un componente en target)."""
        s = self.get(*n)
        b = bn(s)
        if b in ("lever", "tripwire_hook") or b.endswith("pressure_plate") or b.endswith("_button"):
            return 15 if self.src_on(n) else 0
        if b in ("redstone_torch", "redstone_wall_torch"):
            return 15 if self.torch[n] and add(n, D6[attached_dir(s)]) != target else 0
        if b == "redstone_wire":
            if not wires:
                return 0
            p = self.wire[n]
            if target == add(n, D6["down"]):
                return p
            for d, v in H4.items():
                if add(n, v) == target:
                    return p if self.conn[n][d] else 0
            return 0
        if conductor(s):
            return self.strong(n, wires)
        return 0

    def strong(self, pos, wires=True):
        return max([self.direct(add(pos, v), pos, wires) for v in D6.values()] + [0])

    def signal_at(self, pos, skip=None, wires=True):
        return max([self.weak(add(pos, v), pos, wires) for d, v in D6.items() if d != skip] + [0])

    def solve(self):
        for _ in range(64):
            changed = False
            for pos in self.torch:
                s = self.get(*pos)
                lit = self.weak(add(pos, D6[attached_dir(s)]), pos) == 0
                if lit != self.torch[pos]:
                    self.torch[pos] = lit
                    changed = True
            # potencia de los cables: fuentes no cable y vecinos cable - 1
            base = {w: self.signal_at(w, wires=False) for w in self.wire}
            power = dict(base)
            for _ in range(16):
                nxt = {w: max([base[w]] + [power[q] - 1 for q in self.links[w] if q in power]) for w in power}
                if nxt == power:
                    break
                power = nxt
            if power != self.wire:
                self.wire = power
                changed = True
            if not changed:
                return
        raise ValueError("el circuito oscila")

    def powered(self, pos):
        """¿Un componente (pistón, puerta, dispensador, TNT) en pos recibe señal?"""
        s = self.get(*pos)
        b = bn(s)
        if b in ("piston", "sticky_piston"):
            f = parse_state(s)[1]["facing"]
            if self.signal_at(pos, skip=f):
                return True
            above = add(pos, D6["up"])
            return any(self.weak(add(above, v), above) for d, v in D6.items() if d != "down")
        if b.endswith("_door"):
            other = add(pos, D6["up"] if parse_state(s)[1]["half"] == "lower" else D6["down"])
            return bool(self.signal_at(pos) or self.signal_at(other))
        if b == "dispenser":
            return bool(self.signal_at(pos) or self.signal_at(add(pos, D6["up"])))
        return bool(self.signal_at(pos))


def check_static(t):
    """El estado colocado coincide con el que el juego calcularía (nada espera una actualización)."""
    errs = []
    sim = Sim(t)
    for pos, (s, _) in t.blocks.items():
        b, p = parse_state(s)
        b = bn(b)
        if b == "redstone_wire":
            exp = sim.conn[pos]
            for d in H4:
                if (p.get(d) != "none") != exp[d]:
                    errs.append(f"cable con forma distinta de la calculada en {pos}")
            if int(p.get("power", 0)) != sim.wire[pos]:
                errs.append(f"cable con potencia {p.get('power')} y debería tener {sim.wire[pos]} en {pos}")
        elif b in ("redstone_torch", "redstone_wall_torch"):
            if (p["lit"] == "true") != sim.torch[pos]:
                errs.append(f"antorcha de redstone inestable en {pos}")
        elif b in ("piston", "sticky_piston"):
            if (p["extended"] == "true") != sim.powered(pos):
                errs.append(f"pistón inestable en {pos}")
            if p["extended"] == "true":
                head = t.get(*add(pos, D6[p["facing"]]))
                if bn(head) != "piston_head":
                    errs.append(f"pistón extendido sin cabeza en {pos}")
        elif b.endswith("_door") and b.startswith("iron"):
            if (p["open"] == "true") != sim.powered(pos) or (p["powered"] == "true") != sim.powered(pos):
                errs.append(f"puerta de hierro inestable en {pos}")
        elif b == "dispenser" and sim.powered(pos) != (p["triggered"] == "true"):
            errs.append(f"dispensador inestable en {pos}")
        elif b == "redstone_lamp" and (p["lit"] == "true") != sim.powered(pos):
            errs.append(f"lámpara inestable en {pos}")
        elif b == "tnt" and sim.powered(pos):
            errs.append(f"TNT con señal al colocarse en {pos}")
        elif b in ("lever", "tripwire_hook", "redstone_wall_torch"):
            a = t.get(*add(pos, D6[attached_dir(s)]))
            if not conductor(a):
                errs.append(f"{b} sin bloque sólido detrás en {pos}")
    return errs, sim


def set_wire_power(t):
    sim = Sim(t)
    for pos, pw in sim.wire.items():
        s, nbt = t.blocks[pos]
        _, p = parse_state(s)
        p["power"] = str(pw)
        t.blocks[pos] = (state_str("minecraft:redstone_wire", p), nbt)


def check_puzzle(t, nombre, levers, solucion, salida, abre_si="con_potencia"):
    """Prueba todas las combinaciones de las palancas de un puzle: solo la solución debe abrirlo.
    salida: componentes (pistón, puerta...) que mueve el puzle; abre_si: "con_potencia" (puerta que se abre con
    señal) o "sin_potencia" (pistones que sostienen la pared mientras reciben señal)."""
    import itertools
    errs = []
    for combo in itertools.product((False, True), repeat=len(levers)):
        sim = Sim(t, dict(zip(levers, combo)))
        on = [sim.powered(p) for p in salida]
        abre = all(on) if abre_si == "con_potencia" else not any(on)
        if abre != (tuple(combo) == tuple(solucion)):
            errs.append(f"puzle {nombre}: con palancas {combo} {'abre' if abre else 'no abre'}")
    return errs


def set_torches(t):
    """Fija el estado lit de cada antorcha de redstone al estable (tras set_wire_power)."""
    sim = Sim(t)
    for pos, lit in sim.torch.items():
        s, nbt = t.blocks[pos]
        b, p = parse_state(s)
        p["lit"] = "true" if lit else "false"
        t.blocks[pos] = (state_str(b, p), nbt)
