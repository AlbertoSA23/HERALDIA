"""Cripta y osarios (pieza bajo tierra), mecanismos de redstone, trampas, generadores, guardián,
campanario, aguja y daños de ruina. Las piezas salen de tools/gen/unicas/_comun/piezas.py."""
import math
from core import B, F
from lint import passable, top_height, bname
from .base import *
from .._comun import piezas

FLOOR, TOP = -8, -1
ROOMS = [  # nombre, x0, x1, z0, z1, cota superior del aire
    ("sala", 60, 70, 22, 38, -3), ("cámara oeste", 50, 57, 26, 34, -3), ("paso oeste", 58, 59, 30, 30, -6),
    ("eje del osario", 71, 96, 29, 31, -3),
    ("rama N1", 77, 79, 20, 28, -3), ("rama N2", 85, 87, 20, 28, -3), ("bucle N", 77, 87, 20, 22, -3),
    ("rama S1", 77, 79, 32, 40, -3), ("rama S2", 85, 87, 32, 40, -3), ("bucle S", 77, 87, 38, 40, -3),
    ("osario de los esqueletos", 81, 83, 16, 18, -4), ("paso N", 82, 82, 19, 19, -6),
    ("galería hundida", 81, 83, 42, 44, -4), ("paso S", 82, 82, 41, 41, -6),
    ("pasadizo estrecho", 97, 101, 30, 30, -6),
    ("antecámara de los sellos", 102, 114, 24, 30, -3), ("cámara del tesoro", 102, 114, 35, 41, -3),
    ("relicario", 89, 93, 24, 27, -4),
]
# tres virtudes abren; la codicia es una palanca trampa (dispara una flecha desde detrás de su cartel)
LEVERS = [(107, "codicia", False), (109, "fe", True), (111, "esperanza", True), (113, "caridad", True)]


def crypt(c):
    interior = set()
    for (_, x0, x1, z0, z1, top) in ROOMS:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(FLOOR + 1, top + 1):
                    interior.add((x, y, z))
    # escaleras desde los brazos del crucero y pozo del relicario
    for (x, y, z), (st, _) in list(c.t.blocks.items()):
        if y < 0 and 63 < x < 67 and (14 <= z <= 21 or 39 <= z <= 46):
            if bname(st) == "air":
                interior.add((x, y, z))
    for y in range(FLOOR + 1, 0):
        interior.add((91, y, 27))
    cols = {(x, z) for (x, y, z) in interior}
    shell = set()
    for (x, z) in cols:
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                shell.add((x + dx, z + dz))
    stairwell = lambda x, z: 63 <= x <= 67 and (14 <= z <= 22 or 38 <= z <= 46)
    for (x, z) in shell:
        for y in range(FLOOR, TOP + 1):
            if (x, y, z) in interior:
                continue
            if stairwell(x, z) and c.get(x, y, z) is not None:
                continue
            if 14 <= z <= 21 and 64 <= x <= 66 or 39 <= z <= 46 and 64 <= x <= 66:
                if c.get(x, y, z) is not None:
                    continue
            c.set(x, y, z, PA if y == FLOOR else (SB if (x * 7 + y * 3 + z) % 9 else "tuff_bricks"))
    for p in interior:
        if not (63 < p[0] < 67 and (14 <= p[2] <= 21 or 39 <= p[2] <= 46)):
            c.set(*p, "air")
    c.crypt_interior = interior
    hall(c)
    ossuary(c)
    reliquary(c)
    treasury(c)


def hall(c):
    # pilares, sepulcros de obispos, altar y luz tenue
    for x in (62, 68):
        for z in (25, 35):
            c.fill(x, -7, z, x, -3, z, PA)
            c.set(x, -3, z, CSB)
    for (x0, z0) in ((61, 27), (67, 27), (61, 32), (67, 32)):
        for x in range(x0, x0 + 3):
            c.set(x, -7, z0, PA)
            c.set(x, -6, z0, slab("smooth_stone", "bottom"))
    c.set(65, -7, 30, CSB)
    c.set(65, -6, 30, "smooth_quartz")
    c.candles(65, -5, 30, 4)
    for (x, z) in ((61, 23), (69, 23), (61, 37), (69, 37)):
        c.hang(x, -3, z, -2, soul=True)
    c.chest(60, -7, 24, "east", "cripta", "cripta, nicho noroeste")
    c.chest(70, -7, 36, "west", "cripta", "cripta, nicho sureste")
    # cámara oeste: generador de zombis, a oscuras
    piezas.spawner(c.set, *(53, -7, 30), "zombie")
    c.spawners.append(((53, -7, 30), "zombie"))
    for (x, z) in ((51, 27), (56, 33), (51, 33)):
        c.set(x, -7, z, "bone_block")
    c.set(51, -6, 27, s("skeleton_skull", rotation=4))


