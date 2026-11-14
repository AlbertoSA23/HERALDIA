"""Auditoría de diseño: jigsaws íntegros, apoyos, puertas con salida, escaleras completas y accesos."""
from collections import deque, Counter
from core import parse_state

PASS_WORDS = ("_carpet", "torch", "_banner", "rail", "pressure_plate", "button",
              "ladder", "_door", "poppy", "dandelion", "allium", "azure_bluet", "tulip", "orchid", "cornflower",
              "oxeye", "lily_of_the_valley", "rose_bush", "fern", "dead_bush", "sweet_berry", "wheat", "carrots",
              "potatoes", "beetroots", "cobweb", "lily_pad", "vine", "_sign", "short_grass", "lever", "tripwire")


def bname(st):
    return st.split("[")[0].replace("minecraft:", "") if st else None


def passable(st):
    if st is None:
        return True
    b = bname(st)
    if b in ("air", "structure_void", "water", "jigsaw_pass"):
        return True
    if "trapdoor" in b:
        return "open=true" in st
    if "fence_gate" in b:
        return True
    if b.endswith("_leaves") or b.endswith("_wall") or b.endswith("_fence") or b.endswith("_pane") or b == "iron_bars":
        return False
    return any(w in b for w in PASS_WORDS)


def top_height(st):
    """Altura de la superficie pisable dentro del bloque (None = no se pisa)."""
    if st is None:
        return None
    b = bname(st)
    if passable(st) and "_carpet" not in b:
        return None
    if "_carpet" in b:
        return 0.0
    if b.endswith("_slab"):
        return 0.5 if "type=bottom" in st else 1.0
    if b.endswith("_stairs"):
        return 0.5 if "half=bottom" in st else 1.0
    if b.endswith("_fence") or b.endswith("_wall") or "fence_gate" in b:
        return 1.5
    if "trapdoor" in b:
        return 1.0 if "half=top" in st else 0.2
    if "_bed" in b:
        return 0.56
    if b in ("lantern", "soul_lantern", "candle", "flower_pot", "bell", "brewing_stand", "campfire", "iron_chain",
             "decorated_pot", "lightning_rod", "skeleton_skull", "grindstone", "lectern", "composter",
             "cauldron", "water_cauldron", "lava_cauldron", "anvil", "stonecutter") or b.startswith("potted_"):
        return 1.5      # obstáculo: no se camina por encima
    return 1.0


def solid_full(st):
    if st is None:
        return False
    h = top_height(st)
    b = bname(st)
    return h == 1.0 and not b.endswith("_stairs") or b.endswith("_stairs") or (b.endswith("_slab") and "type=top" in st) \
        or (b.endswith("_slab") and "type=double" in st)


LADDER_BACK = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}
NEEDS_FLOOR = ("_carpet", "candle", "flower_pot", "potted_", "_door", "rail", "pressure_plate", "wheat", "carrots",
               "potatoes", "beetroots", "poppy", "dandelion", "allium", "azure_bluet", "tulip", "orchid",
               "cornflower", "oxeye", "lily_of_the_valley", "fern", "dead_bush", "sweet_berry", "brewing_stand",
               "campfire", "cauldron", "lectern", "composter", "decorated_pot", "skeleton_skull",
               "grindstone", "anvil", "short_grass", "lily_pad")
PLANT_SOIL = {"grass_block", "dirt", "coarse_dirt", "podzol", "farmland", "moss_block", "rooted_dirt", "mud"}
FLOWERS = ("poppy", "dandelion", "allium", "azure_bluet", "tulip", "orchid", "cornflower", "oxeye",
           "lily_of_the_valley", "fern", "sweet_berry", "short_grass", "rose_bush")


def prop(st, k):
    return parse_state(st)[1].get(k)


def resolved(t):
    """Vista de la pieza con cada jigsaw sustituido por su estado final."""
    class V:
        pass
    v = V()
    blocks = dict(t.blocks)
    for pos, (st, nbt) in t.blocks.items():
        if nbt and nbt.get("id") == "minecraft:jigsaw":
            fs = nbt["final_state"]
            blocks[pos] = (None if "structure_void" in fs else fs, None)
    for p in getattr(t, "solved_open", ()):   # puertas de puzle: se auditan abiertas (resueltas)
        blocks.pop(p, None)
    v.blocks = {p: b for p, b in blocks.items() if b[0] is not None}
    v.get = lambda x, y, z: (v.blocks.get((x, y, z)) or (None,))[0]
    v.jigsaws = t.jigsaws
    v.bounds = t.bounds
    v.orig = t
    return v


