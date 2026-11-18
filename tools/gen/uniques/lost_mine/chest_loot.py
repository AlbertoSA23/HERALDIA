"""Botín de la Mina perdida (solo vanilla): modesto en la superficie y en la estación, algo mejor en las casas y los
talleres, minerales y herramientas en las galerías y las salas ocultas, y el cofre premium tras el filón madre (90 %
vistoso, 10 % algo más fuerte). Herramientas con encantamientos moderados; nada de netherita ni élitros. Cada tabla
tiene su grupo extra marcado solo_sin_lootr."""
from .._common.chest_loot import cofre, table, pool, item, empty, named as _named, lang

K = "heraldia.mina_perdida."
TEXTS = {   # clave: (es_es, en_us)
    "pico": ("Pico de entibador", "Timberman's Pickaxe"),
    "pala": ("Pala del pocero", "Well-Digger's Shovel"),
    "casco": ("Casco de minero", "Miner's Helmet"),
    "botas": ("Botas de la galería", "Gallery Boots"),
    "libreta": ("Libreta de jornales", "Wage Ledger"),
    "racion": ("Ración de mina", "Mine Ration"),
    "pepita": ("Pepita de Hondavena", "Hondavena Nugget"),
    "lingote": ("Lingote de la Corona", "Crown Ingot"),
    "brujula": ("Brújula del pocero", "Well-Digger's Compass"),
    "farol": ("Farol de la última guardia", "Lamp of the Last Watch"),
}
LANG = lang(K + "objeto.", TEXTS)


def named(name, key, w, **kw):
    return _named(name, w, K + "objeto." + key, TEXTS[key][0], **kw)


MINE = [item("torch", 8, 2, 8), item("coal", 8, 1, 4), item("bread", 5, 1, 3), item("stick", 5, 2, 6),
        item("rail", 5, 2, 6), item("iron_nugget", 5, 2, 6), item("string", 3, 1, 3), item("flint", 3, 1, 2),
        item("cobblestone", 4, 4, 12), item("oak_planks", 3, 2, 6)]
HOUSE = [item("bread", 6, 1, 3), item("cooked_mutton", 4, 1, 2), item("candle", 4, 1, 2), item("wheat", 3, 1, 4),
        item("leather", 3, 1, 2), item("paper", 3, 1, 3), item("bowl", 3, 1, 2), item("white_wool", 2, 1, 2),
        item("torch", 4, 1, 4), item("coal", 4, 1, 3)]
VEIN = [item("raw_iron", 8, 1, 4), item("raw_copper", 8, 2, 6), item("coal", 8, 2, 6), item("raw_gold", 4, 1, 3),
        item("redstone", 5, 2, 6), item("lapis_lazuli", 4, 2, 5), item("iron_ingot", 4, 1, 3), item("amethyst_shard", 3, 1, 3)]

