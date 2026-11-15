"""Cloacas con la cámara del tesoro (bajo el castellum) y cisterna del foro. Cajas rellenas bloque a bloque."""

CLOACA = (64, -11, -5, 92, -1, 44)       # x0, y0, z0, x1, y1, z1
CISTERNA = (33, -9, 42, 63, -1, 60)


class Hueco:
    """Rellena una caja de roca y lleva la cuenta de lo excavado para revestirlo después."""

    def __init__(self, o, box, roca="sandstone", forro="stone_bricks"):
        self.o, self.box, self.forro, self.roca = o, box, forro, roca
        x0, y0, z0, x1, y1, z1 = box
        o.f(x0, y0, z0, x1, y1, z1, roca)
        self.cav = set()

    def air(self, x0, y0, z0, x1, y1, z1):
        bx0, by0, bz0, bx1, by1, bz1 = self.box
        assert bx0 < min(x0, x1) and max(x0, x1) < bx1 and bz0 < min(z0, z1) and max(z0, z1) < bz1, (x0, z0, x1, z1)
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    if y <= by1:
                        self.o.s(x, y, z, "air")
                        self.cav.add((x, y, z))

    def revestir(self):
        o = self.o
        for (x, y, z) in list(self.cav):
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                p = (x + dx, y + dy, z + dz)
                if o.g(*p) == "minecraft:" + self.roca:
                    o.s(*p, self.forro)


def guardian():
    eq = {"head": "golden_helmet", "chest": "iron_chestplate", "legs": "chainmail_leggings",
          "feet": "iron_boots", "mainhand": "iron_sword", "offhand": "shield"}
    from .._comun import piezas
    n = piezas.guardian("husk", "heraldia.unicas.acueducto.guardian", "Centurión Aquilio", 60,
                        equipment={k: {"id": "minecraft:" + v, "count": 1} for k, v in eq.items()},
                        drop_chances={k: 0.0 for k in eq}, attributes={"attack_damage": 5, "knockback_resistance": 0.4})
    n["CustomName"]["color"] = "gold"
    return n