def support_issues(t):
    out = []
    for j in t.jigsaws:
        st = t.get(*j["pos"])
        if st is None or bname(st) != "jigsaw":
            out.append(("jigsaw sobrescrito", j["pos"]))
    terrain = any(k in t.name for k in ("/streets/", "/avenues/", "/terminators/end", "/decor/"))
    t = resolved(t)
    g = t.get
    for (x, y, z), (st, nbt) in t.blocks.items():
        b = bname(st)
        below, above = g(x, y - 1, z), g(x, y + 1, z)
        if "lantern" in b:
            if prop(st, "hanging") == "true":
                if above is None or passable(above) and "iron_chain" not in above:
                    out.append(("farol colgante sin techo", (x, y, z)))
            elif (below is None and y > 0) or bname(below) == "air":
                out.append(("farol de pie sin apoyo", (x, y, z)))
        elif b == "iron_chain":
            if above is None or bname(above) == "air":
                out.append(("cadena sin enganche", (x, y, z)))
            if below is None or bname(below) == "air":
                out.append(("cadena sin nada colgado", (x, y, z)))
        elif b == "ladder":
            dx, dz = LADDER_BACK[prop(st, "facing")]
            back = g(x + dx, y, z + dz)
            if back is None or passable(back):
                out.append(("escalera de mano sin pared detrás", (x, y, z)))
        elif "wall_banner" in b or b == "wall_torch":
            dx, dz = LADDER_BACK[prop(st, "facing")]
            back = g(x + dx, y, z + dz)
            if back is None or passable(back):
                out.append((b + " sin pared", (x, y, z)))
        elif b.endswith("_door") and prop(st, "half") == "upper":
            continue
        elif b == "bell":
            if prop(st, "attachment") == "ceiling" and (above is None or passable(above)):
                out.append(("campana sin viga", (x, y, z)))
            if prop(st, "attachment") == "floor" and (below is None or passable(below)):
                out.append(("campana sin apoyo", (x, y, z)))
        elif b.endswith("_leaves"):
            continue
        elif any(w in b for w in NEEDS_FLOOR) or b.endswith("_fence") or b.endswith("_banner"):
            ground_ok = below is None and (y == 0 or (y == 1 and terrain))
            if b.endswith("_fence") and above is not None and bname(above).endswith("_fence"):
                ground_ok = True
            if not ground_ok and (below is None or bname(below) in ("air", "structure_void") or (
                    passable(below) and "_fence" not in below and bname(below) not in ("water",))):
                if not (b.endswith("_fence") and any(g(x + a, y, z + c) and bname(g(x + a, y, z + c)).endswith("_fence")
                                                     for a, c in ((1, 0), (-1, 0), (0, 1), (0, -1)))):
                    if y > 0 or b not in ("rail",):
                        out.append((b + " sin apoyo", (x, y, z)))
        if b in ("wheat", "carrots", "potatoes", "beetroots") and bname(below) != "farmland":
            out.append(("cultivo fuera de tierra labrada", (x, y, z)))
        if not b.startswith("potted_") and any(w in b for w in FLOWERS) and "half=upper" not in st \
                and bname(below) not in PLANT_SOIL:
            out.append((b + " sobre suelo donde no vive", (x, y, z)))
        if b == "dead_bush" and bname(below) not in PLANT_SOIL | {"sand", "red_sand", "terracotta"}:
            out.append(("dead_bush sobre suelo donde no vive", (x, y, z)))
        if b == "lily_pad" and bname(below) != "water":
            out.append(("nenúfar fuera del agua", (x, y, z)))
        if b.endswith("_stairs") and y > 0 and "half=bottom" in st and (below is None or bname(below) == "air") \
                and (above is None or passable(above)) and "roof" not in b:
            sides = sum(1 for a, c2 in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if g(x + a, y, z + c2) is not None and not passable(g(x + a, y, z + c2)))
            if sides == 0:
                out.append(("peldaño suelto en el aire", (x, y, z)))
    return out


# ---------------------------------------------------------------- recorrido a pie
FACE = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}


