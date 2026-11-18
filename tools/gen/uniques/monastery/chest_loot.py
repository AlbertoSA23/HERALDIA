"""Monastery loot (vanilla only). Richer the more hidden; each chest's extra group is skipped with Lootr."""
from .._common.chest_loot import item, empty, pool, table, named as _named

ID = "monasterio"
LANG_ITEMS = {}     # key -> (es, en)


def named(name, w, key, es, en, ench=None, levels=None, lo=1, hi=1):
    """Object with its own name (common piece), registering its text in both languages."""
    LANG_ITEMS[key] = (es, en)
    return _named(name, w, f"heraldia.unicas.{ID}.{key}", es, ench=ench, lo=lo, hi=hi, levels=levels)


def sub(name, w):
    return {"type": "minecraft:loot_table", "value": f"heraldia:unicas/{ID}/{name}", "weight": w}


FOOD = [item("bread", 12, 1, 3), item("apple", 10, 1, 3), item("baked_potato", 6, 1, 3), item("carrot", 6, 1, 4),
        item("cookie", 3, 2, 5), item("honey_bottle", 3)]
MONK = [item("candle", 8, 1, 3), item("paper", 8, 1, 4), item("wheat_seeds", 6, 2, 6), item("string", 5, 1, 3),
        item("glass_bottle", 5, 1, 2), item("feather", 4, 1, 3), item("book", 3), item("bone_meal", 4, 1, 3)]

