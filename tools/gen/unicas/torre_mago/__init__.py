"""Torre de mago (heraldia:unicas/torre_mago): torre esbelta de ocho plantas con sótano de dos niveles.

Diseño y recorrido: docs/unicas/torre_mago.md. Una sola plantilla rígida diseñada a mano:
  sótano 2 (cámara del tesoro) · sótano 1 (experimentos fallidos) · vestíbulo · biblioteca de doble altura
  con galería · laboratorio · encantamientos · invernadero · dormitorio · observatorio; anexo oculto en la galería.
La plantilla se hunde 14 bloques (start_height -14, sin adaptación del terreno): el suelo del vestíbulo queda
a ras del terreno y el sótano bajo tierra sin que el beard excave alrededor. Una terraza con cimiento absorbe
pendientes suaves.
"""
from .._comun.piezas import open_stairwells
import math
from core import Template, B
from unicas._comun import piezas
from unicas._comun.botin import item, empty, cofre as t2, named as _named, potion as _potion, random_ench, lang

SID = "torre_mago"
NSP = f"unicas/{SID}"
NOMBRE = {"es_es": "Torre de mago", "en_us": "Wizard Tower"}
TROFEO = {"objeto": "blaze_rod", "rareza": "epic",
          "nombre": ("Báculo del Archimago Malvarius", "Staff of Archmage Malvarius"),
          "lore": [("Todavía chisporrotea con su último conjuro.", "It still crackles with his final spell.")]}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
    "cofre": "escondite",
    "relato": [
        ("En el bosque oscuro vive el archimago Malvarius, en una torre llena de libros, calderos y "
         "experimentos. Me ayudó a escribir los pliegos con una tinta que el agua no borra. A cambio, "
         "quiso leerlos todos.",
         "In the dark forest lives Archmage Malvarius, in a tower full of books, cauldrons and "
         "experiments. He helped me write the leaves in an ink that water cannot wash away. In return, he"
         " wished to read them all."),
        ("No se lo permití. Le confié uno solo, que escondió en un cuarto secreto de la torre, y juró no "
         "abrirlo. Creo que lo abrió: desde entonces no deja de buscar el resto.",
         "I did not allow it. I entrusted him with one alone, which he hid in a secret room of the tower,"
         " and he swore not to open it. I believe he did: ever since, he has not stopped seeking the "
         "rest."),
    ],
    "pista": ("el bosque oscuro, donde un archimago sigue con sus experimentos en lo alto de una torre",
              "the dark forest, where an archmage carries on his experiments atop a tower"),
}
LOGRO = {"icono": "minecraft:enchanting_table"}   # logros.py
OX, OZ = 13, 12                      # desplazamiento: coordenadas relativas al eje de la torre -> plantilla >= 0
FEET = dict(B2=2, B1=8, f0=14, f1=20, f2=26, f3=32, f4=38, f5=44, f6=50, f7=56)
REVS = [8, 14, 20, 26, 32, 38, 44, 50]   # tramos de la escalera de caracol (pies al salir de cada planta)
R2 = 70                               # radio exterior de la torre (al cuadrado)
WALL_TOP = 62                         # última hilada del muro del observatorio
TERRACE_R2 = 156

STRUCTURE = dict(biomes="#heraldia:oscuro", start_pool=f"{NSP}/inicio", size=1, max_distance=32,
                 terrain_adaptation="none", step="surface_structures", start_height={"absolute": -14},
                 project_to="WORLD_SURFACE_WG", spacing=250, separation=190)

# ------------------------------------------------------------------ textos (es_es / en_us)
TXT = {
    "guardian": ("Archimago Malvarius", "Archmage Malvarius"),
    "cartel.caldero.1": ("Lo que el caldero", "What the cauldron"),
    "cartel.caldero.2": ("guarda lleno", "keeps when full"),
    "cartel.caldero.3": ("abre lo que", "opens what"),
    "cartel.caldero.4": ("el hierro cierra", "the iron shuts"),
    "cartel.estante.1": ("Cada tomo", "Every tome"),
    "cartel.estante.2": ("en su sitio;", "in its place;"),
    "cartel.estante.3": ("el sexto también", "the sixth one too"),
    "diario.1": ("Diario de Malvarius.\n\nLa torre guarda sus secretos para quien sabe leer: en la galería, "
                 "un estante incompleto espera su sexto tomo.",
                 "Malvarius' journal.\n\nThe tower keeps its secrets for those who can read: in the gallery, "
                 "an unfinished shelf awaits its sixth tome."),
    "diario.2": ("Bajo tierra quedan mis experimentos fallidos. No los despiertes.\n\nLa puerta de hierro solo "
                 "cede ante un caldero lleno hasta el borde.",
                 "Below ground lie my failed experiments. Do not wake them.\n\nThe iron door only yields to a "
                 "cauldron filled to the brim."),
    "diario.3": ("Cuidado con los hilos del ala oeste y con la losa suelta ante mi cámara.",
                 "Beware the threads in the west wing and the loose slab before my chamber."),
    "baculo": ("Báculo de Malvarius", "Staff of Malvarius"),
    "grimorio": ("Grimorio del archimago", "Archmage's grimoire"),
    "capucha": ("Capucha del aprendiz", "Apprentice's hood"),
    "catalejo": ("Catalejo del astrónomo", "Astronomer's spyglass"),
    "reloj": ("Reloj de las horas muertas", "Clock of the dead hours"),
    "elixir": ("Elixir del alquimista", "Alchemist's elixir"),
    "daga": ("Daga ritual", "Ritual dagger"),
    "botas": ("Botas del peregrino", "Pilgrim's boots"),
    "espada": ("Hoja del archimago", "Archmage's blade"),
    "coraza": ("Coraza encantada", "Enchanted cuirass"),
}
KEY = "heraldia.unicas.torre_mago."


def tr(k):
    return {"translate": KEY + k, "fallback": TXT[k][0]}


LANG = lang(KEY, TXT)


# ------------------------------------------------------------------ geometría
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
CIRCLE = {(x, z) for x in range(-9, 10) for z in range(-9, 10) if x * x + z * z <= R2}
WALLC = {c for c in CIRCLE if any((c[0] + a, c[1] + b) not in CIRCLE for a, b in N4)}
INT = CIRCLE - WALLC
PERIM = {c for c in INT if any((c[0] + a, c[1] + b) in WALLC for a, b in N4)}
RING = piezas.RING                    # escalera de caracol alrededor del machón (pieza común)
GALLERY_FREE = set()
ANNEX = {(x, z) for x in range(-13, -7) for z in range(-5, 5)} - CIRCLE


