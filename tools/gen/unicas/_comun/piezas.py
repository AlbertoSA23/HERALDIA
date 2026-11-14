"""Piezas comunes de las estructuras únicas: todas quedan en un estado coherente al colocarse (sin depender de
actualizaciones de bloque que no ocurren al generar)."""
from core import B, F

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
VDIR = {v: k for k, v in DIRV.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def text(key, fallback):
    return {"translate": key, "fallback": fallback}


# ------------------------------------------------------------------ entidades de bloque
def spawner(put, x, y, z, mob, potentials=False):
    """Generador de monstruos de un solo tipo."""
    e = {"entity": {"id": "minecraft:" + mob}}
    nbt = {"id": "minecraft:mob_spawner", "SpawnData": e}
    if potentials:
        nbt["SpawnPotentials"] = [{"weight": 1, "data": e}]
    put(x, y, z, "spawner", nbt)


def chest(put, x, y, z, facing, loot, kind="chest"):
    """Cofre o barril con tabla de botín."""
    st = f"barrel[facing={facing}]" if kind == "barrel" else f"{kind}[facing={facing}]"
    put(x, y, z, st, {"id": "minecraft:" + ("barrel" if kind == "barrel" else kind), "LootTable": loot})


def sign(put, x, y, z, facing, lines, wood="dark_oak"):
    """Cartel de pared encerado; `lines`: hasta 4 componentes de texto (translate + fallback)."""
    msgs = list(lines) + [{"text": ""}] * (4 - len(lines))
    put(x, y, z, f"{wood}_wall_sign[facing={facing}]",
        {"id": "minecraft:sign", "is_waxed": B(1),
         "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
         "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})


def guardian(mob, key, fallback, health, armor=None, equipment=None, drop_chances=None, death_loot=None):
    """NBT de un guardián con nombre, persistente y con atributos moderados."""
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


def wire(put, path, y, ends=()):
    """Polvo de redstone apagado a lo largo de `path` [(x, z)...]; `ends` da, para el primero y el último, la
    dirección extra a la que apunta (p. ej. hacia un comparador o hacia el bloque que alimenta)."""
    extra = dict(ends)
    for i, (x, z) in enumerate(path):
        sides = set()
        for j in (i - 1, i + 1):
            if 0 <= j < len(path):
                sides.add(VDIR[(path[j][0] - x, path[j][1] - z)])
        if i in extra:
            sides.add(extra[i])
        if len(sides) == 1:                       # un tramo suelto apunta en línea recta
            sides.add(OPP[next(iter(sides))])
        put(x, y, z, "redstone_wire[" + ",".join(f"{d}={'side' if d in sides else 'none'}"
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


def tnt_trap(put, x, y, z, plate="stone_pressure_plate", warn=None):
    """Trampa de losa (templo del desierto): placa en (x, y, z) sobre el suelo y TNT dos bloques más abajo;
    `warn` [(x, y, z)] recibe ladrillos agrietados como aviso."""
    put(x, y, z, f"{plate}[powered=false]")
    put(x, y - 2, z, "tnt[unstable=false]")
    for p in warn or ():
        put(*p, "cracked_stone_bricks")


# ------------------------------------------------------------------ escalera de caracol
RING = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
HOLES = (RING[5], RING[6])
GUARD = [(-2, 0), (-2, 1), (-2, 2), (-1, 2)]


def spiral_stair(put, cx, cz, feet, stair, newel, landing, newel_top=None):
    """Escalera de caracol de una casilla alrededor de un machón de 1x1 en (cx, cz): seis peldaños por tramo de 6 de
    altura y rellano de dos casillas al norte. `feet`: alturas de los pies de cada planta de salida (cada 6). Abre el
    hueco del forjado de llegada (HOLES) y devuelve las celdas a proteger con barandilla (GUARD) relativas al eje."""
    top = newel_top if newel_top is not None else feet[-1] + 6
    for y in range(feet[0] - 1, top + 1):
        put(cx, y, cz, newel)
    for f in feet:
        for k in range(2, 8):
            x, z = RING[k]
            px, pz = RING[k - 1]
            facing = VDIR[(x - px, z - pz)]
            put(cx + x, f + k - 2, cz + z, f"{stair}[facing={facing},half=bottom]")
            if k >= 3:
                put(cx + x, f + k - 3, cz + z, f"{stair}[facing={OPP[facing]},half=top]")
        for k in (0, 1):
            put(cx + RING[k][0], f - 1, cz + RING[k][1], landing)
        for (x, z) in HOLES:
            if f != feet[0]:
                put(cx + x, f - 1, cz + z, "air")
    for (x, z) in HOLES:
        put(cx + x, feet[-1] + 5, cz + z, "air")
    return GUARD


def spiral_continuous(put, ring, y0, n, stair, support=None):
    """Caracol continuo de `n` peldaños desde y0 por las casillas contiguas de `ring` (absolutas, alrededor de un
    machón), sin rellanos propios: sirve cuando las plantas no van cada 6 y los rellanos están fuera del anillo.
    Cada peldaño mira hacia donde se llega, así que en las esquinas también se entra por el lado bajo; los de
    esquina no tocan el machón y llevan `support` debajo. Devuelve las posiciones de los peldaños."""
    out, k = [], len(ring)
    for i in range(n):
        x, z = ring[i % k]
        px, pz = ring[(i - 1) % k]
        nx, nz = ring[(i + 1) % k]
        put(x, y0 + i, z, f"{stair}[facing={VDIR[(x - px, z - pz)]},half=bottom]")
        if support and i and (nx - x, nz - z) != (x - px, z - pz):
            put(x, y0 + i - 1, z, support)
        out.append((x, y0 + i, z))
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
