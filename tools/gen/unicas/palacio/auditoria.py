"""Comprobaciones propias del palacio (además de lint.py): redstone, puzles, recorrido, apoyos y ruina.

Cada función devuelve una lista de textos de error; build() los vuelca en reg.warnings, de modo que la
generación falla si alguna no pasa."""
from collections import deque
from core import parse_state
import lint
from lint import bname, passable, solid_full
from .ruinas import wear_probability

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
VEC = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1), "up": (0, 1, 0), "down": (0, -1, 0)}
NOT_CONDUCTOR = ("piston", "dispenser_never", "glass", "leaves", "slab", "stairs", "wall", "fence", "lantern", "chest")


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def conductor(st):
    if st is None:
        return False
    b = bname(st)
    return solid_full(st) and not any(k in b for k in NOT_CONDUCTOR) and not passable(st)


class Red:
    """Modelo mínimo de redstone vanilla para fuentes sin polvo: palancas, ganchos de cable, placas y cofres trampa.
    Una fuente activa da energía a sus vecinos y energía fuerte a su bloque de apoyo; un bloque conductor con
    energía fuerte activa a los componentes vecinos. Pistones y dispensadores se activan también por
    cuasiconectividad (vecinos de la celda de encima)."""

    def __init__(self, t, active):
        self.t, self.active = t, set(active)        # posiciones de fuentes activas
        self.strong = set()
        for p in self.active:
            st = t.get(*p)
            b = bname(st)
            if b == "lever" or b.endswith("_button"):
                self.strong.add(add(p, tuple(-c for c in VEC[parse_state(st)[1]["facing"]])))
            elif b == "tripwire_hook":
                self.strong.add(add(p, tuple(-c for c in VEC[parse_state(st)[1]["facing"]])))
            elif "pressure_plate" in b or b == "trapped_chest":
                self.strong.add(add(p, (0, -1, 0)))
        self.strong = {p for p in self.strong if conductor(t.get(*p))}

    def signal_from(self, n):
        return n in self.active or n in self.strong

    def powered(self, c, qc=True, exclude=None):
        for d in DIRS6:
            n = add(c, d)
            if n != exclude and self.signal_from(n):
                return True
        if qc:
            up = add(c, (0, 1, 0))
            for d in DIRS6:
                n = add(up, d)
                if n != c and self.signal_from(n):
                    return True
        return False


def sources(t, mech, override=None):
    """Fuentes activas en el estado colocado; override = {pos: True/False} para simular al jugador."""
    act = set()
    for m in mech:
        if m["kind"] == "palanca" and m["powered"]:
            act.add(m["pos"])
    for p, v in (override or {}).items():
        (act.add if v else act.discard)(p)
    return act


def comp_powered(t, red, p):
    st = t.get(*p)
    b = bname(st)
    if "piston" in b and "head" not in b:
        f = parse_state(st)[1]["facing"]
        return red.powered(p, qc=True, exclude=add(p, VEC[f]))
    return red.powered(p, qc=b == "dispenser")


