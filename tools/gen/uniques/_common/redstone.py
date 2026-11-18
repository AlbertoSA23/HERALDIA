"""Common redstone: wire shape and static evaluation of the signal with the game rules (use: from uniques._common import redstone).

During generation there are no block updates: what is placed must already be a stable state. This module computes
what the game would compute (connections of each wire, power, torches, pistons, doors, dispensers, TNT)
and allows simulating inputs (levers, hooks, plates) to check the puzzles and traps.
"""
from core import parse_state, state_str

H4 = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
D6 = dict(H4, up=(0, 1, 0), down=(0, -1, 0))
OPP = {"north": "south", "south": "north", "west": "east", "east": "west", "up": "down", "down": "up"}
NON_CONDUCTOR = ("air", "glass", "slab", "stairs", "fence", "_wall", "bars", "pane", "torch", "lever", "rail", "carpet",
                 "door", "lantern", "chain", "banner", "redstone_wire", "tripwire", "ladder", "bed", "campfire",
                 "cauldron", "anvil", "grindstone", "brewing_stand", "lectern", "plate", "piston", "spawner", "lava",
                 "water", "cobweb", "chest", "barrel", "dispenser", "tnt", "leaves", "pot", "button", "repeater")


def bn(s):
    return s.split("[")[0].replace("minecraft:", "") if s else ""


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def conductor(s):
    b = bn(s)
    return bool(b) and not any(k in b for k in NON_CONDUCTOR)


def attached_dir(s):
    """Direction (from the component) of the block it is attached to."""
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
    if b == "repeater":                      # only along its axis
        return parse_state(s)[1]["facing"] in (d_from_wire, OPP[d_from_wire])
    return b in ("redstone_torch", "redstone_wall_torch", "lever", "tripwire_hook", "redstone_block", "detector_rail") \
        or b.endswith("pressure_plate") or b.endswith("_button")


def wire_links(get, pos):
    """Neighboring wires of a wire: {direction: position}, including those that go up or down one block."""
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
    """Connections that the game computes for a wire (also those that go up or down one step)."""
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
    """Static evaluation: fixed inputs (levers, hooks, plates) and fixed point of wires and torches."""

    def __init__(self, t, inputs=None):
        self.get0 = t.get
        self.blocks = t.blocks
        self.inputs = inputs or {}            # pos -> powered (bool) for levers, hooks, plates and detector rails
        self.torch = {}
        self.rep = {}                         # repetidores: pos -> encendido
        self.wire = {}
        self.conn = {}
        self.links = {}
        for pos, (s, _) in t.blocks.items():
            b = bn(s)
            if b in ("redstone_torch", "redstone_wall_torch"):
                self.torch[pos] = True
            elif b == "repeater":
                self.rep[pos] = False
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
        if b in ("lever", "tripwire_hook", "detector_rail") or b.endswith("pressure_plate") or b.endswith("_button"):
            return parse_state(s)[1].get("powered") == "true"
        return False

    def rep_out(self, n):
        """Cell that a repeater outputs to (the side opposite `facing`, which faces its input)."""
        return add(n, D6[OPP[parse_state(self.get(*n))[1]["facing"]]])

    def direct(self, n, target, wires=True):
        """Strong signal that the component at n gives to the block target."""
        s = self.get(*n)
        b = bn(s)
        if b in ("lever", "tripwire_hook") or b.endswith("_button"):
            return 15 if self.src_on(n) and add(n, D6[attached_dir(s)]) == target else 0
        if b == "repeater":
            return 15 if self.rep[n] and self.rep_out(n) == target else 0
        if b.endswith("pressure_plate") or b == "detector_rail":     # the detector rail, like a plate
            return 15 if self.src_on(n) and target == add(n, D6["down"]) else 0
        if b in ("redstone_torch", "redstone_wall_torch"):
            return 15 if self.torch[n] and target == add(n, D6["up"]) else 0
        if b == "redstone_wire":
            return self.weak(n, target) if wires else 0
        return 0

    def weak(self, n, target, wires=True):
        """Signal that n gives to the neighboring position target (what a component at target reads)."""

        s = self.get(*n)
        b = bn(s)
        if b in ("lever", "tripwire_hook", "detector_rail") or b.endswith("pressure_plate") or b.endswith("_button"):
            return 15 if self.src_on(n) else 0
        if b == "repeater":
            return 15 if self.rep[n] and self.rep_out(n) == target else 0
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
            for pos in self.rep:
                f = parse_state(self.get(*pos))[1]["facing"]
                on = self.weak(add(pos, D6[f]), pos) > 0
                if on != self.rep[pos]:
                    self.rep[pos] = on
                    changed = True
            # wire power: non-wire sources and wire neighbors - 1
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
        raise ValueError("the circuit oscillates")

    def powered(self, pos):
        """Does a component (piston, door, dispenser, TNT) at pos receive a signal?"""
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
    """The placed state matches what the game would compute (nothing waits for an update)."""
    errs = []
    sim = Sim(t)
    for pos, (s, _) in t.blocks.items():
        b, p = parse_state(s)
        b = bn(b)
        if b == "redstone_wire":
            exp = sim.conn[pos]
            for d in H4:
                if (p.get(d) != "none") != exp[d]:
                    errs.append(f"wire with a shape different from the computed one at {pos}")
            if int(p.get("power", 0)) != sim.wire[pos]:
                errs.append(f"wire with power {p.get('power')} that should have {sim.wire[pos]} at {pos}")
        elif b == "repeater":
            if (p["powered"] == "true") != sim.rep[pos]:
                errs.append(f"repetidor inestable en {pos}")
        elif b in ("redstone_torch", "redstone_wall_torch"):
            if (p["lit"] == "true") != sim.torch[pos]:
                errs.append(f"antorcha de redstone inestable en {pos}")
        elif b in ("piston", "sticky_piston"):
            if (p["extended"] == "true") != sim.powered(pos):
                errs.append(f"unstable piston at {pos}")
            if p["extended"] == "true":
                head = t.get(*add(pos, D6[p["facing"]]))
                if bn(head) != "piston_head":
                    errs.append(f"extended piston without a head at {pos}")
        elif b.endswith("_door") and b.startswith("iron"):
            if (p["open"] == "true") != sim.powered(pos) or (p["powered"] == "true") != sim.powered(pos):
                errs.append(f"puerta de hierro inestable en {pos}")
        elif b == "dispenser" and sim.powered(pos) != (p["triggered"] == "true"):
            errs.append(f"dispensador inestable en {pos}")
        elif b == "redstone_lamp" and (p["lit"] == "true") != sim.powered(pos):
            errs.append(f"unstable lamp at {pos}")
        elif b == "tnt" and sim.powered(pos):
            errs.append(f"TNT with a signal when placed at {pos}")
        elif b in ("lever", "tripwire_hook", "redstone_wall_torch"):
            a = t.get(*add(pos, D6[attached_dir(s)]))
            if not conductor(a):
                errs.append(f"{b} without a solid block behind it at {pos}")
    return errs, sim


