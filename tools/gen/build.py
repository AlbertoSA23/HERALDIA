"""Herramientas de construcción: muros, ventanas, puertas, tejados, mobiliario."""
import math
from core import with_props, CW, CCW, OPP, DIRS

WORKSTATION = {
    "armorer": "blast_furnace", "butcher": "smoker", "cartographer": "cartography_table",
    "cleric": "brewing_stand", "farmer": "composter", "fisherman": "barrel", "fletcher": "fletching_table",
    "leatherworker": "cauldron", "librarian": "lectern", "mason": "stonecutter", "shepherd": "loom",
    "toolsmith": "smithing_table", "weaponsmith": "grindstone",
}
FACING_BLOCKS = {"blast_furnace", "smoker", "furnace", "lectern", "loom", "stonecutter", "barrel",
                 "chest", "grindstone", "anvil"}


def facing_state(block, facing):
    b = block.split("[")[0].replace("minecraft:", "")
    if b == "grindstone":
        return f"grindstone[face=floor,facing={facing}]"
    if b == "barrel":
        return "barrel[facing=up]"
    if b == "anvil":
        return f"anvil[facing={CW[facing]}]"
    if b == "stonecutter" or b in FACING_BLOCKS:
        return f"{b}[facing={facing}]"
    return block


def stairs(mat, facing, half="bottom", shape="straight"):
    return f"{mat}[facing={facing},half={half},shape={shape}]"


def slab(mat, typ="bottom"):
    return f"{mat}[type={typ}]"


def log(mat, axis="y"):
    if mat.endswith("_log") or mat.endswith("_wood") or mat.endswith("_block") or mat.endswith("_stem") \
            or mat in ("hay_block", "basalt", "polished_basalt", "bone_block", "quartz_pillar", "purpur_pillar"):
        return f"{mat}[axis={axis}]"
    return mat


def door(t, x, y, z, mat, facing, hinge="left"):
    t.set(x, y, z, f"{mat}[facing={facing},half=lower,hinge={hinge},open=false]")
    t.set(x, y + 1, z, f"{mat}[facing={facing},half=upper,hinge={hinge},open=false]")


def lantern(th, hanging=True):
    return f"{th['light']}[hanging={'true' if hanging else 'false'}]"


def leaves(th, kind=None):
    return f"{kind or th['leaves']}[persistent=true]"


# ---------------------------------------------------------------- muros
def wall_block(th, style, x, y, z, edge, ybase, ytop, axis, corner, col_index):
    """Elige el bloque de muro según el estilo."""
    h = y - ybase  # 1..altura
    wall, wall2 = th["wall"], th["wall2"]
    if style == "frame":
        if corner or col_index % 4 == 0:
            return log(th["log"], "y")
        if y == ytop:
            return log(th["stripped"], axis)
        if h == 1 and wall2 != wall:
            return wall2
        return wall
    if style == "stone_base":
        if corner:
            return log(wall2, "y")
        if h == 1:
            return log(wall2, axis)
        return log(wall, axis if wall.endswith("_log") else "y")
    if style == "logcabin":
        if corner:
            return log(th["accent"], "y")
        return log(wall if wall.endswith(("_log", "_wood")) else th["log"], axis)
    if style == "stripes":
        if corner:
            return wall2
        return wall2 if (h % 3 == 1) else wall
    # plain
    if corner and wall2 != wall:
        return wall2
    return log(wall, "y")


def rect_walls(t, th, x0, z0, x1, z1, ybase, height, style=None):
    """Muros perimetrales del rectángulo [x0..x1]x[z0..z1] desde ybase+1 hasta ybase+height."""
    style = style or th["wall_style"]
    ytop = ybase + height
    for y in range(ybase + 1, ytop + 1):
        for x in range(x0, x1 + 1):
            for z in (z0, z1):
                corner = x in (x0, x1)
                t.set(x, y, z, wall_block(th, style, x, y, z, None, ybase, ytop, "x", corner, x - x0))
        for z in range(z0 + 1, z1):
            for x in (x0, x1):
                t.set(x, y, z, wall_block(th, style, x, y, z, None, ybase, ytop, "z", False, z - z0))


def floor_rect(t, x0, z0, x1, z1, y, block):
    t.fill(x0, y, z0, x1, y, z1, block)


