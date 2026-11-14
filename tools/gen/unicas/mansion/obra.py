"""Construcción de la mansión encantada en coordenadas de la finca.

Finca x 0..61, z 0..71 (fachada al norte); y=0 es la capa de suelo y el sótano queda en y<0.
Todo se construye en una plantilla única (la «obra») que luego se parte en las piezas casa (y>=0) y sotano (y<0).
"""
import random
from nbtlib import Compound, String, Byte, IntArray, Float, Int, List, Double
from core import Template, B, F
from .._comun.piezas import spawner, chest, guardian, painting, spiral_continuous
from .._comun import piezas

X0, X1, Z0, Z1 = 12, 49, 14, 40          # muros de la casa principal
GF, P1, P2, AT, CS = 2, 8, 13, 18, -5    # pies en cada planta (sótano CS)
WALL, TRIM, BASE = "deepslate_bricks", "polished_deepslate", "cobbled_deepslate"
FLOOR, PART, BEAM = "spruce_planks", "spruce_planks", "stripped_spruce_log"
GLASS, ROOF = "gray_stained_glass_pane", "deepslate_tile"
CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
OPP = {"north": "south", "south": "north", "east": "west", "west": "east"}
D = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
LOOT = "heraldia:unicas/mansion/"


def S(name, **p):
    if not p:
        return name
    return name + "[" + ",".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}" for k, v in p.items()) + "]"


