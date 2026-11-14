"""Monasterio de montaña: construcción de la plantilla única (macizo de roca, terrazas, edificios y cuevas).

Coordenadas de plantilla: x 0..58, z 0..91 (la entrada en z = 0; se sube hacia z creciente), y 0..~70.
"""
import random
from core import Template, villager, B, F

ID = "monasterio"
P = f"heraldia:unicas/{ID}/"
F0, F1, F2 = 24, 30, 36          # suelos de las terrazas (bloque de suelo; los pies van en +1)
CAVE, DEEP = 13, 5               # suelo de las cuevas y del relicario
XMAX, ZMAX = 58, 91
AIRH = 16                        # aire explícito sobre cada terraza (corta la ladera)
RECTS = [(25, 33, 0, 5, F0), (4, 54, 6, 27, F0), (4, 54, 28, 49, F1), (2, 56, 50, 87, F2)]

# materiales
SB, SBS, SBW, SBSL = "stone_bricks", "stone_brick_stairs", "stone_brick_wall", "stone_brick_slab"
TR = "polished_andesite"
RS, RF, RSL = "deepslate_tile_stairs", "deepslate_tiles", "deepslate_tile_slab"
PL, PLS, PLSL = "spruce_planks", "spruce_stairs", "spruce_slab"
DS = "deepslate_bricks"
FLOWERS = ["poppy", "dandelion", "cornflower", "azure_bluet", "oxeye_daisy", "allium"]


def h3(x, y, z, s=0):
    n = (x * 374761393 + y * 668265263 + z * 1442695041 + s * 1274126177) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return n ^ (n >> 16)


def rock(x, y, z):
    v = h3(x, y, z) % 100
    return "stone" if v < 62 else "andesite" if v < 77 else "tuff" if v < 87 else "cobblestone" if v < 95 else "diorite"


def stair(mat, facing, half="bottom"):
    return f"{mat}[facing={facing},half={half},shape=straight]"


def text(key, fallback):
    return {"translate": f"heraldia.unicas.{ID}.{key}", "fallback": fallback}


EMPTY = {"text": ""}