def cheb(c):
    return max(abs(c[0]), abs(c[1]))


def r2(c):
    return c[0] * c[0] + c[1] * c[1]


# materiales
WALL = "deepslate_bricks"
BAND = "polished_deepslate"
FLOOR = "dark_oak_planks"
DUN = "stone_bricks"
FOUND = "cobbled_deepslate"
STAIR = "dark_oak_stairs"
NEWEL = "dark_oak_log[axis=y]"
GLASS = "gray_stained_glass_pane"
LANT = "lantern[hanging=true]"
SLANT = "soul_lantern[hanging=true]"


class Torre:
    def __init__(self):
        self.t = Template(f"{NSP}/torre")
        self.loot = lambda n: f"heraldia:{NSP}/{n}"

    def s(self, x, y, z, st, nbt=None):
        self.t.set(x + OX, y, z + OZ, st, nbt)

    def g(self, x, y, z):
        return self.t.get(x + OX, y, z + OZ)

    def rm(self, x, y, z):
        self.t.clear(x + OX, y, z + OZ)

    def fill(self, x1, y1, z1, x2, y2, z2, st):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.s(x, y, z, st)

    def chest(self, x, y, z, facing, name, kind="chest"):
        piezas.chest(self.s, x, y, z, facing, self.loot(name), kind)

    def sign(self, x, y, z, facing, keys):
        piezas.sign(self.s, x, y, z, facing, [tr(k) for k in keys])

    def spawner(self, x, y, z, mob):
        piezas.spawner(self.s, x, y, z, mob, potentials=True)


# ------------------------------------------------------------------ terreno: cimiento, terraza
def terraza(T):
    for x in range(-12, 13):
        for z in range(-12, 13):
            c = (x, z)
            if r2(c) > TERRACE_R2:
                continue
            T.fill(x, 9, z, x, 12, z, FOUND)
            T.s(x, 13, z, "polished_tuff" if (x + z) % 5 == 0 else FOUND)
            for y in range(14, 19):
                T.s(x, y, z, "air")
            if r2(c) > 132 and not (abs(x) <= 1 and z < 0):
                T.s(x, 14, z, "cobbled_deepslate_wall")
    # camino de entrada
    for z in range(-12, -8):
        for x in (-1, 0, 1):
            T.s(x, 13, z, "polished_deepslate")
    # postes con farol a los lados del camino (sobre el muro de la terraza)
    for x in (-2, 2):
        T.s(x, 14, -12, "cobbled_deepslate_wall")
        T.s(x, 15, -12, "lantern[hanging=false]")


# ------------------------------------------------------------------ sótanos
B1_MAP = [
    "#####################",   # z=-10
    "###....#.....#....###",   # -9
    "#e#....#.....#....###",   # -8
    "#.#bbbb#bbbbb#bbbb###",   # -7
    "#w#S.............c###",   # -6
    "#w########.##########",   # -5
    "#....#.........#...c#",   # -4
    "#....#.........#w...#",   # -3
    "#....#.........#....#",   # -2
    "#....#.........#....#",   # -1
    "#...................#",   # 0
    "#....#.........#....#",   # 1
    "#....#.........#..S.#",   # 2
    "#....#.........#...w#",   # 3
    "#....#....XXXX.#.w..#",   # 4
    "#######.#KCrrrD######",   # 5
    "###.......####v######",   # 6
    "###.......####v######",   # 7
    "###.......###########",   # 8
    "###.......###########",   # 9
    "#####################",   # 10
]
B2_MAP = [
    "#####################",   # z=1
    "#.........###########",   # 2
    "#.........###########",   # 3
    "#.........###########",   # 4
    "#.........###########",   # 5
    "#.........####v######",   # 6
    "#.........####v######",   # 7
    "#.........####v######",   # 8
    "#.........####v######",   # 9
    "#####.########v######",   # 10
    "#####.....P...L######",   # 11
    "#####################",   # 12
]


def sotanos(T):
    y1, y2 = FEET["B1"], FEET["B2"]
    # sótano 2: cimiento, suelo, salas, techo
    for zi, row in enumerate(B2_MAP):
        z = zi + 1
        for xi, ch in enumerate(row):
            x = xi - 10
            T.s(x, 0, z, DUN)
            T.s(x, 1, z, "polished_tuff" if ch in ".P" and (x + z) % 2 else DUN)
            for y in range(y2, y2 + 5):
                T.s(x, y, z, DUN if ch == "#" else "air")
            T.s(x, 7, z, DUN)
    # sótano 1
    for zi, row in enumerate(B1_MAP):
        z = zi - 10
        for xi, ch in enumerate(row):
            x = xi - 10
            if (x, 7, z) not in [(4, 7, 6), (4, 7, 7)]:
                T.s(x, 7, z, "tuff_bricks" if ch != "#" and (x * 3 + z) % 4 == 0 else DUN)
            for y in range(y1, y1 + 5):
                solid = ch == "#" or (ch in "KCr" and y > y1) or (ch == "D" and y > y1 + 1)
                T.s(x, y, z, DUN if solid else "air")
            T.s(x, 13, z, DUN if (x, z) not in CIRCLE and r2((x, z)) > TERRACE_R2 else T.g(x, 13, z) or DUN)
            if ch == "b":
                for y in range(y1, y1 + 5):
                    T.s(x, y, z, "iron_bars")
            elif ch == "w":
                T.s(x, y1, z, "cobweb")
                T.s(x, y1 + 1, z, "cobweb")
            elif ch == "X":
                T.s(x, y1, z, "polished_tuff")
    # tramo recto al sótano 2, tras la puerta de hierro (pies 7 -> 2)
    for i, z in enumerate(range(6, 11)):
        ys = 6 - i
        T.s(4, ys, z, "stone_brick_stairs[facing=north,half=bottom]")
        for y in range(1, ys):
            T.s(4, y, z, DUN)
        for y in range(ys + 1, 7):
            T.s(4, y, z, "air")
    for z in (6, 7):
        T.s(4, 7, z, "air")
    T.s(4, 1, 11, "polished_tuff")