class Obra:
    def __init__(self):
        self.t = Template("unicas/mansion/obra")
        self.r = random.Random(1887)
        self.chests = []          # (pos, tabla)
        self.spawners = []
        self.hidden = []          # celdas que solo se alcanzan con los mecanismos
        self.mech = {}            # posiciones de los mecanismos para el simulador

    # ------------------------------------------------------------ primitivas
    def s(self, x, y, z, st, nbt=None):
        self.t.set(x, y, z, st, nbt)

    def f(self, x1, y1, z1, x2, y2, z2, st):
        self.t.fill(x1, y1, z1, x2, y2, z2, st)

    def a(self, x1, y1, z1, x2, y2, z2):
        self.t.fill(x1, y1, z1, x2, y2, z2, "air")

    def get(self, x, y, z):
        return self.t.get(x, y, z)

    def stair(self, x, y, z, m, facing, half="bottom"):
        self.s(x, y, z, S(m + "_stairs", facing=facing, half=half))

    def door(self, x, y, z, facing, m="spruce", hinge="left"):
        self.s(x, y, z, S(f"{m}_door", facing=facing, half="lower", hinge=hinge, open=False, powered=False))
        self.s(x, y + 1, z, S(f"{m}_door", facing=facing, half="upper", hinge=hinge, open=False, powered=False))

    def ddoor(self, x, y, z, facing, m="spruce"):
        """Puerta doble: hoja en x/z y su pareja al este (muro norte-sur) o al sur (muro este-oeste)."""
        piezas.double_door(self.s, x, y, z, facing, "east" if facing in ("north", "south") else "south", f"{m}_door")

    def bed(self, x, y, z, facing, color="red"):
        dx, dz = D[facing]
        self.s(x, y, z, S(f"{color}_bed", facing=facing, part="foot", occupied=False))
        self.s(x + dx, y, z + dz, S(f"{color}_bed", facing=facing, part="head", occupied=False))

    def chest(self, x, y, z, facing, table, kind="chest"):
        chest(self.t.set, x, y, z, facing, LOOT + table, kind)
        self.chests.append(((x, y, z), table))

    def spawner(self, x, y, z, mob):
        spawner(self.t.set, x, y, z, mob, potentials=True)
        self.spawners.append((x, y, z))

    def lamp(self, x, y, z):
        self.s(x, y, z, S("soul_lantern", hanging=True, waterlogged=False))

    def candle(self, x, y, z, n=1, lit=False, color=""):
        self.s(x, y, z, S((color + "_" if color else "") + "candle", candles=n, lit=lit, waterlogged=False))

    def table(self, x1, z1, x2, z2, y, m="spruce"):
        self.f(x1, y, z1, x2, y, z2, S(f"{m}_slab", type="top", waterlogged=False))

    def web(self, x, y, z):
        if self.get(x, y, z) in (None, "minecraft:air") and any(
                self.get(x + a, y + b, z + c) not in (None, "minecraft:air", "minecraft:cobweb")
                for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
            self.s(x, y, z, "cobweb")

    def webs(self, x1, z1, x2, z2, y, p=0.5):
        for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
            if self.r.random() < p:
                self.web(x, y, z)

    def painting(self, x, y, z, facing, variant):
        self.t.entity(x, y, z, painting(x, y, z, facing, variant))

    # ------------------------------------------------------------ construcción
    def build(self):
        self.terreno()
        self.cerca()
        self.jardin()
        self.casco()
        self.vestibulo()
        self.biblioteca()
        self.franja_oculta()
        self.cocina()
        self.comedor()
        self.salon()
        self.primera()
        self.segunda()
        self.torreon()
        self.tejado()
        self.buhardilla()
        self.chimeneas()
        self.invernadero()
        self.trasera()
        self.cementerio()
        self.panteon()
        self.sotano()
        self.escaleras_cruzadas()
        self.redstone()
        self.criaturas()
        return self

    # ---------------------------------------------------------------- exterior
    def terreno(self):
        r = self.r
        for x in range(62):
            for z in range(72):
                v = r.random()
                self.s(x, 0, z, "podzol" if v < 0.12 else "coarse_dirt" if v < 0.2 else "mud" if v < 0.25 else "grass_block")
        self.a(0, 1, 0, 61, 4, 71)           # despeja la finca (terreno sobrante, plantas)
        for z in range(0, 10):
            for x in (30, 31):
                self.s(x, 0, z, "mossy_cobblestone" if r.random() < 0.35 else "cobblestone")

    def cerca(self):
        r = self.r
        gaps = {(x, 71) for x in (9, 10, 11)} | {(61, z) for z in (50, 51)} | {(0, z) for z in (20, 21, 22)}
        ring = [(x, 0) for x in range(62)] + [(x, 71) for x in range(62)] + \
               [(0, z) for z in range(1, 71)] + [(61, z) for z in range(1, 71)]
        for x, z in ring:
            if 28 <= x <= 33 and z == 0:
                continue
            if (x, z) in gaps:
                continue
            corner = (x in (0, 61) and z in (0, 71))
            if corner or (z in (0, 71) and x % 6 == 4) or (x in (0, 61) and z % 6 == 0):
                self.f(x, 1, z, x, 2, z, "mossy_stone_bricks" if r.random() < 0.5 else "stone_bricks")
                if r.random() < 0.6:
                    self.s(x, 3, z, S("soul_lantern", hanging=False, waterlogged=False))
            else:
                self.s(x, 1, z, "mossy_cobblestone_wall" if r.random() < 0.4 else "cobblestone_wall")
        for x, z in ((10, 70), (11, 69), (60, 50), (1, 21)):          # cascotes del muro caído
            self.s(x, 1, z, "mossy_cobblestone")
        # verja: pilares, rejas y una hoja de la cancela abierta (la otra se perdió)
        for x in (28, 33):
            self.f(x, 1, 0, x, 3, 0, "stone_bricks")
            self.s(x, 4, 0, S("soul_lantern", hanging=False, waterlogged=False))
        for x in (29, 32):
            self.f(x, 1, 0, x, 2, 0, "iron_bars")
        self.s(30, 1, 0, S("spruce_fence_gate", facing="south", open=True, in_wall=False, powered=False))

    def jardin(self):
        r = self.r
        for x, z, lit in ((28, 4, True), (33, 4, True), (28, 8, True), (33, 8, False)):
            self.f(x, 1, z, x, 2 if lit else 1, z, "spruce_fence")
            if lit:
                self.s(x, 3, z, S("soul_lantern", hanging=False, waterlogged=False))
        for cx in (19, 42):                    # árboles muertos simétricos
            m = 1 if cx < 30 else -1
            self.f(cx, 1, 6, cx, 8, 6, S("spruce_log", axis="y"))
            self.f(cx + m, 5, 6, cx + 2 * m, 5, 6, S("spruce_log", axis="x"))
            self.s(cx + 2 * m, 6, 6, S("spruce_log", axis="y"))
            self.f(cx - m, 7, 6, cx - 2 * m, 7, 6, S("spruce_log", axis="x"))
            self.f(cx, 6, 7, cx, 6, 8, S("spruce_log", axis="z"))
            self.s(cx, 6, 5, S("spruce_log", axis="z"))
            self.s(cx, 0, 6, "podzol")
        for x, z in ((24, 2), (25, 2), (37, 2), (36, 2), (14, 10), (47, 10), (5, 30), (56, 44)):
            self.s(x, 1, z, S("spruce_leaves", persistent=True, distance=7, waterlogged=False))
        for _ in range(30):                    # matas secas sobre podsol
            x, z = r.randint(2, 59), r.randint(2, 12)
            if self.get(x, 1, z) == "minecraft:air" and not 26 <= x <= 35:
                self.s(x, 0, z, "podzol")
                self.s(x, 1, z, "dead_bush")
        # cobertizo del jardín (oeste)
        self.f(2, 1, 44, 6, 3, 48, PART)
        self.a(3, 1, 45, 5, 3, 47)
        self.f(2, 0, 44, 6, 0, 48, FLOOR)
        self.f(1, 4, 43, 7, 4, 49, S("spruce_slab", type="bottom", waterlogged=False))
        self.door(4, 1, 44, "south", hinge="left")
        self.s(3, 2, 48, GLASS); self.s(5, 2, 48, GLASS)
        self.chest(3, 1, 47, "east", "jardin", "barrel")
        self.s(5, 1, 47, "composter")
        self.s(5, 1, 45, S("spruce_trapdoor", facing="north", half="bottom", open=False))
        self.web(5, 3, 47)
        self.f(4, 0, 40, 4, 0, 43, "coarse_dirt")

    # ---------------------------------------------------------------- casco de la casa
    def casco(self):
        self.f(X0, 0, Z0, X1, 0, Z1, BASE)
        for y in range(2, 17):                 # interior despejado (los suelos se ponen después)
            self.a(X0 + 1, y, Z0 + 1, X1 - 1, y, Z1 - 1)
        for y in range(1, 18):
            for x in range(X0, X1 + 1):
                for z in (Z0, Z1):
                    self.s(x, y, z, self.wallmat(x, y, z))
            for z in range(Z0, Z1 + 1):
                for x in (X0, X1):
                    self.s(x, y, z, self.wallmat(x, y, z))
        for y, m in ((1, FLOOR), (7, FLOOR), (12, FLOOR), (17, FLOOR)):
            self.f(X0 + 1, y, Z0 + 1, X1 - 1, y, Z1 - 1, m)
        self.a(25, 7, 15, 36, 7, 24)          # vacío del vestíbulo
        # tabiques
        for y in range(2, 7):
            self.f(24, y, 15, 24, y, 39, WALL); self.f(37, y, 15, 37, y, 39, WALL)
            self.f(13, y, 31, 23, y, 31, PART); self.f(25, y, 30, 36, y, 30, WALL)
            self.f(13, y, 27, 23, y, 27, "bookshelf")
        for y in range(8, 12):
            self.f(24, y, 15, 24, y, 39, PART); self.f(37, y, 15, 37, y, 39, PART)
            self.f(13, y, 25, 23, y, 25, PART); self.f(13, y, 29, 23, y, 29, PART); self.f(25, y, 30, 36, y, 30, PART)
        for y in range(13, 17):
            self.f(13, y, 25, 48, y, 25, PART); self.f(13, y, 29, 48, y, 29, PART)
            for x in (24, 37):
                self.f(x, y, 15, x, y, 24, PART); self.f(x, y, 30, x, y, 39, PART)
        # ventanas: (fachada, coordenada a lo largo, planta)
        lv = {GF: (3, 5), P1: (9, 10), P2: (14, 15)}
        front = [16, 19, 22, 27, 34, 39, 42, 45]
        win = []
        for l in (GF, P1, P2):
            win += [("z", Z0, x, l) for x in front]
        win += [("z", Z0, x, l) for x in (30, 31) for l in (P1, P2)]
        win += [("z", Z1, x, GF) for x in (16, 19, 22, 27, 34, 39, 47)]
        win += [("z", Z1, x, l) for x in (16, 19, 22, 27, 30, 31, 34, 39, 47) for l in (P1, P2)]
        win += [("x", X0, z, GF) for z in (19, 22, 25, 33)]
        win += [("x", X0, z, l) for z in (19, 22, 27, 33, 37) for l in (P1, P2)]
        win += [("x", X1, z, GF) for z in (18, 21, 24, 30, 33, 36)]
        win += [("x", X1, z, P1) for z in (18, 21, 24, 27, 30, 33, 36)]
        win += [("x", X1, z, P2) for z in (18, 21, 24, 27, 33, 36)]
        for ax, c, along, l in win:
            y1, y2 = lv[l]
            x, z = (along, c) if ax == "z" else (c, along)
            for y in range(y1, y2 + 1):
                self.s(x, y, z, GLASS)
            self.s(x, y2 + 1, z, TRIM)
            self.s(x, y1 - 1, z, TRIM)
        # puertas interiores
        self.ddoor(30, GF, Z0, "south")                       # entrada
        self.door(24, GF, 17, "east"); self.door(37, GF, 17, "west")
        self.ddoor(30, GF, 30, "south")                       # vestíbulo -> comedor
        self.door(24, GF, 35, "east")                         # comedor -> cocina
        self.door(X1, GF, 27, "east")                         # salón -> invernadero
        self.ddoor(30, GF, Z1, "north", m="spruce")           # comedor -> terraza
        self.door(24, P1, 27, "west"); self.door(37, P1, 27, "east"); self.ddoor(30, P1, 30, "south")
        self.door(18, P1, 25, "north"); self.door(18, P1, 29, "south")
        for x in (18, 30, 43):
            self.door(x, P2, 25, "north"); self.door(x, P2, 29, "south")
        # porche
        self.f(26, 1, 11, 35, 1, 13, TRIM)
        for x in range(29, 33):
            self.stair(x, 1, 10, "polished_deepslate", "south")
        for x in (26, 35):
            self.f(x, 2, 11, x, 5, 11, S(BEAM, axis="y"))
        self.f(25, 6, 10, 36, 6, 13, S(ROOF + "_slab", type="bottom", waterlogged=False))
        for x in range(25, 37):
            self.s(x, 7, 10, "spruce_fence")
        for z in range(11, 14):
            self.s(25, 7, z, "spruce_fence"); self.s(36, 7, z, "spruce_fence")
        for x in (27, 34):
            self.s(x, 2, 13, S("potted_dead_bush"))

    def wallmat(self, x, y, z):
        if y == 1:
            return BASE
        if x in (X0, X1) and z in (Z0, Z1):
            return TRIM
        if y in (7, 12, 17):
            return TRIM
        return WALL

    # ---------------------------------------------------------------- planta baja
    def vestibulo(self):
        for x in range(25, 37):
            for z in range(15, 30):
                self.s(x, 1, z, "polished_deepslate" if (x + z) % 2 else "calcite")
        for z in range(15, 25):
            self.s(30, 1, z, "red_terracotta"); self.s(31, 1, z, "red_terracotta")
        for k in range(6):                      # escalera doble
            z, y = 19 + k, 2 + k
            for x in (25, 26, 35, 36):
                self.f(x, 2, z, x, y - 1, z, "stripped_spruce_wood")
                self.stair(x, y, z, "spruce", "south")
        for x in (27, 34):                      # pilares bajo el rellano
            self.f(x, 2, 25, x, 6, 25, S(BEAM, axis="y"))
        for x in range(27, 35):
            self.s(x, 8, 25, "spruce_fence")
        self.lamp(30, 9, 20); self.lamp(31, 9, 20)
        self.lamp(30, 6, 27); self.lamp(31, 6, 27)
        for x in (26, 35):
            self.s(x, 2, 15, TRIM); self.s(x, 3, 15, "potted_wither_rose")
        self.webs(25, 15, 36, 29, 11, 0.8)
        self.web(26, 10, 16); self.web(35, 11, 24)
        for x, z in ((25, 17), (36, 17)):       # bancos contra el muro, junto a las puertas laterales
            pass
        self.s(28, 2, 29, S("spruce_stairs", facing="south", half="bottom"))
        self.s(33, 2, 29, S("spruce_stairs", facing="south", half="bottom"))

    def biblioteca(self):
        bs = "bookshelf"
        for z in range(17, 27):
            if z not in (19, 22, 25):
                self.f(13, 2, z, 13, 6, z, bs)
            else:
                self.f(13, 6, z, 13, 6, z, bs)
        for x in (17, 18, 20, 21, 23):
            self.f(x, 2, 15, x, 6, 15, bs)
        for z in (15, 16, 19, 20, 21, 22, 23, 24, 25):
            self.f(23, 2, z, 23, 6, z, bs)
        # cuerpo saliente que oculta el mecanismo y nicho de la puerta secreta
        self.f(20, 2, 26, 21, 6, 26, bs)
        self.f(23, 2, 26, 23, 6, 26, bs)
        self.f(22, 4, 26, 22, 6, 26, bs)
        self.a(22, 2, 26, 22, 3, 26)
        # mesa de lectura con sillas
        self.table(17, 20, 18, 21, 2)
        self.stair(16, 2, 20, "spruce", "west"); self.stair(16, 2, 21, "spruce", "west")
        self.stair(19, 2, 20, "spruce", "east"); self.stair(19, 2, 21, "spruce", "east")
        self.candle(17, 3, 20, 3); self.candle(18, 3, 21, 1, True)
        self.s(14, 2, 22, S("lectern", facing="east", has_book=False, powered=False))
        self.s(14, 2, 19, S("lectern", facing="east", has_book=False, powered=False))
        self.chest(14, 2, 26, "north", "biblioteca")
        self.lamp(18, 6, 18); self.lamp(18, 6, 23)
        for x in range(15, 23):
            for z in range(17, 26):
                if self.get(x, 2, z) == "minecraft:air" and (x, z) not in ((22, 26),):
                    self.s(x, 1, z, "dark_oak_planks" if (x + z) % 2 else FLOOR)
        self.webs(14, 17, 22, 25, 6, 0.7)
        self.web(16, 2, 16)

    def franja_oculta(self):
        """Franja z 28..30 tras la estantería: mecanismo y escalera secreta."""
        self.f(13, 2, 28, 23, 6, 30, BASE)
        for x, z in ((22, 28), (22, 29), (22, 30), (21, 30), (20, 30), (19, 30), (18, 30)):
            self.a(x, 2, z, x, 3, z)
        self.a(17, 2, 30, 17, 3, 30)
        self.s(21, 4, 29, S("soul_wall_torch", facing="south")) if False else None
        self.web(18, 3, 30); self.web(22, 3, 30)
        self.hidden += [(22, 2, 29), (19, 2, 30)]

    def cocina(self):
        for x in range(13, 24):
            for z in range(32, 40):
                self.s(x, 1, z, "polished_tuff")
        # hogar en el muro oeste
        self.a(12, 2, 35, 12, 3, 36)
        self.f(12, 1, 35, 12, 1, 36, "bricks")
        self.s(12, 2, 35, S("campfire", facing="east", lit=False, signal_fire=False, waterlogged=False))
        self.s(12, 2, 36, S("campfire", facing="east", lit=False, signal_fire=False, waterlogged=False))
        self.f(12, 4, 34, 12, 6, 37, "bricks")
        self.f(13, 4, 34, 13, 4, 37, S("brick_slab", type="top", waterlogged=False))
        self.s(13, 2, 33, S("cauldron"))
        self.s(13, 2, 37, S("smoker", facing="east", lit=False))
        # encimera y despensa contra el muro norte
        for x in range(15, 23):
            self.s(x, 2, 32, "smooth_stone")
        self.chest(16, 2, 32, "south", "cocina", "barrel")
        self.chest(22, 2, 32, "south", "cocina", "barrel")
        self.s(19, 2, 32, "crafting_table")
        self.s(17, 3, 32, "decorated_pot"); self.candle(20, 3, 32, 2)
        # mesa de trabajo
        self.table(18, 35, 19, 35, 2)
        self.stair(18, 2, 34, "spruce", "north"); self.stair(19, 2, 36, "spruce", "south")
        # barandilla de la escalera de servicio
        self.s(17, 2, 38, "spruce_fence"); self.s(18, 2, 38, "spruce_fence"); self.s(19, 2, 39, "spruce_fence")
        self.lamp(18, 6, 34)
        self.webs(13, 32, 23, 39, 6, 0.8)

    def comedor(self):
        for x in range(25, 37):
            for z in range(31, 40):
                self.s(x, 1, z, "dark_oak_planks" if x in (30, 31) else FLOOR)
        self.table(30, 33, 31, 37, 2, "dark_oak")
        for z in range(33, 38):
            self.stair(29, 2, z, "spruce", "west"); self.stair(32, 2, z, "spruce", "east")
        for x in (30, 31):
            self.stair(x, 2, 32, "spruce", "north"); self.stair(x, 2, 38, "spruce", "south")
        for z, n, lit in ((33, 3, False), (35, 4, True), (37, 2, False)):
            self.candle(30, 3, z, n, lit, "white"); self.candle(31, 3, z + (1 if z < 37 else 0), 1, False, "white")
        self.lamp(30, 5, 35); self.lamp(31, 5, 35)
        for z in (32, 33, 37, 38):                # aparadores
            self.s(25, 2, z, "spruce_planks"); self.s(36, 2, z, "spruce_planks")
        self.chest(25, 2, 36, "east", "menor")
        self.chest(36, 2, 35, "west", "cocina", "barrel")
        self.s(25, 3, 32, "decorated_pot"); self.s(36, 3, 38, "decorated_pot")
        self.webs(25, 31, 36, 39, 6, 0.9)

    def salon(self):
        for x in range(38, 49):
            for z in range(15, 40):
                self.s(x, 1, z, "polished_blackstone" if (x + z) % 2 else "smooth_quartz")
        # chimenea en el muro sur
        self.a(43, 2, 40, 43, 3, 40)
        self.s(43, 1, 40, "bricks")
        self.s(43, 2, 40, S("soul_campfire", facing="north", lit=True, signal_fire=False, waterlogged=False))
        for x in (42, 44):
            self.f(x, 2, 39, x, 4, 39, TRIM)
        self.f(42, 5, 39, 44, 5, 39, S("polished_deepslate_slab", type="top", waterlogged=False))
        self.s(43, 4, 40, "bricks")
        self.candle(42, 5, 39, 3) if False else None
        for z in (21, 27, 33):
            self.lamp(43, 5, z)
        self.s(41, 2, 30, S("soul_lantern", hanging=False, waterlogged=False))   # lámpara caída
        self.web(41, 3, 30)
        # asientos contra el muro oeste (respaldo al muro) y mesitas
        for z in (20, 21, 33, 34):
            self.stair(38, 2, z, "spruce", "west")
        for z in (19, 22, 32, 35):
            self.table(38, z, 38, z, 2)
        self.candle(38, 3, 19, 1); self.candle(38, 3, 35, 2, True)
        self.chest(48, 2, 39, "west", "menor")
        self.s(38, 2, 39, "jukebox")
        self.webs(38, 15, 48, 39, 6, 0.9)

    # ---------------------------------------------------------------- plantas altas
    def primera(self):
        y = P1
        # dormitorio principal
        for x in range(15, 23):
            for z in range(17, 24):
                self.s(x, 8, z, "red_carpet") if 15 <= x <= 19 and 18 <= z <= 23 else None
        self.bed(14, y, 20, "west", "black"); self.bed(14, y, 21, "west", "black")
        self.table(13, 19, 13, 19, y); self.table(13, 22, 13, 22, y)
        self.candle(13, y + 1, 19, 2); self.candle(13, y + 1, 22, 1)
        self.f(23, y, 17, 23, y + 2, 18, "spruce_planks")       # armario
        self.s(22, y, 17, S("spruce_trapdoor", facing="west", half="bottom", open=True))
        self.chest(23, y, 23, "west", "menor")
        self.lamp(18, 11, 20)
        self.webs(15, 15, 23, 24, 11, 0.8)
        # pasillo
        for x in range(13, 24):
            self.s(x, y, 27, "red_carpet")
        self.lamp(18, 11, 27)
        # dormitorio de invitados (pasa la escala de servicio por x=13 z=38)
        self.bed(22, y, 33, "east", "gray")
        self.table(23, 32, 23, 32, y); self.candle(23, y + 1, 32, 1)
        self.chest(23, y, 36, "west", "menor")
        self.f(18, y, 39, 20, y + 1, 39, "spruce_planks")
        self.s(16, y, 39, "decorated_pot")
        self.lamp(18, 11, 34)
        self.webs(14, 30, 23, 39, 11, 0.8)
        # estudio del señor
        self.table(29, 36, 32, 36, y, "dark_oak")
        self.stair(30, y, 37, "spruce", "south"); self.stair(31, y, 37, "spruce", "south")
        self.candle(29, y + 1, 36, 3); self.candle(32, y + 1, 36, 1, True)
        for x in range(25, 37):
            if x not in (27, 30, 31, 34):
                self.f(x, y, 39, x, 11, 39, "bookshelf")
        for z in range(31, 39):
            if z not in (34, 35):
                self.f(25, y, z, 25, 11, z, "bookshelf")
        self.s(36, y, 32, S("lectern", facing="west", has_book=False, powered=False))
        self.s(36, y, 38, "cartography_table")
        self.chest(36, y, 35, "west", "biblioteca")
        self.lamp(30, 11, 34)
        self.webs(26, 31, 36, 38, 11, 0.8)
        # galería de retratos
        for z in range(15, 40):
            self.s(43, y, z, "purple_carpet")
        arts = ["graham", "wanderer", "prairie_ride", "graham", "wanderer"]
        small = ["kebab", "aztec", "alban", "plant", "wasteland", "bomb", "aztec2", "meditative"]
        k = 0
        for z in (17, 19, 21, 23, 31, 33, 35, 37):
            self.painting(38, 9, z, "east", arts[k % len(arts)]); k += 1
        for i, z in enumerate((16, 19, 22, 25, 29, 32, 35, 38)):
            self.painting(48, 10 if z in (19, 22, 25, 32, 35) else 9, z, "west", small[i % len(small)]) \
                if z not in (18, 21, 24, 27, 30, 33, 36) else None
        for z in (21, 33):
            self.lamp(43, 11, z)
        self.webs(38, 15, 48, 39, 11, 0.9)

    def segunda(self):
        y = P2
        for x in range(13, 49):
            self.s(x, y, 27, "brown_carpet")
        for x in (18, 30, 43):
            self.lamp(x, 16, 27)
        # dormitorio de invitados A (puerta al torreón)
        self.bed(22, y, 20, "east", "blue"); self.table(23, 19, 23, 19, y); self.candle(23, y + 1, 19, 1)
        self.chest(16, y, 24, "north", "menor")
        self.f(19, y, 15, 20, y + 1, 15, "spruce_planks")
        self.lamp(18, 16, 20)
        # cuarto de los niños
        self.bed(26, y, 16, "north", "white"); self.bed(28, y, 16, "north", "white")
        self.s(35, y, 16, "jukebox"); self.chest(33, y, 15, "south", "menor")
        self.s(30, y, 20, "white_carpet"); self.s(31, y, 20, "white_carpet")
        self.lamp(30, 16, 20)
        # dormitorio de invitados B
        self.bed(39, y, 20, "west", "green"); self.table(38, 19, 38, 19, y); self.candle(38, y + 1, 19, 2)
        self.chest(45, y, 24, "north", "menor")
        self.lamp(43, 16, 20)
        # servicio (llega la escala)
        for z in (31, 33, 35):
            self.bed(22, y, z, "east", "brown")
        self.chest(18, y, 39, "north", "menor", "barrel")
        self.lamp(18, 16, 34)
        # costura
        for x in (26, 28):
            self.s(x, y, 39, S("loom", facing="north"))
        self.chest(35, y, 39, "north", "menor", "barrel"); self.chest(36, y, 31, "west", "menor")
        self.table(30, 34, 31, 35, y); self.stair(30, y, 33, "spruce", "north"); self.stair(31, y, 36, "spruce", "south")
        self.lamp(30, 16, 34)
        # sala de música
        for x in (39, 40, 41):
            self.s(x, y, 39, "note_block")
        self.s(47, y, 39, "jukebox"); self.chest(48, y, 31, "west", "menor")
        self.stair(43, y, 34, "spruce", "south"); self.table(43, 35, 44, 35, y)
        self.lamp(43, 16, 34)
        for x0, z0, x1, z1 in ((15, 15, 23, 24), (25, 15, 36, 24), (38, 15, 48, 24), (14, 30, 23, 39), (25, 30, 36, 39), (38, 30, 48, 39)):
            self.webs(x0, z0, x1, z1, 16, 0.7)

    # ---------------------------------------------------------------- torreón y escalera de caracol
    RING = [(10, 12), (11, 12), (12, 12), (12, 13), (12, 14), (11, 14), (10, 14), (10, 13)]

    def torreon(self):
        tx0, tx1, tz0, tz1 = 8, 14, 10, 16
        self.f(tx0, 0, tz0, tx1, 0, tz1, BASE)
        for y in range(1, 27):
            for x in range(tx0, tx1 + 1):
                for z in range(tz0, tz1 + 1):
                    edge = x in (tx0, tx1) or z in (tz0, tz1)
                    if edge:
                        corner = x in (tx0, tx1) and z in (tz0, tz1)
                        self.s(x, y, z, BASE if y == 1 else TRIM if corner or y in (7, 12, 17, 23) else WALL)
                    else:
                        self.s(x, y, z, "air")
        for y in (1, 7, 12, 17, 23):            # rellanos en el anillo exterior
            for x in range(9, 14):
                for z in range(11, 16):
                    if not (10 <= x <= 12 and 12 <= z <= 14):
                        self.s(x, y, z, FLOOR)
        self.f(10, 1, 12, 12, 1, 14, FLOOR)
        self.f(11, 1, 13, 11, 23, 13, TRIM)       # machón central
        spiral_continuous(self.t.set, self.RING, 2, 22, "minecraft:spruce_stairs", "stripped_spruce_wood")
        for x, z in (self.RING[6], self.RING[7]):
            self.s(x, 23, z, FLOOR)
        for y in (GF, P1, P2):
            self.door(14, y, 15, "east")
        self.door(13, AT, 16, "south")
        # saeteras y ventanas del mirador
        for y in (4, 10, 15, 20):
            self.s(8, y, 13, GLASS); self.s(11, y, 10, GLASS)
        for x, z in ((8, 12), (8, 14), (14, 12), (14, 14), (10, 10), (12, 10), (10, 16), (12, 16)):
            self.a(x, 24, z, x, 25, z)
            self.s(x, 24, z, "iron_bars")
        # chapitel macizo y escalonado
        for k in range(4):
            lo, hi, y0 = 8 + k, 14 - k, 27 + 2 * k
            self.f(lo, y0, lo + 2, hi, y0, hi + 2, ROOF + "s")
            for x in range(lo, hi + 1):
                for z in range(lo + 2, hi + 3):
                    if lo < hi and (x in (lo, hi) or z in (lo + 2, hi + 2)):
                        fx = "east" if x == lo else "west" if x == hi else None
                        fz = "south" if z == lo + 2 else "north" if z == hi + 2 else None
                        self.stair(x, y0 + 1, z, ROOF, fz or fx)
                    else:
                        self.s(x, y0 + 1, z, ROOF + "s")
        self.s(11, 35, 13, S("lightning_rod", facing="up", powered=False, waterlogged=False))
        self.chest(9, 24, 11, "south", "desvan")
        self.lamp(11, 26, 11)
        self.web(9, 26, 15); self.web(13, 26, 11); self.web(9, 6, 11)

    # ---------------------------------------------------------------- tejado y buhardilla
    @staticmethod
    def H(z):
        return 18 + min(z - 13, 41 - z)

    HOLE = {(x, z) for x in (40, 41, 42) for z in (19, 20)} | {(41, 21)}

    def tejado(self):
        for x in range(X0, X1 + 1):
            for z in range(13, 42):
                if x <= 14 and z <= 16:
                    continue
                h = self.H(z)
                if z == 27:
                    self.s(x, h - 1, z, ROOF + "s")
                    self.s(x, h, z, S(ROOF + "_slab", type="bottom", waterlogged=False))
                    continue
                if (x, z) in self.HOLE:
                    continue
                self.stair(x, h, z, ROOF, "south" if z < 27 else "north")
                if x in (X0, X1) and Z0 <= z <= Z1:
                    self.f(x, 18, z, x, h - 1, z, WALL)
        for x in (X0, X1):                         # ventanas de los hastiales
            for z in (26, 27, 28):
                for y in (22, 23, 24):
                    self.s(x, y, z, GLASS)
            self.f(x, 25, 26, x, 25, 28, TRIM)
            self.s(x, 33, 27, S("lightning_rod", facing="up", powered=False, waterlogged=False))
        for z in range(13, 18):                    # el tejado arranca junto al torreón
            for y in range(18, self.H(z)):
                self.s(15, y, z, WALL) if z <= 16 else None

    def buhardilla(self):
        y = AT
        for z in range(15, 40):
            for x in range(13, 49):
                if not (x <= 14 and z <= 16):
                    for yy in range(18, self.H(z)):
                        if self.get(x, yy, z) is None:
                            self.s(x, yy, z, "air")
        for x in (19, 25, 36, 42):                 # vigas
            self.f(x, 24, 20, x, 24, 34, S(BEAM, axis="z"))
        self.f(13, 17, 15, 14, 17, 16, FLOOR) if False else None
        for x, z in ((40, 19), (41, 20), (42, 19)):    # escombros bajo la gotera
            self.s(x, y, z, S(ROOF + "_slab", type="bottom", waterlogged=False))
        self.s(41, y, 19, BASE)
        self.chest(22, y, 27, "east", "desvan"); self.chest(39, y, 27, "west", "desvan")
        for x, z in ((24, 22), (26, 31), (35, 23), (33, 32), (28, 27)):
            self.s(x, y, z, S("barrel", facing="up", open=False))
        self.s(30, y, 22, "decorated_pot"); self.s(31, y, 33, S("spruce_trapdoor", facing="north", half="bottom", open=False))
        self.bed(45, y, 27, "east", "white")
        self.candle(30, y, 27, 1, True)
        for x in (20, 30, 40):
            for z in (22, 32):
                self.web(x, 23, z)
        for x in (16, 47):
            self.web(x, 19, 20); self.web(x, 19, 34)

    def chimeneas(self):
        for x0, x1, z0, z1, top in ((10, 11, 35, 36, 34), (42, 44, 41, 42, 34)):
            self.f(x0, 1, z0, x1, top, z1, "bricks")
            self.f(x0, 0, z0, x1, 0, z1, BASE)
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    if (x - x0 + z - z0) % 2 == 0:
                        self.s(x, top + 1, z, S("soul_campfire", facing="north", lit=False, signal_fire=False, waterlogged=False))
        # la chimenea trasera atraviesa el alero
        for x in range(42, 45):
            for z in (41,):
                self.s(x, 18, z, "bricks")

    # ---------------------------------------------------------------- invernadero arruinado
    def invernadero(self):
        x0, x1, z0, z1 = 50, 59, 19, 35
        self.f(x0, 0, z0, x1, 0, z1, BASE)
        self.f(x0, 1, z0, x1, 1, z1, "mossy_cobblestone")
        self.a(x0, 2, z0 + 1, x1 - 1, 7, z1 - 1)
        posts = [(x1, z) for z in range(z0, z1 + 1, 4)] + [(x, z0) for x in (x0, 54)] + [(x, z1) for x in (x0, 54)]
        for x in range(x0, x1 + 1):
            for z in (z0, z1):
                self.f(x, 2, z, x, 6, z, GLASS.replace("gray_stained_", ""))
        for z in range(z0, z1 + 1):
            self.f(x1, 2, z, x1, 6, z, "glass_pane")
        for x, z in posts:
            self.f(x, 2, z, x, 7, z, S(BEAM, axis="y"))
        self.f(x0, 7, z0, x1, 7, z1, "glass")
        for z in range(z0, z1 + 1, 4):
            self.f(x0, 7, z, x1, 7, z, S(BEAM, axis="x"))
        broken = [(x, z) for x in range(55, 60) for z in range(26, 36) if (x + 2 * z) % 3 != 0] + [(53, 31), (52, 33), (56, 29), (57, 33)]
        for x, z in broken:                       # media cubierta caída
            if self.get(x, 7, z) == "minecraft:glass":
                self.s(x, 7, z, "air")
        for x, z, y in ((59, 30, 5), (59, 30, 6), (59, 31, 4), (59, 31, 5), (59, 31, 6), (56, 35, 5), (57, 35, 6),
                        (52, 19, 4), (52, 19, 5), (59, 22, 3)):
            self.s(x, y, z, "air")
        # bancales con tierra y plantas secas
        for z in (21, 22, 32, 33):
            for x in range(52, 58):
                self.s(x, 1, z, "coarse_dirt" if (x + z) % 3 else "rooted_dirt")
                v = (x * 7 + z * 3) % 5
                self.s(x, 2, z, "dead_bush" if v < 2 else "fern" if v == 2 else "air")
        for x in range(52, 58):
            for z in (20, 23, 31, 34):
                self.s(x, 2, z, S("mud_brick_slab", type="bottom", waterlogged=False))
        self.f(54, 2, 26, 55, 2, 28, "stone_bricks")          # fuente seca
        self.a(54, 2, 27, 55, 2, 27)
        self.s(54, 1, 27, "moss_block"); self.s(55, 1, 27, "moss_block")
        self.s(54, 2, 27, "moss_carpet")
        for x, z in ((56, 30), (57, 29), (58, 31), (56, 32)):
            self.s(x, 2, z, "cobblestone" if (x + z) % 2 else "mossy_cobblestone")
        self.s(51, 2, 24, "azalea"); self.s(51, 1, 24, "moss_block"); self.s(51, 2, 30, "flowering_azalea"); self.s(51, 1, 30, "moss_block")
        for z in (23, 27):
            self.s(x1 - 1, 5, z, S("vine", west=False, east=True, north=False, south=False, up=False))
        self.chest(58, 2, 20, "west", "jardin", "barrel")
        self.web(51, 6, 20); self.web(58, 6, 34); self.web(51, 6, 34)

    def trasera(self):
        self.f(26, 1, 41, 35, 1, 43, TRIM)
        for x in range(26, 36):
            self.stair(x, 1, 44, "polished_deepslate", "north")
        for x in (26, 35):
            self.s(x, 2, 43, S("polished_deepslate_wall", up=True))
        for z in range(45, 48):
            for x in (30, 31):
                self.s(x, 0, z, "cobblestone" if (x + z) % 3 else "mossy_cobblestone")

    # ---------------------------------------------------------------- cementerio y panteón
    def cementerio(self):
        r = self.r
        cx0, cx1, cz0, cz1 = 24, 58, 48, 69
        for x in range(cx0, cx1 + 1):
            for z in (cz0, cz1):
                if not (z == cz0 and x in (30, 31)):
                    self.s(x, 1, z, "iron_bars")
        for z in range(cz0, cz1 + 1):
            for x in (cx0, cx1):
                self.s(x, 1, z, "iron_bars")
        for x in (29, 32):
            self.f(x, 1, cz0, x, 2, cz0, "stone_bricks")
            self.s(x, 3, cz0, S("soul_lantern", hanging=False, waterlogged=False))
        self.s(30, 1, cz0, S("spruce_fence_gate", facing="north", open=True, in_wall=False, powered=False))
        self.s(31, 1, cz0, S("spruce_fence_gate", facing="north", open=True, in_wall=False, powered=False))
        for z in range(cz0, 67):
            for x in (30, 31):
                self.s(x, 0, z, "gravel" if False else ("cobblestone" if (x + z) % 3 else "mossy_cobblestone"))
        for x in range(32, 39):
            for z in (58, 59, 60):
                self.s(x, 0, z, "cobblestone" if (x + z) % 3 else "mossy_cobblestone")
        stones = ["stone_brick_wall", "mossy_stone_brick_wall", "cobblestone_wall", "andesite_wall"]
        n = 0
        for z in (51, 55, 59, 63):
            for x in (26, 28, 33, 35, 37, 40, 42) if z < 55 else (26, 28, 33, 35):
                if 32 <= x <= 38 and z == 59:
                    continue
                n += 1
                if n % 7 == 3:                         # lápida caída
                    self.s(x, 1, z, S("stone_brick_slab", type="bottom", waterlogged=False))
                else:
                    self.s(x, 1, z, S(stones[n % 4], up=True))
                    if n % 5 == 1:
                        self.candle(x, 2, z, 1, n % 2 == 0, "black")
                self.s(x, 0, z + 1, "podzol"); self.s(x, 0, z + 2, "coarse_dirt")
                if n % 3 == 0:
                    self.s(x, 1, z + 1, "dead_bush")
        for x, z in ((27, 66), (55, 50), (44, 52)):
            self.f(x, 1, z, x, 4, z, S("spruce_log", axis="y"))
            self.s(x + 1, 3, z, S("spruce_log", axis="x"))
            self.s(x, 0, z, "podzol")

    def panteon(self):
        x0, x1, z0, z1 = 44, 54, 55, 63          # muros
        self.f(x0, 1, z0, x1, 5, z1, "stone_bricks")      # túmulo macizo con la cripta dentro
        self.a(x0 + 1, 2, z0 + 1, x1 - 1, 4, z1 - 1)     # cripta
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    self.s(x, 1, z, "mossy_stone_bricks" if (x + z) % 3 == 0 else "stone_bricks")
        for k in range(5):                         # escalinata al oeste
            for z in (58, 59, 60):
                self.stair(39 + k, 1 + k, z, "stone_brick", "east")
                if k:
                    self.f(39 + k, 1, z, 39 + k, k, z, "stone_bricks")
        self.f(44, 5, 58, 44, 5, 60, "stone_bricks")
        for y in range(6, 11):                     # capilla
            for x in range(x0, x1 + 1):
                for z in (z0, z1):
                    self.s(x, y, z, "stone_bricks")
            for z in range(z0, z1 + 1):
                for x in (x0, x1):
                    self.s(x, y, z, "stone_bricks")
        self.a(x0 + 1, 6, z0 + 1, x1 - 1, 10, z1 - 1)
        self.door(44, 6, 59, "east")
        for z in (57, 61):
            self.f(44, 6, z, 44, 10, z, "chiseled_stone_bricks")
        for z in (57, 61):
            self.f(x1, 7, z, x1, 9, z, "glass_pane")
        h = lambda z: 11 + min(z - 54, 64 - z)
        for x in range(x0, x1 + 1):
            for z in range(54, 65):
                if z == 59:
                    self.s(x, h(z) - 1, z, "stone_bricks")
                    self.s(x, h(z), z, S("stone_brick_slab", type="bottom", waterlogged=False))
                else:
                    self.stair(x, h(z), z, "stone_brick", "south" if z < 59 else "north")
                if x in (x0, x1) and z0 <= z <= z1:
                    self.f(x, 11, z, x, h(z) - 1, z, "stone_bricks")
        self.a(x0 + 1, 11, z0 + 1, x1 - 1, 14, z1 - 1)
        for z in range(56, 63):
            for x in range(45, 54):
                for y in range(11, h(z)):
                    if self.get(x, y, z) not in (None, "minecraft:air") and not self.get(x, y, z).startswith("minecraft:stone_brick_s"):
                        pass
        # altar y sarcófago
        self.f(53, 6, 58, 53, 6, 60, "polished_andesite")
        for z, n, lit in ((58, 3, False), (59, 1, True), (60, 2, False)):
            self.candle(53, 7, z, n, lit, "white")
        self.f(48, 6, 61, 50, 6, 61, "polished_andesite")
        self.f(48, 7, 61, 50, 7, 61, S("stone_brick_slab", type="bottom", waterlogged=False))
        # escalera a la cripta por el lado norte
        for k in range(4):
            self.stair(47 + k, 5 - k, 56, "stone_brick", "west")
            self.a(47 + k, 6 - k, 56, 47 + k, 7 - k, 56)
        for x in range(47, 51):
            self.s(x, 6, 57, "iron_bars") if x > 47 else None
        self.s(51, 1, 56, "stone_bricks")
        self.lamp(49, 13, 59)
        # cripta: nichos, placa y dinamita (como el templo del desierto)
        for x in (46, 48, 50):
            self.s(x, 2, 62, S("skeleton_skull", rotation=0))
        self.s(46, 2, 58, "bone_block"); self.s(46, 3, 58, S("skeleton_skull", rotation=4))
        self.chest(53, 2, 59, "west", "panteon")
        self.s(52, 2, 59, S("stone_pressure_plate", powered=False))
        for x, z in ((52, 59), (51, 59), (53, 59), (52, 58), (52, 60)):
            self.s(x, 0, z, S("tnt", unstable=False))
        self.mech["placa"] = (52, 2, 59)
        self.mech["tnt"] = [(52, 0, 59), (51, 0, 59), (53, 0, 59), (52, 0, 58), (52, 0, 60)]
        self.web(45, 4, 57); self.web(53, 4, 62); self.web(45, 10, 62); self.web(53, 10, 56)

    # ---------------------------------------------------------------- sótano
    ROOMS = {   # nombre: (x0, x1, z0, z1, altura de techo interior, suelo, muro)
        "ante": (13, 20, 16, 26, -2, "deepslate_tiles", "tuff_bricks"),
        "pasaje": (21, 24, 19, 21, -4, "tuff_bricks", "tuff_bricks"),
        "osario": (25, 36, 15, 30, -2, "tuff_bricks", "tuff_bricks"),
        "lab": (38, 48, 15, 27, -2, "polished_tuff", "deepslate_bricks"),
        "camara": (38, 48, 32, 39, -2, "polished_blackstone_bricks", "polished_blackstone_bricks"),
        "almacen": (25, 36, 32, 39, -2, FLOOR, "tuff_bricks"),
        "bodega": (16, 23, 32, 39, -2, "mud_bricks", "tuff_bricks"),
    }

    def sotano(self):
        self.f(X0, -7, Z0, X1, -1, Z1, "tuff")
        for x0, x1, z0, z1, top, fl, wl in self.ROOMS.values():
            self.f(x0 - 1, -6, z0 - 1, x1 + 1, -1, z1 + 1, wl)
        for x0, x1, z0, z1, top, fl, wl in self.ROOMS.values():
            self.a(x0, CS, z0, x1, top, z1)
            self.f(x0, -6, z0, x1, -6, z1, fl)
        self.a(47, CS, 29, 47, -4, 31)            # paso a la cámara
        self.f(47, -6, 29, 47, -6, 31, "polished_blackstone_bricks")
        self.door(37, CS, 22, "east")
        self.door(24, CS, 35, "east")
        self.s(30, CS, 31, S("iron_door", facing="north", half="lower", hinge="left", open=False, powered=False))
        self.s(30, CS + 1, 31, S("iron_door", facing="north", half="upper", hinge="left", open=False, powered=False))
        self.s(47, CS, 28, S("iron_door", facing="south", half="lower", hinge="left", open=False, powered=False))
        self.s(47, CS + 1, 28, S("iron_door", facing="south", half="upper", hinge="left", open=False, powered=False))
        self.s(29, -4, 30, S("stone_button", face="wall", facing="north", powered=False))
        self.mech["boton"] = (29, -4, 30)
        self.mech["puerta_almacen"] = (30, CS, 31)
        # antecámara
        self.table(16, 20, 17, 21, CS, "dark_oak"); self.stair(16, CS, 22, "spruce", "south"); self.stair(17, CS, 19, "spruce", "north")
        self.candle(16, -4, 20, 2, True); self.candle(17, -4, 21, 1)
        self.chest(13, CS, 17, "east", "oculto")
        for z in (18, 19, 23, 24):
            self.f(13, CS, z, 13, -2, z, "bookshelf")
        self.lamp(17, -2, 18)
        self.webs(13, 16, 20, 26, -2, 1.0)
        # corredor con cable trampa (como el templo de la jungla)
        self.s(22, CS, 19, S("tripwire_hook", facing="south", attached=True, powered=False))
        self.s(22, CS, 21, S("tripwire_hook", facing="north", attached=True, powered=False))
        self.s(22, CS, 20, S("tripwire", attached=True, disarmed=False, powered=False, north=True, south=True, east=False, west=False))
        for z, f in ((18, "south"), (22, "north")):
            self.s(22, -4, z, S("dispenser", facing=f, triggered=False),
                   {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": 16}]})
        self.mech["ganchos"] = [(22, CS, 19), (22, CS, 21)]
        self.mech["dispensadores"] = [(22, -4, 18), (22, -4, 22)]
        self.web(21, -4, 19); self.web(23, -4, 21)
        # osario
        for z in range(16, 30, 2):
            for x in (25, 36):
                if z == 22:
                    continue
                self.s(x, CS, z, "bone_block")
                self.s(x, CS + 1, z, S("skeleton_skull", rotation=4 if x == 25 else 12))
        for x in range(27, 35, 3):
            self.s(x, CS, 15, "bone_block"); self.s(x, CS + 1, 15, "bone_block")
        self.spawner(30, CS, 23, "skeleton")
        self.chest(35, CS, 16, "west", "oculto")
        self.lamp(30, -2, 18); self.lamp(31, -2, 28)
        self.webs(25, 15, 36, 30, -2, 1.0)
        # laboratorio
        for x in range(38, 49):
            self.f(x, CS, 15, x, -2, 15, "bookshelf") if x not in (38, 43, 48) else None
        for z in (18, 19, 23, 24):
            self.s(48, CS, z, "polished_tuff")
            self.s(48, CS + 1, z, S("brewing_stand", has_bottle_0=False, has_bottle_1=False, has_bottle_2=False))
        self.s(48, CS, 21, S("cauldron")); self.s(38, CS, 21, S("cauldron"))
        self.table(38, 18, 38, 19, CS); self.table(38, 23, 38, 24, CS)
        self.s(38, CS + 1, 18, S("brewing_stand", has_bottle_0=False, has_bottle_1=False, has_bottle_2=False))
        self.candle(38, CS + 1, 24, 3, True, "purple")
        self.chest(38, CS, 15, "south", "laboratorio"); self.chest(48, CS, 15, "south", "laboratorio")
        self.s(43, CS, 15, S("lectern", facing="south", has_book=False, powered=False))
        self.spawner(43, CS, 20, "spider")
        for x, z in ((41, 18), (45, 22), (40, 24), (46, 17), (42, 25)):
            self.web(x, CS, z)
        self.webs(38, 15, 48, 27, -2, 1.0)
        self.lamp(41, -2, 21); self.lamp(45, -2, 21)
        # combinación: 4 palancas en el muro sur, velas encendidas bajo la 1.ª y la 4.ª
        self.mech["palancas"] = []
        for i, x in enumerate((39, 41, 43, 45)):
            self.s(x, -4, 27, S("lever", face="wall", facing="north", powered=False))
            self.candle(x, CS, 27, 1, i in (0, 3), "white")
            self.mech["palancas"].append((x, -4, 27))
        self.mech["puerta_camara"] = (47, CS, 28)
        # cámara del tesoro
        for x, z in ((38, 32), (48, 32), (38, 39), (48, 39)):
            self.f(x, CS, z, x, -2, z, "gilded_blackstone")
        self.f(42, CS, 39, 44, CS, 39, "polished_blackstone_bricks")
        self.chest(43, CS + 1, 39, "north", "premium")
        self.chest(39, CS, 39, "north", "oculto"); self.chest(47, CS, 39, "north", "oculto")
        self.stair(42, CS, 38, "polished_blackstone_brick", "south"); self.stair(43, CS, 38, "polished_blackstone_brick", "south")
        self.stair(44, CS, 38, "polished_blackstone_brick", "south")
        self.lamp(40, -2, 35); self.lamp(46, -2, 35)
        self.candle(42, CS + 1, 39, 4, True, "black"); self.candle(44, CS + 1, 39, 4, True, "black")
        self.webs(38, 32, 48, 39, -2, 0.6)
        # almacén
        self.chest(25, CS, 39, "east", "menor"); self.chest(36, CS, 39, "west", "menor")
        for x, z in ((25, 33), (25, 34), (36, 33), (27, 39), (34, 39)):
            self.s(x, CS, z, S("barrel", facing="up", open=False))
        self.s(25, CS + 1, 33, S("barrel", facing="up", open=False))
        self.lamp(30, -2, 36)
        self.webs(25, 32, 36, 39, -2, 0.8)
        # bodega
        for z in range(33, 39):
            for y in (CS, CS + 1):
                self.s(16, y, z, S("barrel", facing="east", open=False))
        self.chest(16, CS + 1, 34, "east", "cocina", "barrel"); self.chest(16, CS, 37, "east", "cocina", "barrel")
        self.spawner(20, CS, 34, "zombie")
        self.lamp(21, -2, 36)
        self.webs(17, 32, 23, 38, -2, 0.8)

    def escaleras_cruzadas(self):
        """Escaleras que bajan de la casa al sótano (secreta y de servicio)."""
        # secreta: oeste por z=30 y luego al norte por x=14
        for x, y in ((17, 1), (16, 0), (15, -1), (14, -2)):
            self.stair(x, y, 30, "spruce", "east")
            self.a(x, y + 1, 30, x, y + 2, 30)
        for z, y in ((29, -3), (28, -4), (27, -5)):
            self.stair(14, y, z, "spruce", "south")
            self.a(14, y + 1, z, 14, y + 2, z)
        self.s(17, 3, 30, "cobweb")
        self.hidden += [(14, CS, 22), (30, CS, 20), (43, CS, 22), (43, CS, 35)]
        # de servicio: este por z=39 desde la cocina hasta la bodega
        for k in range(7):
            x, y = 16 + k, 1 - k
            self.stair(x, y, 39, "spruce", "west")
            self.a(x, y + 1, 39, x, y + 2, 39)
            if y - 1 >= -6 and y < 0:
                self.f(x, -6, 39, x, y - 1, 39, "tuff_bricks")
        self.f(16, -6, 39, 17, -1, 39, "tuff_bricks")
        self.s(17, 2, 39, "air")

    # ---------------------------------------------------------------- redstone (estados de reposo: ver redstone.py)
    def redstone(self):
        # estantería secreta: palanca (18,3,26) -> soporte (18,3,27) -> antorcha (18,3,28) -> polvo -> repetidor -> pistones
        self.s(18, 3, 26, S("lever", face="wall", facing="north", powered=False))
        self.s(18, 3, 28, S("redstone_wall_torch", facing="south", lit=True))
        for x in (18, 19, 20):
            self.s(x, 2, 29, BASE)
            self.s(x, 3, 29, S("redstone_wire", power=0, north="none", south="none", east="none", west="none"))
        self.s(20, 2, 28, BASE)
        self.s(20, 3, 28, S("repeater", facing="south", delay=1, locked=False, powered=False))
        for y in (2, 3):
            self.s(20, y, 27, S("sticky_piston", facing="east", extended=True))
            self.s(21, y, 27, S("piston_head", facing="east", type="sticky", short=False))
            self.s(22, y, 27, "bookshelf")
        self.mech["palanca_biblioteca"] = (18, 3, 26)
        self.mech["puerta_secreta"] = [(22, 2, 27), (22, 3, 27)]
        # combinación del laboratorio (capa oculta z 29..30 entre el laboratorio y la cámara)
        self.a(38, CS, 29, 46, -2, 30)
        self.f(38, CS, 29, 46, CS, 30, "tuff")
        self.f(38, -4, 29, 46, -2, 30, "tuff")
        wire = S("redstone_wire", power=0, north="none", south="none", east="none", west="none")
        for x in (39, 45):
            self.s(x, -4, 29, S("redstone_wall_torch", facing="south", lit=True))
            self.a(x, -3, 29, x, -3, 29)
        for x in (41, 43):
            self.s(x, -4, 29, wire)
        for x in range(39, 46):
            self.s(x, -4, 30, wire)
        self.a(46, -4, 30, 46, -4, 30)
        self.s(46, CS, 30, S("redstone_wall_torch", facing="east", lit=True))
        self.s(46, CS, 29, wire)
        self.s(46, -6, 29, "tuff")

    def criaturas(self):
        cuero = lambda i: {"id": "minecraft:" + i, "count": 1, "components": {"minecraft:dyed_color": 1908001}}
        g = guardian("wither_skeleton", "heraldia.mansion.conde", "El Conde Malaquías", 60,
                     equipment={k: cuero(i) for k, i in (("head", "leather_helmet"), ("chest", "leather_chestplate"),
                                                          ("legs", "leather_leggings"), ("feet", "leather_boots"))},
                     drop_chances={k: 0.0 for k in ("head", "chest", "legs", "feet")})
        g["Tags"] = ["heraldia_mansion_guardian"]
        self.t.entity(43, CS, 35, g)
        self.t.entity(29, AT, 30, Compound({"id": String("minecraft:cat"), "PersistenceRequired": Byte(1),
                                            "variant": String("minecraft:all_black")}))
