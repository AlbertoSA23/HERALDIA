"""Dock of the fallen shulkers (heraldia:medianas/embarcadero_shulker/<estilo>, End, outer islands): a 13 x 21 purpur
pier with its mooring hut, where the End ships used to dock; the shulkers that guarded it fell
and their empty shells remain (of purple glazed terracotta: a shulker box could be carried off). Variant
a: the pier with a shulker on guard at the bollard and the captain's chest in the hut; b: the pier with the broken hull
of an End boat (purpur bow and mast with its purple wool sail) and the stranded cargo: the chest and two barrels.

Styles: altas (End highlands) and medias (End midlands and barrens). Matching loot: ender pearls, chorus
fruit, string, iron, sometimes a shulker shell (at most one: the End gives it anyway); no elytra."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from . import _common as c

MID = "embarcadero_shulker"
DIMENSION = "end"
DISPLAY_NAME = {"es_es": "Embarcadero de los shulkers caídos", "en_us": "Fallen Shulker Wharf"}
SEPARATION = 960
ADVANCEMENT_ICON = "minecraft:shulker_shell"
LANG = chest_loot.lang("heraldia.medianas.embarcadero_shulker.", {
    "guardia": ("Guardia del muelle", "Wharf Guard"),
})
LOOT = {
    "capitan": chest_loot.place_chest(((2, 4), [item("ender_pearl", 8, 1, 3), item("chorus_fruit", 8, 2, 6), item("string", 6, 2, 5),
                                     item("iron_ingot", 6, 1, 4), item("lead", 3), item("purple_wool", 4, 1, 3),
                                     item("compass", 2), item("gold_ingot", 3, 1, 2), empty(5)]),
                           ((1, 1), [item("shulker_shell", 1), item("ender_eye", 2), item("emerald", 3, 1, 3), empty(9)])),
    "carga": chest_loot.table(chest_loot.pool((1, 3), [item("chorus_fruit", 6, 1, 4), item("popped_chorus_fruit", 4, 1, 3),
                                             item("purpur_block", 4, 2, 6), item("string", 4, 1, 3),
                                             item("iron_nugget", 5, 2, 6), empty(6)])),
}

AX, AZ = 13, 21          # 13 x 21 (x, z) pier: deck at y = 0 from north to south
CX = 6


def _floor(p):
    mats = p["tablero"]
    return lambda x, z: mats[(x + 3 * z) % len(mats)]


def _pier(p, name):
    t = Template(name)
    c.courtyard(t, 0, 0, AX - 1, AZ - 1, _floor(p), air_block=7, edge_block=p["borde"])
    c.entrance(t, CX, p["borde"])
    for z in range(2, AZ, 4):                                  # bollards (low pillars with a rod) at the sides
        for x in (0, AX - 1):
            t.set(x, 1, z, p["noray"])
            t.set(x, 2, z, "end_rod[facing=up]")
    # mooring hut to the north, left of the entrance
    c.box(t, 1, 1, 2, 4, 4, 6, p["muro"], corner_block=p["pilar"])
    t.fill(1, 5, 2, 4, 5, 6, f"{p['losa']}[type=bottom,waterlogged=false]")
    t.set(4, 1, 4, "air")
    t.set(4, 2, 4, "air")
    c.door(t, 4, 1, 4, "east", "birch_door")
    t.set(1, 2, 4, "purple_stained_glass_pane")
    c.lantern(t, 2, 4, 4)
    # fallen shells along the pier (glazed terracotta: a decorative shulker box would break and give
    # the box, two shells)
    for x, z, color in ((9, 9, "purple"), (3, 12, "magenta"), (10, 16, "purple")):
        t.set(x, 1, z, f"{color}_glazed_terracotta[facing=north]")
    return t


def sentry(p, name):
    t = _pier(p, name)
    c.place_chest(t, 2, 1, 5, "east", MID, "capitan")
    t.set(3, 1, 3, "barrel[facing=up,open=false]")
    t.set(CX, 1, AZ - 3, p["noray"])
    t.entity(CX, 2, AZ - 3, c.mob("shulker", MID, "guardia", "Guardia del muelle", Color=10, Peek=0))
    pieces.connect(t)
    return t


def boat(p, name):
    t = _pier(p, name)
    c.place_chest(t, 2, 1, 5, "east", MID, "capitan")
    # broken hull: purpur gunwale in the shape of a bow, mast and sail
    for z in range(11, AZ - 1):
        for x in (CX - 3, CX + 3):
            t.set(x, 1, z, p["muro"])
    for x in range(CX - 2, CX + 3):
        t.set(x, 1, AZ - 2, p["muro"])
    for y in range(1, 7):
        t.set(CX, y, 15, p["pilar"])
    for x in (CX - 1, CX + 1):
        for y in (4, 5, 6):
            t.set(x, y, 15, "purple_wool")
    c.place_chest(t, CX - 2, 1, 17, "east", MID, "carga", kind="barrel")
    c.place_chest(t, CX + 2, 1, 17, "west", MID, "carga", kind="barrel")
    pieces.connect(t)
    return t


STYLES = {
    "altas": dict(biomas=["end_highlands"], convencionales=[],
                  paleta=dict(tablero=["minecraft:purpur_block", "minecraft:purpur_pillar[axis=z]"],
                              borde="minecraft:end_stone_bricks", noray="purpur_pillar[axis=y]", muro="purpur_block",
                              pilar="purpur_pillar[axis=y]", losa="purpur_slab"),
                  variantes={"a": sentry, "b": boat}),
    "medias": dict(biomas=["end_midlands", "end_barrens"], convencionales=[],
                   paleta=dict(tablero=["minecraft:end_stone_bricks", "minecraft:purpur_block"],
                               borde="minecraft:purpur_block", noray="end_stone_brick_wall", muro="end_stone_bricks",
                               pilar="purpur_pillar[axis=y]", losa="end_stone_brick_slab"),
                   variantes={"a": sentry, "b": boat}),
}
