"""Auditoría propia del castillo: recorrido a pie (ida y vuelta) desde el puente, puertas, cofres, escaleras,
salas ocultas que solo se abren con su mecanismo, redstone en reposo y nada flotando."""
from collections import deque
from core import parse_state
from .._comun.piezas import walk_graph, bn, passable
from .mazmorra import OFF
from . import superficie

INTEREST = ("chest", "barrel", "crafting_table", "furnace", "blast_furnace", "smoker", "brewing_stand", "composter",
            "fletching_table", "cauldron", "water_cauldron", "lava_cauldron", "lectern", "loom", "smithing_table",
            "grindstone", "anvil", "lever", "spawner", "note_block")


def resolved(t, off=(0, 0, 0)):
    out = {}
    for (x, y, z), (st, nbt) in t.blocks.items():
        if nbt and nbt.get("id") == "minecraft:jigsaw":
            st = nbt["final_state"]
        if bn(st) == "air":
            st = None
        out[(x + off[0], y + off[1], z + off[2])] = st
    return {k: v for k, v in out.items() if v is not None}, set(k for k, v in out.items() if v is None)


def combined(t, d, cmeta, dmeta, opened):
    a, air_a = resolved(t)
    b, _ = resolved(d, OFF)
    blocks = dict(b)
    blocks.update(a)
    if opened:
        secrets = [(cmeta["secret"]["estudio"], (0, 0, 0)), (dmeta["secret"]["tesoro"], OFF)]
        for info, o in secrets:
            sh = lambda p: (p[0] + o[0], p[1] + o[1], p[2] + o[2])
            door_state = blocks[sh(info["door"][0])]
            for p in info["door"]:
                blocks.pop(sh(p), None)
            for p in info["corner"]:
                blocks[sh(p)] = door_state
        for p in dmeta["breakable"]:
            blocks.pop((p[0] + OFF[0], p[1] + OFF[1], p[2] + OFF[2]), None)
    return blocks


def audit(t, d, cmeta, dmeta):
    errs = []
    start = cmeta["entrance"]
    bounds = (0, -16, 0, 99, 40, 99)
    opened = combined(t, d, cmeta, dmeta, True)
    closed = combined(t, d, cmeta, dmeta, False)
    S, back = walk_graph(opened, start, bounds)
    ok = set(S) & back
    Sc, backc = walk_graph(closed, start, bounds)
    okc = set(Sc) & backc

    def near(cells, p, r=1):
        x, y, z = p
        return any((x + dx, y + dy, z + dz) in cells for dx in range(-r, r + 1) for dz in range(-r, r + 1)
                   for dy in (-2, -1, 0, 1) if abs(dx) + abs(dz) <= r)

    one_way = set(S) - back
    if one_way:
        errs.append(f"celdas sin vuelta ({len(one_way)}), p. ej. {sorted(one_way)[:3]}")
    for p, st in opened.items():
        b = bn(st)
        if b in INTEREST or b.endswith("_bed") and "part=foot" in st:
            if not near(ok, p, 2 if b == "spawner" else 1):
                errs.append(f"{b} inaccesible en {p}")
        elif b.endswith("_door") and "half=lower" in st:
            f = parse_state(st)[1]["facing"]
            dx, dz = (0, 1) if f in ("north", "south") else (1, 0)
            x, y, z = p
            sides = [any((x + s * dx, y + k, z + s * dz) in ok for k in (-1, 0)) for s in (1, -1)]
            if not all(sides):
                errs.append(f"puerta sin salida en {p}")
        elif b == "ladder" and p not in ok and (p[0], p[1] + 1, p[2]) not in ok:
            errs.append(f"escalera de mano inaccesible en {p}")
    hidden = [cmeta["hidden_chest"], tuple(a + b for a, b in zip(dmeta["premium"], OFF)),
              tuple(a + b for a, b in zip(dmeta["niche"], OFF))]
    for p in hidden:
        if near(okc, p):
            errs.append(f"sala oculta alcanzable sin abrirla: {p}")
        if not near(ok, p):
            errs.append(f"sala oculta inalcanzable incluso abierta: {p}")
    for k, p in dmeta["levers"].items():
        if not near(okc, tuple(a + b for a, b in zip(p, OFF))):
            errs.append(f"palanca {k} inaccesible")
    if not near(okc, cmeta["secret"]["estudio"]["lever"]):
        errs.append("palanca del estudio inaccesible")
    # redstone en reposo
    for name, tt in (("castillo", t), ("mazmorra", d)):
        for p, (st, nbt) in tt.blocks.items():
            b = bn(st)
            props = parse_state(st)[1]
            if b == "redstone_wire" and props["power"] != "0" or b == "lever" and props["powered"] != "false":
                errs.append(f"{name}: redstone encendida en reposo {p}")
            if b == "sticky_piston":
                dx, dz = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}[props["facing"]]
                head = tt.get(p[0] + dx, p[1], p[2] + dz)
                if props["extended"] == "true" and bn(head) != "piston_head":
                    errs.append(f"{name}: pistón extendido sin cabeza {p}")
                src = [tt.get(p[0] + a, p[1] + c, p[2] + e) for a, c, e in
                       ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0))]
                below_s = [tt.get(p[0] + a, p[1] - 1, p[2] + e) for a, c, e in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))]
                if not any(bn(s) == "redstone_torch" for s in src) and not any(bn(s) == "redstone_torch" for s in below_s):
                    errs.append(f"{name}: pistón sin alimentación en reposo {p}")
    # nada flotando: todo bloque conectado con la base
    for name, tt in (("castillo", t), ("mazmorra", d)):
        solid = {p for p, (st, _) in tt.blocks.items() if bn(st) not in ("air", "water")}
        seen = {p for p in solid if p[1] == 0}
        q = deque(seen)
        while q:
            x, y, z = q.popleft()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if n in solid and n not in seen:
                    seen.add(n)
                    q.append(n)
        loose = solid - seen
        if loose:
            errs.append(f"{name}: {len(loose)} bloques flotando, p. ej. {sorted(loose)[:3]}")
    return errs, dict(S=S, ok=ok, okc=okc, opened=opened, closed=closed)


def ruin_share(t):
    """Fracción esperada de la superficie vista en mal estado (procesador incluido)."""
    PROB = {"stone_bricks": 0.15 + 0.85 * 0.1, "cobblestone": 0.2}
    RUIN = ("cracked_", "mossy_", "cobweb", "vine", "gravel")
    exp, n = 0.0, 0
    for (x, y, z), (st, _) in t.blocks.items():
        b = bn(st)
        if b in ("air", "water") or y < superficie.G:
            continue
        if not any(passable(t.get(*q)) for q in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y, z + 1), (x, y, z - 1))):
            continue
        n += 1
        exp += 1.0 if b.startswith(RUIN) or b in RUIN else PROB.get(b, 0.0)
    return exp / max(n, 1)