def ossuary(c):
    oss = [r for r in ROOMS if r[0].startswith(("eje", "rama", "bucle"))]
    def inside(x, y, z):
        return (x, y, z) in c.crypt_interior
    # paredes de huesos con calaveras en hornacinas
    for (_, x0, x1, z0, z1, top) in oss:
        for x in range(x0 - 1, x1 + 2):
            for z in range(z0 - 1, z1 + 2):
                if x < 72:
                    continue
                for y in range(-7, -3):
                    if not inside(x, y, z) and c.get(x, y, z) in ("minecraft:stone_bricks", "minecraft:tuff_bricks"):
                        c.set(x, y, z, s("bone_block", axis="y"))
    for x in range(74, 96, 3):
        for z in (28, 32):
            if c.get(x, -6, z) and not inside(x, -6, z) and x not in (77, 78, 79, 85, 86, 87, 82):
                c.set(x, -6, z, s("skeleton_skull", rotation=8 if z == 28 else 0))
    for (x, z) in ((84, 37), (80, 23)):
        c.hang(x, -3, z, -2, soul=True)
    c.hang(90, -3, 30, -2, soul=True)
    c.chest(84, -7, 20, "south", "osario", "osario, bucle norte")
    # generadores: esqueletos (norte) y arañas de cueva entre telarañas (sur, galería hundida)
    piezas.spawner(c.set, *(82, -7, 17), "skeleton")
    c.spawners.append(((82, -7, 17), "skeleton"))
    piezas.spawner(c.set, *(82, -7, 43), "cave_spider")
    c.spawners.append(((82, -7, 43), "cave_spider"))
    for (x, y, z) in ((81, -7, 42), (83, -6, 44), (81, -5, 44), (83, -5, 42), (82, -4, 42)):
        c.set(x, y, z, "cobweb")
    for (x, y, z) in ((81, -7, 44),):
        c.set(x, y, z, "gravel")
        c.ruin.add((x, y, z))
    # trampa 1: cable trampa en el eje (x = 82) con un dispensador de flechas sobre cada gancho
    piezas.tripwire_trap(c.set, (82, 28), (82, 32), -7, "z", [((82, -6, 28), "south"), ((82, -6, 32), "north")])
    c.mech.append({"tipo": "cable trampa", "sitio": "eje del osario", "ganchos": [(82, -7, 28), (82, -7, 32)],
                   "cable": [(82, -7, z) for z in (29, 30, 31)], "dispensadores": [(82, -6, 28), (82, -6, 32)]})
    # trampa 2: placa de presión en el pasadizo estrecho, dispensadores a ras de suelo
    piezas.plate_trap(c.set, [(99, -7, 30)], "south", arrows=16)
    c.mech.append({"tipo": "placa de presión", "sitio": "pasadizo estrecho", "placa": (99, -7, 30),
                   "dispensadores": [(99, -7, 29), (99, -7, 31)]})


def reliquary(c):
    """Relicario oculto bajo el altar mayor: trampilla de hierro en el estrado, palanca junto a ella y escala."""
    for y in range(-7, 1):
        c.set(91, y, 27, s("ladder", facing="north"))
    c.set(91, 1, 27, s("iron_trapdoor", facing="north", half="top", open=False, powered=False))
    c.set(91, 2, 26, s("lever", face="floor", facing="north", powered=False))
    c.mech.append({"tipo": "trampilla", "sitio": "estrado del altar mayor", "trampilla": (91, 1, 27),
                   "palanca": (91, 2, 26), "apoyo": (91, 1, 26)})
    c.set(89, -7, 26, CSB)
    c.set(89, -6, 26, s("skeleton_skull", rotation=12))
    c.set(93, -7, 26, CSB)
    c.candles(93, -6, 26, 3)
    c.chest(89, -7, 24, "east", "oculto", "relicario bajo el altar mayor")
    c.set(93, -7, 24, "gold_block")
    c.candles(93, -6, 24, 2)


