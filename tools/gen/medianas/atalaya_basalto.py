"""Atalaya de basalto (heraldia:medianas/atalaya_basalto/<estilo>, Nether): una torre de 5 x 5 de basalto pulido en un
patio de 15 x 15, con escalera de mano hasta una terraza almenada y faroles de almas. Variante a: la atalaya entera, de
cuatro plantas, con un arquero esqueleto en la terraza y el cofre del vigía arriba; b: la atalaya y el arranque de un
puente de basalto (un tramo roto que vuela hacia el sur), con el cofre al pie y otro en el puente.

Estilos: deltas (deltas de basalto) y almas (valle de arena de almas: piedra negra, huesos y fuego de almas). Botín
acorde: flechas, huesos, cuarzo, antorchas de almas, oro; nada de netherita."""
from core import Template, F
from loot import item, empty
from unicas._comun import botin, piezas
from . import _comun as c

MID = "atalaya_basalto"
DIMENSION = "nether"
NOMBRE = {"es_es": "Atalaya de basalto", "en_us": "Basalt Watchtower"}
SEPARACION = 640
LOGRO_ICONO = "minecraft:polished_basalt"
LANG = botin.lang("heraldia.medianas.atalaya_basalto.", {
    "vigia": ("Vigía de ceniza", "Ash Lookout"),
})
LOOT = {
    "vigia": botin.cofre(((2, 4), [item("arrow", 10, 4, 12), item("bone", 8, 2, 6), item("quartz", 6, 2, 6),
                                   item("soul_torch", 6, 2, 6), item("gold_nugget", 6, 2, 6), item("spyglass", 1),
                                   item("bow", 2, dmg=(0.3, 0.8)), item("glowstone_dust", 4, 2, 5), empty(4)]),
                         ((1, 1), [item("gold_ingot", 3), item("spectral_arrow", 2, 2, 5), item("fire_charge", 2),
                                   empty(8)])),
    "puente": botin.table(botin.pool((1, 3), [item("bone", 6, 1, 4), item("arrow", 5, 2, 6), item("quartz", 4, 1, 3),
                                              item("soul_torch", 4, 1, 3), item("gold_nugget", 4, 1, 3), empty(6)])),
}

L = 15
X0, Z0, X1, Z1 = 5, 5, 9, 9       # muros de la torre (5 x 5)
CX = 7


def _suelo(p):
    mats = p["suelo"]
    return lambda x, z: mats[(x * 3 + z * 7 + x * z) % len(mats)]


def _torre(t, p, plantas):
    """Torre de `plantas` plantas de 4 de alto (suelos en y = 0, 4, 8...), escalera de mano pegada al muro sur y
    terraza almenada encima. Devuelve la altura de la terraza."""
    techo = 4 * plantas
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    c.caja(t, X0, 1, Z0, X1, techo, Z1, p["muro"], esquina=p["esquina"])
    for k in range(1, plantas):                      # forjados de las plantas, con el hueco de la escalera
        t.fill(X0 + 1, 4 * k, Z0 + 1, X1 - 1, 4 * k, Z1 - 1, p["forjado"])
    t.fill(X0, techo, Z0, X1, techo, Z1, p["forjado"])
    c.escalera_mano(t, CX, Z1 - 1, 1, techo, "north")
    for x in range(X0, X1 + 1):                     # almenas
        for z in range(Z0, Z1 + 1):
            if (x in (X0, X1) or z in (Z0, Z1)) and (x + z) % 2 == 0:
                t.set(x, techo + 1, z, p["almena"])
    for x, z in ((X0, Z0), (X1, Z0), (X0, Z1), (X1, Z1)):
        t.set(x, techo + 2, z, "soul_lantern[hanging=false,waterlogged=false]")
    for k in range(plantas):                        # saeteras y faroles por planta
        y = 4 * k + 2
        for x, z in ((CX, Z0), (X0, CX), (X1, CX)):
            if (x, z) != (CX, Z0) or k:
                t.set(x, y, z, "iron_bars")
        c.farol(t, CX - 1, 4 * k + 3, CX)
    # puerta al norte
    t.set(CX, 1, Z0, "air")
    t.set(CX, 2, Z0, "air")
    c.door(t, CX, 1, Z0, "north", p["puerta"])
    return techo


def entera(p, name):
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=4)
    c.entrada(t, CX, p["suelo"][0])
    techo = _torre(t, p, 4)
    c.cofre(t, X0 + 1, techo + 1, Z0 + 1, "south", MID, "vigia")
    t.entity(X1 - 1, techo + 1, Z0 + 1, c.mob("skeleton", MID, "vigia", "Vigía de ceniza", rot=180.0,
                                              equipment={"mainhand": {"id": "minecraft:bow", "count": 1}}))
    for x, z in ((2, 3), (12, 11), (3, 12)):
        t.set(x, 1, z, p["adorno"])
    piezas.connect(t)
    return t


def puente(p, name):
    """Atalaya de tres plantas y el arranque del puente: un tablero de 3 de ancho que sale de la terraza hacia el sur
    sobre pilas y se corta en seco (con su barandilla), y una escalera de losa desde el patio."""
    t = Template(name)
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p), aire=4)
    c.entrada(t, CX, p["suelo"][0])
    techo = _torre(t, p, 3)
    # tablero del puente a la altura de la terraza, de z = Z1 + 1 a 13, con barandilla de muro
    for z in range(Z1 + 1, L - 1):
        for x in range(CX - 1, CX + 2):
            t.set(x, techo, z, p["forjado"])
        t.set(CX - 2, techo + 1, z, p["almena"])
        t.set(CX + 2, techo + 1, z, p["almena"])
    t.set(CX, techo + 1, Z1, "air")                   # paso de la terraza al puente
    for z in (11, 13):                                 # pilas
        for y in range(1, techo):
            t.set(CX, y, z, p["esquina"])
    c.cofre(t, CX + 1, techo + 1, L - 2, "north", MID, "puente", kind="barrel")
    c.cofre(t, X1 + 2, 1, Z0 + 1, "west", MID, "vigia")
    for x, z in ((2, 3), (12, 2)):
        t.set(x, 1, z, p["adorno"])
    piezas.connect(t)
    return t


ESTILOS = {
    "deltas": dict(biomas=["basalt_deltas"], convencionales=[],
                   paleta=dict(suelo=["minecraft:smooth_basalt", "minecraft:polished_basalt[axis=y]",
                                      "minecraft:polished_blackstone", "minecraft:smooth_basalt"],
                               zocalo="polished_blackstone", muro="polished_basalt[axis=y]", esquina="basalt[axis=y]",
                               forjado="polished_blackstone_bricks", almena="polished_blackstone_wall",
                               puerta="crimson_door", adorno="basalt[axis=y]"),
                   variantes={"a": entera, "b": puente}),
    "almas": dict(biomas=["soul_sand_valley"], convencionales=[],
                  paleta=dict(suelo=["minecraft:polished_blackstone", "minecraft:polished_blackstone_bricks",
                                     "minecraft:smooth_basalt", "minecraft:polished_blackstone"],
                              zocalo="polished_blackstone", muro="polished_blackstone_bricks", esquina="polished_basalt[axis=y]",
                              forjado="polished_blackstone", almena="blackstone_wall", puerta="warped_door",
                              adorno="bone_block[axis=y]"),
                  variantes={"a": entera, "b": puente}),
}
