"""Botín de la costa (heraldia:costa/<tabla>): modesto y marinero. El faro guarda lo del farero (mapas, brújula, catalejo,
velas y algo de comer); la bodega del naufragio, los víveres y pertrechos del barco; el camarote del capitán, sus mapas e
instrumentos y algo de oro (y, rara vez, un fragmento de mapa del tesoro, que añade costa.write con tesoro.con_pista).
El segundo grupo de cada cofre es «solo sin Lootr», como en el resto de Heraldia. Todas las tablas viven bajo
heraldia:costa/, que loot/Reposicion reconoce (se reponen) y la dificultad escala."""
from loot import item, empty
from unicas._comun import botin

LOOT = {
    # cofre de la sala de guardia del faro y tonel de la casa del farero
    "faro": botin.cofre(((2, 4), [item("map", 5, 1, 2), item("compass", 3), item("spyglass", 2), item("candle", 4, 1, 3),
                                  item("cooked_cod", 6, 1, 4), item("bread", 5, 1, 3), item("paper", 4, 2, 6),
                                  item("glow_ink_sac", 2, 1, 3), item("coal", 4, 2, 6), item("lantern", 2),
                                  item("emerald", 2, 1, 2), empty(4)]),
                        ((1, 1), [item("emerald", 2, 1, 2), item("nautilus_shell", 1), item("clock", 1), empty(6)])),
    # bodega del galeón: víveres y pertrechos
    "bodega": botin.cofre(((3, 6), [item("cod", 8, 1, 4), item("salmon", 6, 1, 3), item("dried_kelp", 6, 2, 6),
                                    item("wheat", 5, 2, 6), item("potato", 5, 1, 4), item("coal", 6, 2, 6),
                                    item("string", 5, 1, 4), item("leather", 4, 1, 3), item("paper", 4, 1, 4),
                                    item("gunpowder", 3, 1, 3), item("iron_nugget", 4, 2, 7), item("lead", 2),
                                    item("bamboo", 3, 2, 6), empty(3)]),
                          ((1, 2), [item("iron_ingot", 3, 1, 2), item("gold_nugget", 4, 2, 6), empty(6)])),
    # camarote del capitán: mapas, instrumentos y la caja del barco
    "camarote": botin.cofre(((2, 4), [item("map", 5, 1, 2), item("compass", 4), item("spyglass", 3), item("clock", 2),
                                      item("gold_ingot", 4, 1, 3), item("gold_nugget", 5, 3, 9), item("emerald", 5, 1, 3),
                                      item("book", 3, rand_ench=True), item("iron_sword", 2, dmg=(0.3, 0.8)),
                                      item("name_tag", 1), item("feather", 3, 1, 3), item("ink_sac", 3, 1, 3), empty(3)]),
                            ((1, 1), [item("emerald", 3, 1, 2), item("nautilus_shell", 2), item("gold_ingot", 2), empty(6)])),
}

# Lo que no sale nunca en la costa (tools/gen/tests/test_costa.py lo recorre).
PROHIBIDO = ("netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "diamond", "music_disc", "golden_apple", "_block")
