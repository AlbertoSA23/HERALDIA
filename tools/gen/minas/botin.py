"""Botín de las entradas a mina (heraldia:minas/<tabla>): algo mejor que el de una mina vanilla (más tiradas de lingotes,
menas en bruto y raíles, alguna esmeralda y un pico encantado de vez en cuando), pero moderado: nada de manzanas de oro
encantadas, netherita, élitros, tótems ni plantillas de herrería, y los diamantes con poco peso. El segundo grupo de cada
cofre es «solo sin Lootr» (con Lootr cada jugador abre su copia), como en el resto de estructuras de Heraldia; todas
las tablas viven bajo heraldia:minas/, así que cualquier función que reconozca el botín de Heraldia por su espacio de
nombres las ve también."""
from loot import item, empty
from unicas._comun import botin

# Comparación (cofre de mina vanilla, 26.3): 1 tirada de {manzana de oro encantada, manzana de oro, etiqueta, libro,
# pico de hierro, nada}, 2-4 de {hierro 1-5, oro 1-3, redstone 4-9, lapislázuli 4-9, diamante 1-2 (peso 3), carbón
# 3-8, pan, bayas, semillas} y 3 de raíles y antorchas.
LOOT = {
    # tonel del patio de la boca pequeña: lo de cada día
    "boca": botin.cofre(((2, 4), [item("torch", 8, 4, 12), item("coal", 8, 2, 6), item("bread", 6, 1, 3),
                                  item("rail", 6, 4, 10), item("iron_nugget", 5, 3, 9), item("string", 4, 1, 3),
                                  item("stone_pickaxe", 3, dmg=(0.3, 0.8)), item("iron_pickaxe", 1, dmg=(0.4, 0.8)),
                                  empty(4)]),
                        ((1, 1), [item("raw_iron", 3, 1, 3), item("raw_copper", 3, 2, 5), empty(6)])),
    # cofres de las salas de la galería (todos los tamaños)
    "galeria": botin.table(
        botin.pool(1, [item("golden_apple", 12), item("name_tag", 20), item("book", 12, rand_ench=True),
                       item("iron_pickaxe", 8, ench=(5, 15)), item("emerald", 10, 1, 3), item("glow_berries", 10, 3, 6),
                       empty(8)]),
        botin.pool((3, 5), [item("iron_ingot", 12, 1, 5), item("gold_ingot", 6, 1, 3), item("redstone", 6, 4, 9),
                            item("lapis_lazuli", 6, 4, 9), item("diamond", 3, 1, 2), item("coal", 10, 3, 8),
                            item("raw_iron", 8, 2, 6), item("raw_copper", 6, 3, 8), item("raw_gold", 3, 1, 3),
                            item("amethyst_shard", 4, 1, 4), item("bread", 8, 1, 3)]),
        botin.pool(3, [item("rail", 20, 4, 8), item("powered_rail", 6, 1, 4), item("detector_rail", 4, 1, 3),
                       item("activator_rail", 3, 1, 3), item("torch", 15, 1, 16)]),
        botin.pool((1, 2), [item("iron_ingot", 4, 1, 3), item("emerald", 2, 1, 2), item("gold_nugget", 4, 3, 8),
                            empty(6)], extra=True)),
    # vagoneta de carga (chest_minecart) del patio de la mediana y de la grande
    "vagoneta": botin.cofre(((4, 7), [item("raw_iron", 10, 2, 6), item("raw_copper", 10, 3, 9), item("raw_gold", 3, 1, 3),
                                      item("coal", 12, 4, 12), item("cobblestone", 8, 8, 24), item("gravel", 5, 4, 12),
                                      item("redstone", 4, 3, 8), item("lapis_lazuli", 3, 3, 7), item("flint", 4, 1, 4)]),
                            ((1, 2), [item("raw_iron", 4, 1, 3), item("coal", 4, 2, 6), empty(5)])),
    # cofre del capataz (cabaña de la mediana y oficina de la grande)
    "capataz": botin.cofre(((3, 5), [item("emerald", 6, 1, 4), item("iron_ingot", 8, 2, 5), item("gold_ingot", 4, 1, 3),
                                     item("compass", 3), item("clock", 2), item("map", 3), item("paper", 4, 2, 6),
                                     item("book", 4, rand_ench=True), item("iron_pickaxe", 3, ench=(8, 18)),
                                     item("iron_shovel", 2, ench=(5, 12)), item("golden_carrot", 3, 1, 3),
                                     item("cooked_beef", 5, 1, 3), item("diamond", 2, 1, 1), empty(3)]),
                           ((1, 2), [item("emerald", 3, 1, 2), item("gold_ingot", 2, 1, 2), empty(6)])),
    # tonel de la fundición
    "fundicion": botin.cofre(((3, 5), [item("iron_ingot", 12, 2, 6), item("copper_ingot", 10, 3, 8), item("gold_ingot", 4, 1, 3),
                                       item("coal", 10, 4, 10), item("charcoal", 5, 2, 6), item("iron_nugget", 6, 4, 12),
                                       item("gold_nugget", 4, 3, 9), item("bucket", 2), item("lava_bucket", 1),
                                       item("bricks", 3, 4, 10)]),
                             ((1, 2), [item("iron_ingot", 4, 1, 3), item("copper_ingot", 4, 2, 4), empty(6)])),
    # cofre de la sala del filón rico (nivel hondo de la grande): el mejor de las minas, sin pasar de moderado
    "filon": botin.table(
        botin.pool((1, 2), [item("diamond", 6, 1, 3), item("emerald", 8, 2, 5), item("golden_apple", 6),
                            item("iron_pickaxe", 6, ench=(15, 25)), item("book", 6, rand_ench=True),
                            item("diamond_pickaxe", 1, dmg=(0.5, 0.9)), item("experience_bottle", 6, 2, 5)]),
        botin.pool((4, 6), [item("gold_ingot", 10, 2, 5), item("raw_gold", 8, 2, 5), item("iron_ingot", 10, 3, 7),
                            item("redstone", 8, 6, 12), item("lapis_lazuli", 8, 6, 12), item("amethyst_shard", 6, 2, 6),
                            item("coal", 8, 4, 10)]),
        botin.pool((1, 2), [item("gold_ingot", 4, 1, 3), item("emerald", 3, 1, 2), item("diamond", 1, 1, 1), empty(8)],
                   extra=True)),
}

# Lo que no sale nunca en una mina (la prueba unitaria lo recorre; tools/gen/tests/test_minas.py).
PROHIBIDO = ("netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "music_disc", "diamond_block", "emerald_block", "gold_block")
DIAMANTES_MAX = 3          # diamantes como mucho por entrada de una tabla
