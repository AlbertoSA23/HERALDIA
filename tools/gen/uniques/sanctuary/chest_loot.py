"""Botín del Santuario druídico (solo vanilla): modesto en las cabañas y el claro, mejor bajo las raíces y en las salas
ocultas, y el cofre premium al fondo (90 % vistoso, 10 % algo más fuerte). Cada tabla tiene su grupo extra marcado
solo_sin_lootr."""
from .._common.chest_loot import place_chest, table, pool, item, empty, named as _named, potion, lang

K = "heraldia.santuario."
TEXTS = {   # clave: (es_es, en_us)
    "muerdago": ("Muérdago dorado", "Golden Mistletoe"),
    "corteza": ("Corteza escrita", "Inscribed Bark"),
    "tratado": ("Tratado de las raíces", "Treatise on Roots"),
    "remedio": ("Remedio del herbolario", "Herbalist's Remedy"),
    "tonico": ("Tónico de savia", "Sap Tonic"),
    "miel": ("Miel del claro", "Glade Honey"),
    "daga": ("Daga del rito", "Ritual Dagger"),
    "arco": ("Arco de abedul", "Birchwood Bow"),
    "corona": ("Corona de hojas", "Crown of Leaves"),
    "bordon": ("Bordón del peregrino", "Pilgrim's Staff"),
    "semilla": ("Semilla del árbol sagrado", "Seed of the Sacred Tree"),
}
LANG = lang(K + "objeto.", TEXTS)


def named(name, key, w, **kw):
    return _named(name, w, K + "objeto." + key, TEXTS[key][0], **kw)


LIGHT = [item("bread", 8, 1, 3), item("honey_bottle", 4, 1, 2), item("sweet_berries", 6, 2, 6), item("apple", 6, 1, 3),
         item("wheat_seeds", 5, 2, 6), item("beetroot_seeds", 4, 2, 5), item("bone_meal", 5, 2, 5), item("string", 4, 1, 3),
         item("white_wool", 4, 1, 2), item("candle", 4, 1, 2), item("birch_sapling", 3, 1, 2), item("bowl", 3, 1, 2)]

