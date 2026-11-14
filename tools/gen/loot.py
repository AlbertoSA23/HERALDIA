"""Tablas de botín equilibradas (solo objetos vanilla)."""


def item(name, w, lo=1, hi=1, ench=None, rand_ench=False, dmg=None):
    mods = []
    if hi > 1 or lo > 1:
        mods.append({"type": "minecraft:set_count", "count": {"type": "minecraft:uniform", "min": lo, "max": hi}})
    if dmg:
        mods.append({"type": "minecraft:set_damage", "damage": {"type": "minecraft:uniform", "min": dmg[0], "max": dmg[1]}})
    if ench:
        mods.append({"type": "minecraft:enchant_with_levels", "levels": {"type": "minecraft:uniform", "min": ench[0], "max": ench[1]},
                     "options": "#minecraft:on_random_loot"})
    if rand_ench:
        mods.append({"type": "minecraft:enchant_randomly", "options": "#minecraft:on_random_loot"})
    e = {"type": "minecraft:item", "name": "minecraft:" + name, "weight": w}
    if len(mods) == 1:
        e["modifier"] = mods[0]
    elif mods:
        e["modifier"] = mods
    return e


def empty(w):
    return {"type": "minecraft:empty", "weight": w}


def table(*pools):
    return {"type": "minecraft:chest", "pools": [{"rolls": r if isinstance(r, int) else {"type": "minecraft:uniform", "min": r[0], "max": r[1]},
                                                  "entries": e} for r, e in pools]}


FOOD = [item("bread", 15, 1, 4), item("apple", 12, 1, 3), item("carrot", 10, 1, 4), item("potato", 10, 1, 4),
        item("baked_potato", 6, 1, 3), item("cooked_cod", 6, 1, 3), item("pumpkin_pie", 3, 1, 2), item("cookie", 4, 2, 6)]
BASIC = [item("stick", 10, 2, 6), item("coal", 10, 1, 5), item("torch", 8, 2, 6), item("string", 6, 1, 4),
         item("leather", 5, 1, 3), item("wheat", 8, 2, 6), item("feather", 5, 1, 4), item("paper", 5, 1, 4),
         item("flint", 4, 1, 3), item("bone_meal", 5, 1, 4), item("oak_sapling", 3, 1, 2)]

TABLES = {
    "comun": table(((2, 5), FOOD + BASIC + [empty(10)]),
                   (1, [item("emerald", 2), item("iron_nugget", 6, 2, 8), item("bucket", 2), item("shears", 1), empty(30)])),
    "poco_comun": table(((3, 6), FOOD + BASIC),
                        ((1, 2), [item("iron_ingot", 8, 1, 3), item("gold_ingot", 4, 1, 2), item("emerald", 6, 1, 3),
                                  item("lapis_lazuli", 4, 2, 6), item("redstone", 4, 2, 6), item("book", 5, 1, 2),
                                  item("iron_pickaxe", 2, dmg=(0.5, 0.9)), item("iron_axe", 2, dmg=(0.5, 0.9)),
                                  item("leather_chestplate", 2, rand_ench=False), item("saddle", 1), empty(10)])),
    "raro": table(((2, 4), FOOD),
                  ((2, 4), [item("iron_ingot", 10, 2, 5), item("gold_ingot", 6, 1, 4), item("emerald", 8, 2, 5),
                            item("diamond", 2, 1, 2), item("book", 4, 1, 1, rand_ench=True), item("name_tag", 2),
                            item("iron_sword", 3, ench=(5, 15)), item("iron_chestplate", 2, ench=(5, 15)),
                            item("golden_apple", 2), item("experience_bottle", 4, 2, 6), item("spyglass", 1),
                            item("iron_horse_armor", 1), item("lead", 2)])),
    "epico": table(((1, 3), [item("diamond", 8, 1, 3), item("emerald", 8, 3, 8), item("gold_block", 2),
                             item("book", 6, ench=(25, 30)), item("diamond_sword", 2, ench=(20, 30)),
                             item("diamond_chestplate", 1, ench=(20, 30)), item("golden_apple", 5, 1, 2),
                             item("enchanted_golden_apple", 1), item("diamond_horse_armor", 1),
                             item("wild_armor_trim_smithing_template", 2), item("coast_armor_trim_smithing_template", 2),
                             item("music_disc_cat", 1), item("music_disc_mellohi", 1), item("experience_bottle", 5, 4, 10)]),
                   ((2, 4), FOOD + [item("iron_ingot", 6, 2, 6), item("gold_ingot", 5, 2, 5)])),
}
# temáticos
TABLES["iglesia"] = table(((2, 4), [item("candle", 8, 1, 4), item("bread", 8, 1, 3), item("paper", 6, 2, 5),
                                    item("book", 5, 1, 2), item("glass_bottle", 6, 1, 3), item("redstone", 5, 2, 6),
                                    item("lapis_lazuli", 5, 2, 6), item("glowstone_dust", 3, 1, 4)]),
                          (1, [item("experience_bottle", 6, 2, 5), item("golden_apple", 1), item("book", 4, rand_ench=True),
                               item("emerald", 5, 1, 3), empty(8)]))
