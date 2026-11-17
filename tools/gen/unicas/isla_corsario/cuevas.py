"""Cuevas bajo el cerro del fuerte: la ensenada oculta (se entra en barca por una boca del acantilado norte), el cuerpo
de guardia al pie de la bajada, la sala del mapa con la rosa de los vientos (puzle), la armería con la santabárbara
secreta, los calabozos y, bajo el nivel del mar, la antecámara y la cámara del tesoro con el corsario."""
from core import B
from .obra import S, stairs, h, SB, CSB, COB, N6
from .._comun import piezas

Y = 1                         # pies en las cuevas (suelo a y = 0, techo a y = 5)
YT = -6                       # pies en la cámara del tesoro (suelo a -7)
NATURAL = {"minecraft:stone", "minecraft:andesite", "minecraft:tuff", "minecraft:cobblestone", "minecraft:dirt",
           "minecraft:gravel", "minecraft:grass_block[snowy=false]", "minecraft:sand", "minecraft:sandstone"}
LAGUNA = (68, 82, 13, 24)     # cámara de la ensenada: x0, x1, z0, z1 (interior)
BOCA = (73, 75)               # boca de la ensenada en el acantilado norte (x)


class Cuevas:
    def __init__(self, o):
        self.o = o
        self.carved = {}          # celda de aire -> material del forro alrededor

    def hueco(self, x0, x1, y0, y1, z0, z1, forro=SB):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.o.s(x, y, z, "air")
                    self.carved[(x, y, z)] = forro

    def sala(self, x0, x1, z0, z1, y=Y, alto=4, suelo=SB, forro=SB):
        """Sala de aire de y a y + alto - 1 con su suelo (y - 1); el forro se pone al final (forrar)."""
        self.hueco(x0, x1, y, y + alto - 1, z0, z1, forro)
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.o.s(x, y - 1, z, suelo if not callable(suelo) else suelo(x, z))

    def forrar(self):
        """Toda cara de una celda excavada que da a roca natural pasa a ser del forro de su sala (ni manantiales ni
        liquen dentro, y nada de la isla natural a la vista)."""
        o = self.o
        for (x, y, z), forro in self.carved.items():
            for a, b, c in N6:
                p = (x + a, y + b, z + c)
                if p in self.carved:
                    continue
                st = o.get(*p)
                if st is None or st in NATURAL:
                    o.s(*p, forro if b == 0 else (forro if b > 0 else SB))
                    o.lining.add(p)

    def construir(self):
        self.ensenada()
        self.guardia()
        self.mapa()
        self.armeria()
        self.calabozos()
        self.tesoro()
        self.forrar()

    # ------------------------------------------------------------------ la ensenada oculta
    def ensenada(self):
        o = self.o
        x0, x1, z0, z1 = LAGUNA
        bx0, bx1 = BOCA
        # canal desde mar abierto (a través del talud y el acantilado) hasta la laguna
        for x in range(bx0, bx1 + 1):
            for z in range(4, z0):
                for y in range(-3, 0):
                    o.s(x, y, z, "water")
                    o.agua.add((x, y, z))
                if o.ground.get((x, z)) is not None:
                    self.hueco(x, x, 0, 3, z, z, COB)
                o.s(x, -4, z, "sand") if o.get(x, -4, z) else None
        # cámara: agua en el centro, muelles de piedra al sur y al oeste
        self.hueco(x0, x1, 0, 4, z0, z1, COB)
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                water = x >= x0 + 2 and z <= z1 - 4
                if water:
                    for y in range(-3, 0):
                        o.s(x, y, z, "water")
                        o.agua.add((x, y, z))
                    o.s(x, -4, z, "sand" if h(x, z, 21) < 0.8 else "gravel")
                else:
                    o.s(x, -1, z, SB)
                    o.a(x, 0, z, x, 0, z)
        for x in range(x0 + 1, x1):
            for z in range(z0 + 1, z1 - 4):
                self.carved[(x, 5, z)] = COB            # bóveda más alta en el centro
                o.s(x, 5, z, "air")
        # el muelle queda a ras (suelo y = -1, pies 0): bordillo y amarres
        for x in range(x0 + 2, x1 + 1, 4):
            o.s(x, 0, z1 - 3, "spruce_fence")
        o.t.entity(76, 0, 17, {"id": "minecraft:oak_boat", "Rotation": [__import__("core").F(90.0), __import__("core").F(0.0)]})
        o.spawner(78, -3, 15, "drowned", luz=11)
        o.chest(x0, 0, z1, "east", "ensenada")
        for (x, z) in ((x0, z1 - 2), (x0, z1 - 3)):
            o.s(x, 0, z, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        o.hang(x1 - 1, 3, z1 - 1)
        o.hang(x0 + 1, 3, z0 + 2)
        o.mech["ensenada"] = dict(boca=(bx0, bx1), laguna=LAGUNA)
        # pasillo al cuerpo de guardia (sube un peldaño: del muelle a pies 1)
        self.hueco(79, 80, 0, 3, z1 + 1, z1 + 1, COB)
        o.s(79, -1, z1 + 1, SB)
        o.s(80, -1, z1 + 1, SB)
        for x in (79, 80):
            o.s(x, 0, z1 + 2, stairs("stone_brick", "south"))
            self.hueco(x, x, 1, 3, z1 + 2, z1 + 2, SB)
        self.sala(79, 80, z1 + 3, 27, alto=3)

    # ------------------------------------------------------------------ cuerpo de guardia (llegada de la bajada)
    def guardia(self):
        o = self.o
        self.sala(76, 83, 28, 34)
        # la bajada desde la torre del patio: peldaños (80, 7 - k, 41 - k), del patio (pies 8) a las cuevas (pies 1)
        for k in range(7):
            x, y, z = 80, 7 - k, 41 - k
            o.s(x, y, z, stairs("stone_brick", "south"))
            self.hueco(x, x, y + 1, y + 3, z, z, SB)
            for yy in range(y - 1, -1, -1):
                if (x, yy, z) not in self.carved:
                    o.s(x, yy, z, SB)
        o.table(77, Y, 31)
        o.chair(77, Y, 30, "north")
        o.chair(77, Y, 32, "south")
        o.chest(83, Y, 29, "west", "guardia")
        o.s(83, Y, 33, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        o.hang(79, 4, 31)
        o.sign(76, Y + 1, 34, "north", "guardia", [("Al oeste, el mapa", "West, the map"), ("y la armería.", "and the armoury."),
                                                     ("Al norte, la cala.", "North, the cove.")])
        # pasillo al oeste con la trampa de cable (trampa 1)
        self.sala(75, 75, 31, 32)
        piezas.tripwire_trap(o.s, (75, 30), (75, 33), Y, "z", [((75, Y + 1, 29), "south"), ((75, Y + 1, 34), "north")])
        self.hueco(75, 75, Y, Y, 30, 30)
        self.hueco(75, 75, Y, Y, 33, 33)
        o.s(75, Y, 30, S("tripwire_hook", attached=True, facing="south", powered=False))
        o.s(75, Y, 33, S("tripwire_hook", attached=True, facing="north", powered=False))
        self.carved.pop((75, Y, 30))
        self.carved.pop((75, Y, 33))
        o.mech["ganchos"] = [(75, Y, 30), (75, Y, 33)]
        o.mech["cable"] = [(75, Y, 31), (75, Y, 32)]
        o.mech["dispensadores_cable"] = [(75, Y + 1, 29), (75, Y + 1, 34)]

    # ------------------------------------------------------------------ sala del mapa (puzle de la rosa de los vientos)
    def mapa(self):
        o = self.o
        x0, x1, z0, z1 = 64, 74, 28, 35
        self.sala(x0, x1, z0, z1, suelo=lambda x, z: "polished_andesite" if (x + z) % 2 else "polished_diorite")
        # rosa de los vientos en el suelo
        cx, cz = 69, 32
        for (a, b, c) in ((0, -2, "red_terracotta"), (0, 2, "white_terracotta"), (-2, 0, "white_terracotta"),
                          (2, 0, "white_terracotta"), (0, -1, "red_terracotta"), (0, 1, "black_terracotta"),
                          (-1, 0, "black_terracotta"), (1, 0, "black_terracotta"), (0, 0, "gold_block")):
            o.s(cx + a, Y - 1, cz + b, c)
        o.s(72, Y, 34, "cartography_table")
        o.s(65, Y, 34, "lectern[facing=east,has_book=false,powered=false]")
        o.chest(73, Y, 29, "west", "cartas")
        o.hang(69, 4, 30)
        o.hang(69, 4, 34)
        # puzle: cuatro palancas en el muro norte (la rosa: norte, levante, sur, poniente); solo norte y poniente
        y = Y
        for x in range(x0 - 1, x1 + 2):
            for yy in range(y, y + 4):
                o.s(x, yy, z0 - 1, SB)
        good = [((68, y + 1, z0), (68, y + 1, z0 - 1)), ((74, y + 1, z0), (74, y + 1, z0 - 1))]
        rec = piezas.combo_door(o.s, (64, y, z0 - 3), "x", 1, good, name="rosa", block=CSB)
        for x in (70, 72):                                  # palancas falsas: polvo del bloque de la palanca a la línea
            o.s(x, y + 1, z0, S("lever", face="wall", facing="south", powered=False))
            o.s(x, y + 1, z0 - 2, "redstone_wire[east=none,north=side,south=side,west=none,power=0]")
        names = {68: ("norte", ("Norte", "North")), 70: ("levante", ("Levante", "East")),
                 72: ("sur", ("Sur", "South")), 74: ("poniente", ("Poniente", "West"))}
        for x, (key, l1) in names.items():
            o.s(x, y + 2, z0 - 1, CSB)
            o.sign(x, y + 2, z0, "south", "rosa_" + key, [l1])
        for x in range(x0 - 1, x1 + 2):                     # cara de detrás (hacia la bajada al tesoro)
            for yy in range(y, y + 4):
                if o.free(x, yy, z0 - 4) or o.get(x, yy, z0 - 4) in NATURAL:
                    o.s(x, yy, z0 - 4, SB)
        for z in (z0 - 1, z0 - 2):                          # paso de la puerta (de la sala a la puerta)
            self.hueco(64, 64, y, y + 1, z, z, SB)
        self.hueco(64, 64, y, y + 1, z0 - 4, z0 - 4, SB)
        o.mech["rosa"] = rec
        o.mech["palancas"] = [(x, y + 1, z0) for x in (68, 70, 72, 74)]
        o.mech["solucion"] = (True, False, False, True)
        o.mech["puerta_rosa"] = [(64, y, z0 - 3), (64, y + 1, z0 - 3)]
        # salidas: al este (cuerpo de guardia), al oeste (armería) y al sur (calabozos)
        self.sala(63, 63, 31, 32, alto=3)
        self.sala(68, 69, 36, 36, alto=3)

    # ------------------------------------------------------------------ armería y santabárbara (puerta secreta)
    def armeria(self):
        o = self.o
        x0, x1, z0, z1 = 56, 62, 27, 35
        self.sala(x0, x1, z0, z1)
        o.spawner(57, Y, 34, "skeleton", luz=11)
        for z in (28, 30):
            o.s(x0, Y, z, S("barrel", facing="east", open=False), {"id": "minecraft:barrel"})
        o.chest(x0, Y, 32, "east", "armeria")
        o.s(61, Y, 35, "smithing_table")
        o.s(62, Y, 34, "grindstone[face=floor,facing=north]")
        for x in (58, 60):
            o.s(x, Y + 2, z1 + 1, SB)
        # puerta secreta (palanca junto al armero) a la santabárbara, al norte
        door = piezas.lever_door(o.s, (59, Y, z0 - 1), "west", "south", SB, SB)
        o.mech["santabarbara"] = door
        self.sala(57, 61, 21, 25)
        self.hueco(59, 59, Y, Y + 1, z0 - 2, z0 - 2)
        o.chest(57, Y, 21, "south", "santabarbara")
        for x in (58, 59, 60):
            o.s(x, Y, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        o.s(61, Y, 21, "tnt[unstable=false]")
        o.s(61, Y, 22, "tnt[unstable=false]")
        o.hidden += [(x, Y, z) for x in range(57, 62) for z in range(21, 26)]

    # ------------------------------------------------------------------ calabozos
    def calabozos(self):
        o = self.o
        x0, x1 = 64, 76
        self.sala(x0, x1, 40, 40, alto=3)              # pasillo
        self.sala(68, 69, 37, 39, alto=3)             # bajada desde la sala del mapa
        for i, cx in enumerate((65, 70, 74)):
            for (z0, z1, zb) in ((41, 43, 41), (37, 39, 39)):
                if cx == 70 and z0 == 37:
                    continue
                self.sala(cx - 1, cx + 1, z0, z1, alto=3)
                for x in (cx - 1, cx + 1):
                    o.s(x, Y, zb, "iron_bars")
                    o.s(x, Y + 1, zb, "iron_bars")
                o.s(cx, Y, zb, "air")
                o.s(cx, Y + 2, zb, SB)
        o.chest(75, Y, 43, "north", "calabozo")
        o.s(65, Y, 43, "skeleton_skull[rotation=8]")
        o.spawner(76, Y, 40, "skeleton", luz=11)
        o.sign(67, Y + 1, 39, "south", "calabozo", [("Aquí esperan", "Here wait"), ("los que no", "those who would"),
                                                      ("quisieron izar", "not hoist"), ("la negra.", "the black.")])

    # ------------------------------------------------------------------ antecámara y cámara del tesoro
    def tesoro(self):
        o = self.o
        # tras la puerta de la rosa: pasillo al norte y bajada hacia el oeste hasta los pies -6
        self.hueco(64, 64, Y, Y + 2, 23, 24)
        for k in range(7):
            x, y = 63 - k, 0 - k
            o.s(x, y, 23, stairs("stone_brick", "east"))
            self.hueco(x, x, y + 1, y + 3, 23, 23)
            o.s(x, y - 1, 23, SB) if (x, y - 1, 23) not in self.carved else None
        # antecámara con la trampa de placas (trampa 2)
        self.sala(52, 56, 22, 24, y=YT, alto=3)
        piezas.plate_trap(o.s, [(54, YT, 23), (53, YT, 23)], "north", arrows=16)
        for p in ((54, YT, 22), (54, YT, 24), (53, YT, 22), (53, YT, 24)):
            self.carved.pop(p, None)
        o.mech["placas"] = [(54, YT, 23), (53, YT, 23)]
        o.mech["flechas"] = [(54, YT, 22), (54, YT, 24), (53, YT, 22), (53, YT, 24)]
        # cámara del tesoro
        self.sala(48, 58, 26, 35, y=YT, alto=5, suelo=lambda x, z: "polished_blackstone" if (x + z) % 2 else "polished_andesite")
        self.sala(51, 52, 25, 25, y=YT, alto=3)
        o.chest(53, YT, 35, "north", "premium")
        o.s(52, YT, 35, "gold_block")
        o.s(54, YT, 35, "gold_block")
        for x in (49, 57):
            o.chest(x, YT, 26, "south", "tesoro")
        o.s(52, YT + 1, 35, S("candle", candles=3, lit=True, waterlogged=False))
        o.s(54, YT + 1, 35, S("candle", candles=3, lit=True, waterlogged=False))
        o.hang(53, YT + 4, 30)
        o.t.entity(53, YT, 31, corsario())
        o.hidden += [(x, YT, z) for x in range(48, 59) for z in range(26, 36)]
        o.hidden += [(x, YT, z) for x in range(52, 57) for z in range(22, 25)]


def corsario():
    from .obra import K
    return piezas.guardian("skeleton", K + "guardian", "Roque Salitre, el corsario", 60, armor=6,
                           equipment={"mainhand": {"id": "minecraft:bow", "count": 1},
                                      "head": {"id": "minecraft:chainmail_helmet", "count": 1},
                                      "chest": {"id": "minecraft:leather_chestplate", "count": 1}},
                           drop_chances={"mainhand": 0.1, "head": 0.1, "chest": 0.1},
                           attributes={"attack_damage": 4, "knockback_resistance": 0.4},
                           extra={"CanPickUpLoot": B(0)})
