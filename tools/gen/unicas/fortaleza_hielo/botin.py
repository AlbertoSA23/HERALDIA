"""Botín de la fortaleza de hielo: solo vanilla, modesto en los cofres menores y más rico cuanto más escondido.
Cada tabla termina con un grupo extra marcado solo_sin_lootr (con Lootr cada jugador recibe solo lo demás)."""
from loot import item, empty
from unicas._comun import botin as _comun

K = "heraldia.unicas.fortaleza_hielo."
NAMES = {   # clave -> (es_es, en_us)
    "guardian": ("El Rey Escarcha", "The Frost King"),
    "hacha": ("Hacha del Rey Escarcha", "Frost King's Axe"),
    "corona": ("Corona de escarcha", "Crown of Rime"),
    "arco": ("Arco del vigía glacial", "Glacial Sentry's Bow"),
    "espada": ("Espada del invierno eterno", "Sword of Everlasting Winter"),
    "botas": ("Botas del paso nevado", "Snowstride Boots"),
    "colmillo": ("Colmillo del Rey Escarcha", "Frost King's Fang"),
    "coraza": ("Coraza del glaciar", "Glacier Plate"),
}
LANG = {"es_es": {K + k: v[0] for k, v in NAMES.items()}, "en_us": {K + k: v[1] for k, v in NAMES.items()}}


def named(name, key, w, ench=None):
    return _comun.named(name, w, K + key, NAMES[key][0], ench=ench)


def pools(*groups):
    """groups: (rolls, entries[, solo_sin_lootr])."""
    return _comun.table(*(_comun.pool(*g) for g in groups))


FOOD = [item("bread", 10, 1, 3), item("cooked_mutton", 6, 1, 2), item("cooked_rabbit", 5, 1, 2),
        item("baked_potato", 6, 1, 3), item("sweet_berries", 6, 2, 6)]

