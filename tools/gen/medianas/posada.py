"""Posada de camino (heraldia:medianas/posada/<estilo>): casa de 15 x 9 con sala común (mostrador, hogar y dos mesas),
el posadero (aldeano quieto con tratos fijos: comida y una cama para el viajero) y un cuarto con dos camas y un cofre.
Variante a: con corral de paja y abrevadero al sur; b: con huerto al sur. Sin monstruos."""
from core import Template
from loot import item, empty
from unicas._comun import botin, piezas
from . import _comun as c

MID = "posada"
NOMBRE = {"es_es": "Posada de camino", "en_us": "Roadside Inn"}
SEPARACION = 704
LOGRO_ICONO = "minecraft:bread"
LANG = botin.lang("heraldia.medianas.posada.", {
    "posadero": ("Posadero", "Innkeeper"),
    "cartel1": ("Posada", "Inn"),
    "cartel2": ("del Camino", "of the Road"),
})
LOOT = {
    "cuarto": botin.cofre(((2, 4), [item("bread", 8, 1, 3), item("cookie", 5, 2, 6), item("candle", 5, 1, 2),
                                    item("paper", 5, 1, 4), item("book", 3), item("leather_boots", 2, dmg=(0.4, 0.9)),
                                    item("gold_nugget", 4, 1, 4), item("compass", 1), empty(6)]),
                          ((1, 1), [item("emerald", 3, 1, 2), empty(8)])),
    "despensa": botin.cofre(((3, 5), [item("bread", 8, 1, 4), item("baked_potato", 6, 1, 4), item("cooked_chicken", 5, 1, 2),
                                      item("apple", 6, 1, 3), item("honey_bottle", 3), item("sugar", 4, 1, 3),
                                      item("milk_bucket", 1), item("egg", 4, 1, 3), empty(4)]),
                            ((1, 1), [item("cake", 1), item("pumpkin_pie", 3), empty(8)])),
}

X0, Z0, X1, Z1 = 2, 4, 16, 12      # muros de la casa (15 x 9)
TABIQUE = 11                       # muro entre la sala (oeste) y el cuarto (este)
PUERTA = 6                         # puerta de la calle, en el muro norte
ANCHO, FONDO = 19, 18              # patio


def ofertas():
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.oferta(em(1), {"id": "minecraft:bread", "count": 6}, 12),
            c.oferta(em(1), {"id": "minecraft:cooked_porkchop", "count": 3}, 12),
            c.oferta(em(2), {"id": "minecraft:white_bed", "count": 1}, 3),
            c.oferta({"id": "minecraft:wheat", "count": 18}, em(1), 12)]


def _suelo(p):
    mats = p["patio"]
    return lambda x, z: "minecraft:dirt_path" if x == PUERTA and z < Z0 else mats[(x * 5 + z * 11 + x * z) % len(mats)]