LOOT = {
    "menor": table(pool((2, 4), FOOD + MONK),
                   pool(1, [item("iron_nugget", 6, 2, 6), item("emerald", 2), item("gold_nugget", 4, 2, 5),
                            item("lapis_lazuli", 3, 1, 3), empty(10)], extra=True)),
    "bodega": table(pool((3, 5), [item("honey_bottle", 8, 1, 3), item("sweet_berries", 8, 2, 6), item("apple", 10, 1, 4),
                                  item("glass_bottle", 6, 1, 3), item("sugar", 6, 1, 4), item("wheat", 6, 2, 6),
                                  item("bread", 6, 1, 3), item("glow_berries", 3, 1, 3)]),
                    pool(1, [item("emerald", 3, 1, 2), item("golden_carrot", 2, 1, 3), empty(8)], extra=True)),
    "celda": table(pool((2, 4), [item("candle", 10, 1, 2), item("writable_book", 4), item("paper", 8, 1, 3),
                                 item("bread", 8, 1, 2), item("string", 5, 1, 2), item("book", 4), item("ink_sac", 4)]),
                   pool(1, [item("emerald", 3), item("gold_nugget", 4, 1, 4), empty(8)], extra=True)),
    "biblioteca": table(pool((3, 5), [item("book", 12, 1, 3), item("paper", 12, 2, 6), item("feather", 6, 1, 3),
                                      item("ink_sac", 6, 1, 3), item("writable_book", 4), item("map", 3),
                                      item("compass", 2), item("glow_ink_sac", 2)]),
                        pool(1, [item("book", 5, rand_ench=True), item("experience_bottle", 4, 1, 3), empty(8)], extra=True)),
    "oculto": table(pool((2, 4), [item("emerald", 8, 1, 4), item("gold_ingot", 6, 1, 3), item("iron_ingot", 6, 1, 4),
                                  item("book", 4, ench=(5, 12)), item("candle", 5, 2, 4), item("experience_bottle", 4, 1, 4),
                                  item("golden_carrot", 4, 1, 3), item("name_tag", 1), item("golden_apple", 1)]),
                    pool((1, 2), [item("emerald", 6, 1, 3), item("amethyst_shard", 4, 1, 4), item("gold_ingot", 4, 1, 2),
                                  empty(4)], extra=True)),
    "ermita": table(pool((2, 4), [item("emerald", 8, 1, 4), item("amethyst_shard", 6, 2, 5), item("gold_ingot", 6, 1, 3),
                                  item("book", 5, ench=(5, 15)), item("candle", 5, 1, 3), item("experience_bottle", 4, 2, 4),
                                  item("golden_apple", 2), item("lapis_lazuli", 4, 2, 6)]),
                    pool((1, 2), [item("emerald", 6, 1, 3), item("gold_ingot", 4, 1, 2), item("diamond", 1), empty(5)],
                         extra=True)),
    "archivo": table(pool((3, 5), [item("book", 10, ench=(10, 20)), item("emerald", 8, 2, 6), item("paper", 6, 3, 8),
                                   item("experience_bottle", 6, 2, 6), item("name_tag", 3), item("map", 3),
                                   item("diamond", 2, 1, 2), item("golden_apple", 2), item("spyglass", 2),
                                   item("glow_ink_sac", 3, 1, 3)]),
                     pool((1, 2), [item("book", 4, ench=(15, 25)), item("emerald", 6, 2, 4), item("diamond", 2),
                                   item("gold_ingot", 5, 2, 4)], extra=True)),
    "catacumba": table(pool((3, 5), [item("bone", 10, 2, 6), item("gold_ingot", 6, 1, 4), item("iron_ingot", 8, 2, 5),
                                     item("emerald", 6, 1, 3), item("iron_helmet", 2, ench=(5, 12)),
                                     item("iron_chestplate", 2, ench=(5, 12)), item("golden_apple", 2),
                                     item("experience_bottle", 4, 2, 5), item("arrow", 5, 4, 10)]),
                       pool((1, 2), [item("diamond", 2), item("gold_ingot", 5, 1, 3), item("emerald", 5, 2, 4), empty(3)],
                            extra=True)),
    # premium: one main item (90 % showy, 10 % something stronger), values and the extra without Lootr
    "premium": table(pool(1, [sub("premium_vistoso", 90), sub("premium_fuerte", 10)]),
                     pool((3, 5), [item("emerald", 10, 3, 8), item("gold_ingot", 8, 2, 6), item("diamond", 4, 1, 2),
                                   item("golden_apple", 5, 1, 2), item("experience_bottle", 6, 3, 8), item("book", 5, ench=(15, 25)),
                                   item("amethyst_shard", 4, 2, 6), item("candle", 4, 2, 4)]),
                     pool((2, 3), [item("emerald", 8, 2, 5), item("gold_ingot", 6, 2, 4), item("diamond", 2),
                                   item("experience_bottle", 5, 2, 5)], extra=True)),
    "premium_vistoso": table(pool((2, 3), [
        named("golden_sword", 8, "baculo", "Báculo del abad Tenebrio", "Abbot Tenebrio's Crosier",
              ench={"minecraft:sharpness": 2, "minecraft:unbreaking": 2}),
        named("golden_helmet", 8, "mitra", "Mitra del relicario", "Mitre of the Reliquary",
              ench={"minecraft:protection": 2, "minecraft:unbreaking": 2}),
        named("book", 8, "evangeliario", "Evangeliario iluminado", "Illuminated Gospel Book",
              ench={"minecraft:unbreaking": 3}),
        named("golden_apple", 6, "fruto", "Fruto del huerto del claustro", "Fruit of the Cloister Garden", lo=1, hi=2),
        named("lantern", 5, "lampara", "Lámpara del eremita", "Hermit's Lamp"),
        named("bell", 3, "esquila", "Esquila del campanario", "Belfry Handbell"),
        named("iron_chestplate", 5, "cota", "Cota del hermano lego", "Lay Brother's Mail",
              ench={"minecraft:protection": 2}),
        named("bow", 5, "arco", "Arco del vigía del risco", "Crag Watcher's Bow", ench={"minecraft:power": 2}),
        item("sentry_armor_trim_smithing_template", 5), item("wayfinder_armor_trim_smithing_template", 4),
        item("host_armor_trim_smithing_template", 4), item("shaper_armor_trim_smithing_template", 4),
        item("music_disc_strad", 4), item("music_disc_mellohi", 4), item("music_disc_far", 4), item("music_disc_wait", 3),
        item("music_disc_ward", 3), item("amethyst_cluster", 3)])),
    "premium_fuerte": table(pool(1, [
        named("diamond_sword", 3, "espada", "Espada del guardián del relicario", "Reliquary Warden's Sword", levels=(20, 30)),
        named("diamond_chestplate", 2, "peto", "Peto del prior", "Prior's Breastplate", levels=(20, 30)),
        named("diamond_pickaxe", 3, "pico", "Pico de los canteros del risco", "Crag Masons' Pickaxe", levels=(20, 30)),
        item("enchanted_golden_apple", 2)])),
}
