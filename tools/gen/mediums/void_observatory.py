"""Void observatory (heraldia:medianas/observatorio_vacio/<estilo>, End, outer islands): a 17 x 17
End stone brick platform with a purpur observatory that looks into the void. Variant a: the spyglass
tower (three floors with a ladder and, at the top, the spyglass: a line of End rods pointing at the sky) with the
astronomer's chest; b: the armillary sphere (a ring of purpur pillars with End rods) around the chart
table, with its chest and a barrel.

Styles: altas (End highlands) and medias (End midlands and barrens), with stone and purpur in different
proportions. Matching loot: ender pearls, chorus fruit, amethyst, spyglass, paper; no elytra or netherite."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from . import _common as c

MID = "observatorio_vacio"
DIMENSION = "end"
DISPLAY_NAME = {"es_es": "Observatorio del vacío", "en_us": "Void Observatory"}
SEPARATION = 896
ADVANCEMENT_ICON = "minecraft:end_rod"
LOOT = {
    "astronomo": chest_loot.place_chest(((2, 4), [item("ender_pearl", 8, 1, 3), item("chorus_fruit", 8, 2, 6),
                                       item("popped_chorus_fruit", 5, 1, 4), item("amethyst_shard", 6, 2, 5),
                                       item("paper", 6, 2, 6), item("spyglass", 2), item("glass", 4, 2, 6),
                                       item("map", 2), item("gold_ingot", 3), empty(5)]),
                             ((1, 1), [item("ender_eye", 2), item("emerald", 3, 1, 3), item("book", 2, rand_ench=True),
                                       empty(8)])),
    "cartas": chest_loot.table(chest_loot.pool((1, 3), [item("paper", 6, 2, 6), item("map", 3), item("ink_sac", 4, 1, 3),
                                              item("feather", 4, 1, 3), item("chorus_fruit", 4, 1, 3), empty(6)])),
}

L = 17
CX = 8
X0, Z0, X1, Z1 = 6, 6, 10, 10     # torre de 5 x 5


def _floor(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 5 + z * 7 + x * z) % len(mats)]


def _platform(p, name):
    t = Template(name)
    c.courtyard(t, 0, 0, L - 1, L - 1, _floor(p), air_block=6, edge_block=p["borde"])
    c.entrance(t, CX, p["borde"])
    for x, z in ((0, 0), (L - 1, 0), (0, L - 1), (L - 1, L - 1)):          # rods at the corners
        t.set(x, 1, z, "end_rod[facing=up]")
    return t


def tower(p, name):
    t = _platform(p, name)
    t.fill(X0, 0, Z0, X1, 0, Z1, p["piso"])
    roof = 12
    c.box(t, X0, 1, Z0, X1, roof, Z1, p["muro"], corner_block=p["pilar"])
    for k in (4, 8):
        t.fill(X0 + 1, k, Z0 + 1, X1 - 1, k, Z1 - 1, p["piso"])
    t.fill(X0, roof, Z0, X1, roof, Z1, p["piso"])
    c.ladder(t, CX, Z1 - 1, 1, roof, "north")
    for k in range(3):                                    # purple glass windows and lanterns per floor
        y = 4 * k + 2
        for x, z in ((X0, CX), (X1, CX)) + (((CX, Z0),) if k else ()):
            t.set(x, y, z, "purple_stained_glass_pane")
        c.lantern(t, CX - 1, 4 * k + 3, CX)
    t.set(CX, 1, Z0, "air")
    t.set(CX, 2, Z0, "air")
    c.door(t, CX, 1, Z0, "north", "birch_door")
    # terrace with railing and the spyglass (End rods tilted in a staircase toward the north)
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (X0, X1) or z in (Z0, Z1):
                t.set(x, roof + 1, z, p["barandilla"])
    t.set(CX + 1, roof + 1, CX, p["pilar"])
    for i in range(3):
        t.set(CX + 1, roof + 2 + i, CX, "end_rod[facing=up]")
    c.place_chest(t, X0 + 1, roof + 1, Z0 + 1, "south", MID, "astronomo")
    pieces.connect(t)
    return t


def armillary(p, name):
    t = _platform(p, name)
    ring_cells = [(4, 4), (8, 3), (12, 4), (13, 8), (12, 12), (8, 13), (4, 12), (3, 8)]
    for x, z in ring_cells:
        for y in range(1, 5):
            t.set(x, y, z, p["pilar"])
        t.set(x, 5, z, "end_rod[facing=up]")
    for x in range(CX - 1, CX + 2):                       # chart table on a slab dais
        for z in range(CX - 1, CX + 2):
            t.set(x, 1, z, f"{p['losa']}[type=bottom,waterlogged=false]")
    t.set(CX, 1, CX, "cartography_table")
    c.place_chest(t, CX, 1, CX + 2, "north", MID, "astronomo")
    c.place_chest(t, CX + 2, 1, CX, "west", MID, "cartas", kind="barrel")
    t.set(CX - 2, 1, CX, "lectern[facing=east,has_book=false,powered=false]")
    pieces.connect(t)
    return t


STYLES = {
    "altas": dict(biomas=["end_highlands"], convencionales=[],
                  paleta=dict(suelo=["minecraft:end_stone_bricks", "minecraft:end_stone_bricks", "minecraft:purpur_block"],
                              borde="minecraft:purpur_block", piso="end_stone_bricks", muro="end_stone_bricks",
                              pilar="purpur_pillar[axis=y]", barandilla="end_stone_brick_wall", losa="purpur_slab"),
                  variantes={"a": tower, "b": armillary}),
    "medias": dict(biomas=["end_midlands", "end_barrens"], convencionales=[],
                   paleta=dict(suelo=["minecraft:purpur_block", "minecraft:end_stone_bricks", "minecraft:purpur_block"],
                               borde="minecraft:end_stone_bricks", piso="purpur_block", muro="purpur_block",
                               pilar="purpur_pillar[axis=y]", barandilla="end_stone_brick_wall", losa="end_stone_brick_slab"),
                   variantes={"a": tower, "b": armillary}),
}
