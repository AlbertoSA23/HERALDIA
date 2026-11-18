"""Cabaña de pescador (heraldia:medianas/pescador/<estilo>): patio de 17 x 21 en la orilla con una cabaña de 7 x 7, un
secadero de pescado y un embarcadero de tablones sobre pilotes al sur. Variante a: el pescador (aldeano quieto con
tratos fijos: compra cuerda, vende bacalao asado y una caña) y su gato; b: la cabaña cerrada, con un ahumadero y el
embarcadero más largo con nasas, sin nadie. Sin monstruos."""
from core import Template, B
from loot import item, empty
from uniques._common import chest_loot
from . import _common as c

MID = "pescador"
DISPLAY_NAME = {"es_es": "Cabaña de pescador", "en_us": "Fisher's Hut"}
SEPARATION = 576
BIOME_NEIGHBORS = 2                  # las playas son franjas de pocas decenas de bloques
ADVANCEMENT_ICON = "minecraft:fishing_rod"
LANG = chest_loot.lang("heraldia.medianas.pescador.", {
    "pescador": ("Pescador", "Fisher"),
    "gato": ("Bigotes", "Whiskers"),
})
ADVANCEMENTS = [dict(id="pesca", icono="minecraft:cod", tabla="pesca",
               titulo=("La pesca del día", "Catch of the Day"),
               descripcion=("Abre el tonel de la pesca de una cabaña de pescador",
                            "Open the catch barrel of a fisher's hut"))]
LOOT = {
    "pesca": chest_loot.cofre(((3, 5), [item("cod", 10, 1, 4), item("salmon", 7, 1, 3), item("cooked_cod", 6, 1, 3),
                                   item("tropical_fish", 2), item("pufferfish", 1), item("kelp", 5, 2, 6),
                                   item("ink_sac", 4, 1, 3), item("string", 5, 1, 4), item("bone_meal", 3, 1, 3),
                                   item("lily_pad", 2), empty(4)]),
                         ((1, 1), [item("nautilus_shell", 1), item("emerald", 2), item("prismarine_shard", 2), empty(8)])),
    "cabana": chest_loot.cofre(((2, 4), [item("fishing_rod", 3, dmg=(0.3, 0.8)), item("bread", 6, 1, 3), item("lead", 3),
                                    item("string", 5, 1, 3), item("stick", 5, 2, 5), item("paper", 3, 1, 3),
                                    item("leather_boots", 2, dmg=(0.4, 0.9)), item("compass", 1), item("map", 2),
                                    item("book", 2, rand_ench=True), empty(5)]),
                          ((1, 1), [item("emerald", 3, 1, 2), item("name_tag", 1), empty(8)])),
}

WIDTH, DEPTH = 17, 21
X0, Z0, X1, Z1 = 2, 4, 8, 10       # cabaña (7 x 7), puerta al norte
PUERTA = 5
EX0, EX1 = 11, 13                  # embarcadero (3 de ancho), de z = 6 al fondo


def offers():
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [c.offer({"id": "minecraft:string", "count": 20}, em(1), 12),
            c.offer(em(1), {"id": "minecraft:cooked_cod", "count": 6}, 12),
            c.offer(em(3), {"id": "minecraft:fishing_rod", "count": 1}, 3),
            c.offer({"id": "minecraft:cod", "count": 15}, em(1), 12)]


def _floor(p):
    mats = p["patio"]
    return lambda x, z: p["senda"] if x == PUERTA and z < Z0 else mats[(x * 7 + z * 5 + x * z) % len(mats)]


def _cabin(p, name, shut):
    t = Template(name)
    m = p["madera"]
    c.courtyard(t, 0, 0, WIDTH - 1, DEPTH - 1, _floor(p), air_block=3)
    c.entrance(t, PUERTA, p["senda"])
    # cabaña sobre un zócalo, muros de tablones con postes, tejado a dos aguas
    t.fill(X0, 0, Z0, X1, 0, Z1, p["zocalo"])
    t.fill(X0 + 1, 0, Z0 + 1, X1 - 1, 0, Z1 - 1, f"{m}_planks")
    c.box(t, X0, 1, Z0, X1, 3, Z1, p["muro"], corner_block=f"{p['tronco']}[axis=y]")
    t.fill(X0, 4, Z0, X1, 4, Z1, f"{m}_planks")
    c.roof_tiles(t, X0, Z0, X1, Z1, 4, p["teja"], p["cumbrera"], p["muro"])
    c.door(t, PUERTA, 1, Z0, "south", f"{m}_door")
    c.window(t, X0, 2, 7)
    c.window(t, X1, 2, 7)
    c.window(t, PUERTA, 2, Z1)
    # dentro: cama, cofre, mesa de trabajo y el tonel de la pesca; farol en el centro
    c.bed(t, X0 + 1, Z1 - 1, "west", p["cama"])
    c.cofre(t, X0 + 1, 1, Z0 + 1, "east", MID, "cabana")
    c.cofre(t, X1 - 1, 1, Z1 - 1, "west", MID, "pesca", kind="barrel")
    t.set(X1 - 1, 1, Z0 + 1, "smoker[facing=west,lit=false]" if shut else "crafting_table")
    t.set(X1 - 1, 1, Z1 - 2, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})
    c.lantern(t, PUERTA, 3, 7)
    # secadero de pescado al norte del embarcadero: dos postes con un travesaño de vallas
    for x in (EX0 - 1, EX1 + 1):
        t.set(x, 1, 2, f"{m}_fence")
        t.set(x, 2, 2, f"{m}_fence")
    for x in range(EX0, EX1 + 1):
        t.set(x, 2, 2, f"{m}_fence")
    c.lantern(t, EX0 + 1, 1, 2, hanging=True)
    return t