LOOT = {
    # claro (superficie)
    "cabana": place_chest(((2, 4), LIGHT + [item("book", 2), item("mushroom_stew", 2)]),
                    (1, [item("emerald", 3), item("gold_nugget", 5, 2, 5), item("golden_carrot", 2), empty(8)])),
    "jardin": place_chest(((2, 4), [item("wheat_seeds", 8, 2, 6), item("carrot", 6, 1, 4), item("beetroot", 6, 1, 4),
                              item("potato", 6, 1, 4), item("bone_meal", 8, 2, 6), item("honeycomb", 4, 1, 3),
                              item("allium", 3, 1, 2), item("cornflower", 3, 1, 2), item("lily_of_the_valley", 3, 1, 2),
                              item("shears", 2, dmg=(0.3, 0.8))]),
                    (1, [named("honey_bottle", "miel", 3, lo=1, hi=2), item("glistering_melon_slice", 2),
                         item("golden_carrot", 2), empty(8)])),
    "observatorio": place_chest(((2, 4), [item("paper", 8, 1, 4), item("candle", 5, 1, 2), item("compass", 2), item("clock", 2),
                                    item("amethyst_shard", 4, 1, 3), item("map", 3), item("feather", 4, 1, 3),
                                    item("bread", 5, 1, 2)]),
                          (1, [item("spyglass", 2), item("lapis_lazuli", 4, 2, 6), item("emerald", 3), empty(8)])),
    "copa": place_chest(((2, 4), [item("arrow", 8, 3, 10), item("bread", 6, 1, 2), item("string", 5, 1, 3), item("feather", 4, 1, 3),
                            item("stick", 5, 2, 5), item("bow", 2, dmg=(0.3, 0.8)), item("honey_bottle", 3)]),
                  (1, [named("bow", "arco", 2, levels=(5, 10)), item("iron_ingot", 4, 1, 2), item("emerald", 3),
                       empty(8)])),
    # sala oculta de la superficie
    "archidruida": place_chest(((3, 5), [item("gold_ingot", 8, 1, 3), item("emerald", 8, 1, 4), item("amethyst_shard", 5, 1, 4),
                                   named("glow_berries", "muerdago", 4, lo=1, hi=3), item("book", 4, rand_ench=True),
                                   potion("regeneration", 3), item("honeycomb", 4, 1, 3)]),
                         ((1, 2), [item("diamond", 3), item("golden_apple", 3), item("experience_bottle", 4, 2, 5),
                                   named("stick", "bordon", 2, ench={"minecraft:knockback": 1}), empty(6)])),
    # bajo las raíces, nivel alto
    "biblioteca": place_chest(((3, 5), [item("book", 10, 1, 3), item("paper", 10, 2, 6), item("feather", 6, 1, 3),
                                  item("ink_sac", 6, 1, 3), item("candle", 4, 1, 2), item("writable_book", 3),
                                  named("paper", "corteza", 3, lo=1, hi=2)]),
                        ((1, 2), [item("book", 6, rand_ench=True), item("experience_bottle", 4, 1, 3),
                                  item("lapis_lazuli", 4, 2, 5), empty(6)])),
    "herbolario": place_chest(((3, 5), [item("glass_bottle", 8, 1, 3), item("sugar", 6, 1, 3), item("spider_eye", 5, 1, 2),
                                  item("brown_mushroom", 5, 1, 3), item("red_mushroom", 5, 1, 3), item("glow_berries", 5, 1, 4),
                                  item("redstone", 4, 1, 4), item("glowstone_dust", 3, 1, 3),
                                  potion("healing", 3), potion("swiftness", 2)]),
                        ((1, 2), [named("potion", "remedio", 3, mods=[{"type": "minecraft:set_potion",
                                                                       "id": "minecraft:regeneration"}]),
                                  item("glistering_melon_slice", 3), item("golden_carrot", 3), item("fermented_spider_eye", 2),
                                  item("blaze_powder", 1), empty(6)])),
    "raices": place_chest(((2, 4), [item("string", 6, 1, 3), item("glow_berries", 5, 1, 3), item("brown_mushroom", 5, 1, 3),
                              item("iron_nugget", 6, 2, 6), item("coal", 6, 1, 4), item("torch", 5, 1, 4),
                              item("rooted_dirt", 3, 1, 3), item("moss_block", 3, 1, 2), item("bone", 4, 1, 3)]),
                    (1, [item("iron_ingot", 5, 1, 2), item("emerald", 3), item("golden_apple", 1), empty(8)])),
    "osario": place_chest(((2, 4), [item("bone", 12, 2, 6), item("bone_meal", 6, 2, 6), item("rotten_flesh", 6, 1, 3),
                              item("gold_nugget", 6, 2, 6), item("candle", 4, 1, 2), item("skeleton_skull", 1)]),
                    ((1, 2), [item("gold_ingot", 5, 1, 3), item("iron_ingot", 5, 1, 3), item("experience_bottle", 3, 1, 3),
                              empty(8)])),
    # sala oculta del nivel alto (tras la puerta secreta de la biblioteca)
    "secreto": place_chest(((3, 5), [item("book", 8, rand_ench=True), named("writable_book", "tratado", 3),
                               item("amethyst_shard", 5, 1, 4), item("lapis_lazuli", 6, 2, 6), item("emerald", 6, 1, 3),
                               item("experience_bottle", 4, 1, 3)]),
                     ((1, 2), [item("diamond", 3, 1, 2), item("music_disc_mellohi", 2), item("golden_apple", 2),
                               item("name_tag", 2), empty(5)])),
    # nivel bajo
    "ofrendas": place_chest(((4, 6), [item("gold_ingot", 10, 2, 5), item("gold_nugget", 8, 4, 10), item("emerald", 8, 2, 5),
                                named("honey_bottle", "miel", 4, lo=1, hi=2), item("amethyst_shard", 5, 1, 4)]),
                      ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), item("gold_block", 1), empty(6)])),
    "ritual": place_chest(((3, 5), [item("redstone", 6, 2, 6), item("glowstone_dust", 5, 1, 4), item("lapis_lazuli", 6, 2, 6),
                              item("amethyst_shard", 5, 1, 4), item("candle", 4, 1, 3), item("experience_bottle", 4, 2, 4),
                              named("iron_sword", "daga", 2, levels=(5, 12))]),
                    ((1, 2), [item("diamond", 3, 1, 2), item("emerald", 5, 2, 4), item("golden_apple", 2), empty(6)])),
    # cámara del tesoro
    "premium": table(
        pool((3, 5), [named("golden_carrot", "semilla", 5), named("leather_helmet", "corona", 4, levels=(8, 15)),
                      named("bow", "arco", 4, levels=(10, 20)), named("glow_berries", "muerdago", 4, lo=2, hi=4),
                      item("wild_armor_trim_smithing_template", 4), item("wayfinder_armor_trim_smithing_template", 3),
                      item("raiser_armor_trim_smithing_template", 2), item("music_disc_chirp", 3),
                      item("music_disc_mellohi", 3), item("music_disc_stal", 2), item("gold_ingot", 6, 2, 6),
                      item("emerald", 6, 3, 8), item("book", 4, ench=(10, 20)), item("golden_apple", 3)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                      item("experience_bottle", 5, 2, 6), item("honey_bottle", 4, 1, 3)], extra=True),
        pool(1, [empty(90), item("diamond_axe", 3, ench=(20, 30)), item("diamond_leggings", 3, ench=(20, 30)),   # 10 % más fuerte
                 item("enchanted_golden_apple", 2), item("totem_of_undying", 2)])),
}
