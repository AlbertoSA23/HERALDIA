"""El puerto del corsario en la explanada del sur: muelle con el bergantín amarrado, la taberna (con su bodega y el
escondite tras el tapiz), los almacenes, la horca, la subida al fuerte, el faro de la punta oeste, las palmeras y los
caminos."""
import math
from .._common import pieces
from .construction import S, slab, stairs, h, bed, BASE, PL, LOG, SLOG, DPL, COB, SB, DV

YP = 2                        # pies en la explanada del puerto (suelo a y = 1)
DOCK = (43, 45, 79, 91)     # muelle: x0, x1, z0, z1 (tablero a y = 0)
T_HEAD = (33, 55, 92, 94)      # cabeza del muelle en T
SHIP = (27, 60, 100)         # bergantín: popa x, proa x, crujía z
HIDDEN_NOOK = []


def construct(o):
    roads(o)
    tavern(o)
    warehouse(o, 44, 53, 56, 63, "almacen")
    warehouse(o, 56, 64, 56, 63, "almacen")
    gallows(o, 50, 71)
    ascent(o)
    dock(o)
    brigantine(o)
    lighthouse(o)
    palms(o)


# ------------------------------------------------------------------ caminos
def road(o, x, z):
    g = o.ground.get((x, z))
    if g is None:
        return
    st = o.get(x, g, z)
    if st and ("grass_block" in st or st == "minecraft:sand"):
        o.s(x, g, z, "dirt_path" if "grass_block" in st else "sand")
        o.road.add((x, z))


def stair_steps(o):
    """Donde un camino sube un bloque (de la playa a la hierba), un peldaño en la celda baja mirando a la alta: el
    recorrido no exige saltar."""
    for (x, z) in sorted(o.road):
        g = o.ground[(x, z)]
        for d, (a, b) in DV.items():
            n = (x + a, z + b)
            if n in o.road and o.ground[n] == g + 1 and o.free(x, g + 1, z):
                mat = "sandstone" if o.get(x, g, z) == "minecraft:sand" else "cobblestone"
                o.s(x, g + 1, z, stairs(mat, d))
                break


def roads(o):
    # del muelle a la plaza y de la plaza a la subida del fuerte y al faro
    for z in range(66, 80):
        for x in (43, 44, 45):
            road(o, x, z)
    for x in range(30, 73):
        for z in (67, 68):
            road(o, x, z)
    for z in range(52, 67):
        for x in (71, 72):
            road(o, x, z)
    for x in range(20, 31):
        z = 67 - (30 - x) * 2 // 3
        for dz in (0, 1):
            road(o, x, z + dz)
    for z in range(48, 61):
        road(o, 22, z)
        road(o, 23, z)
    stair_steps(o)


# ------------------------------------------------------------------ edificios del puerto
def basic_house(o, x0, x1, z0, z1, height=4, wall=PL, post=LOG, roof="dark_oak"):
    """Planta rectangular con zócalo de piedra, muros de tablas con pies derechos y tejado a dos aguas (cumbrera a lo
    largo de x). Suelo a y = 1."""
    y0 = YP
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            corner = x in (x0, x1) and z in (z0, z1)
            o.s(x, YP - 1, z, COB if edge else PL)
            for y in range(y0, y0 + height):
                o.s(x, y, z, (post if corner else (COB if y == y0 else wall)) if edge else "air")
    top = y0 + height
    half = (z1 - z0) // 2 + 1
    for i in range(half + 1):
        for x in range(x0 - 1, x1 + 2):
            za, zb = z0 - 1 + i, z1 + 1 - i
            if za <= zb:
                for zz, f_ in ((za, "south"), (zb, "north")):
                    if 0 < i < half - 1 and x0 < x < x1 and h(x, top + i, zz, 9) < 0.06:
                        o.ruin_set(x, top + i, zz, slab(roof))     # teja rota
                    else:
                        o.s(x, top + i, zz, stairs(roof, f_))
            if za + 1 <= zb - 1 and x in (x0, x1):
                for z in range(za + 1, zb):
                    o.s(x, top + i, z, wall)
        for x in range(x0, x1 + 1):
            for z in range(z0 - 1 + i + 1, z1 + 1 - i):
                if x not in (x0, x1) and i == 0:
                    o.s(x, top, z, "air")
    if (z1 - z0) % 2 == 0:
        zc = (z0 + z1) // 2
        for x in range(x0 - 1, x1 + 2):
            o.s(x, top + half - 1, zc, slab(roof))
    return top


