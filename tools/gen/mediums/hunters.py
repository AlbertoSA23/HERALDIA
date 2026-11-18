"""Puesto de cazadores (heraldia:medianas/cazadores/<estilo>): claro de 17 x 17 con una cabaña de troncos de 7 x 7
(chimenea de piedra, literas y el arcón de las pieles), un tendedero de pieles, un tajo para la leña y una atalaya de caza
sobre cuatro postes. Variante a: el cazador (aldeano quieto con tratos fijos: compra pieles de conejo, vende cuero,
flechas y una pechera de cuero) y su lobo; b: el puesto vacío, con la fogata apagada y un ahumadero de carne. Sin
monstruos."""
from core import Template
from loot import item, empty
from uniques._common import chest_loot
from . import _common as c

MID = "cazadores"
DISPLAY_NAME = {"es_es": "Puesto de cazadores", "en_us": "Hunters' Lodge"}
SEPARATION = 768
ADVANCEMENT_ICON = "minecraft:rabbit_hide"
LANG = chest_loot.lang("heraldia.medianas.cazadores.", {
    "cazador": ("Cazador", "Hunter"),
    "lobo": ("Colmillo", "Fang"),
})
ADVANCEMENTS = [dict(id="pieles", icono="minecraft:leather", tabla="pieles",
               titulo=("Piel de invierno", "Winter Pelts"),
               descripcion=("Abre el arcón de las pieles de un puesto de cazadores",
                            "Open the pelt chest of a hunters' lodge"))]
LOOT = {
    "pieles": chest_loot.cofre(((3, 5), [item("leather", 10, 1, 4), item("rabbit_hide", 8, 1, 4), item("rabbit_foot", 2),
                                    item("feather", 5, 2, 6), item("cooked_rabbit", 5, 1, 3), item("cooked_mutton", 5, 1, 3),
                                    item("arrow", 6, 4, 12), item("lead", 3), item("leather_horse_armor", 1),
                                    item("bow", 2, dmg=(0.3, 0.8)), empty(4)]),
                          ((1, 1), [item("emerald", 3, 1, 2), item("name_tag", 1), empty(8)])),
    "despensa": chest_loot.cofre(((2, 4), [item("cooked_beef", 5, 1, 3), item("cooked_porkchop", 4, 1, 2),
                                      item("rabbit_stew", 2), item("sweet_berries", 5, 2, 6), item("bread", 5, 1, 3),
                                      item("charcoal", 4, 2, 6), item("string", 4, 1, 3), item("iron_nugget", 4, 2, 5),
                                      empty(6)]),
                            ((1, 1), [item("emerald", 2), empty(8)])),
}

L = 17
X0, Z0, X1, Z1 = 2, 5, 8, 11       # cabaña (7 x 7), puerta al norte
PUERTA = 5


def offers():
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.offer({"id": "minecraft:rabbit_hide", "count": 9}, em(1), 12),
            c.offer(em(1), {"id": "minecraft:leather", "count": 3}, 12),
            c.offer(em(1), {"id": "minecraft:arrow", "count": 16}, 12),
            c.offer(em(4), {"id": "minecraft:leather_chestplate", "count": 1}, 3)]