def _dock(t, p, z1, fish_traps=False):
    """Tablones en y = 1 de z = 6 a z1 sobre pilotes de tronco (y = 0) cada 3, con barandilla al final y un farol."""
    m = p["madera"]
    t.set(EX0 + 1, 1, 5, f"{m}_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
    for z in range(6, z1 + 1):
        for x in range(EX0, EX1 + 1):
            t.set(x, 1, z, f"{m}_planks")
            for y in (2, 3):
                t.set(x, y, z, "air")
        if (z - 6) % 3 == 0 or z == z1:
            for x in (EX0, EX1):
                t.set(x, 0, z, f"{p['tronco']}[axis=y]")
    for x in range(EX0, EX1 + 1):
        t.set(x, 2, z1, f"{m}_fence")
    t.set(EX0, 2, z1 - 1, f"{m}_fence")
    t.set(EX1, 2, z1 - 1, f"{m}_fence")
    c.lantern(t, EX1, 3, z1, hanging=False)
    t.set(EX0, 2, 9, f"{m}_fence")                  # bolardo
    if fish_traps:
        for z in (12, 15):
            t.set(EX0, 2, z, f"{m}_trapdoor[facing=east,half=bottom,open=false,powered=false,waterlogged=false]")
            t.set(EX1, 2, z, "barrel[facing=up,open=false]", {"id": "minecraft:barrel"})


def with_fisherman(p, name):
    t = _cabin(p, name, shut=False)
    _dock(t, p, DEPTH - 4)
    t.entity(PUERTA, 1, 7, c.villager(MID, "pescador", "Pescador", "fisherman", p["aldeano"], offers(), rot=0.0))
    t.entity(EX0 + 1, 2, 10, c.mob("cat", MID, "gato", "Bigotes", rot=90.0,
                                   variant=p["gato"], CollarColor=B(p["collar"])))
    return t


def smokehouse(p, name):
    """Sin nadie: ahumadero de piedra adosado al este con una fogata, y embarcadero más largo con nasas."""
    t = _cabin(p, name, shut=True)
    _dock(t, p, DEPTH - 1, fish_traps=True)
    # ahumadero 3 x 3 al sur de la cabaña, abierto al este, con la fogata bajo una campana de piedra
    for x in range(X0 + 2, X0 + 5):
        for z in range(Z1 + 2, Z1 + 5):
            edge_block = x in (X0 + 2, X0 + 4) or z in (Z1 + 2, Z1 + 4)
            if edge_block and not (x == X0 + 4 and z == Z1 + 3):
                t.fill(x, 1, z, x, 2, z, p["zocalo"])
            t.set(x, 3, z, p["zocalo"])
    t.set(X0 + 3, 1, Z1 + 3, "campfire[facing=east,lit=true,signal_fire=false,waterlogged=false]")
    t.set(X0 + 3, 2, Z1 + 3, "air")
    t.set(X0 + 3, 4, Z1 + 3, p["muro_chimenea"])
    return t


STYLES = {
    "playa": dict(biomas=["beach"],
                  paleta=dict(madera="birch", tronco="birch_log", muro="birch_planks", zocalo="sandstone",
                              teja="spruce_stairs", cumbrera="spruce_planks", cama="light_blue", aldeano="plains",
                              gato="minecraft:tabby", collar=3, senda="minecraft:smooth_sandstone",
                              muro_chimenea="sandstone_wall",
                              patio=["minecraft:sandstone", "minecraft:smooth_sandstone", "minecraft:gravel"]),
                  variantes={"a": with_fisherman, "b": smokehouse}),
    "nevada": dict(biomas=["snowy_beach"],
                   paleta=dict(madera="spruce", tronco="spruce_log", muro="spruce_planks", zocalo="cobblestone",
                               teja="spruce_stairs", cumbrera="dark_oak_planks", cama="white", aldeano="snow",
                               gato="minecraft:white", collar=14, senda="minecraft:cobblestone",
                               muro_chimenea="cobblestone_wall",
                               patio=["minecraft:gravel", "minecraft:cobblestone", "minecraft:gravel"]),
                   variantes={"a": with_fisherman, "b": smokehouse}),
    "rocosa": dict(biomas=["stony_shore"], convencionales=["c:is_stony_shores"],
                   paleta=dict(madera="oak", tronco="oak_log", muro="oak_planks", zocalo="stone_bricks",
                               teja="dark_oak_stairs", cumbrera="dark_oak_planks", cama="blue", aldeano="plains",
                               gato="minecraft:black", collar=11, senda="minecraft:gravel",
                               muro_chimenea="stone_brick_wall",
                               patio=["minecraft:gravel", "minecraft:cobblestone", "minecraft:stone_bricks"]),
                   variantes={"a": with_fisherman, "b": smokehouse}),
}
