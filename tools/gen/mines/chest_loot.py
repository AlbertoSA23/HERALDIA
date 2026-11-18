"""Loot of the mine entrances (heraldia:minas/<table>): somewhat better than a vanilla mine's (more rolls of ingots,
raw ores and rails, an occasional emerald and an enchanted pickaxe from time to time), but moderate: no enchanted golden
apples, netherite, elytra, totems or smithing templates, and diamonds with low weight. The second group of each
chest is marked "only without Lootr" (with Lootr each player opens their own copy), as in the rest of Heraldia's structures; all
the tables live under heraldia:minas/, so any function that recognizes Heraldia's loot by its namespace
sees them too."""
from loot import item, empty
from uniques._common import chest_loot

# Comparison (vanilla mine chest, 26.3): 1 roll of {enchanted golden apple, golden apple, name tag, book,
# iron pickaxe, nothing}, 2-4 of {iron 1-5, gold 1-3, redstone 4-9, lapis lazuli 4-9, diamond 1-2 (weight 3), coal
# 3-8, bread, berries, seeds} and 3 of rails and torches.
LOOT = {
    # barrel in the small mouth's courtyard: everyday things
    "boca": chest_loot.place_chest(((2, 4), [item("torch", 8, 4, 12), item("coal", 8, 2, 6), item("bread", 6, 1, 3),
                                  item("rail", 6, 4, 10), item("iron_nugget", 5, 3, 9), item("string", 4, 1, 3),
                                  item("stone_pickaxe", 3, dmg=(0.3, 0.8)), item("iron_pickaxe", 1, dmg=(0.4, 0.8)),
                                  empty(4)]),
                        ((1, 1), [item("raw_iron", 3, 1, 3), item("raw_copper", 3, 2, 5), empty(6)])),
    # chests of the gallery rooms (all sizes)
    "galeria": chest_loot.table(
        chest_loot.pool(1, [item("golden_apple", 12), item("name_tag", 20), item("book", 12, rand_ench=True),
                       item("iron_pickaxe", 8, ench=(5, 15)), item("emerald", 10, 1, 3), item("glow_berries", 10, 3, 6),
                       empty(8)]),
        chest_loot.pool((3, 5), [item("iron_ingot", 12, 1, 5), item("gold_ingot", 6, 1, 3), item("redstone", 6, 4, 9),
                            item("lapis_lazuli", 6, 4, 9), item("diamond", 3, 1, 2), item("coal", 10, 3, 8),
                            item("raw_iron", 8, 2, 6), item("raw_copper", 6, 3, 8), item("raw_gold", 3, 1, 3),
                            item("amethyst_shard", 4, 1, 4), item("bread", 8, 1, 3)]),
        chest_loot.pool(3, [item("rail", 20, 4, 8), item("powered_rail", 6, 1, 4), item("detector_rail", 4, 1, 3),
                       item("activator_rail", 3, 1, 3), item("torch", 15, 1, 16)]),
        chest_loot.pool((1, 2), [item("iron_ingot", 4, 1, 3), item("emerald", 2, 1, 2), item("gold_nugget", 4, 3, 8),
                            empty(6)], extra=True)),
    # cargo minecart (chest_minecart) of the medium and large courtyard
    "vagoneta": chest_loot.place_chest(((4, 7), [item("raw_iron", 10, 2, 6), item("raw_copper", 10, 3, 9), item("raw_gold", 3, 1, 3),
                                      item("coal", 12, 4, 12), item("cobblestone", 8, 8, 24), item("gravel", 5, 4, 12),
                                      item("redstone", 4, 3, 8), item("lapis_lazuli", 3, 3, 7), item("flint", 4, 1, 4)]),
                            ((1, 2), [item("raw_iron", 4, 1, 3), item("coal", 4, 2, 6), empty(5)])),
    # foreman's chest (medium cabin and large office)
    "capataz": chest_loot.place_chest(((3, 5), [item("emerald", 6, 1, 4), item("iron_ingot", 8, 2, 5), item("gold_ingot", 4, 1, 3),
                                     item("compass", 3), item("clock", 2), item("map", 3), item("paper", 4, 2, 6),
                                     item("book", 4, rand_ench=True), item("iron_pickaxe", 3, ench=(8, 18)),
                                     item("iron_shovel", 2, ench=(5, 12)), item("golden_carrot", 3, 1, 3),
                                     item("cooked_beef", 5, 1, 3), item("diamond", 2, 1, 1), empty(3)]),
                           ((1, 2), [item("emerald", 3, 1, 2), item("gold_ingot", 2, 1, 2), empty(6)])),
    # smelter barrel
    "fundicion": chest_loot.place_chest(((3, 5), [item("iron_ingot", 12, 2, 6), item("copper_ingot", 10, 3, 8), item("gold_ingot", 4, 1, 3),
                                       item("coal", 10, 4, 10), item("charcoal", 5, 2, 6), item("iron_nugget", 6, 4, 12),
                                       item("gold_nugget", 4, 3, 9), item("bucket", 2), item("lava_bucket", 1),
                                       item("bricks", 3, 4, 10)]),
                             ((1, 2), [item("iron_ingot", 4, 1, 3), item("copper_ingot", 4, 2, 4), empty(6)])),
    # chest of the rich vein room (deep level of the large one): the best of the mines, without going beyond moderate
    "filon": chest_loot.table(
        chest_loot.pool((1, 2), [item("diamond", 6, 1, 3), item("emerald", 8, 2, 5), item("golden_apple", 6),
                            item("iron_pickaxe", 6, ench=(15, 25)), item("book", 6, rand_ench=True),
                            item("diamond_pickaxe", 1, dmg=(0.5, 0.9)), item("experience_bottle", 6, 2, 5)]),
        chest_loot.pool((4, 6), [item("gold_ingot", 10, 2, 5), item("raw_gold", 8, 2, 5), item("iron_ingot", 10, 3, 7),
                            item("redstone", 8, 6, 12), item("lapis_lazuli", 8, 6, 12), item("amethyst_shard", 6, 2, 6),
                            item("coal", 8, 4, 10)]),
        chest_loot.pool((1, 2), [item("gold_ingot", 4, 1, 3), item("emerald", 3, 1, 2), item("diamond", 1, 1, 1), empty(8)],
                   extra=True)),
}

# What never appears in a mine (the unit test walks through it; tools/gen/tests/test_mines.py).
FORBIDDEN = ("netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "music_disc", "diamond_block", "emerald_block", "gold_block")
DIAMONDS_MAX = 3          # diamonds at most per entry of a table
