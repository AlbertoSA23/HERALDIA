"""Plantillas de la costa en coordenadas de diseño: x a lo ancho (0 en el eje), z hacia el mar (la orilla, el ancla, en
z = 0), y = 0 la fila inferior.

Faro (y = 0, la plataforma a ras del terreno más alto de la huella): la plataforma de 15 x 20 en tierra (z = -20..-1),
la torre de 7 x 7 junto a la orilla (z = -8..-2) con 28 bloques de alto, la casa del farero al fondo y el embarcadero de
3 x 11 sobre el agua (z = 0..10) con pilotes cada 3 bloques. La luz: una lámpara de redstone encendida sobre un bloque
de redstone en el centro de la linterna (y = 22-23), con piedra luminosa encima: siempre encendida, sin circuitos.

Naufragio (el galeón de 9 x 31, quilla en y = 0, bodega y = 2-4, cubierta y = 5, castillo de popa con el camarote y = 6-8,
mástil mayor hasta y = 17): encallado (a) con la proa en la playa (z = -14..16, `fila_mar` 1) o semihundido (b) en
aguas poco profundas (z = 8..38, `fila_mar` 4, con la bodega inundada). Partido por la mitad (z de 15 a 17 desde la
proa): sin cubierta y con el costado de estribor abierto. Bajo `fila_mar` no hay aire en la plantilla: lo que no es
casco queda sin poner (el agua o la arena del sitio se quedan)."""
from types import SimpleNamespace
from core import Template, B, F, NS, adult, anchored
from mediums import _common as c
from uniques._common import pieces

WIDTH = 7                     # la mitad de la plataforma del faro (x = -7..7)
DEPTH = 20                    # tierra del faro (z = -20..-1)
DOCK = 10                   # el embarcadero llega hasta z = 10
TOWER_Z = -5                  # centro de la torre
WALL_HEIGHT = 21                # la caña de la torre: y = 1..21
TUNNEL = 22                  # suelo de la galería (y = 22) y la linterna encima (y = 23-24)
HULL_LENGTH = 31


def _table(t, x, y, z, wood):
    t.set(x, y, z, f"{wood}_fence")
    t.set(x, y + 1, z, f"{wood}_pressure_plate[powered=false]")


# ------------------------------------------------------------------ faro
def ring_cells(is_square):
    """dentro(dx, dz, r): la planta de radio r de la torre, cuadrada o octogonal (las esquinas cortadas; r = 1, 3 x 3)."""
    if is_square:
        return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r
    return lambda dx, dz, r: abs(dx) <= r and abs(dz) <= r and (r <= 1 or abs(dx) + abs(dz) <= 2 * r - 1)