def walk(t, extra_ground=True):
    """Celdas (x, y, z) donde puede estar de pie un jugador que entra por el acceso de la pieza,
    sin saltar ni romper bloques. Devuelve {celda: altura de los pies}."""
    t = resolved(t)
    g = t.get
    x0, y0, z0, x1, y1, z1 = t.bounds()

    def surf(x, y, z, mdx=0, mdz=0):
        """(altura al entrar, altura de apoyo) con los pies en la celda y, o None."""
        st = g(x, y, z)
        h = top_height(st)
        b = bname(st) if st else None
        if st is not None and b.endswith("_stairs") and "half=bottom" in st:
            fx, fz = FACE[prop(st, "facing")]
            low = (mdx, mdz) == (fx, fz)            # se entra por el lado bajo subiendo
            return (y + 0.5 if low else y + 1.0, y + 1.0)
        if h is not None and h <= 0.6:
            return (y + h, y + h)
        if h is not None:
            return None
        below = g(x, y - 1, z)
        if below is None:
            return (float(y), float(y)) if (extra_ground and y - 1 < 0) else None
        hb = top_height(below)
        if hb is None:
            return (float(y), float(y)) if bname(below) in ("ladder", "water") else None
        if hb != 1.0 or (bname(below).endswith("_stairs") and "half=bottom" in below):
            return None
        return (float(y), float(y))

    def headroom(x, y, z, s):
        top = s + 1.8
        cy = y if s < y + 1 else y + 1
        while cy < top:
            st = g(x, cy, z)
            if cy == y:
                cy += 1
                continue
            if not passable(st):
                lowpart = cy + (0.5 if ("half=top" in st or "type=top" in st) else 0.0)
                if lowpart < top:
                    return False
            cy += 1
        return True

    seen = {}
    q = deque()
    for j in t.jigsaws:
        if j["name"] in ("heraldia:entrance", "heraldia:street", "heraldia:avenue"):
            x, y, z = j["pos"]
            st = g(x, y, z)
            if st is None or passable(st):
                seen[(x, y, z)] = float(y)
            else:
                seen[(x, y + 1, z)] = float(y + 1)
            q.append(next(iter([k for k in seen if k[0] == x and k[2] == z])))
    while q:
        x, y, z = q.popleft()
        s = seen[(x, y, z)]
        cand = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if not (x0 - 1 <= nx <= x1 + 1 and z0 - 1 <= nz <= z1 + 1):
                continue
            for ny in range(y + 2, y - 5, -1):
                r = surf(nx, ny, nz, dx, dz)
                if r is None:
                    continue
                enter, stand = r
                if enter - s > 0.6 or stand > s + 1.01:
                    continue
                if not headroom(nx, ny, nz, stand):
                    continue
                # el paso debe estar libre a la altura del cuerpo
                cand.append((nx, ny if stand < ny + 1 else ny + 1, nz, stand))
                break
        here = g(x, y, z)
        if bname(here) == "ladder" or bname(g(x, y + 1, z)) == "ladder" or bname(g(x, y - 1, z)) == "ladder":
            for ny in (y + 1, y - 1):
                st = g(x, ny, z)
                if bname(st) == "ladder" or (bname(here) == "ladder" and passable(st)):
                    cand.append((x, ny, z, float(ny)))
        for (nx, ny, nz, ns) in cand:
            if (nx, ny, nz) not in seen:
                seen[(nx, ny, nz)] = ns
                q.append((nx, ny, nz))
    return seen


INTEREST = ("chest", "barrel", "crafting_table", "furnace", "blast_furnace", "smoker", "cartography_table",
            "brewing_stand", "composter", "fletching_table", "cauldron", "lectern", "stonecutter", "loom",
            "smithing_table", "grindstone", "anvil", "bell")


def access_issues(t):
    out = []
    if not any(j["name"] in ("heraldia:entrance", "heraldia:street", "heraldia:avenue") for j in t.jigsaws):
        return out
    seen = walk(t)
    cells = set(seen)
    t = resolved(t)

    def near(x, y, z, r=1):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                for dy in (-1, 0, 1):
                    if abs(dx) + abs(dz) <= r and (x + dx, y + dy, z + dz) in cells:
                        return True
        return False

    g = t.get
    for (x, y, z), (st, nbt) in t.blocks.items():
        b = bname(st)
        if b.endswith("_door") and prop(st, "half") == "lower":
            f = prop(st, "facing")
            dx, dz = (0, 1) if f in ("north", "south") else (1, 0)
            a = (x + dx, y, z + dz) in cells or (x + dx, y - 1, z + dz) in cells
            c = (x - dx, y, z - dz) in cells or (x - dx, y - 1, z - dz) in cells
            if not (a and c):
                out.append(("puerta sin salida o sin acceso", (x, y, z)))
        elif b == "ladder":
            if bname(g(x, y + 1, z)) != "ladder":
                # final de la escalera: debe dar a un suelo
                if not any((x + dx, y + 1, z + dz) in cells or (x + dx, y, z + dz) in cells
                           for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0))) or \
                        not any((x + dx, yy, z + dz) in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                for yy in (y, y + 1)):
                    out.append(("escalera de mano que no lleva a ningún sitio", (x, y, z)))
            if (x, y, z) not in cells:
                out.append(("escalera de mano inaccesible", (x, y, z)))
        elif b in INTEREST:
            hanging = bname(g(x, y + 1, z)) == "iron_chain" or prop(st, "attachment") == "ceiling"
            if not hanging and not near(x, y, z):
                out.append((b + " inaccesible", (x, y, z)))
    for j in t.jigsaws:
        if j["name"] == "heraldia:slot" and "villagers" in j["pool"]:
            x, y, z = j["pos"]
            if not near(x, y + 1, z, 1) and (x, y + 1, z) not in cells:
                out.append(("cama/aldeano inaccesible", (x, y, z)))
    return out


def lint_registry(reg, only=None):
    res = {}
    for name, t in reg.templates.items():
        if only and not only(name):
            continue
        iss = support_issues(t) + access_issues(t)
        if iss:
            res[name] = iss
    return res


def summarize(res):
    c = Counter()
    ex = {}
    for name, iss in res.items():
        kind = "/".join(name.split("/")[1:])
        for msg, pos in iss:
            c[(kind, msg)] += 1
            ex.setdefault((kind, msg), (name, pos))
    return c, ex