def sotano1_detalle(T):
    y = FEET["B1"]
    # puzle del caldero: caldero -> comparador -> 3 de polvo -> puerta de hierro (solo nivel 3 la abre)
    T.s(-1, y, 5, "cauldron")
    piezas.comparator(T.s, 0, y, 5, "west")
    piezas.wire(T.s, [(1, 5), (2, 5), (3, 5)], y, ends={0: "west", 2: "east"})
    T.s(4, y, 5, "iron_door[facing=south,half=lower,hinge=left,open=false,powered=false]")
    T.s(4, y + 1, 5, "iron_door[facing=south,half=upper,hinge=left,open=false,powered=false]")
    T.sign(-1, y + 1, 4, "north", ["cartel.caldero.1", "cartel.caldero.2", "cartel.caldero.3", "cartel.caldero.4"])
    # el cartel cuelga del muro sobre el caldero
    # mesa de trabajo (tapa la acequia de redstone)
    T.s(1, y + 1, 4, "brewing_stand")
    T.s(3, y + 1, 4, "candle[candles=3,lit=false]")
    # trampa del ala oeste (como en los templos de la jungla): hilo de lado a lado, dispensadores con flechas
    piezas.tripwire_trap(T.s, (-6, -4), (-6, 4), y, "z", [((-6, y + 1, -5), "south"), ((-6, y + 1, 5), "north")])
    # generadores en la mazmorra
    T.spawner(-7, y, -6, "zombie_villager")
    T.spawner(8, y, 2, "cave_spider")
    # cofres
    T.chest(7, y, -6, "west", "experimentos")
    T.chest(9, y, -4, "west", "experimentos")
    T.chest(-9, y, -8, "south", "escondite")
    # celdas: restos de experimentos
    T.s(-5, y, -9, "skeleton_skull[rotation=3]")
    T.s(-4, y, -8, "bone_block[axis=x]")
    T.s(0, y, -9, "slime_block")
    T.s(0, y, -8, "crying_obsidian")
    T.s(-1, y, -9, "cobweb")
    T.s(5, y, -9, "cobweb")
    T.s(6, y + 1, -9, "cobweb")
    T.s(4, y, -8, "skeleton_skull[rotation=12]")
    T.s(2, y, -7, "air")             # barrote arrancado
    T.s(2, y + 1, -7, "air")
    # ala oeste: laboratorio derrumbado
    T.fill(-9, y, 2, -8, y, 4, "cobbled_deepslate")
    T.s(-9, y + 1, 4, "cobbled_deepslate")
    T.s(-9, y, 1, "gravel")
    T.s(-8, y, -3, "cauldron")
    T.s(-9, y, -3, "crafting_table")
    T.s(-9, y, -1, "decorated_pot[facing=east]")
    # ala sur: sala de experimentos fallidos (cráter de una explosión)
    for (x, z) in ((-5, 7), (-4, 7), (-5, 8), (-4, 8), (-3, 8), (-4, 9)):
        T.s(x, 7, z, "cracked_stone_bricks")
    T.s(-4, 6, 8, "magma_block")
    T.s(-4, 7, 8, "soul_soil")
    T.s(-7, y, 6, "barrel[facing=up]", {"id": "minecraft:barrel", "LootTable": T.loot("experimentos")})
    T.s(-1, y, 9, "cauldron")
    T.s(-7, y, 9, "decorated_pot[facing=east]")
    T.s(-2, y, 6, "cobweb")
    T.s(-7, y + 4, 8, "cobweb")
    # luz tenue (faroles de almas en el vestíbulo inferior)
    for x, z in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
        T.s(x, y + 4, z, SLANT)


def sotano2_detalle(T):
    y = FEET["B2"]
    # trampa de la losa (como en los templos del desierto): placa sobre el suelo y TNT debajo
    piezas.tnt_trap(T.s, 0, y, 11, warn=[(-1, 1, 11), (1, 1, 11)])
    # cámara del tesoro
    for x, z in ((-8, 3), (-2, 3), (-8, 8), (-2, 8)):
        for yy in range(y, y + 5):
            T.s(x, yy, z, "polished_deepslate" if yy != y + 4 else "chiseled_deepslate")
    T.chest(-5, y, 2, "south", "premium")
    T.chest(-9, y, 6, "east", "tesoro")
    for x in (-7, -6, -4, -3):
        T.s(x, y, 2, "bookshelf")
        T.s(x, y + 1, 2, "bookshelf")
    T.s(-6, y + 2, 2, "purple_candle[candles=2,lit=false]")
    for x in (-6, -5, -4):
        for z in (4, 5, 6, 7):
            T.s(x, y, z, "purple_carpet")
    T.s(-9, y, 3, "amethyst_cluster[facing=up,waterlogged=false]")
    T.s(-1, y, 9, "amethyst_cluster[facing=up,waterlogged=false]")
    T.s(-1, y, 2, "decorated_pot[facing=south]")
    T.s(-9, y, 9, "decorated_pot[facing=east]")
    for x, z in ((-5, 4), (-5, 8)):
        T.s(x, y + 4, z, SLANT)
    T.s(4, y + 4, 11, SLANT)
    # guardián: evocador con nombre, persistente, algo más resistente que uno normal
    T.t.entity(-5 + OX, y, 6 + OZ, piezas.guardian("evoker", KEY + "guardian", TXT["guardian"][0], 48, armor=4,
                                                    death_loot="minecraft:entities/witch"))


# ------------------------------------------------------------------ torre
def muros(T):
    for (x, z) in WALLC:
        for y in range(13, WALL_TOP + 1):
            T.s(x, y, z, BAND if (y + 1) in FEET.values() or y in (13, WALL_TOP) else WALL)
    # interior vacío
    for (x, z) in INT:
        for y in range(14, WALL_TOP + 1):
            T.s(x, y, z, "air")
    # forjados
    for name in ("f0", "f1", "f3", "f4", "f5", "f6", "f7"):
        y = FEET[name] - 1
        for c in INT:
            T.s(c[0], y, c[1], FLOOR if name not in ("f0", "f7") else "polished_deepslate")
    # galería (f2): solo la banda perimetral, la plataforma de la escalera y dos pasarelas
    y = FEET["f2"] - 1
    for c in INT:
        if r2(c) >= 25 or cheb(c) <= 2 or (abs(c[0]) in (3, 4) and abs(c[1]) <= 1 and c[0] > 0) \
                or (abs(c[1]) in (3, 4) and abs(c[0]) <= 1 and c[1] < 0):
            T.s(c[0], y, c[1], FLOOR)


