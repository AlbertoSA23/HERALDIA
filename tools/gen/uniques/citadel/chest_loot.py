"""Botín de la ciudadela (solo vanilla). Cada tabla lleva un grupo extra marcado solo_sin_lootr."""
from loot import item, empty
from uniques._common.chest_loot import pool, table, named, book  # noqa: F401  (piezas comunes)


FOOD = [item("bread", 12, 1, 3), item("cooked_mutton", 8, 1, 2), item("baked_potato", 8, 1, 3), item("carrot", 6, 1, 3)]
SHOWY = [
    named("iron_axe", 12, "item.heraldia.ciudadela.hacha", "Hacha de Borin", {"minecraft:sharpness": 2, "minecraft:unbreaking": 2}),
    named("golden_helmet", 12, "item.heraldia.ciudadela.yelmo", "Yelmo del Rey Bajo la Montaña", {"minecraft:protection": 2}),
    named("honey_bottle", 8, "item.heraldia.ciudadela.jarra", "Jarra de la última cerveza"),
    named("iron_pickaxe", 10, "item.heraldia.ciudadela.pico", "Pico del maestro minero", {"minecraft:efficiency": 2, "minecraft:unbreaking": 1}),
    item("music_disc_otherside", 6), item("music_disc_relic", 6), item("music_disc_mellohi", 6),
    item("shaper_armor_trim_smithing_template", 8), item("host_armor_trim_smithing_template", 8),
    item("wayfinder_armor_trim_smithing_template", 6), item("gold_block", 8, 1, 2)]
STRONG = [
    named("diamond_pickaxe", 3, "item.heraldia.ciudadela.pico_diamante", "Pico de la veta profunda",
          {"minecraft:efficiency": 3, "minecraft:unbreaking": 2}),
    named("diamond_chestplate", 3, "item.heraldia.ciudadela.peto", "Peto de la guardia real", {"minecraft:protection": 2}),
    item("enchanted_golden_apple", 2), book(2, {"minecraft:fortune": 3})]
assert sum(e["weight"] for e in SHOWY) == 90 and sum(e["weight"] for e in STRONG) == 10

TABLES = {
    "menor": table(pool((2, 4), FOOD + [item("torch", 10, 2, 6), item("coal", 10, 1, 4), item("iron_nugget", 8, 2, 6),
                                        item("string", 5, 1, 3), item("candle", 4, 1, 2), empty(8)]),
                   pool(1, [item("iron_ingot", 6, 1, 2), item("gold_nugget", 6, 2, 6), item("emerald", 3), empty(12)], True)),
    "barracones": table(pool((2, 4), FOOD + [item("arrow", 12, 4, 12), item("bow", 4, dmg=(0.3, 0.7)),
                                             item("iron_sword", 3, dmg=(0.3, 0.7)), item("shield", 3),
                                             item("chainmail_helmet", 2), item("chainmail_boots", 2), item("leather", 5, 1, 3)]),
                        pool(1, [item("iron_helmet", 4, ench=(5, 10)), item("crossbow", 3), item("iron_ingot", 5, 1, 3), empty(8)], True)),
    "almacen": table(pool((2, 4), [item("coal", 12, 2, 6), item("torch", 10, 2, 8), item("rail", 8, 2, 6), item("leather", 6, 1, 3),
                                   item("arrow", 6, 2, 8), item("iron_nugget", 8, 2, 6), item("wheat", 6, 2, 6), item("bread", 6, 1, 3)]),
                     pool(1, [item("iron_ingot", 6, 1, 3), item("powered_rail", 2, 1, 2), empty(10)], True)),
    "forja": table(pool((3, 5), [item("iron_ingot", 12, 2, 5), item("coal", 12, 3, 8), item("gold_nugget", 8, 2, 8),
                                 item("iron_nugget", 8, 3, 9), item("iron_pickaxe", 3), item("iron_axe", 3), item("bucket", 3),
                                 item("shield", 2), item("flint_and_steel", 2), item("iron_bars", 3, 2, 6)]),
                   pool(1, [item("diamond", 2), item("iron_chestplate", 3, ench=(5, 12)), item("gold_ingot", 6, 1, 3), empty(8)], True)),
    "cerveceria": table(pool((3, 6), [item("wheat", 12, 2, 6), item("bread", 10, 1, 4), item("sugar", 8, 1, 4),
                                      item("honey_bottle", 6, 1, 2), item("glass_bottle", 8, 1, 4), item("sweet_berries", 6, 2, 6),
                                      item("brown_mushroom", 5, 1, 3), item("red_mushroom", 4, 1, 2), item("pumpkin_pie", 3)]),
                        pool(1, [item("golden_carrot", 5, 1, 3), item("emerald", 4, 1, 2), item("cake", 1), empty(8)], True)),
    "mina": table(pool((3, 5), [item("raw_iron", 12, 2, 5), item("raw_gold", 6, 1, 3), item("coal", 12, 3, 8),
                                item("lapis_lazuli", 6, 2, 6), item("redstone", 6, 2, 6), item("rail", 8, 3, 8),
                                item("iron_pickaxe", 3, dmg=(0.2, 0.6)), item("torch", 6, 2, 6), item("bread", 6, 1, 3)]),
                  pool(1, [item("diamond", 3), item("golden_apple", 1), item("raw_gold", 4, 1, 3), empty(10)], True)),
    "oculto": table(pool((2, 4), [item("gold_ingot", 12, 2, 4), item("emerald", 10, 2, 5), item("diamond", 3, 1, 2),
                                  item("book", 4, rand_ench=True), item("golden_apple", 3), item("experience_bottle", 6, 2, 5),
                                  item("name_tag", 2), item("iron_ingot", 8, 2, 5)]),
                    pool(1, [item("diamond", 4, 1, 2), item("book", 4, ench=(10, 20)), empty(6)], True)),
    "real": table(pool((3, 5), [item("diamond", 6, 1, 3), item("emerald", 10, 3, 6), item("gold_ingot", 10, 3, 6),
                                named("golden_helmet", 4, "item.heraldia.ciudadela.corona", "Corona del rey enano", {"minecraft:protection": 2}),
                                item("book", 5, ench=(15, 25)), item("music_disc_ward", 2), item("music_disc_cat", 2),
                                item("raiser_armor_trim_smithing_template", 3), item("experience_bottle", 6, 3, 6)]),
                  pool(1, [item("golden_apple", 4), item("gold_block", 3), empty(6)], True)),
    "boveda": table(pool((4, 6), [item("gold_ingot", 14, 4, 10), item("gold_block", 3), item("raw_gold", 10, 2, 6),
                                  item("emerald", 10, 4, 8), item("diamond", 5, 1, 3), item("golden_apple", 4),
                                  item("gold_nugget", 10, 6, 16)]),
                    pool(1, [item("diamond", 5, 2, 3), item("book", 4, ench=(15, 25)), empty(6)], True)),
    "premium": table(pool((2, 3), SHOWY),
                     pool(1, SHOWY + STRONG),
                     pool((3, 5), [item("gold_ingot", 10, 4, 9), item("emerald", 8, 3, 7), item("gold_nugget", 6, 8, 20),
                                   item("diamond", 2, 1, 2)]),
                     pool(2, SHOWY, True)),
}
