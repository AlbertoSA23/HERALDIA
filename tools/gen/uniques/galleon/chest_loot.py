"""Botín del galeón: solo objetos vanilla; más rico cuanto más escondido. El extra de cada cofre va en
un grupo "solo_sin_lootr" (con Lootr cada jugador abre el suyo y recibe solo lo modesto)."""
from loot import item, empty, FOOD
from .texts import LANG
from .._common.chest_loot import pool, potion, cofre  # noqa: F401


def named(name, w, key, ench=None, lo=1, hi=1):
    e = item(name, w, lo, hi, ench=ench)
    f = {"type": "minecraft:set_name", "target": "item_name",
         "name": {"translate": f"heraldia.galeon.{key}", "fallback": LANG["es_es"][f"heraldia.galeon.{key}"]}}
    mods = e.pop("modifier", None)
    mods = [] if mods is None else (mods if isinstance(mods, list) else [mods])
    e["modifier"] = [f] + mods
    return e


def chest(base, extra, rb=(2, 4), re=(1, 2)):
    return cofre((rb, base), (re, extra))


BEACH = [item("cooked_cod", 10, 1, 3), item("dried_kelp", 10, 2, 6), item("string", 8, 1, 4), item("stick", 8, 2, 5),
         item("coal", 6, 1, 3), item("bowl", 4), item("bone", 6, 1, 3), item("fishing_rod", 3, dmg=(0.3, 0.7))]
SUPPLIES = [item("bread", 10, 1, 3), item("wheat", 8, 2, 6), item("sugar", 6, 1, 4), item("potato", 6, 1, 4),
           item("glass_bottle", 6, 1, 3), item("paper", 5, 1, 4), item("cod", 6, 1, 3), item("dried_kelp", 6, 2, 6)]

LOOT = {
    "nafrago": chest(BEACH, [item("iron_nugget", 6, 2, 6), item("torch", 6, 2, 5), item("leather", 4, 1, 2), empty(6)]),
    "arena": {"type": "minecraft:archaeology", "pools": [pool(1, [
        item("angler_pottery_sherd", 3), item("shelter_pottery_sherd", 3), item("snort_pottery_sherd", 2),
        item("gold_nugget", 5, 2, 5), item("emerald", 3), item("iron_nugget", 5, 2, 4), item("coal", 4, 1, 3),
        item("bone", 4)])]},
    "bodega": chest(SUPPLIES, [item("iron_nugget", 6, 2, 6), item("emerald", 2), item("lead", 2), empty(6)], rb=(3, 5)),
    "cocina": chest([item("bread", 8, 1, 3), item("cooked_cod", 8, 1, 3), item("baked_potato", 6, 1, 3),
                     item("sugar", 6, 1, 3), item("honey_bottle", 3), item("bowl", 4, 1, 2), item("cocoa_beans", 3, 1, 3)],
                    [item("cake", 1), item("pumpkin_pie", 3, 1, 2), empty(6)]),
    "polvora": chest([item("gunpowder", 12, 2, 6), item("flint", 6, 1, 3), item("fire_charge", 3, 1, 2), item("tnt", 2)],
                     [item("gunpowder", 6, 2, 5), item("flint_and_steel", 2), empty(6)]),
    "cirujano": chest([item("paper", 6, 1, 3), item("glass_bottle", 8, 1, 3), item("spider_eye", 3), item("sugar", 4),
                       item("glistering_melon_slice", 2), potion("healing", 3), potion("regeneration", 2)],
                      [potion("healing", 3), item("golden_carrot", 2, 1, 2), empty(6)]),
    "oficiales": chest([item("emerald", 8, 1, 3), item("gold_ingot", 6, 1, 3), item("book", 6, 1, 2), item("compass", 3),
                        item("map", 4), item("clock", 2), item("paper", 6, 2, 5)],
                       [item("emerald", 6, 1, 3), item("gold_ingot", 4, 1, 2), item("book", 2, rand_ench=True), empty(6)]),
    "cofa": chest([item("spyglass", 4), item("map", 4), item("feather", 6, 1, 4), item("string", 6, 2, 5), item("arrow", 5, 2, 8)],
                  [item("emerald", 4, 1, 2), item("name_tag", 1), empty(6)], rb=(2, 3), re=1),
    "santabarbara": chest([item("gunpowder", 10, 2, 6), item("iron_ingot", 8, 1, 4), item("arrow", 8, 4, 12),
                           item("emerald", 6, 1, 3), item("tnt", 3, 1, 2)],
                          [named("crossbow", 3, "ballesta", ench=(8, 15)), item("iron_ingot", 6, 1, 3),
                           item("diamond", 1), empty(6)]),
    "capitan": chest([item("emerald", 10, 2, 5), item("gold_ingot", 8, 1, 4), item("spyglass", 3), item("compass", 3),
                      item("book", 4, ench=(5, 12)), item("name_tag", 2), item("writable_book", 3)],
                     [item("gold_ingot", 6, 2, 4), item("emerald", 6, 2, 4), item("golden_apple", 1), empty(5)], rb=(3, 5)),
    "contrabando": chest([item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 5), item("gold_nugget", 6, 4, 10),
                          item("golden_apple", 2), item("book", 3, ench=(8, 15)), item("diamond", 1)],
                         [item("emerald", 6, 2, 4), item("gold_ingot", 6, 1, 3), item("diamond", 1), empty(4)], rb=(3, 5)),
    "cueva": chest([item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 5), item("arrow", 6, 4, 10), item("bone", 6, 1, 4),
                    item("golden_apple", 2), item("book", 3, ench=(8, 15)), item("diamond", 1)],
                   [item("emerald", 6, 2, 4), item("gold_ingot", 6, 1, 3), item("diamond", 1), empty(4)], rb=(3, 5)),
    "tesorero": chest([item("gold_ingot", 10, 3, 6), item("emerald", 10, 3, 7), item("diamond", 4, 1, 2),
                       item("golden_apple", 4), item("gold_block", 1), named("gold_nugget", 6, "doblon", lo=3, hi=8),
                       item("coast_armor_trim_smithing_template", 2)],
                      [item("emerald", 6, 2, 5), item("gold_ingot", 6, 2, 4), item("diamond", 2), empty(4)], rb=(4, 6)),
    "premium": {"type": "minecraft:chest", "pools": [
        pool((4, 5), [named("iron_sword", 6, "sable", ench=(12, 20)), named("spyglass", 5, "catalejo"),
                      named("compass", 5, "brujula"), named("golden_helmet", 5, "casco", ench=(10, 18)),
                      named("writable_book", 3, "diario"), named("gold_nugget", 6, "doblon", lo=6, hi=16),
                      item("coast_armor_trim_smithing_template", 5), item("tide_armor_trim_smithing_template", 3),
                      item("music_disc_mellohi", 2), item("music_disc_far", 2), item("music_disc_wait", 2),
                      item("book", 4, ench=(15, 22)), item("emerald", 6, 4, 9), item("gold_ingot", 6, 3, 7),
                      item("diamond", 3, 1, 3)]),
        pool(1, [named("trident", 4, "tridente", ench=(15, 22)), item("heart_of_the_sea", 3),
                 item("enchanted_golden_apple", 3), empty(90)]),
        pool((2, 3), [item("emerald", 8, 2, 6), item("gold_ingot", 6, 2, 5), item("golden_apple", 3),
                      item("experience_bottle", 6, 3, 8), item("diamond", 2)], extra=True),
    ]},
}
