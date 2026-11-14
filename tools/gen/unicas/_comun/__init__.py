"""Piezas comunes y parametrizadas para las estructuras únicas (no es una estructura: el prefijo _ la excluye):
escalera de caracol,
puerta secreta de pistones, trampas de flechas, generadores, guardianes, carteles traducibles y ayudas de botín).

Las funciones reciben cualquier objeto con set(x, y, z, estado, nbt=None) y get(x, y, z), como core.Template.
Todo se coloca en un estado de reposo coherente: funciona al generarse sin actualizaciones de bloque.
"""
from core import B, F, parse_state, state_str
from loot import item

RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # E, NE, N, NO, O, SO, S, SE
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
DIR = {(-1, 0): "west", (1, 0): "east", (0, -1): "north", (0, 1): "south"}


def st(name, **p):
    return state_str("minecraft:" + name, {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in p.items()})


# ---------------------------------------------------------------------- escaleras
def spiral(t, cx, cz, start, k_max, y0=0, mat="stone_brick"):
    """Escalera de caracol de losas alrededor de un núcleo macizo en (cx, cz): 8 celdas por vuelta y 0,5 bloques
    por celda (4 por vuelta, cabeza libre). La celda k tiene la superficie y0 + 0,5 (k + 1); start elige la celda
    inicial en RING. Devuelve las posiciones de los peldaños. La celda central y los muros los pone quien llama."""
    cells = []
    for k in range(k_max + 1):
        dx, dz = RING[(start + k) % 8]
        sv = y0 + 0.5 * (k + 1)
        y, typ = (int(sv - 0.5), "bottom") if sv % 1 else (int(sv) - 1, "top")
        t.set(cx + dx, y, cz + dz, st(mat + "_slab", type=typ))
        cells.append((cx + dx, y, cz + dz))
    return cells


# ---------------------------------------------------------------------- puertas secretas
def piston_door(t, door, axis, sign, levers, name=""):
    """Puerta secreta de dos bloques en la capa central de un muro de tres de grueso, sujeta por dos pistones
    pegajosos extendidos (en door + 1 y + 2 pasos en la dirección axis/sign).

    levers: [(palanca, bloque al que está fijada, correcta)] en una cara del muro. Tras cada palanca correcta se pone
    una antorcha de redstone (inversor) en la capa central; las antorchas alimentan una línea de polvo, a la altura
    del pistón superior, que mantiene los pistones extendidos. Una palanca falsa alimenta la línea directamente.
    Se abre solo con todas las correctas activadas y ninguna falsa. Las antorchas cortan la línea en tramos: cada
    palanca falsa debe estar junto al tramo que llega al pistón (la auditoría de la catedral lo comprueba).
    Devuelve un registro con las posiciones para auditorías y pruebas en servidor."""
    x, y, z = door
    step = (sign, 0) if axis == "x" else (0, sign)
    pos = lambda k, dy=0: (x + step[0] * k, y + dy, z + step[1] * k)
    toward = DIR[(-step[0], -step[1])]
    rec = {"tipo": "puerta de pistones", "sitio": name, "puerta": [pos(0), pos(0, 1)], "cabezas": [], "pistones": [],
           "antorchas": [], "polvo": [], "palancas": [], "falsas": []}
    for dy in (0, 1):
        t.set(*pos(1, dy), st("piston_head", facing=toward, type="sticky", short=False))
        t.set(*pos(2, dy), st("sticky_piston", facing=toward, extended=True))
        rec["cabezas"].append(pos(1, dy))
        rec["pistones"].append(pos(2, dy))
    torches = set()
    for (lp, bp, ok) in levers:
        out = DIR[(lp[0] - bp[0], lp[2] - bp[2])]
        t.set(*lp, st("lever", face="wall", facing=out, powered=False))
        rec["palancas" if ok else "falsas"].append((lp, bp))
        if ok:
            mid = (2 * bp[0] - lp[0], bp[1], 2 * bp[2] - lp[2])
            t.set(*mid, st("redstone_wall_torch", facing=OPP[out], lit=True))
            torches.add(mid)
            rec["antorchas"].append(mid)
    far = max(torches, key=lambda q: abs(q[0] - x) + abs(q[2] - z))
    line, k = [], 3
    while pos(k, 1) != far:
        if pos(k, 1) not in torches:
            line.append(pos(k, 1))
        k += 1
        if k > 30:
            raise ValueError("línea de polvo sin final")
    nb = lambda p: [(p[0] + step[0], p[1], p[2] + step[1]), (p[0] - step[0], p[1], p[2] - step[1])]
    power = {p: (15 if any(q in torches for q in nb(p)) else 0) for p in line}
    for _ in range(len(line)):
        for p in line:
            power[p] = max(power[p], max(power.get(q, 0) - 1 for q in nb(p)))
    sides = ("east", "west") if axis == "x" else ("north", "south")
    for p in line:
        t.set(*p, st("redstone_wire", power=power[p], **{d: ("side" if d in sides else "none")
                                                          for d in ("north", "south", "east", "west")}))
        rec["polvo"].append((p, power[p]))
    return rec