def tavern(o):
    """La taberna de La Sirena Ahorcada: barra, mesas y chimenea; bodega bajo el suelo con los barriles y, tras el tapiz
    del fondo, el escondite del tabernero."""
    x0, x1, z0, z1 = 27, 38, 55, 64
    top = basic_house(o, x0, x1, z0, z1, height=5)
    pieces.double_door(o.s, 32, YP, z1, "south", "east")
    for x in (29, 36):
        o.s(x, YP + 1, z1, S("glass_pane"))
        o.s(x, YP + 2, z1, S("glass_pane"))
    for z in (58, 61):
        o.s(x0, YP + 1, z, S("glass_pane"))
        o.s(x1, YP + 1, z, S("glass_pane"))
    o.sign(34, YP + 2, z1 + 1, "south", "taberna", [("La Sirena", "The Hanged"), ("Ahorcada", "Mermaid")])
    # barra a lo largo del muro norte
    for x in range(29, 36):
        o.s(x, YP, 58, stairs("spruce", "south", "top"))
    for x in range(29, 36, 3):
        o.s(x, YP, 56, S("barrel", facing="south", open=False), {"id": "minecraft:barrel"})
    o.chest(36, YP, 56, "south", "taberna")
    o.s(28, YP, 56, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]", {"id": "minecraft:brewing_stand"})
    # mesas
    for (x, z) in ((30, 61), (35, 61)):
        o.table(x, YP, z)
        o.s(x - 1, YP, z, stairs("spruce", "west"))
        o.s(x + 1, YP, z, stairs("spruce", "east"))
    # chimenea en el muro oeste
    o.s(x0 + 1, YP, 60, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    o.f(x0, YP, 59, x0, top + 4, 61, "bricks")
    o.s(x0, YP, 60, "bricks")
    o.hang(32, YP + 4, 60)
    o.hang(32, YP + 4, 57)
    # bodega: bajo la taberna (pies -3), a la que se baja por una escalera de mano en el rincón noreste
    yb = -3
    for x in range(29, 37):
        for z in range(56, 63):
            for y in range(yb, YP - 1):
                o.s(x, y, z, "air")
            o.s(x, yb - 1, z, SB)
    for x in range(28, 38):
        for z in range(55, 64):
            if x in (28, 37) or z in (55, 63):
                for y in range(yb - 1, YP - 1):
                    o.s(x, y, z, SB)
    for x in range(29, 37):
        for z in range(56, 63):
            o.s(x, YP - 1, z, PL)
    for y in range(yb, YP):
        o.s(36, y, 62, S("ladder", facing="north", waterlogged=False))
    o.a(36, YP, 62, 36, YP + 1, 62)
    for z in range(56, 61):
        o.s(29, yb, z, S("barrel", facing="east", open=False), {"id": "minecraft:barrel"})
    o.chest(30, yb, 62, "north", "bodega")
    o.hang(33, YP - 2, 59)
    # escondite tras el tapiz del muro este de la bodega: paso de 1 x 2 y un cuartito
    o.a(37, yb, 59, 37, yb + 1, 59)
    o.s(37, yb + 2, 59, SB)
    o.s(36, yb + 2, 59, S("red_wall_banner", facing="west"))
    for x in range(38, 41):
        for z in range(57, 62):
            for y in range(yb - 1, yb + 3):
                edge = x == 40 or z in (57, 61) or y in (yb - 1, yb + 2)
                o.s(x, y, z, SB if edge else "air")
    o.chest(39, yb, 58, "south", "escondite")
    o.s(39, yb, 60, S("candle", candles=2, lit=False, waterlogged=False))
    o.secret += [(x, yb, z) for x in range(37, 40) for z in range(58, 61) if (x, z) != (37, 58) and (x, z) != (37, 60)]
    o.mech["tapiz"] = (36, yb + 2, 59)


def warehouse(o, x0, x1, z0, z1, tbl):
    basic_house(o, x0, x1, z0, z1, height=4, wall=PL, post=SLOG, roof="spruce")
    xc = (x0 + x1) // 2
    pieces.double_door(o.s, xc, YP, z1, "south", "east")
    for x in range(x0 + 1, x1):
        for z in (z0 + 1,):
            if (x - x0) % 2 == 1:
                o.s(x, YP, z, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
                o.s(x, YP + 1, z, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.chest(x0 + 1, YP, z1 - 1, "east", tbl)
    o.hang(xc, YP + 3, (z0 + z1) // 2)


def gallows(o, x, z):
    """La horca de la plaza: tarima de tablas con escalones, dos postes y el travesaño con la cadena."""
    for a in range(-1, 2):
        for b in range(-1, 2):
            o.s(x + a, YP, z + b, PL)
    o.s(x, YP, z + 2, stairs("spruce", "north"))
    for a in (-1, 1):
        o.f(x + a, YP + 1, z - 1, x + a, YP + 4, z - 1, "dark_oak_log[axis=y]")
    o.s(x, YP + 4, z - 1, "dark_oak_log[axis=x]")
    o.s(x, YP + 3, z - 1, S("iron_chain", axis="y"))
    o.s(x, YP + 2, z - 1, S("lantern", hanging=True, waterlogged=False))


def ascent(o):
    """Escalinata de la explanada a la puerta del fuerte (pies 2 en z = 52 a pies 8 en la puerta)."""
    for k in range(6):
        y, z = 2 + k, 51 - k
        for x in (70, 71, 72, 73):
            if x in (70, 73):
                o.f(x, 1, z, x, y + 1, z, SB)
                o.a(x, y + 2, z, x, y + 4, z)
            else:
                o.s(x, y, z, stairs("stone_brick", "north"))
                o.f(x, 1, z, x, y - 1, z, SB)
                o.a(x, y + 1, z, x, y + 4, z)
    for x in (71, 72):
        o.s(x, 1, 52, "dirt_path")
        o.a(x, 2, 52, x, 4, 52)


# ------------------------------------------------------------------ muelle y bergantín
def dock(o):
    x0, x1, z0, z1 = DOCK
    tx0, tx1, tz0, tz1 = T_HEAD
    cells = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)] + \
            [(x, z) for x in range(tx0, tx1 + 1) for z in range(tz0, tz1 + 1)]
    for (x, z) in cells:
        if o.ground.get((x, z)) is not None:
            continue
        o.s(x, 0, z, "spruce_planks" if h(x, z, 31) > 0.08 else "spruce_slab[type=top,waterlogged=false]")
        o.a(x, 1, z, x, 3, z)
        pile = (x in (x0, x1) and (z - z0) % 4 == 0) or (z in (tz0, tz1) and (x - tx0) % 4 == 0 and tz0 <= z <= tz1)
        if pile:
            o.s(x, 0, z, "spruce_log[axis=y]")
            for y in range(BASE, 0):
                st = o.get(x, y, z)
                if st is None or "water" in st:
                    o.s(x, y, z, "spruce_log[axis=y]")
    for (x, z) in ((tx0, tz1), (tx1, tz1), (tx0 + 8, tz1), (tx1 - 8, tz1)):
        o.s(x, 1, z, "spruce_fence")
    for (x, z) in ((x0, z0 + 4), (x1, z0 + 8)):
        o.s(x, 1, z, "spruce_fence")
        o.s(x, 2, z, S("lantern", hanging=False, waterlogged=False))


def hull_half_width(x, y):
    """Semimanga del casco en la sección x a la altura y (None fuera del barco)."""
    xs, xb, zc = SHIP
    if not xs <= x <= xb:
        return None
    base = {2: 4, 1: 4, 0: 4, -1: 4, -2: 3, -3: 3, -4: 2, -5: 1}.get(y)
    if base is None:
        return None
    bow = (xb + 0.5 - x) / 9.0
    stern = 0.8 + (x - xs) / 10.0
    f = min(1.0, bow ** 0.55 if bow > 0 else 0.0, stern)
    return int(round(base * f))


def brigantine(o):
    """Bergantín de dos palos amarrado a la cabeza del muelle (casco de roble oscuro, cubierta a pies 2), con la bodega,
    el castillo de popa con el camarote del capitán y la cadena del ancla hasta el fondo."""
    xs, xb, zc = SHIP
    for x in range(xs, xb + 1):
        for y in range(-5, 3):
            hw = hull_half_width(x, y)
            if hw is None:
                continue
            for z in range(zc - hw, zc + hw + 1):
                shell = abs(z - zc) == hw or y == -5 or hull_half_width(x - 1, y) is None or hull_half_width(x + 1, y) is None \
                    or (hull_half_width(x, y - 1) is not None and abs(z - zc) > hull_half_width(x, y - 1))
                if y == 2:
                    o.s(x, y, z, "dark_oak_fence" if shell else "air")
                elif y == 1:
                    o.s(x, y, z, DPL if shell else "spruce_planks")
                elif y == -4:
                    o.s(x, y, z, DPL if shell else "spruce_planks")
                else:
                    o.s(x, y, z, DPL if shell else "air")
                if y == 2:
                    o.a(x, 3, z, x, 6, z) if not shell else None
    # bodega (pies -3) con escotilla y escala
    hx = 44
    for y in range(-3, 1):
        if o.free(hx, y, zc - 3):
            o.s(hx, y, zc - 3, DPL)
    for y in range(-3, 1):
        o.s(hx, y, zc - 2, S("ladder", facing="south", waterlogged=False))
    o.s(hx, 1, zc - 2, S("spruce_trapdoor", facing="south", half="bottom", open=True, powered=False, waterlogged=False))
    o.chest(46, -3, zc + 2, "north", "bergantin")
    for x in (48, 49, 50):
        o.s(x, -3, zc - 2, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
    o.hang(46, 0, zc)
    # castillo de popa: camarote (pies 2) y toldilla encima (pies 6)
    cx1 = xs + 7
    for x in range(xs, cx1 + 1):
        hw = hull_half_width(x, 1)
        for z in range(zc - hw, zc + hw + 1):
            edge = abs(z - zc) == hw or x in (xs, cx1)
            for y in range(2, 5):
                o.s(x, y, z, (DPL if not (x == xs and y == 3 and abs(z - zc) == 1) else S("glass_pane")) if edge else "air")
            o.s(x, 5, z, "spruce_planks")
            o.s(x, 6, z, "dark_oak_fence" if edge else "air")
    o.door(cx1, 2, zc, "east")
    o.a(cx1, 6, zc - 1, cx1, 6, zc + 1)
    # escalera a la toldilla (por estribor, subiendo hacia la popa)
    for k in range(3):
        o.s(cx1 + 3 - k, 2 + k, zc + 2, stairs("spruce", "west"))
        o.f(cx1 + 3 - k, 2, zc + 2, cx1 + 3 - k, 1 + k, zc + 2, PL) if k else None
        o.a(cx1 + 3 - k, 3 + k, zc + 2, cx1 + 3 - k, 5 + k, zc + 2)
    o.s(cx1, 5, zc + 2, "spruce_planks")
    o.a(cx1, 6, zc + 2, cx1, 6, zc + 2)
    o.s(xs + 1, 2, zc - 2, S("red_bed", facing="west", part="head", occupied=False))
    o.s(xs + 2, 2, zc - 2, S("red_bed", facing="west", part="foot", occupied=False))
    o.table(xs + 3, 2, zc + 1)
    o.chest(xs + 1, 2, zc + 2, "east", "camarote")
    o.sign(xs + 5, 3, zc - 3, "south", "diario", [("Del puerto", "From harbour"), ("al tesoro: norte", "to hoard: north"),
                                                    ("y poniente; nunca", "and west; never"), ("levante ni sur.", "east nor south.")])
    o.hang(xs + 4, 4, zc)
    o.s(xs + 2, 5, zc, "spruce_planks")
    # timón en la toldilla
    o.s(xs + 2, 6, zc, "spruce_fence")
    o.s(xs + 2, 7, zc, S("spruce_trapdoor", facing="east", half="bottom", open=True, powered=False, waterlogged=False))
    # palos, vergas y velas cuadras (velas de lana blanca y gris)
    for mx, top in ((40, 19), (51, 17)):
        o.f(mx, -4, zc, mx, top, zc, "spruce_log[axis=y]")
        for (yv, width, y0, y1) in ((top - 2, 4, top - 7, top - 3), (top - 9, 4, 4, top - 10)):
            for z in range(zc - width, zc + width + 1):
                o.s(mx + 1, yv, z, "spruce_fence")
                for y in range(y0, y1 + 1):
                    if abs(z - zc) < width:
                        if y == y0 and h(mx, y, z, 5) < 0.45:
                            o.ruin.add((mx + 1, y, z))        # vela rasgada
                        else:
                            o.s(mx + 1, y, z, "white_wool" if h(mx, y, z) > 0.12 else "light_gray_wool")
        o.s(mx, top + 1, zc, "spruce_fence")
    # bauprés y cadena del ancla (por la amura de babor, hasta la fila inferior: se prolonga hasta el fondo)
    for k in range(6):
        o.s(xb + k, 3, zc, "spruce_log[axis=x]")
    ax = xb - 4
    az = zc - hull_half_width(ax, 1) - 1
    back = bed(ax, az)
    if back is None:
        back = BASE - 1                       # el ancla cuelga de su cadena sobre el fondo (o queda enterrada)
    o.s(ax, back + 1, az, "anvil[facing=north]")
    for y in range(back + 2, 2):
        o.s(ax, y, az, S("iron_chain", axis="y"))
    o.s(ax, 2, az, "dark_oak_fence")
    o.mech["ancla"] = (ax, az)
    # pasarela del muelle a la cubierta: tablón sobre el agua, peldaño y hueco en la borda
    for x in (44, 45):
        o.s(x, 0, 95, "spruce_planks")
        o.s(x, 1, 95, stairs("spruce", "south"))
        o.a(x, 2, 95, x, 4, 95)
        o.a(x, 2, zc - hull_half_width(x, 1), x, 2, zc - hull_half_width(x, 1))


# ------------------------------------------------------------------ faro de la punta oeste
def lighthouse(o):
    cx, cz = 20, 48
    for (x, z) in [(cx + a, cz + b) for a in range(-5, 6) for b in range(-5, 6) if a * a + b * b <= 26]:
        g = o.ground.get((x, z))
        y0 = BASE if g is None else g
        for y in range(y0, 2):
            o.s(x, y, z, "stone" if h(x, y, z) < 0.7 else "andesite")
        o.ground[(x, z)] = 1
    ring = [(cx + a, cz + b) for a in range(-2, 3) for b in range(-2, 3) if 2 <= math.hypot(a, b) <= 2.9]
    inner = [(cx + a, cz + b) for a in range(-1, 2) for b in range(-1, 2)]
    for y in range(2, 16):
        for (x, z) in ring:
            o.s(x, y, z, COB if y < 5 else ("white_terracotta" if (y // 3) % 2 else "red_terracotta"))
        for (x, z) in inner:
            o.s(x, y, z, "air")
    for (x, z) in inner:
        o.s(x, 1, z, SB)
        o.s(x, 15, z, SB)
    o.door(cx + 2, 2, cz, "east")
    for y in range(2, 16):
        o.s(cx - 1, y, cz, S("ladder", facing="east", waterlogged=False))
    o.chest(cx, 2, cz - 1, "south", "faro")
    for y in (6, 10):
        o.s(cx, y, cz - 2, S("glass_pane"))
    # sala de la linterna
    lan = [(cx + a, cz + b) for a in range(-2, 3) for b in range(-2, 3) if math.hypot(a, b) <= 2.9]
    for (x, z) in lan:
        o.s(x, 15, z, SB)
    for (x, z) in ring:
        o.s(x, 16, z, "spruce_fence")
    for (x, z) in inner:
        if (x, z) != (cx - 1, cz):
            o.s(x, 16, z, "air")
    o.s(cx + 1, 16, cz + 1, "sea_lantern")
    o.s(cx - 1, 15, cz, S("ladder", facing="east", waterlogged=False))
    o.a(cx - 1, 16, cz, cx - 1, 17, cz)
    for (x, z) in lan:
        o.s(x, 19, z, slab("spruce"))
    for (a, b) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        o.f(cx + a, 17, cz + b, cx + a, 18, cz + b, "spruce_fence")


# ------------------------------------------------------------------ palmeras
def palm(o, x, z, height, tilt):
    g = o.ground.get((x, z))
    if g is None:
        return
    dx, dz = DV[tilt]
    px, pz = x, z
    for i in range(height):
        y = g + 1 + i
        if i == height // 2:
            o.s(px, y, pz, "jungle_log[axis=y]")
            px, pz = px + dx, pz + dz
        o.s(px, y, pz, "jungle_log[axis=y]")
    ty = g + height
    leaf = "jungle_leaves[distance=1,persistent=true,waterlogged=false]"
    o.s(px, ty + 1, pz, leaf)
    for d, (a, b) in DV.items():
        o.s(px + a, ty + 1, pz + b, leaf)
        o.s(px + 2 * a, ty + 1, pz + 2 * b, leaf)
        o.s(px + 2 * a, ty, pz + 2 * b, leaf)
        o.s(px + 3 * a, ty, pz + 3 * b, leaf)
    for (a, b) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        o.s(px + a, ty + 1, pz + b, leaf)
    o.s(px - dx, ty - 1, pz - dz, S("cocoa", age=2, facing=tilt))


PALMS = [(30, 76, 6, "south"), (38, 79, 7, "south"), (55, 83, 6, "east"), (62, 84, 7, "south"), (24, 68, 6, "west"),
            (19, 60, 7, "west"), (18, 40, 6, "west"), (24, 33, 7, "north"), (33, 22, 6, "north"), (44, 15, 7, "north"),
            (80, 74, 6, "east"), (88, 62, 7, "east"), (90, 52, 6, "east")]


def palms(o):
    for (x, z, height, inc) in PALMS:
        palm(o, x, z, height, inc)
