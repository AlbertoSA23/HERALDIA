"""Botín de la Isla del corsario (solo vanilla): modesto en el puerto y el fuerte, mejor en el bergantín y en las
cuevas, algo más en las salas ocultas y el cofre premium en la cámara del tesoro (90 % vistoso, 10 % algo más fuerte).
Encantamientos moderados; nada de netherita ni élitros. Cada tabla lleva su grupo extra marcado solo_sin_lootr."""
from .._common.chest_loot import place_chest, table, pool, item, empty, named as _named, lang

K = "heraldia.isla_corsario."
TEXTS = {   # clave: (es_es, en_us)
    "sable": ("Sable de abordaje", "Boarding Cutlass"),
    "catalejo": ("Catalejo del vigía", "Lookout's Spyglass"),
    "carta": ("Carta de corso", "Letter of Marque"),
    "ron": ("Ron de la Sirena", "Mermaid's Rum"),
    "real": ("Real de plata", "Silver Real"),
    "lingote": ("Lingote del galeón de Indias", "Treasure-Fleet Ingot"),
    "tricornio": ("Tricornio del corsario", "Corsair's Tricorne"),
    "brujula": ("Brújula del contramaestre", "Boatswain's Compass"),
    "diario": ("Bitácora del bergantín", "Brigantine's Logbook"),
    "mecha": ("Mecha de cañón", "Cannon Fuse"),
}
LANG = lang(K + "objeto.", TEXTS)


def named(name, key, w, **kw):
    return _named(name, w, K + "objeto." + key, TEXTS[key][0], **kw)


HARBOR = [item("cooked_cod", 8, 1, 3), item("cooked_salmon", 5, 1, 2), item("bread", 6, 1, 3), item("dried_kelp", 6, 2, 6),
          item("string", 5, 1, 4), item("stick", 4, 2, 5), item("coal", 4, 1, 3), item("paper", 3, 1, 3),
          item("lead", 2), item("fishing_rod", 2, dmg=(0.3, 0.8))]
TAVERN = [item("bread", 6, 1, 3), item("cooked_cod", 6, 1, 3), item("glass_bottle", 6, 1, 3), item("sugar", 5, 1, 3),
           item("honey_bottle", 3), item("cocoa_beans", 4, 1, 3), item("apple", 4, 1, 3), item("melon_slice", 3, 2, 5)]
FORT = [item("arrow", 8, 4, 12), item("gunpowder", 6, 1, 4), item("bread", 5, 1, 3), item("iron_nugget", 6, 2, 6),
          item("leather", 4, 1, 3), item("flint", 4, 1, 3), item("torch", 4, 2, 6), item("bone", 3, 1, 3)]
CAVE = [item("gold_nugget", 8, 3, 9), item("iron_ingot", 6, 1, 3), item("emerald", 6, 1, 3), item("gold_ingot", 4, 1, 2),
         item("arrow", 5, 4, 10), item("gunpowder", 5, 2, 5), item("nautilus_shell", 2), item("prismarine_shard", 3, 1, 3)]

