"""Mushroom sanctuary (heraldia:medianas/santuario_hongos/<estilo>, Nether): a 15 x 15 clearing in the crimson
or warped forest with a small temple of stems and wart blocks, shroomlight lights and potted fungi. Variant
a: the closed temple (four walls with openings and a wart vault) with the offerings chest on the altar; b: the
mushroom garden (blackstone planters with potted fungi around a shroomlight fountain) with a
chest and a pot.

Styles: carmesi (crimson forest) and deformado (warped forest). Matching loot: fungi, Nether warts, shroomlights,
quartz, gold; no netherite."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from . import _common as c

MID = "santuario_hongos"
DIMENSION = "nether"
DISPLAY_NAME = {"es_es": "Santuario de los hongos", "en_us": "Fungus Shrine"}
SEPARATION = 640
ADVANCEMENT_ICON = "minecraft:crimson_fungus"
ADVANCEMENTS = [dict(id="ofrendas", icono="minecraft:shroomlight",
               titulo=("Ofrenda de esporas", "Spore Offering"),
               descripcion=("Abre el cofre de las ofrendas de un santuario de los hongos",
                            "Open the offering chest of a fungus shrine"),
               tabla="ofrendas")]


LOOT = {
    "ofrendas": chest_loot.place_chest(((2, 4), [item("crimson_fungus", 6, 1, 3), item("warped_fungus", 6, 1, 3),
                                      item("nether_wart", 8, 2, 6), item("shroomlight", 5, 1, 2), item("quartz", 5, 2, 5),
                                      item("gold_nugget", 6, 2, 6), item("crimson_roots", 3, 1, 3),
                                      item("warped_roots", 3, 1, 3), item("glowstone_dust", 4, 2, 4),
                                      item("book", 2, rand_ench=True), empty(5)]),
                            ((1, 1), [item("gold_ingot", 3), item("golden_carrot", 3, 1, 2), item("ender_pearl", 1),
                                      empty(8)])),
    "vasija": chest_loot.table(chest_loot.pool((1, 2), [item("nether_wart", 6, 1, 4), item("crimson_fungus", 4, 1, 2),
                                              item("warped_fungus", 4, 1, 2), item("gold_nugget", 4, 1, 3),
                                              item("bone_meal", 3, 1, 3), empty(6)])),
}

L = 15
CX = 7
T0, T1 = 4, 10          # templete de 7 x 7


def _floor(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 7 + z * 3 + x * z) % len(mats)]


def _clearing(p, name):
    t = Template(name)
    c.courtyard(t, 0, 0, L - 1, L - 1, _floor(p), air_block=7)
    c.entrance(t, CX, p["suelo"][0])
    for x, z in ((1, 1), (13, 1), (1, 13), (13, 13)):          # potted fungi at the corners
        t.set(x, 1, z, p["maceta"])
    return t


def shrine(p, name):
    """Closed small temple: wart walls between stems, openings to the north and south, stepped vault with a shroomlight at
    the keystone, and the altar with the offerings chest and two pots."""
    t = _clearing(p, name)
    c.box(t, T0, 1, T0, T1, 4, T1, p["verruga"], corner_block=p["tallo"], floor=p["piso"])
    for x in (CX - 1, CX, CX + 1):                                # 3 x 3 openings to the north (entrance) and south
        for y in (1, 2, 3):
            t.set(x, y, T0, "air")
            if y > 1:
                t.set(x, y, T1, "air")
    t.fill(T0, 5, T0, T1, 5, T1, p["verruga"])
    t.fill(T0 + 1, 6, T0 + 1, T1 - 1, 6, T1 - 1, p["verruga"])
    t.set(CX, 6, CX, "shroomlight")
    t.set(CX, 1, T1 - 1, p["altar"])
    c.place_chest(t, CX, 2, T1 - 1, "north", MID, "ofrendas")
    for x in (CX - 2, CX + 2):
        t.set(x, 1, T1 - 1, p["maceta"])
    for x, z in ((T0 + 1, T0 + 1), (T1 - 1, T0 + 1)):
        t.set(x, 4, z, "shroomlight")
    pieces.connect(t)
    return t


def garden(p, name):
    """Garden: four blackstone planters with potted fungi on top, the shroomlight fountain in the center (a
    wart pillar crowned with shroomlight between slabs) and the chest and the pot at the foot."""
    t = _clearing(p, name)
    for ax, az in ((3, 3), (9, 3), (3, 9), (9, 9)):
        for x in range(ax, ax + 3):
            for z in range(az, az + 3):
                t.set(x, 1, z, "polished_blackstone_bricks")
        t.set(ax + 1, 2, az + 1, p["maceta"])
    for x in range(CX - 1, CX + 2):
        for z in range(CX - 1, CX + 2):
            if (x, z) != (CX, CX):
                t.set(x, 1, z, "polished_blackstone_slab[type=bottom,waterlogged=false]")
    t.set(CX, 1, CX, p["verruga"])
    t.set(CX, 2, CX, p["verruga"])
    t.set(CX, 3, CX, "shroomlight")
    c.place_chest(t, CX, 1, CX + 3, "north", MID, "ofrendas")
    c.place_chest(t, CX + 3, 1, CX, "west", MID, "vasija", kind="decorated_pot")
    pieces.connect(t)
    return t


STYLES = {
    "carmesi": dict(biomas=["crimson_forest"], convencionales=[],
                    paleta=dict(suelo=["minecraft:crimson_planks", "minecraft:polished_blackstone",
                                       "minecraft:crimson_planks", "minecraft:blackstone"],
                                piso="crimson_planks", verruga="nether_wart_block", tallo="crimson_hyphae[axis=y]",
                                altar="chiseled_polished_blackstone", maceta="potted_crimson_fungus"),
                    variantes={"a": shrine, "b": garden}),
    "deformado": dict(biomas=["warped_forest"], convencionales=[],
                      paleta=dict(suelo=["minecraft:warped_planks", "minecraft:polished_blackstone",
                                         "minecraft:warped_planks", "minecraft:blackstone"],
                                  piso="warped_planks", verruga="warped_wart_block", tallo="warped_hyphae[axis=y]",
                                  altar="chiseled_polished_blackstone", maceta="potted_warped_fungus"),
                      variantes={"a": shrine, "b": garden}),
}
