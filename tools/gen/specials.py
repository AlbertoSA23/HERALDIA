"""Edificios especiales: iglesia/templo, cementerio, ayuntamiento, mercado, herrería, taberna,
posada, biblioteca, granja, molino, puerto."""
import math
from core import Template, nsid, villager, animal
from themes import roofset
from build import *
from houses import bed_slot, villager_pool, Room, LOOT
from streets import golem_slot, P

L = lambda k: f"heraldia:cofres/{k}"


def entrance(t, th, x):
    t.jigsaw(x, 0, 0, "north_up", "heraldia:entrance", "heraldia:side", "minecraft:empty",
             final_state=stairs(th["trim"], "south"))


def staff(t, th, x, y, z, prof, final=None):
    """Aldeano con oficio de pie en su puesto (sin cama): el jigsaw va en el bloque del suelo."""
    t.jigsaw(x, y, z, "up_south", "heraldia:slot", "heraldia:bottom", nsid(f"villagers/{th['vtype']}/nobed_{prof}"),
             final_state=final or th["floor"], joint="aligned")
    t.set(x, y + 1, z, "air"); t.set(x, y + 2, z, "air")


def shell(t, th, x0, z0, x1, z1, fy, H, roof=None, style=None, along=None, gable_fill=None, ceiling=True):
    """Caja con muros, suelo, aire interior y tejado. Devuelve cota superior del tejado."""
    t.fill(x0, fy, z0, x1, fy, z1, log(th["found"], "y"))
    t.fill(x0 + 1, fy, z0 + 1, x1 - 1, fy, z1 - 1, th["floor"])
    rect_walls(t, th, x0, z0, x1, z1, fy, H, style=style)
    t.air(x0 + 1, fy + 1, z0 + 1, x1 - 1, fy + H, z1 - 1)
    kind = roof or th["roof_type"]
    if kind == "cone":
        kind = "hip"
    if kind == "none":
        return fy + H
    if kind not in ("flat",) and ceiling:
        t.fill(x0 + 1, fy + H + 1, z0 + 1, x1 - 1, fy + H + 1, z1 - 1, th["planks"])
    if kind in ("gable", "steep"):
        top = gable_roof(t, th, x0, z0, x1, z1, fy + H + 1, along=along or ("x" if x1 - x0 >= z1 - z0 else "z"),
                         steep=(kind == "steep"), gable_fill=gable_fill)
    else:
        top = roof_for(t, th, x0, z0, x1, z1, fy + H + 1, kind=kind)
    t.fill(x0 + 1, fy + H + 1, z0 + 1, x1 - 1, top, z1 - 1, "air", keep=True)
    return top


def all_windows(t, th, x0, z0, x1, z1, y, rng, skip=(), tall=False, pane=None, spacing=3):
    for side in ("north", "south", "west", "east"):
        windows_on_wall(t, th, x0, z0, x1, z1, side, y, rng, skip=skip, tall=tall, pane=pane, spacing=spacing)


def chandelier(t, th, x, y, z):
    t.set(x, y, z, "iron_chain[axis=y]")
    t.set(x, y - 1, z, lantern(th, True))


def stone_of(th):
    f = th["found"]
    return f if ("log" not in f and "bamboo" not in f) else "stone_bricks"


