"""Simulador de redstone mínimo (palancas, botones, placas, ganchos, antorchas, polvo y mecanismos) para auditar
los puzles y trampas tal como se colocan. Reglas de 26.3 simplificadas a lo que usa la estructura."""
from core import parse_state

V = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
H = ("north", "south", "east", "west")
MECH = ("piston", "dispenser", "_door", "_trapdoor")
NOCOND = ("air", "redstone_wire", "lever", "button", "pressure_plate", "tripwire", "torch", "piston", "_door",
          "_trapdoor", "_slab", "_stairs", "glass", "iron_bars", "ladder", "sign", "lantern", "water", "cobweb", "_wall")


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def name(st):
    return st.split("[")[0].replace("minecraft:", "") if st else "air"


class Sim:
    def __init__(self, get):
        self.get = get          # (x, y, z) -> estado o None

    def props(self, p):
        st = self.get(p)
        return parse_state(st)[1] if st else {}

    def conductor(self, p):
        n = name(self.get(p))
        return not any(k in n for k in NOCOND)

    def run(self, cells, inputs):
        """cells: posiciones de los componentes. inputs: {pos: True} fuentes activadas. Devuelve el estado estable."""
        self.inputs = inputs
        self.cells = cells
        torches = [p for p in cells if "redstone" in name(self.get(p)) and "torch" in name(self.get(p))]
        self.lit = {p: self.props(p).get("lit") == "true" for p in torches}
        for _ in range(64):
            self.dust = self._dust()
            new = {p: not self.block_powered(self.torch_base(p)) for p in torches}
            if new == self.lit:
                return self
            self.lit = new
        raise RuntimeError("el circuito no se estabiliza")

    # --- fuentes
    def sources(self):
        """[(pos, activa, bloque al que da energía fuerte, direcciones a las que da señal)]"""
        out = []
        for p in self.cells:
            n, pr = name(self.get(p)), self.props(p)
            if n == "lever" or n.endswith("_button"):
                face = pr["face"]
                att = add(p, V["up"] if face == "ceiling" else V["down"] if face == "floor" else
                          tuple(-c for c in V[pr["facing"]]))
                out.append((p, bool(self.inputs.get(p)), att, None))
            elif n.endswith("pressure_plate") or n == "tripwire_hook":
                att = add(p, V["down"]) if "plate" in n else add(p, tuple(-c for c in V[pr["facing"]]))
                out.append((p, bool(self.inputs.get(p)), att, None))
            elif n in ("redstone_torch", "redstone_wall_torch"):
                att = self.torch_base(p)
                out.append((p, self.lit[p], add(p, V["up"]), att))
        return out

    def torch_base(self, p):
        pr = self.props(p)
        return add(p, tuple(-c for c in V[pr["facing"]])) if "facing" in pr else add(p, V["down"])

    def signal_into(self, q):
        """Señal directa de fuentes vecinas hacia q."""
        for (p, on, strong, notdir) in self.sources():
            if on and q != p and sum(abs(a - b) for a, b in zip(p, q)) == 1 and q != notdir:
                return True
        return False

    def strong(self, b):
        return any(on and strong == b for (p, on, strong, nd) in self.sources())

    def _dust(self):
        wires = [p for p in self.cells if name(self.get(p)) == "redstone_wire"]
        pw = {p: 0 for p in wires}
        for p in wires:
            if self.signal_into(p) or any(self.conductor(add(p, V[d])) and self.strong(add(p, V[d])) for d in V):
                pw[p] = 15
        changed = True
        while changed:
            changed = False
            for p in wires:
                for q in self.wire_links(p, wires):
                    if pw[q] - 1 > pw[p]:
                        pw[p] = pw[q] - 1
                        changed = True
        return pw

    def wire_links(self, p, wires):
        out = []
        for d in H:
            q = add(p, V[d])
            if q in wires:
                out.append(q)
            up = add(q, V["up"])
            if up in wires and not self.conductor(add(p, V["up"])):
                out.append(up)
            dn = add(q, V["down"])
            if dn in wires and not self.conductor(q):
                out.append(dn)
        return out

    def dust_points(self, w, q):
        pr = self.props(w)
        if q == add(w, V["down"]):
            return True
        for d in H:
            if add(w, V[d]) == q:
                return pr.get(d) in ("side", "up")
        return False

    def block_powered(self, b):
        if self.strong(b):
            return True
        return any(self.dust.get(w, 0) > 0 and self.dust_points(w, b) for w in self.dust
                   if sum(abs(x - y) for x, y in zip(w, b)) == 1)

    def mech_powered(self, p):
        """Mecanismo (pistón, dispensador, puerta, trampilla) recibe señal."""
        st = self.get(p)
        pts = [p]
        if "_door" in name(st):
            other = add(p, V["up"] if "half=lower" in st else V["down"])
            pts.append(other)
        front = add(p, V[self.props(p)["facing"]]) if "piston" in name(st) else None
        for q0 in pts:
            if self.signal_into(q0):
                return True
            for d in V:
                q = add(q0, V[d])
                if q == front or q in pts:
                    continue
                if self.conductor(q) and self.block_powered(q):
                    return True
                if self.dust.get(q, 0) > 0 and self.dust_points(q, q0):
                    return True
        return False