# ---------------------------------------------------------------------- trampas
def arrows(n=32):
    return {"id": "minecraft:dispenser", "Items": [{"Slot": B(i), "id": "minecraft:arrow", "count": 16} for i in range(n // 16)]}


def tripwire_trap(t, hook_a, hook_b, name=""):
    """Cable trampa recto entre dos ganchos (en las caras de dos muros enfrentados) con un dispensador de flechas
    justo encima de cada gancho, que el gancho activa directamente. hook_a y hook_b alineados en x o en z."""
    (ax, ay, az), (bx, by, bz) = hook_a, hook_b
    along_x = az == bz
    fa = ("east" if bx > ax else "west") if along_x else ("south" if bz > az else "north")
    fb = OPP[fa]
    t.set(*hook_a, st("tripwire_hook", attached=True, facing=fa, powered=False))
    t.set(*hook_b, st("tripwire_hook", attached=True, facing=fb, powered=False))
    wire = []
    rng = range(min(ax, bx) + 1, max(ax, bx)) if along_x else range(min(az, bz) + 1, max(az, bz))
    for v in rng:
        p = (v, ay, az) if along_x else (ax, ay, v)
        t.set(*p, st("tripwire", attached=True, disarmed=False, powered=False, north=not along_x, south=not along_x,
                     east=along_x, west=along_x))
        wire.append(p)
    disp = []
    for (h, f) in ((hook_a, fa), (hook_b, fb)):
        p = (h[0], h[1] + 1, h[2])
        t.set(*p, st("dispenser", facing=f, triggered=False), arrows())
        disp.append(p)
    return {"tipo": "cable trampa", "sitio": name, "ganchos": [hook_a, hook_b], "cable": wire, "dispensadores": disp}


def plate_trap(t, plate, dispensers, name="", plate_block="stone_pressure_plate"):
    """Placa de presión con dispensadores de flechas contiguos [(pos, facing)] que la placa activa directamente."""
    t.set(*plate, st(plate_block, powered=False))
    for (p, f) in dispensers:
        t.set(*p, st("dispenser", facing=f, triggered=False), arrows())
    return {"tipo": "placa de presión", "sitio": name, "placa": plate, "dispensadores": [p for p, _ in dispensers]}


# ---------------------------------------------------------------------- generadores, guardianes y carteles
def spawner(t, pos, mob):
    t.set(*pos, "minecraft:spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": "minecraft:" + mob}}})


def guardian(mob, key, fallback, health=40.0, armor=0.0, equipment=None, drops=None):
    """NBT de un guardián con nombre traducible, vida y armadura moderadas y PersistenceRequired.
    equipment: {"mainhand": {"id": ..., "count": 1, "components": {...}}, "head": ...}; drops: {ranura: probabilidad}."""
    n = {"id": "minecraft:" + mob, "PersistenceRequired": B(1), "CustomNameVisible": B(1),
         "CustomName": {"translate": key, "fallback": fallback}, "Health": F(health),
         "attributes": [{"id": "minecraft:max_health", "base": float(health)}]}
    if armor:
        n["attributes"].append({"id": "minecraft:armor", "base": float(armor)})
    if equipment:
        n["equipment"] = equipment
    if drops:
        n["drop_chances"] = {k: F(v) for k, v in drops.items()}
    return n


def sign_nbt(lines):
    """Cartel encerado con líneas traducibles [(clave, texto de respaldo)], centradas en las cuatro líneas."""
    msgs = [{"translate": k, "fallback": f} for k, f in lines]
    pad = (4 - len(msgs)) // 2
    msgs = [{"text": ""}] * pad + msgs + [{"text": ""}] * (4 - len(msgs) - pad)
    side = lambda m: {"messages": m, "color": "black", "has_glowing_text": B(0)}
    return {"id": "minecraft:sign", "is_waxed": B(1), "front_text": side(msgs), "back_text": side([{"text": ""}] * 4)}


# ---------------------------------------------------------------------- botín
def named(name, w, key, fallback, ench=None, lo=1, hi=1):
    """Entrada de botín con nombre traducible y encantamientos fijos opcionales ({"minecraft:sharpness": 3})."""
    e = item(name, w, lo, hi)
    mods = [e.pop("modifier")] if "modifier" in e else []
    mods.append({"type": "minecraft:set_name", "target": "item_name", "name": {"translate": key, "fallback": fallback}})
    if ench:
        mods.append({"type": "minecraft:set_enchantments", "enchantments": ench})
    e["modifier"] = mods
    return e


def pool(rolls, entries, extra=False):
    """Grupo de botín; extra=True lo marca solo_sin_lootr (se omite con Lootr)."""
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}