TABLES["cripta"] = TABLES["epico"]
TABLES["ayuntamiento"] = table(((2, 4), [item("paper", 10, 2, 8), item("map", 6), item("compass", 3), item("book", 6, 1, 3),
                                         item("writable_book", 4), item("emerald", 10, 2, 6), item("gold_ingot", 6, 1, 4),
                                         item("bread", 8, 1, 3)]),
                               (1, [item("name_tag", 3), item("diamond", 2), item("spyglass", 3), item("golden_apple", 1), empty(6)]))
TABLES["herreria"] = table(((2, 5), [item("iron_ingot", 12, 1, 5), item("iron_nugget", 8, 3, 9), item("coal", 10, 2, 8),
                                     item("gold_ingot", 4, 1, 3), item("bread", 6, 1, 3), item("obsidian", 3, 1, 3),
                                     item("iron_pickaxe", 4), item("iron_sword", 4), item("iron_helmet", 3), item("iron_boots", 3),
                                     item("shield", 3), item("bucket", 3)]),
                           (1, [item("diamond", 2, 1, 2), item("iron_chestplate", 3, ench=(5, 15)), item("chainmail_chestplate", 2), empty(6)]))
TABLES["taberna"] = table(((3, 6), [item("bread", 10, 1, 4), item("cooked_beef", 8, 1, 3), item("cooked_porkchop", 8, 1, 3),
                                    item("cooked_chicken", 6, 1, 3), item("mushroom_stew", 4), item("rabbit_stew", 3),
                                    item("honey_bottle", 6, 1, 3), item("potion", 0) if False else item("glass_bottle", 6, 1, 3),
                                    item("sweet_berries", 6, 2, 6), item("emerald", 4, 1, 2), item("cake", 1)]))
TABLES["posada"] = table(((2, 5), FOOD + [item("white_wool", 6, 1, 3), item("candle", 4, 1, 3), item("emerald", 3, 1, 2),
                                          item("map", 2), item("lead", 2)]))
TABLES["biblioteca"] = table(((2, 5), [item("book", 12, 1, 4), item("paper", 12, 2, 8), item("feather", 6, 1, 3),
                                       item("ink_sac", 6, 1, 3), item("writable_book", 4), item("map", 3),
                                       item("bookshelf", 3, 1, 2), item("lapis_lazuli", 4, 2, 6)]),
                             (1, [item("book", 6, rand_ench=True), item("experience_bottle", 4, 2, 5), empty(6)]))
TABLES["granja"] = table(((3, 7), [item("wheat", 12, 3, 10), item("wheat_seeds", 10, 3, 10), item("carrot", 8, 2, 6),
                                   item("potato", 8, 2, 6), item("beetroot_seeds", 6, 2, 6), item("pumpkin_seeds", 5, 1, 4),
                                   item("melon_seeds", 5, 1, 4), item("bone_meal", 8, 2, 6), item("egg", 6, 1, 4),
                                   item("leather", 4, 1, 3), item("iron_hoe", 2), item("bucket", 2)]))
TABLES["molino"] = table(((3, 6), [item("wheat", 12, 4, 12), item("bread", 12, 2, 6), item("hay_block", 6, 1, 3),
                                   item("sugar", 6, 2, 6), item("wheat_seeds", 8, 2, 8), item("cookie", 4, 2, 6)]))
TABLES["mercado"] = table(((3, 6), FOOD + [item("emerald", 8, 1, 4), item("white_wool", 5, 1, 4), item("leather", 5, 1, 3),
                                           item("arrow", 5, 4, 12), item("flint", 4, 1, 4), item("melon_slice", 6, 2, 6),
                                           item("pumpkin", 3), item("honeycomb", 3, 1, 3)]))
TABLES["puerto"] = table(((3, 6), [item("cod", 12, 1, 5), item("salmon", 10, 1, 4), item("cooked_cod", 8, 1, 3),
                                   item("dried_kelp", 8, 2, 8), item("string", 6, 1, 4), item("fishing_rod", 4),
                                   item("lead", 3), item("map", 3), item("compass", 2), item("emerald", 4, 1, 3),
                                   item("tropical_fish", 2), item("nautilus_shell", 1)]))
