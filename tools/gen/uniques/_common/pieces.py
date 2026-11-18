"""Common pieces of the unique structures: all end up in a consistent state when placed (without depending on
block updates that do not happen during generation)."""
from core import B, F, adult, anchored

DIRV = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
VDIR = {v: k for k, v in DIRV.items()}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}


def text(key, fallback):
    return {"translate": key, "fallback": fallback}


# ------------------------------------------------------------------ block entities
def spawner(put, x, y, z, mob, potentials=False, light=None):
    """Spawner for a single mob type. `light` (max. block light, 0-15) adds custom_spawn_rules so that
    the monsters spawn even if there is some light nearby (by default they require block light 0)."""
    e = {"entity": {"id": "minecraft:" + mob}}
    if light is not None:
        e["custom_spawn_rules"] = {"block_light_limit": {"min_inclusive": 0, "max_inclusive": light},
                                   "sky_light_limit": {"min_inclusive": 0, "max_inclusive": 15}}
    nbt = {"id": "minecraft:mob_spawner", "SpawnData": e}
    if potentials:
        nbt["SpawnPotentials"] = [{"weight": 1, "data": e}]
    put(x, y, z, "spawner", nbt)


def chest(put, x, y, z, facing, loot, kind="chest", waterlogged=False):
    """Chest or barrel with a loot table; `waterlogged` for a chest underwater."""
    st = f"barrel[facing={facing}]" if kind == "barrel" else f"{kind}[facing={facing}]"
    if waterlogged:
        st = st[:-1] + ",type=single,waterlogged=true]"
    put(x, y, z, st, {"id": "minecraft:" + ("barrel" if kind == "barrel" else kind), "LootTable": loot})


def sign(put, x, y, z, facing, lines, wood="dark_oak"):
    """Waxed wall sign; `lines`: up to 4 text components (translate + fallback)."""
    msgs = list(lines) + [{"text": ""}] * (4 - len(lines))
    put(x, y, z, f"{wood}_wall_sign[facing={facing}]",
        {"id": "minecraft:sign", "is_waxed": B(1),
         "front_text": {"messages": msgs, "color": "black", "has_glowing_text": B(0)},
         "back_text": {"messages": [{"text": ""}] * 4, "color": "black", "has_glowing_text": B(0)}})


GUARDIAN_TAG = "heraldia_guardian"   # tag (Tags) of every final guardian; the generator adds heraldia_guardian.<id>


def guardian(mob, key, fallback, health, armor=None, equipment=None, drop_chances=None, death_loot=None,
             attributes=None, extra=None):
    """NBT of a named, persistent guardian with moderate attributes. `attributes` {id: base} adds
    attributes (attack_damage, knockback_resistance...); `extra` is merged into the NBT (its `Tags` are added to that of
    guardian, GUARDIAN_TAG, which the advancements use: pack.py also adds that of the structure). The types that could spawn
    as babies also get core.ADULT_TAG (the NBT's IsBaby is not enough: finalizeSpawn ignores it), and all get core.ANCHORED_TAG
    (they do not wander outside their room until attacked, nor pick up items)."""
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
    extra = dict(extra or {})
    n["Tags"] = [GUARDIAN_TAG] + [t for t in extra.pop("Tags", []) if t != GUARDIAN_TAG]
    n.update(extra)
    # Zombies, husks and drowned: never babies (core.ADULT_TAG). All: stay still in their room until attacked and without
    # recoger objetos (core.ANCHORED_TAG).
    return anchored(adult(n), always=True)


# ------------------------------------------------------------------ redstone
def piston_door(put, door, axis, side, block):
    """Secret door: each block of `door` (x, y, z) is held by an EXTENDED sticky piston located two
    cells away in the direction `axis` (dx, dz), with the head between them facing `side`. The power (lever, torch...)
    is supplied by the caller; when it is removed, the pistons retract the blocks and leave the door open."""
    ax, az = axis
    for (x, y, z) in door:
        put(x, y, z, block)
        put(x + ax, y, z + az, f"piston_head[facing={side},short=false,type=sticky]")
        put(x + 2 * ax, y, z + 2 * az, f"sticky_piston[extended=true,facing={side}]")


def wire(put, path, y=None, ends=()):
    """Unpowered redstone dust along `path` [(x, z)...] at height `y`, or [(x, y, z)...] with one-block
    steps (the lower dust "climbs" to the upper one; the caller leaves air above the lower dust).
    `ends` gives, for the first and the last, the extra direction it points to."""
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
        if len(sides) == 1:                       # a loose segment points in a straight line
            sides[OPP[next(iter(sides))]] = "side"
        put(x, py, z, "redstone_wire[" + ",".join(f"{d}={sides.get(d, 'none')}"
                                                   for d in ("north", "south", "east", "west")) + ",power=0]")


def comparator(put, x, y, z, facing):
    """Unpowered comparator that reads the block at `facing` and outputs to the opposite side."""
    put(x, y, z, f"comparator[facing={facing},mode=compare,powered=false]", {"id": "minecraft:comparator", "OutputSignal": 0})