def set_wire_power(t):
    sim = Sim(t)
    for pos, pw in sim.wire.items():
        s, nbt = t.blocks[pos]
        _, p = parse_state(s)
        p["power"] = str(pw)
        t.blocks[pos] = (state_str("minecraft:redstone_wire", p), nbt)


def check_puzzle(t, name, levers, solution, output, opens_if="con_potencia"):
    """Tests all the combinations of a puzzle's levers: only the solution must open it.
    salida: components (piston, door...) that the puzzle moves; abre_si: "con_potencia" (door that opens with
    a signal) or "sin_potencia" (pistons that hold the wall while they receive a signal)."""
    import itertools
    errs = []
    for combo in itertools.product((False, True), repeat=len(levers)):
        sim = Sim(t, dict(zip(levers, combo)))
        on = [sim.powered(p) for p in output]
        opens = all(on) if opens_if == "con_potencia" else not any(on)
        if opens != (tuple(combo) == tuple(solution)):
            errs.append(f"puzle {name}: con palancas {combo} {'abre' if opens else 'no abre'}")
    return errs


def set_torches(t):
    """Sets the lit state of each redstone torch to the stable one (after set_wire_power)."""
    sim = Sim(t)
    for pos, lit in sim.torch.items():
        s, nbt = t.blocks[pos]
        b, p = parse_state(s)
        p["lit"] = "true" if lit else "false"
        t.blocks[pos] = (state_str(b, p), nbt)


def set_repeaters(t):
    """Sets the powered state of each repeater to the stable one."""
    sim = Sim(t)
    for pos, on in sim.rep.items():
        s, nbt = t.blocks[pos]
        b, p = parse_state(s)
        p["powered"] = "true" if on else "false"
        t.blocks[pos] = (state_str(b, p), nbt)


def retract(t, sim):
    """Blocks (pos -> state) after retracting the extended pistons that `sim` leaves without a signal; sticky ones pull the
    block they hold (to check on foot that a piston door ends up open)."""
    b = {p: s for p, (s, _) in t.blocks.items()}
    for pos, s in list(b.items()):
        n, p = parse_state(s)
        n = bn(n)
        if n in ("piston", "sticky_piston") and p.get("extended") == "true" and not sim.powered(pos):
            head = add(pos, D6[p["facing"]])
            front = add(head, D6[p["facing"]])
            p["extended"] = "false"
            b[pos] = state_str("minecraft:" + n, p)
            if n == "sticky_piston" and front in b and conductor(b[front]):
                b[head] = b.pop(front)
            else:
                b.pop(head, None)
    return b
