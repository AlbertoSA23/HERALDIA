"""Botín del palacio: solo vanilla, más rico cuanto más escondido. El grupo extra de cada cofre es solo_sin_lootr."""
from loot import item, empty
from .._common.chest_loot import pool, table, lang, named as _named

NAMES = {   # clave -> (es_es, en_us)
    "hoja": ("Hoja del Dragón Celeste", "Blade of the Celestial Dragon"),
    "coraza": ("Coraza de la Guardia Imperial", "Cuirass of the Imperial Guard"),
    "sable": ("Sable del General de Jade", "Sabre of the Jade General"),
    "ballesta": ("Ballesta de la Muralla", "Crossbow of the Great Wall"),
    "yelmo": ("Yelmo del Sol Naciente", "Helm of the Rising Sun"),
    "sello": ("Sello Imperial", "Imperial Seal"),
    "abanico": ("Abanico de la Emperatriz", "Fan of the Empress"),
    "tratado": ("Tratado de Estrategia", "Treatise on Strategy"),
    "corona": ("Corona del Hijo del Cielo", "Crown of the Son of Heaven"),
}


def named(name, w, key, ench=None):
    """Objeto con nombre del palacio (clave item.heraldia.palacio.<key>, respaldo en español)."""
    return _named(name, w, f"item.heraldia.palacio.{key}", NAMES[key][0], levels=ench)


FOOD = [item("bread", 10, 1, 3), item("cooked_cod", 6, 1, 3), item("baked_potato", 6, 1, 3), item("sweet_berries", 6, 2, 6),
        item("honey_bottle", 3), item("dried_kelp", 6, 2, 6), item("cookie", 4, 2, 5)]

