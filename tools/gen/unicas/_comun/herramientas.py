"""Herramientas comunes para estructuras únicas (uso: from unicas._comun.herramientas import ...). Complementan a
piezas.py (generador, guardián, cofres, conexiones de vallas y cristales) y a redstone.py.

- Construcción: door, dispenser (con flechas), hang, stair.
- Botín: pool, table, named (con `solo_sin_lootr` en el grupo extra).
- Redstone: simulate (punto fijo con palancas, antorchas de pared, polvo con escalones y puertas de hierro; devuelve
  None en las puertas si el circuito oscila), settle_redstone (escribe el estado de reposo coherente), wire_links.
- Acabado: processors (lista de reglas al azar).
- Auditoría: shifted/walk (recorrido a pie de lint en plantillas con sótano en y < 0).
"""
from collections import deque
from core import Template, B, parse_state, state_str
import lint


def door(t, x, y, z, facing, kind="spruce_door", hinge="left"):
    for h, dy in (("lower", 0), ("upper", 1)):
        t.set(x, y + dy, z, f"{kind}[facing={facing},half={h},hinge={hinge},open=false,powered=false]")


def dispenser(t, x, y, z, facing, n=16, item="minecraft:arrow"):
    t.set(x, y, z, f"dispenser[facing={facing},triggered=false]",
          {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": item, "count": n}]})


def hang(t, x, y, z, kind="lantern"):
    t.set(x, y, z, f"{kind}[hanging=true]")


def stair(kind, facing, half="bottom"):
    return f"{kind}[facing={facing},half={half},shape=straight]"




# ------------------------------------------------------------------ botín
def pool(rolls, entries, extra=False):
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}



def named(e, text):
    """Añade un nombre (componente de texto traducible) a una entrada de botín de loot.item."""
    mods = e.get("modifier", [])
    mods = mods if isinstance(mods, list) else [mods]
    e["modifier"] = mods + [{"type": "minecraft:set_name", "name": text, "target": "item_name"}]
    return e


# ------------------------------------------------------------------ redstone y acabado
SIDES = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0))
HOR = {"east": (1, 0), "west": (-1, 0), "south": (0, 1), "north": (0, -1)}


def _b(st):
    return lint.bname(st)


def wire_links(t, x, y, z):
    """Direcciones en que conecta el polvo: (dirección, dy del vecino) con polvo, antorcha o palanca."""
    out = []
    for name, (dx, dz) in HOR.items():
        n = t.get(x + dx, y, z + dz)
        if n and _b(n) in ("redstone_wire", "redstone_wall_torch", "redstone_torch", "lever"):
            out.append((name, 0))
            continue
        up, above = t.get(x + dx, y + 1, z + dz), t.get(x, y + 1, z)
        if up and _b(up) == "redstone_wire" and (above is None or lint.passable(above)):
            out.append((name, 1))
            continue
        down, side = t.get(x + dx, y - 1, z + dz), t.get(x + dx, y, z + dz)
        if down and _b(down) == "redstone_wire" and (side is None or lint.passable(side)):
            out.append((name, -1))
    return out


def wire_conn(t, x, y, z):
    links = dict(wire_links(t, x, y, z))
    return {n: ("up" if links.get(n) == 1 else "side" if n in links else "none") for n in HOR}


