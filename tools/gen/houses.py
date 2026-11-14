"""Casas residenciales amuebladas."""
import math
from core import Template, nsid
from build import *
from core import DIRS
from lint import passable
from themes import roofset

PROFS_HOUSE = ["farmer", "fisherman", "shepherd", "fletcher", "leatherworker", "mason", "butcher",
               "toolsmith", "weaponsmith", "armorer", "librarian", "cartographer", "cleric"]

LOOT = {"comun": "heraldia:cofres/comun", "poco_comun": "heraldia:cofres/poco_comun",
        "raro": "heraldia:cofres/raro", "epico": "heraldia:cofres/epico"}


def pick_tier(rng, size):
    """Cofres equilibrados: no todas las casas tienen."""
    table = {"small": [(None, 70), ("comun", 22), ("poco_comun", 8)],
             "medium": [(None, 55), ("comun", 28), ("poco_comun", 14), ("raro", 3)],
             "large": [(None, 40), ("comun", 25), ("poco_comun", 23), ("raro", 10), ("epico", 2)]}[size]
    tot = sum(w for _, w in table)
    r = rng.uniform(0, tot)
    for k, w in table:
        r -= w
        if r <= 0:
            return k
    return None


def bed_slot(t, th, x, y, z, pool):
    """Hueco de cama: el pool coloca cama (+aldeano) o nada. La cama se extiende hacia +z."""
    t.jigsaw(x, y, z, "up_south", "heraldia:slot", "heraldia:bottom", pool, final_state=th["floor"], joint="aligned")
    t.set(x, y + 1, z, "air"); t.set(x, y + 1, z + 1, "air")


def villager_pool(th, prof, fixed=False):
    return nsid(f"villagers/{th['vtype']}/{'fixed_' if fixed else ''}{prof}")


class Room:
    """Asignador de huecos junto a los muros interiores."""

    def __init__(self, t, x0, z0, x1, z1, y, reserved=()):
        self.t, self.y = t, y
        self.x0, self.z0, self.x1, self.z1 = x0, z0, x1, z1
        self.used = set(reserved)

    def free(self, x, z):
        return (x, z) not in self.used and self.x0 <= x <= self.x1 and self.z0 <= z <= self.z1 \
            and self.t.is_free(x, self.y, z)

    def wall_cells(self):
        out = []
        for x in range(self.x0, self.x1 + 1):
            out.append((x, self.z1, "north"))
        for z in range(self.z1 - 2, self.z0, -1):
            out.append((self.x0, z, "east"))
            out.append((self.x1, z, "west"))
        for x in range(self.x0, self.x1 + 1):
            out.append((x, self.z0, "south"))
        return out

    def take(self, n=1, prefer=None):
        cells = self.wall_cells()
        if prefer:
            cells = [c for c in cells if c[2] == prefer] + [c for c in cells if c[2] != prefer]
        for (x, z, f) in cells:
            if self.free(x, z):
                self.used.add((x, z))
                return x, z, f
        return None

    def put(self, block, prefer=None, nbt=None):
        c = self.take(prefer=prefer)
        if not c:
            return None
        x, z, f = c
        st = facing_state(block, f)
        self.t.set(x, self.y, z, st, nbt)
        return c


