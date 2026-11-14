"""Simulador de redstone mínimo para comprobar los mecanismos de la mansión sin abrir el juego.

Cubre lo que usa la estructura: palancas, botones, placas, ganchos de cable trampa, antorchas (de pie y de pared),
polvo en un solo plano, repetidores, pistones (con cuasiconectividad), puertas, dispensadores y dinamita.
Sigue la semántica del código de 26.3: un bloque conductor se alimenta con lo que lo alimenta «directamente»
(polvo incluido, salvo para otro polvo) y un componente se activa si un vecino le da señal.
"""
from core import parse_state

DIRS = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
HOR = ("north", "south", "east", "west")
NONCOND = ("air", "glass", "_pane", "_slab", "_stairs", "fence", "_wall", "door", "trapdoor", "leaves", "torch", "wire",
           "repeater", "lever", "button", "plate", "chest", "lantern", "chain", "carpet", "candle", "cobweb", "piston",
           "spawner", "tripwire", "bars", "skull", "lectern", "cauldron", "brewing", "bed", "campfire", "pot", "vine",
           "glowstone", "jigsaw")
SOURCES = ("lever", "stone_button", "stone_pressure_plate", "tripwire_hook", "redstone_torch", "redstone_wall_torch", "repeater")


def add(p, d):
    x, y, z = p; dx, dy, dz = DIRS[d]
    return (x + dx, y + dy, z + dz)


def name(st):
    return parse_state(st)[0].replace("minecraft:", "") if st else None


def props(st):
    return parse_state(st)[1] if st else {}


def conductor(st):
    n = name(st)
    return n is not None and not any(k in n for k in NONCOND)