def simulate(t, levers_on):
    """Evalúa el circuito del puzle (y la puerta de pistones) hasta un punto fijo.
    Devuelve (potencia de cada polvo, antorchas encendidas, puertas de hierro alimentadas)."""
    blocks = {p: st for p, (st, _) in t.blocks.items()}
    wires = [p for p, st in blocks.items() if _b(st) == "redstone_wire"]
    torches = {p: st for p, st in blocks.items() if _b(st) == "redstone_wall_torch"}
    levers = {p: st for p, st in blocks.items() if _b(st) == "lever"}
    lit = {p: True for p in torches}
    links = {w: wire_links(t, *w) for w in wires}
    stable = False

    def attached(p, st, opposite=True):
        dx, dz = HOR[parse_state(st)[1]["facing"]]
        return (p[0] - dx, p[1], p[2] - dz)

    power = {}
    for _ in range(40):
        strong = set()
        for p, st in levers.items():
            if p in levers_on:
                strong.add(attached(p, st))
        for p, on in lit.items():
            if on:
                strong.add((p[0], p[1] + 1, p[2]))
        # polvo: fuentes = antorcha encendida vecina (salvo su soporte), palanca activa o bloque fuertemente alimentado
        power = {w: 0 for w in wires}
        q = deque()
        for w in wires:
            src = 0
            for dx, dy, dz in SIDES:
                n = (w[0] + dx, w[1] + dy, w[2] + dz)
                if n in torches and lit[n] and attached(n, torches[n]) != w:
                    src = 15
                if n in levers and n in levers_on:
                    src = 15
                if n in strong and n not in torches and n not in levers and blocks.get(n) and _b(blocks[n]) != "redstone_wire":
                    src = 15
            if src:
                power[w] = src
                q.append(w)
        while q:
            w = q.popleft()
            for name, dy in links[w]:
                dx, dz = HOR[name]
                n = (w[0] + dx, w[1] + dy, w[2] + dz)
                if n in power and power[n] < power[w] - 1:
                    power[n] = power[w] - 1
                    q.append(n)
        # bloques alimentados por el polvo: el de debajo y aquel al que apunta un extremo de línea
        powered = set(strong)
        for w, pw in power.items():
            if pw <= 0:
                continue
            powered.add((w[0], w[1] - 1, w[2]))
            c = [d for d, _ in links[w]]
            if len(c) == 1:
                dx, dz = HOR[c[0]]
                powered.add((w[0] - dx, w[1], w[2] - dz))
        new = {p: attached(p, st) not in powered for p, st in torches.items()}
        if new == lit:
            stable = True
            break
        lit = new
    if not stable:                         # el circuito oscila: un reloj fundiría las antorchas
        return power, lit, None
    doors = {}
    for p, st in blocks.items():
        if _b(st) == "iron_door" and "half=lower" in st:
            on = False
            for hp in (p, (p[0], p[1] + 1, p[2])):
                for dx, dy, dz in SIDES:
                    n = (hp[0] + dx, hp[1] + dy, hp[2] + dz)
                    if n in torches and lit[n] and attached(n, torches[n]) != hp:
                        on = True
                    if n in powered and blocks.get(n) and not lint.passable(blocks[n]):
                        on = True
            doors[p] = on
    return power, lit, doors


def settle_redstone(t):
    """Escribe en el polvo y las antorchas el estado de reposo que da la simulación (todo coherente al colocarse)."""
    power, lit, _ = simulate(t, set())
    for p, pw in power.items():
        c = wire_conn(t, *p)
        t.set(*p, state_str("minecraft:redstone_wire", dict(c, power=str(pw))))
    for p, on in lit.items():
        bid, props = parse_state(t.get(*p))
        props["lit"] = "true" if on else "false"
        t.set(*p, state_str(bid, props))


def processors(rules):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": [
        {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + a, "probability": p},
         "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + b}
        for a, b, p in rules]}]}



# ------------------------------------------------------------------ auditoría
DY = 20     # desplazamiento vertical para el recorrido a pie: lint.walk toma y < 0 como suelo natural


def shifted(t):
    s = Template(t.name)
    s.blocks = {(x, y + DY, z): v for (x, y, z), v in t.blocks.items()}
    s.jigsaws = [dict(j, pos=(j["pos"][0], j["pos"][1] + DY, j["pos"][2])) for j in t.jigsaws]
    return s


def walk(t):
    return {(x, y - DY, z) for (x, y, z) in lint.walk(shifted(t))}