def check_redstone(o):
    t, errs = o.t, []
    mech = o.mech
    levers = {m["label"]: m for m in mech if m["kind"] == "palanca"}
    # estado colocado: todo componente coherente con su energía (nada cambia sin una actualización)
    red0 = Red(t, sources(t, mech))
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in ("sticky_piston", "piston"):
            ext = parse_state(st)[1]["extended"] == "true"
            if ext != comp_powered(t, red0, p):
                errs.append(f"pistón {p} colocado {'extendido' if ext else 'recogido'} con energía contraria")
        elif b == "dispenser":
            trig = parse_state(st)[1]["triggered"] == "true"
            if trig != comp_powered(t, red0, p):
                errs.append(f"dispensador {p} con triggered incoherente")
    for m in mech:
        if m["kind"] == "palanca":
            st = t.get(*m["pos"])
            back = add(m["pos"], tuple(-c for c in VEC[m["facing"]]))
            if bname(st) != "lever" or not conductor(t.get(*back)):
                errs.append(f"palanca {m['label']} {m['pos']} sin bloque conductor detrás")
            if not passable(t.get(*add(m["pos"], (0, 0, 0)))):
                errs.append(f"palanca {m['label']} no es atravesable")
        elif m["kind"] == "puerta":
            f = VEC[m["facing"]]
            for p in m["pistons"]:
                if t.get(*add(p, f)) != f"minecraft:piston_head[facing={m['facing']},short=false,type=sticky]":
                    errs.append(f"puerta {m['label']}: falta la cabeza del pistón {p}")
            for d in m["door"]:
                if not conductor(t.get(*d)) and not solid_full(t.get(*d)):
                    errs.append(f"puerta {m['label']}: bloque de puerta {d} no macizo")
    # puertas: abiertas solo con sus palancas apagadas
    groups = {}
    for m in mech:
        if m["kind"] == "puerta":
            groups.setdefault(m["label"].split(" ")[0], []).append(m)
    for g, ms in groups.items():
        own = [lv for name, lv in levers.items() if name.split(" ")[0] == g]
        if not own:
            errs.append(f"puerta {g} sin palanca")
            continue
        red = Red(t, sources(t, mech, {lv["pos"]: False for lv in own}))
        for m in ms:
            for p in m["pistons"]:
                if comp_powered(t, red, p):
                    errs.append(f"puerta {g}: el pistón {p} sigue con energía con las palancas apagadas")
        if len(own) > 1:
            for lv in own:
                red = Red(t, sources(t, mech, {lv["pos"]: False}))
                if not any(comp_powered(t, red, p) for m in ms for p in m["pistons"]):
                    errs.append(f"puerta {g}: se abre entera con una sola palanca ({lv['label']})")
        # cada pistón empuja su bloque al sitio de la cabeza: hueco libre al abrir
        for m in ms:
            for d in m["door"]:
                if o.lint_open.get(d) != "air":
                    errs.append(f"puerta {g}: el hueco {d} no queda libre al abrir")
    # trampas
    for m in mech:
        if m["kind"] == "cable":
            z, x0, x1, y = m["z"], m["x0"], m["x1"], m["y"]
            hooks = [(x0 + 1, y, z), (x1 - 1, y, z)]
            red = Red(t, hooks)
            for d, fc in (((x0, y + 1, z), "east"), ((x1, y + 1, z), "west")):
                st = t.get(*d)
                if bname(st) != "dispenser" or parse_state(st)[1]["facing"] != fc or not comp_powered(t, red, d):
                    errs.append(f"cable {m['label']}: el dispensador {d} no se activa")
                if not passable(t.get(*add(d, VEC[fc]))):
                    errs.append(f"cable {m['label']}: el dispensador {d} dispara contra un muro")
            for x in range(x0 + 2, x1 - 1):
                if bname(t.get(x, y, z)) != "tripwire":
                    errs.append(f"cable {m['label']}: falta el hilo en {(x, y, z)}")
            for h in hooks:
                f = parse_state(t.get(*h))[1]["facing"]
                if not conductor(t.get(*add(h, tuple(-c for c in VEC[f])))):
                    errs.append(f"cable {m['label']}: gancho {h} sin muro conductor")
        elif m["kind"] == "placa":
            red = Red(t, [m["plate"]])
            for d in m["disp"]:
                st = t.get(*d)
                f = parse_state(st)[1]["facing"]
                if add(d, VEC[f]) != m["plate"] or not comp_powered(t, red, d):
                    errs.append(f"placa {m['label']}: el dispensador {d} no dispara sobre la placa")
        elif m["kind"] == "senuelo":
            red = Red(t, sources(t, mech, {m["lever"]: True}))
            if not comp_powered(t, red, m["disp"]):
                errs.append("palanca señuelo sin efecto")
            for g in groups.values():
                for mm in g:
                    for p in mm["pistons"]:
                        if comp_powered(t, Red(t, sources(t, mech, {m["lever"]: True, **{lv['pos']: False for lv in levers.values()}})), p):
                            errs.append("la palanca señuelo alimenta una puerta")
    for p, st in o.lint_open.items():
        if p not in t.blocks:
            errs.append(f"estado abierto fuera de la pieza {p}")
    return errs


