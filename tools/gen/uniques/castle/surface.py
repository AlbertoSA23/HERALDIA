"""Castillo en superficie: foso, muralla con torres y adarve, puerta con rastrillo, patio de armas y torre del homenaje.
Coordenadas de la plantilla: x, z en 0..99 (norte z=0, la puerta mira al sur); y=5 es la capa de terreno, los pies a y=6."""
import random
from .util import Canvas, hidden_door
from .._common.pieces import circle, spiral_slabs, connect, chest as put_chest
from .._common import pieces

N = 100
G, L, W = 5, 6, 17          # capa de terreno, pies en el patio, pies en el adarve
SB, COB = "stone_bricks", "cobblestone"
LOOT = "heraldia:unicas/castillo/"
NEWEL = (40, 37)            # machón del caracol (baja a la mazmorra)
SPIRAL = dict(s0=-13, s1=22, phase=5)


def ring(x, z):
    return min(x, z, N - 1 - x, N - 1 - z)


def build(rnd=None):
    rnd = rnd or random.Random(1307)
    t = Canvas("unicas/castillo/castillo")
    meta = {"chests": [], "secret": {}, "spirals": [], "doors_open": []}

    def chest(x, y, z, f, table, kind="chest", water=False):
        put_chest(t.set, x, y, z, f, LOOT + table, kind, waterlogged=water)
        meta["chests"].append(((x, y, z), table))

    def hang(x, y, z, soul=False):
        t.set(x, y, z, ("soul_lantern" if soul else "lantern") + "[hanging=true,waterlogged=false]")

    # ------------------------------------------------------------ terreno, foso y muralla
    for x in range(N):
        for z in range(N):
            r = ring(x, z)
            t.set(x, 0, z, "stone")
            if r <= 3:
                t.fill(x, 1, z, x, 4, z, "dirt")
                t.set(x, G, z, "grass_block[snowy=false]")
                if r == 3:
                    t.fill(x, 1, z, x, G, z, SB)
                t.air(x, L, z, x, L + 1, z)
            elif r <= 9:
                t.set(x, 1, z, "gravel" if rnd.random() < 0.7 else "clay")
                t.fill(x, 2, z, x, 4, z, "water[level=0]")
                t.air(x, G, z, x, L + 1, z)
            elif r <= 12:
                t.fill(x, 1, z, x, 3, z, "mossy_cobblestone" if rnd.random() < 0.3 else COB)
                t.fill(x, 4, z, x, W - 1, z, SB)
                if r == 10:
                    t.set(x, W, z, SB)
                    if (x + z) % 2 == 0:
                        t.set(x, W + 1, z, SB)
                else:
                    t.air(x, W, z, x, W + 2, z)
            else:
                t.fill(x, 1, z, x, 4, z, "dirt")
                k = rnd.random()
                t.set(x, G, z, "coarse_dirt" if k < 0.08 else "grass_block[snowy=false]")
                t.air(x, L, z, x, L + 3, z)
    # faroles en el parapeto, cada 12 bloques
    for k in range(18, 82, 12):
        for x, z in ((k, 10), (k, 89), (10, k), (89, k)):
            if (x + z) % 2 == 1:
                t.set(x, W + 1, z, "lantern[hanging=false,waterlogged=false]")

    # ------------------------------------------------------------ patio: caminos, flores
    for z in range(46, 80):
        for x in range(48, 52):
            t.set(x, G, z, "dirt_path" if rnd.random() < 0.7 else "gravel")
    for x in range(42, 58):
        for z in range(56, 64):
            if abs(x - 49.5) + abs(z - 59.5) <= 9 and t.get(x, G, z) != "minecraft:dirt_path":
                t.set(x, G, z, "dirt_path" if rnd.random() < 0.5 else "gravel")
    flowers = ["poppy", "dandelion", "short_grass", "short_grass", "short_grass", "azure_bluet", "oxeye_daisy"]
    for _ in range(260):
        x, z = rnd.randint(14, 85), rnd.randint(47, 85)
        if t.get(x, G, z) == "minecraft:grass_block[snowy=false]" and t.get(x, L, z) == "minecraft:air":
            t.set(x, L, z, rnd.choice(flowers))

    # ------------------------------------------------------------ torres de esquina
    def tower(cx, cz, ix, iz, content=None, ruined=False):
        shell = circle(cx, cz, 5.5)
        inner = set(circle(cx, cz, 3.5))
        rim = [c for c in shell if (c[0] - cx) ** 2 + (c[1] - cz) ** 2 > 20.25]
        for x, z in shell:
            t.fill(x, 0, z, x, 24, z, SB)
        for x, z in rim:
            t.set(x, 25, z, SB)
            if (x + z) % 2 == 0:
                t.set(x, 26, z, SB)
        for x, z in inner:
            t.set(x, G, z, "spruce_planks")
            t.air(x, L, z, x, 15, z)
            t.set(x, 16, z, "spruce_planks")
            t.air(x, W, z, x, 23, z)
            t.air(x, 25, z, x, 27, z)

        def tunnel(x, z, dx, dz, y):
            while (x - cx) ** 2 + (z - cz) ** 2 <= 12.25:
                x, z = x + dx, z + dz
            last = None
            while (x - cx) ** 2 + (z - cz) ** 2 <= 30.25:
                t.air(x, y, z, x, y + 1, z)
                last = (x, z)
                x, z = x + dx, z + dz
            f = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]
            t.door(last[0], y, last[1], f)
        tunnel(cx + 2 * ix, cz + 2 * iz, ix, 0, L)
        tunnel(cx, cz + iz, ix, 0, W)
        tunnel(cx + ix, cz, 0, iz, W)
        lx = cx - 3 * ix
        lf = "east" if ix > 0 else "west"
        top = 16 if ruined else 24
        for y in range(L, top + 1):
            t.set(lx, y, cz, f"ladder[facing={lf},waterlogged=false]")
        hang(cx, 15, cz)
        hang(cx, 23, cz)
        for y in (10, 20):
            t.set(cx - 5 * ix, y, cz, "iron_bars")
            t.set(cx, y, cz - 5 * iz, "iron_bars")
        if ruined:
            for x, z in shell:
                h = 18 + (x * 7 + z * 13) % 5
                if (x - cx) ** 2 + (z - cz) ** 2 > 12.25:
                    for y in range(h, 27):
                        t.clear(x, y, z)
            for x, z in inner:
                for y in range(20, 28):
                    t.clear(x, y, z)
                if (x - cx) ** 2 + (z - cz) ** 2 <= 2:
                    t.set(x, 16, z, "air")
            t.clear(cx, 23, cz)
            t.clear(cx, 15, cz)
            for x, z in shell:
                if (x * 3 + z) % 4 == 0 and (x - cx) ** 2 + (z - cz) ** 2 > 20.25:
                    y = 18 + (x * 7 + z * 13) % 5 - 1
                    nx = x + (1 if x > cx else -1)
                    if t.is_free(nx, y, z):
                        t.set(nx, y, z, "vine[east=false,north=false,south=false,up=false,west=" +
                              ("true" if x > cx else "false") + "]" if x > cx else
                              "vine[east=true,north=false,south=false,up=false,west=false]")
            # escombros dentro, en la planta baja
            for (x, z) in [(cx + 1, cz - 1), (cx - 1, cz + 1), (cx, cz)]:
                t.set(x, L, z, rnd.choice(["cobblestone", "mossy_cobblestone", "gravel"]))
        if content:
            content(cx, cz, ix, iz)

    def tw_sw(cx, cz, ix, iz):
        chest(cx + 2, W, cz + 1, "west", "armeria")
        t.set(cx + 2, W, cz - 1, "barrel[facing=up,open=false]")
        chest(cx - 1, L, cz - 2, "south", "menor", "barrel")

    def tw_nw(cx, cz, ix, iz):
        chest(cx - 1, L, cz - 2, "south", "menor", "barrel")
        t.set(cx + 1, L, cz - 2, "barrel[facing=up,open=false]")
        t.set(cx - 2, W, cz + 1, "red_bed[facing=north,occupied=false,part=head]")
        t.set(cx - 2, W, cz + 2, "red_bed[facing=north,occupied=false,part=foot]")

    def tw_se(cx, cz, ix, iz):
        chest(cx + 1, W, cz + 2, "north", "armeria", "barrel")
        t.set(cx - 2, L, cz + 1, "fletching_table")

    tower(11, 11, 1, 1, tw_nw)
    tower(88, 11, -1, 1, ruined=True)
    tower(11, 88, 1, -1, tw_sw)
    tower(88, 88, -1, -1, tw_se)

    # ------------------------------------------------------------ bastiones a media muralla (este y oeste)
    for cx, wx, side in ((11, 12, 1), (88, 87, -1)):
        cz = 50
        shell = circle(cx, cz, 4.5)
        for x, z in shell:
            t.fill(x, 0, z, x, 22, z, SB)
            if (x - cx) ** 2 + (z - cz) ** 2 > 12.25:
                t.set(x, 23, z, SB)
                if (x + z) % 2 == 0:
                    t.set(x, 24, z, SB)
        for x, z in circle(cx, cz, 2.5):
            t.air(x, W, z, x, 21, z)
        for dz, f in ((-1, "north"), (1, "south")):
            z = cz + 3 * dz
            while (wx - cx) ** 2 + (z - cz) ** 2 <= 20.25:
                t.air(wx, W, z, wx, W + 1, z)
                last = z
                z += dz
            t.door(wx, W, last, f)
        chest(cx - side * 1, W, cz - 2 if side > 0 else cz + 2, "south" if side > 0 else "north", "menor", "barrel")
        hang(cx, 21, cz)
        t.set(cx - 4 * side, 19, cz, "iron_bars")

    # ------------------------------------------------------------ escaleras al adarve
    for k in range(11):
        t.fill(13, L, 30 + k, 13, L + k - 1, 30 + k, SB) if k else None
        t.set(13, L + k, 30 + k, "stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
        t.fill(86, L, 45 - k, 86, L + k - 1, 45 - k, SB) if k else None
        t.set(86, L + k, 45 - k, "stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")

    # ------------------------------------------------------------ puerta: barbacana, rastrillo y puente
    t.fill(42, 0, 80, 57, 22, 92, SB)
    t.air(48, L, 80, 51, 10, 92)
    for x in range(48, 52):
        for z in range(80, 93):
            t.set(x, G, z, "cobblestone" if (x + z) % 3 else "andesite")
    t.air(43, L, 81, 46, 10, 86)
    t.air(53, L, 81, 56, 10, 86)
    t.door(47, L, 84, "east")
    t.door(52, L, 84, "west")
    t.air(43, W, 81, 56, 21, 91)
    t.door(42, W, 87, "west")
    t.door(57, W, 87, "east")
    for x in range(48, 52):
        e = "true" if x < 51 else "false"
        w = "true" if x > 48 else "false"
        t.fill(x, 11, 90, x, 15, 90, f"iron_bars[east={e},north=false,south=false,waterlogged=false,west={w}]")
        t.fill(x, 16, 90, x, 19, 90, "iron_chain[axis=y,waterlogged=false]")
    t.fill(47, 20, 90, 52, 20, 90, "stripped_spruce_log[axis=x]")
    t.fill(47, W, 90, 47, 19, 90, "spruce_log[axis=y]")
    t.fill(52, W, 90, 52, 19, 90, "spruce_log[axis=y]")
    for x in (48, 51):
        f = "east" if x == 48 else "west"
        t.set(x, 10, 92, f"stone_brick_stairs[facing={f},half=top,shape=straight,waterlogged=false]")
    for y in range(W, 23):
        t.set(43, y, 82, "ladder[facing=east,waterlogged=false]")
    for x in range(42, 58):
        for z in range(80, 93):
            if x in (42, 57) or z in (80, 92):
                t.set(x, 23, z, SB)
                if (x + z) % 2 == 0:
                    t.set(x, 24, z, SB)
    t.clear(43, 23, 80)
    for cx in (42, 57):
        for x, z in circle(cx, 91, 3.5):
            t.fill(x, 0, z, x, 25, z, SB)
            if (x - cx) ** 2 + (z - 91) ** 2 > 4.5:
                t.set(x, 26, z, SB)
                if (x + z) % 2 == 0:
                    t.set(x, 27, z, SB)
    for x in (47, 52):
        t.set(x, 14, 93, "red_wall_banner[facing=south]")
        t.set(x, 14, 79, "red_wall_banner[facing=north]")
    for x, z in ((44, 83), (54, 83), (50, 85), (50, 89)):
        hang(x, 10, z)
    hang(46, 21, 84)
    hang(53, 21, 84)
    # cuerpo de guardia (oeste) y almacén (este)
    chest(43, L, 81, "east", "armeria")
    t.set(46, L, 81, "barrel[facing=up,open=false]")
    t.set(44, L, 86, "spruce_slab[type=top,waterlogged=false]")
    t.set(45, L, 86, "spruce_slab[type=top,waterlogged=false]")
    t.set(44, L, 85, "spruce_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    chest(56, L, 81, "west", "menor", "barrel")
    chest(56, L, 82, "west", "cocina", "barrel")
    t.set(53, L, 81, "hay_block[axis=y]")
    t.set(53, L, 86, "barrel[facing=up,open=false]")
    # sala del torno
    chest(56, W, 81, "west", "armeria")
    for z in (83, 85):
        t.set(44, W, z, "red_bed[facing=west,occupied=false,part=head]")
        t.set(45, W, z, "red_bed[facing=west,occupied=false,part=foot]")
    t.set(55, W, 86, "barrel[facing=up,open=false]")
    # puente levadizo tendido
    for z in range(93, 96):
        for x in range(48, 52):
            t.set(x, G, z, "spruce_planks")
        for x in (47, 52):
            t.set(x, G, z, "stripped_spruce_log[axis=z]")
            t.set(x, L, z, "spruce_fence[east=false,north=true,south=true,waterlogged=false,west=false]")
    for x in (47, 52):
        t.fill(x, 1, 94, x, 4, 94, SB)
    t.set(51, G, 94, "water[level=0]")          # tablón perdido
    for z in range(97, 100):
        for x in range(48, 52):
            t.set(x, G, z, "dirt_path")

    # ------------------------------------------------------------ torre del homenaje
    keep(t, chest, hang, meta)
    # ------------------------------------------------------------ capilla, herrería, caballerizas, pozo, huerto, liza
    chapel(t, chest, hang)
    smithy(t, chest, hang)
    stables(t, chest, hang, rnd)
    # pozo con cofre en el fondo
    t.fill(48, 1, 58, 51, G, 61, "cobblestone")
    t.fill(48, L, 58, 51, L, 61, "cobblestone_slab[type=bottom,waterlogged=false]")
    t.fill(49, 1, 59, 50, G, 60, "water[level=0]")
    t.air(49, L, 59, 50, L, 60)
    chest(49, 1, 59, "south", "oculto", water=True)
    for x, z in ((48, 58), (51, 58), (48, 61), (51, 61)):
        t.fill(x, L + 1, z, x, L + 2, z, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
    t.fill(48, L + 3, 58, 51, L + 3, 61, "spruce_slab[type=bottom,waterlogged=false]")
    t.set(49, L + 2, 59, "iron_chain[axis=y,waterlogged=false]")
    t.set(49, L + 1, 59, "lantern[hanging=true,waterlogged=false]")
    # huerto de la cocina
    for x in range(16, 28):
        for z in range(20, 35):
            edge = x in (16, 27) or z in (20, 34)
            if edge:
                gate = (z == 34 and x == 21)
                t.set(x, L, z, "spruce_fence_gate[facing=south,in_wall=false,open=false,powered=false]" if gate
                      else "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
            elif z == 27:
                t.set(x, G, z, "water[level=0]")
            else:
                t.set(x, G, z, "farmland[moisture=7]")
                crop = ["wheat[age=7]", "carrots[age=7]", "beetroots[age=3]", "potatoes[age=7]"][(z - 21) // 3 % 4]
                t.set(x, L, z, crop)
    t.set(17, G, 21, "dirt")
    t.set(17, L, 21, "composter[level=4]")
    # liza: dianas y estafermo
    for x in (30, 34, 38):
        t.set(x, L, 64, "hay_block[axis=y]")
        t.set(x, L + 1, 64, "target[power=0]")
    for x in (32, 36):
        t.set(x, L, 72, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
        t.set(x, L + 1, 72, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
        t.set(x, L + 2, 72, "carved_pumpkin[facing=south]")
    t.set(28, L, 76, "hay_block[axis=x]")
    chest(29, L, 76, "north", "armeria", "barrel")
    # farolas del patio
    for x, z in ((46, 50), (53, 50), (46, 70), (53, 70), (30, 50), (69, 50), (30, 78), (69, 78)):
        t.set(x, L, z, "spruce_fence[east=false,north=false,south=false,waterlogged=false,west=false]")
        t.set(x, L + 1, z, "lantern[hanging=false,waterlogged=false]")
    # escombros al pie de la torre en ruinas
    for _ in range(26):
        x, z = rnd.randint(76, 86), rnd.randint(15, 20)
        if t.get(x, L, z) in ("minecraft:air", None) or "grass" in (t.get(x, L, z) or ""):
            t.set(x, L, z, rnd.choice(["cobblestone", "mossy_cobblestone", "stone_brick_slab[type=bottom,waterlogged=false]",
                                       "gravel", "cracked_stone_bricks"]))
    # parapeto norte desmochado junto a la torre en ruinas
    for x in range(68, 80):
        t.clear(x, W + 1, 10)
        if x % 3 == 0:
            t.clear(x, W, 10)
    connect(t)
    meta["entrance"] = (50, L, 99)
    return t, meta


def window(t, xs, ys, zs, pane="glass_pane", axis="x"):
    for x in xs:
        for y in ys:
            for z in zs:
                t.set(x, y, z, "air")
    mid = zs[len(zs) // 2] if axis == "x" else xs[len(xs) // 2]
    for a in (xs if axis == "x" else zs):
        for y in ys:
            if axis == "x":
                t.set(a, y, mid, pane + "[east=true,north=false,south=false,waterlogged=false,west=true]")
            else:
                t.set(mid, y, a, pane + "[east=false,north=true,south=true,waterlogged=false,west=false]")


def keep(t, chest, hang, meta):
    t.fill(30, 0, 14, 69, 21, 45, SB)
    for x0, z0 in ((26, 13), (67, 13), (26, 40), (67, 40)):
        t.fill(x0, 0, z0, x0 + 6, 26, z0 + 6, SB)
        for x in range(x0, x0 + 7):
            for z in range(z0, z0 + 7):
                if x in (x0, x0 + 6) or z in (z0, z0 + 6):
                    if (x + z) % 2 == 0:
                        t.set(x, 27, z, SB)
    for x in range(30, 70):
        for z in range(14, 46):
            if x in (30, 69) or z in (14, 45):
                t.set(x, 22, z, SB)
                if (x + z) % 2 == 0:
                    t.set(x, 23, z, SB)
    F1, F2 = 15, 22                       # pies en la planta alta y en la azotea
    # planta baja
    t.air(33, L, 17, 42, 13, 27)          # cocina
    t.air(33, L, 29, 42, 13, 33)          # despensa
    t.air(33, L, 35, 37, 13, 42)          # bodega
    t.air(38, L, 40, 42, 13, 42)
    t.air(44, L, 17, 57, 20, 42)          # gran salón (doble altura)
    t.air(59, L, 17, 66, 13, 28)          # armería
    t.air(59, L, 30, 66, 13, 42)          # cuartel
    for x in range(33, 67):
        for z in range(17, 43):
            t.set(x, G, z, "polished_andesite" if 44 <= x <= 57 else ("spruce_planks" if x > 58 else "stone_bricks"))
    # planta alta
    t.air(33, F1, 17, 42, 20, 23)         # estudio
    t.air(33, F1, 25, 42, 20, 33)         # biblioteca
    t.air(33, F1, 35, 37, 20, 42)         # antecámara
    t.air(38, F1, 40, 42, 20, 42)
    t.air(59, F1, 17, 66, 20, 29)         # alcoba del señor
    t.air(59, F1, 31, 66, 20, 42)         # solana
    for x in list(range(33, 43)) + list(range(59, 67)):
        for z in range(17, 43):
            if t.get(x, F1, z) == "minecraft:air":
                t.set(x, F1 - 1, z, "spruce_planks" if x > 58 else "dark_oak_planks")
    # tribuna sobre el salón y escalera principal
    t.fill(44, 14, 17, 57, 14, 21, "spruce_planks")
    for x in (47, 51, 54):
        t.fill(x, L, 21, x, 13, 21, "spruce_log[axis=y]")
    t.fill(46, F1, 21, 57, F1, 21, "spruce_fence[east=true,north=false,south=false,waterlogged=false,west=true]")
    for k in range(9):
        for x in (44, 45):
            if k:
                t.fill(x, L, 30 - k, x, L + k - 1, 30 - k, SB)
            t.set(x, L + k, 30 - k, "stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    # puertas
    t.door(43, L, 19, "east")
    t.door(37, L, 28, "south")
    t.door(35, L, 34, "south")
    t.door(58, L, 22, "west")
    t.door(58, L, 36, "west")
    t.door(43, F1, 19, "east")
    t.door(58, F1, 19, "west")
    t.door(38, F1, 24, "south")
    t.door(35, F1, 34, "south")
    t.door(62, F1, 30, "south")
    t.air(50, L, 43, 51, 9, 45)
    pieces.double_door(t.set, 50, L, 45, "south", "east", "dark_oak_door")
    for x in range(50, 52):
        for z in range(43, 46):
            t.set(x, G, z, "polished_andesite")
    # caracol: de la mazmorra (-13) a la azotea (22)
    t.fill(38, 22, 35, 42, 24, 39, SB)
    t.fill(38, 25, 35, 42, 25, 39, "stone_brick_slab[type=bottom,waterlogged=false]")
    for x in range(39, 42):
        for z in range(36, 39):
            t.air(x, 0, z, x, 24, z)
    t.fill(NEWEL[0], 1, NEWEL[1], NEWEL[0], 24, NEWEL[1], SB)
    put = lambda x, y, z, s: t.set(x, y, z, s) if y >= 0 else meta.setdefault("below", []).append((x, y, z, s))
    meta["spirals"].append(spiral_slabs(put, NEWEL[0], NEWEL[1], SPIRAL["s0"], SPIRAL["s1"], SPIRAL["phase"], "stone_brick_slab"))
    t.opening(42, L, 37)
    t.opening(43, L, 37)
    t.opening(40, F1, 39)
    t.opening(42, F2, 37)
    for y in (9, 18):
        t.set(38, y, 37, "iron_bars")
    t.jigsaw(NEWEL[0], 0, NEWEL[1], "down_south", "unicas/castillo/bajada", "unicas/castillo/subida",
             "unicas/castillo/mazmorra", final_state=SB)
    # ventanas
    for xs in ((46, 47), (50, 51), (54, 55)):
        window(t, xs, range(9, 19), (14, 15, 16))
        window(t, xs, range(12, 19), (43, 44, 45))
    window(t, (37, 38), range(8, 11), (14, 15, 16))
    window(t, (37, 38), range(16, 19), (14, 15, 16))
    window(t, (61, 62), range(8, 11), (14, 15, 16))
    window(t, (61, 62), range(16, 19), (14, 15, 16))
    for zs in ((20, 21), (25, 26)):
        window(t, (30, 31, 32), range(8, 11), zs, axis="z")
    for zs in ((21, 22), (34, 35), (39, 40)):
        window(t, (67, 68, 69), range(8, 11), zs, axis="z")
        window(t, (67, 68, 69), range(16, 19), zs, axis="z")
    window(t, (61, 62), range(8, 11), (43, 44, 45))
    window(t, (61, 62), range(16, 19), (43, 44, 45))
    # pasadizo en el grueso del muro oeste y gabinete secreto en el torreón SO
    t.air(31, F1, 17, 31, F1 + 1, 40)
    t.air(28, F1, 41, 31, 19, 44)
    for z in (20, 26, 32, 38):
        t.set(30, F1 + 1, z, "iron_bars")
    for z in (23, 35):
        t.set(31, F1 + 1, z, "wall_torch[facing=east]")
    hang(29, 19, 42)
    chest(28, F1, 44, "north", "oculto")
    meta["hidden_chest"] = (28, F1, 44)
    t.set(28, F1, 41, "lectern[facing=east,has_book=false,powered=false]")
    t.set(30, F1, 44, "barrel[facing=up,open=false]")
    t.set(31, F1, 44, "candle[candles=3,lit=false,waterlogged=false]")
    # estudio: pared de librerías y puerta secreta (palanca en el rincón noroeste)
    t.fill(32, F1, 17, 32, 18, 23, "bookshelf")
    info = hidden_door(t.set, 33, 17, F1, -1, "bookshelf")
    meta["secret"]["estudio"] = info
    chest(42, F1, 17, "west", "aposentos")
    t.set(42, F1, 22, "lectern[facing=west,has_book=false,powered=false]")
    t.fill(38, F1, 20, 40, F1, 20, "dark_oak_slab[type=top,waterlogged=false]")
    t.set(39, F1, 21, "dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    t.set(38, F1 + 1, 20, "candle[candles=2,lit=false,waterlogged=false]")
    hang(37, 20, 20)
    t.set(36, F1, 23, "red_carpet")
    # biblioteca
    t.fill(32, F1, 25, 32, 18, 33, "bookshelf")
    t.fill(43, F1, 25, 43, 18, 33, "bookshelf")
    t.fill(37, F1, 28, 38, F1, 30, "spruce_slab[type=top,waterlogged=false]")
    for z in (28, 30):
        t.set(36, F1, z, "spruce_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
        t.set(39, F1, z, "spruce_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    chest(42, F1, 33, "west", "aposentos", "barrel")
    hang(37, 20, 27)
    hang(37, 20, 31)
    # antecámara
    for x in range(33, 38):
        t.set(x, F1, 38, "red_carpet")
    t.set(33, F1, 42, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    t.set(33, F1 + 2, 37, "red_wall_banner[facing=east]")
    hang(35, 20, 40)
    # alcoba del señor y solana
    for x in (62, 63):
        t.set(x, F1, 17, "red_bed[facing=north,occupied=false,part=head]")
        t.set(x, F1, 18, "red_bed[facing=north,occupied=false,part=foot]")
    chest(59, F1, 17, "east", "aposentos")
    t.set(66, F1, 17, "barrel[facing=up,open=false]")
    for x in range(61, 65):
        for z in range(20, 25):
            t.set(x, F1, z, "red_carpet")
    t.set(66, F1, 28, "lectern[facing=west,has_book=false,powered=false]")
    hang(62, 20, 23)
    t.set(59, F1, 42, "loom[facing=east]")
    t.set(66, F1, 42, "bookshelf")
    t.set(66, F1 + 1, 42, "potted_red_tulip")
    t.set(60, F1, 36, "spruce_slab[type=top,waterlogged=false]")
    t.set(59, F1, 36, "spruce_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
    t.set(61, F1, 36, "spruce_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    hang(62, 20, 36)
    # cocina
    t.set(33, L, 18, "smoker[facing=east,lit=false]")
    t.set(33, L, 19, "furnace[facing=east,lit=false]")
    t.set(33, L, 20, "smoker[facing=east,lit=false]")
    t.set(33, L, 23, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    t.fill(33, L, 22, 33, L + 1, 22, "bricks")
    t.fill(33, L, 24, 33, L + 1, 24, "bricks")
    t.fill(33, L + 2, 22, 33, 13, 24, "bricks")
    t.set(33, L, 26, "water_cauldron[level=3]")
    chest(42, L, 17, "west", "cocina")
    chest(42, L, 26, "west", "cocina", "barrel")
    t.set(42, L, 27, "barrel[facing=up,open=false]")
    t.set(42, L, 24, "crafting_table")
    t.fill(37, L, 21, 38, L, 24, "spruce_slab[type=top,waterlogged=false]")
    hang(37, 13, 19)
    hang(37, 13, 25)
    # despensa y bodega
    for z in range(29, 34):
        t.set(33, L, z, "barrel[facing=east,open=false]")
    chest(33, L, 31, "east", "cocina", "barrel")
    t.set(42, L, 29, "hay_block[axis=y]")
    t.set(42, L, 33, "hay_block[axis=y]")
    hang(37, 13, 31)
    for z in range(35, 42):
        t.set(33, L, z, "barrel[facing=east,open=false]")
        t.set(33, L + 1, z, "barrel[facing=east,open=false]")
    chest(37, L, 42, "north", "cocina", "barrel")
    t.set(36, L, 35, "cobweb")
    t.set(33, 13, 42, "cobweb")
    hang(35, 13, 38)
    # gran salón
    t.fill(50, L, 26, 51, L, 38, "dark_oak_slab[type=top,waterlogged=false]")
    for z in range(26, 39, 2):
        t.set(49, L, z, "dark_oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
        t.set(52, L, z, "dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]")
    t.fill(47, L, 19, 54, L, 19, "dark_oak_slab[type=top,waterlogged=false]")
    for x in range(47, 55):
        t.set(x, L, 18, "dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    t.fill(50, L, 39, 51, L, 42, "red_carpet")
    t.set(57, L, 33, "campfire[facing=west,lit=true,signal_fire=false,waterlogged=false]")
    t.fill(57, L, 32, 57, L + 1, 32, "bricks")
    t.fill(57, L, 34, 57, L + 1, 34, "bricks")
    t.fill(57, L + 2, 32, 57, 20, 34, "bricks")
    t.fill(57, 21, 33, 57, 23, 33, "bricks")
    for z in (34, 38, 41):
        t.set(44, 12, z, "red_wall_banner[facing=east]")
    for z in (25, 29, 38):
        t.set(57, 12, z, "red_wall_banner[facing=west]")
    for z in (27, 35):
        t.fill(50, 16, z, 50, 20, z, "iron_chain[axis=y,waterlogged=false]")
        hang(50, 15, z)
    hang(49, 13, 19)
    hang(53, 13, 19)
    t.set(56, F1, 17, "note_block[instrument=harp,note=0,powered=false]")
    # armería y cuartel
    chest(66, L, 17, "west", "armeria")
    chest(66, L, 28, "west", "armeria")
    t.set(59, L, 17, "fletching_table")
    t.set(59, L, 24, "grindstone[face=floor,facing=east]")
    t.set(66, L, 22, "smithing_table")
    for z in range(18, 28, 3):
        t.set(66, L, z, "barrel[facing=west,open=false]") if t.get(66, L, z) == "minecraft:air" else None
    hang(62, 13, 21)
    hang(62, 13, 26)
    for z in (31, 33, 39, 41):
        t.set(66, L, z, "red_bed[facing=east,occupied=false,part=head]")
        t.set(65, L, z, "red_bed[facing=east,occupied=false,part=foot]")
    chest(59, L, 42, "east", "menor")
    t.set(59, L, 31, "barrel[facing=up,open=false]")
    hang(62, 13, 33)
    hang(62, 13, 39)


def chapel(t, chest, hang):
    x0, x1, z0, z1 = 72, 85, 21, 33
    t.fill(x0, 0, z0, x1, 12, z1, SB)
    t.air(x0 + 1, L, z0 + 1, x1 - 1, 12, z1 - 1)
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            t.set(x, G, z, "polished_andesite")
    for z in range(z0, z1 + 1):
        d = abs(z - 27)
        y = 19 - d
        for x in range(x0, x1 + 1):
            if d == 0:
                t.set(x, y, z, "deepslate_tile_slab[type=bottom,waterlogged=false]")
            else:
                f = "south" if z < 27 else "north"
                t.set(x, y, z, f"deepslate_tile_stairs[facing={f},half=bottom,shape=straight,waterlogged=false]")
            if x in (x0, x1):
                t.fill(x, 13, z, x, y - 1, z, SB)
            elif d < 6:
                t.air(x, 13, z, x, y - 1, z)
    t.door(x0, L, 27, "west")
    for x in (75, 78, 81):
        for z in (z0, z1):
            for y in range(7, 11):
                t.set(x, y, z, "red_stained_glass_pane[east=false,north=false,south=false,waterlogged=false,west=false]"
                      if x == 78 else "blue_stained_glass_pane[east=false,north=false,south=false,waterlogged=false,west=false]")
    t.set(75, 9, z0, "air")                 # vidriera rota
    for z in (26, 27, 28):
        for y in range(7, 12):
            t.set(x1, y, z, "yellow_stained_glass_pane[east=false,north=true,south=true,waterlogged=false,west=false]")
    for z in (26, 27, 28):
        t.set(83, L, z, "chiseled_stone_bricks")
        t.set(83, L + 1, z, "candle[candles=3,lit=true,waterlogged=false]")
    t.set(81, L, 27, "lectern[facing=west,has_book=false,powered=false]")
    for x in range(74, 80, 2):
        for z in list(range(23, 26)) + list(range(29, 32)):
            t.set(x, L, z, "spruce_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]")
    chest(84, L, 22, "west", "capilla")
    t.set(84, L, 32, "barrel[facing=up,open=false]")
    for z in (22, 32):
        t.set(83, 9, z, "red_wall_banner[facing=" + ("south" if z == 22 else "north") + "]")
    for x in (76, 80):
        t.fill(x, 15, 27, x, 18, 27, "iron_chain[axis=y,waterlogged=false]")
        hang(x, 14, 27)
    t.set(73, 10, 27, "red_wall_banner[facing=east]")


def smithy(t, chest, hang):
    x0, x1, z0, z1 = 75, 86, 62, 74
    t.fill(x0, 0, z0, x1, 4, z1, "stone")
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.set(x, G, z, "cobblestone" if (x + z) % 4 else "gravel")
    t.fill(x1, L, z0, x1, 10, z1, SB)
    t.fill(x0 + 1, L, z0, x1, 10, z0, SB)
    t.fill(x0 + 1, L, z1, x1, 10, z1, SB)
    t.air(x0, L, z0 + 1, x1 - 1, 10, z1 - 1)
    for z in (z0, 66, 70, z1):
        t.fill(x0, L, z, x0, 10, z, "spruce_log[axis=y]")
    t.fill(x0, 11, z0, x1, 11, z1, "spruce_slab[type=bottom,waterlogged=false]")
    t.fill(x0, 11, z0, x0, 11, z1, "stripped_spruce_log[axis=z]")
    t.set(85, L, 64, "lava_cauldron")
    t.set(85, L, 65, "blast_furnace[facing=west,lit=false]")
    t.set(85, L, 66, "furnace[facing=west,lit=false]")
    t.fill(85, L + 1, 64, 85, 10, 66, "bricks")
    t.fill(85, 11, 65, 85, 14, 65, "bricks")
    t.set(80, L, 67, "anvil[facing=north]")
    t.set(80, L, 71, "grindstone[face=floor,facing=north]")
    t.set(85, L, 69, "smithing_table")
    t.set(85, L, 71, "water_cauldron[level=3]")
    chest(85, L, 73, "west", "herreria")
    t.set(85, L, 72, "barrel[facing=up,open=false]")
    hang(80, 10, 64)
    hang(80, 10, 72)


def stables(t, chest, hang, rnd):
    x0, x1, z0, z1 = 13, 24, 54, 76
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.set(x, G, z, "coarse_dirt" if rnd.random() < 0.5 else "packed_mud")
    t.fill(x0, L, z0, x1, 10, z0, "spruce_planks")
    t.fill(x0, L, z1, x1, 10, z1, "spruce_planks")
    t.fill(x1, L, z0, x1, 10, z1, "spruce_planks")
    for z in (z0, 62, 68, z1):
        t.fill(x1, L, z, x1, 10, z, "spruce_log[axis=y]")
    t.air(x0, L, z0 + 1, x1 - 1, 10, z1 - 1)
    for z in (60, 61, 70, 71):
        t.air(x1, L, z, x1, L + 2, z)
    t.fill(x0, 11, z0, x1, 11, z1, "dark_oak_slab[type=bottom,waterlogged=false]")
    t.fill(x1, 11, z0, x1, 11, z1, "stripped_dark_oak_log[axis=z]")
    for zs in range(55, 75, 4):
        for z in (zs + 3,):
            if z < z1:
                t.fill(x0, L, z, 17, L, z, "spruce_fence[east=true,north=false,south=false,waterlogged=false,west=true]")
        t.set(x0, L, zs, "hay_block[axis=y]")
        t.set(x0, L, zs + 2, "water_cauldron[level=3]")
        t.set(17, L, zs, "spruce_fence[east=false,north=false,south=true,waterlogged=false,west=false]")
        t.set(17, L, zs + 1, "spruce_fence_gate[facing=east,in_wall=false,open=false,powered=false]")
        t.set(17, L, zs + 2, "spruce_fence[east=false,north=true,south=false,waterlogged=false,west=false]")
    chest(23, L, 55, "west", "establo")
    t.set(23, L, 56, "barrel[facing=up,open=false]")
    t.set(23, L, 75, "hay_block[axis=y]")
    t.set(23, L + 1, 75, "hay_block[axis=y]")
    hang(20, 10, 58)
    hang(20, 10, 73)
    # tejado hundido
    for x in range(18, 25):
        for z in range(65, 70):
            if not (x == 18 and z in (65, 69)):
                t.set(x, 11, z, "air")
    for x, z in ((19, 64), (21, 70), (22, 64)):
        t.set(x, 10, z, "cobweb")
    t.set(21, L, 66, "stripped_dark_oak_log[axis=x]")
    t.set(22, L, 66, "stripped_dark_oak_log[axis=x]")
