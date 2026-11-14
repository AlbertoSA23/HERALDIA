"""Comprobaciones propias del faro: redstone de puzles y trampas, cueva estanca, ruina y recorrido a pie.

`run(t)` devuelve la lista de errores (el generador falla si no está vacía).
`python3 -m unicas.faro.checks <carpeta>` (desde tools/gen) escribe planos de planta y renders en <carpeta>.
"""
import itertools
from core import parse_state, state_str
from lint import walk, bname

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


def settle(t):
    """Escribe en la plantilla el estado de reposo del circuito (antorchas y potencia del polvo)."""
    from unicas.faro.plano import LEVERS, REST
    torches, power, _ = simulate(t, {LEVERS[k]: REST[k] for k in LEVERS})
    for p, lit in torches.items():
        st = t.get(*p)
        b, pr = parse_state(st)
        pr["lit"] = str(lit).lower()
        t.set(*p, state_str(b, pr))
    for p, pw in power.items():
        b, pr = parse_state(t.get(*p))
        pr["power"] = str(pw)
        t.set(*p, state_str(b, pr))


def redstone_issues(t):
    from unicas.faro.plano import LEVERS, REST, VAULT_DOOR
    out = []
    g = lambda p: t.get(*p)
    lev = {LEVERS[k]: REST[k] for k in LEVERS}
    for p, on in lev.items():
        if props(g(p))["powered"] != str(on).lower():
            out.append(f"palanca {p} no está en su posición de reposo")
    torches, power, fed = simulate(t, lev)
    for p, lit in torches.items():
        if props(g(p))["lit"] != str(lit).lower():
            out.append(f"antorcha {p} colocada en un estado que no es el estable")
    for p, pw in power.items():
        if props(g(p))["power"] != str(pw):
            out.append(f"polvo {p} con potencia {props(g(p))['power']}, estable {pw}")
    up = add(VAULT_DOOR, DIR["up"])
    for door_pos in (VAULT_DOOR, up):
        if "open=false" not in g(door_pos) or "powered=false" not in g(door_pos):
            out.append("la puerta de la cámara no está cerrada y sin alimentar en reposo")
    if fed(VAULT_DOOR) or fed(up):
        out.append("la puerta de la cámara recibe señal en reposo")
    good = {"A": False, "B": True, "C": False}
    for combo in itertools.product((False, True), repeat=3):
        cfg = dict(zip("ABC", combo))
        _, _, fed = simulate(t, {LEVERS[k]: cfg[k] for k in cfg})
        opens = fed(VAULT_DOOR) or fed(up)
        if opens != (cfg == good):
            out.append(f"puzle del despacho: con {cfg} la puerta {'abre' if opens else 'no abre'}")
    # puzle 1: trampilla del sótano
    hatch, lever = (15, 16, 16), (16, 17, 16)
    for on in (False, True):
        _, _, fed = simulate(t, {lever: on})
        if fed(hatch) != on:
            out.append(f"puzle del sótano: con la palanca {'subida' if on else 'bajada'} la trampilla no responde")
    if "open=false" not in g(hatch) or "powered=false" not in g(lever):
        out.append("el puzle del sótano no está cerrado en reposo")
    # trampa 1: ganchos enfrentados, cable tenso y un dispensador con flechas encima de cada gancho
    for hook, face in (((14, 9, 19), "east"), ((16, 9, 19), "west")):
        st = g(hook)
        if bname(st) != "tripwire_hook" or props(st)["facing"] != face or props(st)["attached"] != "true":
            out.append(f"gancho {hook} mal colocado")
        if not conductor(g(add(hook, tuple(-c for c in DIR[face])))):
            out.append(f"gancho {hook} sin bloque detrás")
        disp = add(hook, DIR["up"])
        st, nbt = t.blocks.get(disp, (None, None))
        if bname(st) != "dispenser" or props(st)["facing"] != face or not (nbt and nbt.get("Items")):
            out.append(f"dispensador {disp} mal colocado o vacío")
    wire = g((15, 9, 19))
    if bname(wire) != "tripwire" or "attached=true" not in wire or "east=true" not in wire or "west=true" not in wire:
        out.append("cable trampa sin tensar")
    # trampa 2: placa sobre un bloque conductor con TNT debajo
    plate = (37, 9, 39)
    if bname(g(plate)) != "stone_pressure_plate" or not conductor(g(add(plate, DIR["down"]))) \
            or bname(g(add(plate, DIR["down"], 2))) != "tnt":
        out.append("trampa de TNT mal montada")
    return out


def sealing_issues(t):
    """Ninguna celda de aire bajo la cima toca el vacío (terreno natural) salvo en la boca de la cueva."""
    from unicas.faro.plano import TOP
    out = []
    for (x, y, z), (st, _) in t.blocks.items():
        if y >= TOP or bname(st) not in ("air", "water") or (19 <= x <= 25 and z >= 41):
            continue
        if bname(st) == "water" and z > 40:
            continue
        for v in D6:
            if add((x, y, z), v) not in t.blocks:
                out.append(f"la cueva se abre al exterior en {(x, y, z)}")
                break
    return out[:5]