def ventanas(T):
    W = {"N": [(0, -8)], "S": [(0, 8)], "E": [(8, 0)], "O": [(-8, 0)]}
    plan = {"f0": "SEO", "f1": "NSE", "f2": "NSE", "f3": "NSEO", "f4": "NEO", "f5": "NSEO", "f6": "NEO", "f7": "NSEO"}
    for fl, dirs in plan.items():
        y = FEET[fl]
        tall = 3 if fl in ("f5", "f7") else 2
        wide = fl in ("f5", "f7")
        for d in dirs:
            for (x, z) in W[d]:
                cells = [(x, z)]
                if wide:
                    cells = [(x + k, z) for k in (-1, 1)] + cells if d in "NS" else [(x, z + k) for k in (-1, 1)] + cells
                for cx, cz in cells:
                    for yy in range(y + 1, y + 1 + tall):
                        T.s(cx, yy, cz, GLASS if fl not in ("f5",) else "glass_pane")
    # puerta principal (norte) y su arco
    y = FEET["f0"]
    T.s(0, y, -8, "dark_oak_door[facing=south,half=lower,hinge=left,open=false]")
    T.s(0, y + 1, -8, "dark_oak_door[facing=south,half=upper,hinge=left,open=false]")
    T.s(0, y + 2, -8, "chiseled_deepslate")
    T.s(-1, y + 2, -9, "deepslate_brick_stairs[facing=east,half=top]")
    T.s(1, y + 2, -9, "deepslate_brick_stairs[facing=west,half=top]")
    T.s(0, y + 3, -9, "lantern[hanging=true]")
    T.s(0, y + 4, -9, "deepslate_brick_slab[type=top]")


def escalera(T):
    guard = piezas.spiral_stair(T.s, 0, 0, REVS, STAIR, NEWEL, FLOOR, newel_top=FEET["f7"])
    for (x, z) in RING[:2]:
        T.s(x, FEET["B1"] - 1, z, DUN)
    # barandilla junto al hueco en cada planta a la que llega la escalera (salvo la galería, que tiene la suya)
    for fl in ("f0", "f1", "f3", "f4", "f5", "f6", "f7"):
        for (x, z) in guard + ([RING[4]] if fl == "f7" else []):
            T.s(x, FEET[fl], z, "dark_oak_fence")


def galeria(T):
    """f1 + f2: biblioteca de doble altura. Abajo estanterías bajo la galería; arriba galería con barandilla."""
    y1, y2 = FEET["f1"], FEET["f2"]
    band = {c for c in INT if r2(c) >= 25}
    atrium = {c for c in INT if r2(c) < 25 and cheb(c) >= 3}
    bridges = {(3, 0), (4, 0), (0, -3), (0, -4)}
    keep1 = {(0, -7), (0, 7), (7, 0), (-7, 0)}            # frente de ventana (y el armario del cofre)
    for c in PERIM:
        if c in keep1:
            continue
        for y in range(y1, y1 + 5):
            T.s(c[0], y, c[1], "bookshelf")
    # cofre de la biblioteca y atriles de lectura
    T.chest(-7, y1, 0, "east", "biblioteca")
    for y in range(y1 + 1, y1 + 5):
        T.s(-7, y, 0, "bookshelf")
    T.s(3, y1, 3, "lectern[facing=north,has_book=false,powered=false]")
    T.s(-3, y1, 3, "lectern[facing=north,has_book=false,powered=false]")
    T.s(3, y1, -3, "lectern[facing=south,has_book=false,powered=false]")
    # mesa de lectura con sillas (respaldo hacia fuera)
    T.s(-3, y1, -3, "dark_oak_fence")
    T.s(-3, y1 + 1, -3, "dark_oak_pressure_plate[powered=false]")
    T.s(-4, y1, -3, f"{STAIR}[facing=west,half=bottom]")
    T.s(-3, y1, -4, f"{STAIR}[facing=north,half=bottom]")
    for c in ((5, 3), (-5, 3), (5, -3), (-5, -3)):
        T.s(c[0], y1 + 4, c[1], LANT)
    # galería: estanterías en el muro, barandilla al atrio; donde el pasillo gira en diagonal se deja libre
    # la celda del muro (sin estantería) para que la barandilla siga continua
    edge = {c for c in band - PERIM if any((c[0] + a, c[1] + b) in atrium for a, b in N4)} - {(5, 0), (0, -5)}
    lane = band - PERIM - edge
    free = {(0, -7), (0, 7), (7, 0), (-7, 0)}
    for (x, z) in lane:
        for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            d = (x + a, z + b)
            if d in lane and (x + a, z) not in lane and (x, z + b) not in lane:
                free |= {p for p in ((x + a, z), (x, z + b)) if p in PERIM}
    GALLERY_FREE.update(free)
    for c in PERIM:
        if c in free:
            continue
        for y in range(y2, y2 + 4):
            T.s(c[0], y, c[1], "bookshelf")
    for c in edge:
        T.s(c[0], y2, c[1], "dark_oak_fence")
    for c in INT:
        if cheb(c) == 2 and c not in ((2, 0), (0, -2)):
            T.s(c[0], y2, c[1], "dark_oak_fence")
    for (bx, bz) in ((3, 0), (4, 0)):
        for dz in (-1, 1):
            T.s(bx, y2 - 1, dz, FLOOR)
            T.s(bx, y2, dz, "dark_oak_fence")
    for (bx, bz) in ((0, -3), (0, -4)):
        for dx in (-1, 1):
            T.s(dx, y2 - 1, bz, FLOOR)
            T.s(dx, y2, bz, "dark_oak_fence")
    T.chest(6, y2, 3, "west", "biblioteca")
    T.s(3, y2 + 4, 5, LANT)
    T.s(-3, y2 + 4, -5, LANT)
    T.s(0, y2 + 4, 5, LANT)
    # estanterías cinceladas decorativas
    assert not GALLERY_FREE & {(-7, 1), (-7, 2), (-7, -1), (-7, -2), (7, 2), (7, -2)}, "estanterías que tapan la puerta"
    for c, fac in (((7, 2), "west"), ((7, -2), "west")):
        T.s(c[0], y2 + 1, c[1], f"chiseled_bookshelf[facing={fac},slot_0_occupied=true,slot_1_occupied=false,"
                                 f"slot_2_occupied=true,slot_3_occupied=true,slot_4_occupied=false,slot_5_occupied=false]",
            {"id": "minecraft:chiseled_bookshelf", "last_interacted_slot": -1,
             "Items": [{"Slot": B(i), "id": "minecraft:book", "count": 1} for i in (0, 2, 3)]})


