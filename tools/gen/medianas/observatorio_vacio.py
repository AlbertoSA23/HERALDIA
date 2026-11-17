"""Observatorio del vacío (heraldia:medianas/observatorio_vacio/<estilo>, End, islas exteriores): una plataforma de
17 x 17 de ladrillo de piedra del End con un observatorio de púrpura que mira al vacío. Variante a: la torre del
anteojo (tres plantas con escalera de mano y, arriba, el anteojo: una línea de varas del End que apunta al cielo) con el
cofre del astrónomo; b: la esfera armilar (un anillo de pilares de púrpura con varas del End) alrededor de la mesa de
cartas, con su cofre y un barril.

Estilos: altas (tierras altas del End) y medias (tierras medias y yermos del End), con piedra y púrpura en distinta
proporción. Botín acorde: perlas de ender, fruta coral, amatista, catalejo, papel; nada de élitros ni netherita."""
from core import Template
from loot import item, empty
from unicas._comun import botin, piezas
from . import _comun as c

MID = "observatorio_vacio"
DIMENSION = "end"
NOMBRE = {"es_es": "Observatorio del vacío", "en_us": "Void Observatory"}
SEPARACION = 896
LOGRO_ICONO = "minecraft:end_rod"
LOOT = {
    "astronomo": botin.cofre(((2, 4), [item("ender_pearl", 8, 1, 3), item("chorus_fruit", 8, 2, 6),
                                       item("popped_chorus_fruit", 5, 1, 4), item("amethyst_shard", 6, 2, 5),
                                       item("paper", 6, 2, 6), item("spyglass", 2), item("glass", 4, 2, 6),
                                       item("map", 2), item("gold_ingot", 3), empty(5)]),
                             ((1, 1), [item("ender_eye", 2), item("emerald", 3, 1, 3), item("book", 2, rand_ench=True),
                                       empty(8)])),
    "cartas": botin.table(botin.pool((1, 3), [item("paper", 6, 2, 6), item("map", 3), item("ink_sac", 4, 1, 3),
                                              item("feather", 4, 1, 3), item("chorus_fruit", 4, 1, 3), empty(6)])),
}

L = 17
CX = 8
X0, Z0, X1, Z1 = 6, 6, 10, 10     # torre de 5 x 5


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 5 + z * 7 + x * z) % len(mats)]


def _plataforma(p, name):
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=6, borde=p["borde"])
    c.entrada(t, CX, p["borde"])
    for x, z in ((0, 0), (L - 1, 0), (0, L - 1), (L - 1, L - 1)):          # varas en las esquinas
        t.set(x, 1, z, "end_rod[facing=up]")
    return t


def torre(p, name):
    t = _plataforma(p, name)
    t.fill(X0, 0, Z0, X1, 0, Z1, p["piso"])
    techo = 12
    c.caja(t, X0, 1, Z0, X1, techo, Z1, p["muro"], esquina=p["pilar"])
    for k in (4, 8):
        t.fill(X0 + 1, k, Z0 + 1, X1 - 1, k, Z1 - 1, p["piso"])
    t.fill(X0, techo, Z0, X1, techo, Z1, p["piso"])
    c.escalera_mano(t, CX, Z1 - 1, 1, techo, "north")
    for k in range(3):                                    # ventanas de cristal morado y faroles por planta
        y = 4 * k + 2
        for x, z in ((X0, CX), (X1, CX)) + (((CX, Z0),) if k else ()):
            t.set(x, y, z, "purple_stained_glass_pane")
        c.farol(t, CX - 1, 4 * k + 3, CX)
    t.set(CX, 1, Z0, "air")
    t.set(CX, 2, Z0, "air")
    c.door(t, CX, 1, Z0, "north", "birch_door")
    # terraza con barandilla y el anteojo (varas del End inclinadas en escalera hacia el norte)
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (X0, X1) or z in (Z0, Z1):
                t.set(x, techo + 1, z, p["barandilla"])
    t.set(CX + 1, techo + 1, CX, p["pilar"])
    for i in range(3):
        t.set(CX + 1, techo + 2 + i, CX, "end_rod[facing=up]")
    c.cofre(t, X0 + 1, techo + 1, Z0 + 1, "south", MID, "astronomo")
    piezas.connect(t)
    return t


def armilar(p, name):
    t = _plataforma(p, name)
    anillo = [(4, 4), (8, 3), (12, 4), (13, 8), (12, 12), (8, 13), (4, 12), (3, 8)]
    for x, z in anillo:
        for y in range(1, 5):
            t.set(x, y, z, p["pilar"])
        t.set(x, 5, z, "end_rod[facing=up]")
    for x in range(CX - 1, CX + 2):                       # mesa de cartas sobre un estrado de losas
        for z in range(CX - 1, CX + 2):
            t.set(x, 1, z, f"{p['losa']}[type=bottom,waterlogged=false]")
    t.set(CX, 1, CX, "cartography_table")
    c.cofre(t, CX, 1, CX + 2, "north", MID, "astronomo")
    c.cofre(t, CX + 2, 1, CX, "west", MID, "cartas", kind="barrel")
    t.set(CX - 2, 1, CX, "lectern[facing=east,has_book=false,powered=false]")
    piezas.connect(t)
    return t


ESTILOS = {
    "altas": dict(biomas=["end_highlands"], convencionales=[],
                  paleta=dict(suelo=["minecraft:end_stone_bricks", "minecraft:end_stone_bricks", "minecraft:purpur_block"],
                              borde="minecraft:purpur_block", piso="end_stone_bricks", muro="end_stone_bricks",
                              pilar="purpur_pillar[axis=y]", barandilla="end_stone_brick_wall", losa="purpur_slab"),
                  variantes={"a": torre, "b": armilar}),
    "medias": dict(biomas=["end_midlands", "end_barrens"], convencionales=[],
                   paleta=dict(suelo=["minecraft:purpur_block", "minecraft:end_stone_bricks", "minecraft:purpur_block"],
                               borde="minecraft:end_stone_bricks", piso="purpur_block", muro="purpur_block",
                               pilar="purpur_pillar[axis=y]", barandilla="end_stone_brick_wall", losa="end_stone_brick_slab"),
                   variantes={"a": torre, "b": armilar}),
}
