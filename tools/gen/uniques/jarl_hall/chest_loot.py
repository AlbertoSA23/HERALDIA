"""Botín del Salón del Jarl (solo vanilla): modesto en el patio, mejor en el túmulo y en las salas ocultas, y el cofre
premium al fondo (90 % vistoso, 10 % algo más fuerte). Cada tabla tiene su grupo extra marcado solo_sin_lootr."""
from .._common.chest_loot import place_chest, table, pool, item, empty, named as _named, book, lang

K = "heraldia.salon_jarl."
TEXTS = {   # clave: (es_es, en_us)
    "hacha": ("Hacha de la incursión", "Raiding Axe"),
    "cuerno": ("Cuerno de la asamblea", "Horn of the Assembly"),
    "saga": ("Saga de Ulfgrim", "Saga of Ulfgrim"),
    "anillo": ("Anillo del juramento", "Oath Ring"),
    "escudo": ("Escudo del salón", "Hall Shield"),
    "remo": ("Remo del barco largo", "Longship Oar"),
    "martillo": ("Martillo del herrero", "Smith's Hammer"),
    "hidromiel": ("Hidromiel del jarl", "The Jarl's Mead"),
    "capa": ("Capa de piel de oso", "Bearskin Cloak"),
    "runa": ("Piedra rúnica tallada", "Carved Rune Stone"),
}
LANG = lang(K + "objeto.", TEXTS)


def named(name, key, w, **kw):
    return _named(name, w, K + "objeto." + key, TEXTS[key][0], **kw)


HEARTH = [item("bread", 8, 1, 3), item("cooked_salmon", 6, 1, 3), item("sweet_berries", 6, 2, 6), item("bowl", 4, 1, 2),
         item("white_wool", 5, 1, 3), item("leather", 6, 1, 3), item("string", 5, 1, 3), item("stick", 5, 2, 5),
         item("candle", 4, 1, 2), item("feather", 4, 1, 3)]

