"""Piezas comunes de las estructuras únicas: todas quedan en un estado coherente al colocarse (sin depender de
actualizaciones de bloque que no ocurren al generar)."""
from core import B, F

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
VDIR = {v: k for k, v in DIRV.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def text(key, fallback):
    return {"translate": key, "fallback": fallback}


# ------------------------------------------------------------------ entidades de bloque
def spawner(put, x, y, z, mob, potentials=False, luz=None):
    """Generador de monstruos de un solo tipo. `luz` (máx. de luz de bloque, 0-15) añade custom_spawn_rules para que
    los monstruos salgan aunque haya algo de luz cerca (por defecto exigen luz de bloque 0)."""
    e = {"entity": {"id": "minecraft:" + mob}}
    if luz is not None:
        e["custom_spawn_rules"] = {"block_light_limit": {"min_inclusive": 0, "max_inclusive": luz},
                                   "sky_light_limit": {"min_inclusive": 0, "max_inclusive": 15}}
    nbt = {"id": "minecraft:mob_spawner", "SpawnData": e}
    if potentials:
        nbt["SpawnPotentials"] = [{"weight": 1, "data": e}]
    put(x, y, z, "spawner", nbt)


def chest(put, x, y, z, facing, loot, kind="chest", waterlogged=False):
    """Cofre o barril con tabla de botín; `waterlogged` para un cofre bajo el agua."""
    st = f"barrel[facing={facing}]" if kind == "barrel" else f"{kind}[facing={facing}]"
    if waterlogged:
        st = st[:-1] + ",type=single,waterlogged=true]"
    put(x, y, z, st, {"id": "minecraft:" + ("barrel" if kind == "barrel" else kind), "LootTable": loot})


def sign(put, x, y, z, facing, lines, wood="dark_oak"):
    """Cartel de pared encerado; `lines`: hasta 4 componentes de texto (translate + fallback)."""
    msgs = list(lines) + [{"text": ""}] * (4 - len(lines))
    put(x, y, z, f"{wood}_wall_sign[facing={facing}]",
        {"id": "minecraft:sign", "is_waxed": B(1),
         "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
         "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})


def guardian(mob, key, fallback, health, armor=None, equipment=None, drop_chances=None, death_loot=None,
             attributes=None, extra=None):
    """NBT de un guardián con nombre, persistente y con atributos moderados. `attributes` {id: base} añade
    atributos (attack_damage, knockback_resistance...); `extra` se mezcla en el NBT."""
    n = {"id": "minecraft:" + mob, "PersistenceRequired": B(1), "CustomNameVisible": B(1),
         "CustomName": text(key, fallback), "Health": F(float(health)),
         "attributes": [{"id": "minecraft:max_health", "base": float(health)}]}
    if armor:
        n["attributes"].append({"id": "minecraft:armor", "base": float(armor)})
    if equipment:
        n["equipment"] = equipment
    if drop_chances:
        n["drop_chances"] = {k: F(v) for k, v in drop_chances.items()}
    if death_loot:
        n["DeathLootTable"] = death_loot
    for aid, base in (attributes or {}).items():
        n["attributes"].append({"id": "minecraft:" + aid, "base": float(base)})
    n.update(extra or {})
    return n


# ------------------------------------------------------------------ redstone
def piston_door(put, door, axis, side, block):
    """Puerta secreta: cada bloque de `door` (x, y, z) queda sujeto por un pistón pegajoso EXTENDIDO situado a dos
    casillas en la dirección `axis` (dx, dz), con la cabeza entre ambos mirando a `side`. La alimentación (palanca,
    antorcha...) la pone quien llama; al quitarla, los pistones retiran los bloques y dejan la puerta abierta."""
    ax, az = axis
    for (x, y, z) in door:
        put(x, y, z, block)
        put(x + ax, y, z + az, f"piston_head[facing={side},short=false,type=sticky]")
        put(x + 2 * ax, y, z + 2 * az, f"sticky_piston[extended=true,facing={side}]")


def wire(put, path, y=None, ends=()):
    """Polvo de redstone apagado a lo largo de `path` [(x, z)...] a la altura `y`, o [(x, y, z)...] con escalones de
    un bloque (el polvo de abajo «sube» hacia el de arriba; quien llama deja aire sobre el polvo de abajo).
    `ends` da, para el primero y el último, la dirección extra a la que apunta."""
    extra = dict(ends)
    pts = [(p[0], y, p[1]) if len(p) == 2 else tuple(p) for p in path]
    for i, (x, py, z) in enumerate(pts):
        sides = {}
        for j in (i - 1, i + 1):
            if 0 <= j < len(pts):
                nx, ny, nz = pts[j]
                sides[VDIR[(nx - x, nz - z)]] = "up" if ny > py else "side"
        if i in extra:
            sides[extra[i]] = "side"
        if len(sides) == 1:                       # un tramo suelto apunta en línea recta
            sides[OPP[next(iter(sides))]] = "side"
        put(x, py, z, "redstone_wire[" + ",".join(f"{d}={sides.get(d, 'none')}"
                                                   for d in ("north", "south", "east", "west")) + ",power=0]")


def comparator(put, x, y, z, facing):
    """Comparador apagado que lee el bloque en `facing` y emite hacia el lado contrario."""
    put(x, y, z, f"comparator[facing={facing},mode=compare,powered=false]", {"id": "minecraft:comparator", "OutputSignal": 0})


def tripwire_trap(put, hook_a, hook_b, y, along, dispensers, arrows=6):
    """Trampa de hilo (templo de la jungla): ganchos en hook_a y hook_b (x, z) unidos en línea recta a lo largo de
    `along` ('x' o 'z'); cada dispensador ((x, y, z), facing) va junto al bloque al que se agarra un gancho."""
    (ax, az), (bx, bz) = hook_a, hook_b
    if along == "z":
        put(ax, y, az, f"tripwire_hook[attached=true,facing={'south' if bz > az else 'north'},powered=false]")
        put(bx, y, bz, f"tripwire_hook[attached=true,facing={'north' if bz > az else 'south'},powered=false]")
        cells = [(ax, z) for z in range(min(az, bz) + 1, max(az, bz))]
        props = "north=true,south=true,east=false,west=false"
    else:
        put(ax, y, az, f"tripwire_hook[attached=true,facing={'east' if bx > ax else 'west'},powered=false]")
        put(bx, y, bz, f"tripwire_hook[attached=true,facing={'west' if bx > ax else 'east'},powered=false]")
        cells = [(x, az) for x in range(min(ax, bx) + 1, max(ax, bx))]
        props = "north=false,south=false,east=true,west=true"
    for (x, z) in cells:
        put(x, y, z, f"tripwire[attached=true,disarmed=false,powered=false,{props}]")
    for (p, facing) in dispensers:
        put(*p, f"dispenser[facing={facing},triggered=false]",
            {"id": "minecraft:dispenser", "Items": [{"Slot": B(i), "id": "minecraft:arrow", "count": arrows} for i in range(3)]})


def door(put, x, y, z, facing, kind="spruce_door", hinge="left"):
    """Puerta de dos bloques cerrada (también de hierro: se abre al recibir señal)."""
    for h, dy in (("lower", 0), ("upper", 1)):
        put(x, y + dy, z, f"{kind}[facing={facing},half={h},hinge={hinge},open=false,powered=false]")


def tnt_trap(put, x, y, z, plate="stone_pressure_plate", warn=None):
    """Trampa de losa (templo del desierto): placa en (x, y, z) sobre el suelo y TNT dos bloques más abajo;
    `warn` [(x, y, z)] recibe ladrillos agrietados como aviso."""
    put(x, y, z, f"{plate}[powered=false]")
    put(x, y - 2, z, "tnt[unstable=false]")
    for p in warn or ():
        put(*p, "cracked_stone_bricks")


def lever_door(put, door, slide, face, block, wall):
    """Puerta secreta enrasada de 1 x 2 al fondo de un nicho, con su palanca (Coliseo, probada en servidor).

    door: bloque inferior de la puerta; slide: dirección (dentro del muro) hacia la que se recoge; face: dirección de
    la sala, donde quedan el nicho y la palanca. Usa `piston_door` y la alimenta con una antorcha de redstone en la cara
    oculta del bloque de la palanca (y el bloque macizo de encima para el pistón superior): palanca encendida ->
    antorcha apagada -> la puerta se abre. El resto del muro lo pone quien llama. Devuelve las posiciones y el estado
    con la puerta abierta (pos -> estado) para auditar el recorrido."""
    sx, sz = DIRV[slide]
    fx, fz = DIRV[face]
    x, y, z = door
    cells = [(x, y, z), (x, y + 1, z)]
    piston_door(put, cells, (sx, sz), OPP[slide], block)
    torch = (x + 3 * sx, y, z + 3 * sz)
    base = (torch[0] + fx, y, torch[2] + fz)
    lever = (base[0] + fx, y, base[2] + fz)
    put(*torch, f"redstone_wall_torch[facing={OPP[face]},lit=true]")
    put(torch[0], y + 1, torch[2], wall)
    put(*base, wall)
    put(*lever, f"lever[face=wall,facing={face},powered=false]")
    for c in cells:
        put(c[0] + fx, c[1], c[2] + fz, "air")
    opened = {}
    for (cx, cy, cz) in cells:
        opened[(cx, cy, cz)] = "minecraft:air"
        opened[(cx + sx, cy, cz + sz)] = block if ":" in block else "minecraft:" + block
        opened[(cx + 2 * sx, cy, cz + 2 * sz)] = f"minecraft:sticky_piston[extended=false,facing={OPP[slide]}]"
    opened[torch] = f"minecraft:redstone_wall_torch[facing={OPP[face]},lit=false]"
    opened[lever] = f"minecraft:lever[face=wall,facing={face},powered=true]"
    return {"door": door, "lever": lever, "torch": torch, "opened": opened}


def plate_trap(put, plates, side, arrows=6, plate="stone_pressure_plate"):
    """Trampa de placas con flechas: cada placa (x, y, z) activa los dos dispensadores a ras de suelo que tiene a
    los lados (`side` y su opuesto), que disparan hacia ella."""
    for (x, y, z) in plates:
        put(x, y, z, f"{plate}[powered=false]")
        for d in (side, OPP[side]):
            a, c = DIRV[d]
            put(x + a, y, z + c, f"dispenser[facing={OPP[d]},triggered=false]",
                {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": arrows}]})


def item_frame(x, y, z, facing_byte, item=None):
    """NBT de un marco: sin `block_pos` el juego descarta la entidad al colocar la plantilla."""
    n = {"id": "minecraft:item_frame", "Facing": B(facing_byte), "block_pos": [x, y, z]}
    if item:
        n["Item"] = {"id": "minecraft:" + item, "count": 1}
    return n


# ------------------------------------------------------------------ escalera de caracol
RING = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
HOLES = (RING[5], RING[6])
GUARD = [(-2, 0), (-2, 1), (-2, 2), (-1, 2)]


def spiral_stair(put, cx, cz, feet, stair, newel, landing, newel_top=None):
    """Escalera de caracol de una casilla alrededor de un machón de 1x1 en (cx, cz): seis peldaños por tramo de 6 de
    altura y rellano de dos casillas al norte. `feet`: alturas de los pies de cada planta de salida (cada 6). Abre el
    hueco del forjado de llegada (HOLES) y devuelve las celdas a proteger con barandilla (GUARD) relativas al eje.
    Cada tramo es un spiral_continuous de 6 peldaños con contrapeldaño invertido."""
    top = newel_top if newel_top is not None else feet[-1] + 6
    for y in range(feet[0] - 1, top + 1):
        put(cx, y, cz, newel)
    ring = [(cx + x, cz + z) for (x, z) in RING]
    for f in feet:
        spiral_continuous(put, ring, f, 6, stair, start=2, under=True)
        for k in (0, 1):
            put(cx + RING[k][0], f - 1, cz + RING[k][1], landing)
        for (x, z) in HOLES:
            if f != feet[0]:
                put(cx + x, f - 1, cz + z, "air")
    for (x, z) in HOLES:
        put(cx + x, feet[-1] + 5, cz + z, "air")
    return GUARD


RING8 = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def slab_y(s):
    """(y, tipo) de la losa cuya superficie queda a la altura s (múltiplo de 0,5)."""
    return (int(s) - 1, "top") if s == int(s) else (int(s - 0.5), "bottom")


def spiral_slabs(put, nx, nz, s0, s1, phase, slab, ring=None, props=",waterlogged=false"):
    """Caracol continuo de losas de 3 x 3 alrededor de un machón en (nx, nz) (lo pone quien llama): cada peldaño sube
    media altura, de los pies s0 a s1, sin rellanos. El peldaño i ocupa ring[(i + phase) % 8] (por defecto RING8,
    sentido horario; SLAB_RING, antihorario); `phase` elige el lado de cada salida y `props` añade propiedades al
    estado de la losa. Devuelve [(i, x, z, pies)]; la y de cada losa es slab_y(pies)[0]."""
    ring = ring or RING8
    steps = []
    for i in range(int(round((s1 - s0) * 2)) + 1):
        s = s0 + 0.5 * i
        dx, dz = ring[(i + phase) % 8]
        x, z = nx + dx, nz + dz
        y, typ = slab_y(s)
        put(x, y, z, f"{slab}[type={typ}{props}]")
        steps.append((i, x, z, s))
    return steps


def circle(cx, cz, r):
    """Celdas (x, z) de un círculo de radio r."""
    R = int(r) + 1
    return [(cx + dx, cz + dz) for dx in range(-R, R + 1) for dz in range(-R, R + 1) if dx * dx + dz * dz <= r * r]


def spiral_continuous(put, ring, y0, n, stair, support=None, start=0, under=False):
    """Caracol continuo de `n` peldaños desde y0 por las casillas contiguas de `ring` (absolutas, alrededor de un
    machón), empezando en ring[start], sin rellanos propios: sirve cuando las plantas no van cada 6 y los rellanos
    están fuera del anillo. Cada peldaño mira hacia donde se llega, así que en las esquinas también se entra por el
    lado bajo; los de esquina no tocan el machón y llevan `support` debajo; con `under`, todos menos el primero
    llevan debajo un peldaño invertido. Devuelve las posiciones de los peldaños."""
    out, k = [], len(ring)
    for i in range(start, start + n):
        x, z = ring[i % k]
        px, pz = ring[(i - 1) % k]
        nx, nz = ring[(i + 1) % k]
        facing = VDIR[(x - px, z - pz)]
        y = y0 + i - start
        put(x, y, z, f"{stair}[facing={facing},half=bottom]")
        if under and i > start:
            put(x, y - 1, z, f"{stair}[facing={OPP[facing]},half=top]")
        elif support and i > start and (nx - x, nz - z) != (x - px, z - pz):
            put(x, y - 1, z, support)
        out.append((x, y, z))
    return out


# ------------------------------------------------------------------ entidades
def painting(x, y, z, facing, variant):
    """NBT de un cuadro para Template.entity: `facing` en código 2D y `block_pos` como IntArray (verificado en 26.3;
    1x2 ocupa la casilla y la de encima)."""
    from nbtlib import Compound, String, Byte, IntArray
    f2d = {"south": 0, "west": 1, "north": 2, "east": 3}[facing]
    return Compound({"id": String("minecraft:painting"), "variant": String("minecraft:" + variant),
                     "facing": Byte(f2d), "block_pos": IntArray([x, y, z])})


# ------------------------------------------------------------------ conexiones
NONFULL = ("air", "stairs", "slab", "fence", "pane", "bars", "_wall", "door", "carpet", "lantern", "torch",
           "chest", "lectern", "cauldron", "pot", "sign", "banner", "bed", "candle", "chain", "rod", "plate",
           "cobweb", "wire", "comparator", "hook", "tripwire", "skull", "brewing", "cluster", "enchanting",
           "fern", "blossom", "azalea", "orchid", "allium", "valley", "pitcher", "eyeblossom", "torchflower",
           "vine", "piston_head", "composter", "water", "lava", "lever", "button", "ladder")


def connect(t):
    """Vallas, cristales, barrotes y muros de piedra conectan con sus vecinos (el juego no los actualiza al colocar)."""
    def name(st):
        return st.split("[")[0].replace("minecraft:", "") if st else ""

    def full(st):
        return bool(st) and not any(k in name(st) for k in NONFULL)

    for (x, y, z), (st, nbt) in list(t.blocks.items()):
        b = name(st)
        fam = "fence" if b.endswith("_fence") else "pane" if (b.endswith("_pane") or b == "iron_bars") else \
            "wall" if (b.endswith("_wall") and "wall_" not in b) else None
        if not fam:
            continue
        props = {}
        for d, (a, c) in DIRV.items():
            o = t.get(x + a, y, z + c)
            ob = name(o)
            same = (fam == "fence" and (ob.endswith("_fence") or "fence_gate" in ob)) or \
                   (fam == "pane" and (ob.endswith("_pane") or ob == "iron_bars")) or \
                   (fam == "wall" and ob.endswith("_wall") and "wall_" not in ob)
            con = same or full(o)
            props[d] = ("low" if con else "none") if fam == "wall" else ("true" if con else "false")
        if fam == "wall":
            ns, ew = props["north"] != "none" and props["south"] != "none", props["east"] != "none" and props["west"] != "none"
            straight = (ns and props["east"] == props["west"] == "none") or (ew and props["north"] == props["south"] == "none")
            props["up"] = "false" if straight else "true"
        props["waterlogged"] = "false"
        t.blocks[(x, y, z)] = (f"minecraft:{b}[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]", nbt)


# ------------------------------------------------------------------ añadidos de la catedral
def combo_door(put, door, axis, sign, levers, name="", block=None):
    """Puerta secreta de combinación (varias palancas; con una sola, mejor lever_door): dos bloques (door = bloque
    inferior) con su alimentación: dos pistones pegajosos extendidos
    (como piston_door) y, por cada palanca [(palanca, bloque al que se fija)], una antorcha de redstone al otro lado
    de ese bloque (inversor) que enciende una línea de polvo a la altura del pistón superior, en la capa de la puerta.
    La puerta se abre solo con todas las palancas activadas.

    Con varias palancas, las antorchas van en una capa intermedia, junto a la línea y no dentro de ella: una antorcha
    en la línea la corta en tramos y solo su tramo llega al pistón (se abriría con una sola palanca). Así, un muro de
    cuatro de grueso: palancas | antorchas | puerta, pistones y polvo | cara opuesta. Con una palanca basta un muro
    de tres (la antorcha cierra la línea). El polvo lleva escritas su forma y su potencia.
    axis 'x' o 'z' y sign ±1: hacia dónde quedan los pistones. Con `block`, la puerta y sus pistones salen de
    piston_door; sin él, el bloque de la puerta lo pone quien llama.
    Devuelve un registro con posiciones (puerta, cabezas, pistones, antorchas, polvo, palancas)."""
    x, y, z = door
    step = (sign, 0) if axis == "x" else (0, sign)
    pos = lambda k, dy=0: (x + step[0] * k, y + dy, z + step[1] * k)
    toward = VDIR[(-step[0], -step[1])]
    rec = {"tipo": "puerta de pistones", "sitio": name, "puerta": [pos(0), pos(0, 1)],
           "cabezas": [pos(1), pos(1, 1)], "pistones": [pos(2), pos(2, 1)], "antorchas": [], "polvo": [],
           "palancas": [], "falsas": []}
    if block:
        piston_door(put, [pos(0), pos(0, 1)], step, toward, block)
    else:                                     # la puerta la pone quien llama
        for dy in (0, 1):
            put(*pos(1, dy), f"piston_head[facing={toward},short=false,type=sticky]")
            put(*pos(2, dy), f"sticky_piston[extended=true,facing={toward}]")
    torches = {}
    for (lp, bp) in levers:
        out = VDIR[(lp[0] - bp[0], lp[2] - bp[2])]
        put(*lp, f"lever[face=wall,facing={out},powered=false]")
        tp = (2 * bp[0] - lp[0], bp[1], 2 * bp[2] - lp[2])
        put(*tp, f"redstone_wall_torch[facing={OPP[out]},lit=true]")
        torches[tp] = OPP[out]
        rec["palancas"].append((lp, bp))
        rec["antorchas"].append(tp)
    proj = lambda q: (q[0] - x) * step[0] + (q[2] - z) * step[1]
    far = max(proj(q) for q in torches)
    line = [pos(k, 1) for k in range(3, far + 1) if pos(k, 1) not in torches]
    adj = lambda p: {VDIR[(q[0] - p[0], q[2] - p[2])] for q in torches
                     if q[1] == p[1] and abs(q[0] - p[0]) + abs(q[2] - p[2]) == 1}
    nb = lambda p: [(p[0] + step[0], p[1], p[2] + step[1]), (p[0] - step[0], p[1], p[2] - step[1])]
    power = {p: (15 if adj(p) else 0) for p in line}
    for _ in range(len(line)):
        for p in line:
            power[p] = max(power[p], max(power.get(q, 0) - 1 for q in nb(p)))
    for p in line:
        sides = {VDIR[(q[0] - p[0], q[2] - p[2])] for q in nb(p) if q in power} | adj(p)
        if len(sides) == 1:                       # un extremo suelto apunta en línea recta (hacia el pistón)
            sides.add(OPP[next(iter(sides))])
        put(*p, "redstone_wire[" + ",".join(f"{d}={'side' if d in sides else 'none'}"
                                            for d in ("north", "south", "east", "west")) + f",power={power[p]}]")
        rec["polvo"].append((p, power[p]))
    return rec


def lever_trap(put, lever, block, dispenser, facing, arrows=16):
    """Palanca trampa: el dispensador, contiguo al bloque al que se fija la palanca, dispara al accionarla."""
    out = VDIR[(lever[0] - block[0], lever[2] - block[2])]
    put(*lever, f"lever[face=wall,facing={out},powered=false]")
    put(*dispenser, f"dispenser[facing={facing},triggered=false]",
        {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": arrows}]})


SLAB_RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # E, NE, N, NO, O, SO, S, SE
