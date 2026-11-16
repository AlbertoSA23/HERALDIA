"""Torre de vigía (heraldia:medianas/torre_vigia/<estilo>): torre cuadrada de 7 x 7 en un patio de 15 x 15 con su
hoguera arriba. Variante a: tres plantas y atalaya cubierta con un arquero esqueleto (el reto); b: dos plantas, terraza
descubierta y un cobertizo de leña adosado, sin mobs."""
from core import Template, F
from loot import item, empty
from unicas._comun import botin
from . import _comun as c

MID = "torre_vigia"
NOMBRE = {"es_es": "Torre de vigía", "en_us": "Watchtower"}
SEPARACION = 640
LOGRO_ICONO = "minecraft:spyglass"
LANG = botin.lang("heraldia.medianas.torre_vigia.", {
    "arquero": ("Vigía del camino", "Road Watcher"),
})
LOOT = {
    "vigia": botin.cofre(((2, 4), [item("arrow", 10, 4, 12), item("bread", 8, 1, 3), item("torch", 6, 2, 6),
                                   item("iron_nugget", 6, 2, 6), item("coal", 6, 1, 4), item("string", 4, 1, 3),
                                   item("spyglass", 1), item("map", 2), item("bow", 2, dmg=(0.3, 0.8)), empty(4)]),
                         ((1, 2), [item("emerald", 3), item("iron_ingot", 2), item("arrow", 4, 2, 6), empty(8)])),
    "provisiones": botin.cofre(((2, 4), [item("bread", 8, 1, 4), item("apple", 6, 1, 3), item("cooked_mutton", 4, 1, 2),
                                         item("wheat", 6, 2, 5), item("leather", 3), item("candle", 3, 1, 2), empty(6)]),
                               ((1, 1), [item("emerald", 2), empty(8)])),
}

L = 15                # patio de 15 x 15
X0, Z0, X1, Z1 = 4, 5, 10, 11   # muros de la torre (7 x 7)
CX = 7                # eje de la puerta y de la escalera de mano


def _suelo(p):
    mats = p["patio"]
    return lambda x, z: "minecraft:dirt_path" if x == CX and z < Z0 else mats[(x * 7 + z * 13 + x * z) % len(mats)]


