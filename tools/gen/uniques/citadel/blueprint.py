"""Geometría de la Ciudadela enana: una sola plantilla con todas las salas.

Coordenadas de diseño: x hacia el este, z hacia dentro de la montaña (la puerta mira al norte, z=0), y hacia arriba.
Fuera de las salas no se coloca nada (structure_void implícito): la roca natural se conserva. Cada sala recibe
una piel de dos bloques: muro labrado por dentro y piedra por fuera.
"""
import random
from core import Template, B, F
from .._common import redstone

NAME = "unicas/ciudadela/ciudadela"
LOOT = "heraldia:unicas/ciudadela/"

F0, FT, F1, FB, F2, F3 = 30, 33, 21, 15, 12, 3      # suelos por nivel (se pisa en suelo+1)
W, T, P, C, COB = "deepslate_bricks", "deepslate_tiles", "polished_deepslate", "chiseled_deepslate", "cobbled_deepslate"
BS, PB = "polished_blackstone_bricks", "polished_blackstone"
WOOD, LOG = "spruce_planks", "spruce_log"
HOST_ROCK = "stone"
RUIN_PIECE = {COB, "cracked_deepslate_bricks", "cracked_deepslate_tiles", "cobweb", "cobbled_deepslate_slab",
         "cobbled_deepslate_stairs", "magma_block", "damaged_anvil", "chipped_anvil", "tuff", "polished_basalt_x"}


def st(mat, facing, half="bottom"):
    return f"{mat}[facing={facing},half={half},shape=straight]"


def sl(mat, typ="bottom"):
    return f"{mat}[type={typ}]"