# ======================================================================= IGLESIA / TEMPLO
def church(th, rng, name):
    style = th["church"]
    if style == "pyramid":
        return pyramid_temple(th, rng, name)
    if style == "pagoda":
        return pagoda_temple(th, rng, name)
    t = Template(name)
    stone = style in ("romanesque", "gothic", "domed")
    W = 11 if style != "chapel" else 9
    D = 21 if style != "chapel" else 17
    H = {"romanesque": 8, "gothic": 10, "chapel": 6, "domed": 8, "stave": 7, "onion": 7}[style]
    cx = W // 2
    tz0, tw = 2, 5                         # torre delantera
    nz0 = tz0 + 3
    nz1 = nz0 + D - 1
    entrance(t, th, cx)
    t.fill(cx - 1, 0, 1, cx + 1, 0, 1, stone_of(th))
    nave_style = "stone_base" if stone else th["wall_style"]
    nth = dict(th)
    if stone:
        w = th["wall"]
        ok = any(k in w for k in ("stone", "brick", "terracotta", "calcite", "concrete", "mud", "tuff"))
        nth["wall"] = w if ok else "stone_bricks"
        nth["wall2"] = stone_of(th)
    roofk = "flat" if style == "domed" else ("steep" if style in ("gothic", "stave") else "gable")
    top = shell(t, nth, 0, nz0, W - 1, nz1, 0, H, roof=roofk, style=nave_style, along="z", ceiling=False)
    if style == "gothic":
        for z in range(nz0 + 2, nz1, 4):
            for x, f in ((-1, "east"), (W, "west")):
                for y in range(0, H - 1):
                    t.set(x, y, z, nth["wall2"])
                t.set(x, H - 1, z, stairs(th["trim"], f))
    # vidrieras altas, simétricas, y rosetón tras el altar
    gl = f"{th['church_glass']}_stained_glass_pane"
    for z in range(nz0 + 4, nz1 - 2, 3):
        for x in (0, W - 1):
            for y in range(3, 3 + (4 if style == "gothic" else 3)):
                t.set(x, y, z, gl)
    for y in range(4, H - 1):
        t.set(cx, y, nz1, gl)
    t.set(cx - 1, H - 3, nz1, gl); t.set(cx + 1, H - 3, nz1, gl)
    # torre
    tx0 = cx - 2
    th_h = H + 11
    twall = (nth["wall"] if style == "domed" else nth["wall2"]) if stone else th["log"]
    for y in range(0, th_h + 1):
        for x in range(tx0, tx0 + tw):
            for z in range(tz0, tz0 + tw):
                edge = x in (tx0, tx0 + tw - 1) or z in (tz0, tz0 + tw - 1)
                if y == 0:
                    t.set(x, y, z, stone_of(th))
                elif edge:
                    t.set(x, y, z, twall if stone else log(twall, "y"))
                else:
                    t.set(x, y, z, "air")
    # arco de paso torre -> nave (3 de alto)
    for y in range(1, 4):
        t.set(cx, y, tz0 + tw - 1, "air")
    door(t, cx, 1, tz0, th["door"], "north")
    # campanario: forjado, huecos y campana colgada de una viga
    by = th_h - 2
    t.fill(tx0 + 1, by - 2, tz0 + 1, tx0 + 3, by - 2, tz0 + 3, th["planks"])
    for (x, z) in ((cx, tz0), (cx, tz0 + tw - 1), (tx0, tz0 + 2), (tx0 + tw - 1, tz0 + 2)):
        t.set(x, by, z, "air"); t.set(x, by - 1, z, "air")
    for x in range(tx0 + 1, tx0 + 4):
        t.set(x, by + 1, tz0 + 2, log(th["log"], "x"))
    t.set(cx, by, tz0 + 2, "bell[attachment=ceiling,facing=north]")
    for y in range(1, by - 1):
        t.set(tx0 + 1, y, tz0 + 3, "ladder[facing=north]")
    # remate
    cap = th["tower_cap"]
    ty = th_h + 1
    if cap == "spire":
        t.fill(tx0, ty - 1, tz0, tx0 + tw - 1, ty - 1, tz0 + tw - 1, th["roof_full"])
        sy = spire(t, cx, tz0 + 2, ty, 2, th["roof_stairs"], th["roof_full"])
        t.set(cx, sy, tz0 + 2, "lightning_rod[facing=up]")
    elif cap == "pyramid":
        hip_roof(t, th, tx0, tz0, tx0 + tw - 1, tz0 + tw - 1, ty - 1, overhang=1)
    elif cap == "dome":
        dm = roofset(th["dome"] or "copper")[2]
        t.fill(tx0, ty - 1, tz0, tx0 + tw - 1, ty - 1, tz0 + tw - 1, th["roof_full"])
        dome(t, cx, ty, tz0 + 2, 2, dm, finial="lightning_rod[facing=up]")
    elif cap == "onion":
        dm = roofset(th["dome"] or "copper")[2]
        t.fill(tx0, ty - 1, tz0, tx0 + tw - 1, ty - 1, tz0 + tw - 1, th["roof_full"])
        onion(t, cx, ty, tz0 + 2, 2, dm)
    elif cap == "pagoda":
        hip_roof(t, th, tx0, tz0, tx0 + tw - 1, tz0 + tw - 1, ty - 1, overhang=1, upturn=True)
    else:
        cone_roof(t, th, cx, tz0 + 2, 2, ty)
    if style == "domed":
        dm = roofset(th["dome"] or "copper")[2]
        dome(t, cx, top, nz0 + D // 2, 4, dm, finial="lightning_rod[facing=up]")
    if style == "onion":
        dm = roofset(th["dome"] or "copper")[2]
        onion(t, cx, top + 1, nz1 - 4, 2, dm)
    # --- interior
    # bancos a ambos lados del pasillo, mirando al altar
    for z in range(nz0 + 4, nz1 - 6, 2):
        for x in list(range(1, cx - 1)) + list(range(cx + 2, W - 1)):
            t.set(x, 1, z, stairs(th["wstairs"], "north"))
    for z in range(nz0 + 2, nz1 - 4):
        t.set(cx, 1, z, f"{th['carpet'][0]}_carpet")
    # presbiterio: un escalón corrido y tarima
    plat = stone_of(th)
    az = nz1 - 4
    for x in range(1, W - 1):
        t.set(x, 1, az, stairs(th["trim"], "south"))
        for z in range(az + 1, nz1):
            t.set(x, 1, z, plat)
    t.set(cx, 2, az + 1, f"{th['carpet'][0]}_carpet")
    # altar centrado con velas; el clérigo detrás
    t.set(cx, 2, nz1 - 2, "chiseled_stone_bricks" if stone else th["planks"])
    for dxx, f in ((-1, "west"), (1, "east")):
        t.set(cx + dxx, 2, nz1 - 2, stairs(th["trim"], f, half="top"))
        t.set(cx + dxx, 3, nz1 - 2, "candle[candles=3,lit=true]")
    staff(t, th, cx, 1, nz1 - 1, "cleric", final=plat)
    t.set(1, 2, nz1 - 1, "brewing_stand")
    t.chest(W - 2, 2, nz1 - 1, "north", L("iglesia"))
    # lámparas colgadas de tirantes de madera (o del techo plano)
    for z in range(nz0 + 5, nz1 - 4, 5):
        if roofk != "flat":
            for x in range(0, W):
                if t.get(x, H + 1, z) is None or t.get(x, H + 1, z) == "minecraft:air":
                    t.set(x, H + 1, z, log(th["log"], "x"))
        chandelier(t, th, cx, H, z)
    t.edge_jigsaw("east", nz1 - 8, 0, "heraldia:side", "heraldia:entrance", P(th, "cemetery"), sel=8, place=8)
    return t


def pyramid_temple(th, rng, name):
    """Templo escalonado: escalinata frontal completa hasta un santuario en la cima."""
    t = Template(name)
    N, z0 = 19, 2
    c = N // 2
    entrance(t, th, c)
    t.fill(c - 1, 0, 1, c + 1, 0, 1, th["wall2"])
    for lv in range(3):
        for y in (2 * lv, 2 * lv + 1):
            t.fill(2 * lv, y, z0 + 2 * lv, N - 1 - 2 * lv, y, z0 + N - 1 - 2 * lv, th["wall2"] if y == 2 * lv else th["wall"])
    # escalinata de 3 de ancho, despejada por encima
    for k in range(6):
        for x in range(c - 1, c + 2):
            t.set(x, k, z0 + k, stairs(th["trim"], "south"))
            for y in range(k + 1, k + 4):
                t.set(x, y, z0 + k, "air")
    py = 6                                   # cota de la plataforma superior (pies)
    # braseros a los lados de la escalinata
    for x in (c - 3, c + 3):
        t.set(x, py, z0 + 5, "campfire[lit=true,signal_fire=false]")
    # santuario 7x7
    sx0, sx1, sz0, sz1 = c - 3, c + 3, z0 + 7, z0 + 13
    for y in range(py, py + 4):
        for x in range(sx0, sx1 + 1):
            for z in range(sz0, sz1 + 1):
                edge = x in (sx0, sx1) or z in (sz0, sz1)
                corner = x in (sx0, sx1) and z in (sz0, sz1)
                t.set(x, y, z, (th["wall2"] if corner else th["wall"]) if edge else "air")
    t.fill(sx0 + 1, py + 4, sz0 + 1, sx1 - 1, py + 4, sz1 - 1, th["planks"])
    hip_roof(t, th, sx0, sz0, sx1, sz1, py + 4, overhang=1)
    door(t, c, py, sz0, th["door"], "north")
    gl = f"{th['church_glass']}_stained_glass_pane"
    for x in (sx0, sx1):
        t.set(x, py + 1, sz0 + 3, gl); t.set(x, py + 2, sz0 + 3, gl)
    # interior: altar al fondo, velas, puesto del clérigo y cofre
    t.set(c, py, sz1 - 1, "chiseled_sandstone" if "sandstone" in th["wall"] else "chiseled_stone_bricks")
    t.set(c, py + 1, sz1 - 1, "candle[candles=3,lit=true]")
    t.set(sx0 + 1, py, sz1 - 1, "brewing_stand")
    t.chest(sx1 - 1, py, sz1 - 1, "north", L("iglesia"))
    for z in range(sz0 + 1, sz0 + 3):
        t.set(c, py, z, f"{th['carpet'][0]}_carpet")
    staff(t, th, c, py - 1, sz0 + 4, "cleric", final=th["wall"])
    t.set(c, py + 3, sz0 + 3, lantern(th, True))
    t.edge_jigsaw("east", z0 + N - 3, 0, "heraldia:side", "heraldia:entrance", P(th, "cemetery"),
                  final_state=th["wall2"], sel=8, place=8)
    return t


def pagoda_temple(th, rng, name):
    t = Template(name)
    W, D, zf = 13, 15, 3
    cx = W // 2
    zb = zf + D - 1
    red = th["id"] != "cerezos_templo"
    entrance(t, th, cx)
    # plataforma de piedra
    t.fill(-1, 0, zf - 1, W, 0, zb + 1, th["found"])
    t.fill(cx - 1, 0, 1, cx + 1, 0, 1, th["found"])
    # torii sobre el camino de entrada
    post = "red_concrete" if red else log(th["log"], "y")
    for x in (cx - 3, cx + 3):
        t.set(x, 0, 1, th["found"])
        for y in range(1, 6):
            t.set(x, y, 1, post)
    for x in range(cx - 2, cx + 3):
        t.set(x, 4, 1, "red_concrete" if red else log(th["log"], "x"))
    for x in range(cx - 4, cx + 5):
        t.set(x, 6, 1, f"{th['roof_slab']}[type=bottom]")
    # sala principal
    shell(t, th, 0, zf, W - 1, zb, 1, 6, roof="none")
    t.fill(1, 8, zf + 1, W - 2, 8, zb - 1, th["planks"])
    hip_roof(t, th, 0, zf, W - 1, zb, 8, overhang=2, upturn=True, max_rings=3)
    for y in range(9, 13):                                    # cuerpo alto entre los dos tejados
        for x in range(1, W - 1):
            for z in range(zf + 1, zb):
                if x in (1, W - 2) or z in (zf + 1, zb - 1):
                    corner = x in (1, W - 2) and z in (zf + 1, zb - 1)
                    t.set(x, y, z, log(th["log"], "y") if corner else th["wall"])
    hip_roof(t, th, 1, zf + 1, W - 2, zb - 1, 13, overhang=1, upturn=True)
    for x in range(cx - 1, cx + 2):
        t.set(x, 1, zf - 1, stairs(th["trim"], "south"))
    door(t, cx, 2, zf, th["door"], "north")
    gl = f"{th['church_glass']}_stained_glass_pane"
    for z in range(zf + 3, zb - 1, 3):
        for x in (0, W - 1):
            t.set(x, 3, z, gl); t.set(x, 4, z, gl)
    for x in (cx - 3, cx + 3):
        t.set(x, 3, zf, gl); t.set(x, 4, zf, gl)
    # interior: altar al fondo, pasillo, cojines en filas
    t.set(cx, 2, zb - 1, "chiseled_stone_bricks")
    t.set(cx, 3, zb - 1, "candle[candles=4,lit=true]")
    for x in (cx - 1, cx + 1):
        t.set(x, 2, zb - 1, f"{th['wslab']}[type=top]")
        t.set(x, 3, zb - 1, "candle[candles=1,lit=true]")
    t.set(1, 2, zb - 1, "brewing_stand")
    t.chest(W - 2, 2, zb - 1, "north", L("iglesia"))
    for z in range(zf + 1, zb - 2):
        t.set(cx, 2, z, f"{th['carpet'][1]}_carpet")
    for x in (cx - 4, cx - 2, cx + 2, cx + 4):
        for z in range(zf + 4, zb - 3, 2):
            t.set(x, 2, z, f"{th['carpet'][0]}_carpet")
    staff(t, th, cx, 1, zb - 2, "cleric")
    for z in (zf + 4, zb - 5):
        chandelier(t, th, cx, 7, z)
    # pagoda de cuatro cuerpos, accesible por dentro
    px0, pz0 = W + 2, zf + 4
    t.fill(W + 1, 0, pz0 - 1, px0 + 5, 0, pz0 + 5, th["found"])
    pc = (px0 + 2, pz0 + 2)
    for k in range(4):
        y0 = k * 4
        if k:
            t.fill(px0, y0, pz0, px0 + 4, y0, pz0 + 4, th["planks"])
        for y in range(y0 + 1, y0 + 4):
            for x in range(px0, px0 + 5):
                for z in range(pz0, pz0 + 5):
                    edge = x in (px0, px0 + 4) or z in (pz0, pz0 + 4)
                    corner = x in (px0, px0 + 4) and z in (pz0, pz0 + 4)
                    if edge:
                        t.set(x, y, z, log(th["log"], "y") if corner else th["wall"])
                    else:
                        t.set(x, y, z, "air" if y < y0 + 3 else th["planks"])
        for (x, z) in ((px0, pz0 + 2), (px0 + 4, pz0 + 2), (px0 + 2, pz0 + 4)):
            t.set(x, y0 + 2, z, th["window"])
        if k < 3:
            hip_roof(t, th, px0, pz0, px0 + 4, pz0 + 4, y0 + 3, overhang=1, upturn=True, max_rings=1)
    fy_ = hip_roof(t, th, px0, pz0, px0 + 4, pz0 + 4, 15, overhang=1, upturn=True)
    t.set(pc[0], fy_ + 1, pc[1], "lightning_rod[facing=up]")
    door(t, px0 + 2, 1, pz0, th["door"], "north")
    for y in range(1, 13):
        t.set(px0 + 1, y, pz0 + 3, "ladder[facing=north]")
    t.set(pc[0], 14, pc[1], lantern(th, True))
    t.fill(cx - 1, 0, zb + 2, cx + 1, 0, zb + 2, th["found"])
    t.edge_jigsaw("south", cx, 0, "heraldia:side", "heraldia:entrance", P(th, "cemetery"),
                  final_state=th["found"], sel=8, place=8)
    return t


# ======================================================================= CEMENTERIO
WALLS = {"cobblestone": "cobblestone_wall", "stone_bricks": "stone_brick_wall", "mossy_stone_bricks": "mossy_stone_brick_wall",
         "cobbled_deepslate": "cobbled_deepslate_wall", "sandstone": "sandstone_wall", "red_sandstone": "red_sandstone_wall",
         "mud_bricks": "mud_brick_wall", "tuff": "tuff_wall", "terracotta": "mud_brick_wall", "red_terracotta": "mud_brick_wall",
         "cut_sandstone": "sandstone_wall", "mossy_cobblestone": "mossy_cobblestone_wall"}


def cemetery(th, rng, name):
    t = Template(name)
    N, z0 = 15, 1
    c = N // 2
    entrance(t, th, c)
    wallb = WALLS.get(th["found"], "cobblestone_wall")
    pil = stone_of(th)
    for x in range(N):
        for z in range(z0, z0 + N):
            edge = x in (0, N - 1) or z in (z0, z0 + N - 1)
            t.set(x, 0, z, "coarse_dirt" if rng.random() < 0.75 else "podzol")
            if edge:
                t.set(x, 0, z, pil)
                t.set(x, 1, z, wallb)
            else:
                for y in (1, 2, 3):
                    t.set(x, y, z, "air")
    # puerta con dos pilares y faroles
    t.set(c, 0, z0, th["path"])
    t.set(c, 1, z0, f"{th['gate']}[facing=north,open=false]")
    for x in (c - 1, c + 1):
        t.set(x, 1, z0, pil); t.set(x, 2, z0, pil); t.set(x, 3, z0, lantern(th, False))
    mz0 = z0 + N - 6
    for z in range(z0 + 1, mz0):
        t.set(c, 0, z, th["path"])
    # tumbas en dos filas simétricas a cada lado del camino
    heads = ["stone_brick_wall", "cobblestone_wall", "mossy_stone_brick_wall", "mossy_cobblestone_wall"]
    flowers = ["poppy", "dandelion", "azure_bluet", "oxeye_daisy", "lily_of_the_valley"]
    for x in (2, 4, N - 5, N - 3):
        for z in (z0 + 2, z0 + 5):
            t.set(x, 0, z, "podzol"); t.set(x, 0, z + 1, "podzol"); t.set(x, 0, z + 2, pil)
            t.set(x, 1, z + 2, rng.choice(heads))
            if rng.random() < 0.4:
                t.set(x, 1, z + 1, rng.choice(flowers))
    # mausoleo con el cofre dentro
    mx0 = c - 2
    t.fill(mx0, 0, mz0, mx0 + 4, 0, mz0 + 4, "stone_bricks")
    for y in range(1, 4):
        for x in range(mx0, mx0 + 5):
            for z in range(mz0, mz0 + 5):
                edge = x in (mx0, mx0 + 4) or z in (mz0, mz0 + 4)
                t.set(x, y, z, th["wall2"] if edge else "air")
    t.fill(mx0, 4, mz0, mx0 + 4, 4, mz0 + 4, th["wall2"])
    hip_roof(t, th, mx0, mz0, mx0 + 4, mz0 + 4, 5, overhang=0)
    t.set(c, 1, mz0, "air"); t.set(c, 2, mz0, "air")
    t.chest(c, 1, mz0 + 3, "north", L("cripta"))
    for x in (c - 1, c + 1):
        t.set(x, 1, mz0 + 3, "candle[candles=2,lit=true]")
    t.set(c, 3, mz0 + 2, lantern(th, True))
    return t


# ======================================================================= AYUNTAMIENTO
def townhall(th, rng, name):
    t = Template(name)
    W, D, zf = 15, 11, 3
    cx = W // 2
    zb = zf + D - 1
    entrance(t, th, cx)
    t.fill(cx - 2, 0, 1, cx + 2, 0, zf - 1, stone_of(th))
    rk = th["roof_type"] if th["roof_type"] in ("flat", "pagoda") else "hip"
    shell(t, th, 0, zf, W - 1, zb, 0, 8, roof=rk)
    door(t, cx, 1, zf, th["door"], "north")
    skip = [(cx, zf)]
    all_windows(t, th, 0, zf, W - 1, zb, 2, rng, skip=skip, tall=True, spacing=2)
    all_windows(t, th, 0, zf, W - 1, zb, 6, rng, skip=skip, spacing=2)
    # pórtico con balcón practicable encima
    for x in (cx - 2, cx + 2):
        for y in range(1, 4):
            t.set(x, y, 1, log(th["log"], "y"))
    t.fill(cx - 2, 4, 1, cx + 2, 4, zf - 1, f"{th['wslab']}[type=top]")
    for x in range(cx - 2, cx + 3):
        t.set(x, 5, 1, th["fence"])
    for x in (cx - 2, cx + 2):
        t.set(x, 5, 2, th["fence"])
    door(t, cx, 5, zf, th["door"], "north")
    for x in (cx - 4, cx + 4):
        t.set(x, 7, zf - 1, f"{th['banner']}_wall_banner[facing=north]")
    golem_slot(t, cx - 1, 0, 1, stone_of(th))
    # forjado y escalera de mano en la esquina del fondo
    t.fill(1, 4, zf + 1, W - 2, 4, zb - 1, th["planks"])
    for y in range(1, 5):
        t.set(1, y, zb - 1, "ladder[facing=north]")
    # planta baja: sala de plenos
    tz = zf + 5
    for x in range(4, W - 4):
        table(t, th, x, 1, tz)
        if x % 2 == 0:
            chair(t, th, x, 1, tz - 1, "north")
            chair(t, th, x, 1, tz + 1, "south")
    for x in range(3, W - 2):
        t.set(x, 1, zb - 1, "bookshelf"); t.set(x, 2, zb - 1, "bookshelf")
    t.set(W - 2, 1, zf + 1, "cartography_table")
    staff(t, th, W - 3, 0, zf + 2, "cartographer")
    for x in range(cx - 1, cx + 2):
        t.set(x, 1, zf + 1, f"{th['carpet'][0]}_carpet")
    t.set(cx, 3, tz, lantern(th, True))
    # planta alta: despacho
    table(t, th, cx, 5, zb - 3)
    chair(t, th, cx, 5, zb - 2, "south")
    t.chest(W - 2, 5, zb - 1, "north", L("ayuntamiento"))
    for x in (4, 5, W - 6, W - 5):
        t.set(x, 5, zb - 1, "bookshelf"); t.set(x, 6, zb - 1, "bookshelf")
    for x in range(cx - 1, cx + 2):
        for z in range(zf + 2, zf + 5):
            t.set(x, 5, z, f"{th['carpet'][0]}_carpet")
    for x in (cx - 1, cx + 1):
        t.set(x, 5, zf + 1, potted(rng.choice(th["plants"])))
    t.set(cx, 8, zf + 4, lantern(th, True))
    return t


# ======================================================================= MERCADO
def market(th, rng, name):
    """Plaza de mercado: puestos a ambos lados de un pasillo central despejado, con el pozo en medio."""
    t = Template(name)
    W, D = 17, 16
    cx = W // 2
    entrance(t, th, cx)
    for x in range(W):
        for z in range(1, D + 1):
            edge = x in (0, W - 1) or z in (1, D)
            t.set(x, 0, z, stone_of(th) if edge else (th["path"] if rng.random() < 0.8 else th["path2"]))
            for y in (1, 2, 3, 4):
                t.set(x, y, z, "air")
    wools = [th["carpet"][0], th["carpet"][1]]
    wares = [("fletching_table", None), ("stonecutter[facing=east]", "melon"), ("loom[facing=east]", "hay_block[axis=y]"),
             ("smoker[facing=west]", "barrel[facing=up]"), ("composter[level=5]", "pumpkin"), ("barrel[facing=up]", "dried_kelp_block")]
    i = 0
    for side in ("west", "east"):
        for z0 in (2, 7, 12):
            xb, xf = (1, 4) if side == "west" else (W - 2, W - 5)      # fondo y mostrador
            xa, xz = min(xb, xf), max(xb, xf)
            for (px, pz) in ((xa, z0), (xz, z0), (xa, z0 + 3), (xz, z0 + 3)):
                for y in (1, 2):
                    t.set(px, y, pz, th["fence"])
            for x in range(xa, xz + 1):
                for z in range(z0, z0 + 4):
                    t.set(x, 3, z, f"{wools[i % 2]}_wool" if (z - z0) % 2 == 0 else "white_wool")
            for z in (z0 + 1, z0 + 2):
                t.set(xf, 1, z, f"{th['wslab']}[type=top]")
            job, good = wares[i]
            t.set(xb, 1, z0 + 1, job)
            if good is None:
                t.barrel(xb, 1, z0 + 2, loot=L("mercado"))
            else:
                t.set(xb, 1, z0 + 2, good)
            i += 1
    # pozo central con brocal y tejadillo sobre cuatro postes
    wz = 8
    for x in range(cx - 1, cx + 2):
        for z in range(wz - 1, wz + 2):
            t.set(x, 0, z, stone_of(th))
            if (x, z) != (cx, wz):
                t.set(x, 1, z, stone_of(th))
    t.set(cx, 0, wz, "water"); t.set(cx, 1, wz, "water")
    for (x, z) in ((cx - 1, wz - 1), (cx + 1, wz - 1), (cx - 1, wz + 1), (cx + 1, wz + 1)):
        t.set(x, 2, z, th["fence"]); t.set(x, 3, z, th["fence"])
    t.fill(cx - 1, 4, wz - 1, cx + 1, 4, wz + 1, f"{th['roof_slab']}[type=bottom]")
    for (x, z) in ((0, 1), (W - 1, 1), (0, D), (W - 1, D)):
        t.set(x, 1, z, th["fence"]); t.set(x, 2, z, th["fence"]); t.set(x, 3, z, lantern(th, False))
    staff(t, th, 2, 0, 3, "fletcher", final=th["path"])
    golem_slot(t, cx, 0, 13, th["path"])
    t.min_size = (W, 6, D + 1)
    return t


# ======================================================================= HERRERÍA
def blacksmith(th, rng, name):
    t = Template(name)
    W, D, zf = 13, 11, 2
    zb = zf + D - 1
    cx = 3
    H = 4
    entrance(t, th, cx)
    t.fill(cx - 1, 0, 1, cx + 1, 0, 1, stone_of(th))
    # vivienda (izquierda) y fragua abierta (derecha) bajo un mismo tejado
    shell(t, th, 0, zf, 6, zb, 0, H, roof="none")
    t.fill(1, H + 1, zf + 1, 5, H + 1, zb - 1, th["planks"])
    t.fill(7, 0, zf, W - 1, 0, zb, "stone_bricks")
    for x in range(8, W - 1):
        t.set(x, 0, 1, "stone_brick_stairs[facing=south,half=bottom,shape=straight]")
    for (x, z) in ((W - 1, zf), (W - 1, zb)):
        for y in range(1, H + 1):
            t.set(x, y, z, log(th["log"], "y"))
    for x in range(7, W - 1):
        t.set(x, H, zf, log(th["stripped"], "x")); t.set(x, H, zb, log(th["stripped"], "x"))
    for z in range(zf + 1, zb):
        t.set(W - 1, H, z, log(th["stripped"], "z"))
    for x in range(7, W):
        for z in range(zf, zb + 1):
            for y in range(1, H + 1):
                if t.get(x, y, z) is None:
                    t.set(x, y, z, "air")
    rk = "hip" if th["roof_type"] == "cone" else th["roof_type"]
    if rk in ("gable", "steep"):
        top = gable_roof(t, th, 0, zf, W - 1, zb, H + 1, along="x", steep=(rk == "steep"))
    else:
        top = roof_for(t, th, 0, zf, W - 1, zb, H + 1, kind=rk)
    door(t, cx, 1, zf, th["door"], "north")
    for side in ("north", "south", "west"):
        windows_on_wall(t, th, 0, zf, 6, zb, side, 2, rng, skip=[(cx, zf)])
    # vivienda
    bed_slot(t, th, 1, 0, zb - 2, villager_pool(th, "armorer", fixed=True))
    t.chest(5, 1, zb - 1, "north", L("herreria"))
    t.set(5, 1, zf + 1, "crafting_table")
    t.set(1, 1, zf + 1, f"{th['wslab']}[type=top]")
    t.set(1, 2, zf + 1, potted(rng.choice(th["plants"])))
    for x in range(2, 5):
        for z in range(zf + 4, zf + 7):
            t.set(x, 1, z, f"{th['carpet'][0]}_carpet")
    t.set(3, H, zf + 5, lantern(th, True))
    # fragua: útiles en línea contra el muro de la vivienda, horno al fondo
    t.set(7, 1, zf + 2, "anvil[facing=north]")
    t.set(7, 1, zf + 3, "water_cauldron[level=3]")
    t.set(7, 1, zf + 5, "blast_furnace[facing=east]")
    t.set(7, 1, zf + 6, "smithing_table")
    t.set(W - 2, 1, zf + 2, "grindstone[face=floor,facing=west]")
    for z in range(zf + 1, zb):
        t.set(W - 1, 1, z, "cobblestone_wall")
    for x in range(W - 4, W - 1):
        for z in range(zb - 2, zb + 1):
            for y in range(1, 4):
                t.set(x, y, z, "bricks")
    t.set(W - 3, 1, zb - 2, "lava_cauldron")
    t.set(W - 3, 2, zb - 2, "iron_bars")
    for y in range(4, top + 2):
        t.set(W - 3, y, zb - 1, "bricks")
    t.set(W - 3, top + 2, zb - 1, "campfire[lit=true,signal_fire=false]")
    for x in range(7, W - 4):
        t.set(x, 1, zb, "cobblestone_wall")
    t.set(9, H - 1, zf + 4, lantern(th, True))
    return t


# ======================================================================= TABERNA / POSADA
def tavern(th, rng, name, inn=False):
    t = Template(name)
    W, D = (13, 13) if not inn else (15, 11)
    cx = W // 2
    zf = 2
    zb = zf + D - 1
    hz = zf + 4                                  # hogar en el muro este
    entrance(t, th, cx)
    t.fill(cx - 1, 0, 1, cx + 1, 0, 1, stone_of(th))
    top = shell(t, th, 0, zf, W - 1, zb, 0, 8)
    door(t, cx, 1, zf, th["door"], "north")
    for fl in (0, 1):
        for side in ("north", "south", "west", "east"):
            windows_on_wall(t, th, 0, zf, W - 1, zb, side, 2 + 4 * fl, rng,
                            skip=[(cx, zf), (W - 1, hz), (W - 1, hz - 1), (W - 1, hz + 1)])
    t.set(cx + 2, 4, zf - 1, f"{th['banner']}_wall_banner[facing=north]")
    t.set(cx - 2, 4, zf - 1, f"{th['banner']}_wall_banner[facing=north]")
    t.fill(1, 4, zf + 1, W - 2, 4, zb - 1, th["planks"])
    for y in range(1, 5):
        t.set(1, y, zf + 1, "ladder[facing=east]")
    # hogar empotrado en el muro con chimenea exterior
    for y in range(0, top + 2):
        t.set(W, y, hz, "bricks")
    for y in range(1, top + 1):
        if t.get(W - 1, y, hz) is not None:
            t.set(W - 1, y, hz, "bricks")
    t.set(W - 1, 1, hz, "campfire[lit=true,signal_fire=false]")
    t.set(W, top + 2, hz, "campfire[lit=true,signal_fire=false]")
    # barra al fondo, toneles contra el muro y el tabernero detrás
    bz = zb - 3
    for x in range(3, W - 3):
        t.set(x, 1, bz, stairs(th["wstairs"], "north", half="top"))
    for x in range(3, W - 3):
        t.set(x, 1, zb - 1, "smoker[facing=north]" if x == cx else "barrel[facing=north]")
    t.barrel(3, 2, zb - 1, "north", L("posada" if inn else "taberna"))
    t.barrel(W - 4, 2, zb - 1, "north")
    staff(t, th, cx, 0, zb - 2, "leatherworker" if inn else "butcher")
    if inn:
        t.set(W - 2, 1, zb - 1, "cauldron")
    # mesas: dos junto a los muros y una central, sillas con el respaldo hacia fuera
    for (x, z) in ((3, zf + 3), (W - 4, zf + 3), (cx, zf + (5 if inn else 6))):
        table(t, th, x, 1, z)
        chair(t, th, x - 1, 1, z, "west")
        chair(t, th, x + 1, 1, z, "east")
        if x != cx:
            t.set(x, 2, z, "candle[candles=2,lit=true]")
    t.set(cx, 3, zf + (5 if inn else 6), lantern(th, True))
    t.set(cx, 3, zb - 2, lantern(th, True))
    # planta alta: camas contra el muro este, con mesilla
    spots = [(W - 2, zf + 1, "farmer"), (W - 2, zf + 6, "librarian")]
    if inn:
        spots.append((1, zf + 5, "shepherd"))
    for (x, z, prof) in spots:
        bed_slot(t, th, x, 4, z, villager_pool(th, prof))
        t.set(x, 5, z + 2, f"{th['wslab']}[type=top]")
        t.set(x, 6, z + 2, potted(rng.choice(th["plants"])))
    for x in range(cx - 1, cx + 2):
        for z in range(zf + 3, zf + 6):
            t.set(x, 5, z, f"{th['carpet'][1]}_carpet")
    t.set(cx, 8, zf + 4, lantern(th, True))
    return t


# ======================================================================= BIBLIOTECA
def library(th, rng, name):
    t = Template(name)
    W, D, zf = 11, 15, 2
    cx = W // 2
    zb = zf + D - 1
    z0i, z1i = zf + 1, zb - 1                  # interior
    entrance(t, th, cx)
    t.fill(cx - 1, 0, 1, cx + 1, 0, 1, stone_of(th))
    shell(t, th, 0, zf, W - 1, zb, 0, 7, along="z")
    door(t, cx, 1, zf, th["door"], "north")
    wrows = list(range(zf + 3, zb - 1, 3))
    for z in wrows:
        for x in (0, W - 1):
            for y in range(2, 6):
                t.set(x, y, z, th["window"])
    # estanterías de suelo a altillo en los muros largos, dejando libres las ventanas
    for z in range(z0i, z1i + 1):
        if z in wrows:
            continue
        for x in (1, W - 2):
            for y in (1, 2, 3, 5, 6):
                t.set(x, y, z, "bookshelf")
    for x in range(2, W - 2):
        if x != cx:
            for y in (1, 2, 3):
                t.set(x, y, z1i, "bookshelf")
    # altillo en U con barandilla
    for z in range(z0i, z1i + 1):
        for x in (1, 2, 3, W - 4, W - 3, W - 2):
            t.set(x, 4, z, f"{th['wslab']}[type=top]")
    for x in range(4, W - 4):
        for z in (z1i - 1, z1i):
            t.set(x, 4, z, f"{th['wslab']}[type=top]")
    for z in range(z0i, z1i - 1):
        t.set(3, 5, z, th["fence"]); t.set(W - 4, 5, z, th["fence"])
    for x in range(3, W - 3):
        t.set(x, 5, z1i - 1, th["fence"])
    # escalera completa al altillo (4 peldaños) en el lado oeste
    sz0 = z0i + 1
    for k in range(4):
        z = sz0 + k
        t.set(3, 4, z, "air"); t.set(3, 5, z, "air")
        t.set(3, 1 + k, z, stairs(th["wstairs"], "south"))
        for y in range(1, 1 + k):
            t.set(3, y, z, th["planks"])
    t.set(3, 5, sz0 + 4, "air")                 # desembarco sin barandilla
    # mesas de lectura en el eje central
    for z in (zf + 7, zf + 10):
        table(t, th, cx, 1, z)
        t.set(cx, 2, z, "candle[candles=1,lit=true]")
        chair(t, th, cx - 1, 1, z, "west")
        chair(t, th, cx + 1, 1, z, "east")
    t.set(cx, 1, z1i, "lectern[facing=north]")
    t.set(W - 2, 2, z0i, "air"); t.set(W - 2, 3, z0i, "air")
    t.chest(W - 2, 1, z0i, "west", L("biblioteca"))
    staff(t, th, cx, 0, z1i - 2, "librarian")
    for z in (zf + 5, zf + 9):
        chandelier(t, th, cx, 7, z)
    t.set(cx, 1, z0i, f"{th['carpet'][0]}_carpet")
    return t


# ======================================================================= GRANJA
def farm(th, rng, name):
    t = Template(name)
    W, D = 21, 19
    cx = W // 2
    dry = th["family"] in ("desierto", "badlands")
    soil = "coarse_dirt" if dry else "grass_block"
    entrance(t, th, cx)
    for x in range(W):
        for z in range(1, D + 1):
            t.set(x, 0, z, soil)
            for y in (1, 2, 3):
                t.set(x, y, z, "air")
    for x in range(W):
        for z in (1, D):
            t.set(x, 1, z, th["fence"])
    for z in range(1, D + 1):
        for x in (0, W - 1):
            t.set(x, 1, z, th["fence"])
    # camino central de puerta a puerta (la del fondo da al molino)
    for z in range(1, D + 1):
        t.set(cx, 0, z, th["path"])
    t.set(cx, 1, 1, f"{th['gate']}[facing=north,open=false]")
    t.set(cx, 1, D, f"{th['gate']}[facing=north,open=false]")
    t.jigsaw(cx, 0, D, "south_up", "heraldia:side", "heraldia:entrance", P(th, "mill"),
             final_state=th["path"], sel=6, place=6)
    # dos bancales con acequia central
    crops = ["wheat", "carrots", "potatoes", "beetroots"]
    rng.shuffle(crops)
    for i, fx in enumerate((1, cx + 1)):
        crop = crops[i]
        for x in range(fx, fx + 9):
            for z in range(2, 9):
                if x == fx + 4:
                    t.set(x, 0, z, "water")
                else:
                    t.set(x, 0, z, "farmland[moisture=7]")
                    age = rng.randint(4, 7) if crop != "beetroots" else rng.randint(2, 3)
                    t.set(x, 1, z, f"{crop}[age={age}]")
    # granero con la cama del granjero en un rincón
    bx0, bz0 = 1, 10
    rk = "flat" if th["roof_type"] == "flat" else "gable"
    shell(t, th, bx0, bz0, bx0 + 7, bz0 + 7, 0, 4, roof=rk, along="z")
    door(t, bx0 + 7, 1, bz0 + 3, th["door"], "east")
    windows_on_wall(t, th, bx0, bz0, bx0 + 7, bz0 + 7, "west", 2, rng)
    for (x, z) in ((bx0 + 1, bz0 + 5), (bx0 + 1, bz0 + 6), (bx0 + 2, bz0 + 6)):
        t.set(x, 1, z, "hay_block[axis=y]")
    t.set(bx0 + 1, 2, bz0 + 6, "hay_block[axis=y]")
    t.set(bx0 + 4, 1, bz0 + 6, "composter[level=0]")
    t.chest(bx0 + 6, 1, bz0 + 6, "north", L("granja"))
    bed_slot(t, th, bx0 + 1, 0, bz0 + 1, villager_pool(th, "farmer", fixed=True))
    t.set(bx0 + 4, 4, bz0 + 3, lantern(th, True))
    # corral contra la valla exterior
    px0, pz0 = cx + 1, 10
    for x in range(px0, W - 1):
        t.set(x, 1, pz0, th["fence"])
    for z in range(pz0, D):
        t.set(px0, 1, z, th["fence"])
    t.set(px0, 1, pz0 + 4, f"{th['gate']}[facing=west,open=false]")
    t.set(px0 + 1, 1, pz0 + 1, "water_cauldron[level=3]")
    t.set(W - 2, 1, pz0 + 1, "hay_block[axis=y]")
    beasts = rng.choice([("cow", "cow", "sheep", "sheep"), ("pig", "pig", "chicken", "chicken"),
                         ("sheep", "sheep", "goat"), ("cow", "pig", "chicken", "sheep")])
    for i, b in enumerate(beasts):
        t.entity(px0 + 2 + (i % 2) * 3, 1, pz0 + 3 + (i // 2) * 3, animal(b))
    t.min_size = (W, 6, D + 1)
    return t


# ======================================================================= MOLINO
def mill(th, rng, name):
    t = Template(name)
    N, c, zf = 7, 3, 3
    entrance(t, th, c)
    t.fill(c - 1, 0, 1, c + 1, 0, zf - 1, th["path"])
    Ht = 11
    stone = th["family"] not in ("bosque", "taiga", "jungla", "pantano")
    for y in range(0, Ht + 1):
        for x in range(N):
            for z in range(zf, zf + N):
                dx, dz = x - c, z - zf - c
                if abs(dx) == 3 and abs(dz) == 3:
                    continue
                if y == 0:
                    t.set(x, y, z, stone_of(th))
                elif max(abs(dx), abs(dz)) == 3:
                    t.set(x, y, z, (th["wall2"] if y < 4 else th["wall"]) if stone else (th["planks"] if y > 3 else th["wall2"]))
                else:
                    t.set(x, y, z, "air")
    door(t, c, 1, zf, th["door"], "north")
    for y in (3, 8):
        t.set(0, y, zf + 3, th["window"]); t.set(6, y, zf + 3, th["window"])
    # planta alta de molienda, a la que llega la escalera de mano
    t.fill(1, 6, zf + 1, 5, 6, zf + 5, th["planks"])
    for y in range(1, 7):
        t.set(5, y, zf + 5, "ladder[facing=north]")
    t.fill(1, Ht, zf + 1, 5, Ht, zf + 5, th["planks"])
    for (x, z) in ((1, zf + 5), (1, zf + 4), (2, zf + 5)):
        t.set(x, 1, z, "hay_block[axis=y]")
    t.chest(1, 1, zf + 1, "east", L("molino"))
    t.set(3, 5, zf + 3, lantern(th, True))
    t.set(3, 7, zf + 3, "grindstone[face=floor,facing=north]")
    t.set(1, 7, zf + 1, "barrel[facing=up]"); t.set(1, 7, zf + 2, "hay_block[axis=y]")
    t.set(3, Ht - 1, zf + 3, lantern(th, True))
    if th["roof_type"] == "cone":
        cone_roof(t, th, c, zf + c, 3, Ht + 1)
    else:
        hip_roof(t, th, 0, zf, N - 1, zf + N - 1, Ht + 1, overhang=1)
    # aspas: cuatro palos de valla desde el eje y vela a un lado de cada uno
    hub_y = Ht - 2
    hz = zf - 1
    t.set(c, hub_y, hz, log(th["log"], "z"))
    t.set(c, hub_y, hz - 1, log(th["log"], "z"))
    sail = f"{th['wool']}_wool"
    for k in range(1, 6):
        for (dx, dy) in ((k, 0), (-k, 0), (0, k), (0, -k)):
            t.set(c + dx, hub_y + dy, hz - 1, th["fence"])
    for k in range(2, 6):
        t.set(c + k, hub_y + 1, hz - 1, sail)
        t.set(c - k, hub_y - 1, hz - 1, sail)
        t.set(c - 1, hub_y + k, hz - 1, sail)
        t.set(c + 1, hub_y - k, hz - 1, sail)
    return t


# ======================================================================= PUERTO
def port(th, rng, name):
    t = Template(name)
    W, Lp, c = 9, 26, 6
    pw = th["pier"]
    t.jigsaw(c, 0, 0, "north_up", "heraldia:entrance", "heraldia:side", "minecraft:empty",
             final_state=stairs(pw["wstairs"], "south"))
    # caseta del puerto a la entrada, con la puerta al muelle
    shell(t, th, 0, 2, 4, 6, 0, 3)
    door(t, 4, 1, 4, th["door"], "east")
    t.chest(1, 1, 5, "north", L("puerto"))
    t.set(3, 1, 5, "barrel[facing=up]")
    t.set(1, 1, 3, "crafting_table")
    t.set(2, 3, 4, lantern(th, True))
    # muelle
    for z in range(1, Lp):
        for x in range(5 if z < 7 else 0, W):
            t.set(x, 0, z, pw["planks"])
    for z in range(1, Lp, 4):
        for x in ((0 if z >= 7 else 5), W - 1):
            for y in (-2, -1):
                t.set(x, y, z, log(pw["log"], "y"))
            t.set(x, 1, z, pw["fence"])
            if z % 8 == 1:
                t.set(x, 2, z, lantern(th, False))
    for (x, z) in ((0, 2), (4, 2), (0, 6), (4, 6)):
        for y in (-2, -1):
            t.set(x, y, z, log(pw["log"], "y"))
    # grúa con un tonel colgado
    gx, gz = W - 2, Lp - 4
    for y in range(1, 6):
        t.set(gx, y, gz, log(pw["log"], "y"))
    for x in range(gx - 3, gx + 1):
        t.set(x, 6, gz, log(pw["log"], "x"))
    for y in (5, 4):
        t.set(gx - 3, y, gz, "iron_chain[axis=y]")
    t.set(gx - 3, 3, gz, "barrel[facing=up]")
    # carga apilada en un rincón
    for (x, y, z) in ((1, 1, 10), (2, 1, 10), (1, 1, 11), (1, 2, 10)):
        t.set(x, y, z, "barrel[facing=up]")
    staff(t, th, 3, 0, 14, "fisherman", final=pw["planks"])
    wk = th["wood_kind"] if th["wood_kind"] not in ("bamboo", "pale_oak") else "oak"
    t.entity(-1, 0, 16, {"id": f"minecraft:{wk}_boat"})
    t.entity(W, 0, 20, {"id": "minecraft:oak_boat"})
    return t


SPECIALS = {
    "church": church, "cemetery": cemetery, "townhall": townhall, "market": market, "blacksmith": blacksmith,
    "tavern": tavern, "inn": lambda th, rng, n: tavern(th, rng, n, inn=True), "library": library,
    "farm": farm, "mill": mill, "port": port,
}
