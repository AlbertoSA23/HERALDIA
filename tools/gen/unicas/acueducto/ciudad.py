"""La ciudad: murallas, calles, insulae, foro con templo, termas y villa del gobernador (todo con y >= 0)."""
import random
from .obra import FACE

X0, Z0, X1, Z1 = 0, 5, 95, 96          # muralla
ROAD, SIDE, GROUND = "polished_andesite", "cut_sandstone", "sandstone"
WALL, BASE, TRIM, CEIL = "smooth_sandstone", "cut_sandstone", "cut_sandstone", "spruce_planks"


# ------------------------------------------------------------------ calles y muralla
def calles(o):
    o.f(X0 - 1, 0, Z0, X1 + 1, 0, Z1 + 1, GROUND)
    o.air(X0 - 1, 1, Z0, X1 + 1, 9, Z1 + 1)

    def calle_x(z0, x0, x1):         # calzada de 3 con aceras (z0-1 y z0+3)
        o.f(x0, 0, z0 - 1, x1, 0, z0 + 3, SIDE)
        o.f(x0, 0, z0, x1, 0, z0 + 2, ROAD)

    def calle_z(x0, z0, z1):
        o.f(x0 - 1, 0, z0, x0 + 3, 0, z1, SIDE)
        o.f(x0, 0, z0, x0 + 2, 0, z1, ROAD)

    calle_x(19, 1, 94)                 # calle norte (z 18-22)
    calle_x(49, 1, 32); calle_x(49, 64, 94)     # decumano
    calle_x(77, 1, 94)                 # calle sur (z 76-80)
    calle_z(46, 61, 95)                # cardo sur
    calle_z(21, 53, 95); calle_z(72, 53, 95)    # cardines menores
    calle_z(78, 6, 18)                 # callejón del castellum


def muralla(o):
    o.ring(X0, Z0, X1, Z1, 1, 5, BASE)
    for x in range(X0, X1 + 1, 2):
        o.s(x, 6, Z0, BASE); o.s(x, 6, Z1, BASE)
    for z in range(Z0, Z1 + 1, 2):
        o.s(X0, 6, z, BASE); o.s(X1, 6, z, BASE)
    for cx, cz in ((X0, Z0), (X1 - 4, Z0), (X0, Z1 - 4), (X1 - 4, Z1 - 4)):   # torres macizas
        o.f(cx, 1, cz, cx + 4, 7, cz + 4, BASE)
        o.f(cx, 1, cz, cx + 4, 1, cz + 4, "chiseled_sandstone")
        for k in range(5):
            if k % 2 == 0:
                for (a, b) in ((cx + k, cz), (cx + k, cz + 4), (cx, cz + k), (cx + 4, cz + k)):
                    o.s(a, 8, b, BASE)
    # puertas: sur (cardo), oeste y este (decumano), y la del castellum
    o.air(46, 1, Z1, 48, 4, Z1); o.f(45, 5, Z1, 49, 5, Z1, "chiseled_sandstone")
    o.air(X0, 1, 49, X0, 4, 51); o.f(X0, 5, 48, X0, 5, 52, "chiseled_sandstone")
    o.air(X1, 1, 49, X1, 4, 51); o.f(X1, 5, 48, X1, 5, 52, "chiseled_sandstone")
    o.f(46, 0, Z1, 48, 0, Z1, ROAD); o.f(X0, 0, 49, X0, 0, 51, ROAD); o.f(X1, 0, 49, X1, 0, 51, ROAD)
    for x in range(46, 49):
        o.slab(x, 0, Z1 + 1, "bottom", "smooth_sandstone_slab")
    for z in range(49, 52):
        o.slab(X0 - 1, 0, z, "bottom", "smooth_sandstone_slab"); o.slab(X1 + 1, 0, z, "bottom", "smooth_sandstone_slab")
    o.air(79, 1, Z0, 79, 2, Z0)
    o.sign(47, 5, Z1 + 1, "south", [("heraldia.unicas.acueducto.cartel.colonia1", "COLONIA"),
                                   ("heraldia.unicas.acueducto.cartel.colonia2", "AQVAE SICCAE")])
    # dos tramos caídos (con escombros a ambos lados)
    for (x, za, zb) in ((X0, 27, 33), (X1, 66, 71)):
        for z in range(za, zb + 1):
            top = 1 if za < z < zb else 2
            o.air(x, top + 1, z, x, 6, z)
        o.ruina += (zb - za + 1)
        for z in range(za + 1, zb, 2):
            o.slab(x + (1 if x == X0 else -1), 1, z, "bottom", "sandstone_slab")
    o.sup += 2 * (X1 - X0 + Z1 - Z0)