def furnish(t, th, rng, room, *, prof=None, tier=None, kind="living", ceil=None, hearth=False, table_len=1):
    """Amuebla una estancia con criterio: todo va pegado a un muro, nada tapa ventanas y el centro queda libre
    salvo la mesa de comedor."""
    y = room.y
    items = []
    if prof:
        items.append(("ws", WORKSTATION[prof]))
    if tier:
        items.append(("chest", tier))
    if kind == "living":
        items += [("b", "crafting_table")] + ([] if hearth else [("b", "furnace")]) + [("shelf", None), ("pot", None)]
    elif kind == "bedroom":
        items += [("shelf", None), ("pot", None)]

    def window_behind(x, z, f, yy):
        dx, dz = DIRS[f]
        return "pane" in (t.get(x - dx, yy, z - dz) or "")

    for k, v in items:
        c = room.take(prefer="north" if k in ("ws", "chest") else None)
        if not c:
            continue
        x, z, f = c
        if k == "ws":
            t.set(x, y, z, facing_state(v, f))
        elif k == "chest":
            t.chest(x, y, z, f, LOOT[v])
        elif k == "shelf":
            t.set(x, y, z, "bookshelf")
            if ceil and ceil - y >= 2 and not window_behind(x, z, f, y + 1):
                t.set(x, y + 1, z, "bookshelf")
        elif k == "pot":
            t.set(x, y, z, f"{th['wslab']}[type=top]")
            t.set(x, y + 1, z, potted(rng.choice(th["plants"])))
        else:
            t.set(x, y, z, facing_state(v, f))
    cx, cz = (room.x0 + room.x1) // 2, (room.z0 + room.z1) // 2
    col = rng.choice(th["carpet"])
    if kind == "living" and table_len:
        # mesa de comedor centrada, con sillas enfrentadas y el respaldo hacia fuera
        zs = [cz] if table_len == 1 else [cz - 1, cz, cz + 1]
        if all(room.free(cx, z) for z in zs) and all(room.free(cx + d, z) for z in zs for d in (-1, 1)):
            for z in zs:
                table(t, th, cx, y, z)
                room.used.add((cx, z))
            for z in (zs if table_len == 1 else [zs[0], zs[-1]]):
                chair(t, th, cx - 1, y, z, "west")
                chair(t, th, cx + 1, y, z, "east")
                room.used |= {(cx - 1, z), (cx + 1, z)}
    else:
        # alfombra recogida en el centro
        for x in range(cx - 1, cx + 2):
            for z in range(cz - 1, cz + 2):
                if room.free(x, z):
                    t.set(x, y, z, f"{col}_carpet")
    if ceil:
        lz = cz if (kind != "living" or not table_len) else cz
        t.set(cx, ceil, lz, lantern(th, True))