def interior_air(t, x0, z0, x1, z1, y0, y1):
    t.air(x0, y0, z0, x1, y1, z1)


def windows_on_wall(t, th, x0, z0, x1, z1, side, y, rng, skip=(), tall=False, pane=None, spacing=3):
    """Ventanas en un muro. side in north/south/west/east."""
    pane = pane or th["window"]
    if side in ("north", "south"):
        z = z0 if side == "north" else z1
        rngx = range(x0 + 2, x1 - 1)
        cells = [(x, z) for x in rngx]
    else:
        x = x0 if side == "west" else x1
        cells = [(x, zz) for zz in range(z0 + 2, z1 - 1)]
    placed = []
    for i, (x, z) in enumerate(cells):
        if i % spacing != 1 % spacing and len(cells) > 2:
            continue
        if any(abs(x - sx) <= 0 and abs(z - sz) <= 0 for sx, sz in skip):
            continue
        cur = t.get(x, y, z) or ""
        if "_log" in cur and th["wall_style"] == "frame":
            continue
        t.set(x, y, z, pane)
        if tall:
            t.set(x, y + 1, z, pane)
        placed.append((x, z))
    return placed


# ---------------------------------------------------------------- tejados
def gable_roof(t, th, x0, z0, x1, z1, ybase, along="x", overhang=1, steep=False, gable_fill=None,
               mat=None, slabm=None, fullm=None):
    """Tejado a dos aguas sobre la caja [x0..x1]x[z0..z1]; ybase = cota del alero (encima del muro)."""
    rs = mat or th["roof_stairs"]
    rsl = slabm or th["roof_slab"]
    rf = fullm or th["roof_full"]
    gable_fill = gable_fill or th["wall"]
    if along == "x":
        a0, a1 = x0 - overhang, x1 + overhang     # extensión de la cumbrera
        s0, s1 = z0 - 1, z1 + 1                    # pendiente
    else:
        a0, a1 = z0 - overhang, z1 + overhang
        s0, s1 = x0 - 1, x1 + 1
    span = s1 - s0 + 1
    half = span // 2
    rise = 2 if steep else 1
    top_y = ybase
    for k in range(half):
        y = ybase + k * rise
        lo, hi = s0 + k, s1 - k
        for a in range(a0, a1 + 1):
            if along == "x":
                if steep:
                    t.set(a, y, lo, rf); t.set(a, y, hi, rf)
                    if k > 0:
                        t.set(a, y - 1, lo, rf); t.set(a, y - 1, hi, rf)
                    t.set(a, y + 1, lo, stairs(rs, "south"))
                    t.set(a, y + 1, hi, stairs(rs, "north"))
                else:
                    t.set(a, y, lo, stairs(rs, "south"))
                    t.set(a, y, hi, stairs(rs, "north"))
            else:
                if steep:
                    t.set(lo, y, a, rf); t.set(hi, y, a, rf)
                    if k > 0:
                        t.set(lo, y - 1, a, rf); t.set(hi, y - 1, a, rf)
                    t.set(lo, y + 1, a, stairs(rs, "east"))
                    t.set(hi, y + 1, a, stairs(rs, "west"))
                else:
                    t.set(lo, y, a, stairs(rs, "east"))
                    t.set(hi, y, a, stairs(rs, "west"))
        # relleno del hastial (dentro de los muros)
        for s in range(lo + 1, hi):
            for yy in range(y, y + rise):
                for a in (x0 if along == "x" else z0, x1 if along == "x" else z1):
                    if along == "x":
                        if z0 <= s <= z1:
                            t.set(a, yy, s, gable_fill)
                    else:
                        if x0 <= s <= x1:
                            t.set(s, yy, a, gable_fill)
        top_y = y + rise - 1
    if span % 2 == 1:
        mid = s0 + half
        y = ybase + half * rise
        for a in range(a0, a1 + 1):
            if along == "x":
                t.set(a, y, mid, slab(rsl))
                if steep:
                    t.set(a, y - 1, mid, rf); t.set(a, y - 2, mid, rf)
            else:
                t.set(mid, y, a, slab(rsl))
                if steep:
                    t.set(mid, y - 1, a, rf); t.set(mid, y - 2, a, rf)
        for yy in range(ybase + (half - 1) * rise + rise, y):
            for a in (x0 if along == "x" else z0, x1 if along == "x" else z1):
                if along == "x":
                    t.set(a, yy, mid, gable_fill)
                else:
                    t.set(mid, yy, a, gable_fill)
        top_y = y
    return top_y