def tripwire_trap(put, hook_a, hook_b, y, along, dispensers, arrows=6):
    """Tripwire trap (jungle temple): hooks at hook_a and hook_b (x, z) joined in a straight line along
    `along` ('x' or 'z'); each dispenser ((x, y, z), facing) sits next to the block a hook is attached to."""
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
    """Closed two-block door (also iron: it opens when it receives a signal)."""
    for h, dy in (("lower", 0), ("upper", 1)):
        put(x, y + dy, z, f"{kind}[facing={facing},half={h},hinge={hinge},open=false,powered=false]")


def double_door(put, x, y, z, facing, side, kind="spruce_door"):
    """Closed double door: one leaf at (x, y, z) and the other in the adjacent cell toward `side` (horizontal direction
    perpendicular to `facing`). Both with the same `facing` and the hinge on the outer side (`lint.door_hinge`),
    so that they open mirrored and do not collide. `lint.door_pair_issues` audits all the pairs."""
    from lint import FACE, OPPOSITE, door_hinge
    dx, dz = FACE[side]
    door(put, x, y, z, facing, kind, door_hinge(facing, side))
    door(put, x + dx, y, z + dz, facing, kind, door_hinge(facing, OPPOSITE[side]))


def tnt_trap(put, x, y, z, plate="stone_pressure_plate", warn=None):
    """Pressure plate trap (desert temple): plate at (x, y, z) on the floor and TNT two blocks below;
    `warn` [(x, y, z)] receives cracked bricks as a warning."""
    put(x, y, z, f"{plate}[powered=false]")
    put(x, y - 2, z, "tnt[unstable=false]")
    for p in warn or ():
        put(*p, "cracked_stone_bricks")