def rect_house(th, rng, name, size, prof, tier):
    t = Template(name)
    s = th["stilts"]
    if th["shape"] == "long":
        W, D, floors = {"small": (7, 11, 1), "medium": (7, 13, 1), "large": (9, 15, 2)}[size]
    else:
        W, D, floors = {"small": (7, 7, 1), "medium": rng.choice([(9, 9, 1), (9, 11, 1), (9, 7, 2)]),
                        "large": rng.choice([(11, 11, 2), (9, 11, 2), (11, 9, 2)])}[size]
    dx = W // 2
    fy = s                      # cota del suelo
    zf = 2 + (s if s else 0)    # muro frontal
    zb = zf + D - 1
    H = 4 * floors - 1
    # --- acceso
    t.jigsaw(dx, 0, 0, "north_up", "heraldia:entrance", "heraldia:side", "minecraft:empty",
             final_state=stairs(th["trim"] if not s else th["wstairs"], "south"))
    if s:
        # escalera completa hasta el porche: peldaños con zanca por debajo y barandilla
        for k in range(1, s + 1):
            t.set(dx, k, k, stairs(th["wstairs"], "south"))
            t.set(dx, k - 1, k, stairs(th["wstairs"], "north", half="top"))
            for y in range(k + 1, k + 4):
                t.set(dx, y, k, "air")
        t.fill(dx - 1, fy, s + 1, dx + 1, fy, zf - 1, th["planks"])
        for px in (dx - 1, dx + 1):
            t.set(px, fy + 1, s + 1, th["fence"])
            for y in range(0, fy):
                t.set(px, y, s + 1, th["fence"])
        # pilotes
        for x in sorted(set(list(range(0, W, 4)) + [W - 1])):
            for z in sorted(set(list(range(zf, zb + 1, 4)) + [zb])):
                for y in range(0, fy):
                    t.set(x, y, z, log(th["log"], "y"))
    else:
        t.fill(dx - 1, 0, 1, dx + 1, 0, 1, th["found"])
        for px in (dx - 1, dx + 1):
            t.set(px, 1, 1, potted(rng.choice(th["plants"])))
    shutters = th["roof_type"] != "flat" and rng.random() < 0.55
    shed = (not s) and th["roof_type"] != "flat" and size != "small" and rng.random() < 0.45
    chimney = th["chimney"] and th["roof_type"] in ("gable", "steep") and rng.random() < 0.6
    # --- base y suelo
    t.fill(0, fy, zf, W - 1, fy, zb, log(th["found"], "y"))
    t.fill(1, fy, zf + 1, W - 2, fy, zb - 1, th["floor"])
    # --- muros
    rect_walls(t, th, 0, zf, W - 1, zb, fy, H)
    t.air(1, fy + 1, zf + 1, W - 2, fy + H, zb - 1)
    door(t, dx, fy + 1, zf, th["door"], "north")
    # --- ventanas (alineadas en ambas plantas)
    for fl in range(floors):
        wy = fy + 2 + 4 * fl
        front = windows_on_wall(t, th, 0, zf, W - 1, zb, "north", wy, rng, skip=[(dx, zf)])
        if fl == 0 and not s:
            for (wx, wz) in front:
                if abs(wx - dx) > 1:
                    t.set(wx, wy - 1, wz - 1, f"{th['trapdoor']}[facing=north,half=top,open=false]")
                    t.set(wx, wy, wz - 1, potted(rng.choice(th["plants"])))
        if shutters and fl > 0:
            for (wx, wz) in front:
                for sx in (wx - 1, wx + 1):
                    cur = t.get(sx, wy, wz) or ""
                    if t.get(sx, wy, wz - 1) is None and cur not in ("", "minecraft:air") and "pane" not in cur:
                        t.set(sx, wy, wz - 1, f"{th['trapdoor']}[facing=north,half=bottom,open=true]")
        windows_on_wall(t, th, 0, zf, W - 1, zb, "south", wy, rng,
                        skip=[(W - 2, zb)] if chimney else [])
        windows_on_wall(t, th, 0, zf, W - 1, zb, "west", wy, rng)
        windows_on_wall(t, th, 0, zf, W - 1, zb, "east", wy, rng)
    # --- forjado y escalera de mano
    if floors == 2:
        t.fill(1, fy + 4, zf + 1, W - 2, fy + 4, zb - 1, th["planks"])
        for y in range(fy + 1, fy + 5):
            t.set(1, y, zf + 1, "ladder[facing=east]")
    # --- techo interior y tejado
    t.fill(1, fy + H + 1, zf + 1, W - 2, fy + H + 1, zb - 1, th["planks"])
    top = roof_for(t, th, 0, zf, W - 1, zb, fy + H + 1)
    # --- cobertizo lateral: leñera baja que no tapa las ventanas
    if shed:
        ax0, ax1 = W, W + 2
        az0, az1 = zf + 1, min(zb - 1, zf + 4)
        t.fill(ax0, fy, az0, ax1, fy, az1, th["found"])
        for (px, pz) in ((ax1, az0), (ax1, az1)):
            for y in range(fy + 1, fy + 3):
                t.set(px, y, pz, th["fence"])
        for z in range(az0, az1 + 1):
            t.set(ax0, fy + 3, z, f"{th['roof_slab']}[type=top]")
            t.set(ax0 + 1, fy + 3, z, f"{th['roof_slab']}[type=top]")
            t.set(ax1, fy + 3, z, f"{th['roof_slab']}[type=bottom]")
            t.set(ax0, fy + 1, z, log(th["log"], "x"))
        t.set(ax0 + 1, fy + 1, az1, "barrel[facing=up]")
    # --- tejado plano: vigas vistas y cúpula en las casas grandes
    if th["roof_type"] == "flat":
        ry = fy + H
        for x in range(1, W - 1, 2):
            if abs(x - dx) > 0:
                t.set(x, ry, zf - 1, log(th["stripped"], "z"))
            t.set(x, ry, zb + 1, log(th["stripped"], "z"))
        if size == "large" and th["dome"]:
            dome(t, W // 2, fy + H + 2, zf + D // 2, 2, roofset(th["dome"])[2], finial="lightning_rod[facing=up]")
    # --- farol bajo el alero junto a la puerta (solo si hay alero)
    for yy in range(fy + 3, fy + H + 3):
        above = t.get(dx + 1, yy + 1, zf - 1)
        if above and not passable(above) and t.get(dx + 1, yy, zf - 1) is None:
            t.set(dx + 1, yy, zf - 1, lantern(th, True))
            break
    t.fill(1, fy + H + 2, zf + 1, W - 2, top, zb - 1, "air", keep=True)
    # --- chimenea en la esquina del fondo, con el hogar abajo
    hx, hz = W - 2, zb - 1
    if chimney:
        cm = "bricks" if "brick" not in th["found"] else th["found"]
        for y in range(fy + 1, top + 2):
            t.set(hx, y, hz, cm)
        t.set(hx, top + 2, hz, "campfire[lit=true,signal_fire=false]")
        t.set(hx, fy + 1, hz, "furnace[facing=north]")
    # --- interior
    front_clear = {(dx, zf + 1), (dx - 1, zf + 1), (dx + 1, zf + 1), (dx, zf + 2)}
    reserved = set(front_clear)
    if chimney:
        reserved |= {(hx, hz), (hx, hz - 1)}
    if floors == 2:
        reserved |= {(1, zf + 1), (1, zf + 2), (2, zf + 1)}
    pool = villager_pool(th, prof)
    tl = 0 if size == "small" else (3 if (zb - zf) >= 9 else 1)
    bx, bz = 1, zb - 2                     # cama siempre en la esquina del fondo, lejos de la chimenea
    if floors == 1:
        bed_slot(t, th, bx, fy, bz, pool)
        reserved |= {(bx, bz), (bx, bz + 1), (bx + 1, bz), (bx + 1, bz + 1)}
        room = Room(t, 1, zf + 1, W - 2, zb - 1, fy + 1, reserved)
        furnish(t, th, rng, room, prof=prof, tier=tier, kind="living", ceil=fy + 3, hearth=chimney, table_len=tl)
    else:
        room = Room(t, 1, zf + 1, W - 2, zb - 1, fy + 1, reserved)
        furnish(t, th, rng, room, prof=prof, tier=None, kind="living", ceil=fy + 3, hearth=chimney, table_len=tl)
        uy = fy + 4
        ureserved = {(1, zf + 1), (1, zf + 2), (2, zf + 1), (2, zf + 2)}
        if chimney:
            ureserved |= {(hx, hz), (hx, hz - 1)}
        bed_slot(t, th, bx, uy, bz, pool)
        ureserved |= {(bx, bz), (bx, bz + 1), (bx + 1, bz), (bx + 1, bz + 1)}
        uroom = Room(t, 1, zf + 1, W - 2, zb - 1, uy + 1, ureserved)
        furnish(t, th, rng, uroom, tier=tier, kind="bedroom", ceil=uy + 3)
    return t


def round_house(th, rng, name, size, prof, tier):
    t = Template(name)
    r = {"small": 3, "medium": 4, "large": 5}[size]
    cx, cz = r + 1, r + 3
    fy = 0
    H = 4 if size != "large" else 5
    t.jigsaw(cx, 0, 0, "north_up", "heraldia:entrance", "heraldia:side", "minecraft:empty",
             final_state=stairs(th["trim"], "south"))
    t.fill(cx - 1, 0, 1, cx + 1, 0, cz - r - 1, th["found"])
    inside = []
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = math.sqrt(dx * dx + dz * dz)
            x, z = cx + dx, cz + dz
            if d <= r + 0.5:
                t.set(x, fy, z, th["found"] if d > r - 0.5 else th["floor"])
            if r - 0.5 < d <= r + 0.5:
                for y in range(fy + 1, fy + H + 1):
                    t.set(x, y, z, th["wall2"] if y == fy + 1 else th["wall"])
            elif d <= r - 0.5:
                for y in range(fy + 1, fy + H + 1):
                    t.set(x, y, z, "air")
                inside.append((x, z))
    door(t, cx, fy + 1, cz - r, th["door"], "north")
    for (wx, wz) in ((cx - r, cz), (cx + r, cz), (cx, cz + r)):
        t.set(wx, fy + 2, wz, th["window"])
    cone_roof(t, th, cx, cz, r, fy + H + 1)
    # interior: cama pegada al muro este, muebles pegados al muro oeste y al fondo, centro libre
    pool = villager_pool(th, prof)
    bed_slot(t, th, cx + r - 1, fy, cz, pool)
    y = fy + 1
    t.set(cx - r + 1, y, cz + 1, facing_state(WORKSTATION[prof], "east"))
    t.set(cx - r + 1, y, cz - 1, "crafting_table")
    t.set(cx - r + 1, y, cz, f"{th['wslab']}[type=top]")
    t.set(cx - r + 1, y + 1, cz, potted(rng.choice(th["plants"])))
    if tier:
        t.chest(cx - 1, y, cz + r - 1, "north", LOOT[tier])
    t.set(cx + 1, y, cz + r - 1, "barrel[facing=up]")
    col = rng.choice(th["carpet"])
    for ddx in (-1, 0, 1):
        for ddz in (-1, 0, 1):
            if t.is_free(cx + ddx, y, cz + ddz) and (cx + ddx, cz + ddz) in inside and cx + ddx < cx + r - 1:
                t.set(cx + ddx, y, cz + ddz, f"{col}_carpet")
    t.set(cx, fy + H, cz, lantern(th, True))
    return t


def make_house(th, rng, name, size, prof):
    tier = pick_tier(rng, size)
    if th["shape"] == "round":
        return round_house(th, rng, name, size, prof, tier)
    return rect_house(th, rng, name, size, prof, tier)
