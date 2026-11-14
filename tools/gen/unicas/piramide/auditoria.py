"""Auditoría propia del Templo-pirámide (sobre la obra completa, superficie y subsuelo juntos).

Recorrido a pie desde la plaza hasta cada cofre, generador, palanca, trampa y sala oculta; la puerta secreta
cierra de verdad la cámara del tesoro; el foso tiene salida; nada flota; el agua está encerrada; los circuitos
están en reposo coherente; y la fracción de superficie exterior en buen estado queda entre 0,80 y 0,85.
"""
from collections import deque
from core import Template, parse_state
from lint import walk, access_issues, passable, bname
from .obra import CX

ENTRANCE = (CX, 1, 0)
GOOD_RANGE = (0.80, 0.85)
WEAR = {"tuff_bricks": None, "polished_tuff": None, "red_terracotta": 0.15}   # None = probabilidad de erosión
RUIN_BLOCKS = {"tuff", "gravel", "moss_block", "cobblestone", "grass_block", "tuff_slab"}
EXPECTED = {"cofre": 13, "generador": 4}


def view(o, solved=True, opened=True, start=ENTRANCE):
    v = Template("vista")
    for p, (st, nbt) in o.t.blocks.items():
        b = bname(st)
        if (opened and p in o.sealed) or (solved and p in o.puzzle):
            st = "minecraft:air"
        elif b == "water" or "waterlogged=true" in st and b != "sea_pickle":
            st = "minecraft:ladder[facing=north,waterlogged=false]"      # nadar = moverse en las tres direcciones
        v.blocks[p] = (st, None)
    v.jigsaws = [dict(pos=start, name="heraldia:entrance")]
    return v


def near(cells, p, r=1):
    x, y, z = p
    return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
               for dy in (-1, 0, 1) if abs(dx) + abs(dz) <= r)


def floating(o):
    solid = {p for p, (st, _) in o.t.blocks.items() if bname(st) != "air"}
    ymin = min(p[1] for p in solid)
    q = deque(p for p in solid if p[1] in (0, ymin))
    seen = set(q)
    while q:
        x, y, z = q.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(solid - seen)


def water_issues(o):
    out = []
    g = o.get
    for (x, y, z), (st, _) in o.t.blocks.items():
        if bname(st) == "water" or "waterlogged=true" in st:
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
                n = g(x + dx, y + dy, z + dz)
                if n is None or bname(n) == "air" or passable(n) and bname(n) != "water" and "waterlogged=true" not in n:
                    out.append(("agua sin encerrar", (x, y, z)))
                    break
    return out


def props(st):
    return parse_state(st)[1]


SOLID_OK = ("tuff", "stone", "deepslate", "bricks", "polished", "chiseled", "cobblestone")


def conductor(st):
    return st is not None and any(k in bname(st) for k in SOLID_OK) and not any(
        k in bname(st) for k in ("stairs", "slab", "wall", "pressure_plate"))


def redstone_issues(o):
    out = []
    g = o.get
    # cable trampa: ganchos enganchados, cuerda tendida y dispensador pegado al bloque de apoyo
    for (x, y, z) in o.marks.get("trampa:cable", []):
        st = g(x, y, z)
        if bname(st) != "tripwire" or props(st).get("attached") != "true":
            out.append(("cuerda sin tensar", (x, y, z)))
        if not conductor(g(x, y - 1, z)):
            out.append(("cuerda sin suelo", (x, y, z)))
        for dz, face in ((-1, "south"), (1, "north")):
            hk = g(x, y, z + dz)
            if bname(hk) != "tripwire_hook" or props(hk) != {"attached": "true", "facing": face, "powered": "false"}:
                out.append(("gancho mal colocado", (x, y, z + dz)))
            base = (x, y, z + 2 * dz)
            if not conductor(g(*base)):
                out.append(("gancho sin apoyo", base))
            disp = [n for n in ((base[0], base[1] + 1, base[2]), (base[0], base[1] - 1, base[2]))
                    if bname(g(*n)) == "dispenser"]
            if not disp or not o.t.blocks[disp[0]][1].get("Items"):
                out.append(("trampa de cable sin dispensador cargado", base))
    # losas de dardos: placa sobre dispensador hacia arriba con flechas
    for (x, y, z) in o.marks.get("trampa:dardos", []):
        d = o.t.blocks.get((x, y - 1, z))
        if not d or bname(d[0]) != "dispenser" or props(d[0]).get("facing") != "up" or not d[1].get("Items"):
            out.append(("losa de dardos sin dispensador", (x, y, z)))
        if bname(g(x, y, z)) != "polished_blackstone_pressure_plate":
            out.append(("losa sin placa", (x, y, z)))
    # foso: la placa carga su bloque y ese bloque toca una trampilla de hierro cerrada
    for (x, y, z) in o.marks.get("trampa:foso", []):
        base = (x, y - 1, z)
        if not conductor(g(*base)):
            out.append(("placa del foso sin bloque conductor", base))
        tds = [n for n in ((x + 1, y - 1, z), (x - 1, y - 1, z), (x, y - 1, z + 1), (x, y - 1, z - 1))
               if bname(g(*n)) == "iron_trapdoor"]
        if not tds or any(props(g(*n)).get("open") != "false" for n in tds):
            out.append(("placa del foso sin trampilla", (x, y, z)))
    # puerta secreta
    d = o.door
    tx, ty, tz = d["torch"]
    if g(*d["torch"]) != "minecraft:redstone_wall_torch[facing=west,lit=true]":
        out.append(("antorcha de la puerta", d["torch"]))
    if d["X"] != (tx + 1, ty, tz) or not conductor(g(*d["X"])) or not conductor(g(*d["Y"])) or d["Y"] != (tx, ty + 1, tz):
        out.append(("bloques X/Y de la puerta", d["X"]))
    for p, hd, dd in zip(d["pistons"], d["heads"], d["D"]):
        if g(*p) != "minecraft:sticky_piston[extended=true,facing=west]" or (p[0] + 1, p[1], p[2]) not in (d["torch"], d["Y"]):
            out.append(("pistón de la puerta", p))
        if g(*hd) != "minecraft:piston_head[facing=west,short=false,type=sticky]" or hd != (p[0] - 1, p[1], p[2]):
            out.append(("cabeza de pistón", hd))
        if not conductor(g(*dd)) or dd != (hd[0] - 1, hd[1], hd[2]):
            out.append(("bloque de la puerta", dd))
    lv = g(*d["lever"])
    if lv != "minecraft:lever[face=wall,facing=south,powered=false]" or d["lever"] != (d["X"][0], d["X"][1], d["X"][2] + 1):
        out.append(("palanca de la puerta", d["lever"]))
    # nada más con corriente en reposo
    for p, (st, _) in o.t.blocks.items():
        pr = props(st)
        if pr.get("powered") == "true" or pr.get("triggered") == "true" or (
                bname(st) == "redstone_wire" and pr.get("power") != "0"):
            out.append(("bloque con corriente en reposo", p))
    return out