def lever_door(put, door, slide, face, block, wall):
    """Flush 1 x 2 secret door at the back of a niche, with its lever (Colosseum, tested on a server).

    door: lower block of the door; slide: direction (inside the wall) toward which it retracts; face: direction of
    the room, where the niche and the lever are. It uses `piston_door` and powers it with a redstone torch on the hidden
    face of the lever's block (and the solid block above for the upper piston): lever on ->
    torch off -> the door opens. The rest of the wall is placed by the caller. Returns the positions and the state
    with the door open (pos -> state) to audit the walkthrough."""
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
    """Arrow plate trap: each plate (x, y, z) activates the two floor-level dispensers on
    its sides (`side` and its opposite), which fire toward it."""
    for (x, y, z) in plates:
        put(x, y, z, f"{plate}[powered=false]")
        for d in (side, OPP[side]):
            a, c = DIRV[d]
            put(x + a, y, z + c, f"dispenser[facing={OPP[d]},triggered=false]",
                {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": arrows}]})


def item_frame(x, y, z, facing_byte, item=None):
    """NBT of a frame: without `block_pos` the game discards the entity when the template is placed."""
    n = {"id": "minecraft:item_frame", "Facing": B(facing_byte), "block_pos": [x, y, z]}
    if item:
        n["Item"] = {"id": "minecraft:" + item, "count": 1}
    return n


# ------------------------------------------------------------------ escalera de caracol
RING = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
HOLES = (RING[5], RING[6])
GUARD = [(-2, 0), (-2, 1), (-2, 2), (-1, 2)]


def spiral_stair(put, cx, cz, feet, stair, newel, landing, newel_top=None):
    """One-cell spiral staircase around a 1x1 pillar at (cx, cz): six steps per flight of 6 in
    height and a two-cell landing to the north. `feet`: feet heights of each exit floor (every 6). It opens the
    stairwell hole in the arrival floor (HOLES) and returns the cells to protect with a railing (GUARD) relative to the axis.
    Each flight is a spiral_continuous of 6 steps with inverted riser."""
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
    """(y, type) of the slab whose surface is at height s (a multiple of 0.5)."""
    return (int(s) - 1, "top") if s == int(s) else (int(s - 0.5), "bottom")


def spiral_slabs(put, nx, nz, s0, s1, phase, slab, ring=None, props=",waterlogged=false"):
    """Continuous 3 x 3 slab spiral around a pillar at (nx, nz) (placed by the caller): each step rises
    half a block, from feet s0 to s1, without landings. Step i occupies ring[(i + phase) % 8] (by default RING8,
    clockwise; SLAB_RING, counterclockwise); `phase` chooses the side of each exit and `props` adds properties to the
    slab state. Returns [(i, x, z, feet)]; the y of each slab is slab_y(feet)[0]."""
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
    """Cells (x, z) of a circle of radius r."""
    R = int(r) + 1
    return [(cx + dx, cz + dz) for dx in range(-R, R + 1) for dz in range(-R, R + 1) if dx * dx + dz * dz <= r * r]


def spiral_continuous(put, ring, y0, n, stair, support=None, start=0, under=False):
    """Continuous spiral of `n` steps from y0 through the adjacent cells of `ring` (absolute, around a
    pillar), starting at ring[start], without landings of its own: useful when the floors are not every 6 and the landings
    are outside the ring. Each step faces where you arrive from, so at the corners you also enter from the
    low side; the corner ones do not touch the pillar and carry `support` below; with `under`, all but the first
    carry an inverted step below. Returns the positions of the steps."""
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
    """NBT of a painting for Template.entity: `facing` in 2D code and `block_pos` as IntArray (verified in 26.3;
    1x2 occupies the cell and the one above)."""
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
    """Fences, glass panes, bars and stone walls connect to their neighbors (the game does not update them when placing)."""
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
            with_it = same or full(o)
            props[d] = ("low" if with_it else "none") if fam == "wall" else ("true" if with_it else "false")
        if fam == "wall":
            ns, ew = props["north"] != "none" and props["south"] != "none", props["east"] != "none" and props["west"] != "none"
            straight = (ns and props["east"] == props["west"] == "none") or (ew and props["north"] == props["south"] == "none")
            props["up"] = "false" if straight else "true"
        props["waterlogged"] = "false"
        t.blocks[(x, y, z)] = (f"minecraft:{b}[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]", nbt)


# ------------------------------------------------------------------ cathedral additions
def combo_door(put, door, axis, sign, levers, name="", block=None):
    """Combination secret door (several levers; with only one, better lever_door): two blocks (door = lower
    block) with their power supply: two extended sticky pistons
    (like piston_door) and, for each lever [(lever, block it is attached to)], a redstone torch on the other side
    of that block (inverter) that powers a line of dust at the height of the upper piston, in the door layer.
    The door opens only with all the levers activated.

    With several levers, the torches go in an intermediate layer, next to the line and not inside it: a torch
    in the line cuts it into segments and only its segment reaches the piston (it would open with a single lever). Thus, a wall
    four blocks thick: levers | torches | door, pistons and dust | opposite face. With one lever a three-block
    wall is enough (the torch closes the line). The dust has its shape and power written explicitly.
    axis 'x' or 'z' and sign ±1: which way the pistons lie. With `block`, the door and its pistons come from
    piston_door; without it, the door block is placed by the caller.
    Returns a record with positions (door, heads, pistons, torches, dust, levers)."""
    x, y, z = door
    step = (sign, 0) if axis == "x" else (0, sign)
    pos = lambda k, dy=0: (x + step[0] * k, y + dy, z + step[1] * k)
    toward = VDIR[(-step[0], -step[1])]
    rec = {"tipo": "puerta de pistones", "sitio": name, "puerta": [pos(0), pos(0, 1)],
           "cabezas": [pos(1), pos(1, 1)], "pistones": [pos(2), pos(2, 1)], "antorchas": [], "polvo": [],
           "palancas": [], "falsas": []}
    if block:
        piston_door(put, [pos(0), pos(0, 1)], step, toward, block)
    else:                                     # the door is placed by the caller
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
        if len(sides) == 1:                       # a loose end points in a straight line (toward the piston)
            sides.add(OPP[next(iter(sides))])
        put(*p, "redstone_wire[" + ",".join(f"{d}={'side' if d in sides else 'none'}"
                                            for d in ("north", "south", "east", "west")) + f",power={power[p]}]")
        rec["polvo"].append((p, power[p]))
    return rec


def lever_trap(put, lever, block, dispenser, facing, arrows=16):
    """Trap lever: the dispenser, adjacent to the block the lever is attached to, fires when it is pulled."""
    out = VDIR[(lever[0] - block[0], lever[2] - block[2])]
    put(*lever, f"lever[face=wall,facing={out},powered=false]")
    put(*dispenser, f"dispenser[facing={facing},triggered=false]",
        {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": arrows}]})


SLAB_RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # E, NE, N, NW, W, SW, S, SE


def open_stairwells(t):
    """Lengthens the stairwell hole where the floor above is 3 blocks from the previous step that the player keeps
    climbing (`lint.stair_headroom_issues`, "on the way up"): when moving to the next step the player's body
    (1.8 tall) is still over that step and the head reaches +3.3. It removes the block (x, y + 3, z) from the finished
    template; if it is a block with data or a jigsaw, it fails instead of breaking it. Returns the opened positions."""
    import lint
    open_ones = []
    for msg, (x, y, z) in lint.stair_headroom_issues(t):
        if msg != "escalera con techo bajo en la subida":
            continue
        st, nbt = t.blocks.get((x, y + 3, z), (None, None))
        if nbt is not None or lint.bname(st) == "jigsaw":
            raise ValueError(f"{t.name}: the low ceiling of the staircase at {(x, y, z)} is a block with data")
        cavity = t.get(x, y + 2, z)      # same medium as the hollow below (air or water); without a block the terrain is not preserved
        t.set(x, y + 3, z, cavity if lint.bname(cavity) in ("air", "water", "cave_air") else "minecraft:air")
        open_ones.append((x, y + 3, z))
        above, _ = t.blocks.get((x, y + 4, z), (None, None))
        b = lint.bname(above)
        if b and (b.endswith(("_fence", "_wall", "_pane")) or any(w in b for w in lint.NEEDS_FLOOR)):
            t.set(x, y + 4, z, "minecraft:air")     # railing or decoration that rested on the removed floor
            open_ones.append((x, y + 4, z))
    return open_ones