def anexo(T):
    """Estudio oculto tras la galería, en un torreón adosado al oeste.

    Puerta de dos estanterías sujetas por pistones pegajosos extendidos (alimentados por una antorcha de
    redstone). Estantería cincelada con el sexto hueco vacío -> comparador -> 6 de polvo -> bloque de la antorcha.
    Solo el hueco 6 da señal 6, que llega con 1 al final del polvo: la antorcha se apaga y los pistones retraen.
    Todo queda en estado coherente al colocarse (nada depende de actualizaciones de bloque)."""
    y0, top = 13, 31
    for (x, z) in ANNEX:
        for y in range(y0, top + 1):
            T.s(x, y, z, WALL if y not in (y0, top, FEET["f2"] - 1) else BAND)
        if x in (-13,) or z in (-5, 4) or (x, z) in ((-8, -5), (-8, 4)):
            T.s(x, top + 1, z, "deepslate_brick_wall")
    for x in range(-12, -8):
        for z in range(-4, 4):
            T.s(x, top + 1, z, "deepslate_tile_slab[type=bottom]")
    y = FEET["f2"]
    # estudio
    for x in range(-12, -8):
        for z in range(0, 4):
            for yy in range(y, y + 4):
                T.s(x, yy, z, "air")
    T.chest(-12, y, 1, "east", "estudio")
    T.s(-10, y, 3, "dark_oak_slab[type=top]")
    T.s(-10, y + 1, 3, "candle[candles=2,lit=false]")
    T.s(-10, y, 2, f"{STAIR}[facing=north,half=bottom]")
    T.s(-12, y, 3, "bookshelf")
    T.s(-12, y + 1, 3, "bookshelf")
    T.s(-11, y, 3, "bookshelf")
    T.s(-12, y, 0, "cartography_table")
    T.s(-11, y + 3, 1, LANT)
    T.s(-13, y + 1, 2, GLASS)
    # hornacina en el muro de la torre y puerta secreta
    T.s(-8, y, 0, "air")
    T.s(-8, y + 1, 0, "air")
    piezas.piston_door(T.s, [(-9, y, 0), (-9, y + 1, 0)], (0, -1), "south", "bookshelf")
    T.s(-8, y + 1, -1, "chiseled_bookshelf[facing=south," + ",".join(
        f"slot_{i}_occupied={'true' if i < 5 else 'false'}" for i in range(6)) + "]",
        {"id": "minecraft:chiseled_bookshelf", "last_interacted_slot": -1,
         "Items": [{"Slot": B(i), "id": "minecraft:book", "count": 1} for i in range(5)]})
    T.s(-8, y, -1, "bookshelf")
    yy = y + 1
    piezas.comparator(T.s, -8, yy, -2, "south")
    piezas.wire(T.s, [(-8, -3), (-8, -4), (-9, -4), (-10, -4), (-11, -4), (-11, -3)], yy, ends={0: "south", 5: "south"})
    T.s(-11, yy, -2, "polished_andesite")                         # bloque que sujeta la antorcha
    T.s(-10, yy, -2, "redstone_wall_torch[facing=east,lit=true]")
    T.sign(-7, y + 2, 0, "east", ["cartel.estante.1", "cartel.estante.2", "cartel.estante.3"])
    # en el análisis de recorrido, la puerta se considera abierta (puzle resuelto)
    T.t.lint_open = {(-9 + OX, y, 0 + OZ): "minecraft:air", (-9 + OX, y + 1, 0 + OZ): "minecraft:air"}


