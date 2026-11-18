"""Ermita (heraldia:medianas/ermita/<estilo>): capilla de 7 x 11 con espadaña y campana, bancos, altar con velas y la
celda del ermitaño (cama y cofre con su diario), y un huerto vallado con una acequia. Variante a: el huerto al este;
b: el huerto al oeste y un pequeño camposanto al este. Sin monstruos."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot
from . import _common as c

MID = "ermita"
DISPLAY_NAME = {"es_es": "Ermita", "en_us": "Hermitage"}
SEPARATION = 768
ADVANCEMENT_ICON = "minecraft:bell"
_K = "heraldia.medianas.ermita."
LANG = chest_loot.lang(_K, {
    "diario": ("Diario del ermitaño", "The Hermit's Diary"),
    "diario.p1": ("Subí aquí para estar lejos de todo. El camino sigue pasando a lo lejos: torres, posadas, fogatas "
                  "de gente que no quiere ser vista.",
                  "I came up here to be far from everything. The road still passes in the distance: towers, inns, "
                  "campfires of people who do not wish to be seen."),
    "diario.p2": ("El huerto da lo justo. La campana la toco al alba y al ocaso; si alguien la oye, que sepa que aquí "
                  "hay techo y pan para quien llegue en paz.",
                  "The garden gives just enough. I ring the bell at dawn and dusk; whoever hears it should know there "
                  "is a roof and bread here for anyone who comes in peace."),
})
_DIARY = chest_loot.written_book([{"translate": _K + "diario.p1", "fallback": LANG["es_es"][_K + "diario.p1"]},
                       {"translate": _K + "diario.p2", "fallback": LANG["es_es"][_K + "diario.p2"]}],
                      {"translate": _K + "diario", "fallback": LANG["es_es"][_K + "diario"]},
                      LANG["es_es"][_K + "diario"], "Ermitaño")
LOOT = {
    "celda": chest_loot.table(
        chest_loot.pool(1, [_DIARY]),
        chest_loot.pool((2, 4), [item("bread", 8, 1, 3), item("candle", 6, 1, 3), item("paper", 5, 1, 4), item("book", 4),
                            item("golden_carrot", 2, 1, 2), item("glistering_melon_slice", 2), item("honey_bottle", 3),
                            item("experience_bottle", 2, 1, 2), item("book", 2, rand_ench=True), empty(4)]),
        chest_loot.pool((1, 1), [item("emerald", 3, 1, 2), item("lapis_lazuli", 3, 2, 5), empty(8)], extra=True)),
}

X0, Z0, X1, Z1 = 7, 3, 13, 13       # muros de la capilla (7 x 11), puerta al norte
CX = 10
WIDTH, DEPTH = 21, 17


def _floor(p):
    mats = p["patio"]
    return lambda x, z: "minecraft:dirt_path" if x == CX and z < Z0 else mats[(x * 7 + z * 3 + x * z) % len(mats)]


def _chapel(p, name):
    t = Template(name)
    m = p["madera"]
    c.courtyard(t, 0, 0, WIDTH - 1, DEPTH - 1, _floor(p))
    c.entrance(t, CX, f"{p['peldano']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, p["suelo"])
    # muros girados: la cumbrera va a lo largo de z, así que se construye en (z, x) con el tejado común sobre x
    c.box(t, X0, 1, Z0, X1, 4, Z1, p["muro"], corner_block=p["esquina"])
    t.fill(X0, 5, Z0, X1, 5, Z1, p["muro"])
    t.fill(X0 + 1, 5, Z0 + 1, X1 - 1, 5, Z1 - 1, f"{m}_planks")
    summit = _roof_z(t, p, 5)
    c.door(t, CX, 1, Z0, "south", f"{m}_door")
    # espadaña sobre la fachada norte con la campana
    t.fill(CX - 1, summit, Z0, CX + 1, summit + 3, Z0, p["esquina"])
    t.set(CX, summit + 1, Z0, "air")
    t.set(CX, summit + 2, Z0, "bell[attachment=ceiling,facing=north,powered=false]")
    # ventanas altas en los muros largos, rosetón sobre la puerta
    for z in (5, 8, 11):
        c.window(t, X0, 3, z, p["vidriera"])
        c.window(t, X1, 3, z, p["vidriera"])
    c.window(t, CX, 4, Z0, p["vidriera"])
    # bancos mirando al altar (sur): respaldo al norte
    for z in (5, 7):
        for x in (X0 + 1, X0 + 2, X1 - 2, X1 - 1):
            t.set(x, 1, z, f"{m}_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    # presbiterio: escalón, altar con velas; la celda detrás de un tabique con puerta
    t.fill(X0 + 1, 1, 9, X1 - 1, 1, 9, f"{p['losa']}[type=bottom,waterlogged=false]")
    t.fill(X0 + 1, 1, 10, X1 - 1, 4, 10, p["muro"])
    t.set(CX, 1, 10, p["altar"])
    t.set(CX, 2, 10, "candle[candles=4,lit=true,waterlogged=false]")
    t.set(CX, 3, 10, p["muro"])
    c.door(t, X1 - 1, 1, 10, "south", f"{m}_door")
    t.set(X1 - 1, 1, 9, "air")
    c.bed(t, X0 + 1, 12, "west", p["cama"])
    c.place_chest(t, X1 - 1, 1, 12, "west", MID, "celda")
    t.set(CX, 1, 12, "lectern[facing=north,has_book=false,powered=false]")
    c.lantern(t, CX, 4, 7)
    c.lantern(t, CX, 4, 11)
    return t


def _roof_z(t, p, y):
    """Tejado a dos aguas con la cumbrera a lo largo de z (las aguas hacia el este y el oeste)."""
    xa, xb, yy = X0 - 1, X1 + 1, y
    while True:
        for z in range(Z0 - 1, Z1 + 2):
            if xa == xb:
                t.set(xa, yy, z, p["cumbrera"])
            else:
                t.set(xa, yy, z, f"{p['teja']}[facing=east,half=bottom,shape=straight,waterlogged=false]")
                t.set(xb, yy, z, f"{p['teja']}[facing=west,half=bottom,shape=straight,waterlogged=false]")
        if xa == xb:
            return yy
        for z in (Z0, Z1):
            for x in range(max(xa + 1, X0), min(xb - 1, X1) + 1):
                t.set(x, yy, z, p["muro"])
        xa, xb, yy = xa + 1, xb - 1, yy + 1


def _garden(t, p, x0, x1):
    """Huerto vallado de x0..x1 (z 4..12) con bancales, una acequia de una fuente en el centro y un compostador."""
    m = p["madera"]
    z0, z1 = 4, 12
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x in (x0, x1) or z in (z0, z1):
                t.set(x, 1, z, f"{m}_fence")
            elif (x, z) == ((x0 + x1) // 2, (z0 + z1) // 2):
                t.set(x, 0, z, "water[level=0]")
            else:
                t.set(x, 0, z, "farmland[moisture=7]")
                t.set(x, 1, z, p["cultivos"][(z // 2) % len(p["cultivos"])])
    t.set((x0 + x1) // 2, 1, z0, f"{m}_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    t.set(x0 + 1, 1, z0 - 1, "composter[level=0]")


def orchard_east(p, name):
    t = _chapel(p, name)
    _garden(t, p, X1 + 2, WIDTH - 2)
    return t


def churchyard(p, name):
    """Huerto al oeste y, al este, tres tumbas con su lápida y una vela."""
    t = _chapel(p, name)
    _garden(t, p, 1, X0 - 2)
    for z in (5, 8, 11):
        t.set(X1 + 4, 1, z, p["lapida"])
        t.set(X1 + 4, 2, z, "candle[candles=1,lit=false,waterlogged=false]")
        for dx in (1, 2):
            t.set(X1 + 4 + dx, 0, z, "packed_mud")
    return t


_CROPS_SHORT = ["wheat[age=7]", "carrots[age=7]", "potatoes[age=7]", "beetroots[age=3]"]
STYLES = {
    "montana": dict(biomas=["grove", "snowy_slopes"],
                    paleta=dict(madera="spruce", muro="stone_bricks", esquina="chiseled_stone_bricks", zocalo="cobblestone",
                                suelo="polished_andesite", losa="stone_brick_slab", altar="chiseled_stone_bricks",
                                teja="spruce_stairs", cumbrera="spruce_planks", peldano="stone_brick_stairs",
                                vidriera="light_blue_stained_glass_pane", cama="blue", lapida="cobblestone_wall",
                                cultivos=_CROPS_SHORT, patio=["minecraft:cobblestone", "minecraft:dirt_path"]),
                    variantes={"a": orchard_east, "b": churchyard}),
    "oscuro": dict(biomas=["dark_forest", "pale_garden"], convencionales=["c:is_dark_forest"],
                   paleta=dict(madera="dark_oak", muro="mossy_cobblestone", esquina="dark_oak_log[axis=y]",
                               zocalo="cobblestone", suelo="spruce_planks", losa="cobblestone_slab",
                               altar="polished_deepslate", teja="dark_oak_stairs", cumbrera="dark_oak_planks",
                               peldano="cobblestone_stairs", vidriera="purple_stained_glass_pane", cama="black",
                               lapida="mossy_cobblestone_wall", cultivos=_CROPS_SHORT,
                               patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:mossy_cobblestone"]),
                   variantes={"a": orchard_east, "b": churchyard}),
    "cerezo": dict(biomas=["cherry_grove"],
                   paleta=dict(madera="cherry", muro="white_terracotta", esquina="stripped_cherry_log[axis=y]",
                               zocalo="stone_bricks", suelo="cherry_planks", losa="smooth_stone_slab",
                               altar="calcite", teja="cherry_stairs", cumbrera="cherry_planks",
                               peldano="stone_brick_stairs", vidriera="pink_stained_glass_pane", cama="pink",
                               lapida="stone_brick_wall", cultivos=_CROPS_SHORT,
                               patio=["minecraft:dirt_path", "minecraft:stone_bricks"]),
                   variantes={"a": orchard_east, "b": churchyard}),
}