LOOT = {
    # patio
    "salon": place_chest(((2, 4), HEARTH + [item("arrow", 5, 2, 8), item("rabbit_hide", 3, 1, 2)]),
                   (1, [item("iron_nugget", 6, 2, 6), item("gold_nugget", 4, 2, 5), item("emerald", 2), empty(8)])),
    "atalaya": place_chest(((2, 4), [item("arrow", 10, 4, 12), item("bread", 6, 1, 2), item("torch", 6, 2, 6), item("string", 5, 1, 3),
                               item("flint", 4, 1, 3), item("bow", 2, dmg=(0.3, 0.8)), item("spyglass", 1)]),
                    (1, [item("iron_ingot", 5, 1, 2), item("emerald", 2), empty(8)])),
    "herreria": place_chest(((2, 5), [item("iron_ingot", 8, 1, 3), item("iron_nugget", 10, 3, 9), item("coal", 10, 2, 6),
                                item("charcoal", 6, 1, 4), item("flint", 4, 1, 3), item("iron_axe", 3, dmg=(0.3, 0.8)),
                                item("iron_shovel", 2, dmg=(0.3, 0.8)), item("iron_chain", 3, 1, 3), item("bucket", 2)]),
                     ((1, 2), [item("iron_ingot", 6, 1, 3), item("gold_ingot", 3, 1, 2), item("diamond", 1),
                               named("iron_pickaxe", "martillo", 2, levels=(5, 12)), empty(8)])),
    "establo": place_chest(((2, 4), [item("leather", 8, 1, 4), item("wheat", 8, 2, 6), item("lead", 4, 1, 2), item("hay_block", 3, 1, 2),
                               item("apple", 5, 1, 3), item("carrot", 4, 1, 3), item("saddle", 2)]),
                    (1, [item("leather_horse_armor", 3), item("iron_horse_armor", 2), item("golden_carrot", 2, 1, 2), empty(8)])),
    "astillero": place_chest(((2, 5), [item("spruce_planks", 10, 4, 12), item("stick", 8, 2, 6), item("string", 6, 2, 5),
                                 item("white_wool", 5, 1, 3), item("iron_nugget", 5, 2, 6), item("spruce_boat", 2),
                                 item("black_dye", 3, 1, 2), item("lead", 3)]),
                      (1, [named("spruce_boat", "remo", 2), item("map", 2), item("compass", 2), empty(8)])),
    "guerreros": place_chest(((2, 4), [item("arrow", 8, 3, 10), item("bread", 6, 1, 3), item("leather_helmet", 3, dmg=(0.3, 0.8)),
                                 item("leather_chestplate", 3, dmg=(0.3, 0.8)), item("stone_axe", 4, dmg=(0.2, 0.7)),
                                 item("shield", 2, dmg=(0.3, 0.8)), item("cooked_porkchop", 4, 1, 2), item("bone", 4, 1, 3)]),
                      ((1, 2), [item("iron_ingot", 6, 1, 3), item("chainmail_helmet", 2), item("iron_axe", 2, ench=(5, 10)),
                                item("emerald", 3, 1, 2), empty(8)])),
    "despensa": place_chest(((3, 6), [item("bread", 8, 1, 4), item("wheat", 8, 2, 6), item("potato", 6, 1, 4), item("beetroot", 5, 1, 4),
                                item("dried_kelp", 6, 2, 6), item("cooked_cod", 5, 1, 3), item("sweet_berries", 6, 2, 6),
                                item("honey_bottle", 3, 1, 2), item("mushroom_stew", 2), item("salmon", 4, 1, 3)]),
                     (1, [item("cake", 1), item("pumpkin_pie", 3), item("golden_apple", 1), empty(8)])),
    # sala oculta de la superficie
    "jarl": place_chest(((3, 5), [item("gold_ingot", 8, 1, 3), item("emerald", 8, 1, 4), item("iron_ingot", 6, 1, 3),
                            item("goat_horn", 2), named("gold_nugget", "anillo", 3), item("amethyst_shard", 4, 1, 4),
                            item("book", 4, rand_ench=True), named("honey_bottle", "hidromiel", 4, lo=1, hi=2)]),
                  ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), named("brown_banner", "capa", 2),
                            item("experience_bottle", 4, 2, 5), empty(6)])),
    # túmulo
    "tumba": place_chest(((2, 4), [item("bone", 10, 2, 5), item("gold_nugget", 8, 2, 7), item("iron_nugget", 6, 2, 6),
                             item("candle", 4, 1, 2), item("rotten_flesh", 6, 1, 3), item("iron_sword", 2, dmg=(0.4, 0.8))]),
                   ((1, 2), [item("gold_ingot", 5, 1, 3), item("emerald", 3, 1, 2), item("golden_helmet", 2, ench=(5, 10)),
                             empty(8)])),
    "osario": place_chest(((2, 4), [item("bone", 12, 2, 6), item("bone_meal", 6, 2, 6), item("arrow", 6, 2, 8),
                              item("gold_nugget", 6, 2, 6), item("rotten_flesh", 6, 1, 3), item("skeleton_skull", 1)]),
                    ((1, 2), [item("gold_ingot", 5, 1, 3), item("iron_ingot", 5, 1, 3), item("experience_bottle", 3, 1, 3),
                              item("bow", 2, ench=(5, 12)), empty(8)])),
    "escaldo": place_chest(((3, 5), [item("book", 10, 1, 3), item("paper", 10, 2, 6), item("feather", 6, 1, 3), item("ink_sac", 6, 1, 3),
                               item("candle", 4, 1, 2), item("writable_book", 3), named("writable_book", "saga", 2)]),
                     ((1, 2), [item("book", 6, rand_ench=True), item("experience_bottle", 5, 2, 5), item("amethyst_shard", 3, 1, 3),
                               item("music_disc_far", 2), item("goat_horn", 2), empty(5)])),
    "ofrendas": place_chest(((3, 5), [item("gold_ingot", 8, 1, 3), item("gold_nugget", 10, 3, 9), item("emerald", 6, 1, 3),
                                item("amethyst_shard", 5, 1, 4), item("candle", 5, 1, 3), item("honey_bottle", 3, 1, 2),
                                named("chiseled_tuff", "runa", 2)]),
                      ((1, 2), [item("diamond", 2), item("golden_apple", 3), item("experience_bottle", 4, 2, 5),
                                item("lapis_lazuli", 4, 2, 6), empty(6)])),
    "codicia": place_chest(((4, 6), [item("gold_ingot", 10, 2, 5), item("gold_nugget", 8, 4, 10), item("emerald", 8, 2, 5),
                               item("raw_gold", 6, 1, 4)]),
                     ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), item("gold_block", 1), empty(6)])),
    # cámara del tesoro
    "premium": table(
        pool((3, 5), [named("iron_axe", "hacha", 6, levels=(10, 20)), named("goat_horn", "cuerno", 5),
                      named("shield", "escudo", 4, levels=(5, 15)),
                      item("coast_armor_trim_smithing_template", 4), item("wild_armor_trim_smithing_template", 3),
                      item("rib_armor_trim_smithing_template", 2), item("music_disc_far", 3), item("music_disc_strad", 3),
                      item("music_disc_otherside", 2), item("gold_ingot", 6, 2, 6), item("emerald", 6, 3, 8),
                      item("book", 4, ench=(10, 20)), item("golden_apple", 3), item("spyglass", 2)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                      item("experience_bottle", 5, 2, 6), item("golden_carrot", 4, 1, 3)], extra=True),
        pool(1, [empty(90), item("diamond_axe", 3, ench=(20, 30)), item("diamond_chestplate", 3, ench=(20, 30)),   # 10 % más fuerte
                 item("enchanted_golden_apple", 2), item("totem_of_undying", 2)])),
}