def hip_roof(t, th, x0, z0, x1, z1, ybase, overhang=1, mat=None, slabm=None, fullm=None, upturn=False, max_rings=None):
    rs = mat or th["roof_stairs"]
    rsl = slabm or th["roof_slab"]
    rf = fullm or th["roof_full"]
    ax0, az0, ax1, az1 = x0 - overhang, z0 - overhang, x1 + overhang, z1 + overhang
    k = 0
    y = ybase
    while ax0 <= ax1 and az0 <= az1:
        if ax0 == ax1 or az0 == az1:
            t.fill(ax0, y, az0, ax1, y, az1, slab(rsl))
            break
        for x in range(ax0 + 1, ax1):
            t.set(x, y, az0, stairs(rs, "south"))
            t.set(x, y, az1, stairs(rs, "north"))
        for z in range(az0 + 1, az1):
            t.set(ax0, y, z, stairs(rs, "east"))
            t.set(ax1, y, z, stairs(rs, "west"))
        t.set(ax0, y, az0, stairs(rs, "south", shape="outer_left"))
        t.set(ax1, y, az0, stairs(rs, "south", shape="outer_right"))
        t.set(ax0, y, az1, stairs(rs, "north", shape="outer_right"))
        t.set(ax1, y, az1, stairs(rs, "north", shape="outer_left"))
        if upturn and k == 0:
            for (cx, cz, f) in ((ax0, az0, "north"), (ax1, az0, "north"), (ax0, az1, "south"), (ax1, az1, "south")):
                t.set(cx, y + 1, cz, stairs(rs, OPP[f], half="bottom"))
        # relleno interior debajo del anillo superior
        if ax1 - ax0 >= 2 and az1 - az0 >= 2:
            pass
        ax0 += 1; az0 += 1; ax1 -= 1; az1 -= 1
        y += 1
        k += 1
        if max_rings and k >= max_rings:
            break
        if ax0 > ax1 or az0 > az1:
            break
        if ax0 == ax1 and az0 == az1:
            t.set(ax0, y, az0, slab(rsl))
            break
    return y