def _torre(t, p, plantas, cubierta):
    """Torre de `plantas` plantas de 4 de alto (suelos en y = 0, 5, 9...), terraza con almenas y hoguera."""
    m = p["madera"]
    techo = 5 + 4 * (plantas - 1)                          # suelo de la terraza
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    c.caja(t, X0, 1, Z0, X1, techo - 1, Z1, p["muro"], esquina=p["esquina"])
    for y in range(5, techo + 1, 4):                      # forjados (el último es la terraza)
        t.fill(X0 + 1, y, Z0 + 1, X1 - 1, y, Z1 - 1, f"{m}_planks")
        t.fill(X0, y, Z0, X1, y, Z1, p["muro"], keep=True)
        for x, z in ((X0, Z0), (X0, Z1), (X1, Z0), (X1, Z1)):
            t.set(x, y, z, p["esquina"])
    c.escalera_mano(t, CX, Z1 - 1, 1, techo, "north")      # pegada al muro sur, atraviesa los forjados
    c.door(t, CX, 1, Z0, "south", f"{m}_door")
    # saeteras: en el centro de los muros este y oeste de cada planta y en el norte de las de arriba
    for k in range(plantas):
        y = 2 + 4 * k + (1 if k else 0)
        c.ventana(t, X0, y, 8)
        c.ventana(t, X1, y, 8)
        if k:
            c.ventana(t, CX, y, Z0)
        t.set(X1 - 1, 3 + 4 * k, Z0 + 1, "wall_torch[facing=south]")
        t.set(X0 + 1, 3 + 4 * k, Z0 + 1, "wall_torch[facing=south]")
    # almenas: merlón en las casillas pares del anillo; en las esquinas, pilares (que sostienen la cubierta)
    y = techo + 1
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            if x in (X0, X1) or z in (Z0, Z1):
                corner = x in (X0, X1) and z in (Z0, Z1)
                if corner:
                    for yy in range(y, y + (3 if cubierta else 1)):
                        t.set(x, yy, z, p["esquina"])
                elif (x + z) % 2 == 0:
                    t.set(x, y, z, p["muro"])
            else:
                for yy in range(y, y + 3):
                    t.set(x, yy, z, "air")
    t.set(CX, y, 8, "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    if cubierta:
        t.fill(X0 - 1, y + 3, Z0 - 1, X1 + 1, y + 3, Z1 + 1, f"{m}_slab[type=bottom,waterlogged=false]")
        c.farol(t, CX, y + 2, 8)
    return techo


def _patio(t, p):
    c.patio(t, 0, 0, L - 1, L - 1, _suelo(p))
    c.entrada(t, CX, f"{p['peldano']}[facing=south,half=bottom,shape=straight,waterlogged=false]")
    m = p["madera"]
    for x in (CX - 2, CX + 2):                             # faroles a los lados del camino
        t.set(x, 1, 2, f"{m}_fence")
        c.farol(t, x, 2, 2, colgado=False)


def alta(p, name):
    """Tres plantas (almacén, dormitorio, armería) y atalaya cubierta con el arquero."""
    t = Template(name)
    _patio(t, p)
    m = p["madera"]
    techo = _torre(t, p, 3, cubierta=True)
    c.cofre(t, X0 + 1, 1, Z0 + 2, "east", MID, "vigia")
    c.cofre(t, X0 + 1, 1, Z0 + 3, "east", MID, "provisiones", kind="barrel")
    t.set(X1 - 1, 1, Z1 - 1, "crafting_table")
    c.cama(t, X0 + 1, Z1 - 2, "west", "red", y=6)
    c.farol(t, X1 - 1, 8, Z0 + 2)
    t.set(X1 - 1, 10, Z0 + 2, "fletching_table")
    t.set(X1 - 1, 10, Z0 + 3, f"{m}_slab[type=bottom,waterlogged=false]")
    t.entity(X0 + 1, techo + 1, Z0 + 1, c.mob(
        "skeleton", MID, "arquero", LANG["es_es"]["heraldia.medianas.torre_vigia.arquero"], rot=180.0,
        equipment={"mainhand": {"id": "minecraft:bow", "count": 1}, "head": {"id": "minecraft:chainmail_helmet", "count": 1}},
        drop_chances={"head": F(0.0)}))
    return t


def baja(p, name):
    """Dos plantas, terraza descubierta y cobertizo de leña adosado al este; sin mobs."""
    t = Template(name)
    _patio(t, p)
    m = p["madera"]
    _torre(t, p, 2, cubierta=False)
    c.cofre(t, X0 + 1, 1, Z0 + 2, "east", MID, "vigia")
    c.cama(t, X0 + 1, Z1 - 2, "west", "blue", y=6)
    t.set(X1 - 1, 6, Z0 + 1, "crafting_table")
    # cobertizo: postes en x = 13, tejadillo de losas en y = 4, leña y paja dentro, abierto al norte
    for z in (Z0 + 1, Z1 - 1):
        for y in (1, 2, 3):
            t.set(X1 + 3, y, z, f"{m}_fence")
    t.fill(X1 + 1, 4, Z0 + 1, X1 + 3, 4, Z1 - 1, f"{m}_slab[type=bottom,waterlogged=false]")
    for z in range(Z0 + 2, Z1 - 1):
        t.set(X1 + 1, 1, z, f"{p['tronco']}[axis=z]")
    t.set(X1 + 1, 2, Z0 + 3, f"{p['tronco']}[axis=z]")
    t.set(X1 + 2, 1, Z1 - 1, "hay_block[axis=y]")
    c.cofre(t, X1 + 2, 1, Z1 - 2, "west", MID, "provisiones", kind="barrel")
    c.farol(t, X1 + 2, 3, 8)
    return t


ESTILOS = {
    "colinas": dict(biomas=["windswept_hills", "windswept_gravelly_hills", "windswept_forest", "windswept_savanna",
                            "meadow"],
                    convencionales=["c:is_windswept"],
                    paleta=dict(muro="stone_bricks", esquina="polished_andesite", zocalo="cobblestone", madera="spruce",
                                tronco="spruce_log", peldano="cobblestone_stairs",
                                patio=["minecraft:cobblestone", "minecraft:dirt_path", "minecraft:mossy_cobblestone",
                                       "minecraft:dirt_path"]),
                    variantes={"a": alta, "b": baja}),
    "taiga": dict(biomas=["taiga", "old_growth_pine_taiga", "old_growth_spruce_taiga", "snowy_taiga"],
                  convencionales=["minecraft:is_taiga", "c:is_taiga"],
                  paleta=dict(muro="cobblestone", esquina="stripped_spruce_log[axis=y]", zocalo="mossy_cobblestone",
                              madera="spruce", tronco="spruce_log", peldano="spruce_stairs",
                              patio=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:dirt_path",
                                     "minecraft:cobblestone"]),
                  variantes={"a": alta, "b": baja}),
}