class Obra(Template):
    def __init__(self):
        super().__init__(f"unicas/{ID}/monasterio")
        self.rng = random.Random(1187)
        self.ruinas = []          # (x0, z0, x1, z1) huella en ruinas
        self.huella = []          # (x0, z0, x1, z1) huella construida
        self.abiertos = {}        # pos -> estado en la vista de auditoría (puertas secretas abiertas)
        self.cofres = []          # (pos, tabla)
        self.circuitos = {}       # nombre -> dict de componentes para la comprobación de redstone
        self.top = {}

    # ------------------------------------------------------------ utilidades
    def box(self, x1, y1, z1, x2, y2, z2, st):
        self.fill(x1, y1, z1, x2, y2, z2, st)

    def walls(self, x1, z1, x2, z2, y1, y2, st, corner=None):
        for x in range(x1, x2 + 1):
            for z in (z1, z2):
                self.box(x, y1, z, x, y2, z, st)
        for z in range(z1, z2 + 1):
            for x in (x1, x2):
                self.box(x, y1, z, x, y2, z, st)
        if corner:
            for x, z in ((x1, z1), (x1, z2), (x2, z1), (x2, z2)):
                self.box(x, y1, z, x, y2, z, corner)

    def door(self, x, y, z, facing, mat="spruce_door", hinge="left"):
        self.set(x, y, z, f"{mat}[facing={facing},half=lower,hinge={hinge},open=false,powered=false]")
        self.set(x, y + 1, z, f"{mat}[facing={facing},half=upper,hinge={hinge},open=false,powered=false]")

    def hang(self, x, y, z, soul=False):
        self.set(x, y, z, f"{'soul_lantern' if soul else 'lantern'}[hanging=true,waterlogged=false]")

    def chest(self, x, y, z, facing, tabla, kind="chest"):
        st = f"{kind}[facing={facing},type=single,waterlogged=false]" if kind == "chest" else f"barrel[facing={facing},open=false]"
        self.set(x, y, z, st, {"id": f"minecraft:{kind}", "LootTable": P + tabla})
        self.cofres.append(((x, y, z), tabla))

    def candle(self, x, y, z, n=1, lit=True, color=""):
        self.set(x, y, z, f"{color + '_' if color else ''}candle[candles={n},lit={'true' if lit else 'false'},waterlogged=false]")

    def sign(self, x, y, z, facing, key, lines):
        msgs = [text(f"{key}.{i + 1}", l) if l else EMPTY for i, l in enumerate(lines)]
        side = {"messages": msgs, "color": "black", "has_glowing_text": B(0)}
        self.set(x, y, z, f"spruce_wall_sign[facing={facing},waterlogged=false]",
                 {"id": "minecraft:sign", "front_text": side, "back_text": {"messages": [EMPTY] * 4, "color": "black",
                                                                               "has_glowing_text": B(0)}, "is_waxed": B(1)})

    def bed(self, x, z, y, facing, color="brown"):
        dx, dz = {"west": (-1, 0), "east": (1, 0), "north": (0, -1), "south": (0, 1)}[facing]
        self.set(x + dx, y, z + dz, f"{color}_bed[facing={facing},occupied=false,part=head]")
        self.set(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=foot]")

    def spawner(self, x, y, z, mob):
        self.set(x, y, z, "spawner", {"id": "minecraft:mob_spawner", "SpawnData": {
            "entity": {"id": f"minecraft:{mob}"},
            "custom_spawn_rules": {"block_light_limit": {"min_inclusive": 0, "max_inclusive": 11},
                                   "sky_light_limit": {"min_inclusive": 0, "max_inclusive": 15}}},
            "MaxNearbyEntities": 5, "SpawnCount": 3, "RequiredPlayerRange": 14})

    def gable_z(self, x1, x2, z1, z2, y0, end=SB):
        """Tejado a dos aguas con la cumbrera a lo largo de z; aleros de 1 bloque. Rellena los hastiales."""
        w = x2 - x1 + 3
        for i in range((w + 1) // 2):
            xa, xb, y = x1 - 1 + i, x2 + 1 - i, y0 + i
            for z in range(z1 - 1, z2 + 2):
                if xa == xb:
                    self.set(xa, y, z, f"{RSL}[type=bottom,waterlogged=false]")
                else:
                    self.set(xa, y, z, stair(RS, "east"))
                    self.set(xb, y, z, stair(RS, "west"))
            if i == 1:
                for z in range(z1, z2 + 1):
                    self.set(xa, y0, z, end)
                    self.set(xb, y0, z, end)
            for x in range(xa + 1, xb):
                for z in (z1, z2):
                    self.set(x, y, z, end)

    def gable_x(self, x1, x2, z1, z2, y0, end=SB, ox=(1, 1)):
        w = z2 - z1 + 3
        for i in range((w + 1) // 2):
            za, zb, y = z1 - 1 + i, z2 + 1 - i, y0 + i
            for x in range(x1 - ox[0], x2 + 1 + ox[1]):
                if za == zb:
                    self.set(x, y, za, f"{RSL}[type=bottom,waterlogged=false]")
                else:
                    self.set(x, y, za, stair(RS, "south"))
                    self.set(x, y, zb, stair(RS, "north"))
            if i == 1:
                for x in range(x1, x2 + 1):
                    self.set(x, y0, za, end)
                    self.set(x, y0, zb, end)
            for z in range(za + 1, zb):
                for x in (x1, x2):
                    self.set(x, y, z, end)

    def panes(self, cells, y1, y2, st="glass_pane"):
        for x, z in cells:
            self.box(x, y1, z, x, y2, z, st)

    def flowers(self, x1, z1, x2, z2, y, p=0.08):
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if self.get(x, y, z) == "minecraft:grass_block" and self.is_free(x, y + 1, z) and self.rng.random() < p:
                    self.set(x, y + 1, z, self.rng.choice(FLOWERS))

    # ------------------------------------------------------------ macizo
    def macizo(self):
        top = {}
        for x0, x1, z0, z1, h in RECTS:
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    top[(x, z)] = max(top.get((x, z), -1), h)
        self.top = top
        for x in range(0, XMAX + 1):
            for z in range(0, ZMAX + 1):
                if (x, z) in top:
                    h = top[(x, z)]
                    for y in range(0, h):
                        self.blocks[(x, y, z)] = ("minecraft:" + rock(x, y, z), None)
                    self.set(x, h, z, "grass_block[snowy=false]")
                    for y in range(h + 1, h + AIRH + 1):
                        self.blocks[(x, y, z)] = ("minecraft:air", None)
                    continue
                best = None
                for d in range(1, 5):
                    hs = [top[(x + a, z + c)] for a in range(-d, d + 1) for c in range(-d, d + 1) if (x + a, z + c) in top]
                    if hs:
                        best = (d, max(hs))
                        break
                if not best:
                    continue
                d, h = best
                ht = h - 2 - 3 * d + (h3(x, 0, z, 7) % 3) - 1
                if ht < 1:
                    continue
                for y in range(0, ht):
                    self.blocks[(x, y, z)] = ("minecraft:" + rock(x, y, z), None)
                self.set(x, ht, z, "grass_block[snowy=false]" if h3(x, 1, z) % 4 else "coarse_dirt")
        # caras de sillería hacia las terrazas más bajas, con contrafuertes
        for (x, z), h in top.items():
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                hn = top.get((x + dx, z + dz))
                if hn is not None and hn < h:
                    for y in range(hn + 1, h + 1):
                        self.set(x, y, z, SB)

    def buttresses(self, z, xs, y0, y1, side):
        """Contrafuertes delante de un muro de contención (side: hacia dónde sobresalen)."""
        dz = -1 if side == "north" else 1
        for x in xs:
            self.box(x, y0, z + dz, x, y1 - 1, z + dz, SB)
            self.set(x, y1, z + dz, stair(SBS, "south" if dz < 0 else "north"))

    # ------------------------------------------------------------ camino y atrio (T0)
    def camino(self):
        for z in range(0, 6):
            for x in range(26, 33):
                self.set(x, F0, z, "cobblestone" if h3(x, F0, z) % 3 == 0 else SB if 27 <= x <= 31 else "gravel")
            self.set(25, F0, z, "coarse_dirt")
            self.set(33, F0, z, "coarse_dirt")
        for x in (25, 33):
            self.box(x, F0 + 1, 2, x, F0 + 2, 2, SBW)
            self.set(x, F0 + 3, 2, "lantern[hanging=false,waterlogged=false]")

    def cerca(self):
        y = F0 + 1
        for x in list(range(4, 22)) + list(range(37, 55)):
            self.box(x, y, 6, x, y + 1, 6, SB)
            self.set(x, y + 2, 6, SBW)
        for z in range(6, 28):
            for x in (4, 54):
                self.box(x, y, z, x, y + 1, z, SB)
                self.set(x, y + 2, z, SBW)
        # tramo caído del cementerio (ruina): muro bajo y piedras en el suelo
        for z in range(11, 15):
            self.set(4, y + 2, z, "air")
            self.set(4, y + 1, z, "mossy_cobblestone" if z % 2 else "air")
        self.set(5, y, 12, "mossy_cobblestone")
        self.set(5, y, 13, f"{SBSL}[type=bottom,waterlogged=false]")
        self.ruinas.append((4, 11, 5, 14))
        for z in range(16, 20):                              # tramo caído de la cerca oriental
            self.set(54, y + 2, z, "air")
            self.set(54, y + 1, z, "air" if z % 2 else "mossy_stone_bricks")
        self.set(53, y, 17, "mossy_cobblestone")
        self.ruinas.append((53, 16, 54, 19))

    def porteria(self):
        x1, x2, z1, z2 = 22, 36, 6, 13
        self.huella.append((x1, z1, x2, z2))
        y = F0
        self.box(x1, y, z1, x2, y, z2, SB)
        self.walls(x1, z1, x2, z2, y + 1, y + 6, SB, corner=TR)
        for x in (27, 31):
            self.box(x, y + 1, z1, x, y + 6, z2, SB)
        self.box(x1 + 1, y + 7, z1 + 1, x2 - 1, y + 7, z2 - 1, PL)
        self.gable_x(x1, x2, z1, z2, y + 7)
        self.box(x1, y + 7, z1, x2, y + 7, z1, SB)
        self.box(x1, y + 7, z2, x2, y + 7, z2, SB)
        for z in (z1, z2):                                   # arcos del paso
            self.box(28, y + 1, z, 30, y + 4, z, "air")
            self.set(28, y + 4, z, stair(SBS, "west", "top"))
            self.set(30, y + 4, z, stair(SBS, "east", "top"))
            self.set(29, y + 5, z, "chiseled_stone_bricks")
        self.box(28, y + 1, z1 + 1, 30, y + 6, z2 - 1, "air")
        self.box(28, y, z1, 30, y, z2, "cobblestone")
        self.hang(29, y + 6, 9)
        self.hang(29, y + 6, 11)
        # portería (oeste)
        self.door(27, y + 1, 10, "east")
        self.bed(25, 12, y + 1, "west")
        self.chest(23, y + 1, 7, "east", "menor", "barrel")
        self.set(26, y + 1, 7, "crafting_table")
        self.set(23, y + 1, 9, stair(PLS, "west"))
        self.set(24, y + 1, 9, f"{PLSL}[type=top,waterlogged=false]")
        self.candle(24, y + 2, 9, 2)
        self.hang(24, y + 6, 10)
        self.panes([(24, z1), (25, z1)], y + 2, y + 3)
        self.panes([(x1, 10)], y + 2, y + 3)
        # sala de las limosnas (este)
        self.door(31, y + 1, 10, "west", hinge="right")
        for z in range(8, 12):
            self.set(35, y + 1, z, stair(PLS, "east"))
        self.chest(32, y + 1, 7, "south", "menor")
        self.set(32, y + 1, 12, SB)
        self.candle(32, y + 2, 12, 3)
        self.hang(33, y + 6, 10)
        self.panes([(33, z1), (34, z1)], y + 2, y + 3)
        self.panes([(x2, 10)], y + 2, y + 3)
        self.set(33, y + 3, z2 - 1, "white_wall_banner[facing=north]")
        # sala de limosnas: techo y cubierta hundidos (ruina); queda en pie el hastial
        for x in range(32, 38):
            for z in range(z1 - 1, z2 + 2):
                for yy in range(y + 7, y + 14):
                    st = self.get(x, yy, z) or ""
                    if "deepslate" in st or "planks" in st:
                        self.set(x, yy, z, "air")
        for yy in range(y + 10, y + 12):
            self.set(x2, yy, 9, "air")
            self.set(x2, yy, 10, "air")
        self.set(33, y + 1, 9, f"{RSL}[type=bottom,waterlogged=false]")
        self.set(34, y + 1, 11, "cobblestone")
        self.ruinas.append((32, z1, x2, z2))

    def atrio(self):
        y = F0
        for z in range(14, 22):
            for x in range(28, 31):
                self.set(x, y, z, SB if h3(x, y, z) % 5 else "cracked_stone_bricks")
        for z in (16, 20):
            for x in (27, 31):
                self.box(x, y + 1, z, x, y + 2, z, SBW)
                self.set(x, y + 3, z, "lantern[hanging=false,waterlogged=false]")
        self.buttresses(28, (8, 14, 20, 38, 44, 50), y + 1, F1 - 1, "north")
        # escalinata T0 -> T1
        self.escalinata(27, 31, 22, F0)
        self.flowers(21, 14, 37, 21, y, 0.12)

    def escalinata(self, xa, xb, z0, yb):
        """Seis peldaños subiendo hacia +z, con zancas y pretil; el último queda a ras de la terraza alta."""
        for k in range(1, 7):
            z, ys = z0 + k - 1, yb + k
            for x in range(xa, xb + 1):
                self.box(x, yb + 1, z, x, ys - 1, z, SB)
                self.set(x, ys, z, stair(SBS, "south"))
                self.box(x, ys + 1, z, x, ys + 4, z, "air")
            for x in (xa - 1, xb + 1):
                self.box(x, yb + 1, z, x, ys, z, SB)
                self.set(x, ys + 1, z, SBW)

    def cementerio(self):
        y = F0
        x1, x2, z1, z2 = 6, 20, 15, 26
        for x in range(x1, x2 + 1):
            for z in (z1, z2):
                self.set(x, y + 1, z, "cobblestone_wall")
        for z in range(z1, z2 + 1):
            for x in (x1, x2):
                self.set(x, y + 1, z, "cobblestone_wall")
        self.set(x2, y + 1, 20, "spruce_fence_gate[facing=east,in_wall=false,open=false,powered=false]")
        for gx in (8, 11, 14, 17):
            for gz in (17, 22):
                self.set(gx, y, gz + 1, "coarse_dirt")
                self.set(gx, y, gz + 2, "coarse_dirt")
                self.set(gx, y + 1, gz, SBW)
                if h3(gx, y, gz) % 3 == 0:
                    self.candle(gx, y + 1, gz + 2, 1, lit=False)
        self.box(13, y + 1, 20, 13, y + 4, 20, TR)          # cruz del cementerio
        self.set(12, y + 3, 20, TR)
        self.set(14, y + 3, 20, TR)
        for x in range(9, 13):                                # muro caído
            self.set(x, y + 1, z1, "air")
        self.set(10, y + 1, z1 + 1, "mossy_cobblestone")
        self.set(11, y + 1, z1 - 1, "cobblestone")
        self.ruinas.append((9, z1, 12, z1 + 1))
        self.flowers(x1 + 1, z1 + 1, x2 - 1, z2 - 1, y, 0.06)

    def hospederia(self):
        """Hospedería en ruinas: sin tejado, muros mellados, escombros y un cofre entre ellos."""
        y = F0
        x1, x2, z1, z2 = 38, 52, 15, 26
        self.ruinas.append((x1, z1, x2, z2))
        self.huella.append((x1, z1, x2, z2))
        self.box(x1, y, z1, x2, y, z2, "cobblestone")
        for x in range(x1 + 1, x2):
            for z in range(z1 + 1, z2):
                self.set(x, y, z, PL if h3(x, y, z) % 4 else "coarse_dirt")
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x in (x1, x2) or z in (z1, z2):
                    corner = x in (x1, x2) and z in (z1, z2)
                    hgt = 5 if corner else 2 + h3(x, 0, z, 3) % 3
                    self.box(x, y + 1, z, x, y + hgt, z, TR if corner else SB if h3(x, 1, z) % 4 else "mossy_stone_bricks")
        self.box(x1, y + 1, 20, x1, y + 2, 21, "air")        # puerta (hueco)
        self.box(45, y + 1, z1 + 1, 45, y + 3, z2 - 1, SB)   # tabique
        self.box(45, y + 1, 19, 45, y + 2, 20, "air")
        self.set(45, y + 3, 19, "air")
        for z in (17, 23):
            self.box(x2, y + 2, z, x2, y + 2, z, "air")
        # escombros, vigas caídas y camas viejas
        for x, z in ((40, 16), (41, 16), (40, 17), (49, 24), (51, 23), (47, 16), (43, 25)):
            self.set(x, y + 1, z, self.rng.choice(["cobblestone", "mossy_cobblestone", f"{SBSL}[type=bottom,waterlogged=false]"]))
        for x in range(46, 51):
            self.set(x, y + 1, 21, "stripped_spruce_log[axis=x]")
        self.bed(42, 24, y + 1, "west", "white")
        self.bed(42, 22, y + 1, "west", "white")
        self.chest(51, y + 1, 25, "west", "menor")
        self.set(50, y + 1, 25, f"{SBSL}[type=bottom,waterlogged=false]")
        self.set(51, y + 1, 24, "mossy_cobblestone")
        for z in range(z1 + 2, z2 - 1, 3):
            if "stone_bricks" in (self.get(x1, y + 2, z) or ""):
                self.set(x1 + 1, y + 2, z, "vine[east=false,north=false,south=false,up=false,west=true]")

    # ------------------------------------------------------------ T1: huerto, refectorio, cocina, bodega
    def t1(self):
        y = F1
        for z in range(28, 50):                                       # pretiles
            for x in (4, 54):
                self.set(x, y + 1, z, SBW)
        for x in range(4, 55):
            if not 26 <= x <= 32:
                self.set(x, y + 1, 28, SBW)
        for x in (12, 20, 41):                                         # huecos de ruina en el pretil
            self.set(x, y + 1, 28, "air")
        for z in range(29, 44):                                        # paseo central
            for x in range(24, 35):
                self.set(x, y, z, SB if h3(x, y, z) % 6 else "cobblestone")
        for z in (32, 40):
            self.box(24, y + 1, z, 24, y + 2, z, SBW)
            self.set(24, y + 3, z, "lantern[hanging=false,waterlogged=false]")
        self.escalinata(27, 31, 44, F1)
        self.buttresses(50, (8, 16), y + 1, F2 - 1, "north")
        self.huerto()
        self.bodega()
        self.refectorio()

    def huerto(self):
        y = F1
        crops = ["wheat[age={}]", "carrots[age={}]", "potatoes[age={}]", "beetroots[age={}]"]

        def bed(x1, x2, z1, z2, yb, chan, path_x, ci):
            for x in range(x1, x2 + 1):
                for z in range(z1, z2 + 1):
                    if x == path_x:
                        self.set(x, yb, z, SB if z == chan else "dirt_path")
                    elif z == chan:
                        self.set(x, yb, z, "water[level=0]")
                    else:
                        self.set(x, yb, z, "farmland[moisture=7]")
                        c = crops[(ci + (x > path_x) + (z > chan) * 2) % 4]
                        age = self.rng.randint(2, 7) if "wheat" in c or "carrots" in c or "potatoes" in c else self.rng.randint(1, 3)
                        self.set(x, yb + 1, z, c.format(age))
        for z in range(29, 39):
            self.set(5, y, z, "dirt_path")
            self.set(23, y, z, "dirt_path")
        for x in range(5, 24):
            self.set(x, y, 29, "dirt_path")
            self.set(x, y, 38, "dirt_path")
        bed(6, 22, 30, 37, y, 33, 14, 0)
        # bancal alto (+1)
        for x in range(5, 24):
            for z in range(39, 50):
                self.set(x, y, z, rock(x, y, z))
                self.set(x, y + 1, z, "dirt_path" if z in (40, 48, 49) or x in (10, 23) else "coarse_dirt")
            self.set(x, y + 1, 39, SB)
        self.set(14, y + 1, 39, stair(SBS, "south"))
        bed(11, 22, 41, 47, y + 1, 44, 16, 1)
        self.set(24, y + 1, 39, SBW)
        # cobertizo (tejado medio hundido)
        x1, x2, z1, z2, yb = 5, 9, 41, 47, y + 1
        self.huella.append((x1, z1, x2, z2))
        self.box(x1, yb, z1, x2, yb, z2, PL)
        self.walls(x1, z1, x2, z2, yb + 1, yb + 3, PL, corner="spruce_log[axis=y]")
        self.door(x2, yb + 1, 44, "east")
        self.panes([(x1, 43), (x1, 45)], yb + 2, yb + 2)
        self.gable_z(x1, x2, z1, z2, yb + 4, end=PL)
        for x in range(x1 - 1, x2 + 2):                                 # media cubierta caída
            for z in range(z1 - 1, 44):
                for yy in range(yb + 4, yb + 8):
                    if "deepslate" in (self.get(x, yy, z) or ""):
                        self.set(x, yy, z, "air")
        for x in range(x1 + 1, x2):
            for z in range(z1, 44):
                if z == z1:
                    self.box(x, yb + 4, z, x, yb + 7, z, "air")
        self.ruinas.append((x1, z1, x2, 43))
        self.set(6, yb + 1, 42, "hay_block[axis=y]")
        self.set(7, yb + 1, 42, f"{PLSL}[type=bottom,waterlogged=false]")
        self.set(6, yb + 1, 46, "composter[level=3]")
        self.chest(8, yb + 1, 46, "west", "menor")
        self.set(6, yb + 1, 44, "barrel[facing=up,open=false]")
        self.candle(6, yb + 2, 44, 1)
        self.flowers(24, 44, 26, 49, y, 0.3)

    def refectorio(self):
        y = F1
        x1, x2, z1, z2 = 35, 53, 30, 47
        self.huella.append((x1, z1, x2, z2))
        self.box(x1, y, z1, x2, y, z2, SB)
        self.box(x1 + 1, y, z1 + 1, 46, y, z2 - 1, PL)
        self.walls(x1, z1, x2, z2, y + 1, y + 6, SB, corner=TR)
        self.box(47, y + 1, z1 + 1, 47, y + 6, z2 - 1, SB)
        self.gable_z(x1, x2, z1, z2, y + 7)
        self.box(x1 + 1, y + 7, z1, x2 - 1, y + 7, z1, SB)
        self.box(x1 + 1, y + 7, z2, x2 - 1, y + 7, z2, SB)
        for z in (34, 38, 42):
            self.box(x1 + 1, y + 7, z, x2 - 1, y + 7, z, "stripped_spruce_log[axis=x]")
            for x in (39, 43, 50):
                self.hang(x, y + 6, z)
        self.door(x1, y + 1, 38, "east", hinge="left")
        self.door(x1, y + 1, 39, "east", hinge="right")
        self.set(x1 - 1, y + 3, 37, "lantern[hanging=false,waterlogged=false]")
        self.set(x1 - 1, y + 2, 37, SBW)
        self.set(x1 - 1, y + 1, 37, SBW)
        self.door(47, y + 1, 38, "east")
        self.panes([(x1, z) for z in (32, 35, 42, 45)], y + 2, y + 4)
        self.panes([(x2, z) for z in (33, 37, 41, 45)], y + 2, y + 4)
        self.panes([(x, z1) for x in (38, 41, 44, 50)] + [(x, z2) for x in (38, 41, 44, 50)], y + 2, y + 4)
        # mesa larga con bancos (respaldo hacia fuera) y mesa del abad
        for z in range(33, 44):
            self.set(41, y + 1, z, f"{PLSL}[type=top,waterlogged=false]")
            self.set(40, y + 1, z, stair(PLS, "west"))
            self.set(42, y + 1, z, stair(PLS, "east"))
        for x in range(38, 45):
            self.set(x, y + 1, 45, f"{PLSL}[type=top,waterlogged=false]")
            self.set(x, y + 1, 46, stair(PLS, "south"))
        for x in (39, 43):
            self.candle(x, y + 2, 45, 3)
        self.set(36, y + 3, 40, "white_wall_banner[facing=east]")
        self.set(46, y + 3, 40, "white_wall_banner[facing=west]")
        # cocina
        k = [("smoker[facing=west,lit=false]", 32), ("furnace[facing=west,lit=false]", 33), ("water_cauldron[level=3]", 35),
             ("crafting_table", 36), ("smoker[facing=west,lit=false]", 31)]
        for st, z in k:
            self.set(52, y + 1, z, st)
        self.chest(52, y + 1, 37, "west", "menor", "barrel")
        for z in range(31, 34):
            self.set(48, y + 1, z, "barrel[facing=up,open=false]")
        self.set(48, y + 1, 36, f"{PLSL}[type=top,waterlogged=false]")
        self.candle(48, y + 2, 36, 2)
        # escalera a la bodega (baja hacia -z) con barandilla
        for k in range(1, 7):
            z, ys = 46 - k, y - k
            for x in (50, 51):
                self.box(x, F0 + 1, z, x, ys - 1, z, SB)
                self.set(x, ys, z, stair(SBS, "south"))
                self.box(x, ys + 1, z, x, min(ys + 3, y - 1 if k > 2 else ys + 3), z, "air")
        for z in (44, 45):
            for x in (50, 51):
                self.set(x, y, z, "air")
            self.set(49, y + 1, z, "spruce_fence")
            self.set(52, y + 1, z, "spruce_fence")
        self.set(50, y + 1, 43, "spruce_fence")
        self.set(51, y + 1, 43, "spruce_fence")

    def bodega(self):
        yb = F0
        x1, x2, z1, z2 = 35, 53, 30, 47
        self.box(x1 + 1, yb + 1, z1 + 1, x2 - 1, F1 - 1, z2 - 1, "air")
        self.box(x1 + 1, yb, z1 + 1, x2 - 1, yb, z2 - 1, "cobblestone")
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                if x in (x1, x2) or z in (z1, z2):
                    self.box(x, yb, z, x, F1 - 1, z, SB)
        for x in (40, 44):
            for z in (35, 42):
                self.box(x, yb + 1, z, x, F1 - 1, z, TR)
        for z in range(32, 46):                                       # cubas tumbadas en dos alturas
            if z in (38, 39):
                continue
            self.set(36, yb + 1, z, "barrel[facing=east,open=false]")
            self.set(36, yb + 2, z, "barrel[facing=east,open=false]")
        for x in range(38, 49):
            if x in (40, 44):
                continue
            self.set(x, yb + 1, 46, "barrel[facing=south,open=false]")
        self.chest(36, yb + 1, 38, "east", "bodega", "barrel")
        self.chest(36, yb + 1, 39, "east", "bodega", "barrel")
        for x, z in ((38, 33), (46, 38), (42, 44), (49, 33)):
            self.hang(x, F1 - 1, z)
        # rincón de la despensa secreta: trampilla tras dos pilas de cubas
        self.box(46, yb + 1, 31, 46, yb + 2, 33, "barrel[facing=up,open=false]")
        self.box(43, yb + 1, 33, 45, yb + 1, 33, "barrel[facing=up,open=false]")
        self.set(44, yb + 1, 31, "spruce_trapdoor[facing=south,half=bottom,open=false,powered=false,waterlogged=false]")
        self.abiertos[(44, yb + 1, 31)] = "minecraft:spruce_trapdoor[facing=south,half=bottom,open=true,powered=false,waterlogged=false]"
        self.box(44, 19, 31, 44, yb, 31, "ladder[facing=east,waterlogged=false]")
        # despensa del cillerero (sala oculta)
        dx1, dx2, dz1, dz2, fy = 43, 50, 30, 35, 18
        self.box(dx1, fy, dz1, dx2, fy + 5, dz2, SB)
        self.box(dx1 + 1, fy + 1, dz1 + 1, dx2 - 1, fy + 4, dz2 - 1, "air")
        self.box(dx1 + 1, fy, dz1 + 1, dx2 - 1, fy, dz2 - 1, PL)
        self.box(44, fy + 1, 31, 44, fy + 5, 31, "ladder[facing=east,waterlogged=false]")
        self.set(43, fy + 1, 31, SB)
        self.chest(49, fy + 1, 34, "west", "oculto")
        self.set(49, fy + 1, 31, "hay_block[axis=y]")
        self.set(48, fy + 1, 34, "barrel[facing=up,open=false]")
        self.candle(48, fy + 2, 34, 2)
        self.set(46, fy + 4, 33, "lantern[hanging=true,waterlogged=false]")

    # ------------------------------------------------------------ T2: claustro, dormitorio, biblioteca, capítulo
    def t2(self):
        y = F2
        for z in range(72, 88):
            self.set(2, y + 1, z, SBW)
            self.set(56, y + 1, z, SBW)
        for x in range(2, 57):
            self.set(x, y + 1, 87, SBW)
        for x in (19, 37):
            self.set(x, y + 1, 87, "air")
        for x in range(2, 57):
            self.set(x, y, 72, SB if h3(x, y, 72) % 5 else "cobblestone")
        self.claustro()
        self.ala_oeste()
        self.dormitorio()
        self.iglesia()
        self.campanario()

    def claustro(self):
        y = F2
        x1, x2, z1, z2 = 14, 44, 50, 71
        self.huella.append((x1, z1, x2, z2))
        self.box(x1, y, z1, x2, y, z2, SB)
        self.walls(x1, z1, x2, z2, y + 1, y + 7, SB, corner=TR)
        for x in range(x1, x2 + 1):
            for z in (z1, z2):
                self.set(x, y + 8, z, SBW)
        for z in range(z1, z2 + 1):
            for x in (x1, x2):
                self.set(x, y + 8, z, SBW)
        ax1, ax2, az1, az2 = 18, 40, 54, 67           # línea de la arquería
        for x in range(x1 + 1, x2):
            for z in range(z1 + 1, z2):
                inner = ax1 < x < ax2 and az1 < z < az2
                if inner:
                    self.set(x, y, z, "grass_block[snowy=false]")
                    continue
                self.set(x, y + 6, z, PL)
                self.set(x, y + 7, z, f"{RSL}[type=bottom,waterlogged=false]")
        # arquería: columnas, arcos, pretil y dintel
        def arcade_line(cells, along_x, gap):
            for i, (x, z) in enumerate(cells):
                self.set(x, y + 5, z, SB)
                corner = (x in (ax1, ax2)) and (z in (az1, az2))
                col = corner or i % 3 == 0
                if col:
                    self.box(x, y + 1, z, x, y + 4, z, SB if corner else SBW)
                    if not corner:
                        self.set(x, y + 4, z, "chiseled_stone_bricks")
                    continue
                if (x, z) in gap:
                    continue
                self.set(x, y + 1, z, SBW)
                prev = i % 3 == 1
                if along_x:
                    self.set(x, y + 4, z, stair(SBS, "west" if prev else "east", "top"))
                else:
                    self.set(x, y + 4, z, stair(SBS, "north" if prev else "south", "top"))
        arcade_line([(x, az1) for x in range(ax1, ax2 + 1)], True, {(29, az1), (28, az1)})
        arcade_line([(x, az2) for x in range(ax1, ax2 + 1)], True, {(29, az2), (28, az2)})
        arcade_line([(ax1, z) for z in range(az1, az2 + 1)], False, {(ax1, 61), (ax1, 62)})
        arcade_line([(ax2, z) for z in range(az1, az2 + 1)], False, {(ax2, 61), (ax2, 62)})
        for x in (28, 29):
            for z in (az1, az2):
                self.box(x, y + 1, z, x, y + 3, z, "air")
        for z in (61, 62):
            for x in (ax1, ax2):
                self.box(x, y + 1, z, x, y + 3, z, "air")
        for x, z in ((17, 56), (17, 62), (41, 56), (41, 62), (24, 53), (34, 53), (24, 68), (34, 68), (16, 52), (42, 52),
                     (42, 69)):
            self.hang(x, y + 5, z)
        # puertas: entrada sur (desde T1), iglesia (norte), dormitorio y biblioteca
        self.box(28, y + 1, z1, 30, y + 3, z1, "air")
        self.set(28, y + 3, z1, stair(SBS, "west", "top"))
        self.set(30, y + 3, z1, stair(SBS, "east", "top"))
        self.set(29, y + 4, z1, "chiseled_stone_bricks")
        self.door(29, y + 1, z2, "north")
        self.door(x2, y + 1, 52, "east")
        self.door(x1, y + 1, 57, "west")
        # jardín: caminos, pozo cubierto, flores y arbustos
        for z in range(az1 + 1, az2):
            self.set(29, y, z, "dirt_path")
        for x in range(ax1 + 1, ax2):
            self.set(x, y, 61, "dirt_path")
        self.box(28, y + 1, 60, 30, y + 1, 62, SB)
        self.set(29, y + 1, 61, "air")
        self.set(29, y, 61, "water[level=0]")
        self.set(29, y - 1, 61, "stone")
        for x in (28, 30):
            self.box(x, y + 2, 61, x, y + 3, 61, "spruce_fence")
        self.box(28, y + 4, 61, 30, y + 4, 61, f"{PLSL}[type=top,waterlogged=false]")
        self.set(29, y + 3, 61, "iron_chain[axis=y,waterlogged=false]")
        self.set(29, y + 2, 61, "lantern[hanging=true,waterlogged=false]")
        for x, z in ((21, 57), (37, 57), (21, 65), (37, 65)):
            self.set(x, y + 1, z, "azalea")
        self.flowers(ax1 + 1, az1 + 1, ax2 - 1, az2 - 1, y, 0.14)
        # esquina noroeste hundida: sin cubierta y con escombros (queda un paso libre)
        for x in range(x1 + 1, ax1 + 1):
            for z in range(64, z2):
                self.set(x, y + 6, z, "air")
                self.set(x, y + 7, z, "air")
        for z in range(65, z2):
            self.set(x1, y + 7, z, "air")
            self.set(x1, y + 8, z, "air")
            self.set(15, y + 1, z, self.rng.choice(["cobblestone", "mossy_cobblestone", "mossy_stone_bricks"]))
            if z % 2:
                self.set(16, y + 1, z, f"{SBSL}[type=bottom,waterlogged=false]")
        self.ruinas.append((x1, 64, ax1, z2))

    def ala_oeste(self):
        y = F2
        x1, x2, z1, z2 = 2, 14, 50, 71
        self.huella.append((x1, z1, x2, z2))
        self.box(x1, y, z1, x2, y, z2, PL)
        self.walls(x1, z1, x2, z2, y + 1, y + 8, SB, corner=TR)
        self.box(x1 + 1, y + 1, 62, x2 - 1, y + 8, 62, SB)
        self.door(x2, y + 1, 57, "west")                               # puerta desde el claustro
        self.box(x1 + 1, y + 7, z1 + 1, x2 - 1, y + 7, z2 - 1, PL)     # techo / suelo del desván
        self.gable_z(x1, x2, z1, z2, y + 9)
        self.box(x1 + 1, y + 9, z1, x2 - 1, y + 9, z1, SB)
        self.box(x1 + 1, y + 9, z2, x2 - 1, y + 9, z2, SB)
        for x in range(x1 + 1, x2):                                   # tabique del desván, bajo la cubierta
            self.box(x, y + 8, 62, x, y + 8 + min(x - x1, x2 - x), 62, SB)
        # biblioteca
        for z in range(52, 60):
            self.box(3, y + 1, z, 3, y + 3, z, "bookshelf")
        self.set(3, y + 3, 60, "bookshelf")
        for x in range(4, 13):
            self.box(x, y + 1, 51, x, y + 3, 51, "bookshelf")
            self.box(x, y + 1, 61, x, y + 3, 61, "bookshelf")
        for z in range(52, 61):
            if z not in (56, 57, 58):
                self.box(13, y + 1, z, 13, y + 3, z, "bookshelf")
        self.panes([(x1, z) for z in (53, 56, 59)], y + 4, y + 5)
        self.panes([(x2, z) for z in (54, 60)], y + 4, y + 5)
        for x in range(6, 11):
            self.set(x, y + 1, 56, f"{PLSL}[type=top,waterlogged=false]")
            self.set(x, y + 1, 55, stair(PLS, "north"))
            self.set(x, y + 1, 57, stair(PLS, "south"))
        self.candle(7, y + 2, 56, 3)
        self.candle(9, y + 2, 56, 2)
        self.set(8, y + 1, 60, "lectern[facing=north,has_book=false,powered=false]")
        self.chest(12, y + 1, 52, "south", "biblioteca")
        for x, z in ((6, 54), (10, 54), (6, 59), (10, 59)):
            self.hang(x, y + 6, z)
        # hueco tras la estantería del rincón: escala oculta al escritorio del desván
        self.box(3, y + 1, 61, 3, y + 7, 61, "ladder[facing=east,waterlogged=false]")
        self.box(5, y + 1, 60, 5, y + 3, 60, "bookshelf")              # pantalla que tapa el rincón
        # escritorio oculto bajo cubierta (z 51..61)
        for x in range(5, 12):
            self.set(x, y + 8, 52, PL if x in (5, 11) else f"{PLSL}[type=top,waterlogged=false]")
        self.set(8, y + 8, 53, stair(PLS, "south"))
        self.candle(6, y + 9, 52, 2)
        self.candle(10, y + 9, 52, 1)
        self.chest(11, y + 8, 58, "west", "oculto")
        self.set(5, y + 8, 58, "barrel[facing=up,open=false]")
        self.set(10, y + 8, 60, "cartography_table")
        self.set(8, y + 12, 56, "lantern[hanging=true,waterlogged=false]")
        # sala capitular
        self.box(x2, y + 1, 64, x2, y + 3, 65, "air")
        self.set(x2, y + 3, 64, stair(SBS, "north", "top"))
        self.set(x2, y + 3, 65, stair(SBS, "south", "top"))
        self.panes([(x2, 63), (x2, 67)], y + 2, y + 3)
        self.panes([(x1, z) for z in (64, 67, 70)], y + 3, y + 5)
        for z in range(64, 71):
            self.set(3, y + 1, z, stair(SBS, "west"))
        for x in range(4, 13):
            if x == 8:
                continue
            self.set(x, y + 1, 70, stair(SBS, "south"))
            self.set(x, y + 1, 63, stair(SBS, "north"))
        self.set(8, y + 1, 70, SB)
        self.set(8, y + 2, 70, stair(SBS, "south"))
        self.set(8, y + 4, 70, "white_wall_banner[facing=north]")
        self.hang(11, y + 6, 66)
        # media cubierta caída sobre la sala capitular
        for x in range(x1 - 1, 9):
            for z in range(66, z2 + 2):
                for yy in range(y + 7, y + 17):
                    if (x, yy, z) in self.blocks and (x > x1 or yy > y + 8):
                        self.set(x, yy, z, "air")
        for x in range(x1, 9):
            self.set(x, y + 8, z2, "air")
        for x, z in ((4, 68), (5, 69), (6, 67), (4, 66), (7, 69)):
            self.set(x, y + 1, z, self.rng.choice(["cobblestone", "mossy_cobblestone", f"{RSL}[type=bottom,waterlogged=false]"]))
        self.set(5, y + 1, 66, "stripped_spruce_log[axis=z]")
        self.ruinas.append((x1, 66, 8, z2))

    def dormitorio(self):
        y = F2
        x1, x2, z1, z2 = 44, 56, 50, 71
        self.huella.append((x1, z1, x2, z2))
        self.box(x1 + 1, y, z1, x2, y, z2, PL)
        self.walls(x1, z1, x2, z2, y + 1, y + 5, SB, corner=TR)
        self.door(x1, y + 1, 52, "east")                               # puerta desde el claustro
        self.box(x1 + 1, y + 5, z1 + 1, x2 - 1, y + 5, z2 - 1, PL)
        self.gable_z(x1, x2, z1, z2, y + 6)
        self.box(x1 + 1, y + 6, z1, x2 - 1, y + 6, z1, SB)
        self.box(x1 + 1, y + 6, z2, x2 - 1, y + 6, z2, SB)
        for x in (48, 52):
            self.box(x, y + 1, z1 + 1, x, y + 4, z2 - 1, SB)
        self.box(48, y + 1, 52, 48, y + 2, 52, "air")
        cells_w = [55, 59, 63, 67]
        cells_e = [51, 55, 59, 63, 67]
        for zc in cells_w:
            self.box(45, y + 1, zc - 1, 47, y + 4, zc - 1, SB)
        self.box(45, y + 1, 54, 47, y + 4, 54, SB)
        for zc in cells_e:
            if zc > 51:
                self.box(53, y + 1, zc - 1, 55, y + 4, zc - 1, SB)
        self.box(53, y + 1, 70, 55, y + 4, 70, SB)
        self.box(45, y + 1, 70, 47, y + 4, 70, SB)
        for i, zc in enumerate(cells_w):
            self.door(48, y + 1, zc + 1, "west")
            self.bed(46, zc, y + 1, "west")
            if zc == 59:
                continue
            self.set(45, y + 1, zc + 2, "barrel[facing=up,open=false]")
            self.candle(45, y + 2, zc + 2, 1, lit=(i % 2 == 0))
        for i, zc in enumerate(cells_e):
            self.door(52, y + 1, zc + 1, "east")
            self.bed(54, zc, y + 1, "east")
            self.panes([(x2, zc + 1)], y + 2, y + 3)
            if zc in (51, 63):
                continue
            self.set(55, y + 1, zc + 2, "barrel[facing=up,open=false]")
            self.candle(55, y + 2, zc + 2, 1, lit=(i % 2 == 1))
        # celda del prior (la primera del este): escritorio y cofre
        self.chest(55, y + 1, 53, "west", "oculto")
        self.chest(45, y + 1, 61, "east", "celda")
        self.chest(55, y + 1, 65, "west", "celda")
        for z in (53, 57, 61, 65, 69):
            self.hang(50, y + 4, z)
        self.door(50, y + 1, z2, "north")
        self.box(49, y + 1, 51, 51, y + 4, 51, "air")
        self.box(45, y + 1, 51, 47, y + 4, 53, "air")
        # dos celdas del norte (este) sin techo: cubierta hundida
        for x in range(52, x2 + 2):
            for z in range(62, z2 + 2):
                for yy in range(y + 5, y + 14):
                    if (x, yy, z) in self.blocks and not (x == x2 and yy == y + 5) and not (z == z2 and yy <= y + 5):
                        if x >= 53 or yy > y + 5:
                            self.set(x, yy, z, "air")
        for x, z in ((53, 64), (55, 68), (54, 69)):
            self.set(x, y + 1, z, self.rng.choice(["cobblestone", f"{RSL}[type=bottom,waterlogged=false]"]))
        self.ruinas.append((52, 62, x2, z2))

    def iglesia(self):
        y = F2
        x1, x2, z1, z2 = 6, 48, 73, 85
        self.huella.append((x1, z1, x2, z2))
        for x in range(x1, x2 + 1):
            for z in range(z1, z2 + 1):
                self.set(x, y, z, TR if (x + z) % 2 else "polished_diorite")
        self.walls(x1, z1, x2, z2, y + 1, y + 11, SB, corner=TR)
        for x in range(x1, x2 + 1, 6):                               # contrafuertes laterales
            for z, dz in ((z2, 1),):
                if (x, z + dz) in self.top:
                    self.box(x, y + 1, z + dz, x, y + 8, z + dz, SB)
                    self.set(x, y + 9, z + dz, stair(SBS, "south" if dz < 0 else "north"))
        self.gable_x(x1, x2, z1, z2, y + 12, ox=(1, 0))
        for x in range(12, 45, 8):
            self.box(x, y + 11, z1 + 1, x, y + 11, z2 - 1, "dark_oak_log[axis=z]")
            self.hang(x, y + 9, 79)
        # columnas y arquerías longitudinales
        for zc in (76, 82):
            for x in range(10, 39):
                self.set(x, y + 10, zc, SB)
            for x in range(10, 39, 4):
                self.box(x, y + 1, zc, x, y + 9, zc, SB)
                self.set(x, y + 1, zc, "chiseled_stone_bricks")
                self.set(x, y + 9, zc, "chiseled_stone_bricks")
                if x + 1 < 39:
                    self.set(x + 1, y + 9, zc, stair(SBS, "west", "top"))
                if x - 1 >= 10:
                    self.set(x - 1, y + 9, zc, stair(SBS, "east", "top"))
            self.box(x1 + 1, y + 10, zc, 9, y + 10, zc, SB)
            self.box(39, y + 10, zc, x2 - 1, y + 10, zc, SB)
        # bancos de la nave (miran al altar, respaldo al oeste)
        for x in range(12, 35, 2):
            for z in (77, 78, 80, 81):
                self.set(x, y + 1, z, stair(PLS, "west"))
        for x in range(36, 40):
            self.set(x, y + 1, 77, stair(PLS, "north"))
            self.set(x, y + 1, 81, stair(PLS, "south"))
        # presbiterio elevado, altar y vidriera
        for z in range(z1 + 1, z2):
            self.set(40, y + 1, z, stair(SBS, "east"))
            for x in range(41, x2):
                self.set(x, y + 1, z, "polished_andesite")
        for z in (78, 79, 80):
            self.set(45, y + 2, z, "chiseled_stone_bricks" if z != 79 else "polished_diorite")
        self.candle(45, y + 3, 78, 4)
        self.candle(45, y + 3, 80, 4)
        self.set(45, y + 3, 79, "white_carpet")
        self.panes([(x2, z) for z in (78, 79, 80)], y + 4, y + 9, "yellow_stained_glass_pane")
        self.panes([(x2, 79)], y + 6, y + 7, "red_stained_glass_pane")
        for x in (43, 47):
            self.set(x, y + 2, 75, "lantern[hanging=false,waterlogged=false]")
            self.set(x, y + 2, 83, "lantern[hanging=false,waterlogged=false]")
        # ventanas altas
        for x in (10, 14, 18, 22, 34, 38):
            for z in (z1, z2):
                self.panes([(x, z)], y + 3, y + 7, "white_stained_glass_pane")
                self.set(x, y + 8, z, "white_stained_glass_pane")
        # portada oeste y rosetón
        self.box(x1, y + 1, 78, x1, y + 4, 80, "air")
        self.set(x1, y + 4, 78, stair(SBS, "north", "top"))
        self.set(x1, y + 4, 80, stair(SBS, "south", "top"))
        self.set(x1, y + 5, 79, "chiseled_stone_bricks")
        for dz in range(-3, 4):
            for dy in range(-3, 4):
                r2 = dz * dz + dy * dy
                if r2 <= 10:
                    c = "red_stained_glass_pane" if r2 <= 1 else "blue_stained_glass_pane" if r2 <= 5 else "yellow_stained_glass_pane"
                    self.set(x1, y + 12 + dy, 79 + dz, c)
        for z in range(76, 83):                                     # escalones de la explanada oeste
            self.set(x1 - 1, y, z, SB)
        # puerta sur (desde el claustro)
        self.door(29, y + 1, z1, "north")
        self.set(29, y + 3, z1, "chiseled_stone_bricks")
        # escalera a la cripta (nave norte, baja hacia +x)
        for k in range(1, 8):
            x, ys = 32 + k, y - k
            for z in (83, 84):
                self.set(x, ys, z, stair(SBS, "west"))
                self.box(x, ys + 1, z, x, min(ys + 3, y - 1) if k > 2 else ys + 2, z, "air")
        for z in (83, 84):
            for x in (33, 34):
                self.set(x, y, z, "air")
        self.set(33, y + 1, 82, "spruce_fence")
        self.set(35, y + 1, 83, "spruce_fence")
        self.set(35, y + 1, 84, "spruce_fence")
        self.cripta()

    def cripta(self):
        yb = 29
        x1, x2, z1, z2 = 39, 48, 73, 85
        self.box(x1, yb, z1, x2, yb + 6, z2, DS)
        self.box(x1 + 1, yb + 1, z1 + 1, x2 - 1, yb + 6, z2 - 1, "air")
        self.box(x1 + 1, yb, z1 + 1, x2 - 1, yb, z2 - 1, "polished_deepslate")
        self.box(x1, yb + 1, 83, x1, yb + 3, 84, "air")
        self.set(x1, yb, 83, "polished_deepslate")
        self.set(x1, yb, 84, "polished_deepslate")
        for x in (42, 45):
            for z in (77, 81):
                self.box(x, yb + 1, z, x, yb + 6, z, "polished_deepslate")
        for zc in (79,):
            for x0 in (41, 44):
                self.box(x0, yb + 1, zc, x0 + 1, yb + 1, zc, "polished_deepslate")
                self.box(x0, yb + 2, zc, x0 + 1, yb + 2, zc, f"{RSL}[type=bottom,waterlogged=false]")
        for x0 in (42, 45):
            self.box(x0, yb + 1, 84, x0 + 1, yb + 1, 84, "polished_deepslate")
            self.box(x0, yb + 2, 84, x0 + 1, yb + 2, 84, f"{RSL}[type=bottom,waterlogged=false]")
        self.spawner(46, yb + 1, 82, "zombie")
        self.cobweb(47, yb + 1, 84)
        self.cobweb(40, yb + 5, 76)
        self.set(47, yb + 1, 74, "skeleton_skull[rotation=4]")
        self.candle(41, yb + 3, 79, 2, lit=False)
        self.puzle_cripta()

    def puzle_cripta(self):
        """Puzle 1: dos palancas encendidas (O) mantienen extendidos dos pistones pegajosos que sostienen la lápida."""
        y = 30
        xd, zc, zm, zp = 41, 73, 72, 71
        for x in range(39, 49):
            for yy in range(29, 34):
                self.set(x, yy, zm, DS)
                self.set(x, yy, zp, DS)
        self.box(xd, y, zc, xd, y + 1, zc, "air")                      # nicho
        self.box(xd, y, zm, xd, y + 1, zm, "chiseled_deepslate")       # lápida
        self.box(xd, y, zp, xd, y + 1, zp, "air")
        for yy in (y, y + 1):
            self.set(xd + 1, yy, zm, "piston_head[facing=west,short=false,type=sticky]")
            self.set(xd + 2, yy, zm, "sticky_piston[extended=true,facing=west]")
        levers = (45, 47)
        dust = {}
        for x in range(44, 48):
            dust[x] = max(15 - abs(x - lx) for lx in levers)
            self.set(x, y + 1, zm, f"redstone_wire[east=side,north=none,power={dust[x]},south=none,west=side]")
        for lx in levers:
            self.set(lx, y + 1, zc + 1, "lever[face=wall,facing=south,powered=true]")
            self.set(lx, y + 2, zc, "redstone_lamp[lit=true]")
        self.sign(43, y + 2, zc + 1, "south", "cripta", ["Apagad las luces", "de los difuntos", "y la lápida", "se apartará."])
        for yy in (y, y + 1):
            self.abiertos[(xd, yy, zm)] = "minecraft:air"
            self.abiertos[(xd + 1, yy, zm)] = "minecraft:chiseled_deepslate"
            self.abiertos[(xd + 2, yy, zm)] = "minecraft:sticky_piston[extended=false,facing=west]"
        self.circuitos["cripta"] = dict(levers=[(lx, y + 1, zc + 1) for lx in levers], solucion=(False, False),
                                        salida=[(xd + 2, y, zm), (xd + 2, y + 1, zm)], abre_si="sin_potencia")
        # pasadizo secreto: 16 peldaños hasta la gruta
        for k in range(1, 17):
            z, ys = zp - k, 29 - k
            self.set(xd, ys, z, stair("cobblestone_stairs", "south"))
            self.box(xd, ys + 1, z, xd, ys + 3, z, "air")
        self.set(xd, 29, zp, "cobblestone")

    def campanario(self):
        y = F2
        x1, x2, z1, z2 = 48, 54, 73, 79
        self.huella.append((x1 + 1, z1, x2, z2))
        top = 64
        self.box(x1 + 1, y, z1, x2, y + 1, z2, SB)
        self.walls(x1, z1, x2, z2, y + 1, top, SB, corner=TR)
        self.box(x1 + 1, y + 1, z1 + 1, x2 - 1, top, z2 - 1, "air")
        self.box(x1 + 1, y + 1, z1 + 1, x2 - 1, y + 1, z2 - 1, SB)
        self.door(x1, y + 2, 76, "east")
        # sacristía
        self.set(53, y + 2, 74, "brewing_stand[has_bottle_0=false,has_bottle_1=false,has_bottle_2=false]")
        self.set(49, y + 2, 74, SB)
        self.chest(49, y + 2, 78, "east", "oculto")
        self.set(50, y + 2, 78, "barrel[facing=up,open=false]")
        self.candle(50, y + 3, 78, 3)
        self.hang(51, y + 6, 75)
        # pisos y escala
        for fy in (y + 7, y + 14, y + 22):
            self.box(x1 + 1, fy, z1 + 1, x2 - 1, fy, z2 - 1, PL)
        self.box(53, y + 2, 77, 53, y + 22, 77, "ladder[facing=west,waterlogged=false]")
        self.chest(49, y + 15, 74, "east", "menor")
        self.hang(51, y + 21, 76)
        self.panes([(51, z1), (51, z2)], y + 10, y + 11)
        self.panes([(x2, 76)], y + 17, y + 18)
        # campanas: arcos y barandilla
        by = y + 23
        for side in ("n", "s", "w", "e"):
            for i in (-1, 0, 1):
                if side in ("n", "s"):
                    x, z = 51 + i, z1 if side == "n" else z2
                else:
                    x, z = x1 if side == "w" else x2, 76 + i
                self.box(x, by + 1, z, x, by + 3, z, "air")
                self.set(x, by, z, SBW)
                if i:
                    self.set(x, by + 3, z, stair(SBS, ("west" if i < 0 else "east") if side in ("n", "s") else ("north" if i < 0 else "south"), "top"))
        self.box(x1 + 1, by + 5, 76, x2 - 1, by + 5, 76, "dark_oak_log[axis=x]")
        self.set(51, by + 4, 76, "bell[attachment=ceiling,facing=north,powered=false]")
        # cubierta piramidal
        for i in range(0, 5):
            self.box(x1 - 1 + i, top + 1 + i, z1 - 1 + i, x2 + 1 - i, top + 1 + i, z2 + 1 - i, RF)
        self.set(51, top + 6, 76, "lightning_rod[facing=up,powered=false,waterlogged=false]")
        # esquina rota (ruina)
        for yy in range(top - 2, top + 2):
            self.set(x2, yy, z2, "air")
        for x, z in ((x2 + 1, z2 + 1), (x2, z2 + 1), (x2 + 1, z2), (x2, z2)):
            self.set(x, top + 1, z, "air")
        self.ruinas.append((x2 - 1, z2 - 1, x2, z2))

    # ------------------------------------------------------------ cuevas
    def cobweb(self, x, y, z):
        for k in range(6):
            above = self.get(x, y + k + 1, z)
            if above and above != "minecraft:air":
                self.set(x, y + k, z, "cobweb")
                return

    def carve(self, x1, y1, z1, x2, y2, z2):
        self.box(x1, y1, z1, x2, y2, z2, "air")

    def cuevas(self):
        y = CAVE
        # rellano y pasillo desde el pasadizo
        self.carve(40, y + 1, 50, 42, y + 4, 55)
        self.carve(34, y + 1, 49, 41, y + 3, 51)
        # gruta de los eremitas
        cx, cz, rx, rz = 29, 42, 13, 10
        for x in range(cx - rx, cx + rx + 1):
            for z in range(cz - rz, cz + rz + 1):
                r = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2
                if r <= 1.0:
                    hc = 3 + int(4 * (1 - r)) + h3(x, 0, z, 5) % 2
                    self.carve(x, y + 1, z, x, y + hc, z)
                    self.set(x, y, z, "moss_block" if h3(x, y, z) % 7 == 0 else rock(x, y, z) if h3(x, y, z) % 3 else "stone")
        for x, z in ((22, 38), (36, 46), (25, 48)):                      # columnas naturales
            self.box(x, y + 1, z, x, y + 8, z, "stone")
            self.set(x, y + 9, z, "stone")
        for x, z in ((20, 44), (33, 37), (31, 49)):
            self.set(x, y + 1, z, "cobblestone")
        # altar de los eremitas en el centro de la gruta
        self.box(28, y + 1, 41, 30, y + 1, 41, "stone_bricks")
        self.set(29, y + 2, 41, "chiseled_stone_bricks")
        self.candle(28, y + 2, 41, 3)
        self.candle(30, y + 2, 41, 2)
        self.set(29, y + 1, 43, "water_cauldron[level=3]")
        # ermitas
        self.ermita(9, 14, 39, 44, "east", (15, 17, 41, 42))
        self.ermita(24, 29, 23, 28, "south", (26, 27, 29, 33))
        self.ermita(33, 38, 23, 28, "south", (34, 36, 29, 34))
        self.trampa_cable(35, 31)
        self.aranas()
        self.archivo()
        self.osario()
        self.catacumbas()

    def ermita(self, x1, x2, z1, z2, door, passage):
        y = CAVE
        self.box(x1 - 1, y, z1 - 1, x2 + 1, y + 5, z2 + 1, "cobblestone")
        for x in range(x1 - 1, x2 + 2):
            for z in range(z1 - 1, z2 + 2):
                for yy in range(y, y + 6):
                    if h3(x, yy, z, 2) % 3 == 0:
                        self.set(x, yy, z, "mossy_cobblestone")
        self.carve(x1, y + 1, z1, x2, y + 4, z2)
        self.box(x1, y, z1, x2, y, z2, "stone_bricks")
        px1, px2, pz1, pz2 = passage
        self.carve(px1, y + 1, pz1, px2, y + 3, pz2)
        self.box(px1, y, pz1, px2, y, pz2, "stone_bricks")
        # altar contra el fondo, lecho de paja, cofre y cruz
        if door == "east":
            ax, az, chest, bed = x1, (z1 + z2) // 2, (x1, y + 1, z2), (x2 - 1, z1)
            self.set(ax, y + 1, az, "chiseled_stone_bricks")
            self.candle(ax, y + 2, az, 3, lit=False)
            self.box(ax, y + 2, az + 1, ax, y + 4, az + 1, TR)
            self.set(ax, y + 3, az, TR)
            self.set(ax, y + 3, az + 2, TR)
            self.chest(*chest, "east", "ermita")
            self.set(x2, y + 1, z1, "hay_block[axis=y]")
            self.set(x2, y + 2, z1, "white_carpet")
        else:
            ax, az = (x1 + x2) // 2, z1
            self.set(ax, y + 1, az, "chiseled_stone_bricks")
            self.candle(ax, y + 2, az, 3, lit=False)
            self.box(ax + 1, y + 2, az, ax + 1, y + 4, az, TR)
            self.set(ax, y + 3, az, TR)
            self.set(ax + 2, y + 3, az, TR)
            self.chest(x2, y + 1, z1, "west", "ermita")
            self.set(x1, y + 1, z2 - 1, "hay_block[axis=y]")
            self.set(x1, y + 2, z2 - 1, "white_carpet")
        self.cobweb(x1, y + 4, z1)

    def trampa_cable(self, xc, z):
        """Trampa 1 (como el templo de la jungla): cable trampa entre dos ganchos; cada gancho activa el dispensador de encima."""
        y = CAVE + 1
        self.set(xc - 1, y, z, "tripwire_hook[attached=true,facing=east,powered=false]")
        self.set(xc + 1, y, z, "tripwire_hook[attached=true,facing=west,powered=false]")
        self.set(xc, y, z, "tripwire[attached=true,disarmed=false,east=true,north=false,powered=false,south=false,west=true]")
        for x, f in ((xc - 2, "east"), (xc + 2, "west")):
            self.set(x, y, z, "stone_bricks")
            self.set(x, y + 1, z, f"dispenser[facing={f},triggered=false]",
                     {"id": "minecraft:dispenser", "Items": [{"Slot": B(0), "id": "minecraft:arrow", "count": 8},
                                                            {"Slot": B(4), "id": "minecraft:arrow", "count": 8}]})
        self.circuitos["cable"] = dict(ganchos=[(xc - 1, y, z), (xc + 1, y, z)], dispensadores=[(xc - 2, y + 1, z), (xc + 2, y + 1, z)])

    def aranas(self):
        y = CAVE
        cx, cz = 18, 56
        for x in range(cx - 4, cx + 5):
            for z in range(cz - 4, cz + 5):
                if (x - cx) ** 2 + (z - cz) ** 2 <= 17:
                    self.carve(x, y + 1, z, x, y + 3 + h3(x, 0, z) % 2, z)
                    self.set(x, y, z, rock(x, y, z))
        self.carve(19, y + 1, 50, 22, y + 3, 52)
        self.carve(19, y + 1, 52, 20, y + 3, 53)
        self.spawner(17, y + 1, 57, "cave_spider")
        self.chest(14, y + 1, 56, "east", "menor")
        for x, z, yy in ((15, 54, 2), (20, 58, 1), (16, 59, 2), (21, 55, 3), (18, 53, 3), (14, 57, 2), (19, 56, 1)):
            self.cobweb(x, y + yy, z)
        self.set(16, y + 1, 54, "skeleton_skull[rotation=2]")

    def osario(self):
        y = CAVE
        x1, x2, z1, z2 = 42, 54, 37, 47
        self.box(x1, y, z1, x2, y + 6, z2, "bone_block[axis=y]")
        self.carve(x1 + 1, y + 1, z1 + 1, x2 - 1, y + 5, z2 - 1)
        self.box(x1 + 1, y, z1 + 1, x2 - 1, y, z2 - 1, "stone_bricks")
        self.carve(41, y + 1, 41, x1, y + 3, 43)
        self.box(41, y, 41, x1, y, 43, "stone_bricks")
        for x in range(x1 + 2, x2 - 1, 2):                              # nichos con calaveras en el muro norte
            self.set(x, y + 2, z1, "air")
            self.set(x, y + 2, z1 - 1, "bone_block[axis=y]")
        for x in range(x1 + 2, x2 - 1, 4):
            self.set(x, y + 1, z1 + 1, "skeleton_skull[rotation=8]")
        for z in range(z1 + 2, z2 - 1, 3):
            self.set(x2 - 1, y + 1, z, "skeleton_skull[rotation=4]")
        self.spawner(48, y + 1, 41, "skeleton")
        for x, z, yy in ((44, 39, 4), (52, 44, 4), (50, 38, 1), (47, 45, 3)):
            self.cobweb(x, y + yy, z)
        self.puzle_osario()

    def puzle_osario(self):
        """Puzle 2: abre la puerta del archivo solo con las palancas 1 y 3 subidas y la 2 bajada.
        Palancas 1 y 3 -> antorchas inversoras; palanca 2 -> polvo; las tres salidas se suman en la línea z=49,
        que alimenta el bloque de la antorcha final; esa antorcha abre la puerta de hierro."""
        y = CAVE + 1
        zl, zw, zt, zs, zb = 46, 47, 48, 49, 50
        a = 43
        for x in range(a - 1, a + 12):
            for yy in range(CAVE, CAVE + 4):
                self.set(x, yy, zw, "stone_bricks" if yy > CAVE else "stone")
                self.set(x, yy, zt, "stone")
                self.set(x, yy, zs, "stone")
                self.set(x, yy, zb, "stone_bricks")
        levers = [a, a + 2, a + 4]
        for x in levers:
            self.set(x, y, zl, "lever[face=wall,facing=north,powered=false]")
        self.set(a, y, zt, "redstone_wall_torch[facing=south,lit=true]")
        self.set(a + 4, y, zt, "redstone_wall_torch[facing=south,lit=true]")
        self.set(a + 2, y, zt, "redstone_wire[east=none,north=side,power=0,south=side,west=none]")
        for x in range(a, a + 8):
            ns = "side" if x == a + 2 else "none"
            self.set(x, y, zs, f"redstone_wire[east=side,north={ns},power=0,south=none,west=side]")
        bf = a + 8
        self.set(bf, y, zs, "stone")
        self.set(bf + 1, y, zs, "redstone_wall_torch[facing=east,lit=false]")
        xd = bf + 2
        for z in (zw, zt, zb):
            self.set(xd, y, z, "air")
            self.set(xd, y + 1, z, "air")
        self.set(xd, y, zs, "iron_door[facing=north,half=lower,hinge=left,open=false,powered=false]")
        self.set(xd, y + 1, zs, "iron_door[facing=north,half=upper,hinge=left,open=false,powered=false]")
        self.sign(a + 2, y + 2, zl, "north", "osario", ["Velan el primero", "y el último;", "el del medio", "duerme."])
        self.circuitos["osario"] = dict(levers=[(x, y, zl) for x in levers], solucion=(True, False, True),
                                        salida=[(xd, y, zs)], abre_si="con_potencia")

    def archivo(self):
        y = CAVE
        x1, x2, z1, z2 = 43, 54, 50, 58
        self.box(x1, y, z1, x2, y + 6, z2, "stone_bricks")
        self.carve(x1 + 1, y + 1, z1 + 1, x2 - 1, y + 5, z2 - 1)
        self.box(x1 + 1, y, z1 + 1, x2 - 1, y, z2 - 1, "dark_oak_planks")
        for z in range(z1 + 1, z2):
            self.box(x1 + 1, y + 1, z, x1 + 1, y + 3, z, "bookshelf")
            if z not in (z1 + 1,):
                self.box(x2 - 1, y + 1, z, x2 - 1, y + 3, z, "bookshelf")
        self.chest(x1 + 2, y + 1, z2 - 1, "north", "archivo")
        self.chest(x2 - 2, y + 1, z2 - 1, "north", "archivo")
        self.set(48, y + 1, 53, f"dark_oak_slab[type=top,waterlogged=false]")
        self.set(49, y + 1, 53, f"dark_oak_slab[type=top,waterlogged=false]")
        self.set(48, y + 1, 52, stair("dark_oak_stairs", "north"))
        self.set(49, y + 1, 54, stair("dark_oak_stairs", "south"))
        self.candle(48, y + 2, 53, 3)
        self.set(46, y + 1, z1 + 1, "cartography_table")
        self.set(50, y + 1, z1 + 1, "lectern[facing=south,has_book=false,powered=false]")
        self.set(48, y + 4, 51, "lantern[hanging=true,waterlogged=false]")
        self.set(48, y + 5, 51, "iron_chain[axis=y,waterlogged=false]")
        # escalera a las catacumbas (baja hacia +z)
        for k in range(1, 9):
            z, ys = z2 - 1 + k, y - k
            for x in (48, 49):
                self.set(x, ys, z, stair("stone_brick_stairs", "north"))
                self.carve(x, ys + 1, z, x, ys + 3 if k > 1 else ys + 4, z)
        self.carve(48, y + 1, z2, 49, y + 3, z2)

    def catacumbas(self):
        y = DEEP
        self.box(45, y, 66, 52, y + 5, 75, "stone_bricks")
        self.carve(47, y + 1, 66, 50, y + 4, 74)
        self.box(47, y, 66, 50, y, 74, "cobblestone")
        for z in range(67, 75, 2):                                     # nichos (lóculos)
            for x in (46, 51):
                self.set(x, y + 2, z, "bone_block[axis=y]" if z % 4 == 1 else "air")
                if z % 4 == 3:
                    self.set(x, y + 2, z, "skeleton_skull[rotation=4]" if x == 46 else "skeleton_skull[rotation=12]")
        self.set(46, y + 1, 72, "air")
        self.chest(46, y + 1, 71, "east", "catacumba")
        self.spawner(50, y + 1, 70, "zombie")
        for x, z, yy in ((47, 68, 4), (50, 73, 4), (48, 72, 1)):
            self.cobweb(x, y + yy, z)
        # antecámara con la trampa 2: losas de presión sobre dispensadores que disparan hacia arriba
        self.box(45, y, 75, 52, y + 6, 79, "polished_blackstone_bricks")
        self.carve(47, y + 1, 75, 50, y + 5, 78)
        self.box(47, y, 75, 50, y, 78, "polished_blackstone")
        for x in range(47, 51):
            for z in (76, 77):
                items = [{"Slot": B(0), "id": "minecraft:arrow", "count": 3}] if (x + z) % 2 else \
                    [{"Slot": B(0), "id": "minecraft:splash_potion", "count": 1,
                      "components": {"minecraft:potion_contents": {"potion": "minecraft:poison"}}}]
                self.set(x, y, z, "dispenser[facing=up,triggered=false]", {"id": "minecraft:dispenser", "Items": items})
                self.set(x, y + 1, z, "stone_pressure_plate[powered=false]")
        self.circuitos["losas"] = dict(losas=[(x, y + 1, z) for x in range(47, 51) for z in (76, 77)])
        # relicario
        x1, x2, z1, z2 = 42, 55, 79, 88
        self.box(x1, y, z1, x2, y + 8, z2, "polished_blackstone_bricks")
        self.carve(x1 + 1, y + 1, z1, x2 - 1, y + 7, z2 - 1)
        self.box(x1 + 1, y, z1, x2 - 1, y, z2 - 1, "polished_blackstone")
        for x in range(x1 + 1, x2):
            if not 47 <= x <= 50:
                self.box(x, y + 1, z1, x, y + 7, z1, "polished_blackstone_bricks")
        for x in (45, 52):
            for z in (81, 84):
                self.box(x, y + 1, z, x, y + 7, z, "chiseled_polished_blackstone")
        for x in range(x1 + 1, x2):                                     # estrado del altar
            self.set(x, y + 1, 85, stair("polished_blackstone_brick_stairs", "south"))
            self.box(x, y + 1, 86, x, y + 1, z2 - 1, "polished_blackstone_bricks")
        self.set(48, y + 2, 87, "gilded_blackstone")
        self.set(50, y + 2, 87, "gilded_blackstone")
        self.chest(49, y + 2, 87, "north", "premium")
        self.candle(48, y + 3, 87, 4)
        self.candle(50, y + 3, 87, 4)
        for x, z in ((46, 82), (51, 82), (46, 86), (51, 86)):
            self.set(x, y + 7, z, "iron_chain[axis=y,waterlogged=false]")
            self.set(x, y + 6, z, "soul_lantern[hanging=true,waterlogged=false]")
        self.entity(49, y + 1, 83, guardian())

    # ------------------------------------------------------------ habitantes y conexiones
    def monjes(self):
        self.entity(51, F2 + 2, 76, villager("cleric", "plains"))
        self.entity(10, F2 + 1, 58, villager("librarian", "plains"))
        self.entity(14, F1 + 1, 35, villager("farmer", "plains"))

    def connect(self):
        """Estados de unión de cristales, verjas, vallas y muros según sus vecinos."""
        def solid(st):
            if not st:
                return False
            b = st.split("[")[0].replace("minecraft:", "")
            return b not in ("air", "water", "lantern", "candle", "torch") and not any(
                k in b for k in ("_carpet", "door", "sign", "banner", "candle", "lantern", "chain", "skull", "flower", "trapdoor",
                                 "fence_gate", "ladder", "lever", "wire", "pressure_plate", "tripwire", "bed", "slab",
                                 "stairs", "bell", "rod", "azalea") + tuple(FLOWERS))
        for (x, y, z), (st, nbt) in list(self.blocks.items()):
            b = st.split("[")[0].replace("minecraft:", "")
            if b.endswith("_pane") or b == "iron_bars" or b.endswith("_fence"):
                props = {}
                for d, (dx, dz) in (("north", (0, -1)), ("south", (0, 1)), ("west", (-1, 0)), ("east", (1, 0))):
                    n = self.get(x + dx, y, z + dz)
                    nb = n.split("[")[0].replace("minecraft:", "") if n else ""
                    same = nb.endswith("_pane") or nb == "iron_bars" if not b.endswith("_fence") else nb.endswith("_fence") or "fence_gate" in nb
                    props[d] = "true" if same or solid(n) else "false"
                self.set(x, y, z, f"{b}[east={props['east']},north={props['north']},south={props['south']},waterlogged=false,west={props['west']}]")
            elif b.endswith("_wall") and "sign" not in b and "banner" not in b and "torch" not in b:
                props = {}
                for d, (dx, dz) in (("north", (0, -1)), ("south", (0, 1)), ("west", (-1, 0)), ("east", (1, 0))):
                    n = self.get(x + dx, y, z + dz)
                    nb = n.split("[")[0].replace("minecraft:", "") if n else ""
                    ok = (nb.endswith("_wall") and "sign" not in nb and "banner" not in nb and "torch" not in nb) or solid(n) or "fence_gate" in nb
                    props[d] = "low" if ok else "none"
                above = self.get(x, y + 1, z)
                straight = (props["north"] == props["south"] == "low" and props["east"] == props["west"] == "none") or \
                           (props["east"] == props["west"] == "low" and props["north"] == props["south"] == "none")
                up = "false" if straight and not (above and above != "minecraft:air") else "true"
                self.set(x, y, z, f"{b}[east={props['east']},north={props['north']},south={props['south']},up={up},waterlogged=false,west={props['west']}]")

    def puzles_ajuste(self):
        """Niveles de polvo y antorchas del estado estable (calculados por el simulador de auditoria)."""
        from .auditoria import simular
        dust, _, torches = simular(self, {})
        for p, pw in dust.items():
            self.set(*p, self.get(*p).replace(f"power={self.get(*p).split('power=')[1].split(',')[0].split(']')[0]}", f"power={pw}"))
        for p, lit in torches.items():
            st = self.get(*p)
            self.set(*p, st.replace("lit=true", f"lit={'true' if lit else 'false'}").replace("lit=false", f"lit={'true' if lit else 'false'}"))

    def entrada(self):
        self.jigsaw(29, F0, 0, "north_up", "heraldia:entrance", "heraldia:entrance", "minecraft:empty",
                    final_state="minecraft:stone_bricks")


def guardian():
    return {"id": "minecraft:skeleton", "PersistenceRequired": B(1),
            "CustomName": text("guardian", "Fray Tenebrio, guardián del relicario"), "CustomNameVisible": B(1),
            "Health": F(40.0), "attributes": [{"id": "minecraft:max_health", "base": 40.0}],
            "equipment": {"mainhand": {"id": "minecraft:iron_sword", "count": 1,
                                       "components": {"minecraft:enchantments": {"minecraft:sharpness": 1}}},
                          "head": {"id": "minecraft:golden_helmet", "count": 1},
                          "chest": {"id": "minecraft:chainmail_chestplate", "count": 1}},
            "drop_chances": {"mainhand": F(0.15), "head": F(0.5), "chest": F(0.1)}}


def construir():
    o = Obra()
    o.macizo()
    o.camino()
    o.cerca()
    o.porteria()
    o.atrio()
    o.cementerio()
    o.hospederia()
    o.t1()
    o.t2()
    o.cuevas()
    o.monjes()
    o.connect()
    o.entrada()
    from pack import fix_supports
    fix_supports(o)
    o.puzles_ajuste()
    return o
