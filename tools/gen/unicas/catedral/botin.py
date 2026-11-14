"""Botín (solo vanilla) y textos de la catedral."""
from loot import item, empty
from .._comun.botin import named as comun_named, pool, table


def named(name, w, key, ench=None, lo=1, hi=1):
    return comun_named(name, w, key, LANG["es_es"][key], ench, lo, hi)


K = "heraldia.unicas.catedral."
LANG = {
    "es_es": {
        K + "guardian": "Fray Osmundo, custodio del tesoro",
        K + "sello.fe": "Fe",
        K + "sello.esperanza": "Esperanza",
        K + "sello.codicia": "Codicia",
        K + "sello.caridad": "Caridad",
        K + "sello.pista1": "Tres virtudes abren",
        K + "sello.pista2": "y la codicia castiga",
        K + "obj.baculo": "Báculo del obispo Ermengol",
        K + "obj.espada": "Espada del cabildo",
        K + "obj.yelmo": "Yelmo del capitán de la guardia",
        K + "obj.salterio": "Salterio iluminado",
        K + "obj.campana": "Campana de la torre norte",
        K + "obj.reliquia": "Hueso de santo (dudoso)",
        K + "obj.caliz": "Cáliz de oro",
        K + "obj.arco": "Arco de Fray Osmundo",
        K + "obj.peto": "Peto de los mártires",
    },
    "en_us": {
        K + "guardian": "Friar Osmund, Keeper of the Treasure",
        K + "sello.fe": "Faith",
        K + "sello.esperanza": "Hope",
        K + "sello.codicia": "Greed",
        K + "sello.caridad": "Charity",
        K + "sello.pista1": "Three virtues open",
        K + "sello.pista2": "and greed is punished",
        K + "obj.baculo": "Crosier of Bishop Ermengol",
        K + "obj.espada": "Sword of the Chapter",
        K + "obj.yelmo": "Helm of the Guard Captain",
        K + "obj.salterio": "Illuminated Psalter",
        K + "obj.campana": "Bell of the North Tower",
        K + "obj.reliquia": "Saint's Bone (Dubious)",
        K + "obj.caliz": "Golden Chalice",
        K + "obj.arco": "Bow of Friar Osmund",
        K + "obj.peto": "Breastplate of the Martyrs",
    },
}
assert LANG["es_es"].keys() == LANG["en_us"].keys()