LOOT = {
    # superficie y estación
    "malacate": cofre(((2, 4), MINE[:7] + [item("lead", 2), item("bucket", 2)]),
                      (1, [item("iron_ingot", 4, 1, 2), item("emerald", 2), empty(8)])),
    "estacion": cofre(((2, 4), MINE + [item("lantern", 3), item("ladder", 4, 2, 6)]),
                      (1, [item("iron_ingot", 4, 1, 2), named("bread", "racion", 3, lo=1, hi=3), item("minecart", 2),
                           empty(8)])),
    "almacen": cofre(((3, 5), [item("bread", 8, 2, 5), item("potato", 6, 2, 6), item("carrot", 5, 2, 5),
                               item("cooked_beef", 4, 1, 3), item("torch", 6, 4, 12), item("rail", 5, 4, 10),
                               item("iron_shovel", 2), item("stone_pickaxe", 3), item("bucket", 2)]),
                     (1, [item("iron_pickaxe", 3, rand_ench=False), named("bread", "racion", 3, lo=2, hi=4),
                          item("emerald", 3), empty(8)])),
    # la colonia
    "vivienda": cofre(((2, 4), HOUSE),
                      (1, [item("emerald", 3), item("gold_nugget", 4, 2, 5), named("gold_nugget", "pepita", 2),
                           empty(8)])),
    "capataz": cofre(((3, 5), HOUSE + [named("writable_book", "libreta", 4), item("clock", 2), item("compass", 2)]),
                     ((1, 2), [item("gold_ingot", 4, 1, 3), item("emerald", 4, 1, 3), item("book", 3, rand_ench=True),
                               empty(6)])),
    "herreria": cofre(((3, 5), [item("iron_ingot", 8, 1, 4), item("iron_nugget", 6, 3, 8), item("coal", 6, 2, 6),
                                item("flint", 4, 1, 3), item("iron_chain", 3, 1, 3), item("iron_shovel", 2),
                                item("iron_pickaxe", 2), item("shears", 2), item("bucket", 2)]),
                      ((1, 2), [named("iron_pickaxe", "pico", 3, ench={"minecraft:efficiency": 2}),
                                item("iron_helmet", 2), item("emerald", 3), empty(6)])),
    "carpinteria": cofre(((3, 5), [item("spruce_log", 8, 2, 6), item("spruce_planks", 8, 4, 12), item("stick", 6, 4, 10),
                                   item("rail", 5, 4, 10), item("ladder", 4, 2, 6), item("iron_axe", 2),
                                   item("string", 3, 1, 3)]),
                         ((1, 2), [item("powered_rail", 3, 2, 4), item("emerald", 3), item("iron_ingot", 3, 1, 2),
                                   empty(6)])),
    "fundicion": cofre(((3, 5), [item("iron_ingot", 8, 2, 5), item("copper_ingot", 8, 2, 6), item("coal", 6, 2, 6),
                                 item("raw_iron", 6, 1, 4), item("raw_copper", 6, 2, 6), item("bucket", 3),
                                 item("blast_furnace", 1)]),
                       ((1, 2), [item("gold_ingot", 4, 1, 3), item("lava_bucket", 2), item("iron_block", 1),
                                 empty(6)])),
    "embarcadero": cofre(((2, 4), [item("cod", 6, 1, 3), item("salmon", 4, 1, 2), item("string", 4, 1, 3),
                                   item("fishing_rod", 3), item("oak_boat", 2), item("lead", 2), item("bread", 4, 1, 3),
                                   item("glow_ink_sac", 3, 1, 2)]),
                         (1, [item("emerald", 3), item("iron_ingot", 3, 1, 2), item("name_tag", 1), empty(8)])),
    # sala oculta tras el tapiz del cobertizo
    "alijo": cofre(((3, 5), [item("gold_ingot", 8, 1, 3), item("emerald", 8, 1, 4), item("raw_gold", 6, 1, 3),
                             item("diamond", 2), item("experience_bottle", 4, 1, 3), named("gold_ingot", "lingote", 3),
                             named("compass", "brujula", 3)]),
                   ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), item("book", 3, rand_ench=True),
                             empty(6)])),
    # el sector derrumbado e inundado, la sima
    "derrumbe": cofre(((3, 5), VEIN[:5] + [item("string", 6, 2, 5), item("spider_eye", 4, 1, 2),
                                           item("iron_pickaxe", 2, rand_ench=True)]),
                      ((1, 2), [item("diamond", 2), item("gold_ingot", 4, 1, 3), item("experience_bottle", 3, 1, 3),
                                empty(6)])),
    "inundada": cofre(((3, 5), VEIN + [item("nautilus_shell", 2), item("prismarine_crystals", 2, 1, 3)]),
                      ((1, 2), [item("diamond", 3, 1, 2), item("gold_ingot", 4, 1, 3),
                                named("leather_boots", "botas", 3, ench={"minecraft:depth_strider": 1}), empty(6)])),
    "sima": cofre(((3, 5), [item("bone", 8, 2, 5), item("arrow", 6, 2, 8), item("rail", 4, 2, 6), item("raw_iron", 5, 1, 3),
                            item("torch", 4, 2, 6), item("iron_ingot", 4, 1, 3)]),
                  ((1, 2), [item("diamond", 2), item("bow", 3, rand_ench=True), named("iron_helmet", "casco", 3,
                            ench={"minecraft:protection": 2}), empty(6)])),
    # galerías del este
    "cargadero": cofre(((3, 5), VEIN + [item("rail", 5, 4, 10), item("powered_rail", 3, 1, 3), item("minecart", 2)]),
                       ((1, 2), [item("diamond", 2), item("detector_rail", 3, 1, 2), item("emerald", 4, 1, 3),
                                 empty(6)])),
    "frente": cofre(((3, 5), VEIN + [item("rotten_flesh", 5, 1, 3), item("iron_shovel", 2, rand_ench=True)]),
                    ((1, 2), [item("diamond", 3, 1, 2), item("gold_ingot", 4, 1, 3),
                              named("iron_shovel", "pala", 3, ench={"minecraft:efficiency": 2, "minecraft:unbreaking": 1}),
                              empty(6)])),
    # sala oculta del capataz (el pliego de la Crónica)
    "despacho": cofre(((3, 5), [named("writable_book", "libreta", 4), item("paper", 6, 2, 6), item("gold_ingot", 6, 1, 3),
                                item("emerald", 6, 2, 5), item("map", 3), item("book", 4, rand_ench=True),
                                item("experience_bottle", 4, 1, 3)]),
                      ((1, 2), [item("diamond", 3, 1, 2), named("compass", "brujula", 3), item("golden_apple", 2),
                                empty(6)])),
    # el filón madre
    "filon": cofre(((4, 6), [item("raw_gold", 8, 2, 6), item("gold_ingot", 8, 2, 5), item("diamond", 4, 1, 2),
                             item("emerald", 6, 2, 5), item("amethyst_shard", 5, 2, 6), item("lapis_lazuli", 5, 4, 10),
                             item("redstone", 5, 4, 10), item("experience_bottle", 4, 2, 4)]),
                   ((1, 2), [item("diamond", 3, 1, 3), item("golden_apple", 3), item("gold_block", 2),
                             named("iron_pickaxe", "pico", 3, ench={"minecraft:efficiency": 3, "minecraft:unbreaking": 2}),
                             empty(6)])),
    "premium": table(
        pool((3, 5), [named("gold_ingot", "lingote", 5, lo=1, hi=3), named("lantern", "farol", 4),
                      named("iron_helmet", "casco", 4, levels=(8, 15)), named("iron_pickaxe", "pico", 4, levels=(10, 18)),
                      named("compass", "brujula", 3), item("wayfinder_armor_trim_smithing_template", 3),
                      item("shaper_armor_trim_smithing_template", 3), item("raiser_armor_trim_smithing_template", 2),
                      item("music_disc_13", 3), item("music_disc_cat", 3), item("music_disc_stal", 2),
                      item("gold_block", 3), item("emerald", 6, 3, 8), item("book", 4, ench=(10, 20)),
                      item("golden_apple", 3)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                      item("experience_bottle", 5, 2, 6), item("raw_gold", 4, 2, 5)], extra=True),
        pool(1, [empty(90), item("diamond_pickaxe", 3, ench=(20, 30)), item("diamond_shovel", 2, ench=(20, 30)),   # 10 % más fuerte
                 item("enchanted_golden_apple", 2), item("totem_of_undying", 2), item("diamond_chestplate", 1, ench=(20, 30))])),
}
