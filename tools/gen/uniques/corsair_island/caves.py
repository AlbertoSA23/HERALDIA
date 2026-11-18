"""Caves under the fort's hill: the hidden cove (entered by boat through a mouth in the north cliff), the guardroom
at the foot of the descent, the map room with the compass rose (puzzle), the armory with the secret powder
magazine, the dungeons and, below sea level, the antechamber and the treasure chamber with the corsair."""
from core import B
from .construction import S, stairs, h, SB, CSB, COB, N6
from .._common import pieces

Y = 1                         # feet in the caves (floor at y = 0, ceiling at y = 5)
YT = -6                       # feet in the treasure chamber (floor at -7)
NATURAL = {"minecraft:stone", "minecraft:andesite", "minecraft:tuff", "minecraft:cobblestone", "minecraft:dirt",
           "minecraft:gravel", "minecraft:grass_block[snowy=false]", "minecraft:sand", "minecraft:sandstone"}
LAGOON = (68, 82, 13, 24)     # cove chamber: x0, x1, z0, z1 (interior)
MOUTH = (73, 75)               # mouth of the cove in the north cliff (x)


class Caves:
    def __init__(self, o):
        self.o = o
        self.carved = {}          # air cell -> lining material around it

    def cavity(self, x0, x1, y0, y1, z0, z1, lining=SB):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.o.s(x, y, z, "air")
                    self.carved[(x, y, z)] = lining

    def room(self, x0, x1, z0, z1, y=Y, height=4, floor=SB, lining=SB):
        """Air room from y to y + height - 1 with its floor (y - 1); the lining is placed at the end (forrar)."""
        self.cavity(x0, x1, y, y + height - 1, z0, z1, lining)
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.o.s(x, y - 1, z, floor if not callable(floor) else floor(x, z))

    def line_walls(self):
        """Every face of an excavated cell that looks onto natural rock becomes part of its room's lining (no springs or
        lichen inside, and nothing of the natural island in view)."""
        o = self.o
        for (x, y, z), lining in self.carved.items():
            for a, b, c in N6:
                p = (x + a, y + b, z + c)
                if p in self.carved:
                    continue
                st = o.get(*p)
                if st is None or st in NATURAL:
                    o.s(*p, lining if b == 0 else (lining if b > 0 else SB))
                    o.lining.add(p)

    def construct(self):
        self.cove()
        self.sentry()
        self.map_obj()
        self.armory()
        self.dungeon_cells()
        self.treasure()
        self.line_walls()

    # ------------------------------------------------------------------ the hidden cove
    def cove(self):
        o = self.o
        x0, x1, z0, z1 = LAGOON
        bx0, bx1 = MOUTH
        # channel from open sea (through the slope and the cliff) to the lagoon
        for x in range(bx0, bx1 + 1):
            for z in range(4, z0):
                for y in range(-3, 0):
                    o.s(x, y, z, "water")
                    o.water.add((x, y, z))
                if o.ground.get((x, z)) is not None:
                    self.cavity(x, x, 0, 3, z, z, COB)
                o.s(x, -4, z, "sand") if o.get(x, -4, z) else None
        # chamber: water in the center, stone piers to the south and west
        self.cavity(x0, x1, 0, 4, z0, z1, COB)
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                water = x >= x0 + 2 and z <= z1 - 4
                if water:
                    for y in range(-3, 0):
                        o.s(x, y, z, "water")
                        o.water.add((x, y, z))
                    o.s(x, -4, z, "sand" if h(x, z, 21) < 0.8 else "gravel")
                else:
                    o.s(x, -1, z, SB)
                    o.a(x, 0, z, x, 0, z)
        for x in range(x0 + 1, x1):
            for z in range(z0 + 1, z1 - 4):
                self.carved[(x, 5, z)] = COB            # higher vault in the center
                o.s(x, 5, z, "air")
        # the pier is flush (floor y = -1, feet 0): curb and moorings
        for x in range(x0 + 2, x1 + 1, 4):
            o.s(x, 0, z1 - 3, "spruce_fence")
        o.t.entity(76, 0, 17, {"id": "minecraft:oak_boat", "Rotation": [__import__("core").F(90.0), __import__("core").F(0.0)]})
        o.spawner(78, -3, 15, "drowned", light=11)
        o.chest(x0, 0, z1, "east", "ensenada")
        for (x, z) in ((x0, z1 - 2), (x0, z1 - 3)):
            o.s(x, 0, z, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        o.hang(x1 - 1, 3, z1 - 1)
        o.hang(x0 + 1, 3, z0 + 2)
        o.mech["ensenada"] = dict(boca=(bx0, bx1), laguna=LAGOON)
        # corridor to the guardroom (rises one step: from the pier to feet 1)
        self.cavity(79, 80, 0, 3, z1 + 1, z1 + 1, COB)
        o.s(79, -1, z1 + 1, SB)
        o.s(80, -1, z1 + 1, SB)
        for x in (79, 80):
            o.s(x, 0, z1 + 2, stairs("stone_brick", "south"))
            self.cavity(x, x, 1, 3, z1 + 2, z1 + 2, SB)
        self.room(79, 80, z1 + 3, 27, height=3)

    # ------------------------------------------------------------------ guardroom (arrival of the descent)
    def sentry(self):
        o = self.o
        self.room(76, 83, 28, 34)
        # the descent from the courtyard tower: steps (80, 7 - k, 41 - k), from the courtyard (feet 8) to the caves (feet 1)
        for k in range(7):
            x, y, z = 80, 7 - k, 41 - k
            o.s(x, y, z, stairs("stone_brick", "south"))
            self.cavity(x, x, y + 1, y + 3, z, z, SB)
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
        # corridor to the west with the wire trap (trap 1)
        self.room(75, 75, 31, 32)
        pieces.tripwire_trap(o.s, (75, 30), (75, 33), Y, "z", [((75, Y + 1, 29), "south"), ((75, Y + 1, 34), "north")])
        self.cavity(75, 75, Y, Y, 30, 30)
        self.cavity(75, 75, Y, Y, 33, 33)
        o.s(75, Y, 30, S("tripwire_hook", attached=True, facing="south", powered=False))
        o.s(75, Y, 33, S("tripwire_hook", attached=True, facing="north", powered=False))
        self.carved.pop((75, Y, 30))
        self.carved.pop((75, Y, 33))
        o.mech["ganchos"] = [(75, Y, 30), (75, Y, 33)]
        o.mech["cable"] = [(75, Y, 31), (75, Y, 32)]
        o.mech["dispensadores_cable"] = [(75, Y + 1, 29), (75, Y + 1, 34)]

    # ------------------------------------------------------------------ map room (compass-rose puzzle)
    def map_obj(self):
        o = self.o
        x0, x1, z0, z1 = 64, 74, 28, 35
        self.room(x0, x1, z0, z1, floor=lambda x, z: "polished_andesite" if (x + z) % 2 else "polished_diorite")
        # compass rose on the floor
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
        # puzzle: four levers on the north wall (the rose: north, east, south, west); only north and west
        y = Y
        for x in range(x0 - 1, x1 + 2):
            for yy in range(y, y + 4):
                o.s(x, yy, z0 - 1, SB)
        good = [((68, y + 1, z0), (68, y + 1, z0 - 1)), ((74, y + 1, z0), (74, y + 1, z0 - 1))]
        rec = pieces.combo_door(o.s, (64, y, z0 - 3), "x", 1, good, name="rosa", block=CSB)
        for x in (70, 72):                                  # fake levers: dust from the lever's block to the line
            o.s(x, y + 1, z0, S("lever", face="wall", facing="south", powered=False))
            o.s(x, y + 1, z0 - 2, "redstone_wire[east=none,north=side,south=side,west=none,power=0]")
        names = {68: ("norte", ("Norte", "North")), 70: ("levante", ("Levante", "East")),
                 72: ("sur", ("Sur", "South")), 74: ("poniente", ("Poniente", "West"))}
        for x, (key, l1) in names.items():
            o.s(x, y + 2, z0 - 1, CSB)
            o.sign(x, y + 2, z0, "south", "rosa_" + key, [l1])
        for x in range(x0 - 1, x1 + 2):                     # back face (toward the descent to the treasure)
            for yy in range(y, y + 4):
                if o.free(x, yy, z0 - 4) or o.get(x, yy, z0 - 4) in NATURAL:
                    o.s(x, yy, z0 - 4, SB)
        for z in (z0 - 1, z0 - 2):                          # door passage (from the room to the door)
            self.cavity(64, 64, y, y + 1, z, z, SB)
        self.cavity(64, 64, y, y + 1, z0 - 4, z0 - 4, SB)
        o.mech["rosa"] = rec
        o.mech["palancas"] = [(x, y + 1, z0) for x in (68, 70, 72, 74)]
        o.mech["solucion"] = (True, False, False, True)
        o.mech["puerta_rosa"] = [(64, y, z0 - 3), (64, y + 1, z0 - 3)]
        # exits: east (guardroom), west (armory) and south (dungeons)
        self.room(63, 63, 31, 32, height=3)
        self.room(68, 69, 36, 36, height=3)

    # ------------------------------------------------------------------ armory and powder magazine (secret door)
    def armory(self):
        o = self.o
        x0, x1, z0, z1 = 56, 62, 27, 35
        self.room(x0, x1, z0, z1)
        o.spawner(57, Y, 34, "skeleton", light=11)
        for z in (28, 30):
            o.s(x0, Y, z, S("barrel", facing="east", open=False), {"id": "minecraft:barrel"})
        o.chest(x0, Y, 32, "east", "armeria")
        o.s(61, Y, 35, "smithing_table")
        o.s(62, Y, 34, "grindstone[face=floor,facing=north]")
        for x in (58, 60):
            o.s(x, Y + 2, z1 + 1, SB)
        # secret door (lever next to the armorer) to the powder magazine, to the north
        door = pieces.lever_door(o.s, (59, Y, z0 - 1), "west", "south", SB, SB)
        o.mech["santabarbara"] = door
        self.room(57, 61, 21, 25)
        self.cavity(59, 59, Y, Y + 1, z0 - 2, z0 - 2)
        o.chest(57, Y, 21, "south", "santabarbara")
        for x in (58, 59, 60):
            o.s(x, Y, 21, S("barrel", facing="up", open=False), {"id": "minecraft:barrel"})
        o.s(61, Y, 21, "tnt[unstable=false]")
        o.s(61, Y, 22, "tnt[unstable=false]")
        o.hidden += [(x, Y, z) for x in range(57, 62) for z in range(21, 26)]

    # ------------------------------------------------------------------ calabozos
    def dungeon_cells(self):
        o = self.o
        x0, x1 = 64, 76
        self.room(x0, x1, 40, 40, height=3)              # pasillo
        self.room(68, 69, 37, 39, height=3)             # descent from the map room
        for i, cx in enumerate((65, 70, 74)):
            for (z0, z1, zb) in ((41, 43, 41), (37, 39, 39)):
                if cx == 70 and z0 == 37:
                    continue
                self.room(cx - 1, cx + 1, z0, z1, height=3)
                for x in (cx - 1, cx + 1):
                    o.s(x, Y, zb, "iron_bars")
                    o.s(x, Y + 1, zb, "iron_bars")
                o.s(cx, Y, zb, "air")
                o.s(cx, Y + 2, zb, SB)
        o.chest(75, Y, 43, "north", "calabozo")
        o.s(65, Y, 43, "skeleton_skull[rotation=8]")
        o.spawner(76, Y, 40, "skeleton", light=11)
        o.sign(67, Y + 1, 39, "south", "calabozo", [("Aquí esperan", "Here wait"), ("los que no", "those who would"),
                                                      ("quisieron izar", "not hoist"), ("la negra.", "the black.")])

    # ------------------------------------------------------------------ antechamber and treasure chamber
    def treasure(self):
        o = self.o
        # behind the rose door: corridor north and descent west down to feet -6
        self.cavity(64, 64, Y, Y + 2, 23, 24)
        for k in range(7):
            x, y = 63 - k, 0 - k
            o.s(x, y, 23, stairs("stone_brick", "east"))
            self.cavity(x, x, y + 1, y + 3, 23, 23)
            o.s(x, y - 1, 23, SB) if (x, y - 1, 23) not in self.carved else None
        # antechamber with the pressure-plate trap (trap 2)
        self.room(52, 56, 22, 24, y=YT, height=3)
        pieces.plate_trap(o.s, [(54, YT, 23), (53, YT, 23)], "north", arrows=16)
        for p in ((54, YT, 22), (54, YT, 24), (53, YT, 22), (53, YT, 24)):
            self.carved.pop(p, None)
        o.mech["placas"] = [(54, YT, 23), (53, YT, 23)]
        o.mech["flechas"] = [(54, YT, 22), (54, YT, 24), (53, YT, 22), (53, YT, 24)]
        # treasure chamber
        self.room(48, 58, 26, 35, y=YT, height=5, floor=lambda x, z: "polished_blackstone" if (x + z) % 2 else "polished_andesite")
        self.room(51, 52, 25, 25, y=YT, height=3)
        o.chest(53, YT, 35, "north", "premium")
        o.s(52, YT, 35, "gold_block")
        o.s(54, YT, 35, "gold_block")
        for x in (49, 57):
            o.chest(x, YT, 26, "south", "tesoro")
        o.s(52, YT + 1, 35, S("candle", candles=3, lit=True, waterlogged=False))
        o.s(54, YT + 1, 35, S("candle", candles=3, lit=True, waterlogged=False))
        o.hang(53, YT + 4, 30)
        o.t.entity(53, YT, 31, corsair())
        o.hidden += [(x, YT, z) for x in range(48, 59) for z in range(26, 36)]
        o.hidden += [(x, YT, z) for x in range(52, 57) for z in range(22, 25)]


def corsair():
    from .construction import K
    return pieces.guardian("skeleton", K + "guardian", "Roque Salitre, el corsario", 60, armor=6,
                           equipment={"mainhand": {"id": "minecraft:bow", "count": 1},
                                      "head": {"id": "minecraft:chainmail_helmet", "count": 1},
                                      "chest": {"id": "minecraft:leather_chestplate", "count": 1}},
                           drop_chances={"mainhand": 0.1, "head": 0.1, "chest": 0.1},
                           attributes={"attack_damage": 4, "knockback_resistance": 0.4},
                           extra={"CanPickUpLoot": B(0)})
