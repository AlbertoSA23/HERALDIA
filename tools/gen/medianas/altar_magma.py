"""Altar de magma (heraldia:medianas/altar_magma/<estilo>, Nether): un claro de 17 x 17 con un anillo de pilares de
basalto y piedra negra y, en medio, un altar de tres gradas con calderos de lava (la lava queda contenida: nunca suelta)
y el cofre de las ofrendas. Variante a: el altar mayor con un generador de cubos de magma bajo el ara y braseros; b: el
altar roto (pilares caídos, grietas de magma entre las losas) con dos cubos de magma de guardia.

Estilos: deltas (deltas de basalto: basalto pulido y basalto liso) y yermo (desiertos del Nether: piedra negra y ladrillo
rojo del Nether). Botín acorde: crema de magma, polvo de blaze, cargas ígneas, oro; nada de netherita."""
from core import Template
from loot import item, empty
from unicas._comun import botin, piezas
from . import _comun as c

MID = "altar_magma"
DIMENSION = "nether"
NOMBRE = {"es_es": "Altar de magma", "en_us": "Magma Altar"}
SEPARACION = 640
LOGRO_ICONO = "minecraft:magma_cream"
LOOT = {
    "ofrendas": botin.cofre(((2, 4), [item("magma_cream", 8, 1, 4), item("blaze_powder", 6, 1, 3),
                                      item("fire_charge", 6, 1, 3), item("gold_nugget", 8, 2, 7),
                                      item("quartz", 6, 2, 5), item("gold_ingot", 3), item("obsidian", 3, 1, 2),
                                      item("book", 2, rand_ench=True), empty(5)]),
                            ((1, 1), [item("blaze_rod", 3), item("golden_apple", 1), item("gold_ingot", 3, 1, 2),
                                      empty(8)])),
    "brasero": botin.table(botin.pool((1, 2), [item("magma_cream", 6, 1, 2), item("coal", 5, 1, 3),
                                               item("gold_nugget", 5, 1, 4), item("fire_charge", 2), empty(6)])),
}

L = 17
CX = 8
RING = [(3, 3), (8, 2), (13, 3), (14, 8), (13, 13), (8, 14), (3, 13), (2, 8)]


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 5 + z * 11 + x * z) % len(mats)]


def _claro(p, name, roto):
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=8)
    c.entrada(t, CX, p["suelo"][0])
    # anillo de pilares (los del norte, a los lados de la entrada; enteros o caídos)
    for i, (x, z) in enumerate(RING):
        if (x, z) == (CX, 2):
            continue
        alto = 2 if roto and i % 2 else 5
        for y in range(1, alto + 1):
            t.set(x, y, z, p["pilar"])
        if alto == 5:
            t.set(x, 6, z, p["capitel"])
    # altar de tres gradas: 7 x 7, 5 x 5 y 3 x 3, escalones al norte
    for n, (a, b) in enumerate(((5, 11), (6, 10), (7, 9))):
        y = n + 1
        for x in range(a, b + 1):
            for z in range(a, b + 1):
                t.set(x, y, z, p["grada"])
        t.set(CX, y, a, f"{p['escalon']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    # calderos de lava en las esquinas de la grada baja
    for x, z in ((5, 5), (11, 5), (5, 11), (11, 11)):
        t.set(x, 2, z, "lava_cauldron")
    return t


def mayor(p, name):
    """Altar entero: el ara con el cofre de las ofrendas encima, el generador de cubos de magma debajo (encerrado en la
    grada) y dos braseros (barriles) junto a la entrada."""
    t = _claro(p, name, roto=False)
    t.set(CX, 4, CX, p["ara"])
    c.cofre(t, CX, 4, CX + 1, "north", MID, "ofrendas")
    piezas.spawner(t.set, CX, 2, CX + 1, "magma_cube")
    for x in (4, 12):
        c.cofre(t, x, 1, 6, "north", MID, "brasero", kind="barrel")
        t.set(x, 2, 6, "soul_campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    piezas.connect(t)
    return t


def roto(p, name):
    """Altar roto: pilares caídos (sus tambores en el suelo), grietas de magma y dos cubos de magma de guardia."""
    t = _claro(p, name, roto=True)
    for x, z in ((1, 5), (1, 6), (15, 10), (15, 11), (10, 15)):
        t.set(x, 1, z, p["tambor"])
    for x, z in ((4, 9), (12, 7), (9, 3)):
        t.set(x, 0, z, "magma_block")
    c.cofre(t, CX, 4, CX, "north", MID, "ofrendas")
    c.cofre(t, 3, 1, 8, "east", MID, "brasero", kind="barrel")
    for x in (4, 12):
        t.entity(x, 1, 12, c.mob("magma_cube", MID, rot=180.0, Size=1))
    piezas.connect(t)
    return t


ESTILOS = {
    "deltas": dict(biomas=["basalt_deltas"], convencionales=[],
                   paleta=dict(suelo=["minecraft:polished_basalt[axis=y]", "minecraft:smooth_basalt",
                                      "minecraft:polished_blackstone", "minecraft:smooth_basalt"],
                               pilar="polished_basalt[axis=y]", capitel="chiseled_polished_blackstone",
                               grada="polished_blackstone_bricks", escalon="polished_blackstone_brick_stairs",
                               ara="chiseled_polished_blackstone", tambor="basalt[axis=x]"),
                   variantes={"a": mayor, "b": roto}),
    "yermo": dict(biomas=["nether_wastes"], convencionales=[],
                  paleta=dict(suelo=["minecraft:red_nether_bricks", "minecraft:nether_bricks",
                                     "minecraft:blackstone", "minecraft:nether_bricks"],
                              pilar="red_nether_bricks", capitel="chiseled_nether_bricks", grada="nether_bricks",
                              escalon="nether_brick_stairs", ara="chiseled_nether_bricks", tambor="red_nether_bricks"),
                  variantes={"a": mayor, "b": roto}),
}