LOOT = {
    "barracones": pools(((2, 4), FOOD + [item("arrow", 8, 2, 8), item("leather", 5, 1, 3), item("string", 5, 1, 3),
                                         item("iron_nugget", 6, 2, 6), item("torch", 5, 2, 5), item("stone_sword", 2),
                                         item("leather_helmet", 2, dmg=(0.3, 0.7)), item("leather_boots", 2, dmg=(0.3, 0.7))]),
                        (1, [item("iron_ingot", 3, 1, 2), item("emerald", 2), item("snowball", 3, 4, 12), empty(4)], True)),
    "cocina": pools(((3, 5), [item("cooked_beef", 8, 1, 3), item("cooked_mutton", 8, 1, 3), item("rabbit_stew", 3),
                              item("mushroom_stew", 3), item("sweet_berries", 8, 2, 8), item("bowl", 4, 1, 3),
                              item("coal", 6, 2, 6), item("salmon", 5, 1, 3), item("pumpkin_pie", 2)]),
                    (1, [item("honey_bottle", 3), item("cake", 1), item("emerald", 1), empty(4)], True)),
    "perrera": pools(((2, 4), [item("bone", 12, 2, 6), item("bone_meal", 6, 2, 6), item("lead", 4), item("leather", 5, 1, 3),
                               item("rabbit_hide", 5, 1, 3), item("rotten_flesh", 6, 1, 4)]),
                     (1, [item("name_tag", 1), item("lead", 2), item("rabbit_foot", 1), empty(5)], True)),
    "garita": pools(((2, 4), [item("arrow", 10, 4, 12), item("bread", 6, 1, 3), item("torch", 6, 2, 6),
                              item("crossbow", 3, dmg=(0.3, 0.8)), item("bow", 3, dmg=(0.3, 0.8)), item("iron_nugget", 5, 3, 8),
                              item("spyglass", 1)]),
                    (1, [item("iron_ingot", 4, 1, 3), item("emerald", 2, 1, 2), empty(4)], True)),
    "atalaya": pools(((2, 3), [item("map", 6), item("compass", 3), item("paper", 6, 2, 5), item("glow_ink_sac", 3, 1, 3),
                               item("spyglass", 2), item("bread", 5, 1, 2), item("candle", 4, 1, 3)]),
                     (1, [item("emerald", 4, 1, 3), item("gold_ingot", 2, 1, 2), empty(3)], True)),
    "galeria": pools(((2, 4), [item("packed_ice", 6, 2, 6), item("blue_ice", 3, 1, 3), item("lapis_lazuli", 6, 2, 6),
                               item("candle", 5, 1, 3), item("book", 5, 1, 2), item("painting", 3), item("white_dye", 4, 1, 3),
                               item("light_blue_dye", 4, 1, 3)]),
                     (1, [item("amethyst_shard", 4, 1, 4), item("emerald", 3, 1, 2), item("book", 2, rand_ench=True), empty(4)], True)),
    "cripta": pools(((3, 5), [item("bone", 12, 2, 6), item("arrow", 8, 2, 8), item("gold_nugget", 8, 2, 8),
                              item("rotten_flesh", 6, 1, 3), item("iron_ingot", 6, 1, 3), item("emerald", 5, 1, 3),
                              item("candle", 4, 1, 2)]),
                    ((1, 2), [item("gold_ingot", 6, 1, 3), item("experience_bottle", 4, 1, 3), item("golden_apple", 1),
                              item("book", 3, rand_ench=True), item("iron_sword", 2, ench=(5, 12)), empty(4)]),
                    (1, [item("gold_ingot", 4, 1, 2), item("diamond", 1), empty(5)], True)),
    "tesoro_real": pools(((3, 5), [item("gold_ingot", 10, 2, 5), item("emerald", 10, 2, 6), item("lapis_lazuli", 6, 3, 8),
                                   item("experience_bottle", 6, 2, 5), item("candle", 3, 1, 3)]),
                         ((1, 2), [item("diamond", 4, 1, 2), item("golden_apple", 4), item("book", 5, ench=(15, 25)),
                                   named("golden_helmet", "corona", 4, ench=(10, 20)),
                                   named("iron_axe", "hacha", 3, ench=(10, 20)),
                                   item("sentry_armor_trim_smithing_template", 2)]),
                         (1, [item("diamond", 3, 1, 2), item("gold_block", 1), item("emerald", 4, 2, 4)], True)),
    # Premium: el primer grupo da la pieza principal: 90 % vistosa, 10 % algo más fuerte.
    "premium": pools((1, [named("iron_sword", "espada", 20, ench=(15, 25)), named("bow", "arco", 20, ench=(15, 25)),
                          named("iron_boots", "botas", 15, ench=(15, 25)), named("golden_helmet", "corona", 15, ench=(15, 25)),
                          item("music_disc_strad", 10), item("music_disc_far", 10),
                          named("diamond_sword", "colmillo", 4, ench=(25, 30)),
                          named("diamond_chestplate", "coraza", 3, ench=(25, 30)),
                          item("enchanted_golden_apple", 2), item("totem_of_undying", 1)]),
                     ((2, 3), [item("sentry_armor_trim_smithing_template", 6), item("coast_armor_trim_smithing_template", 5),
                               item("tide_armor_trim_smithing_template", 4), item("wild_armor_trim_smithing_template", 4),
                               item("music_disc_mall", 3), item("music_disc_stal", 3), item("book", 6, ench=(20, 30)),
                               item("blue_ice", 3, 4, 12), item("golden_apple", 5, 1, 2)]),
                     ((3, 5), [item("gold_ingot", 10, 3, 7), item("emerald", 10, 3, 8), item("diamond", 5, 1, 3),
                               item("experience_bottle", 8, 3, 8), item("lapis_lazuli", 6, 4, 10)]),
                     ((1, 2), [item("diamond", 6, 1, 3), item("emerald", 6, 4, 8), item("golden_apple", 3),
                               item("experience_bottle", 5, 4, 8)], True)),
}