def plantas(T):
    # f0 vestíbulo
    y = FEET["f0"]
    for z in range(-7, -2):
        T.s(0, y, z, "purple_carpet")
    T.s(-1, y + 1, -7, "purple_wall_banner[facing=south]")
    T.s(1, y + 1, -7, "purple_wall_banner[facing=south]")
    for z in (-2, -1, 1, 2):
        T.s(-7, y, z, f"{STAIR}[facing=west,half=bottom]")
        T.s(7, y, z, f"{STAIR}[facing=east,half=bottom]")
    T.chest(3, y, 6, "north", "vestibulo", kind="barrel")
    T.s(-3, y, 6, "lectern[facing=north,has_book=true,powered=false]", {
        "id": "minecraft:lectern", "Page": 0, "Book": {"id": "minecraft:written_book", "count": 1, "components": {
            "minecraft:written_book_content": {"title": {"raw": "Malvarius"}, "author": "Malvarius",
                                               "pages": [{"raw": tr(f"diario.{i}")} for i in (1, 2, 3)]}}}})
    for c in ((5, 5), (-5, 5), (5, -5), (-5, -5)):
        T.s(c[0], y, c[1], "potted_fern" if c[1] > 0 else "potted_red_mushroom")
    for c in ((4, -4), (-4, -4), (4, 4), (-4, 4)):
        T.s(c[0], y + 4, c[1], LANT)
    # f3 laboratorio de pociones
    y = FEET["f3"]
    for c in ((-6, -3), (-6, -4), (-5, -5), (-4, -6), (-3, -6)):
        T.s(c[0], y, c[1], "polished_andesite")
    for c in ((-6, -3), (-5, -5), (-3, -6)):
        T.s(c[0], y + 1, c[1], "brewing_stand")
    T.s(-6, y + 1, -4, "potted_brown_mushroom")
    T.s(-4, y + 1, -6, "potted_crimson_fungus")
    T.s(6, y, -3, "water_cauldron[level=3]")
    T.s(6, y, 3, "cauldron")
    T.chest(-6, y, 3, "east", "laboratorio")
    T.chest(3, y, 6, "north", "laboratorio")
    T.s(-4, y, 6, "barrel[facing=up]")
    T.s(-3, y, 6, "barrel[facing=up]")
    T.s(6, y, 2, "decorated_pot[facing=west]")
    T.s(4, y, -6, "decorated_pot[facing=south]")
    # restos de una explosión: suelo chamuscado y ventana este sin vidrio
    for c in ((4, 3), (5, 2), (4, 2), (5, 3)):
        T.s(c[0], y - 1, c[1], "blackstone" if (c[0] + c[1]) % 2 else "coal_block")
    T.s(8, y + 1, 0, "air")
    T.s(8, y + 2, 0, "air")
    for c in ((4, -4), (-4, 4), (4, 4)):
        T.s(c[0], y + 4, c[1], LANT)
    # f4 sala de encantamientos
    y = FEET["f4"]
    T.s(0, y, 5, "enchanting_table")
    for c in ((-2, 4), (-2, 5), (-2, 6), (2, 4), (2, 5), (2, 6), (-1, 7), (1, 7), (0, 7)):
        T.s(c[0], y, c[1], "bookshelf")
        T.s(c[0], y + 1, c[1], "bookshelf")
    for c in ((-3, 6), (3, 6)):
        T.s(c[0], y, c[1], "amethyst_block")
        T.s(c[0], y + 1, c[1], "amethyst_cluster[facing=up,waterlogged=false]")
    for x in (-1, 0, 1):
        T.s(x, y, 3, "purple_carpet")
    T.chest(-6, y, -3, "east", "encantamientos")
    T.s(6, y, -3, "lectern[facing=west,has_book=false,powered=false]")
    T.s(-5, y, -5, "purple_candle[candles=4,lit=false]")
    T.s(5, y, -5, "purple_candle[candles=3,lit=false]")
    for c in ((-4, -4), (4, -4), (0, 5)):
        T.s(c[0], y + 4, c[1], LANT)
    # f5 invernadero
    y = FEET["f5"]
    beds = [c for c in PERIM if c not in {(0, -7), (0, 7), (7, 0), (-7, 0), (1, -7), (-1, -7), (1, 7), (-1, 7),
                                          (7, 1), (7, -1), (-7, 1), (-7, -1)}]
    plants = ["torchflower", "open_eyeblossom", "lily_of_the_valley", "fern", "azalea", "blue_orchid",
              "closed_eyeblossom", "flowering_azalea", "allium", "pitcher_plant"]
    for i, c in enumerate(sorted(beds, key=lambda c: math.atan2(c[0], -c[1]))):
        T.s(c[0], y, c[1], "moss_block" if i % 3 else "rooted_dirt")
        p = plants[i % len(plants)]
        if p == "pitcher_plant":
            T.s(c[0], y + 1, c[1], "pitcher_plant[half=lower]")
            T.s(c[0], y + 2, c[1], "pitcher_plant[half=upper]")
        else:
            T.s(c[0], y + 1, c[1], p)
    T.chest(-4, y, -4, "south", "invernadero", kind="barrel")
    T.s(4, y, -4, "water_cauldron[level=2]")
    T.s(4, y, 4, "composter[level=3]")
    for c in ((-3, -3), (3, 3), (3, -3), (-3, 3)):
        T.s(c[0], y + 4, c[1], "spore_blossom")
    T.s(0, y + 4, -4, LANT)
    T.s(0, y + 4, 4, LANT)
    # f6 dormitorio del mago: cama contra el muro sur, mesillas, librería, escritorio
    y = FEET["f6"]
    T.s(0, y, 7, "purple_bed[facing=south,part=head,occupied=false]")
    T.s(0, y, 6, "purple_bed[facing=south,part=foot,occupied=false]")
    T.chest(1, y, 7, "west", "dormitorio")
    T.s(-1, y, 7, "bookshelf")
    T.s(-1, y + 1, 7, "potted_allium")
    for c in ((-7, -2), (-6, -3), (-6, -4)):
        T.s(c[0], y, c[1], "bookshelf")
        T.s(c[0], y + 1, c[1], "bookshelf")
    T.s(6, y, -3, "dark_oak_slab[type=top]")
    T.s(6, y + 1, -3, "purple_candle[candles=1,lit=false]")
    T.s(5, y, -3, f"{STAIR}[facing=west,half=bottom]")
    for x in (-1, 0, 1):
        for z in (3, 4):
            T.s(x, y, z, "purple_carpet")
    T.s(-6, y, 3, "barrel[facing=up]")
    for c in ((4, 4), (-4, -4)):
        T.s(c[0], y + 4, c[1], LANT)
    T.s(6, y + 4, 2, "cobweb")
    T.s(-5, y + 4, 5, "cobweb")
    # f7 observatorio
    y = FEET["f7"]
    T.s(0, y + 1, 0, "polished_blackstone_wall[up=true]")
    T.s(0, y + 2, 0, "waxed_copper_block")
    T.s(0, y + 2, -1, "lightning_rod[facing=north,powered=false,waterlogged=false]")
    T.s(0, y + 2, 1, "lightning_rod[facing=south,powered=false,waterlogged=false]")
    T.chest(6, y, 3, "west", "observatorio")
    T.s(-6, y, 3, "cartography_table")
    T.s(-6, y, -3, "lectern[facing=east,has_book=false,powered=false]")
    T.s(5, y, -5, "purple_candle[candles=2,lit=false]")
    T.s(-5, y, 5, "amethyst_cluster[facing=up,waterlogged=false]")
    # escombros del tejado caído en el sudeste
    T.s(4, y, 5, "cobbled_deepslate")
    T.s(5, y, 4, "deepslate_tile_slab[type=bottom]")


def tejado(T):
    base = WALL_TOP + 1
    H = 14
    shell = set()
    for j in range(H):
        rj = 8.6 * (1 - j / H)
        rn = 8.6 * (1 - (j + 1) / H)
        for x in range(-9, 10):
            for z in range(-9, 10):
                d = math.hypot(x, z)
                if d <= rj and (d > rn - 0.6 or j == H - 1):
                    ang = math.degrees(math.atan2(x, -z))
                    if abs(ang) < 14 and 1 <= j <= 6:
                        continue                      # rendija de observación hacia el norte
                    if 1 <= j <= 3 and 120 < ang < 140 and d > rj - 1.2:
                        continue                      # hueco de tejas caídas (sudeste)
                    shell.add((x, base + j, z))
    for (x, y, z) in shell:
        T.s(x, y, z, "deepslate_tiles")
    top = base + H
    T.s(0, top, 0, "amethyst_block")
    T.s(0, top + 1, 0, "lightning_rod[facing=up,powered=false,waterlogged=false]")
    # cornisa
    for x in range(-9, 10):
        for z in range(-9, 10):
            if (x, z) not in CIRCLE and any((x + a, z + b) in WALLC for a, b in N4):
                T.s(x, WALL_TOP, z, "deepslate_brick_slab[type=top]")


