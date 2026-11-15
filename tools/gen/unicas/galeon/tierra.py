"""Suelo propio, campamento de náufragos y peñón con la cueva del tesoro (coordenadas de diseño)."""
from .comun import SC, ZMIN
from .barco import in_hull, hw

ZMAX = 76
CAMP_X = (24, 55)
# peñón: superelipse centrada en (11, 46)
PX, PZ, RX, RZ = 11, 46, 14, 30


def suelo(o):
    """Arena de 4 de grosor con base de arenisca hasta el casco y lecho bajo la quilla; aire que rebaja dunas."""
    for z in range(ZMIN, ZMAX + 1):
        for x in range(CAMP_X[0], SC):
            for y in range(-6, 1):
                if x > CAMP_X[1] and not (0 <= z <= 61 and x < SC - hw(y, z)):
                    continue
                if in_hull(x, y, z):
                    continue
                o.s(x, y, z, "sand" if y >= -3 else "sandstone")
            if x <= CAMP_X[1]:
                o.air(x, 1, z, x, 6, z)
    for z in range(0, 62):
        for x in range(SC - 8, SC + 9):
            for y in (-7, -8, -9):
                if not in_hull(x, y, z):
                    o.s(x, y, z, "sandstone" if y == -9 else "sand")


def penon_d(x, z):
    return (abs(x - PX) / RX) ** 4 + (abs(z - PZ) / RZ) ** 4


ROCK = ["stone"] * 11 + ["andesite"] * 4 + ["cobblestone"] * 3 + ["tuff"] * 2


def penon(o):
    for x in range(PX - RX, PX + RX + 1):
        for z in range(PZ - RZ, PZ + RZ + 1):
            d = penon_d(x, z)
            if d > 1:
                continue
            h = round(3 + 6 * (1 - d))
            for y in range(-10, h + 1):
                st = o.rng.choice(ROCK)
                if y == h and o.rng.random() < 0.12:
                    st = "gravel"
                o.s(x, y, z, st)


def hueco(o, x1, y1, z1, x2, y2, z2):
    o.air(x1, y1, z1, x2, y2, z2)