def piston_door(c, nombre, door, axis, sign, levers):
    rec = piezas.combo_door(c.set, door, axis, sign, levers, nombre)
    c.mech.append(rec)
    return rec


def treasury(c):
    # sellos (palancas) de la antecámara, en el muro de cuatro de grueso (z 31..34) de la cámara del tesoro
    for (lx, name, ok) in LEVERS:
        c.set(lx, -6, 31, CSB)
        sign(c, lx, -5, 30, "north", [f"heraldia.unicas.catedral.sello.{name}"])
    for (x, z) in ((105, 24), (113, 24), (103, 24)):
        c.candles(x, -7, z, 3)
    sign(c, 102, -5, 27, "east", ["heraldia.unicas.catedral.sello.pista1",
          "heraldia.unicas.catedral.sello.pista2"])
    for dy in (0, 1):
        for zz in (31, 32, 34):
            c.set(103, -7 + dy, zz, "air")
        c.set(103, -7 + dy, 33, CSB)
    piston_door(c, "cámara del tesoro", (103, -7, 33), "x", 1,
                [((lx, -6, 30), (lx, -6, 31)) for (lx, _, ok) in LEVERS if ok])
    piezas.lever_trap(c.set, (107, -6, 30), (107, -6, 31), (107, -5, 31), "north")
    c.mech.append({"tipo": "palanca trampa", "sitio": "sello de la codicia", "apoyo": (107, -6, 31),
                   "palanca": (107, -6, 30), "dispensadores": [(107, -5, 31)]})
    # cámara del tesoro: cofre principal, dos cofres laterales y el guardián
    c.chest(108, -7, 41, "north", "premium", "cámara del tesoro (cofre principal)")
    c.chest(104, -7, 41, "north", "tesoro", "cámara del tesoro, oeste")
    c.chest(112, -7, 41, "north", "tesoro", "cámara del tesoro, este")
    for x in (106, 110):
        c.set(x, -7, 41, CSB)
        c.candles(x, -6, 41, 4)
    for (x, z) in ((102, 35), (114, 35)):
        c.set(x, -7, z, CSB)
        c.lamp(x, -6, z, soul=True)
    c.entities.append((108, -7, 38, guardian()))


def guardian():
    return piezas.guardian("skeleton", "heraldia.unicas.catedral.guardian", "Fray Osmundo, custodio del tesoro", 40.0, 4.0,
                          {"mainhand": {"id": "minecraft:bow", "count": 1,
                                        "components": {"minecraft:enchantments": {"minecraft:power": 2}}},
                           "head": {"id": "minecraft:chainmail_helmet", "count": 1},
                           "chest": {"id": "minecraft:golden_chestplate", "count": 1}},
                          {"mainhand": 0.15, "head": 0.15, "chest": 0.25})


def sign(c, x, y, z, facing, keys):
    from .botin import LANG
    piezas.sign(c.set, x, y, z, facing, [piezas.text(k, LANG["es_es"][k]) for k in keys], wood="oak")


# ---------------------------------------------------------------------- superficie: detalles finales
def library_door(c):
    """Gabinete secreto: puerta de estantería de una palanca (lever_door común), escondida entre estanterías."""
    for z in range(5, 11):
        for y in range(9, 12):
            c.set(86, y, z, "bookshelf")
    m = piezas.lever_door(c.set, (87, 9, 9), "north", "west", "bookshelf", SB)
    c.set(88, 9, 9, "air")
    c.set(88, 10, 9, "air")
    (x, y, z), lv, tc = m["door"], m["lever"], m["torch"]
    c.mech.append({"tipo": "puerta de pistones", "sitio": "gabinete secreto de la biblioteca",
                   "puerta": [(x, y, z), (x, y + 1, z)], "cabezas": [(x, y, z - 1), (x, y + 1, z - 1)],
                   "pistones": [(x, y, z - 2), (x, y + 1, z - 2)], "antorchas": [tc], "polvo": [],
                   "palancas": [(lv, (lv[0] + 1, lv[1], lv[2]))], "falsas": []})