def ruina(T):
    # muro de la terraza derrumbado en el sudoeste, musgo y enredaderas
    for x in range(-12, 13):
        for z in range(-12, 13):
            if 132 < r2((x, z)) <= TERRACE_R2 and math.degrees(math.atan2(x, -z)) < -110 and z > 0:
                T.s(x, 14, z, "air")
                if (x + z) % 3 == 0:
                    T.s(x, 14, z, "cobbled_deepslate_slab[type=bottom]")
    for (x, z) in ((5, -10), (6, -9), (-8, 7), (-9, 6), (9, 4), (10, 3), (3, 10)):
        if T.g(x, 14, z) in (None, "minecraft:air"):
            T.s(x, 14, z, "pale_moss_carpet[bottom=true,east=none,north=none,south=none,west=none]")
    # enredaderas por la cara exterior: la propiedad indica el muro al que se agarran
    for (x, z, face, h) in ((9, -2, "west", 12), (9, -1, "west", 9), (-2, 9, "north", 16), (2, 9, "north", 7),
                            (3, -8, "south", 10)):
        for y in range(14, 14 + h):
            if T.g(x, y, z) in (None, "minecraft:air"):
                T.s(x, y, z, "vine[" + ",".join(f"{d}={'true' if d == face else 'false'}"
                                                for d in ("east", "north", "south", "up", "west")) + "]")


def conexiones(T):
    piezas.connect(T.t)


# ------------------------------------------------------------------ auditoría propia
def auditar(t):
    """Comprobaciones específicas: estado coherente de los circuitos y piezas clave en su sitio."""
    errs = []

    def at(x, y, z):
        return t.get(x + OX, y, z + OZ) or ""

    y = FEET["f2"]
    for yy in (y, y + 1):
        if "sticky_piston" not in at(-9, yy, -2) or "extended=true" not in at(-9, yy, -2):
            errs.append(f"pistón de la puerta secreta y={yy}")
        if "piston_head" not in at(-9, yy, -1) or "bookshelf" not in at(-9, yy, 0):
            errs.append(f"cabeza/estantería de la puerta secreta y={yy}")
    if "lit=true" not in at(-10, y + 1, -2):
        errs.append("antorcha de la puerta secreta apagada")
    wires = [p for p, (st, _) in t.blocks.items() if "redstone_wire" in st]
    if any("power=0" not in t.blocks[p][0] for p in wires):
        errs.append("polvo de redstone con potencia al colocar")
    if len(wires) != 9:
        errs.append(f"se esperaban 9 de polvo, hay {len(wires)}")
    # el polvo del estudio: 6 tramos, para que solo la señal 6 (hueco 6) llegue a la antorcha
    yb = FEET["B1"]
    if "iron_door" not in at(4, yb, 5) or "cauldron" not in at(-1, yb, 5):
        errs.append("puzle del caldero incompleto")
    if "tnt" not in at(0, 0, 11) or "pressure_plate" not in at(0, FEET["B2"], 11):
        errs.append("trampa de la losa incompleta")
    for z in range(-3, 4):
        if "tripwire[" not in at(-6, yb, z):
            errs.append(f"hilo interrumpido en z={z}")
    if not any(e[3]["id"] == "minecraft:evoker" for e in t.entities):
        errs.append("falta el guardián")
    return errs


# ------------------------------------------------------------------ construcción
def construir():
    T = Torre()
    terraza(T)
    sotanos(T)
    sotano1_detalle(T)
    sotano2_detalle(T)
    muros(T)
    ventanas(T)
    anexo(T)
    galeria(T)
    escalera(T)
    plantas(T)
    tejado(T)
    ruina(T)
    conexiones(T)
    # jigsaw de entrada, lo último (un fill posterior lo borraría)
    T.t.jigsaw(0 + OX, 13, -12 + OZ, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty",
               final_state="minecraft:polished_deepslate")
    return T.t


PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:deepslate_bricks", "probability": 0.12},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:cracked_deepslate_bricks"},
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": 0.12},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_stone_bricks"},
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": 0.09},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:cracked_stone_bricks"},
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:cobbled_deepslate", "probability": 0.10},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_cobblestone"},
]}]}


def build(reg):
    t = construir()
    open_stairwells(t)   # huecos de escalera cortos
    name = reg.add(t, "unica")
    errs = auditar(t)
    if errs:
        reg.warnings.extend(f"{name}: {e}" for e in errs)
    reg.pool(f"{NSP}/inicio", [(name, 1, "rigid", PROCESSORS)])


# ------------------------------------------------------------------ botín
def named(name, key, w, mods=()):
    return _named(name, w, KEY + key, TXT[key][0], mods=mods)


def ench(d):
    return {"type": "minecraft:set_enchantments", "enchantments": d}


def potion(pid, w, name=None):
    return _potion(pid, w, KEY + name if name else None, TXT[name][0] if name else None)


BOOKS = [item("book", 8, 1, 3), item("paper", 8, 2, 6), item("feather", 4, 1, 3), item("ink_sac", 4, 1, 2),
         item("writable_book", 2), item("candle", 4, 1, 3)]
ALQ = [item("glass_bottle", 10, 1, 4), item("nether_wart", 6, 1, 4), item("redstone", 6, 2, 6),
       item("glowstone_dust", 5, 1, 4), item("sugar", 6, 1, 4), item("spider_eye", 5, 1, 2),
       item("fermented_spider_eye", 2), item("gunpowder", 4, 1, 3), item("blaze_powder", 1),
       item("magma_cream", 2), item("rabbit_foot", 1), item("glistering_melon_slice", 2),
       potion("healing", 2), potion("swiftness", 2), potion("night_vision", 2)]