def cloaca(o):
    h = Hueco(o, CLOACA)
    A = h.air
    # escalera secreta desde el castellum
    for k in range(9):
        z, s = -5 + k, -1 - k
        A(73, s + 1, z, 73, min(s + 3, -1), z) if s + 1 <= -1 else None
    # galería de entrada, colector, lararium, sala de generadores, antecámara, cámara
    A(72, -8, 4, 74, -6, 11)
    A(71, -8, 8, 71, -7, 8); A(75, -8, 8, 75, -7, 8)
    A(66, -8, 12, 90, -6, 14)
    A(67, -8, 11, 67, -7, 11); A(65, -8, 6, 69, -6, 10)
    A(78, -8, 15, 80, -6, 15); A(70, -8, 16, 88, -4, 26)
    A(79, -8, 27, 79, -6, 31); A(78, -8, 32, 80, -6, 33)
    A(79, -8, 35, 79, -7, 35); A(73, -8, 36, 85, -4, 43)
    h.revestir()
    for k in range(9):
        z, s = -5 + k, -1 - k
        o.stair(73, s, z, "north", "stone_brick_stairs")
    # canal del colector (agua contenida: muros, suelo y dos puentes)
    for x in range(66, 91):
        o.s(x, -9, 13, "stone_bricks" if x in (73, 79) else "water")
    for x in (70, 76, 86):
        o.lantern(x, -6, 13)
    o.lantern(73, -6, 5)
    # trampa 1: cable trampa de muro a muro y dispensadores sobre los bloques de los ganchos
    o.s(71, -8, 8, "tripwire_hook[attached=true,facing=east,powered=false]")
    o.s(75, -8, 8, "tripwire_hook[attached=true,facing=west,powered=false]")
    for x in (72, 73, 74):
        o.s(x, -8, 8, "tripwire[attached=true,disarmed=false,east=true,north=false,powered=false,south=false,west=true]")
    o.dispenser(70, -7, 8, "east"); o.dispenser(76, -7, 8, "west")
    o.red["gancho_O"], o.red["gancho_E"] = (71, -8, 8), (75, -8, 8)
    o.red["dispensadores_1"] = [(70, -7, 8), (76, -7, 8)]
    # lararium oculto tras las telarañas
    o.s(67, -8, 11, "cobweb"); o.s(67, -7, 11, "cobweb")
    o.chest(65, -8, 7, "east", "oculto")
    o.s(67, -8, 6, "chiseled_stone_bricks"); o.s(67, -7, 6, "candle[candles=2,lit=false,waterlogged=false]")
    o.pot(66, -8, 6, "south"); o.pot(68, -8, 6, "south")
    o.s(69, -8, 10, "skeleton_skull[powered=false,rotation=12]")
    o.s(65, -6, 10, "cobweb"); o.s(69, -6, 6, "cobweb")
    # sala de generadores y pozo de salida
    o.f(79, -8, 21, 79, -4, 21, "stone_bricks")
    for y in range(-8, 0):
        o.s(79, y, 20, "ladder[facing=north,waterlogged=false]")
    o.s(80, -1, 20, "air")
    o.s(80, -1, 20, "lever[face=ceiling,facing=north,powered=false]")
    o.red["palanca_reja"] = (80, -1, 20)
    o.spawner(73, -8, 21, "husk"); o.spawner(85, -8, 21, "skeleton")
    o.chest(70, -8, 25, "east", "cloaca")
    for (x, z) in ((70, 16), (88, 16), (88, 26)):
        o.s(x, -8, z, "bone_block[axis=y]")
    o.s(71, -8, 16, "skeleton_skull[powered=false,rotation=4]")
    for z in (18, 22):
        o.s(69, -6, z, "iron_bars"); o.s(89, -6, z, "iron_bars")
    # trampa 2: placas de presión con dispensadores a los pies
    for z in (28, 30):
        o.s(79, -8, z, "stone_pressure_plate[powered=false]")
        o.dispenser(78, -8, z, "east"); o.dispenser(80, -8, z, "west")
        o.red[f"placa_{z}"] = (79, -8, z)
        o.red[f"dispensadores_{z}"] = [(78, -8, z), (80, -8, z)]
    # puzle 2: la fuente de las ofrendas y la puerta de hierro
    for half, y in (("lower", -8), ("upper", -7)):
        o.s(79, y, 34, f"iron_door[facing=north,half={half},hinge=left,open=false,powered=false]")
    o.s(80, -7, 34, "oak_pressure_plate[powered=false]")
    o.s(80, -8, 34, "chiseled_stone_bricks"); o.s(81, -7, 34, "chiseled_stone_bricks")
    o.sign(80, -6, 33, "north", [("heraldia.unicas.acueducto.ofrenda1", "OBOLVM AQVIS"),
                                ("heraldia.unicas.acueducto.ofrenda2", "Da tu óbolo"),
                                ("heraldia.unicas.acueducto.ofrenda3", "a las aguas")])
    o.s(79, -7, 35, "stone_button[face=wall,facing=east,powered=false]")
    o.red["puerta_2"] = [(79, -8, 34), (79, -7, 34)]
    o.red["placa_ofrenda"], o.red["boton"] = (80, -7, 34), (79, -7, 35)
    o.lantern(79, -6, 32)
    # cámara del tesoro
    for x in range(73, 86):
        for z in range(36, 44):
            o.s(x, -9, z, "chiseled_quartz_block" if x in (73, 85) or z in (36, 43) else "smooth_quartz")
    for (x, z) in ((75, 38), (83, 38), (75, 41), (83, 41)):
        o.f(x, -8, z, x, -4, z, "quartz_pillar[axis=y]")
    o.chest(79, -8, 43, "north", "premium")
    o.chest(74, -8, 43, "north", "oculto"); o.chest(84, -8, 43, "north", "oculto")
    for x in (78, 80):
        o.s(x, -8, 43, "chiseled_quartz_block"); o.s(x, -7, 43, "candle[candles=4,lit=false,waterlogged=false]")
    for (x, z) in ((73, 36), (85, 36), (73, 43), (85, 43)):
        o.pot(x, -8, z, "north")
    for (x, z) in ((77, 39), (81, 39), (79, 42)):
        o.lantern(x, -4, z, soul=True)
    o.t.entity(79, -8, 39, guardian())
    o.red["premium"] = (79, -8, 43)


def cisterna(o):
    h = Hueco(o, CISTERNA)
    h.air(35, -7, 44, 61, -3, 58)
    for k in range(1, 9):                          # escalera desde la casa de la fuente (s = 0 está en la ciudad)
        z, s = 58 - k, -k
        for y in (s + 1, s + 2, s + 3):
            if y <= -1:
                h.air(40, y, z, 40, y, z)
    h.revestir()
    walk = lambda x, z: (x <= 36 or x >= 60 or z <= 45 or z >= 57 or 48 <= x <= 49 or 50 <= z <= 51
                         or 39 <= x <= 41 or (47 <= x <= 50 and 49 <= z <= 52))
    cols = {(x, z) for x in (38, 44, 53, 58) for z in (47, 54)}
    for x in range(35, 62):
        for z in range(44, 59):
            if (x, z) in cols:
                o.f(x, -8, z, x, -3, z, "stone_bricks")
            else:
                o.s(x, -8, z, "smooth_sandstone" if walk(x, z) else "water")
    for k in range(1, 9):
        z, s = 58 - k, -k
        o.f(40, -8, z, 40, s - 1, z, "smooth_sandstone") if s - 1 >= -8 else None
        o.stair(40, s, z, "south", "sandstone_stairs")
    o.spawner(48, -7, 50, "spider")
    o.chest(50, -7, 49, "west", "cisterna")
    o.s(47, -7, 52, "bone_block[axis=y]")
    o.lantern(40, -3, 46); o.lantern(58, -3, 57); o.lantern(36, -3, 57)