def _casa(p, name):
    t = Template(name)
    m = p["madera"]
    c.patio(t, 0, 0, ANCHO - 1, FONDO - 1, _suelo(p))
    c.entrada(t, PUERTA, f"{p['peldano']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    # muros: entramado (troncos en esquinas y cada 4) y paños de `muro`, zócalo en y = 0, techo en y = 5
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    c.caja(t, X0, 1, Z0, X1, 4, Z1, p["muro"])
    for x in range(X0, X1 + 1, 4):
        for z in (Z0, Z1):
            t.fill(x, 1, z, x, 4, z, p["tronco"] + "[axis=y]")
    for z in (Z0, Z1):
        t.fill(X1, 1, z, X1, 4, z, p["tronco"] + "[axis=y]")
    t.fill(X0, 5, Z0, X1, 5, Z1, f"{m}_planks")
    cumbre = c.tejado(t, X0, Z0, X1, Z1, 5, p["teja"], p["cumbrera"], p["muro"])
    # chimenea del hogar (muro oeste) hasta por encima de la cumbrera
    t.set(X0 + 1, 1, 8, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    for z in (7, 9):
        t.fill(X0 + 1, 1, z, X0 + 1, 4, z, "bricks")
    t.fill(X0 + 1, 2, 8, X0 + 1, 4, 8, "bricks")
    t.fill(X0 + 1, 5, 8, X0 + 1, cumbre + 2, 8, "bricks")
    # tabique y su puerta
    t.fill(TABIQUE, 1, Z0 + 1, TABIQUE, 4, Z1 - 1, p["muro"])
    c.door(t, TABIQUE, 1, 8, "east", f"{m}_door")
    c.door(t, PUERTA, 1, Z0, "south", f"{m}_door")
    piezas.sign(c.put(t), PUERTA + 2, 3, Z0 - 1, "north", [c.texto(MID, "cartel1", "Posada"),
                                                          c.texto(MID, "cartel2", "del Camino")], wood=m)
    # ventanas
    for x in (4, 8, 13):
        c.ventana(t, x, 2, Z0)
        c.ventana(t, x, 2, Z1)
    c.ventana(t, X1, 2, 8)
    # sala: mostrador al sur (con hueco al oeste), posadero detrás, toneles, dos mesas y faroles
    for x in range(8, TABIQUE):
        t.set(x, 1, Z1 - 2, f"stripped_{p['tronco']}[axis=x]")
    t.set(TABIQUE - 1, 1, Z1 - 1, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    c.cofre(t, TABIQUE - 1, 2, Z1 - 1, "west", MID, "despensa", kind="barrel")
    t.entity(9, 1, Z1 - 1, c.aldeano(MID, "posadero", "Posadero", "butcher", p["aldeano"], ofertas(), rot=180.0))
    c.mesa(t, 5, 6, m)
    c.mesa(t, 5, 10, m)
    c.farol(t, 5, 4, 8)
    c.farol(t, 9, 4, 7)
    # cuarto: dos camas contra el muro este, cofre entre ellas, farol
    c.cama(t, X1 - 1, Z0 + 1, "east", p["cama"])
    c.cama(t, X1 - 1, Z1 - 1, "east", p["cama"])
    c.cofre(t, X1 - 1, 1, 8, "west", MID, "cuarto")
    c.farol(t, 13, 4, 8)
    return t


def corral(p, name):
    """Con corral de paja y abrevadero al sur de la casa (sin animales: los traen los viajeros)."""
    t = _casa(p, name)
    m = p["madera"]
    x0, x1, z0, z1 = 3, 15, Z1 + 1, FONDO - 1
    for x in range(x0, x1 + 1):
        for z in (z0 + 1, z1):
            t.set(x, 1, z, f"{m}_fence")
    for z in range(z0 + 1, z1 + 1):
        t.set(x0, 1, z, f"{m}_fence")
        t.set(x1, 1, z, f"{m}_fence")
    t.set(9, 1, z0 + 1, f"{m}_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    t.set(5, 1, z1 - 1, "hay_block[axis=y]")
    t.set(6, 1, z1 - 1, "hay_block[axis=y]")
    t.set(5, 2, z1 - 1, "hay_block[axis=y]")
    t.set(13, 1, z1 - 1, "water_cauldron[level=3]")
    t.set(12, 1, z1 - 1, "water_cauldron[level=3]")
    return t


def huerto(p, name):
    """Con huerto al sur de la casa: bancales con cultivo en cada casilla y una acequia de una fuente."""
    t = _casa(p, name)
    cultivos = p["cultivos"]
    for x in range(4, 15):
        for z in range(Z1 + 2, FONDO - 1):
            if (x, z) == (9, Z1 + 3):
                t.set(x, 0, z, "water[level=0]")
                continue
            t.set(x, 0, z, "farmland[moisture=7]")
            t.set(x, 1, z, cultivos[(x // 2) % len(cultivos)])
    t.set(15, 1, Z1 + 2, "composter[level=0]")
    return t


_CULTIVOS = ["wheat[age=7]", "carrots[age=7]", "potatoes[age=7]", "beetroots[age=3]"]
ESTILOS = {
    "llanura": dict(biomas=["plains", "sunflower_plains"], convencionales=["c:is_plains"],
                    paleta=dict(madera="oak", tronco="spruce_log", muro="oak_planks", zocalo="cobblestone",
                                teja="spruce_stairs", cumbrera="spruce_planks", peldano="cobblestone_stairs",
                                cama="red", aldeano="plains", cultivos=_CULTIVOS,
                                patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:dirt_path"]),
                    variantes={"a": corral, "b": huerto}),
    "bosque": dict(biomas=["forest", "birch_forest", "old_growth_birch_forest", "flower_forest"],
                   convencionales=["c:is_birch_forest", "c:is_flower_forest"],
                   paleta=dict(madera="birch", tronco="dark_oak_log", muro="birch_planks", zocalo="stone_bricks",
                               teja="dark_oak_stairs", cumbrera="dark_oak_planks", peldano="stone_brick_stairs",
                               cama="green", aldeano="plains", cultivos=_CULTIVOS,
                               patio=["minecraft:dirt_path", "minecraft:cobblestone", "minecraft:dirt_path"]),
                   variantes={"a": corral, "b": huerto}),
    "sabana": dict(biomas=["savanna", "savanna_plateau", "windswept_savanna"],
                   convencionales=["minecraft:is_savanna", "c:is_savanna"],
                   paleta=dict(madera="acacia", tronco="acacia_log", muro="white_terracotta", zocalo="smooth_sandstone",
                               teja="acacia_stairs", cumbrera="acacia_planks", peldano="smooth_sandstone_stairs",
                               cama="orange", aldeano="savanna", cultivos=["wheat[age=7]", "beetroots[age=3]"],
                               patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:smooth_sandstone"]),
                   variantes={"a": corral, "b": huerto}),
}