# ------------------------------------------------------------------ casas y tiendas
ITEMS = {
    "casa": ["chest:menor", "crafting_table", "barrel:menor", "pot", "potted_dead_bush", "furnace"],
    "grande": ["chest:menor", "bookshelf", "barrel:menor", "pot", "crafting_table", "bookshelf", "smoker", "pot", "barrel:menor"],
    "taberna": ["barrel:tienda", "pot", "chest:tienda", "barrel:tienda", "pot"],
    "panaderia": ["furnace", "smoker", "furnace", "barrel:menor", "crafting_table", "hay_block", "barrel:menor"],
    "fullonica": ["water_cauldron", "water_cauldron", "loom", "barrel:tienda", "water_cauldron", "pot"],
    "alfareria": ["pot", "pot", "barrel:tienda", "crafting_table", "pot", "furnace", "pot"],
}


def item(o, kind, x, y, z, facing):
    if kind.startswith("chest:"):
        o.chest(x, y, z, facing, kind.split(":")[1])
    elif kind.startswith("barrel:"):
        o.barrel(x, y, z, kind.split(":")[1])
    elif kind == "pot":
        o.pot(x, y, z, facing)
    elif kind in ("furnace", "smoker"):
        o.s(x, y, z, f"{kind}[facing={facing},lit=false]")
    elif kind == "loom":
        o.s(x, y, z, f"loom[facing={facing}]")
    elif kind == "water_cauldron":
        o.s(x, y, z, "water_cauldron[level=3]")
    elif kind == "hay_block":
        o.s(x, y, z, "hay_block[axis=y]")
    else:
        o.s(x, y, z, kind)


def anillo(ix0, iz0, ix1, iz1):
    """Celdas interiores pegadas a los muros, en orden horario desde la esquina noroeste, con la dirección hacia dentro."""
    out = []
    for x in range(ix0, ix1 + 1):
        out.append((x, iz0, "south"))
    for z in range(iz0 + 1, iz1 + 1):
        out.append((ix1, z, "west"))
    for x in range(ix1 - 1, ix0 - 1, -1):
        out.append((x, iz1, "north"))
    for z in range(iz1 - 1, iz0, -1):
        out.append((ix0, z, "east"))
    return out