NATURAL = ("stone", "andesite", "tuff", "diorite", "dirt", "grass_block", "gravel", "water", "air")
RUIN_PROB = {"stone_bricks": 0.22, "cobblestone": 0.25, "white_terracotta": 0.22, "red_terracotta": 0.20,
             "spruce_planks": 0.15, "glass_pane": 0.10}
RUIN_SPOTS = 2 + 4 + 3 + 2 + 2 + 8 + 2 + 6   # cristales, tejado, barandilla, galería, pasillo, derrumbe, barrotes, telarañas


def ruin_share(t):
    """Parte estimada de la superficie construida visible con detalles de ruina."""
    vis, alt = 0, 0.0
    for p, (st, _) in t.blocks.items():
        b = bname(st)
        if b in NATURAL or any(w in b for w in ("lantern", "torch", "chain", "wire", "lever", "sign", "candle")):
            continue
        if any(t.get(*add(p, v)) in (None, "minecraft:air") for v in D6):
            vis += 1
            alt += RUIN_PROB.get(b, 0.0)
    return (alt + RUIN_SPOTS) / (vis + RUIN_SPOTS)


def access_points(t):
    """Celdas que el jugador tiene que alcanzar (con los puzles resueltos)."""
    from unicas.faro.plano import LEVERS
    pts = {"palanca del sótano": (16, 17, 16), "cofre premium": (18, 10, 4), "boca de la cueva": (22, 9, 40)}
    pts.update({f"palanca {k}": p for k, p in LEVERS.items()})
    return pts


def run(t):
    out = redstone_issues(t) + sealing_issues(t)
    share = ruin_share(t)
    if not 0.15 <= share <= 0.20:
        out.append(f"superficie en ruina estimada {share:.0%}, fuera del 15-20 %")
    cells = walk(t)
    for name, (x, y, z) in access_points(t).items():
        if not any((x + dx, y + dy, z + dz) in cells for dx, dy, dz in itertools.product((-1, 0, 1), (-1, 0, 1), (-1, 0, 1))):
            out.append(f"{name} {(x, y, z)} no se alcanza a pie")
    return out


# ------------------------------------------------------------------ planos y renders
SYMBOL = {"chest": "C", "barrel": "b", "spawner": "S", "ladder": "H", "lever": "P", "tnt": "T", "tripwire": "t",
          "dispenser": "d", "lectern": "A", "iron_trapdoor": "=", "bookshelf": "L"}


def plans(t, out_dir):
    import os
    from unicas.faro.plano import X, Z
    from render import render
    os.makedirs(out_dir, exist_ok=True)
    cells = walk(t)
    levels = ((9, "cueva (nivel del mar)"), (17, "sótano"), (22, "cima: casa y base del faro"),
              (39, "sala de guardia"), (44, "linterna y galería"))
    lines = ["Planos de planta del faro. Norte arriba (z=0, entrada); el mar al sur.",
             "· alcanzable a pie (con los puzles resueltos)  # muro/roca  ~ agua  D puerta  C cofre  b barril",
             "S generador  H escalera de mano  P palanca  = trampilla  T TNT  t cable trampa  d dispensador",
             "A atril  L estantería  / peldaño", ""]
    for y, title in levels:
        lines.append(f"== y={y}: {title}")
        for z in range(Z):
            row = ""
            for x in range(X):
                st = t.get(x, y, z)
                b = bname(st) if st else None
                ch = next((c for k, c in SYMBOL.items() if b == k), None)
                if ch is None and b and b.endswith("_door"):
                    ch = "D"
                if ch is None and b and b.endswith("_stairs"):
                    ch = "/"
                if ch is None:
                    if b == "water" or bname(t.get(x, y - 1, z) or "") == "water" and b in (None, "air"):
                        ch = "~"
                    elif (x, y, z) in cells:
                        ch = "·"
                    elif b and b != "air" and conductor(st) or b in ("glass_pane", "iron_bars", "spruce_fence"):
                        ch = "#"
                    else:
                        ch = " "
                row += ch
            lines.append(row.rstrip())
        lines.append("")
    with open(os.path.join(out_dir, "planos.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    render(t, os.path.join(out_dir, "exterior.png"), scale=3)

    class Cut:
        pass
    cut = Cut()
    cut.blocks = {p: v for p, v in t.blocks.items() if p[1] <= 13 and not (p[1] >= 9 and p[2] >= 40)}
    render(cut, os.path.join(out_dir, "cueva.png"), scale=3)


if __name__ == "__main__":
    import sys
    from unicas.faro.plano import make
    t = make()
    print("\n".join(run(t)) or "sin errores", f"ruina {ruin_share(t):.1%}")
    plans(t, sys.argv[1])