def _clearing(x, z):
    """Claro redondo: fuera queda el terreno natural."""
    return (x - L // 2) ** 2 + (z - L // 2) ** 2 <= (L // 2 + 0.5) ** 2


def _floor(p):
    mats = p["suelo"]
    return lambda x, z: "minecraft:dirt_path" if x == PUERTA and z < Z0 else mats[(x * 3 + z * 11 + x * z) % len(mats)]


def _outpost(p, name, lit):
    t = Template(name)
    m, tr = p["madera"], p["tronco"]
    c.courtyard(t, 0, 0, L - 1, L - 1, _floor(p), air_block=3, inside=_clearing)
    for x in range(PUERTA - 1, PUERTA + 2):          # el claro es redondo: el borde norte del camino, explícito
        t.set(x, 0, 0, "minecraft:dirt_path")
        for y in (1, 2, 3):
            t.set(x, y, 0, "air")
    c.entrance(t, PUERTA, "minecraft:dirt_path")
    # cabaña de troncos: troncos tumbados que se cruzan en las esquinas
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    for y in range(1, 4):
        for x in range(X0, X1 + 1):
            for z in range(Z0, Z1 + 1):
                if x in (X0, X1) or z in (Z0, Z1):
                    corner_block = x in (X0, X1) and z in (Z0, Z1)
                    axis = "y" if corner_block else ("x" if z in (Z0, Z1) else "z")
                    t.set(x, y, z, f"{tr}[axis={axis}]")
                else:
                    t.set(x, y, z, "air")
    t.fill(X0, 4, Z0, X1, 4, Z1, f"{m}_planks")
    summit = c.roof_tiles(t, X0, Z0, X1, Z1, 4, p["teja"], p["cumbrera"], f"{m}_planks")
    c.door(t, PUERTA, 1, Z0, "south", f"{m}_door")
    c.window(t, X0, 2, 8)
    c.window(t, X1, 2, 7)
    # chimenea de piedra en el muro este con el hogar dentro
    t.set(X1, 1, 9, p["piedra"])
    t.set(X1 - 1, 1, 9, f"campfire[facing=west,lit={'true' if lit else 'false'},signal_fire=false,waterlogged=false]")
    for y in range(2, 4):
        t.set(X1 - 1, y, 9, p["piedra"])
    t.set(X1, 2, 9, p["piedra"])
    t.set(X1, 3, 9, p["piedra"])
    t.fill(X1 - 1, 4, 9, X1 - 1, summit + 1, 9, p["piedra"])
    # literas al oeste, arcón de las pieles y despensa
    c.bed(t, X0 + 1, Z1 - 1, "west", p["cama"])
    c.bed(t, X0 + 1, Z1 - 3, "west", p["cama"])
    c.cofre(t, X0 + 1, 1, Z0 + 1, "east", MID, "pieles")
    c.cofre(t, X1 - 1, 1, Z1 - 1, "west", MID, "despensa", kind="barrel")
    t.set(X1 - 1, 1, Z0 + 1, "crafting_table")
    c.lantern(t, PUERTA, 3, 8)
    # tendedero de pieles al este: dos postes con travesaño y cuero (alfombras marrones) en el suelo
    for z in (6, 10):
        t.fill(14, 1, z, 14, 2, z, f"{m}_fence")
    t.fill(14, 2, 7, 14, 2, 9, f"{m}_fence")
    for z in range(7, 10):
        t.set(13, 1, z, f"{p['piel']}_carpet")
    # tajo con el hacha clavada (un tronco y un leño apilado)
    t.set(13, 1, 12, f"stripped_{tr}[axis=y]")
    t.set(12, 1, 13, f"{tr}[axis=x]")
    t.set(13, 1, 13, f"{tr}[axis=x]")
    return t


def _lookout(t, p, x0, z0):
    """Atalaya de caza: plataforma de 3 x 3 en y = 4 sobre cuatro postes, con su escalera de mano (pegada a un poste al
    sur) y un farol en cada esquina de la barandilla."""
    m, tr = p["madera"], p["tronco"]
    for x in (x0, x0 + 2):
        for z in (z0, z0 + 2):
            t.fill(x, 1, z, x, 3, z, f"{tr}[axis=y]")
    t.fill(x0, 4, z0, x0 + 2, 4, z0 + 2, f"{m}_planks")
    t.fill(x0 + 1, 1, z0 + 3, x0 + 1, 4, z0 + 3, f"{tr}[axis=y]")
    c.ladder(t, x0 + 1, z0 + 2, 1, 4, "north")
    for x, z in ((x0, z0), (x0 + 2, z0), (x0, z0 + 2), (x0 + 2, z0 + 2)):
        t.set(x, 5, z, f"{m}_fence")
    c.lantern(t, x0, 6, z0, hanging=False)
    c.lantern(t, x0 + 2, 6, z0, hanging=False)


def with_hunter(p, name):
    t = _outpost(p, name, lit=True)
    _lookout(t, p, 10, 1)
    t.entity(PUERTA + 1, 1, 8, c.villager(MID, "cazador", "Cazador", "leatherworker", p["aldeano"], offers(), rot=0.0))
    t.entity(PUERTA, 1, 3, c.mob("wolf", MID, "lobo", "Colmillo", rot=0.0, variant=p["lobo"]))
    return t


def smokehouse(p, name):
    """Sin nadie: la fogata apagada y, fuera, un ahumadero de carne (fogata con un tejadillo) junto a la atalaya."""
    t = _outpost(p, name, lit=False)
    _lookout(t, p, 10, 1)
    m = p["madera"]
    t.set(3, 1, 13, "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]")
    for x in (2, 4):
        t.fill(x, 1, 13, x, 2, 13, f"{m}_fence")
    t.fill(2, 3, 13, 4, 3, 13, f"{m}_slab[type=bottom,waterlogged=false]")
    t.set(5, 1, 13, "smoker[facing=west,lit=false]")
    return t


STYLES = {
    "nieve": dict(biomas=["snowy_plains", "ice_spikes"], convencionales=["c:is_snowy_plains"],
                  paleta=dict(madera="spruce", tronco="spruce_log", zocalo="cobblestone", piedra="cobblestone",
                              teja="spruce_stairs", cumbrera="spruce_planks", cama="white", piel="white",
                              aldeano="snow", lobo="minecraft:snowy",
                              suelo=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:dirt_path",
                                     "minecraft:gravel"]),
                  variantes={"a": with_hunter, "b": smokehouse}),
    "sabana": dict(biomas=["savanna", "savanna_plateau", "windswept_savanna"],
                   convencionales=["minecraft:is_savanna", "c:is_savanna"],
                   paleta=dict(madera="acacia", tronco="acacia_log", zocalo="smooth_sandstone", piedra="terracotta",
                               teja="acacia_stairs", cumbrera="acacia_planks", cama="orange", piel="brown",
                               aldeano="savanna", lobo="minecraft:spotted",
                               suelo=["minecraft:dirt_path", "minecraft:packed_mud", "minecraft:smooth_sandstone"]),
                   variantes={"a": with_hunter, "b": smokehouse}),
}
