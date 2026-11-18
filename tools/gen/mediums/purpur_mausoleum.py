"""Mausoleo púrpura (heraldia:medianas/mausoleo_purpura/<estilo>, End, islas exteriores): un recinto de 17 x 17 con un
mausoleo de púrpura de 9 x 9, de bóveda escalonada, donde reposa un viajero que no volvió del vacío. Variante a: la
cripta cerrada con el sarcófago (losas de púrpura sobre un zócalo), el cofre del ajuar a sus pies y un generador de
endermites dentro del sarcófago; b: el mausoleo abierto (sin muro sur, pilares rotos) con dos tumbas y el cofre del ajuar.

Estilos: altas (tierras altas del End) y medias (tierras medias y yermos del End). Botín acorde: perlas de ender, fruta
coral, oro, hierro, velas; nada de élitros ni netherita."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot, pieces
from . import _common as c

MID = "mausoleo_purpura"
DIMENSION = "end"
DISPLAY_NAME = {"es_es": "Mausoleo púrpura", "en_us": "Purpur Mausoleum"}
SEPARATION = 896
ADVANCEMENT_ICON = "minecraft:purpur_pillar"
LOOT = {
    "ajuar": chest_loot.cofre(((2, 4), [item("ender_pearl", 8, 1, 3), item("chorus_fruit", 6, 2, 5), item("gold_ingot", 5, 1, 3),
                                   item("iron_ingot", 6, 1, 4), item("candle", 5, 1, 3), item("bone", 5, 1, 4),
                                   item("golden_helmet", 2, dmg=(0.3, 0.7)), item("book", 2, rand_ench=True),
                                   item("purpur_block", 4, 2, 6), empty(5)]),
                         ((1, 1), [item("ender_eye", 2), item("emerald", 3, 1, 3), item("golden_apple", 1),
                                   empty(8)])),
}

L = 17
CX = 8
M0, M1 = 4, 12          # mausoleo de 9 x 9


def _floor(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 3 + z * 5 + x * z) % len(mats)]


def _enclosure(p, name):
    t = Template(name)
    c.courtyard(t, 0, 0, L - 1, L - 1, _floor(p), air_block=9)
    c.entrance(t, CX, p["suelo"][0])
    for x in range(L):                                        # pretil bajo alrededor, abierto al norte
        for z in range(L):
            if (x in (0, L - 1) or z in (0, L - 1)) and not (z == 0 and CX - 1 <= x <= CX + 1):
                t.set(x, 1, z, p["pretil"])
    for x in (CX - 2, CX + 2):
        t.set(x, 2, 0, "end_rod[facing=up]")
        t.set(x, 1, 0, p["pilar"])
    return t


def _vault(t, p, y):
    """Bóveda escalonada de tres hiladas sobre los muros (y es la primera)."""
    for k in range(3):
        a, b = M0 + k, M1 - k
        t.fill(a, y + k, a, b, y + k, b, p["muro"])
        if k < 2:
            t.fill(a + 1, y + k, a + 1, b - 1, y + k, b - 1, "air")
    t.set(CX, y + 3, CX, "end_rod[facing=up]")


def crypt(p, name):
    t = _enclosure(p, name)
    c.box(t, M0, 1, M0, M1, 5, M1, p["muro"], corner_block=p["pilar"], floor=p["piso"])
    _vault(t, p, 6)
    for y in (1, 2, 3):                                        # portada de 3 x 3 al norte
        for x in (CX - 1, CX, CX + 1):
            t.set(x, y, M0, "air")
    # sarcófago al fondo: zócalo y tapa de losas
    for x in (CX - 1, CX, CX + 1):
        t.set(x, 1, M1 - 2, p["zocalo"])
        t.set(x, 2, M1 - 2, f"{p['losa']}[type=bottom,waterlogged=false]")
    c.cofre(t, CX, 1, M1 - 4, "north", MID, "ajuar")
    pieces.spawner(t.set, CX, 1, M1 - 2, "endermite")           # dentro del sarcófago, bajo la tapa
    for x in (M0 + 1, M1 - 1):
        t.set(x, 1, M1 - 1, "candle[candles=3,lit=true,waterlogged=false]")
        c.lantern(t, x, 5, M0 + 2)
    pieces.connect(t)
    return t


def abierto(p, name):
    t = _enclosure(p, name)
    t.fill(M0, 0, M0, M1, 0, M1, p["piso"])
    for x, z in ((M0, M0), (M1, M0), (M0, M1), (M1, M1), (CX, M0), (CX, M1)):
        height = 3 if (x, z) in ((M1, M1), (CX, M1)) else 6
        for y in range(1, height + 1):
            t.set(x, y, z, p["pilar"])
    t.fill(M0, 7, M0, M1, 7, M0 + 4, p["muro"])                 # media bóveda que queda en pie, al norte
    for x in (CX - 2, CX + 2):                                 # dos tumbas
        for z in (CX, CX + 1, CX + 2):
            t.set(x, 1, z, f"{p['losa']}[type=bottom,waterlogged=false]")
    c.cofre(t, CX, 1, CX + 1, "north", MID, "ajuar")
    t.set(CX, 1, CX + 3, "candle[candles=2,lit=true,waterlogged=false]")
    pieces.connect(t)
    return t


STYLES = {
    "altas": dict(biomas=["end_highlands"], convencionales=[],
                  paleta=dict(suelo=["minecraft:end_stone_bricks", "minecraft:purpur_block", "minecraft:end_stone_bricks"],
                              pretil="end_stone_brick_wall", pilar="purpur_pillar[axis=y]", muro="purpur_block",
                              piso="purpur_block", zocalo="end_stone_bricks", losa="purpur_slab"),
                  variantes={"a": crypt, "b": abierto}),
    "medias": dict(biomas=["end_midlands", "end_barrens"], convencionales=[],
                   paleta=dict(suelo=["minecraft:purpur_block", "minecraft:end_stone_bricks", "minecraft:purpur_block"],
                               pretil="purpur_slab[type=bottom,waterlogged=false]", pilar="purpur_pillar[axis=y]",
                               muro="end_stone_bricks", piso="end_stone_bricks", zocalo="purpur_block",
                               losa="end_stone_brick_slab"),
                   variantes={"a": crypt, "b": abierto}),
}