class Blueprint:
    def __init__(self):
        self.t = Template(NAME)
        self.mat = {}            # celda de aire -> material del muro de su sala
        self.rng = random.Random(1717)
        self.ruin_piece = set()       # posiciones de detalles de ruina colocados a mano
        self.lint_open = {}      # estados "abiertos" de los puzles para la auditoría de recorrido
        self.circuits = {}       # nombre -> datos para redstone.py
        self.marks = {}          # nombre -> posición (para la auditoría y los planos)

    # ------------------------------------------------------------ primitivas
    def set(self, x, y, z, s, nbt=None):
        self.t.set(x, y, z, s, nbt)

    def fill(self, x0, y0, z0, x1, y1, z1, s):
        self.t.fill(x0, y0, z0, x1, y1, z1, s)

    def carve(self, x0, y0, z0, x1, y1, z1, mat=W):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.t.set(x, y, z, "air")
                    self.mat[(x, y, z)] = mat

    def room(self, x0, z0, x1, z1, f, h, mat=W, floor=P, ceil=None):
        self.carve(x0, f + 1, z0, x1, f + h, z1, mat)
        self.fill(x0, f, z0, x1, f, z1, floor)
        if ceil:
            self.fill(x0, f + h + 1, z0, x1, f + h + 1, z1, ceil)

    def ruin(self, x, y, z, s):
        self.set(x, y, z, s)
        self.ruin_piece.add((x, y, z))

    def stairs_down(self, x0, x1, z0, dz, ftop, n, mat=W, step="deepslate_brick_stairs"):
        """Tramo de n peldaños que baja desde el suelo ftop avanzando dz por peldaño (headroom 4)."""
        up = "north" if dz > 0 else "south"
        for k in range(1, n + 1):
            z = z0 + dz * (k - 1)
            y = ftop + 1 - k
            self.carve(x0, y + 1, z, x1, y + 4, z, mat)
            for x in range(x0, x1 + 1):
                self.set(x, y, z, st(step, up))

    def chest(self, x, y, z, facing, table, name):
        self.t.chest(x, y, z, facing, LOOT + table)
        self.marks[name] = (x, y, z)

    def lantern(self, x, y, z):
        self.set(x, y, z, "lantern[hanging=true]")

    def spawner(self, x, y, z, mob, name):
        self.set(x, y, z, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": {"entity": {"id": "minecraft:" + mob}},
                                      "SpawnRange": 4, "MinSpawnDelay": 200, "MaxSpawnDelay": 800,
                                      "SpawnCount": 3, "MaxNearbyEntities": 6, "RequiredPlayerRange": 16})
        self.marks[name] = (x, y, z)

    def pillar(self, x, z, y0, y1, cap=C):
        self.set(x, y0, z, cap)
        self.fill(x, y0 + 1, z, x, y1 - 1, z, "polished_basalt[axis=y]")
        self.set(x, y1, z, cap)

    # ------------------------------------------------------------ niveles
    def build(self):
        self.porch()
        self.hall()
        self.barracks()
        self.east_wing()
        self.throne()
        self.level1()
        self.level2()
        self.level3()
        self.shell()
        self.connect()
        # la entrada (jigsaw) se coloca al final para que nada la sobrescriba
        self.t.jigsaw(35, F0, 0, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
                      final_state=f"minecraft:{T}")
        return self

    def porch(self):
        self.room(25, 0, 45, 7, F0, 14, W, T, ceil=T)
        self.fill(25, 24, 0, 45, 29, 7, W)                       # cimiento por si la ladera baja
        for x in range(25, 46):
            self.set(x, F0, 0, C if x % 4 == 3 else T)
        # fachada de 3 de grueso con la gran puerta 5 x 7 en arco
        self.fill(25, F0 + 1, 8, 45, F0 + 14, 10, W)
        self.fill(33, F0, 8, 37, F0, 10, T)
        self.carve(33, F0 + 1, 8, 37, F0 + 7, 10)
        for z in (8, 9, 10):
            self.set(33, F0 + 7, z, st("deepslate_brick_stairs", "west", "top"))
            self.set(37, F0 + 7, z, st("deepslate_brick_stairs", "east", "top"))
        for x in range(32, 39):
            self.set(x, F0 + 8, 8, "gold_block" if x in (33, 35, 37) else C)
        # columnas adosadas a la fachada y estatuas de guardianes
        for x in (31, 39):
            self.pillar(x, 7, F0 + 1, F0 + 14)
        for x0 in (27, 42):
            for x in (x0, x0 + 1):
                for z in (3, 4):
                    self.set(x, F0 + 1, z, C)
                    self.fill(x, F0 + 2, z, x, F0 + 3, z, P)
                    self.fill(x, F0 + 4, z, x, F0 + 6, z, T)
                    self.set(x, F0 + 7, z, P)
                    self.set(x, F0 + 8, z, "gold_block" if z == 3 else C)
        for x in (30, 40):                                        # braseros
            self.set(x, F0 + 1, 5, P)
            self.set(x, F0 + 2, 5, "campfire[lit=true,facing=north]")
        for x in (32, 38):
            self.set(x, F0 + 6, 7, "red_wall_banner[facing=north]")

    def hall(self):
        self.room(18, 11, 52, 44, F0, 12, W, P, ceil=T)
        for z in range(11, 45):                                   # pasillo central con incrustaciones
            for x in range(33, 38):
                self.set(x, F0, z, "gold_block" if (x == 35 and z % 6 == 2) else T)
        for xs in ((24, 25), (45, 46)):
            for z0 in (14, 20, 26, 32, 38):
                for x in xs:
                    for z in (z0, z0 + 1):
                        self.pillar(x, z, F0 + 1, F0 + 12)
        # pilar derrumbado: queda el capitel colgado del techo, el fuste caído y escombros
        for x in (45, 46):
            for z in (32, 33):
                self.fill(x, F0 + 4, z, x, F0 + 11, z, "air")
                self.ruin(x, F0 + 3, z, sl("cobbled_deepslate_slab"))
        for x in range(47, 51):
            self.ruin(x, F0 + 1, 34, "polished_basalt[axis=x]")
        for (x, z) in ((44, 31), (47, 32), (48, 33), (44, 35), (47, 36), (49, 31)):
            self.ruin(x, F0 + 1, z, sl("cobbled_deepslate_slab") if (x + z) % 2 else COB)
        for z in (17, 23, 29, 35, 41):
            for x in (30, 40):
                self.lantern(x, F0 + 8, z)
        # bancos de piedra contra los muros (respaldo hacia el muro)
        for zs in ((14, 17), (20, 23), (36, 39), (40, 43)):
            for z in range(zs[0], zs[1] + 1):
                self.set(18, F0 + 1, z, st("polished_deepslate_stairs", "west"))
                if not 30 <= z <= 36:
                    self.set(52, F0 + 1, z, st("polished_deepslate_stairs", "east"))
        self.chest(18, F0 + 1, 31, "east", "menor", "cofre_salon_o")
        self.chest(52, F0 + 1, 24, "west", "menor", "cofre_salon_e")
        # paso al salón del trono: tres peldaños
        self.carve(32, F0 + 1, 45, 38, F0 + 8, 47)
        for k, z in enumerate((45, 46, 47)):
            for x in range(32, 39):
                self.fill(x, F0, z, x, F0 + k, z, P)
                self.set(x, F0 + 1 + k, z, st("deepslate_brick_stairs", "south"))
        for x in (31, 39):
            self.set(x, F0 + 4, 44, "red_wall_banner[facing=north]")

    def barracks(self):
        self.carve(12, F0 + 1, 26, 17, F0 + 4, 28)
        self.fill(12, F0, 26, 17, F0, 28, T)
        self.room(2, 16, 11, 38, F0, 6, W, P, ceil=T)
        beds = [(2, z, "west") for z in (20, 22, 31, 33, 35, 37)] + [(11, z, "east") for z in (17, 19, 21, 23, 31, 33, 35, 37)]
        for x, z, f in beds:
            self.set(x, F0 + 1, z, f"red_bed[facing={f},part=head]")
            self.set(x + (1 if f == "west" else -1), F0 + 1, z, f"red_bed[facing={f},part=foot]")
        # mesa con bancos en el centro
        for x in range(5, 9):
            self.set(x, F0 + 1, 27, sl("spruce_slab", "top"))
            self.set(x, F0 + 1, 26, "spruce_stairs[facing=north,half=bottom,shape=straight]")
            self.set(x, F0 + 1, 28, "spruce_stairs[facing=south,half=bottom,shape=straight]")
        # armero y cofres
        self.chest(2, F0 + 1, 25, "east", "barracones", "cofre_barracones_1")
        self.chest(2, F0 + 1, 29, "east", "barracones", "cofre_barracones_2")
        self.set(2, F0 + 1, 27, "grindstone[face=floor,facing=east]")
        for z in (26, 28):
            self.t.entity(2, F0 + 1, z, {"id": "minecraft:armor_stand", "ShowArms": B(1), "Rotation": [F(270.0), F(0.0)],
                                        "equipment": {"head": {"id": "minecraft:chainmail_helmet", "count": 1},
                                                      "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}}})
        for z in (21, 34):
            self.lantern(6, F0 + 5, z)
        # esquina noroeste hundida: hueco en el techo, escombros y telarañas
        self.carve(2, F0 + 7, 16, 4, F0 + 8, 18)
        for (x, z, h) in ((2, 16, 3), (3, 16, 2), (2, 17, 2), (4, 16, 1), (3, 17, 1), (2, 18, 1)):
            for k in range(h):
                self.ruin(x, F0 + 1 + k, z, COB)
        for (x, y, z) in ((4, F0 + 6, 18), (5, F0 + 6, 16), (3, F0 + 7, 18), (5, F0 + 1, 17)):
            self.ruin(x, y, z, "cobweb")
        self.ruin(5, F0 + 1, 16, sl("cobbled_deepslate_slab"))

    def east_wing(self):
        self.carve(53, F0 + 1, 26, 53, F0 + 4, 28)
        self.fill(53, F0, 26, 53, F0, 28, T)
        self.room(54, 20, 59, 32, F0, 6, W, T, ceil=T)
        self.stairs_down(55, 57, 33, 1, F0, F0 - F1)
        self.chest(59, F0 + 1, 21, "west", "menor", "cofre_vestibulo")
        self.lantern(56, F0 + 5, 26)
        # almacén
        self.carve(60, F0 + 1, 25, 60, F0 + 3, 27)
        self.fill(60, F0, 25, 60, F0, 27, T)
        self.room(61, 16, 69, 44, F0, 6, W, P, ceil=T)
        loot = {(69, 18), (61, 33), (64, 22), (65, 31), (69, 36), (64, 36)}
        def barrel(x, z, h=1):
            for k in range(h):
                self.t.barrel(x, F0 + 1 + k, z, "up", LOOT + "almacen" if (k == 0 and (x, z) in loot) else None)
        for z in range(17, 38):
            barrel(69, z, 2 if z % 3 else 1)
            if not 23 <= z <= 29:
                barrel(61, z, 2 if z % 4 else 1)
        for z in range(19, 38):
            if z not in (28, 29):
                for x in (64, 65):
                    barrel(x, z, 2 if (z + x) % 5 == 0 else 1)
        # muro de barriles con un hueco junto al muro este: sala oculta 1
        for x in range(61, 69):
            barrel(x, 39, 2)
        self.chest(61, F0 + 1, 43, "east", "oculto", "cofre_oculto_almacen")
        self.t.barrel(62, F0 + 1, 44, "up")
        self.set(69, F0 + 1, 44, "crafting_table")
        self.lantern(65, F0 + 5, 24)
        self.lantern(65, F0 + 5, 33)

    def throne(self):
        self.room(24, 48, 46, 64, FT, 11, W, P, ceil=T)
        for z in range(48, 57):
            for x in (34, 35, 36):
                self.set(x, FT + 1, z, "red_carpet")
        for x in (28, 42):
            for z in (51, 55, 59):
                self.pillar(x, z, FT + 1, FT + 11)
        # estrado y trono
        self.fill(31, FT + 1, 58, 39, FT + 1, 63, T)
        self.fill(33, FT + 2, 60, 37, FT + 2, 63, C)
        for x in range(33, 38):
            self.set(x, FT + 1, 57, st("deepslate_tile_stairs", "south"))
        for x in range(34, 37):
            self.set(x, FT + 2, 59, st("deepslate_tile_stairs", "south"))
        self.set(35, FT + 3, 61, st("polished_blackstone_stairs", "south"))
        for x in (34, 36):
            self.set(x, FT + 3, 61, PB)
        self.fill(35, FT + 3, 62, 35, FT + 4, 62, PB)
        self.set(35, FT + 5, 62, "gold_block")
        for x in (30, 40):
            self.set(x, FT + 1, 60, PB)
            self.set(x, FT + 2, 60, "campfire[lit=true,facing=north]")
        for z in (50, 54, 62):
            self.set(24, FT + 6, z, "red_wall_banner[facing=east]")
            self.set(46, FT + 6, z, "red_wall_banner[facing=west]")
        for z in (51, 59):
            for x in (31, 39):
                self.lantern(x, FT + 8, z)
        # muro del fondo: 3 de grueso (cara, mecanismo, trasdós) con hornacinas
        self.fill(24, FT, 65, 46, FT + 11, 67, W)
        for x in (29, 35, 41):
            self.carve(x, FT + 1, 65, x, FT + 2, 65)
        for x in (29, 41):
            self.set(x, FT + 1, 66, C)
            self.set(x, FT + 2, 66, C)
        for x in (32, 38):                                        # hornacinas bajas de las palancas
            self.carve(x, FT + 1, 65, x, FT + 1, 65)
        y1, y2 = FT + 1, FT + 2
        for y in (y1, y2):
            self.set(33, y, 66, "sticky_piston[extended=true,facing=east]")
            self.set(34, y, 66, "piston_head[facing=east,short=false,type=sticky]")
            self.set(35, y, 66, W)
        self.set(32, y1, 66, "lever[face=ceiling,facing=south,powered=true]")
        self.set(38, y1, 66, "lever[face=ceiling,facing=south,powered=true]")
        self.circuits["trono"] = dict(lever=(32, y1, 66), decoy=(38, y1, 66), pistons=[(33, y1, 66), (33, y2, 66)])
        for y in (y1, y2):
            self.lint_open[(35, y, 66)] = None
        # cámara real (sala oculta 2)
        self.carve(35, y1, 67, 35, y2, 67)
        self.room(31, 68, 39, 73, FT, 5, W, T, ceil=T)
        for x in range(33, 38):
            for z in range(69, 73):
                self.set(x, FT + 1, z, "red_carpet")
        self.set(31, FT + 1, 72, "red_bed[facing=west,part=head]")
        self.set(32, FT + 1, 72, "red_bed[facing=west,part=foot]")
        self.chest(39, FT + 1, 73, "west", "real", "cofre_real")
        self.set(31, FT + 1, 68, "bookshelf")
        self.set(31, FT + 2, 68, "bookshelf")
        self.set(39, FT + 1, 68, "lectern[facing=west]")
        self.set(35, FT + 1, 73, "decorated_pot")
        self.lantern(35, FT + 4, 70)
        self.marks["puerta_trono"] = (35, y1, 66)

    def level1(self):
        self.room(53, 42, 59, 48, F1, 6, W, P, ceil=T)
        self.carve(54, F1 + 1, 49, 58, F1 + 4, 49)
        self.fill(54, F1, 49, 58, F1, 49, P)
        # forjas
        self.room(36, 50, 64, 70, F1, 9, BS, BS, ceil=BS)
        for z in range(50, 71):
            for x in range(48, 53):
                self.set(x, F1, z, P)
        for i, c in enumerate((41, 47, 53, 59)):
            cold = c == 59
            self.fill(c - 2, F1 + 1, 68, c + 2, F1 + 1, 70, PB)
            for x in range(c - 1, c + 2):
                if cold:
                    self.ruin(x, F1 + 1, 69, "magma_block")
                else:
                    self.set(x, F1 + 1, 69, "lava")
                self.set(x, F1 + 2, 68, "iron_bars")
            self.fill(c - 2, F1 + 6, 68, c + 2, F1 + 9, 70, BS)
            for x in range(c - 2, c + 3):
                self.set(x, F1 + 6, 67, st("polished_blackstone_brick_stairs", "south", "top"))
            if i < 3:
                self.set(c + 3, F1 + 1, 70, "blast_furnace[facing=north]")
        stations = [("anvil[facing=east]", 43), ("smithing_table", 46), ("grindstone[face=floor,facing=north]", 49),
                    ("damaged_anvil[facing=east]", 54), ("lava_cauldron", 57), ("chipped_anvil[facing=east]", 60)]
        for s, x in stations:
            self.set(x, F1 + 1, 59, s)
        for x in (54, 60):
            self.ruin_piece.add((x, F1 + 1, 59))
        self.chest(36, F1 + 1, 56, "east", "forja", "cofre_forja_1")
        self.chest(64, F1 + 1, 62, "west", "forja", "cofre_forja_2")
        for x in (42, 58):
            self.lantern(x, F1 + 7, 54)
        self.stairs_down(38, 40, 49, -1, F1, F1 - F2, BS)
        # pasillo y cervecería
        self.carve(26, F1 + 1, 52, 35, F1 + 4, 54)
        self.fill(26, F1, 52, 35, F1, 54, P)
        self.room(8, 46, 25, 64, F1, 7, W, WOOD, ceil=T)
        for z0 in (47, 53, 59):                                    # cubas
            for x in range(8, 12):
                for z in range(z0, z0 + 4):
                    edge = x in (8, 11) and z in (z0, z0 + 3)
                    self.fill(x, F1 + 1, z, x, F1 + 4, z, "spruce_log[axis=y]" if edge else WOOD)
                    self.set(x, F1 + 5, z, sl("spruce_slab"))
            self.t.barrel(12, F1 + 2, z0 + 1, "east")
            self.set(12, F1 + 1, z0 + 1, WOOD)
        # sala oculta 3: trampilla en el rincón entre dos cubas y escalera de mano a la bodega
        self.set(8, F1 + 1, 57, "spruce_trapdoor[facing=east,half=bottom,open=false]")
        self.lint_open[(8, F1 + 1, 57)] = "spruce_trapdoor[facing=east,half=bottom,open=true]"
        self.room(8, 54, 14, 60, FB, 4, W, P, ceil=W)
        self.carve(8, FB + 1, 57, 8, F1, 57)
        for y in range(FB + 1, F1 + 1):
            self.set(8, y, 57, "ladder[facing=east]")
        self.chest(14, FB + 1, 54, "west", "oculto", "cofre_bodega")
        self.t.barrel(14, FB + 1, 60, "up")
        self.t.barrel(13, FB + 1, 60, "up")
        self.set(11, FB + 1, 60, "brewing_stand")
        self.ruin(14, FB + 4, 57, "cobweb")
        self.ruin(9, FB + 4, 54, "cobweb")
        # mesa larga con sillas, calderos, soportes y barriles
        for x in range(16, 23):
            self.set(x, F1 + 1, 55, sl("spruce_slab", "top"))
            self.set(x, F1 + 1, 54, "spruce_stairs[facing=north,half=bottom,shape=straight]")
            self.set(x, F1 + 1, 56, "spruce_stairs[facing=south,half=bottom,shape=straight]")
        for x in (16, 18, 20):
            self.set(x, F1 + 1, 46, "water_cauldron[level=3]")
        for x in (22, 23):
            self.set(x, F1 + 1, 46, WOOD)
            self.set(x, F1 + 2, 46, "brewing_stand")
        for z in range(58, 64):
            self.t.barrel(25, F1 + 1, z, "west", LOOT + "cerveceria" if z == 60 else None)
        self.chest(25, F1 + 1, 49, "west", "cerveceria", "cofre_cerveceria_1")
        self.chest(17, F1 + 1, 64, "north", "cerveceria", "cofre_cerveceria_2")
        for x, z in ((19, 50), (19, 60)):
            self.lantern(x, F1 + 6, z)

    def level2(self):
        # estación
        self.room(30, 26, 46, 40, F2, 6, W, P, ceil=T)
        for (x, z) in ((34, 28), (42, 28), (34, 38), (42, 38)):
            self.pillar(x, z, F2 + 1, F2 + 6)
        for x in range(30, 47):
            self.set(x, F2 + 1, 34, "rail[shape=east_west]")
        for x in range(32, 45):
            self.set(x, F2 + 1, 30, "rail[shape=east_west]")
        self.t.entity(36, F2 + 1, 30, {"id": "minecraft:minecart"})
        self.t.entity(42, F2 + 1, 30, {"id": "minecraft:chest_minecart", "LootTable": LOOT + "mina"})
        self.marks["vagoneta_estacion"] = (42, F2 + 1, 30)
        self.chest(30, F2 + 1, 27, "east", "menor", "cofre_estacion")
        for x in (38, 46):
            self.lantern(x, F2 + 5, 32)
        # túnel oeste con marcos de madera
        self.room(8, 33, 29, 35, F2, 4, COB, COB)
        for x in range(8, 30):
            self.set(x, F2 + 1, 34, "rail[shape=east_west]")
        for x in (11, 15, 23, 27):
            for z in (33, 35):
                self.fill(x, F2 + 1, z, x, F2 + 3, z, "spruce_fence")
            self.fill(x, F2 + 4, 33, x, F2 + 4, 35, WOOD)
        # cubil de arañas con veta de menas
        self.room(2, 30, 7, 38, F2, 5, COB, COB)
        for x in range(2, 8):
            self.set(x, F2 + 1, 34, "rail[shape=east_west]")
        self.t.entity(4, F2 + 1, 34, {"id": "minecraft:chest_minecart", "LootTable": LOOT + "mina"})
        self.marks["vagoneta_cubil"] = (4, F2 + 1, 34)
        self.spawner(3, F2 + 1, 31, "cave_spider", "generador_arañas")
        ores = ["deepslate_iron_ore", "deepslate_coal_ore", "deepslate_copper_ore", "deepslate_gold_ore", "deepslate_lapis_ore"]
        for k, (y, z) in enumerate(((F2 + 2, 31), (F2 + 3, 33), (F2 + 1, 36), (F2 + 4, 35), (F2 + 2, 37), (F2 + 4, 32))):
            self.set(1, y, z, ores[k % len(ores)])
        for (x, y, z) in ((2, F2 + 5, 30), (3, F2 + 5, 30), (2, F2 + 4, 30), (7, F2 + 5, 38), (6, F2 + 5, 38),
                          (2, F2 + 5, 38), (5, F2 + 5, 31)):
            self.ruin(x, y, z, "cobweb")
        # galería hundida, trampa de placa y escondite del minero
        self.room(18, 18, 20, 32, F2, 4, COB, COB)
        for z in (25, 26, 27):
            for x in (18, 20):
                for y in range(F2 + 1, F2 + 5):
                    self.ruin(x, y, z, COB if (x + y + z) % 3 else "tuff")
            self.ruin(19, F2 + 2, z, "cobweb")
            self.ruin(19, F2 + 3, z, COB)
            self.ruin(19, F2 + 4, z, COB)
        self.ruin(19, F2 + 1, 24, sl("cobbled_deepslate_slab"))
        for z in (20, 21, 22):
            for x in (18, 20):
                self.fill(x, F2 + 1, z, x, F2 + 4, z, COB)
        self.set(19, F2 + 1, 21, "stone_pressure_plate")
        self.set(19, F2, 21, COB)
        self.set(19, F2 - 1, 21, "tnt")
        self.circuits["tnt"] = dict(plate=(19, F2 + 1, 21), tnt=(19, F2 - 1, 21))
        self.room(15, 12, 23, 17, F2, 4, COB, WOOD)
        self.chest(15, F2 + 1, 12, "south", "oculto", "cofre_minero")
        self.t.barrel(23, F2 + 1, 12, "up")
        self.set(23, F2 + 2, 12, "lantern[hanging=false]")
        self.set(22, F2 + 1, 16, "red_bed[facing=east,part=head]")
        self.set(21, F2 + 1, 16, "red_bed[facing=east,part=foot]")
        self.set(15, F2 + 1, 16, "crafting_table")
        # abismo con lava al fondo y puente
        self.carve(47, F2 + 1, 33, 47, F2 + 4, 35)
        self.fill(47, F2, 33, 47, F2, 35, T)
        self.carve(48, 6, 20, 58, 19, 52, "abismo")
        self.fill(48, 4, 20, 58, 4, 52, COB)
        self.fill(48, 5, 20, 58, 5, 52, "lava")
        for x in range(48, 59):
            for z in (33, 34, 35):
                broken = (x, z) in ((51, 34), (55, 33), (52, 35))
                if broken:
                    self.ruin(x, F2, z, "cracked_deepslate_tiles")
                else:
                    self.set(x, F2, z, T)
            for z in (32, 36):
                self.set(x, F2, z, T)
                if not (z == 36 and x in (52, 53)):
                    self.set(x, F2 + 1, z, "deepslate_brick_wall")
        for x in (50, 56):
            for z in (32, 36):
                self.fill(x, F2 + 2, z, x, 19, z, "iron_chain[axis=y]")
        self.carve(59, F2 + 1, 33, 59, F2 + 4, 35)
        self.fill(59, F2, 33, 59, F2, 35, T)
        # rellano del abismo (mazmorra)
        self.room(60, 29, 68, 38, F2, 5, W, P, ceil=W)
        self.spawner(67, F2 + 1, 30, "skeleton", "generador_esqueletos")
        self.chest(68, F2 + 1, 37, "west", "menor", "cofre_rellano")
        for (x, y, z) in ((60, F2 + 5, 29), (68, F2 + 5, 29), (68, F2 + 5, 38)):
            self.ruin(x, y, z, "cobweb")
        # pasillo de la trampa de flechas
        self.room(63, 39, 65, 47, F2, 4, W, T, ceil=W)
        zt = 43
        self.fill(62, F2 + 1, 39, 62, F2 + 4, 47, W)
        self.fill(66, F2 + 1, 39, 66, F2 + 4, 47, W)
        self.set(63, F2 + 1, zt, "tripwire_hook[attached=true,facing=east,powered=false]")
        self.set(65, F2 + 1, zt, "tripwire_hook[attached=true,facing=west,powered=false]")
        self.set(64, F2 + 1, zt, "tripwire[attached=true,disarmed=false,east=true,west=true,north=false,south=false,powered=false]")
        arrows = {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": 9}]}
        disp = []
        for x, f in ((62, "east"), (66, "west")):
            for z in (zt - 1, zt + 1):
                self.set(x, F2 + 1, z, f"dispenser[facing={f},triggered=false]", dict(arrows))
                disp.append((x, F2 + 1, z))
        self.circuits["flechas"] = dict(hooks=[(63, F2 + 1, zt), (65, F2 + 1, zt)], dispensers=disp)
        self.stairs_down(63, 65, 48, 1, F2, F2 - F3)

    def level3(self):
        # antecámara con la cerradura de combinación
        self.room(57, 57, 71, 63, F3, 6, W, T, ceil=T)
        for z in range(57, 64):
            self.set(64, F3, z, "gold_block" if z % 3 == 0 else C)
        self.spawner(58, F3 + 1, 58, "zombie", "generador_zombis")
        zw, y = 64, F3 + 2
        self.fill(56, F3, zw, 72, F3 + 8, zw + 4, W)             # muro grueso de la bóveda (mecanismo dentro)
        order = [("A", "gold_block"), ("C", P), ("B", "gold_block"), ("D", P)]
        levers = {}
        for i, (k, blk) in enumerate(order):
            x = 57 + i
            self.set(x, y, zw, blk)
            self.set(x, y, zw - 1, "lever[face=wall,facing=north,powered=false]")
            levers[k] = (x, y, zw - 1)
            if blk == "gold_block":
                self.set(x, y, zw + 1, "redstone_wall_torch[facing=south,lit=true]")
            else:
                self.set(x, y, zw + 1, "redstone_wire")
        for x in range(57, 62):
            self.set(x, y, zw + 2, "redstone_wire")
        self.set(62, y, zw + 2, W)                                 # bloque X
        self.set(63, y, zw + 2, "redstone_wall_torch[facing=east,lit=false]")
        self.set(63, y, zw + 1, "redstone_wire")
        dx = 64
        self.set(dx, F3 + 1, zw, "iron_door[facing=south,half=lower,hinge=left,open=false,powered=false]")
        self.set(dx, F3 + 2, zw, "iron_door[facing=south,half=upper,hinge=left,open=false,powered=false]")
        self.carve(dx, F3 + 1, zw + 1, dx, F3 + 2, zw + 4)
        self.fill(dx, F3, zw + 1, dx, F3, zw + 4, T)
        self.circuits["boveda"] = dict(levers=levers, door=(dx, F3 + 1, zw), solution={"A": True, "B": True, "C": False, "D": False})
        self.marks["puerta_boveda"] = (dx, F3 + 1, zw)
        # bóveda del tesoro
        self.room(59, 69, 69, 80, F3, 7, W, T, ceil=T)
        for z in range(69, 81):
            self.set(64, F3, z, "gold_block" if z % 4 == 1 else C)
        piles = [(60, 71, 2), (60, 72, 1), (61, 71, 1), (68, 71, 2), (68, 72, 1), (67, 71, 1),
                 (60, 76, 1), (68, 76, 1), (60, 77, 2), (68, 77, 2)]
        for (x, z, h) in piles:
            for k in range(h):
                self.set(x, F3 + 1 + k, z, "raw_gold_block" if (x + z + k) % 3 else "gold_block")
        self.chest(59, F3 + 1, 74, "east", "boveda", "cofre_boveda_1")
        self.chest(69, F3 + 1, 74, "west", "boveda", "cofre_boveda_2")
        self.fill(62, F3 + 1, 77, 66, F3 + 1, 80, C)
        for x in range(63, 66):
            self.set(x, F3 + 1, 76, st("deepslate_tile_stairs", "south"))
        self.chest(64, F3 + 2, 79, "north", "premium", "cofre_premium")
        self.fill(64, F3 + 2, 80, 64, F3 + 3, 80, "gold_block")
        for x in (62, 66):
            self.set(x, F3 + 2, 80, "lantern[hanging=false]")
        for (x, z) in ((61, 72), (67, 72), (61, 78), (67, 78)):
            self.lantern(x, F3 + 6, z)
        self.t.entity(64, F3 + 1, 72, guardian())
        self.marks["guardian"] = (64, F3 + 1, 72)

    # ------------------------------------------------------------ piel y conexiones
    def shell(self):
        blocks = self.t.blocks
        air = [p for p, (s, _) in blocks.items() if s == "minecraft:air"]
        n26 = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]
        wall = {}
        for (x, y, z) in air:
            m = self.mat.get((x, y, z), W)
            for a, b, c in n26:
                q = (x + a, y + b, z + c)
                if q not in blocks and q not in wall and q[2] >= 0:
                    wall[q] = m
        for q, m in wall.items():
            if m == "abismo":
                m = self.rng.choice((COB, COB, "smooth_basalt", "tuff_bricks"))
            self.t.set(*q, m)
        n6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        inner = [p for p, (s, _) in blocks.items() if s != "minecraft:air"]
        outer = set()
        for (x, y, z) in inner:
            for a, b, c in n6:
                q = (x + a, y + b, z + c)
                if q not in blocks and q[2] >= 0:
                    outer.add(q)
        for q in outer:
            self.t.set(*q, HOST_ROCK)

    def connect(self):
        """Estados de conexión que el juego calcularía con actualizaciones (no hay ninguna al generar)."""
        g = self.t.get
        def solid(s):
            if s is None:
                return False
            b = s.split("[")[0].replace("minecraft:", "")
            return not (b in ("air", "lava", "water", "cobweb") or any(k in b for k in (
                "slab", "stairs", "fence", "_wall", "bars", "pane", "torch", "lever", "rail", "carpet", "door",
                "trapdoor", "lantern", "chain", "banner", "redstone_wire", "tripwire", "ladder", "bed", "campfire",
                "cauldron", "anvil", "grindstone", "brewing_stand", "lectern", "plate", "piston_head", "spawner")))
        for (x, y, z), (s, nbt) in list(self.t.blocks.items()):
            b = s.split("[")[0].replace("minecraft:", "")
            fam = None
            if b.endswith("_fence"):
                fam = "fence"
            elif b.endswith("_wall") and "banner" not in b and "torch" not in b:
                fam = "wall"
            elif b == "iron_bars" or b.endswith("_pane"):
                fam = "bars"
            if not fam:
                continue
            props = {}
            for d, (dx, dz) in (("north", (0, -1)), ("south", (0, 1)), ("west", (-1, 0)), ("east", (1, 0))):
                n = g(x + dx, y, z + dz)
                nb = n.split("[")[0].replace("minecraft:", "") if n else ""
                same = (fam == "fence" and nb.endswith("_fence")) or (fam == "wall" and nb.endswith("_wall") and "banner" not in nb) \
                    or (fam == "bars" and (nb == "iron_bars" or nb.endswith("_pane")))
                ok = same or solid(n)
                if fam == "wall":
                    props[d] = "low" if ok else "none"
                else:
                    props[d] = "true" if ok else "false"
            if fam == "wall":
                straight = (props["north"] != "none" and props["south"] != "none" and props["east"] == "none" and props["west"] == "none") or \
                           (props["east"] != "none" and props["west"] != "none" and props["north"] == "none" and props["south"] == "none")
                props["up"] = "false" if straight else "true"
            self.t.set(x, y, z, b + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]", nbt)
        redstone.wire_shapes(self.t)
        redstone.set_wire_power(self.t)


def guardian():
    from .._common import pieces
    return pieces.guardian("vindicator", "heraldia.ciudadela.guardian", "Borin Barbahierro, último guardián", 60,
                           equipment={"mainhand": {"id": "minecraft:iron_axe", "count": 1},
                                      "head": {"id": "minecraft:iron_helmet", "count": 1},
                                      "chest": {"id": "minecraft:iron_chestplate", "count": 1}},
                           drop_chances={"mainhand": 0.5, "head": 0.25, "chest": 0.25},
                           extra={"Rotation": [F(180.0), F(0.0)]})


def construct():
    return Blueprint().build()
