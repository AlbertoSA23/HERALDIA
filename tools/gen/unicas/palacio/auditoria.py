"""Comprobaciones propias del palacio (además de lint.py): redstone, puzles, recorrido, apoyos y ruina.

Cada función devuelve una lista de textos de error; build() los vuelca en reg.warnings, de modo que la
generación falla si alguna no pasa."""
from collections import deque
from core import parse_state
import lint
from lint import bname, passable
from .ruinas import wear_probability
from .._comun import redstone

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
VEC = {"east": (1, 0, 0), "west": (-1, 0, 0), "south": (0, 0, 1), "north": (0, 0, -1), "up": (0, 1, 0), "down": (0, -1, 0)}


def check_redstone(o):
    """Con el modelo común (_comun.redstone): estado colocado estable y efecto de cada palanca, cable y placa."""
    t, errs = o.t, list(redstone.check_static(o.t)[0])
    mech = o.mech
    levers = {m["label"]: m for m in mech if m["kind"] == "palanca"}
    groups = {}
    for m in mech:
        if m["kind"] == "puerta":
            groups.setdefault(m["label"].split(" ")[0], []).append(m)
    pistons = lambda ms: [p for m in ms for p in m["pistons"]]
    for g, ms in groups.items():
        own = [lv["pos"] for name, lv in levers.items() if name.split(" ")[0] == g]
        if not own:
            errs.append(f"puerta {g} sin palanca")
            continue
        sim = redstone.Sim(t, {p: False for p in own})
        errs += [f"puerta {g}: el pistón {p} sigue con energía con las palancas apagadas" for p in pistons(ms) if sim.powered(p)]
        if len(own) > 1:
            for lv in own:
                if not any(redstone.Sim(t, {lv: False}).powered(p) for p in pistons(ms)):
                    errs.append(f"puerta {g}: se abre entera con una sola palanca {lv}")
        errs += [f"puerta {g}: el hueco {d} no queda libre al abrir" for m in ms for d in m["door"] if o.lint_open.get(d) != "air"]
    for m in mech:
        if m["kind"] == "cable":
            z, x0, x1, y = m["z"], m["x0"], m["x1"], m["y"]
            sim = redstone.Sim(t, {(x0 + 1, y, z): True, (x1 - 1, y, z): True})
            for d in ((x0, y + 1, z), (x1, y + 1, z)):
                if bname(t.get(*d)) != "dispenser" or not sim.powered(d):
                    errs.append(f"cable {m['label']}: el dispensador {d} no se activa")
        elif m["kind"] == "placa":
            sim = redstone.Sim(t, {m["plate"]: True})
            errs += [f"placa {m['label']}: el dispensador {d} no se activa" for d in m["disp"]
                     if bname(t.get(*d)) != "dispenser" or not sim.powered(d)]
        elif m["kind"] == "senuelo":
            sim = redstone.Sim(t, {m["lever"]: True, **{lv["pos"]: False for lv in levers.values() if lv["pos"] != m["lever"]}})
            if not sim.powered(m["disp"]):
                errs.append("palanca señuelo sin efecto")
            if any(sim.powered(p) for ms in groups.values() for p in pistons(ms)):
                errs.append("la palanca señuelo alimenta una puerta")
    # cada dispensador de trampa dispara hacia una celda libre
    for p, (st, _) in t.blocks.items():
        if bname(st) == "dispenser":
            f = parse_state(st)[1]["facing"]
            q = (p[0] + VEC[f][0], p[1] + VEC[f][1], p[2] + VEC[f][2])
            if not passable(t.get(*q)) and bname(t.get(*q)) != "stone_pressure_plate":
                errs.append(f"dispensador {p} dispara contra un muro")
    return errs


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


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