CANDLES = [item("candle", 8, 1, 4), item("white_candle", 4, 1, 3)]
LOOT = {
    # cofres menores: modestos
    "menor": table(pool((2, 4), CANDLES + [item("bread", 8, 1, 3), item("paper", 6, 1, 4), item("string", 5, 1, 3),
                                           item("coal", 6, 1, 4), item("iron_nugget", 5, 2, 6), item("bone", 4, 1, 3),
                                           item("glass_bottle", 4, 1, 2), empty(6)]),
                   pool(1, [item("emerald", 3, 1, 2), item("iron_ingot", 3), item("book", 3), empty(10)], extra=True)),
    "capilla": table(pool((1, 3), CANDLES + [item("gold_nugget", 6, 1, 5), item("paper", 4, 1, 3), item("glass_bottle", 4),
                                             item("honeycomb", 3, 1, 2), empty(5)]),
                     pool(1, [item("emerald", 3), item("experience_bottle", 2, 1, 2), empty(8)], extra=True)),
    "sacristia": table(pool((2, 5), CANDLES + [item("gold_nugget", 8, 2, 7), item("white_wool", 5, 1, 3), item("book", 4, 1, 2),
                                               item("glass_bottle", 5, 1, 3), item("honey_bottle", 3), item("red_carpet", 3, 1, 2)]),
                       pool(1, [item("gold_ingot", 4, 1, 2), item("emerald", 4, 1, 3), item("experience_bottle", 3, 1, 3),
                                item("lead", 1), empty(4)], extra=True)),
    "biblioteca": table(pool((3, 6), [item("book", 12, 1, 3), item("paper", 12, 2, 8), item("feather", 6, 1, 3),
                                      item("ink_sac", 6, 1, 3), item("writable_book", 4), item("map", 3), item("lapis_lazuli", 4, 2, 5)]),
                        pool(1, [item("book", 6, rand_ench=True), item("experience_bottle", 3, 2, 4), empty(6)], extra=True)),
    "campanario": table(pool((2, 5), [item("string", 8, 2, 6), item("iron_chain", 6, 1, 3), item("lantern", 4, 1, 2),
                                      item("iron_nugget", 8, 3, 9), item("bread", 6, 1, 3), item("honeycomb", 3, 1, 3),
                                      item("arrow", 5, 4, 10)]),
                        pool(1, [item("iron_ingot", 6, 1, 3), item("spyglass", 2), named("bell", 1, K + "obj.campana"), empty(6)],
                             extra=True)),
    "cripta": table(pool((3, 6), [item("bone", 10, 2, 6), item("rotten_flesh", 8, 1, 4), item("candle", 6, 1, 3),
                                  item("gold_nugget", 6, 2, 8), item("iron_ingot", 5, 1, 3), item("emerald", 4, 1, 2)]),
                    pool((1, 2), [item("gold_ingot", 5, 1, 3), item("diamond", 1), item("golden_apple", 1),
                                  item("iron_sword", 2, ench=(5, 12)), empty(5)], extra=True)),
    "osario": table(pool((3, 6), [item("bone", 12, 3, 8), item("bone_meal", 8, 2, 6), item("arrow", 8, 4, 12),
                                  item("gold_nugget", 5, 2, 6), item("string", 4, 1, 3)]),
                    pool((1, 2), [item("skeleton_skull", 1), item("golden_apple", 2), item("emerald", 5, 2, 4),
                                  named("bone", 2, K + "obj.reliquia"), item("diamond", 1), empty(4)], extra=True)),
    # escondidos: más ricos
    "oculto": table(pool((2, 4), [item("book", 6, ench=(10, 20)), item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 5),
                                  item("diamond", 4, 1, 2), item("experience_bottle", 5, 2, 6), item("name_tag", 2),
                                  item("golden_apple", 3), named("writable_book", 2, K + "obj.salterio")]),
                    pool((1, 2), [item("diamond", 3, 1, 2), item("music_disc_strad", 1), item("music_disc_mellohi", 1),
                                  item("gold_block", 2), empty(3)], extra=True)),
    "tesoro": table(pool((3, 5), [item("gold_ingot", 10, 2, 6), item("emerald", 10, 2, 6), item("diamond", 4, 1, 3),
                                  item("golden_apple", 4), item("experience_bottle", 6, 3, 8),
                                  item("iron_chestplate", 2, ench=(10, 20)), item("iron_sword", 2, ench=(10, 20)),
                                  named("gold_block", 2, K + "obj.caliz")]),
                    pool((1, 2), [item("diamond", 4, 1, 2), item("gold_block", 3), item("emerald", 4, 3, 6)], extra=True)),
    # premium: pieza principal (90 % vistosa, 10 % algo más fuerte) + vistosos + valores + extra sin Lootr
    "premium": table(
        pool(1, [named("golden_sword", 18, K + "obj.espada", {"minecraft:sharpness": 3, "minecraft:unbreaking": 3}),
                 named("chainmail_helmet", 18, K + "obj.yelmo", {"minecraft:protection": 3}),
                 named("golden_hoe", 18, K + "obj.baculo", {"minecraft:unbreaking": 3, "minecraft:efficiency": 3}),
                 named("bow", 18, K + "obj.arco", {"minecraft:power": 3, "minecraft:punch": 1}),
                 named("gold_block", 18, K + "obj.caliz"),
                 named("diamond_chestplate", 4, K + "obj.peto", {"minecraft:protection": 3, "minecraft:unbreaking": 2}),
                 named("diamond_sword", 3, K + "obj.espada", {"minecraft:sharpness": 4, "minecraft:unbreaking": 3}),
                 item("enchanted_golden_apple", 3)]),
        pool((2, 3), [item("music_disc_cat", 3), item("music_disc_far", 3), item("music_disc_strad", 3),
                      item("music_disc_mall", 3), item("host_armor_trim_smithing_template", 3),
                      item("raiser_armor_trim_smithing_template", 3), item("shaper_armor_trim_smithing_template", 3),
                      item("wayfinder_armor_trim_smithing_template", 3), item("book", 4, ench=(15, 25)),
                      named("writable_book", 2, K + "obj.salterio")]),
        pool((3, 5), [item("gold_ingot", 8, 3, 8), item("emerald", 8, 3, 8), item("diamond", 4, 1, 3),
                      item("golden_apple", 4, 1, 2), item("experience_bottle", 6, 4, 10), item("golden_carrot", 4, 2, 5)]),
        pool((1, 2), [item("diamond", 4, 1, 2), item("gold_block", 3), item("golden_apple", 3), item("name_tag", 2)], extra=True)),
}