def belfry(c):
    for z in range(14, 22):
        c.set(15, 45, z, s("dark_oak_log", axis="z"))
    for z in (16, 20):
        c.set(15, 44, z, s("bell", attachment="ceiling", facing="west", powered=False))
    c.chest(9, 40, 21, "east", "campanario", "campanario (torre norte)")
    c.lamp(13, 40, 14)


def south_tower_ruin(c):
    for x in range(13, 16):
        for z in range(39, 42):
            c.set(x, 55, z, "air")
            c.ruin.add((x, 55, z))
    for (x, z, b) in ((13, 40, "cobblestone"), (14, 39, "gravel"), (15, 41, "cracked_stone_bricks"), (14, 41, "cobblestone")):
        c.set(x, 40, z, b)
        c.ruin.add((x, 40, z))
    for (x, z) in ((17, 48), (16, 48), (6, 48), (17, 44), (17, 45), (11, 48), (6, 41)):
        for y in range(56, 61):
            if c.get(x, y, z):
                c.set(x, y, z, "air")
                c.ruin.add((x, y, z))


def spire(c):
    cx, cz = 65, 30
    for y in range(41, 47):
        for x in range(cx - 2, cx + 3):
            for z in range(cz - 2, cz + 3):
                corner = abs(x - cx) == 2 and abs(z - cz) == 2
                c.set(x, y, z, "polished_deepslate" if not corner else "deepslate_tiles")
    for (x, z) in ((cx - 2, cz - 2), (cx + 2, cz - 2), (cx - 2, cz + 2), (cx + 2, cz + 2)):
        c.set(x, 47, z, "deepslate_tile_wall")
        c.set(x, 48, z, "deepslate_tile_wall")
    for y in range(47, 55):
        for x in range(cx - 1, cx + 2):
            for z in range(cz - 1, cz + 2):
                c.set(x, y, z, ROOF)
    for y in range(55, 68):
        c.set(cx, y, cz, "polished_deepslate")
    c.set(cx, 68, cz, s("lightning_rod", facing="up"))
    for (dx, dz, f) in ((0, -1, "north"), (0, 1, "south"), (-1, 0, "west"), (1, 0, "east")):
        c.set(cx + dx, 55, cz + dz, stairs("deepslate_tile", MIRROR.get(f) or {"west": "east", "east": "west"}[f]))


def ruin_details(c):
    # vidrieras rotas en el claristorio sur y huecos en el pretil de la terraza sur
    for x in (43, 44, 45, 50):
        for y in range(18, 23):
            if "pane" in (c.get(x, y, 36) or ""):
                c.set(x, y, 36, "air")
                c.ruin.add((x, y, 36))
    for (x, z) in ((37, 42), (38, 42), (52, 42), (25, 42)):
        c.set(x, 17, z, "air")
        c.ruin.add((x, 17, z))
    # boquete en la cubierta de la nave (sur), con el desván a la vista
    for x in (44, 45, 46):
        for z in (32, 33):
            for y in range(32, 38):
                if c.get(x, y, z) == "minecraft:deepslate_tiles":
                    c.set(x, y, z, "air")
                    c.ruin.add((x, y, z))
    c.set(45, 28, 33, "cobblestone")
    c.set(44, 28, 32, "gravel")
    # panda sur del claustro hundida en parte
    for x in range(40, 47):
        for z in range(73, 77):
            for y in (6, 7, 8):
                if c.get(x, y, z):
                    c.set(x, y, z, "air")
                    c.ruin.add((x, y, z))
    for (x, z, b) in ((41, 74, "cobblestone"), (43, 75, "mossy_cobblestone"), (46, 74, "gravel"), (44, 73, "moss_carpet")):
        c.set(x, 1, z, b)
        c.ruin.add((x, 1, z))
    for (x, z) in ((43, 72), (46, 72)):
        for y in range(2, 7):
            c.set(x, y, z, "air")
            c.ruin.add((x, y, z))
        c.set(x, 1, z, "cobblestone")