LOOT = {
    "vestibulo": t2(((2, 4), [item("bread", 8, 1, 3), item("apple", 6, 1, 3), item("torch", 6, 2, 6),
                              item("candle", 4, 1, 2), item("stick", 4, 2, 5), item("coal", 4, 1, 4), empty(6)]),
                    ((1, 2), [item("lantern", 2), item("paper", 4, 1, 3), item("iron_nugget", 4, 2, 6), empty(8)])),
    "biblioteca": t2(((2, 4), BOOKS + [empty(4)]),
                     ((1, 1), [item("book", 3, rand_ench=True), item("lapis_lazuli", 4, 1, 4), item("map", 2),
                               item("experience_bottle", 2, 1, 2), empty(8)])),
    "laboratorio": t2(((2, 5), ALQ),
                      ((1, 2), [item("brewing_stand", 1), item("cauldron", 1), item("ghast_tear", 1),
                                potion("strength", 1), potion("fire_resistance", 2), item("glass_bottle", 4, 2, 4)])),
    "encantamientos": t2(((2, 4), [item("lapis_lazuli", 10, 2, 6), item("book", 8, 1, 3), item("experience_bottle", 5, 1, 3),
                                   item("amethyst_shard", 5, 1, 3), item("candle", 3, 1, 2)]),
                         ((1, 1), [item("book", 5, rand_ench=True), item("iron_sword", 2, ench=(5, 12)),
                                   item("golden_helmet", 2, ench=(5, 12)), empty(6)])),
    "invernadero": t2(((2, 5), [item("bone_meal", 10, 2, 6), item("torchflower_seeds", 4, 1, 2), item("pitcher_pod", 3),
                                item("moss_block", 5, 1, 3), item("azalea", 4), item("flowering_azalea", 2),
                                item("glow_berries", 5, 1, 4), item("pumpkin_seeds", 4, 1, 3), item("melon_seeds", 4, 1, 3),
                                item("open_eyeblossom", 3, 1, 2), item("pale_hanging_moss", 3, 1, 3)]),
                        ((1, 1), [item("golden_carrot", 3, 1, 2), item("spore_blossom", 1), item("big_dripleaf", 2), empty(5)])),
    "dormitorio": t2(((2, 4), [item("bread", 6, 1, 3), item("candle", 4, 1, 2), item("purple_wool", 4, 1, 3),
                               item("book", 4, 1, 2), item("clock", 2), item("compass", 2), item("gold_nugget", 5, 2, 7)]),
                     ((1, 1), [item("name_tag", 3), item("emerald", 4, 1, 3), item("golden_apple", 1), empty(6)])),
    "observatorio": t2(((2, 4), [item("paper", 8, 1, 4), item("map", 4), item("compass", 3), item("amethyst_shard", 6, 1, 4),
                                 item("glow_ink_sac", 3, 1, 2), item("candle", 3, 1, 2)]),
                       ((1, 1), [item("spyglass", 3), item("recovery_compass", 1), item("emerald", 3, 1, 3), empty(5)])),
    "experimentos": t2(((2, 4), [item("rotten_flesh", 10, 2, 5), item("bone", 8, 1, 4), item("string", 6, 1, 3),
                                 item("glass_bottle", 5, 1, 3), item("spider_eye", 4, 1, 2), item("slime_ball", 3, 1, 2),
                                 item("redstone", 5, 2, 5), item("gunpowder", 4, 1, 3)]),
                       ((1, 2), [item("iron_ingot", 5, 1, 3), item("gold_ingot", 3, 1, 2), item("experience_bottle", 3, 1, 3),
                                 potion("weakness", 2), item("golden_carrot", 2), empty(6)])),
    "escondite": t2(((2, 4), [item("gold_ingot", 6, 1, 3), item("iron_ingot", 6, 2, 4), item("emerald", 6, 1, 4),
                              item("experience_bottle", 4, 2, 4), item("redstone", 4, 3, 8)]),
                    ((1, 2), [item("diamond", 2), item("book", 4, rand_ench=True), item("golden_apple", 2),
                              item("music_disc_13", 1), item("iron_pickaxe", 2, ench=(8, 15))])),
    "estudio": t2(((3, 5), BOOKS + [item("lapis_lazuli", 6, 2, 6), item("experience_bottle", 5, 2, 4), item("emerald", 4, 1, 3)]),
                  ((1, 2), [item("book", 6, rand_ench=True), item("diamond", 1), item("name_tag", 2),
                            item("music_disc_cat", 1), item("ender_pearl", 3, 1, 2), item("golden_apple", 2)])),
    "tesoro": t2(((3, 5), [item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 6), item("lapis_lazuli", 6, 3, 8),
                           item("amethyst_shard", 5, 2, 6), item("experience_bottle", 6, 2, 5), item("diamond", 2, 1, 2)]),
                 ((1, 2), [item("golden_apple", 3), item("book", 4, ench=(15, 25)), item("diamond_horse_armor", 1),
                           item("music_disc_mellohi", 1), item("ender_pearl", 3, 1, 3)])),
    "premium": {"type": "minecraft:chest", "pools": [
        # 90 % vistoso
        {"rolls": 1, "entries": [
            named("blaze_rod", "baculo", 14, [ench({"minecraft:knockback": 2})]),
            named("book", "grimorio", 14, [random_ench()]),
            named("leather_helmet", "capucha", 10, [ench({"minecraft:protection": 2, "minecraft:unbreaking": 1})]),
            named("spyglass", "catalejo", 10),
            named("clock", "reloj", 8),
            named("iron_sword", "daga", 8, [ench({"minecraft:sharpness": 2})]),
            named("golden_boots", "botas", 8, [ench({"minecraft:feather_falling": 3})]),
            item("vex_armor_trim_smithing_template", 8),
            item("music_disc_strad", 5), item("music_disc_far", 5),
            # 10 % algo más fuerte (sin romper la progresión)
            named("diamond_sword", "espada", 4, [ench({"minecraft:sharpness": 3, "minecraft:unbreaking": 2})]),
            named("diamond_chestplate", "coraza", 3, [ench({"minecraft:protection": 2})]),
            item("enchanted_golden_apple", 3)]},
        {"rolls": {"type": "minecraft:uniform", "min": 3, "max": 5}, "entries": [
            item("gold_ingot", 8, 2, 6), item("emerald", 8, 3, 7), item("lapis_lazuli", 6, 4, 10),
            item("experience_bottle", 6, 3, 6), item("amethyst_shard", 5, 3, 8), item("diamond", 3, 1, 2),
            potion("regeneration", 3, "elixir"), item("golden_apple", 3)]},
        {"rolls": {"type": "minecraft:uniform", "min": 1, "max": 2}, "solo_sin_lootr": True, "entries": [
            named("spyglass", "catalejo", 2), named("clock", "reloj", 2), item("vex_armor_trim_smithing_template", 2),
            item("diamond", 3, 1, 2), item("golden_apple", 3), item("music_disc_13", 1), item("emerald", 4, 2, 5)]},
    ]},
}