LOOT = {
    # el puerto
    "taberna": place_chest(((2, 4), TAVERN + [named("honey_bottle", "ron", 3)]),
                     (1, [item("emerald", 3), item("gold_nugget", 4, 2, 5), empty(8)])),
    "bodega": place_chest(((2, 4), TAVERN + [item("wheat", 4, 2, 5), item("sweet_berries", 3, 2, 5)]),
                    (1, [named("honey_bottle", "ron", 4, lo=1, hi=2), item("emerald", 2), empty(8)])),
    "escondite": place_chest(((3, 5), [item("emerald", 8, 2, 5), item("gold_ingot", 6, 1, 3), named("gold_nugget", "real", 6, lo=2, hi=6),
                                 item("book", 3, rand_ench=True), item("name_tag", 2), item("compass", 2),
                                 item("experience_bottle", 3, 1, 3)]),
                       ((1, 2), [item("diamond", 2), item("golden_apple", 2), named("compass", "brujula", 3), empty(6)])),
    "almacen": place_chest(((2, 4), HARBOR + [item("white_wool", 4, 1, 4), item("barrel", 2), item("iron_chain", 2, 1, 3)]),
                     (1, [item("iron_ingot", 4, 1, 2), item("emerald", 2), empty(8)])),
    "faro": place_chest(((2, 4), HARBOR[:6] + [item("candle", 4, 1, 3), item("spyglass", 2), item("glow_ink_sac", 3, 1, 3)]),
                  (1, [named("spyglass", "catalejo", 2), item("emerald", 2), empty(8)])),
    # el bergantín
    "bergantin": place_chest(((3, 5), HARBOR + [item("gunpowder", 5, 2, 5), item("iron_ingot", 4, 1, 3), item("saddle", 1)]),
                       ((1, 2), [item("emerald", 4, 1, 3), item("gold_ingot", 3, 1, 2), item("heart_of_the_sea", 1),
                                 empty(6)])),
    "camarote": place_chest(((3, 5), [named("writable_book", "diario", 4), item("map", 4), item("compass", 4), item("clock", 2),
                                item("emerald", 6, 1, 3), item("gold_ingot", 5, 1, 3), item("paper", 5, 2, 5),
                                item("book", 3, rand_ench=True)]),
                      ((1, 2), [named("compass", "brujula", 3), item("gold_ingot", 4, 1, 3), item("diamond", 1),
                                empty(6)])),
    # el fuerte
    "polvorin": place_chest(((3, 5), [item("gunpowder", 10, 2, 6), item("flint", 5, 1, 3), item("fire_charge", 4, 1, 3),
                                item("tnt", 2), named("string", "mecha", 4, lo=1, hi=3), item("arrow", 4, 4, 10)]),
                      (1, [item("tnt", 2, 1, 2), item("flint_and_steel", 2), empty(6)])),
    "cuartel": place_chest(((2, 4), FORT + [item("leather_helmet", 2, dmg=(0.2, 0.6)), item("iron_sword", 1, dmg=(0.3, 0.7))]),
                     (1, [item("iron_ingot", 4, 1, 2), item("emerald", 2), empty(8)])),
    "casa": place_chest(((2, 4), [item("cooked_porkchop", 5, 1, 3), item("bread", 5, 1, 3), item("glass_bottle", 4, 1, 3),
                            item("paper", 5, 2, 5), item("map", 3), item("candle", 3, 1, 3), item("gold_nugget", 5, 2, 6)]),
                  (1, [item("emerald", 3, 1, 2), named("honey_bottle", "ron", 3), empty(8)])),
    "corsario": place_chest(((3, 5), [item("emerald", 8, 1, 4), item("gold_ingot", 6, 1, 3), named("gold_nugget", "real", 6, lo=2, hi=6),
                                named("paper", "carta", 3), item("book", 3, rand_ench=True), item("spyglass", 2),
                                item("golden_carrot", 3, 1, 3)]),
                      ((1, 2), [item("diamond", 2), named("spyglass", "catalejo", 3), item("golden_apple", 2), empty(6)])),
    # las cuevas
    "ensenada": place_chest(((3, 5), CAVE[:6] + [item("cod", 4, 1, 3), item("oak_boat", 2), item("lead", 2)]),
                      ((1, 2), [item("diamond", 2), item("emerald", 4, 1, 3), item("heart_of_the_sea", 1), empty(6)])),
    "guardia": place_chest(((3, 5), FORT + [item("iron_ingot", 4, 1, 3), item("shield", 2, dmg=(0.2, 0.5))]),
                     ((1, 2), [item("emerald", 4, 1, 3), item("crossbow", 2, rand_ench=True), empty(6)])),
    "cartas": place_chest(((3, 5), [item("map", 6), item("paper", 6, 2, 6), item("compass", 4), item("emerald", 5, 1, 3),
                              item("gold_ingot", 4, 1, 3), item("book", 3, rand_ench=True), item("ink_sac", 3, 1, 3),
                              named("paper", "carta", 3)]),
                    ((1, 2), [named("compass", "brujula", 3), item("diamond", 2), item("experience_bottle", 3, 1, 3),
                              empty(6)])),
    "armeria": place_chest(((3, 5), [item("iron_ingot", 6, 1, 4), item("arrow", 6, 6, 14), item("iron_sword", 3, rand_ench=True),
                               item("bow", 3, rand_ench=True), item("chainmail_helmet", 2), item("chainmail_chestplate", 2),
                               item("shield", 3), item("gunpowder", 5, 2, 5)]),
                     ((1, 2), [named("iron_sword", "sable", 3, ench={"minecraft:sharpness": 2}), item("diamond", 2),
                               item("emerald", 4, 1, 3), empty(6)])),
    "santabarbara": place_chest(((3, 5), [item("gunpowder", 8, 4, 10), item("tnt", 4, 1, 3), item("fire_charge", 4, 2, 4),
                                    item("gold_ingot", 5, 1, 3), item("emerald", 5, 2, 4), item("diamond", 2),
                                    named("string", "mecha", 3, lo=2, hi=4), item("experience_bottle", 3, 1, 3)]),
                          ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), item("book", 3, rand_ench=True),
                                    empty(6)])),
    "calabozo": place_chest(((3, 5), [item("bone", 8, 2, 5), item("rotten_flesh", 5, 1, 3), item("iron_nugget", 6, 2, 6),
                                item("gold_nugget", 5, 2, 6), item("arrow", 4, 2, 8), item("emerald", 3, 1, 2),
                                item("iron_chain", 3, 1, 3), item("name_tag", 1)]),
                      ((1, 2), [item("emerald", 4, 1, 3), item("gold_ingot", 3, 1, 2), item("diamond", 1), empty(6)])),
    "tesoro": place_chest(((4, 6), [item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 6), named("gold_nugget", "real", 6, lo=4, hi=10),
                              item("diamond", 4, 1, 2), item("golden_apple", 3), item("experience_bottle", 4, 2, 4),
                              item("heart_of_the_sea", 1), item("book", 3, ench=(10, 18))]),
                    ((1, 2), [item("diamond", 3, 1, 2), item("gold_block", 2), named("gold_ingot", "lingote", 3), empty(6)])),
    "premium": table(
        pool((3, 5), [named("iron_sword", "sable", 5, levels=(10, 18)), named("spyglass", "catalejo", 4),
                      named("leather_helmet", "tricornio", 4, levels=(8, 15)), named("compass", "brujula", 3),
                      named("gold_ingot", "lingote", 5, lo=1, hi=3), named("paper", "carta", 2),
                      item("coast_armor_trim_smithing_template", 3), item("sentry_armor_trim_smithing_template", 3),
                      item("music_disc_strad", 3), item("music_disc_blocks", 2), item("music_disc_chirp", 2),
                      item("gold_block", 3), item("emerald", 6, 3, 8), item("book", 4, ench=(10, 20)),
                      item("golden_apple", 3)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                      item("experience_bottle", 5, 2, 6), named("gold_nugget", "real", 4, lo=4, hi=12)], extra=True),
        pool(1, [empty(90), item("trident", 3, ench=(15, 25)),     # 10 % más fuerte
                 item("diamond_sword", 2, ench=(20, 30)), item("enchanted_golden_apple", 2),
                 item("totem_of_undying", 2), item("diamond_chestplate", 1, ench=(20, 30))])),
}