def _lighthouse(variant, p, name):
    """La plataforma y la torre: caña (r = 3) de y = 1 a 21 con el interior (r = 2) hueco, la sala de guardia en y = 12,
    la galería (r = 4, y = 22) con barandilla y el paseo sobre el muro, y la linterna (r = 2) acristalada con la luz."""
    t = Template(name)
    inside = ring_cells(variant == "b")
    m, foundation = p["madera"], p["cimiento"]
    # plataforma (y = 0) y aire encima: el terreno de la huella queda despejado
    for x in range(-WIDTH, WIDTH + 1):
        for z in range(-DEPTH, 0):
            t.set(x, 0, z, foundation[(x * 7 + z * 3 + x * z) % len(foundation)])
            for y in range(1, 5):
                t.set(x, y, z, "air")
            if p["nieve"] and (x * 5 + z * 11) % 7 == 0:
                t.set(x, 1, z, "snow[layers=1]")
    for dx in range(-4, 5):
        for dz in range(-4, 5):
            x, z = dx, TOWER_Z + dz
            if inside(dx, dz, 3) and not inside(dx, dz, 2):            # muro de la caña
                for y in range(1, WALL_HEIGHT + 1):
                    corner_block = variant == "b" and abs(dx) == 3 and abs(dz) == 3
                    if y == 1:
                        st = p["zocalo"]
                    elif corner_block:
                        st = f"{p['esquina']}[axis=y]" if p["esquina"].endswith(("_log", "_wood")) else p["esquina"]
                    elif variant == "a":
                        st = p["banda"] if y in (7, 8, 15, 16) else p["muro"]
                    else:
                        st = p["banda"] if (y // 3) % 2 == 1 else p["muro"]
                    t.set(x, y, z, f"{st}[axis=y]" if st.endswith("_wood") else st)
            elif inside(dx, dz, 2):                                     # interior hueco con el piso de la sala
                t.set(x, 0, z, foundation[0])
                for y in range(1, TUNNEL):
                    t.set(x, y, z, "air")
                t.set(x, 11, z, f"{m}_planks")
            if not inside(dx, dz, 4):
                continue
            # galería, barandilla, paseo y linterna
            if (dx, dz) != (0, 2):
                t.set(x, TUNNEL, z, p["zocalo"])
            if not inside(dx, dz, 3):
                t.set(x, TUNNEL + 1, z, f"{m}_fence")
            elif not inside(dx, dz, 2) or inside(dx, dz, 1) or (dx, dz) == (0, 2):
                for y in (TUNNEL + 1, TUNNEL + 2):
                    t.set(x, y, z, "air")
            else:
                for y in (TUNNEL + 1, TUNNEL + 2):
                    t.set(x, y, z, "glass_pane")
            if inside(dx, dz, 2):                                       # tejado de la linterna
                t.set(x, TUNNEL + 3, z, p["zocalo"] if inside(dx, dz, 1) else f"{p['losa']}[type=bottom,waterlogged=false]")
    # ventanas en tres caras (en la del mar, la sur, va la escalera por dentro)
    for y in (5, 9, 14, 18):
        for dx, dz in ((3, 0), (-3, 0), (0, -3)):
            t.set(dx, y, TOWER_Z + dz, "glass_pane")
    # puerta al norte (hacia la casa) y escalera de mano pegada al muro sur, de la planta baja a la galería
    c.door(t, 0, 1, TOWER_Z - 3, "south", f"{m}_door")
    for y in range(1, TUNNEL + 1):
        t.set(0, y, TOWER_Z + 2, "ladder[facing=north,waterlogged=false]")
    # la luz: bloque de redstone bajo la lámpara (siempre encendida) y piedra luminosa encima; el pararrayos en lo alto
    t.set(0, TUNNEL, TOWER_Z, "redstone_block")
    t.set(0, TUNNEL + 1, TOWER_Z, "redstone_lamp[lit=true]")
    t.set(0, TUNNEL + 2, TOWER_Z, "glowstone")
    t.set(0, TUNNEL + 4, TOWER_Z, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    if p["nieve"]:
        for dx, dz in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            t.set(dx, TUNNEL + 4, TOWER_Z + dz, "snow[layers=2]")
    # dentro: planta baja con toneles y farol; sala de guardia (y = 12) con el cofre y la mesa de cartografía
    t.set(-2, 1, TOWER_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    t.set(2, 1, TOWER_Z - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    c.lantern(t, 2, 1, TOWER_Z + 1, hanging=False)
    pieces.chest(c.put(t), -2, 12, TOWER_Z, "east", f"{NS}:costa/faro")
    t.set(2, 12, TOWER_Z, "cartography_table")
    c.lantern(t, 0, 21, TOWER_Z, hanging=True)
    c.lantern(t, 0, 10, TOWER_Z, hanging=True)
    return t


def _house(t, p, side):
    """Casa del farero de 7 x 6 al fondo de la plataforma (lado -1: al oeste; 1: al este), con la puerta al sur."""
    m, house = p["madera"], p["casa"]
    x0, x1 = (-6, 0) if side < 0 else (0, 6)
    z0, z1 = -18, -13
    c.box(t, x0, 1, z0, x1, 3, z1, house, corner_block=f"{p['tronco']}[axis=y]")
    t.fill(x0, 0, z0, x1, 0, z1, p["cimiento"][0])
    t.fill(x0, 4, z0, x1, 4, z1, f"{m}_planks")
    c.roof_tiles(t, x0, z0, x1, z1, 5, p["teja"], p["cumbrera"], house)
    door = (x0 + x1) // 2
    c.door(t, door, 1, z1, "north", f"{m}_door")
    c.window(t, x0, 2, -15)
    c.window(t, x1, 2, -15)
    c.window(t, door, 2, z0)
    # cama, mesa con silla, horno y el tonel del farero
    c.bed(t, x0 + 1, z0 + 1, "north", p["cama"])
    _table(t, x1 - 2, 1, z0 + 2, m)
    t.set(x1 - 1, 1, z0 + 2, f"{m}_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    t.set(x1 - 1, 1, z0 + 1, "furnace[facing=west,lit=false]")
    pieces.chest(c.put(t), x0 + 1, 1, z1 - 1, "east", f"{NS}:costa/faro", kind="barrel")
    c.lantern(t, door, 3, z0 + 3)
    # senda de la puerta a la torre
    for z in range(z1 + 1, TOWER_Z - 3):
        t.set(door, 0, z, p["cimiento"][1])
    if door != 0:
        for x in range(min(door, 0), max(door, 0) + 1):
            t.set(x, 0, TOWER_Z - 4, p["cimiento"][1])
    return door


def _pier(t, p):
    """Embarcadero de 3 x 11 (z = 0..10) a la altura de la plataforma, sobre pilotes cada 3 bloques (bajan al fondo)."""
    m = p["madera"]
    for z in range(-1, DOCK + 1):
        for x in (-1, 0, 1):
            t.set(x, 0, z, f"{m}_planks")
        if z >= 0 and (z % 3 == 0 or z == DOCK):
            for x in (-1, 1):
                t.set(x, 0, z, f"{p['tronco']}[axis=y]")
    for x in (-1, 0, 1):
        t.set(x, 1, DOCK, f"{m}_fence")
    t.set(-1, 1, DOCK - 1, f"{m}_fence")
    t.set(1, 1, DOCK - 1, f"{m}_fence")
    c.lantern(t, 1, 2, DOCK, hanging=False)
    t.set(-1, 1, 4, f"{m}_fence")                    # bolardo


def offers():
    """Tratos del farero: compra bacalao y algas secas, vende mapas vacíos, una brújula y un catalejo."""
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.offer({"id": "minecraft:cod", "count": 12}, em(1), 12),
            c.offer({"id": "minecraft:dried_kelp_block", "count": 6}, em(1), 12),
            c.offer(em(2), {"id": "minecraft:map", "count": 1}, 6),
            c.offer(em(4), {"id": "minecraft:compass", "count": 1}, 3),
            c.offer(em(6), {"id": "minecraft:spyglass", "count": 1}, 2)]


def lighthouse(variant, p, name):
    t = _lighthouse(variant, p, name)
    side = -1 if variant == "a" else 1
    door = _house(t, p, side)
    _pier(t, p)
    if variant == "a":                               # el farero, junto a su puerta
        n = {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
             "CustomName": pieces.text(f"{NS}.costa.farero", "Farero"), "CustomNameVisible": B(1),
             "VillagerData": {"profession": "minecraft:cartographer", "level": 2, "type": f"minecraft:{p['aldeano']}"},
             "Xp": 10, "Rotation": [F(0.0), F(0.0)], "Offers": {"Recipes": offers()}}
        t.entity(door, 1, -11, n)
    o = SimpleNamespace(t=t, anchor_point=(0, 0), sea_row=None, light=(0, TUNNEL + 1, TOWER_Z),
                        land=(-WIDTH, -DEPTH, WIDTH, -1), sea=(-1, 2, 1, DOCK), tunnel=TUNNEL, tower=TOWER_Z)
    return o


# ------------------------------------------------------------------ naufragio
def sleeve(s):
    """Media manga del casco a s bloques de la proa (0) hacia la popa (ESLORA - 1)."""
    return (0, 1, 2, 2, 3)[s] if s < 5 else 4 if s < 27 else 3


def _galleon(t, p, z0, sea_row, sunken):
    """El casco con la proa en z0 y la popa en z0 + ESLORA - 1. Bajo fila_mar no se pone aire."""
    m, trunk, band = p["madera"], p["tronco"], p["banda"]
    board = f"{m}_planks"
    air_block = lambda x, y, z: t.set(x, y, z, "air") if y > sea_row else None
    broken = lambda s: 15 <= s <= 17
    for s in range(HULL_LENGTH):
        z, h = z0 + s, sleeve(s)
        # quilla y fondo
        t.set(0, 0, z, f"{trunk}[axis=z]")
        for x in range(-max(h - 2, 0), max(h - 2, 0) + 1):
            if x:
                t.set(x, 0, z, board)
        # costados (y = 1 un bloque más adentro: la curva del casco) y suelo de la bodega
        for x in range(-h, h + 1):
            if abs(x) == max(h - 1, 0) and h > 0:
                t.set(x, 1, z, board)
            elif abs(x) < h - 1:
                t.set(x, 1, z, board)
        for y in range(2, 5):
            for x in range(-h, h + 1):
                if abs(x) == h:
                    if not (broken(s) and x > 0):               # estribor abierto en la rotura
                        t.set(x, y, z, band if y == 3 else board)
                elif not broken(s):
                    air_block(x, y, z)
        # cubierta (y = 5) y borda (y = 6)
        for x in range(-h, h + 1):
            if broken(s) and x >= -1:
                continue
            if (x, s) in ((0, 9), (0, 10)):
                air_block(x, 5, z)                                 # escotilla abierta a la bodega
            else:
                t.set(x, 5, z, board)
        if 8 <= s <= 21 and not broken(s) and s not in (14, 18):
            for x in (-h, h):
                t.set(x, 6, z, f"{m}_fence")
    # castillo de proa (y = 6) con su borda y un peldaño desde la cubierta
    for s in range(1, 8):
        for x in range(-sleeve(s), sleeve(s) + 1):
            t.set(x, 6, z0 + s, board)
        for x in (-sleeve(s), sleeve(s)):
            if sleeve(s):
                t.set(x, 7, z0 + s, f"{m}_fence")
    t.set(0, 6, z0 + 8, f"{m}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    for s in range(-3, 1):                                     # bauprés
        t.set(0, 6, z0 + s, f"{trunk}[axis=z]")
    # castillo de popa: el camarote (y = 6-8) con su puerta a proa y el techo con borda (y = 9-10)
    for s in range(22, HULL_LENGTH):
        z, h = z0 + s, sleeve(s)
        for x in range(-h, h + 1):
            edge_block = abs(x) == h or s in (22, HULL_LENGTH - 1)
            for y in range(6, 9):
                t.set(x, y, z, board if edge_block else "air")
            t.set(x, 9, z, board)
            if abs(x) == h or s == HULL_LENGTH - 1:
                t.set(x, 10, z, f"{m}_fence")
    c.door(t, 0, 6, z0 + 22, "south", f"{m}_door")
    for s in (25, 28):
        for x in (-sleeve(s), sleeve(s)):
            t.set(x, 7, z0 + s, "glass_pane")
    pieces.chest(c.put(t), -2, 6, z0 + 28, "east", f"{NS}:costa/camarote")
    _table(t, 2, 6, z0 + 26, m)
    t.set(2, 6, z0 + 27, f"{m}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    c.lantern(t, 0, 8, z0 + 26, hanging=True)
    # mástil mayor (y = 1..17) con la verga y la vela rota; el muñón del de mesana, partido en y = 9
    for y in range(1, 18):
        t.set(0, y, z0 + 12, f"{trunk}[axis=y]")
    for x in range(-4, 5):
        t.set(x, 15, z0 + 13, f"{trunk}[axis=x]")
    for x in range(-3, 4):
        for y in range(8, 15):
            if (x * 3 + y * 5) % 7 != 0 and not (y < 10 and (x + y) % 3 == 0):
                t.set(x, y, z0 + 13, p["vela"])
    for y in range(1, 10):
        t.set(0, y, z0 + 20, f"{trunk}[axis=y]")
    t.set(0, 10, z0 + 20, f"stripped_{trunk}[axis=y]")
    # en la bodega: el cofre (bajo el agua en el semihundido) y unos toneles
    pieces.chest(c.put(t), 2, 2, z0 + 6, "west", f"{NS}:costa/bodega", waterlogged=sunken)
    if not sunken:
        t.set(-2, 2, z0 + 6, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
        t.set(-2, 2, z0 + 10, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    if p["nieve"]:
        for s in range(9, 22):
            for x in range(-sleeve(s) + 1, sleeve(s)):
                if not broken(s) and (x * 7 + s * 3) % 5 == 0 and t.get(x, 6, z0 + s) is None \
                        and "planks" in (t.get(x, 5, z0 + s) or ""):
                    t.set(x, 6, z0 + s, "snow[layers=1]")


def shipwreck(variant, p, name):
    t = Template(name)
    sunken = variant == "b"
    if sunken:
        z0, row = 8, 4
    else:
        z0, row = -14, 1
    _galleon(t, p, z0, row, sunken)
    if sunken:                                       # el ahogado de la bodega inundada, anclado y adulto
        n = {"id": "minecraft:drowned", "PersistenceRequired": B(1), "Rotation": [F(180.0), F(0.0)]}
        t.entity(-2, 2, z0 + 4, anchored(adult(n), always=True))
        land, sea = (-2, -6, 2, -2), (-4, z0, 4, z0 + HULL_LENGTH - 1)
    else:
        land, sea = (-3, z0, 3, -3), (-3, 3, 3, z0 + HULL_LENGTH - 1)
    return SimpleNamespace(t=t, anchor_point=(0, 0), sea_row=row, light=None, land=land, sea=sea, bow=z0)


def construct(kind, variant, palette, name):
    return (lighthouse if kind == "faro" else shipwreck)(variant, palette, name)