LOOT = {
    "guardia": table(pool((2, 4), FOOD + [item("arrow", 8, 3, 10), item("torch", 6, 2, 5), item("iron_nugget", 6, 2, 6),
                                          item("string", 4, 1, 3), item("bone", 4, 1, 3), item("leather", 3, 1, 2)]),
                     pool(1, [item("iron_ingot", 4, 1, 2), item("emerald", 2), item("shield", 1), empty(6)], extra=True)),
    "almacen": table(pool((3, 5), FOOD + [item("wheat", 8, 2, 6), item("sugar", 4, 1, 4), item("bowl", 3, 1, 3),
                                          item("bamboo", 4, 2, 6), item("cocoa_beans", 2, 1, 3)]),
                     pool(1, [item("honeycomb", 2, 1, 2), item("cake", 1), empty(6)], extra=True)),
    "torre": table(pool((2, 3), [item("arrow", 10, 4, 12), item("torch", 6, 2, 6), item("bread", 6, 1, 2),
                                 item("spyglass", 1), item("string", 4, 1, 3)]),
                   pool(1, [item("iron_ingot", 3), item("emerald", 2), empty(6)], extra=True)),
    "jardin": table(pool((2, 4), [item("pink_petals", 8, 1, 4), item("cherry_sapling", 5, 1, 2), item("bamboo", 6, 2, 6),
                                  item("bone_meal", 6, 2, 5), item("lily_pad", 4, 1, 3), item("sweet_berries", 4, 2, 5),
                                  item("string", 3, 1, 3)]),
                   pool(1, [item("emerald", 2), item("glow_berries", 3, 1, 4), empty(6)], extra=True)),
    "pabellon": table(pool((3, 5), [item("pink_dye", 6, 1, 4), item("red_dye", 6, 1, 4), item("white_dye", 4, 1, 3),
                                    item("candle", 6, 1, 3), item("pink_petals", 6, 1, 4), item("string", 5, 1, 4),
                                    item("amethyst_shard", 4, 1, 3), item("gold_nugget", 6, 2, 7), item("paper", 4, 1, 3),
                                    item("cherry_sapling", 3), item("glow_ink_sac", 2, 1, 2)]),
                      pool(1, [item("emerald", 5, 1, 2), item("gold_ingot", 3), item("name_tag", 1), item("lead", 1), empty(4)]),
                      pool(1, [item("emerald", 3, 1, 3), item("gold_ingot", 3, 1, 2), empty(4)], extra=True)),
    "biblioteca": table(pool((3, 5), [item("paper", 10, 2, 6), item("book", 8, 1, 3), item("ink_sac", 6, 1, 3),
                                      item("feather", 6, 1, 3), item("writable_book", 3), item("map", 2), item("candle", 4, 1, 2)]),
                        pool(1, [item("book", 2, ench=(5, 10)), item("lapis_lazuli", 4, 2, 5), item("compass", 1), empty(6)]),
                        pool(1, [item("experience_bottle", 3, 1, 3), item("emerald", 2), empty(6)], extra=True)),
    "tesoreria_menor": table(pool((3, 5), [item("gold_nugget", 10, 3, 10), item("iron_nugget", 8, 3, 10),
                                           item("copper_ingot", 6, 1, 4), item("raw_copper", 4, 1, 3), item("emerald", 2)]),
                             pool(1, [item("gold_ingot", 3), item("emerald", 2, 1, 2), empty(6)], extra=True)),
    "salon": table(pool((3, 5), [item("candle", 6, 1, 3), item("gold_nugget", 8, 3, 9), item("golden_carrot", 4, 1, 3),
                                 item("emerald", 5, 1, 3), item("clock", 2), item("spyglass", 2), item("yellow_banner", 2)]),
                   pool(1, [named("name_tag", 2, "sello"), item("gold_ingot", 4, 1, 3), item("golden_apple", 1), empty(4)]),
                   pool(1, [item("emerald", 3, 1, 3), item("gold_ingot", 3, 1, 2), empty(4)], extra=True)),
    "tesoreria": table(pool((3, 5), [item("gold_ingot", 10, 2, 5), item("emerald", 8, 2, 6), item("raw_gold", 6, 1, 4),
                                     item("gold_nugget", 6, 4, 12), item("diamond", 1)]),
                       pool(1, [item("golden_apple", 2), item("golden_horse_armor", 1), item("experience_bottle", 3, 2, 5), empty(4)]),
                       pool((1, 2), [item("gold_ingot", 4, 1, 3), item("emerald", 4, 1, 4), item("diamond", 1), empty(3)], extra=True)),
    "biblioteca_secreta": table(pool((1, 2), [item("book", 10, ench=(10, 20))]),
                                pool((2, 4), [item("experience_bottle", 6, 2, 6), item("lapis_lazuli", 6, 4, 10),
                                              item("emerald", 4, 2, 5), item("paper", 4, 3, 8), item("amethyst_shard", 3, 2, 4)]),
                                pool(1, [named("writable_book", 3, "tratado"), item("diamond", 1), item("golden_apple", 1), empty(3)]),
                                pool(1, [item("book", 3, ench=(10, 20)), item("experience_bottle", 4, 2, 5), empty(4)], extra=True)),
    "pagoda": table(pool((2, 4), [item("ender_pearl", 4, 1, 2), item("amethyst_shard", 6, 2, 5), item("experience_bottle", 5, 2, 5),
                                  item("emerald", 6, 2, 5), item("gold_ingot", 5, 1, 3), item("candle", 4, 1, 3)]),
                    pool(1, [item("book", 4, ench=(10, 20)), item("golden_apple", 2), named("bamboo", 1, "abanico"), empty(3)]),
                    pool(1, [item("diamond", 1), item("ender_pearl", 3, 1, 2), empty(5)], extra=True)),
    "boveda": table(pool((3, 5), [item("gold_ingot", 8, 2, 6), item("emerald", 8, 3, 7), item("diamond", 3, 1, 2),
                                  item("lapis_lazuli", 4, 4, 9), item("experience_bottle", 4, 3, 6), item("ender_pearl", 3, 1, 2)]),
                    pool(1, [item("iron_sword", 3, ench=(10, 20)), item("iron_chestplate", 3, ench=(10, 20)),
                             item("bow", 3, ench=(10, 20)), item("golden_apple", 3), item("crossbow", 2, ench=(10, 20))]),
                    pool((1, 2), [item("diamond", 2, 1, 2), item("gold_ingot", 4, 2, 4), item("emerald", 4, 2, 5)], extra=True)),
    "premium": table(
        # joya: 90 % vistosa (nombre, oro y hierro, encantamientos moderados), 10 % algo más fuerte
        pool(1, [named("golden_sword", 20, "hoja", ench=(20, 30)), named("golden_chestplate", 18, "coraza", ench=(15, 25)),
                 named("iron_sword", 18, "sable", ench=(15, 25)), named("crossbow", 16, "ballesta", ench=(15, 25)),
                 named("golden_helmet", 18, "yelmo", ench=(15, 25)),
                 item("diamond_sword", 3, ench=(20, 30)),
                 item("diamond_chestplate", 3, ench=(20, 30)), item("enchanted_golden_apple", 2), item("totem_of_undying", 2)]),
        pool(1, [item("coast_armor_trim_smithing_template", 3), item("wild_armor_trim_smithing_template", 3),
                 item("wayfinder_armor_trim_smithing_template", 3), item("shaper_armor_trim_smithing_template", 3),
                 item("raiser_armor_trim_smithing_template", 3), item("host_armor_trim_smithing_template", 3),
                 item("sentry_armor_trim_smithing_template", 2), item("dune_armor_trim_smithing_template", 2)]),
        pool(1, [item("music_disc_relic", 3), item("music_disc_otherside", 2), item("music_disc_cat", 3),
                 item("music_disc_mellohi", 3), item("music_disc_far", 3), item("music_disc_creator_music_box", 2), empty(6)]),
        pool((3, 5), [item("gold_ingot", 8, 3, 8), item("emerald", 8, 4, 10), item("diamond", 3, 1, 3),
                      item("golden_apple", 3, 1, 2), item("lapis_lazuli", 4, 6, 12), named("golden_helmet", 1, "corona"),
                      named("name_tag", 2, "sello")]),
        pool((1, 2), [item("emerald", 5, 3, 8), item("gold_ingot", 5, 2, 6), item("diamond", 2, 1, 2),
                      item("wild_armor_trim_smithing_template", 1), item("music_disc_relic", 1)], extra=True)),
}

LANG = lang("item.heraldia.palacio.", NAMES)
LANG["es_es"]["heraldia.palacio.guardian"] = "Comandante de la Guardia Imperial"
LANG["en_us"]["heraldia.palacio.guardian"] = "Commander of the Imperial Guard"