def cueva(o):
    penon(o)
    # boca y galería en bajada (3 de ancho)
    for x in range(22, 27):
        hueco(o, x, 1, 38, x, 3, 40)
        for z in (38, 39, 40):
            o.s(x, 0, z, "cobblestone")
    for i in range(6):
        hueco(o, 16 + i, -4 + i, 38, 16 + i, -2 + i, 40)
    o.flight(16, 38, -5, "east", 6, width=3, support="cobblestone")
    hueco(o, 10, -5, 38, 15, -3, 40)
    # trampa de cable: ganchos, cable y dispensadores a la altura de la cabeza
    o.s(12, -5, 38, "tripwire_hook[attached=true,facing=south,powered=false]")
    o.s(12, -5, 40, "tripwire_hook[attached=true,facing=north,powered=false]")
    o.s(12, -5, 39, "tripwire[attached=true,disarmed=false,east=false,north=true,powered=false,south=true,west=false]")
    o.dispenser(12, -4, 37, "south")
    o.dispenser(12, -4, 41, "north")
    o.circuitos.append(("cable", [("cable", (12, -5, 39))], [("dispara", (12, -4, 37)), ("dispara", (12, -4, 41))]))
    o.spawner(14, -4, 41, "zombie")
    # cueva de los huesos
    for x in range(1, 11):
        for z in range(32, 47):
            if ((x - 5.5) / 4.6) ** 2 + ((z - 39) / 6.6) ** 2 <= 1:
                hueco(o, x, -5, z, x, -1, z)
    o.spawner(5, -5, 39, "skeleton")
    for x, z in ((2, 37), (2, 38), (3, 43), (8, 35)):
        o.s(x, -5, z, "bone_block[axis=y]")
    o.s(2, -4, 37, "bone_block[axis=x]")
    for x, z in ((3, 41), (7, 36)):
        o.s(x, -5, z, "skeleton_skull[rotation=4]")
    for p in ((2, -1, 39), (9, -1, 37), (8, -1, 43), (3, -1, 36)):
        o.s(*p, "cobweb")
    # nicho oculto tras una cortina de telarañas
    hueco(o, 4, -5, 29, 6, -3, 31)
    o.s(5, -5, 32, "cobweb")
    o.s(5, -4, 32, "cobweb")
    o.chest(4, -5, 29, "south", "cueva")
    o.s(6, -5, 29, "skeleton_skull[rotation=8]")
    o.s(6, -5, 31, "candle[candles=2,lit=false,waterlogged=false]")
    # paso a la antecámara
    hueco(o, 6, -5, 45, 8, -3, 47)
    # antecámara del puzle de los faroles
    hueco(o, 3, -5, 48, 11, -2, 52)
    for x in range(3, 12):
        for z in range(48, 53):
            o.s(x, -6, z, "stone_bricks")
    for x in range(2, 13):
        for y in range(-6, -1):
            o.s(x, y, 53, "stone_bricks")
    o.s(6, -2, 53, "red_wool")
    o.s(9, -2, 53, "green_wool")
    o.s(4, -2, 53, "white_wool")
    o.s(6, -4, 52, "lever[face=wall,facing=north,powered=false]")      # babor (rojo)
    o.s(9, -4, 52, "lever[face=wall,facing=north,powered=true]")       # estribor (verde), encendido
    o.s(4, -4, 52, "lever[face=wall,facing=north,powered=false]")      # popa (blanco): trampa
    o.dispenser(4, -3, 53, "north", arrows=8)
    o.s(7, -5, 53, "iron_door[facing=north,half=lower,hinge=left,open=false,powered=false]")
    o.s(7, -4, 53, "iron_door[facing=north,half=upper,hinge=left,open=false,powered=false]")
    hueco(o, 7, -5, 54, 8, -4, 54)
    o.air(9, -5, 54, 9, -5, 54)
    o.s(9, -4, 54, "redstone_wall_torch[facing=south,lit=false]")
    o.s(9, -5, 55, "iron_door[facing=north,half=lower,hinge=left,open=false,powered=false]")
    o.s(9, -4, 55, "iron_door[facing=north,half=upper,hinge=left,open=false,powered=false]")
    o.sign(3, -4, 50, "east", ["heraldia.galeon.cartel.1", "heraldia.galeon.cartel.2",
                               "heraldia.galeon.cartel.3", "heraldia.galeon.cartel.4"], o.langs)
    o.circuitos += [
        ("faroles", [("palanca", (6, -4, 52)), ("palanca", (9, -4, 52))],
         [("abierta", (7, -5, 53)), ("abierta", (9, -5, 55)), ("quieto", (4, -3, 53))]),
        ("faroles_solo_rojo", [("palanca", (6, -4, 52))], [("abierta", (7, -5, 53)), ("cerrada", (9, -5, 55))]),
        ("faroles_popa", [("palanca", (4, -4, 52))], [("dispara", (4, -3, 53)), ("cerrada", (7, -5, 53))]),
    ]
    # bajada a la cámara del tesoro
    hueco(o, 8, -5, 56, 10, -3, 56)
    hueco(o, 8, -6, 57, 10, -3, 58)
    o.flight(8, 58, -7, "north", 2, width=3, support="stone_bricks")
    # cámara del tesoro
    for x in range(2, 17):
        for z in range(59, 72):
            o.s(x, -8, z, "polished_andesite")
            hueco(o, x, -7, z, x, -2, z)
    for x, z in ((4, 62), (14, 62), (4, 68), (14, 68)):
        o.fill(x, -7, z, x, -2, z, "stone_bricks")
    o.fill(7, -7, 68, 11, -7, 70, "polished_andesite")
    for x in range(7, 12):
        o.s(x, -7, 67, "polished_andesite_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    o.chest(9, -6, 70, "north", "premium")
    for x in (7, 11):
        o.s(x, -6, 69, "candle[candles=3,lit=true,waterlogged=false]")
    for x, z in ((3, 63), (3, 64), (4, 64), (3, 65)):
        o.s(x, -8, z, "water")
    o.s(9, -2, 64, "iron_chain[axis=y]")
    o.lantern_hang(9, -3, 64)
    o.barrel(16, -7, 60)
    o.barrel(16, -7, 61)
    o.s(15, -7, 70, "bone_block[axis=y]")
    o.s(2, -7, 70, "skeleton_skull[rotation=6]")
    o.t.entity(9, -7, 63, capitan(o.langs))


def capitan(langs):
    from core import B
    from .._comun import piezas
    return piezas.guardian("drowned", "heraldia.galeon.capitan", langs["heraldia.galeon.capitan"], 50, armor=4,
                           equipment={"mainhand": {"id": "minecraft:iron_sword", "count": 1},
                                      "offhand": {"id": "minecraft:nautilus_shell", "count": 1},
                                      "head": {"id": "minecraft:golden_helmet", "count": 1}},
                           drop_chances={"mainhand": 0.25, "offhand": 1.0, "head": 0.1},
                           attributes={"attack_damage": 4}, extra={"CanPickUpLoot": B(0)})


def campamento(o):
    # choza del vigía hecha con tablas del barco
    for x in range(29, 36):
        for z in range(2, 9):
            edge = x in (29, 35) or z in (2, 8)
            for y in (1, 2, 3):
                o.s(x, y, z, "spruce_planks" if edge else "air")
            o.s(x, 4, z, "spruce_slab[type=bottom,waterlogged=false]")
    o.door(35, 1, 5, "east")
    o.s(32, 2, 2, "glass_pane")
    o.s(32, 2, 8, "glass_pane")
    o.bed(30, 1, 3, "north", "white")
    o.chest(30, 1, 7, "east", "nafrago")
    o.s(34, 1, 3, "crafting_table")
    o.lantern_hang(32, 3, 5)
    o.s(37, 1, 9, "spruce_fence")
    o.s(37, 2, 9, "spruce_fence")
    o.s(37, 3, 9, "lantern[hanging=false,waterlogged=false]")
    # dos tiendas hechas con velas
    for x0, z0, wool, kind in ((40, 11, "white_wool", "chest"), (46, 20, "brown_wool", "barrel")):
        for z in range(z0, z0 + 5):
            for dx, y in ((0, 1), (4, 1), (1, 2), (3, 2), (2, 3)):
                o.s(x0 + dx, y, z, wool)
        o.s(x0 + 1, 1, z0 + 4, wool)
        o.s(x0 + 3, 1, z0 + 4, wool)
        o.s(x0 + 2, 2, z0 + 4, wool)
        if kind == "chest":
            o.chest(x0 + 2, 1, z0 + 4, "north", "nafrago")
        else:
            o.barrel(x0 + 2, 1, z0 + 4, "nafrago")
    # hoguera apagada con bancos
    o.s(44, 1, 32, "campfire[facing=north,lit=false,signal_fire=false,waterlogged=false]")
    for z in (31, 32, 33):
        o.s(41, 1, z, "stripped_spruce_log[axis=z]")
        o.s(47, 1, z, "stripped_spruce_log[axis=z]")
    # mastelero de trinquete caído y restos que salieron por la brecha
    for x in range(40, 55):
        o.s(x, 1, 27, "spruce_log[axis=x]")
    o.s(53, 1, 29, "polished_basalt[axis=z]")
    o.s(53, 1, 30, "polished_basalt[axis=z]")
    o.barrel(54, 1, 24)
    o.barrel(52, 1, 35)
    for x, z in ((50, 30), (49, 33), (51, 38)):
        o.s(x, 1, z, "spruce_slab[type=bottom,waterlogged=false]")
    # tendedero de pescado
    for z in (46, 50):
        o.s(40, 1, z, "spruce_fence")
        o.s(40, 2, z, "spruce_fence")
    for z in (47, 48, 49):
        o.s(40, 2, z, "spruce_fence")
    o.s(40, 1, 48, "dried_kelp_block")
    # tumbas de los náufragos
    for x in (30, 33, 36):
        o.s(x, 0, 53, "coarse_dirt")
        o.s(x, 0, 54, "coarse_dirt")
        o.s(x, 1, 52, "spruce_fence")
        o.s(x, 2, 52, "spruce_fence")
        o.s(x - 1, 2, 52, "spruce_fence")
        o.s(x + 1, 2, 52, "spruce_fence")
    o.s(33, 1, 54, "skeleton_skull[rotation=0]")
    o.s(36, 1, 54, "dead_bush")
    # bote salvavidas varado
    o.t.entity(52, 1, 46, {"id": "minecraft:oak_boat", "Rotation": [F(30.0), F(0.0)]})
    # tesoros enterrados (arqueología) señalados con arbustos secos
    for x, z in ((38, 40), (50, 8), (36, 66)):
        o.s(x, 0, z, "suspicious_sand[dusted=0]", {"id": "minecraft:brushable_block", "LootTable": "heraldia:unicas/galeon/arena"})
        o.s(x + 1, 1, z, "dead_bush")


def F(v):
    from core import F as _F
    return _F(v)
