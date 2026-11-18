"""Magma altar (heraldia:medianas/altar_magma/<estilo>, Nether): a 17 x 17 clearing with a ring of basalt and
blackstone pillars and, in the middle, a three-tier altar with lava cauldrons (the lava stays contained: it never spills)
and the offerings chest. Variant a: the high altar with a magma cube spawner under the altar stone and braziers; b: the
broken altar (fallen pillars, magma cracks between the slabs) with two magma cubes on guard.

Styles: deltas (basalt deltas: polished basalt and smooth basalt) and yermo (Nether wastes: blackstone and red Nether
brick). Matching loot: magma cream, blaze powder, fire charges, gold; no netherite."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from . import _common as c

MID = "altar_magma"
DIMENSION = "nether"
DISPLAY_NAME = {"es_es": "Altar de magma", "en_us": "Magma Altar"}
SEPARATION = 640
ADVANCEMENT_ICON = "minecraft:magma_cream"
LOOT = {
    "ofrendas": chest_loot.place_chest(((2, 4), [item("magma_cream", 8, 1, 4), item("blaze_powder", 6, 1, 3),
                                      item("fire_charge", 6, 1, 3), item("gold_nugget", 8, 2, 7),
                                      item("quartz", 6, 2, 5), item("gold_ingot", 3), item("obsidian", 3, 1, 2),
                                      item("book", 2, rand_ench=True), empty(5)]),
                            ((1, 1), [item("blaze_rod", 3), item("golden_apple", 1), item("gold_ingot", 3, 1, 2),
                                      empty(8)])),
    "brasero": chest_loot.table(chest_loot.pool((1, 2), [item("magma_cream", 6, 1, 2), item("coal", 5, 1, 3),
                                               item("gold_nugget", 5, 1, 4), item("fire_charge", 2), empty(6)])),
}

L = 17
CX = 8
RING = [(3, 3), (8, 2), (13, 3), (14, 8), (13, 13), (8, 14), (3, 13), (2, 8)]


def _floor(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 5 + z * 11 + x * z) % len(mats)]


def _clearing(p, name, broken):
    t = Template(name)
    c.courtyard(t, 0, 0, L - 1, L - 1, _floor(p), air_block=8)
    c.entrance(t, CX, p["suelo"][0])
    # ring of pillars (the northern ones, at the sides of the entrance; whole or fallen)
    for i, (x, z) in enumerate(RING):
        if (x, z) == (CX, 2):
            continue
        height = 2 if broken and i % 2 else 5
        for y in range(1, height + 1):
            t.set(x, y, z, p["pilar"])
        if height == 5:
            t.set(x, 6, z, p["capitel"])
    # three-tier altar: 7 x 7, 5 x 5 and 3 x 3, steps to the north
    for n, (a, b) in enumerate(((5, 11), (6, 10), (7, 9))):
        y = n + 1
        for x in range(a, b + 1):
            for z in range(a, b + 1):
                t.set(x, y, z, p["grada"])
        t.set(CX, y, a, f"{p['escalon']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    # lava cauldrons at the corners of the lowest tier
    for x, z in ((5, 5), (11, 5), (5, 11), (11, 11)):
        t.set(x, 2, z, "lava_cauldron")
    return t


def main(p, name):
    """Whole altar: the altar stone with the offerings chest on top, the magma cube spawner below (enclosed in the
    tier) and two braziers (barrels) next to the entrance."""
    t = _clearing(p, name, broken=False)
    t.set(CX, 4, CX, p["ara"])
    c.place_chest(t, CX, 4, CX + 1, "north", MID, "ofrendas")
    pieces.spawner(t.set, CX, 2, CX + 1, "magma_cube")
    for x in (4, 12):
        c.place_chest(t, x, 1, 6, "north", MID, "brasero", kind="barrel")
        t.set(x, 2, 6, "soul_campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    pieces.connect(t)
    return t


def broken(p, name):
    """Broken altar: fallen pillars (their drums on the ground), magma cracks and two magma cubes on guard."""
    t = _clearing(p, name, broken=True)
    for x, z in ((1, 5), (1, 6), (15, 10), (15, 11), (10, 15)):
        t.set(x, 1, z, p["tambor"])
    for x, z in ((4, 9), (12, 7), (9, 3)):
        t.set(x, 0, z, "magma_block")
    c.place_chest(t, CX, 4, CX, "north", MID, "ofrendas")
    c.place_chest(t, 3, 1, 8, "east", MID, "brasero", kind="barrel")
    for x in (4, 12):
        t.entity(x, 1, 12, c.mob("magma_cube", MID, rot=180.0, Size=1))
    pieces.connect(t)
    return t


STYLES = {
    "deltas": dict(biomas=["basalt_deltas"], convencionales=[],
                   paleta=dict(suelo=["minecraft:polished_basalt[axis=y]", "minecraft:smooth_basalt",
                                      "minecraft:polished_blackstone", "minecraft:smooth_basalt"],
                               pilar="polished_basalt[axis=y]", capitel="chiseled_polished_blackstone",
                               grada="polished_blackstone_bricks", escalon="polished_blackstone_brick_stairs",
                               ara="chiseled_polished_blackstone", tambor="basalt[axis=x]"),
                   variantes={"a": main, "b": broken}),
    "yermo": dict(biomas=["nether_wastes"], convencionales=[],
                  paleta=dict(suelo=["minecraft:red_nether_bricks", "minecraft:nether_bricks",
                                     "minecraft:blackstone", "minecraft:nether_bricks"],
                              pilar="red_nether_bricks", capitel="chiseled_nether_bricks", grada="nether_bricks",
                              escalon="nether_brick_stairs", ara="chiseled_nether_bricks", tambor="red_nether_bricks"),
                  variantes={"a": main, "b": broken}),
}