def good_fraction(o, wear):
    """Fracción esperada de superficie exterior en buen estado (pieza de superficie)."""
    g = o.get
    total, bad = 0, 0.0
    for (x, y, z), (st, _) in o.t.blocks.items():
        if y < 0 or passable(st) or bname(st) in ("water",):
            continue
        exposed = False
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            nb = g(*n)
            if n not in o.carved and (nb is None or bname(nb) == "air" or passable(nb)):
                exposed = True
                break
        if not exposed:
            continue
        total += 1
        b = bname(st)
        if (x, y, z) in o.ruin or b in RUIN_BLOCKS:
            bad += 1
        elif b in WEAR:
            bad += WEAR[b] if WEAR[b] is not None else wear
    return total, bad


def tune_wear(o):
    """Probabilidad de erosión del ladrillo y la toba pulida para quedar en el centro del intervalo."""
    total, bad0 = good_fraction(o, 0.0)
    _, bad1 = good_fraction(o, 1.0)
    target = 1 - sum(GOOD_RANGE) / 2
    p = (target * total - bad0) / max(1.0, bad1 - bad0)
    return round(min(0.25, max(0.02, p)), 3)


def audit(o, wear):
    issues = []
    v = view(o)
    cells = walk(v)
    water = {p for p, (st, _) in o.t.blocks.items() if bname(st) == "water" or "waterlogged=true" in st}
    issues += [i for i in access_issues(v) if i[1] not in water]
    for name, ps in o.marks.items():
        if name.startswith("trampa:cable") or name == "foso":
            continue
        for p in ps:
            if not near(cells, p, 1 if not name.startswith("cofre") else 1):
                issues.append((f"{name} inalcanzable", p))
    counts = {k: sum(len(v) for n, v in o.marks.items() if n.startswith(k + ":")) for k in EXPECTED}
    for k, n in EXPECTED.items():
        if counts[k] != n:
            issues.append((f"{k}: {counts[k]} (esperados {n})", None))
    # la puerta secreta cierra el tesoro y el tapiado oculta su sala
    shut = walk(view(o, solved=False))
    if near(shut, o.marks["sala_oculta:tesoro"][0]):
        issues.append(("el tesoro se alcanza sin abrir la puerta secreta", o.marks["sala_oculta:tesoro"][0]))
    sealed = walk(view(o, opened=False))
    if near(sealed, o.marks["sala_oculta:tapiada"][0]):
        issues.append(("la cámara tapiada se alcanza sin romper el tapiado", o.marks["sala_oculta:tapiada"][0]))
    # del fondo del foso se vuelve a la plaza
    pit = walk(view(o, start=o.marks["foso"][0]))
    if ENTRANCE not in pit:
        issues.append(("el foso no tiene salida", o.marks["foso"][0]))
    fl = floating(o)
    issues += [("bloque flotando", p) for p in fl[:10]]
    issues += water_issues(o)[:10]
    issues += redstone_issues(o)
    total, bad = good_fraction(o, wear)
    good = 1 - bad / total
    if not GOOD_RANGE[0] <= good <= GOOD_RANGE[1]:
        issues.append((f"superficie en buen estado {good:.3f} fuera de {GOOD_RANGE}", None))
    stats = dict(celdas=len(cells), buen_estado=round(good, 3), erosion=wear, superficie=total, **counts)
    return issues, stats, cells