def near(cells, p, r=1):
    x, y, z = p
    return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
               for dy in (-1, 0, 1) if abs(dx) + abs(dz) <= r)


class Closed:
    """Vista de la plantilla sin los mecanismos abiertos (todo cerrado, como se genera)."""
    def __init__(self, t):
        self.__dict__.update(t.__dict__)
        self.lint_open = {}
        self.get = t.get
        self.bounds = t.bounds


def check_walk(o):
    t, errs = o.t, []
    opened = set(lint.walk(t))
    closed = set(lint.walk(Closed(t)))
    for p in o.secret:
        if near(closed, p):
            errs.append(f"{p} se alcanza sin resolver ningún puzle")
        if not near(opened, p):
            errs.append(f"{p} no se alcanza ni con los puzles resueltos")
    for (p, tabla) in o.chests:
        if not near(opened, p):
            errs.append(f"cofre {tabla} {p} inaccesible")
    for m in o.mech:
        if m["kind"] == "palanca" and not near(opened, m["pos"]):
            errs.append(f"palanca {m['label']} inaccesible")
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in ("trapped_chest", "stone_button", "loom", "smoker") and not near(opened, p):
            errs.append(f"{b} {p} inaccesible")
    if not near(opened, o.guardian, r=0):
        errs.append("el guardián no está en una celda alcanzable")
    return errs, opened


def check_floating(o):
    """Nada flotando: todo bloque (agua incluida) unido por caras al zócalo y = 0."""
    t = o.t
    solid = {p for p, (st, _) in t.blocks.items() if bname(st) not in ("air", "structure_void")}
    seen = {p for p in solid if p[1] == 0}
    q = deque(seen)
    while q:
        p = q.popleft()
        for d in DIRS6:
            n = add(p, d)
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    loose = sorted(solid - seen)
    return [f"{len(loose)} bloques flotando, p. ej. {loose[:5]} ({t.get(*loose[0])})"] if loose else []


def exposed(t, keys):
    out = set()
    for p in keys:
        st = t.get(*p)
        if st is None or bname(st) == "air":
            continue
        for d in DIRS6:
            n = t.get(*add(p, d))
            if n is None or passable(n) or bname(n) == "air":
                if add(p, d)[1] >= 0:
                    out.add(p)
                    break
    return out


def ruin_ratio(good, ruined):
    """Fracción de la superficie expuesta en ruina: bloques quitados o cambiados por la ruina, más el
    desgaste esperado del procesador sobre lo que queda."""
    exp_good = exposed(good, good.blocks)
    changed = sum(1 for p in exp_good if ruined.get(*p) != good.get(*p))
    # escombro, hiedra y musgo añadidos: cada uno tapa una cara de la superficie
    added = sum(1 for p, (st, _) in ruined.blocks.items() if bname(st) not in ("air", "jigsaw", "iron_chain")
                and good.get(*p) in (None, "minecraft:air"))
    wear = sum(wear_probability(ruined.get(*p)) for p in exp_good if ruined.get(*p) == good.get(*p))
    return (changed + added + wear) / max(1, len(exp_good)), len(exp_good), changed + added, wear


def check_ruin(good, ruined):
    r, n, c, w = ruin_ratio(good, ruined)
    if not 0.15 <= r <= 0.20:
        return [f"ruina {r:.1%} fuera de 15-20 % (superficie {n}, quitado/cambiado {c}, desgaste {w:.0f})"]
    return []
