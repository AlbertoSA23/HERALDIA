"""Coast loot (heraldia:costa/<table>): modest and nautical. The lighthouse keeps the keeper's things (maps, compass, spyglass,
candles and something to eat); the shipwreck hold, the ship's provisions and supplies; the captain's cabin, his maps and
instruments and some gold (and, rarely, a treasure map fragment, which coast.write adds with treasure.with_hint).
The second group of each chest is "only without Lootr", as in the rest of Heraldia. All the tables live under
heraldia:costa/, which loot/Reposicion recognises (they are restocked) and the difficulty scales."""
from loot import item, empty
from uniques._common import chest_loot

LOOT = {
    # chest of the lighthouse guard room and barrel of the keeper's house
    "faro": chest_loot.place_chest(((2, 4), [item("map", 5, 1, 2), item("compass", 3), item("spyglass", 2), item("candle", 4, 1, 3),
                                  item("cooked_cod", 6, 1, 4), item("bread", 5, 1, 3), item("paper", 4, 2, 6),
                                  item("glow_ink_sac", 2, 1, 3), item("coal", 4, 2, 6), item("lantern", 2),
                                  item("emerald", 2, 1, 2), empty(4)]),
                        ((1, 1), [item("emerald", 2, 1, 2), item("nautilus_shell", 1), item("clock", 1), empty(6)])),
    # galleon hold: provisions and supplies
    "bodega": chest_loot.place_chest(((3, 6), [item("cod", 8, 1, 4), item("salmon", 6, 1, 3), item("dried_kelp", 6, 2, 6),
                                    item("wheat", 5, 2, 6), item("potato", 5, 1, 4), item("coal", 6, 2, 6),
                                    item("string", 5, 1, 4), item("leather", 4, 1, 3), item("paper", 4, 1, 4),
                                    item("gunpowder", 3, 1, 3), item("iron_nugget", 4, 2, 7), item("lead", 2),
                                    item("bamboo", 3, 2, 6), empty(3)]),
                          ((1, 2), [item("iron_ingot", 3, 1, 2), item("gold_nugget", 4, 2, 6), empty(6)])),
    # captain's cabin: maps, instruments and the ship's strongbox
    "camarote": chest_loot.place_chest(((2, 4), [item("map", 5, 1, 2), item("compass", 4), item("spyglass", 3), item("clock", 2),
                                      item("gold_ingot", 4, 1, 3), item("gold_nugget", 5, 3, 9), item("emerald", 5, 1, 3),
                                      item("book", 3, rand_ench=True), item("iron_sword", 2, dmg=(0.3, 0.8)),
                                      item("name_tag", 1), item("feather", 3, 1, 3), item("ink_sac", 3, 1, 3), empty(3)]),
                            ((1, 1), [item("emerald", 3, 1, 2), item("nautilus_shell", 2), item("gold_ingot", 2), empty(6)])),
}

# What never appears on the coast (tools/gen/tests/test_coast.py goes through it).
FORBIDDEN = ("netherite", "elytra", "enchanted_golden_apple", "totem_of_undying", "smithing_template",
             "heart_of_the_sea", "trident", "diamond", "music_disc", "golden_apple", "_block")
