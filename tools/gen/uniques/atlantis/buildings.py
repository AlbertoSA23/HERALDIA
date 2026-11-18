"""Edificios genéricos de la Atlántida. Sistema local de Vista: fachada en v = 0, y = 0 es el pavimento."""
from . import urban_layout as U
from . import things as C
from .._common import pieces as P

BRICK, DARK, PRISMARINE, LANTERN = "prismarine_bricks", "dark_prismarine", "prismarine", "sea_lantern"
GLASS, QUARTZ, PILLAR = "light_blue_stained_glass", "quartz_bricks", "quartz_pillar[axis=y]"
PUERTA = "warped_door"
CORALS = ("tube_coral_block", "brain_coral_block", "bubble_coral_block", "fire_coral_block", "horn_coral_block")


def h(u, v, salt):
    return U.dispersion(u, v, salt)


def door(v, u, y, w, facing, material=PUERTA, hinge="left"):
    """Puerta cerrada (pieza común); mira = hacia dónde mira quien sale por ella (cara exterior)."""
    P.door(v.set, u, y, w, facing, kind=material, hinge=hinge)


def column(v, u, w, y1, y2):
    v.set(u, y1, w, QUARTZ)
    v.fill(u, y1 + 1, w, u, y2 - 1, w, PILLAR)
    v.set(u, y2, w, "chiseled_quartz_block")