def flat_roof(t, th, x0, z0, x1, z1, y, parapet=None, light=True):
    t.fill(x0, y, z0, x1, y, z1, th["roof_full"])
    p = parapet or th.get("flat_parapet") or th["roof_slab"] + "[type=bottom]"
    for x in range(x0, x1 + 1):
        t.set(x, y + 1, z0, p)
        t.set(x, y + 1, z1, p)
    for z in range(z0, z1 + 1):
        t.set(x0, y + 1, z, p)
        t.set(x1, y + 1, z, p)
    if light:
        t.set((x0 + x1) // 2, y + 1, (z0 + z1) // 2, lantern(th, False))
    return y + 1


def dome(t, cx, cy, cz, r, mat_full, mat_stairs=None, finial=None):
    """Cúpula semiesférica centrada en (cx,cy,cz)."""
    for dy in range(0, r + 1):
        rr = math.sqrt(max(0, r * r - dy * dy))
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                d = math.sqrt(dx * dx + dz * dz)
                if rr - 1.0 < d <= rr + 0.3:
                    t.set(cx + dx, cy + dy, cz + dz, mat_full)
                elif d <= rr - 1.0:
                    t.set(cx + dx, cy + dy, cz + dz, "air")
    if finial:
        t.set(cx, cy + r + 1, cz, finial)


def cone_roof(t, th, cx, cz, r, ybase, mat=None, top="hay_block"):
    rs = mat or th["roof_stairs"]
    for k in range(r + 2):
        rad = r + 1 - k
        y = ybase + k
        if rad <= 0:
            t.set(cx, y, cz, log(top, "y"))
            break
        for dx in range(-rad, rad + 1):
            for dz in range(-rad, rad + 1):
                d = math.sqrt(dx * dx + dz * dz)
                if rad - 0.5 <= d < rad + 0.5:
                    if abs(dx) >= abs(dz):
                        f = "east" if dx < 0 else "west"
                    else:
                        f = "south" if dz < 0 else "north"
                    t.set(cx + dx, y, cz + dz, stairs(rs, f))
                elif d < rad - 0.5:
                    t.set(cx + dx, y, cz + dz, log(top, "y") if top.endswith("block") else top)
    return ybase + r + 1


def spire(t, cx, cz, y, r, mat_stairs, mat_full, height=None):
    """Chapitel piramidal estrecho sobre una torre (r = semilado)."""
    height = height or (r * 3 + 2)
    yy = y
    rad = r
    while rad >= 0:
        for _ in range(2 if rad > 0 else 1):
            if rad == 0:
                t.set(cx, yy, cz, mat_full)
            else:
                for dx in range(-rad, rad + 1):
                    t.set(cx + dx, yy, cz - rad, stairs(mat_stairs, "south"))
                    t.set(cx + dx, yy, cz + rad, stairs(mat_stairs, "north"))
                for dz in range(-rad + 1, rad):
                    t.set(cx - rad, yy, cz + dz, stairs(mat_stairs, "east"))
                    t.set(cx + rad, yy, cz + dz, stairs(mat_stairs, "west"))
                for dx in range(-rad + 1, rad):
                    for dz in range(-rad + 1, rad):
                        t.set(cx + dx, yy, cz + dz, mat_full)
            yy += 1
        rad -= 1
    return yy


def onion(t, cx, cy, cz, r, mat_full):
    """Cúpula bulbosa."""
    depth = [r - 1, r, r + 1, r + 1, r, r - 1, r - 2, max(1, r - 3), 0, 0]
    for i, rr in enumerate(depth):
        for dx in range(-rr, rr + 1):
            for dz in range(-rr, rr + 1):
                if dx * dx + dz * dz <= rr * rr + 0.5:
                    t.set(cx + dx, cy + i, cz + dz, mat_full)
    t.set(cx, cy + len(depth), cz, "lightning_rod[facing=up]")


def roof_for(t, th, x0, z0, x1, z1, ybase, kind=None, along=None):
    kind = kind or th["roof_type"]
    w, d = x1 - x0 + 1, z1 - z0 + 1
    along = along or ("x" if w >= d else "z")
    if kind == "gable":
        return gable_roof(t, th, x0, z0, x1, z1, ybase, along=along)
    if kind == "steep":
        return gable_roof(t, th, x0, z0, x1, z1, ybase, along=along, steep=True)
    if kind in ("hip",):
        return hip_roof(t, th, x0, z0, x1, z1, ybase)
    if kind == "pagoda":
        return hip_roof(t, th, x0, z0, x1, z1, ybase, overhang=2, upturn=True)
    if kind == "flat":
        return flat_roof(t, th, x0, z0, x1, z1, ybase)
    if kind == "cone" and abs(w - d) > 1:
        return hip_roof(t, th, x0, z0, x1, z1, ybase)
    if kind == "cone":
        cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
        return cone_roof(t, th, cx, cz, max(w, d) // 2, ybase)
    raise ValueError(kind)


# ---------------------------------------------------------------- mobiliario
def table(t, th, x, y, z):
    t.set(x, y, z, f"{th['wslab']}[type=top]")


def chair(t, th, x, y, z, back):
    """Silla: `back` es el lado donde queda el respaldo (el lado alto del escalón)."""
    t.set(x, y, z, stairs(th["wstairs"], back))


def bookshelf_col(t, x, y, z, h=2):
    for i in range(h):
        t.set(x, y + i, z, "bookshelf")


def carpet(t, th, x0, z0, x1, z1, y, color=None):
    color = color or th["carpet"][0]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if t.is_free(x, y, z):
                t.set(x, y, z, f"{color}_carpet")


def potted(plant):
    m = {"cactus_pot": "potted_cactus", "bamboo_pot": "potted_bamboo", "sweet_berry_bush": "potted_fern"}
    return m.get(plant, "potted_" + plant)


def planter_plant(plant):
    m = {"cactus_pot": "dead_bush", "bamboo_pot": "fern", "sweet_berry_bush": "sweet_berry_bush[age=3]"}
    return m.get(plant, plant)