class Circuit:
    def __init__(self, blocks):
        """blocks: {pos: estado} (solo hace falta la zona de los mecanismos, pero vale la plantilla entera)."""
        self.b = dict(blocks)
        self.comp = {p: st for p, st in self.b.items() if name(st) in SOURCES + ("redstone_wire",) or
                     name(st) in ("sticky_piston", "piston", "iron_door", "dispenser", "tnt") or
                     (name(st) or "").endswith("_door")}

    # --- geometría
    def support(self, p, st):
        n, pr = name(st), props(st)
        if n in ("redstone_torch",):
            return "down"
        if n in ("redstone_wall_torch", "tripwire_hook"):
            return OPP[pr["facing"]]
        if n in ("lever", "stone_button"):
            return {"floor": "down", "ceiling": "up"}.get(pr["face"], OPP[pr["facing"]])
        if n == "stone_pressure_plate":
            return "down"
        return None

    def wire_shape(self, p):
        """Conexiones del polvo en el plano (como quedarían tras actualizarse)."""
        con = set()
        for d in HOR:
            q = add(p, d)
            st = self.b.get(q)
            n = name(st)
            if n == "redstone_wire" or n in SOURCES[:-1]:
                con.add(d)
            elif n == "repeater" and props(st)["facing"] in (d, OPP[d]):
                con.add(d)
        if len(con) == 1:
            con.add(OPP[next(iter(con))])
        return con

    # --- evaluación
    def solve(self, on=frozenset()):
        """Punto fijo con las fuentes manuales de `on` activadas. Devuelve el estado de cada componente."""
        s = {}
        for p, st in self.comp.items():
            n = name(st)
            if n in ("lever", "stone_button", "stone_pressure_plate", "tripwire_hook"):
                s[p] = p in on
            elif n in ("redstone_torch", "redstone_wall_torch"):
                s[p] = props(st).get("lit") == "true"
            elif n == "repeater":
                s[p] = props(st).get("powered") == "true"
            elif n == "redstone_wire":
                s[p] = int(props(st).get("power", 0))
        shapes = {p: self.wire_shape(p) for p, st in self.comp.items() if name(st) == "redstone_wire"}
        for _ in range(400):
            old = dict(s)
            for p, st in self.comp.items():
                n = name(st)
                if n in ("redstone_torch", "redstone_wall_torch"):
                    sp = add(p, self.support(p, st))
                    s[p] = not self.cond_power(sp, s, shapes, True)
                elif n == "repeater":
                    f = props(st)["facing"]
                    s[p] = self.signal_from(add(p, f), OPP[f], s, shapes)
                elif n == "redstone_wire":
                    best = 0
                    for d in DIRS:
                        q = add(p, d)
                        qst = self.b.get(q)
                        if name(qst) == "redstone_wire":
                            if d in HOR and d in shapes[p]:
                                best = max(best, s[q] - 1)
                        elif conductor(qst):
                            best = max(best, self.cond_power(q, s, shapes, False))
                        else:
                            best = max(best, self.emit(q, OPP[d], s, shapes, wires=False))
                    s[p] = max(0, best)
            if s == old:
                break
        else:
            raise RuntimeError("el circuito no se estabiliza")
        out = {}
        for p, st in self.comp.items():
            n = name(st)
            if n in ("sticky_piston", "piston"):
                f = props(st)["facing"]
                pw = any(self.signal_from(add(p, d), OPP[d], s, shapes) for d in DIRS if d != f)
                up = add(p, "up")
                pw = pw or any(self.signal_from(add(up, d), OPP[d], s, shapes) for d in DIRS if d != "down")
                out[p] = pw
            elif n.endswith("_door"):
                if props(st)["half"] == "lower":
                    out[p] = self.neighbor_signal(p, s, shapes) or self.neighbor_signal(add(p, "up"), s, shapes)
            elif n == "dispenser":
                out[p] = self.neighbor_signal(p, s, shapes) or self.neighbor_signal(add(p, "up"), s, shapes)
            elif n == "tnt":
                out[p] = self.neighbor_signal(p, s, shapes)
            else:
                out[p] = s[p]
        self.shapes = shapes
        return out

    def emit(self, q, d, s, shapes, wires=True):
        """Señal que da el bloque en q hacia la dirección d (hacia q+d)."""
        st = self.b.get(q)
        n = name(st)
        if n is None or q not in s:
            return 0
        if n in ("lever", "stone_button", "stone_pressure_plate", "tripwire_hook"):
            return 15 if s[q] else 0
        if n in ("redstone_torch", "redstone_wall_torch"):
            return 15 if s[q] and d != self.support(q, st) else 0
        if n == "repeater":
            return 15 if s[q] and d == OPP[props(st)["facing"]] else 0
        if n == "redstone_wire" and wires:
            return s[q] if (d == "down" or d in shapes[q]) else 0
        return 0

    def strong_into(self, q, d, s, shapes, wires):
        """Potencia directa que el bloque en q mete en el conductor q+d."""
        st = self.b.get(q)
        n = name(st)
        if n is None or q not in s:
            return 0
        if n in ("lever", "stone_button", "stone_pressure_plate", "tripwire_hook"):
            return 15 if s[q] and d == self.support(q, st) else 0
        if n in ("redstone_torch", "redstone_wall_torch"):
            return 15 if s[q] and d == "up" else 0
        if n == "repeater":
            return 15 if s[q] and d == OPP[props(st)["facing"]] else 0
        if n == "redstone_wire" and wires:
            return s[q] if (d == "down" or d in shapes[q]) else 0
        return 0

    def cond_power(self, c, s, shapes, wires):
        if not conductor(self.b.get(c)):
            return 0
        return max(self.strong_into(add(c, d), OPP[d], s, shapes, wires) for d in DIRS)

    def signal_from(self, q, d, s, shapes):
        """¿Recibe señal el componente en q+d desde q? (d = dirección de q hacia el componente)."""
        if conductor(self.b.get(q)):
            return self.cond_power(q, s, shapes, True) > 0
        return self.emit(q, d, s, shapes) > 0

    def neighbor_signal(self, p, s, shapes):
        return any(self.signal_from(add(p, d), OPP[d], s, shapes) for d in DIRS)

    # --- estados de reposo
    def rest_states(self):
        """Estados de bloque coherentes con el reposo (sin nada pulsado): {pos: estado nuevo}."""
        out = self.solve()
        new = {}
        for p, st in self.comp.items():
            n = name(st)
            pr = props(st)
            if n in ("redstone_torch", "redstone_wall_torch"):
                pr["lit"] = str(out[p]).lower()
            elif n == "repeater":
                pr["powered"] = str(out[p]).lower()
            elif n == "redstone_wire":
                pr["power"] = str(out[p])
                for d in HOR:
                    pr[d] = "side" if d in self.shapes[p] else "none"
            else:
                continue
            new[p] = "minecraft:" + n + "[" + ",".join(f"{k}={v}" for k, v in sorted(pr.items())) + "]"
        return new

    def check_rest(self):
        """Fallos de coherencia del estado guardado con el reposo."""
        out = self.solve()
        errs = []
        for p, st in self.comp.items():
            n, pr = name(st), props(st)
            if n in ("sticky_piston", "piston") and (pr["extended"] == "true") != out[p]:
                errs.append(f"pistón {p} extendido={pr['extended']} con potencia={out[p]}")
            if n.endswith("_door") and pr["half"] == "lower" and ((pr["open"] == "true") != out[p] or (pr["powered"] == "true") != out[p]):
                errs.append(f"puerta {p} abierta={pr['open']} con potencia={out[p]}")
            if n == "dispenser" and (out[p] or pr["triggered"] == "true"):
                errs.append(f"dispensador {p} alimentado en reposo")
            if n == "tnt" and out[p]:
                errs.append(f"dinamita {p} alimentada en reposo")
            if n in ("redstone_torch", "redstone_wall_torch") and (pr["lit"] == "true") != out[p]:
                errs.append(f"antorcha {p} lit={pr['lit']} en reposo {out[p]}")
            if n == "redstone_wire" and int(pr["power"]) != out[p]:
                errs.append(f"polvo {p} potencia {pr['power']} en reposo {out[p]}")
            if n == "repeater" and (pr["powered"] == "true") != out[p]:
                errs.append(f"repetidor {p} powered={pr['powered']} en reposo {out[p]}")
            if n in ("sticky_piston", "piston") and pr["extended"] == "true":
                h = add(p, pr["facing"])
                hs = self.b.get(h)
                if name(hs) != "piston_head" or props(hs)["facing"] != pr["facing"] or \
                        props(hs)["type"] != ("sticky" if n == "sticky_piston" else "normal"):
                    errs.append(f"pistón {p} extendido sin cabeza")
        return errs

    def retract(self, out):
        """Bloques tras recoger los pistones que se quedan sin potencia (los pegajosos tiran del bloque)."""
        b = dict(self.b)
        for p, st in self.comp.items():
            n, pr = name(st), props(st)
            if n in ("sticky_piston", "piston") and pr["extended"] == "true" and not out[p]:
                f = pr["facing"]
                h = add(p, f)
                front = add(h, f)
                b[p] = st.replace("extended=true", "extended=false")
                if n == "sticky_piston" and front in b and conductor(b[front]):
                    b[h] = b.pop(front)
                else:
                    b.pop(h, None)
        return b