def deck(v, w, d, y, style):
    """Cubierta sobre el forjado y: 0 = azotea con peto, 1 = escalonada."""
    if style == 0:
        for u in range(w):
            for z in range(d):
                if (u in (0, w - 1) or z in (0, d - 1)) and (u + z) % 2 == 0:
                    v.set(u, y + 1, z, DARK)
    else:
        k = 1
        while 2 * k < min(w, d) - 1 and k <= 3:
            v.fill(k, y + k, k, w - 1 - k, y + k, d - 1 - k, DARK if k % 2 else BRICK)
            k += 1
        v.set(w // 2, y + k, d // 2, LANTERN)


def furniture(v, w, d, y, salt):
    """Planta seca: muebles pegados a los muros, centro libre. Devuelve la celda del cofre (o None)."""
    kind = h(v.ox, v.oz, salt) % 3
    if kind == 0:      # dormitorio
        v.set(1, y, d - 2, "cyan_bed[facing=south,part=head]")
        v.set(1, y, d - 3, "cyan_bed[facing=south,part=foot]")
        v.set(2, y, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
    elif kind == 1:    # taller
        v.set(1, y, d - 2, "crafting_table")
        v.set(2, y, d - 2, "smithing_table")
        v.set(3, y, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
    else:              # estudio
        v.fill(1, y, d - 2, 3, y + 1, d - 2, "bookshelf")
        v.set(w - 2, y, d - 2, "lectern[facing=north]", {"id": "minecraft:lectern"})
    v.set(w - 2, y, 1, "decorated_pot", {"id": "minecraft:decorated_pot"})
    return (w - 2, y, d - 3)


def house(v, w, d, dry=True, salt=0, cofre=None, name="casa"):
    """Casa de dos plantas (5 de alto cada una). seca: planta alta seca por piscina lunar o baja seca con puerta."""
    y1, y2 = 5, 10
    v.shell(0, 0, 0, w - 1, y2, d - 1, BRICK, floor=DARK, roof=DARK)
    v.fill(0, y1, 0, w - 1, y1, d - 1, DARK)
    for u, z in ((0, 0), (w - 1, 0), (0, d - 1), (w - 1, d - 1)):          # esquinas de cuarzo
        v.fill(u, 1, z, u, y2 - 1, z, QUARTZ)
    cu = w // 2
    variant = h(v.ox, v.oz, salt + 1) % 2 if dry else 0
    for side in (0, w - 1):                                               # ventanas altas
        v.fill(side, y1 + 2, d // 2 - 1, side, y1 + 3, d // 2 + 1, GLASS)
    v.fill(cu - 1, y1 + 2, 0, cu + 1, y1 + 3, 0, GLASS)
    v.set(cu, 3, 0, LANTERN)                                             # dintel iluminado
    if dry and variant == 1:
        # planta baja seca con puerta a la calle y escalera de mano a la alta
        v.air(1, 1, 1, w - 2, y1 - 1, d - 2)
        v.air(1, y1 + 1, 1, w - 2, y2 - 1, d - 2)
        door(v, cu, 1, 0, "north")
        v.air(w - 2, y1, d - 2, w - 2, y1, d - 2)
        for y in range(1, y1 + 1):
            v.set(w - 2, y, d - 2, "ladder[facing=north]")
        v.set(1, y1 - 1, 1, LANTERN)
        v.set(1, y2 - 1, 1, LANTERN)
        free = furniture(v, w, d - 1, y1 + 1, salt)
        v.set(1, 1, d - 2, "barrel[facing=up]", {"id": "minecraft:barrel"})
        v.mark("seca", 1, 1, 1)
        v.mark("seca", cu, y1 + 1, 2)
    elif dry:
        # planta baja inundada y abierta; alta seca por piscina lunar
        v.remove(cu, 1, 0, cu, 2, 0)
        v.air(1, y1 + 1, 1, w - 2, y2 - 1, d - 2)
        v.remove(cu, y1, 2, cu + 1, y1, 3)
        v.fill(cu, y1, 2, cu + 1, y1, 3, "water")
        v.set(1, y2 - 1, 1, LANTERN)
        v.set(w - 2, y2 - 1, d - 2, LANTERN)
        free = furniture(v, w, d, y1 + 1, salt)
        v.mark("seca", cu, y1 + 1, 4)
        v.mark("agua", cu, y1, 2)
    else:
        # inundada: portal abierto, hueco en el forjado, sin cristales (se nada por dentro)
        v.remove(cu, 1, 0, cu, 2, 0)
        v.remove(cu - 1, y1, d // 2 - 1, cu + 1, y1, d // 2 + 1)
        v.remove(cu - 1, y1 + 2, 0, cu + 1, y1 + 3, 0)
        v.set(1, y1 - 1, 1, LANTERN)
        v.set(w - 2, y2 - 1, d - 2, LANTERN)
        free = (w - 2, y1 + 1, d - 2)
    deck(v, w, d, y2, h(v.ox, v.oz, salt + 2) % 2)
    if cofre:
        C.cofre(v, *free, "north" if free[2] > 1 else "south", cofre)
    v.site(name, 0, 0, 0, w - 1, y2 + 4, d - 1)
    return free


def ruin_piece(v, w, d, salt=0, cofre=None):
    """Casa derruida e inundada: muros a media altura, escombros, coral y algas."""
    y2 = 10
    for u in range(w):
        for z in range(d):
            edge_block = u in (0, w - 1) or z in (0, d - 1)
            v.set(u, 0, z, DARK if h(u + v.ox, z + v.oz, salt) % 5 else "gravel")
            if edge_block:
                height = 2 + h((u + v.ox) >> 1, (z + v.oz) >> 1, salt + 3) % 7
                for y in range(1, min(height, y2) + 1):
                    r = h(u + v.ox + y * 31, z + v.oz, salt + 4) % 10
                    v.set(u, y, z, BRICK if r < 6 else PRISMARINE if r < 9 else "mossy_cobblestone")
            else:
                r = h(u + v.ox, z + v.oz, salt + 5) % 40
                if r < 3:
                    v.set(u, 1, z, CORALS[r % 5])
                elif r < 6:
                    height = 2 + r
                    for y in range(1, height):
                        v.set(u, y, z, "kelp_plant")
                    v.set(u, height, z, "kelp[age=25]")
                elif r < 8:
                    v.set(u, 1, z, "sea_pickle[pickles=3,waterlogged=true]")
                elif r < 10:
                    v.set(u, 1, z, BRICK)
    v.remove(w // 2, 1, 0, w // 2, 3, 0)
    if cofre:
        C.cofre(v, w - 2, 1, d - 2, "north", cofre)
    v.site("ruina", 0, 0, 0, w - 1, y2, d - 1, ruinous=True)


def tower(v, r=5, salt=0, cofre=None):
    """Torre redonda de tres cuerpos con cúpula; arriba, sala seca a la que se sube buceando por el hueco central."""
    c = r
    height = 16
    v.disk(c, c, r, 0, 0, DARK)
    v.disk(c, c, r, 1, height, BRICK, cavity=r - 1)
    for y in (5, 10):
        v.disk(c, c, r, y, y, DARK, cavity=r - 1)
    v.disk(c, c, r - 1, 11, 11, DARK)                      # forjado de la sala alta
    v.disk(c, c, r - 1, height, height, DARK)
    v.remove(c, 1, 0, c, 2, 0)                                # portal
    v.set(c, 3, 0, LANTERN)
    for u in range(c - r + 1, c + r):
        for z in range(c - r + 1, c + r):
            if (u - c) ** 2 + (z - c) ** 2 <= (r - 1 + 0.3) ** 2:
                v.air(u, 12, z, u, height - 1, z)
    v.fill(c, 11, c, c, 11, c, "water")                       # piscina lunar (1 x 1 basta para subir)
    v.fill(c + 1, 11, c, c + 1, 11, c, "water")
    for side in ((c, 13, 0), (c, 13, 2 * r), (0, 13, c), (2 * r, 13, c)):
        v.set(*side, GLASS)
        v.set(side[0], 14, side[2], GLASS)
    v.set(c, height, c, LANTERN)
    v.dome(c, c, r, height + 1, DARK, rib=BRICK)
    v.set(c, height + r + 1, c, LANTERN)
    if cofre:
        C.cofre(v, c, 12, c + r - 2, "north", cofre)
    v.mark("seca", c - 1, 12, c - 1)
    v.mark("agua", c, 11, c)
    v.site("torre", 0, 0, 0, 2 * r, height + r + 2, 2 * r)


def small_plaza(v, side=9, salt=0):
    """Templete abierto: cuatro columnas, linterna central y una fuente de coral."""
    c = side // 2
    v.fill(0, 0, 0, side - 1, 0, side - 1, BRICK)
    v.fill(1, 0, 1, side - 2, 0, side - 2, DARK)
    for u, z in ((1, 1), (side - 2, 1), (1, side - 2), (side - 2, side - 2)):
        column(v, u, z, 1, 6)
    v.fill(0, 7, 0, side - 1, 7, side - 1, DARK)
    v.fill(2, 8, 2, side - 3, 8, side - 3, BRICK)
    v.set(c, 7, c, LANTERN)
    v.set(c, 1, c, CORALS[h(v.ox, v.oz, salt) % 5])
    v.set(c, 2, c, LANTERN)
    v.site("plazuela", 0, 0, 0, side - 1, 8, side - 1)


def ornament(v, u1, w1, u2, w2, y1, y2, step=6, parapet=True):
    """Articula una caja lisa sin tocar su estanqueidad: pilastras de cuarzo en esquinas y cada «paso», zócalo oscuro y
    peto almenado. Solo sustituye ladrillo de muro (respeta puertas, cristales y mecanismos)."""
    def wall(u, y, w):
        return v.built(u, y, w) == "minecraft:prismarine_bricks"
    for u in range(u1, u2 + 1):
        for w in range(w1, w2 + 1):
            if not (u in (u1, u2) or w in (w1, w2)):
                continue
            corner_block = u in (u1, u2) and w in (w1, w2)
            a = (u - u1) if w in (w1, w2) else (w - w1)
            length = (u2 - u1) if w in (w1, w2) else (w2 - w1)
            pilaster = corner_block or (a % step == 0 and 0 < a < length)
            for y in range(y1 + 1, y2):
                if wall(u, y, w):
                    if pilaster:
                        v.set(u, y, w, QUARTZ)
                    elif y == y1 + 1:
                        v.set(u, y, w, DARK)
            if parapet and (pilaster or (a % 2 == 0)) and v.built(u, y2 + 1, w) is None:
                v.set(u, y2 + 1, w, DARK if not pilaster else QUARTZ)


def windows(v, constant, axis, a, b, y1, y2, step=6):
    """Ventanas de cristal macizo de 2 de ancho en un muro (eje 'u': muro w = fijo, de u = a a b; eje 'w': muro u = fijo)."""
    for t in range(a + 3, b - 2, step):
        for k in (0, 1):
            for y in range(y1, y2 + 1):
                u, w = (t + k, constant) if axis == "u" else (constant, t + k)
                if v.built(u, y, w) == "minecraft:prismarine_bricks":
                    v.set(u, y, w, GLASS)