def amueblar(o, ix0, iz0, ix1, iz1, kind, libres, excl, camas=0, mesa=True, luz=True):
    used = set(libres) | set(excl)
    sx, sz = ix1 - ix0 + 1, iz1 - iz0 + 1
    for k in range(camas):                       # camas en las esquinas del fondo (norte), cabecera al muro
        x = ix0 if k == 0 else ix1
        if {(x, iz0), (x, iz0 + 1)} & used:
            continue
        o.bed(x, 1, iz0 + 1, "north", ("red", "white")[k])
        used |= {(x, iz0), (x, iz0 + 1)}
    items = list(ITEMS[kind])
    ring = anillo(ix0, iz0, ix1, iz1)
    for (x, z, facing) in ring[::2] + ring[1::2]:
        if not items:
            break
        if (x, z) in used:
            continue
        item(o, items.pop(0), x, 1, z, facing)
        used.add((x, z))
    cx, cz = (ix0 + ix1) // 2, (iz0 + iz1) // 2
    if mesa and sx >= 5 and sz >= 5 and not ({(cx, cz), (cx - 1, cz), (cx + 1, cz)} & set(excl)):
        o.s(cx, 1, cz, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
        o.s(cx, 2, cz, "brown_carpet")
        o.stair(cx - 1, 1, cz, "west", "spruce_stairs")
        o.stair(cx + 1, 1, cz, "east", "spruce_stairs")
    if luz and (cx, cz + 1) not in excl and o.solid(cx, 5, cz + 1):
        o.lantern(cx, 4, cz + 1)


def escombros(o, rng, x0, z0, x1, z1, y=1, arena=1):
    cells = [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if not o.solid(x, y, z)]
    rng.shuffle(cells)
    for i, (x, z) in enumerate(cells[: max(1, len(cells) * 2 // 5)]):
        if i < arena:
            o.brush(x, y, z)
        elif i % 4 == 0:
            o.s(x, y, z, "sand")
        else:
            o.slab(x, y, z, "bottom", "brick_slab")
    if len(cells) > 3:
        x, z = cells[-1]
        if not o.solid(x + 1, y, z) and x + 1 <= x1:
            o.s(x, y, z, "stripped_spruce_log[axis=x]"); o.s(x + 1, y, z, "stripped_spruce_log[axis=x]")


def casa(o, x0, z0, x1, z1, puerta, kind="casa", ruina=None, seed=0):
    """Casa o tienda de una planta. puerta = (lado, coordenada a lo largo del muro). ruina = None | (tipo, zona)."""
    rng = random.Random(seed)
    side, p = puerta
    tienda = kind in ("taberna", "alfareria")
    eje = "z" if (x1 - x0) < (z1 - z0) else "x"
    o.f(x0, 0, z0, x1, 0, z1, "smooth_sandstone")
    o.ring(x0, z0, x1, z1, 1, 1, BASE)
    o.ring(x0, z0, x1, z1, 2, 4, WALL)
    o.ring(x0, z0, x1, z1, 5, 5, TRIM)
    o.f(x0 + 1, 5, z0 + 1, x1 - 1, 5, z1 - 1, CEIL)
    o.tejado(x0 - 1, z0 - 1, x1 + 1, z1 + 1, 6, eje)
    # ventanas altas en los muros largos
    for z in range(z0 + 2, z1 - 1, 3):
        o.s(x0, 3, z, "iron_bars"); o.s(x1, 3, z, "iron_bars")
    for x in range(x0 + 2, x1 - 1, 3):
        o.s(x, 3, z0, "iron_bars"); o.s(x, 3, z1, "iron_bars")
    # puerta o frente abierto de la tienda
    wall = {"north": z0, "south": z1, "west": x0, "east": x1}[side]
    inward = FACE[{"north": "south", "south": "north", "west": "east", "east": "west"}[side]]
    libres = set()
    along = range(x0 + 2, x1 - 1) if side in ("north", "south") else range(z0 + 2, z1 - 1)
    if tienda:
        cells = [a for a in along]
        for a in cells:
            x, z = (a, wall) if side in ("north", "south") else (wall, a)
            o.air(x, 1, z, x, 3, z)
            o.s(x, 4, z, "chiseled_sandstone" if a in (cells[0], cells[-1]) else TRIM)
            libres.add((x + inward[0], z + inward[1]))
        # mostrador con paso en un extremo
        for a in cells[:-1]:
            x, z = (a, wall) if side in ("north", "south") else (wall, a)
            cx, cz = x + 2 * inward[0], z + 2 * inward[1]
            o.slab(cx, 1, cz, "top", "smooth_sandstone_slab")
            libres.add((cx, cz))
            if a % 3 == 1:
                o.pot(cx, 2, cz)
        a = cells[-1]
        x, z = (a, wall) if side in ("north", "south") else (wall, a)
        libres.add((x + 2 * inward[0], z + 2 * inward[1]))
    else:
        x, z = (p, wall) if side in ("north", "south") else (wall, p)
        o.door(x, z, side)
        o.s(x, 3, z, WALL)
        ix, iz = x + inward[0], z + inward[1]
        libres |= {(ix, iz), (ix + inward[1], iz + inward[0]), (ix - inward[1], iz - inward[0])}
    ix0, iz0, ix1, iz1 = x0 + 1, z0 + 1, x1 - 1, z1 - 1
    area = (x1 - x0 + 1) * (z1 - z0 + 1)
    o.sup += area
    excl = set()
    if ruina:
        tipo, (rx0, rz0, rx1, rz1) = ruina
        if tipo == "derrumbe":
            rx0, rz0, rx1, rz1 = x0, z0, x1, z1
        for x in range(rx0 - (1 if rx0 == x0 else 0), rx1 + (2 if rx1 == x1 else 1)):
            for z in range(rz0 - (1 if rz0 == z0 else 0), rz1 + (2 if rz1 == z1 else 1)):
                for y in range(5, 13):
                    o.s(x, y, z, "air")
        if tipo in ("muro", "derrumbe"):
            for x in range(rx0, rx1 + 1):
                for z in range(rz0, rz1 + 1):
                    if x in (x0, x1) or z in (z0, z1):
                        if (x, z) == ((p, wall) if side in ("north", "south") else (wall, p)) and tipo == "muro":
                            continue
                        top = 1 + rng.randint(0, 2) if tipo == "derrumbe" else 2 + rng.randint(0, 1)
                        for y in range(top + 1, 5):
                            o.s(x, y, z, "air")
        for x in range(rx0, rx1 + 1):
            for z in range(rz0, rz1 + 1):
                if ix0 <= x <= ix1 and iz0 <= z <= iz1:
                    excl.add((x, z))
        escombros(o, rng, max(rx0, ix0), max(rz0, iz0), min(rx1, ix1), min(rz1, iz1))
        o.ruina += (rx1 - rx0 + 1) * (rz1 - rz0 + 1)
        if tipo == "derrumbe":
            return
    camas = 2 if kind == "grande" else (1 if kind == "casa" else 0)
    amueblar(o, ix0, iz0, ix1, iz1, kind, libres, excl, camas=camas, mesa=not tienda)


PARCELAS = [
    # (x0, z0, x1, z1, puerta, tipo, ruina)
    (2, 6, 12, 17, ("south", 7), "casa", ("tejado", (3, 7, 7, 16))),
    (14, 6, 24, 17, ("south", 0), "taberna", None),
    (26, 6, 36, 17, ("south", 31), "casa", ("tejado", (27, 7, 31, 12))),
    (38, 6, 50, 17, ("south", 44), "panaderia", None),
    (52, 6, 62, 17, ("south", 57), "casa", ("tejado", (53, 7, 58, 16))),
    (64, 6, 75, 17, ("south", 69), "fullonica", None),
    (82, 6, 93, 17, ("south", 87), "grande", None),
    (2, 53, 10, 63, ("north", 6), "casa", None),
    (11, 53, 19, 63, ("north", 0), "taberna", None),
    (2, 65, 10, 75, ("south", 6), "casa", None),
    (11, 65, 19, 75, ("south", 15), "casa", ("derrumbe", (11, 65, 19, 75))),
    (25, 53, 32, 60, ("west", 0), "alfareria", None),
    (25, 62, 34, 75, ("west", 68), "casa", ("derrumbe", (25, 62, 34, 75))),
    (36, 62, 44, 75, ("east", 0), "taberna", None),
    (50, 62, 59, 75, ("west", 0), "taberna", None),
    (61, 62, 70, 75, ("east", 68), "casa", ("tejado", (62, 63, 66, 69))),
    (64, 53, 70, 60, ("north", 0), "alfareria", None),
    (76, 53, 85, 63, ("west", 58), "casa", ("tejado", (77, 54, 81, 62))),
    (86, 53, 94, 63, ("north", 90), "casa", ("tejado", (87, 57, 93, 62))),
    (76, 65, 94, 75, ("south", 85), "grande", ("tejado", (77, 66, 86, 74))),
    (2, 81, 19, 95, ("north", 10), "grande", ("muro", (2, 81, 10, 95))),
    (25, 81, 34, 95, ("north", 29), "casa", ("muro", (25, 88, 30, 95))),
    (36, 81, 44, 95, ("east", 0), "taberna", None),
    (50, 81, 59, 95, ("west", 88), "panaderia", None),
    (61, 81, 70, 95, ("north", 65), "casa", ("tejado", (62, 82, 66, 90))),
    (76, 81, 85, 95, ("north", 80), "casa", ("tejado", (77, 87, 84, 94))),
    (87, 81, 94, 95, ("north", 90), "casa", None),
]


def parcelas(o):
    for i, (x0, z0, x1, z1, puerta, kind, ruina) in enumerate(PARCELAS):
        if puerta[1] == 0:       # tiendas: el frente abierto no usa coordenada
            puerta = (puerta[0], 0)
        casa(o, x0, z0, x1, z1, puerta, kind, ruina, seed=i)


# ------------------------------------------------------------------ foro y templo
def foro(o):
    for x in range(33, 64):
        for z in range(24, 61):
            o.s(x, 0, z, "cut_sandstone" if (x % 6 == 0 or z % 6 == 0) else "smooth_sandstone")
    o.f(33, 1, 24, 63, 5, 24, BASE)                      # muro del recinto del templo
    o.sup += 31 * 37
    for lado in (-1, 1):                                 # pórticos oeste y este
        back, col, eave = (33, 37, 38) if lado < 0 else (63, 59, 58)
        o.f(back, 1, 24, back, 7, 60, BASE)
        o.air(back, 1, 48, back, 4, 52)
        for z in range(25, 60, 3):
            if 47 <= z <= 52:
                continue
            o.f(col, 1, z, col, 4, z, "quartz_pillar[axis=y]")
        o.f(col, 5, 24, col, 5, 60, TRIM)
        lo, hi = sorted((back, col))
        o.f(lo + (1 if lado < 0 else 0), 5, 25, hi - (0 if lado < 0 else 1), 5, 59, CEIL)
        for x in range(min(back, eave), max(back, eave) + 1):
            d = abs(eave - x)
            for z in range(24, 61):
                o.slab(x, 6 + d // 2, z, "bottom" if d % 2 == 0 else "top", "brick_slab")
                if z in (24, 60) and x != eave and x != back:
                    for k in range(6, 6 + d // 2):
                        o.s(x, k, z, BASE)
        o.lantern(back - lado * 2, 4, 36); o.lantern(back - lado * 2, 4, 56)
    # columna caída del pórtico este (ruina) y tramo de cubierta perdido
    o.air(59, 1, 31, 59, 4, 31)
    o.s(59, 1, 31, "quartz_pillar[axis=y]")
    for z in range(30, 33):
        for x in range(58, 63):
            for y in range(5, 10):
                o.s(x, y, z, "air")
    for x in range(52, 57):
        o.s(x, 1, 32, "quartz_pillar[axis=x]")
    o.s(57, 1, 32, "chiseled_quartz_block")
    o.ruina += 5 * 3 + 6
    # fuente central
    o.ring(46, 48, 50, 52, 1, 1, "cut_sandstone")
    o.f(47, 1, 49, 49, 1, 51, "water")
    o.f(48, 1, 50, 48, 3, 50, "quartz_pillar[axis=y]")
    o.s(48, 4, 50, "chiseled_quartz_block")
    # farolas sobre pedestal a los lados de la escalinata
    for x in (39, 57):
        o.s(x, 1, 45, "chiseled_sandstone"); o.s(x, 2, 45, "cut_sandstone")
        o.s(x, 3, 45, "lantern[hanging=false,waterlogged=false]")
    # puestos de mercado
    for k, x0 in enumerate((51, 55)):
        for (x, z) in ((x0, 54), (x0 + 2, 54), (x0, 56), (x0 + 2, 56)):
            o.f(x, 1, z, x, 2, z, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
        for x in range(x0, x0 + 3):
            for z in range(54, 57):
                o.s(x, 3, z, ("red_wool", "white_wool")[(x + k) % 2])
        o.barrel(x0 + 1, 1, 56, "tienda")
        o.pot(x0 + 1, 1, 54, "north")
    templo(o)
    casa_fuente(o)


def templo(o):
    o.air(41, 1, 25, 55, 18, 43)
    o.f(41, 1, 25, 55, 2, 40, WALL)
    o.f(41, 3, 25, 55, 3, 40, "smooth_quartz")
    for z in range(25, 41):
        o.s(41, 1, z, BASE); o.s(55, 1, z, BASE)
    for x in (41, 42, 54, 55):                       # antas de la escalinata
        o.f(x, 1, 41, x, 3, 43, BASE)
    for k, z in enumerate((43, 42, 41)):
        for x in range(43, 54):
            o.f(x, 1, z, x, k, z, WALL) if k else None
            o.stair(x, k + 1, z, "north", "quartz_stairs")
    # favissa dentro del podio
    o.air(47, 1, 27, 52, 2, 29)
    o.chest(47, 1, 28, "east", "oculto")
    o.pot(48, 1, 29, "north"); o.pot(50, 1, 29, "north"); o.pot(52, 1, 29, "west")
    o.s(49, 1, 27, "candle[candles=3,lit=false,waterlogged=false]")
    for y in (1, 2):
        o.s(51, y, 27, "ladder[facing=south,waterlogged=false]")
    o.s(51, 3, 27, "spruce_trapdoor[facing=south,half=top,open=false,powered=false,waterlogged=false]")
    o.red["trampilla_favissa"] = (51, 3, 27)
    # cella y pronaos
    o.ring(43, 26, 53, 34, 4, 10, "quartz_block")
    o.air(47, 4, 34, 49, 7, 34)
    for x in range(43, 54, 2):
        o.f(x, 4, 40, x, 9, 40, "quartz_pillar[axis=y]"); o.s(x, 10, 40, "chiseled_quartz_block")
    for x in (43, 53):
        o.f(x, 4, 37, x, 9, 37, "quartz_pillar[axis=y]"); o.s(x, 10, 37, "chiseled_quartz_block")
    o.f(42, 11, 25, 54, 11, 41, "smooth_quartz")
    o.tejado(41, 24, 55, 42, 12, "z", hastial="smooth_quartz")
    o.f(47, 4, 27, 49, 4, 27, "smooth_quartz")
    o.f(48, 5, 27, 48, 6, 27, "quartz_pillar[axis=y]"); o.s(48, 7, 27, "chiseled_quartz_block")
    o.s(48, 4, 30, "chiseled_quartz_block"); o.s(48, 5, 30, "candle[candles=4,lit=false,waterlogged=false]")
    o.sign(44, 5, 30, "east", [("heraldia.unicas.acueducto.pista1", "El agua y la tierra"),
                              ("heraldia.unicas.acueducto.pista2", "sostienen la ciudad;"),
                              ("heraldia.unicas.acueducto.pista3", "el fuego"),
                              ("heraldia.unicas.acueducto.pista4", "la consume.")])
    o.chest(52, 4, 33, "west", "menor")
    o.s(45, 4, 32, "campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]")
    o.s(51, 4, 32, "campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]")
    o.lantern(46, 10, 30); o.lantern(50, 10, 30)
    o.sup += 15 * 19


def casa_fuente(o):
    x0, z0, x1, z1 = 38, 51, 44, 59
    o.f(x0, 0, z0, x1, 0, z1, "smooth_sandstone")
    o.ring(x0, z0, x1, z1, 1, 1, BASE); o.ring(x0, z0, x1, z1, 2, 4, WALL); o.ring(x0, z0, x1, z1, 5, 5, TRIM)
    o.f(x0 + 1, 5, z0 + 1, x1 - 1, 5, z1 - 1, CEIL)
    o.tejado(x0 - 1, z0 - 1, x1 + 1, z1 + 1, 6, "z")
    o.door(41, z0, "north"); o.s(41, 3, z0, WALL)
    o.sign(41, 3, z0 - 1, "north", [("heraldia.unicas.acueducto.cartel.cisterna", "CISTERNA")])
    o.stair(40, 0, 58, "south", "sandstone_stairs")
    o.air(40, 0, 56, 40, 0, 57)
    for z in (55, 56, 57):
        o.s(39, 1, z, "sandstone_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
        o.s(41, 1, z, "sandstone_wall[east=none,north=tall,south=tall,up=true,waterlogged=false,west=none]")
    o.ring(42, 52, 43, 54, 1, 1, "cut_sandstone")
    o.s(42, 1, 53, "water"); o.s(43, 1, 53, "water")
    o.s(43, 2, 53, "chiseled_sandstone")
    o.lantern(41, 4, 54)
    o.sup += 7 * 9


# ------------------------------------------------------------------ termas
def termas(o):
    x0, z0, x1, z1 = 66, 25, 92, 46
    o.f(x0, 0, z0, x1, 0, z1, "smooth_sandstone")
    o.ring(x0, z0, x1, z1, 1, 1, BASE); o.ring(x0, z0, x1, z1, 2, 7, "bricks"); o.ring(x0, z0, x1, z1, 8, 8, TRIM)
    o.f(x0 + 1, 8, z0 + 1, x1 - 1, 8, z1 - 1, "smooth_sandstone")
    o.tejado(x0 - 1, z0 - 1, x1 + 1, z1 + 1, 9, "x", hastial="bricks")
    o.f(67, 1, 35, 91, 7, 35, "bricks")            # tabiques
    o.f(78, 1, 26, 78, 7, 45, "bricks")
    o.f(85, 1, 36, 85, 7, 45, "bricks")
    for x in range(x0 + 3, x1 - 1, 4):
        o.s(x, 6, z0, "iron_bars"); o.s(x, 6, z1, "iron_bars")
    o.door(72, z1, "south"); o.s(72, 3, z1, "bricks")
    o.sign(73, 3, z1 + 1, "south", [("heraldia.unicas.acueducto.cartel.termas", "THERMAE")])
    o.air(71, 1, 35, 73, 3, 35)                     # apodyterium -> frigidarium
    o.air(78, 1, 40, 78, 3, 41)                     # apodyterium -> tepidarium
    o.door(85, 43, "east")                          # tepidarium -> praefurnium
    # apodyterium: bancos y taquillas
    for x in (68, 69, 70, 74, 75, 76):
        o.stair(x, 1, 36, "north")
    for z in range(37, 45):
        o.stair(67, 1, z, "west")
    o.barrel(77, 1, 44, "termas"); o.barrel(77, 1, 37, "menor")
    o.chest(68, 1, 45, "north", "termas")
    o.lantern(72, 7, 40)
    # frigidarium
    o.ring(69, 27, 75, 33, 1, 1, "cut_sandstone")
    o.f(70, 1, 28, 74, 1, 32, "water")
    o.lantern(72, 7, 30)
    for z in (27, 33):
        o.s(67, 1, z, "chiseled_sandstone"); o.s(67, 2, z, "quartz_pillar[axis=y]")
    # tepidarium y escalera al caldarium elevado
    for k, z in enumerate((37, 36, 35)):
        for x in (81, 82):
            o.f(x, 1, z, x, k, z, "bricks") if k else None
            o.stair(x, k + 1, z, "north", "brick_stairs")
            o.air(x, k + 2, z, x, 7, z)
    for z in range(37, 42):
        o.stair(84, 1, z, "east")
    o.s(80, 1, 44, "campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]")
    o.lantern(81, 7, 41)
    # caldarium sobre el hipocausto
    o.air(79, 1, 26, 91, 2, 34)
    for x in (81, 84, 87, 90):
        for z in (28, 31):
            o.f(x, 1, z, x, 2, z, "bricks")
    for x in range(79, 92):
        for z in range(26, 35):
            o.s(x, 3, z, "red_terracotta" if x in (79, 91) or z in (26, 34) else "white_terracotta")
    o.ring(83, 28, 89, 32, 4, 4, "cut_sandstone")
    o.f(84, 4, 29, 88, 4, 31, "water")
    o.s(80, 4, 30, "water_cauldron[level=3]")
    for x in range(80, 91):
        if x not in (81, 82):
            o.stair(x, 4, 26, "north")
    o.lantern(85, 7, 33); o.lantern(85, 7, 27)
    o.chest(79, 1, 26, "south", "oculto")           # hipocausto: sala oculta
    o.pot(91, 1, 26, "south"); o.s(91, 1, 34, "skeleton_skull[powered=false,rotation=0]")
    # praefurnium
    o.air(88, 1, 35, 88, 2, 35)                     # boca del hipocausto
    o.s(87, 1, 36, "furnace[facing=south,lit=false]"); o.s(89, 1, 36, "blast_furnace[facing=south,lit=false]")
    o.f(91, 1, 40, 91, 2, 44, "stripped_acacia_log[axis=z]")
    o.barrel(86, 1, 45, "menor"); o.barrel(91, 1, 37, None)
    o.s(86, 1, 37, "coal_block")
    o.lantern(88, 7, 41)
    # la bóveda del apodyterium se hundió en su lado oeste
    o.air(65, 8, 36, 72, 15, 47); o.s(72, 7, 40, "air")
    o.f(66, 8, 36, 66, 8, 46, TRIM)
    escombros(o, random.Random(11), 68, 37, 72, 44)
    o.ruina += 8 * 12
    o.sup += 27 * 22


# ------------------------------------------------------------------ villa del gobernador
def villa(o):
    x0, z0, x1, z1 = 4, 24, 30, 46
    o.f(x0, 0, z0, x1, 0, z1, "smooth_sandstone")
    jardin = lambda x, z: 11 <= x <= 23 and 25 <= z <= 29
    compl = lambda x, z: 16 <= x <= 18 and 40 <= z <= 41
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            if 13 <= x <= 21 and 33 <= z <= 35:
                o.s(x, 0, z, "white_terracotta" if (x + z) % 2 else "red_terracotta")
            elif 11 <= x <= 23 and 37 <= z <= 45:
                o.s(x, 0, z, "terracotta" if x in (11, 23) or z in (37, 45) else "white_terracotta")
    o.ring(x0, z0, x1, z1, 1, 1, BASE); o.ring(x0, z0, x1, z1, 2, 4, WALL); o.ring(x0, z0, x1, z1, 5, 5, TRIM)
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            if not (jardin(x, z) or compl(x, z)):
                o.s(x, 5, z, CEIL)
    ruina = lambda x, z: 24 <= x <= 31 and 41 <= z <= 47
    o.tejado(x0 - 1, z0 - 1, x1 + 1, z1 + 1, 6, "x",
             hueco=lambda x, z: jardin(x, z) or compl(x, z) or ruina(x, z))
    for x in range(25, 30):
        for z in range(41, 46):
            o.s(x, 5, z, "air")
    o.door(17, z1, "south"); o.s(17, 3, z1, WALL)
    o.sign(16, 3, z1 + 1, "south", [("heraldia.unicas.acueducto.cartel.villa", "DOMVS PRAEFECTI")])
    for z in range(z0 + 2, z1 - 1, 4):
        o.s(x0, 3, z, "iron_bars"); o.s(x1, 3, z, "iron_bars")
    # tabiques
    o.f(5, 1, 32, 29, 4, 32, WALL); o.air(15, 1, 32, 19, 3, 32)
    o.f(5, 1, 36, 29, 4, 36, WALL); o.air(15, 1, 36, 19, 3, 36)
    o.f(12, 1, 33, 12, 4, 35, WALL); o.f(22, 1, 33, 22, 4, 35, WALL)
    o.door(8, 32, "north"); o.door(26, 32, "north")
    o.f(10, 1, 37, 10, 4, 45, WALL); o.f(5, 1, 41, 9, 4, 41, WALL)
    o.door(10, 39, "west"); o.door(10, 43, "west")
    o.f(24, 1, 37, 24, 4, 45, WALL); o.air(24, 1, 40, 24, 3, 42)
    # peristilo y jardín
    for x in range(11, 24):
        for z in range(25, 30):
            o.s(x, 0, z, "grass_block[snowy=false]")
    rng = random.Random(7)
    for x in range(11, 24):
        for z in range(25, 30):
            if 15 <= x <= 19 and 26 <= z <= 28:
                continue
            r = rng.random()
            if r < 0.25:
                o.s(x, 1, z, rng.choice(["poppy", "allium", "azure_bluet", "cornflower", "short_grass"]))
    o.ring(15, 26, 19, 28, 1, 1, "cut_sandstone"); o.f(16, 1, 27, 18, 1, 27, "water")
    o.s(17, 1, 27, "chiseled_sandstone"); o.s(17, 2, 27, "potted_dead_bush")
    for x in range(10, 25, 2):
        o.f(x, 1, 30, x, 4, 30, "quartz_pillar[axis=y]")
    for z in (25, 27, 29):
        o.f(10, 1, z, 10, 4, z, "quartz_pillar[axis=y]"); o.f(24, 1, z, 24, 4, z, "quartz_pillar[axis=y]")
    o.lantern(7, 4, 28); o.lantern(27, 4, 28)
    for z in (26, 28, 30):
        o.stair(5, 1, z, "west"); o.stair(29, 1, z, "east")
    # culina (cocina)
    o.s(5, 1, 33, "smoker[facing=east,lit=false]"); o.s(5, 1, 34, "furnace[facing=east,lit=false]")
    o.barrel(6, 1, 35, "menor"); o.s(11, 1, 35, "crafting_table"); o.s(11, 1, 33, "water_cauldron[level=3]")
    o.pot(9, 1, 35, "north"); o.lantern(8, 4, 34)
    # tablinum
    o.s(17, 1, 33, "cartography_table"); o.stair(17, 1, 34, "south", "spruce_stairs")
    o.chest(13, 1, 33, "south", "villa"); o.s(21, 1, 33, "bookshelf"); o.s(21, 1, 35, "bookshelf")
    o.s(13, 1, 35, "lectern[facing=east,has_book=false,powered=false]")
    o.lantern(17, 4, 35)
    # biblioteca
    for z in (33, 34, 35):
        o.f(29, 1, z, 29, 3, z, "bookshelf")
    o.s(23, 1, 35, "lectern[facing=east,has_book=false,powered=false]"); o.chest(27, 1, 35, "north", "menor")
    o.lantern(26, 4, 34)
    # atrio con impluvio
    o.ring(15, 39, 19, 42, 1, 1, "cut_sandstone"); o.f(16, 1, 40, 18, 1, 41, "water")
    o.pot(11, 1, 37, "south"); o.pot(23, 1, 37, "south"); o.pot(11, 1, 45, "north"); o.pot(23, 1, 44, "west")
    o.lantern(13, 4, 41); o.lantern(21, 4, 41)
    # cubicula
    o.bed(5, 1, 38, "north", "red"); o.chest(9, 1, 37, "south", "villa"); o.pot(5, 1, 40, "east")
    o.bed(5, 1, 43, "north", "white"); o.barrel(9, 1, 45, "menor"); o.s(5, 1, 45, "potted_dead_bush")
    o.lantern(7, 4, 39); o.lantern(7, 4, 43)
    # triclinium (la mitad sur tiene el techo hundido)
    o.s(27, 1, 38, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
    o.s(27, 2, 38, "brown_carpet")
    o.stair(26, 1, 38, "west", "spruce_stairs"); o.stair(28, 1, 38, "east", "spruce_stairs")
    o.stair(27, 1, 37, "north", "spruce_stairs")
    o.lantern(27, 4, 39)
    escombros(o, random.Random(3), 25, 41, 29, 45)
    o.sup += 27 * 23
    o.ruina += 6 * 6


def construir(o):
    calles(o)
    parcelas(o)
    foro(o)
    termas(o)
    villa(o)
    muralla(o)
    # salida de las cloacas: reja de hierro en la calle norte
    o.s(79, 0, 20, "iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]")
    o.red["reja"] = (79, 0, 20)
