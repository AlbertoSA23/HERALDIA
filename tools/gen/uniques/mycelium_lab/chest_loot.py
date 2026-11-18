"""Loot of the Mycologist's laboratory (vanilla only): modest in the garden, better in the galleries and in the hidden
rooms, and the premium chest at the bottom (90 % showy, 10 % something stronger). Potions, rare ingredients and books. Each
table has its extra group marked solo_sin_lootr."""
from .._common.chest_loot import place_chest, table, pool, item, empty, named as _named, potion, lang

K = "heraldia.laboratorio_micelio."
TEXTS = {   # clave: (es_es, en_us)
    "cuaderno": ("Cuaderno de cepas", "Strain Notebook"),
    "tonico": ("Tónico del micólogo", "Mycologist's Tonic"),
    "elixir": ("Elixir de micelio", "Mycelium Elixir"),
    "espora": ("Espora dorada", "Golden Spore"),
    "lupa": ("Lupa del micólogo", "Mycologist's Lens"),
    "baston": ("Bastón de cepa", "Strain Cane"),
    "sombrero": ("Sombrero de ala ancha", "Wide-Brimmed Hat"),
    "tijeras": ("Tijeras de podar", "Pruning Shears"),
    "estofado": ("Estofado de la casa", "House Stew"),
    "remedio": ("Remedio contra todo", "Cure for Everything"),
}
LANG = lang(K + "objeto.", TEXTS)


def named(name, key, w, **kw):
    return _named(name, w, K + "objeto." + key, TEXTS[key][0], **kw)


def named_potion(key, w, pid, kind="potion"):
    return named(kind, key, w, mods=[{"type": "minecraft:set_potion", "id": "minecraft:" + pid}])


def splash(pid, w):
    e = item("splash_potion", w)
    e["modifier"] = {"type": "minecraft:set_potion", "id": "minecraft:" + pid}
    return e


GARDEN = [item("red_mushroom", 8, 1, 4), item("brown_mushroom", 8, 1, 4), item("mushroom_stew", 5),
          item("bread", 5, 1, 3), item("bone_meal", 5, 2, 5), item("glass_bottle", 6, 1, 3), item("string", 4, 1, 3),
          item("candle", 3, 1, 2), item("paper", 4, 1, 3), item("bowl", 3, 1, 2)]

LOOT = {
    # garden (surface)
    "ayudantes": place_chest(((2, 4), GARDEN + [item("book", 2), item("brown_wool", 3, 1, 2)]),
                       (1, [item("emerald", 3), item("gold_nugget", 5, 2, 5), named("mushroom_stew", "estofado", 3),
                            empty(8)])),
    "estudio": place_chest(((3, 5), [item("book", 6, 1, 2), item("paper", 8, 2, 5), item("ink_sac", 5, 1, 3),
                               item("feather", 4, 1, 2), item("glass_bottle", 6, 1, 3), item("spider_eye", 4, 1, 2),
                               potion("night_vision", 3), named("writable_book", "cuaderno", 3)]),
                     ((1, 2), [item("book", 4, rand_ench=True), item("emerald", 4, 1, 3), named("spyglass", "lupa", 2),
                               empty(6)])),
    "biblioteca": place_chest(((3, 5), [item("book", 10, 1, 3), item("paper", 10, 2, 6), item("glass_bottle", 6, 1, 3),
                                  item("red_mushroom", 5, 1, 3), item("brown_mushroom", 5, 1, 3),
                                  item("crimson_fungus", 3, 1, 2), item("warped_fungus", 3, 1, 2),
                                  named("writable_book", "cuaderno", 3)]),
                        ((1, 2), [item("book", 6, rand_ench=True), item("experience_bottle", 4, 1, 3),
                                  item("lapis_lazuli", 4, 2, 5), empty(6)])),
    "herbario": place_chest(((2, 4), [item("red_mushroom", 8, 1, 4), item("brown_mushroom", 8, 1, 4), item("fern", 4, 1, 2),
                                item("moss_block", 3, 1, 2), item("glow_lichen", 4, 1, 3), item("glow_berries", 4, 1, 3),
                                item("crimson_fungus", 3), item("warped_fungus", 3), item("paper", 4, 1, 3)]),
                      (1, [item("nether_wart", 3, 1, 3), item("emerald", 3), named("golden_carrot", "espora", 2),
                           empty(8)])),
    "secadero": place_chest(((2, 4), [item("red_mushroom", 10, 2, 6), item("brown_mushroom", 10, 2, 6),
                                item("dried_kelp", 5, 2, 5), item("bone_meal", 6, 2, 6), item("string", 4, 1, 3),
                                item("sugar", 4, 1, 3)]),
                      (1, [item("emerald", 3), item("gold_nugget", 4, 2, 5), item("glowstone_dust", 3, 1, 3),
                           empty(8)])),
    "invernadero": place_chest(((2, 4), [item("nether_wart", 6, 1, 3), item("torchflower_seeds", 5, 1, 3),
                                   item("pitcher_pod", 3), item("sweet_berries", 6, 2, 6), item("cocoa_beans", 5, 1, 4),
                                   item("glow_berries", 5, 1, 4), item("chorus_fruit", 3, 1, 2), item("bone_meal", 6, 2, 6),
                                   item("melon_seeds", 4, 1, 3)]),
                         (1, [item("glistering_melon_slice", 3), item("golden_carrot", 3), item("emerald", 3),
                              empty(8)])),
    "destileria": place_chest(((3, 5), [item("glass_bottle", 10, 2, 5), item("nether_wart", 6, 1, 4), item("sugar", 5, 1, 3),
                                  item("redstone", 5, 1, 4), item("glowstone_dust", 4, 1, 3), item("spider_eye", 4, 1, 2),
                                  item("gunpowder", 4, 1, 3), potion("healing", 3), potion("swiftness", 3),
                                  potion("fire_resistance", 2)]),
                        ((1, 2), [item("blaze_powder", 3, 1, 2), item("magma_cream", 3, 1, 2),
                                  item("fermented_spider_eye", 3), named_potion("tonico", 3, "regeneration"),
                                  empty(6)])),
    "corral": place_chest(((2, 3), [item("wheat", 8, 2, 6), item("bowl", 5, 1, 3), item("leather", 4, 1, 2),
                              item("bucket", 2), item("lead", 2), item("hay_block", 2)]),
                    (1, [item("emerald", 3), item("golden_carrot", 2), item("saddle", 1), empty(8)])),
    # hidden room of the garden (behind the tapestry)
    "alcoba": place_chest(((3, 5), [item("gold_ingot", 8, 1, 3), item("emerald", 8, 1, 4), named("writable_book", "cuaderno", 4),
                              named_potion("elixir", 4, "night_vision"), item("book", 4, rand_ench=True),
                              potion("regeneration", 3), item("amethyst_shard", 4, 1, 3)]),
                    ((1, 2), [item("diamond", 3), item("golden_apple", 3), item("experience_bottle", 4, 2, 5),
                              named("stick", "baston", 2, ench={"minecraft:knockback": 1}), empty(6)])),
    # galleries, upper level
    "criadero": place_chest(((2, 4), [item("red_mushroom", 8, 2, 5), item("brown_mushroom", 8, 2, 5),
                                item("mycelium", 3, 1, 2), item("glow_lichen", 5, 1, 3), item("bone_meal", 6, 2, 6),
                                item("glass_bottle", 5, 1, 3), item("iron_nugget", 5, 2, 6), item("torch", 4, 1, 4)]),
                      (1, [item("iron_ingot", 5, 1, 2), item("emerald", 3), item("nether_wart", 3, 1, 3), empty(8)])),
    "laboratorio": place_chest(((3, 5), [item("glass_bottle", 8, 1, 3), item("spider_eye", 6, 1, 3), item("sugar", 5, 1, 3),
                                   item("redstone", 5, 1, 4), item("glowstone_dust", 4, 1, 3), item("gunpowder", 4, 1, 3),
                                   item("rabbit_foot", 2), item("phantom_membrane", 2), potion("leaping", 3),
                                   potion("slow_falling", 2), potion("water_breathing", 2)]),
                         ((1, 2), [named_potion("tonico", 3, "regeneration"), item("blaze_powder", 3, 1, 2),
                                   item("ghast_tear", 1), item("fermented_spider_eye", 3), item("book", 3, rand_ench=True),
                                   empty(6)])),
    "galeria": place_chest(((2, 4), [item("string", 8, 1, 4), item("spider_eye", 5, 1, 2), item("bone", 5, 1, 3),
                               item("red_mushroom", 5, 1, 3), item("iron_nugget", 6, 2, 6), item("coal", 6, 1, 4),
                               item("glow_berries", 4, 1, 3), item("glass_bottle", 4, 1, 2)]),
                     (1, [item("iron_ingot", 5, 1, 2), item("emerald", 3), item("golden_apple", 1), empty(8)])),
    # hidden room of the upper level (behind the laboratory panel)
    "cepario": place_chest(((3, 5), [item("book", 8, rand_ench=True), named("writable_book", "cuaderno", 3),
                               named("golden_carrot", "espora", 4, lo=1, hi=2), item("ghast_tear", 2),
                               item("rabbit_foot", 3), item("lapis_lazuli", 6, 2, 6), item("experience_bottle", 4, 1, 3)]),
                     ((1, 2), [item("diamond", 3, 1, 2), item("music_disc_mall", 2), item("golden_apple", 2),
                               item("name_tag", 2), empty(5)])),
    # nivel bajo
    "capullos": place_chest(((2, 4), [item("string", 12, 2, 6), item("cobweb", 4, 1, 3), item("spider_eye", 6, 1, 3),
                                item("fermented_spider_eye", 3), item("bone", 4, 1, 3), item("gold_nugget", 6, 2, 6)]),
                      ((1, 2), [item("gold_ingot", 5, 1, 3), item("iron_ingot", 5, 1, 3), item("experience_bottle", 3, 1, 3),
                                splash("poison", 2), empty(8)])),
    "experimentos": place_chest(((3, 5), [item("rotten_flesh", 8, 1, 4), item("glass_bottle", 6, 1, 3),
                                    item("fermented_spider_eye", 4, 1, 2), item("redstone", 5, 2, 6),
                                    splash("weakness", 3), potion("strength", 2), item("golden_carrot", 3),
                                    item("experience_bottle", 4, 1, 3)]),
                          ((1, 2), [item("diamond", 2), item("golden_apple", 3), named_potion("remedio", 2, "healing"),
                                    empty(6)])),
    "reactivos": place_chest(((4, 6), [item("nether_wart", 8, 2, 5), item("blaze_powder", 6, 1, 3), item("glowstone_dust", 6, 2, 6),
                                 item("magma_cream", 5, 1, 3), item("ghast_tear", 3), item("rabbit_foot", 3),
                                 item("phantom_membrane", 3, 1, 2), item("glistering_melon_slice", 4, 1, 3),
                                 item("dragon_breath", 1)]),
                       ((1, 2), [item("diamond", 3, 1, 2), item("golden_apple", 3), item("emerald_block", 1), empty(6)])),
    "cepa": place_chest(((3, 5), [item("red_mushroom_block", 4, 1, 3), item("shroomlight", 4, 1, 2), item("glowstone_dust", 5, 1, 4),
                            item("lapis_lazuli", 6, 2, 6), item("experience_bottle", 4, 2, 4),
                            named("shears", "tijeras", 2, levels=(5, 12)), potion("turtle_master", 2)]),
                  ((1, 2), [item("diamond", 3, 1, 2), item("emerald", 5, 2, 4), item("golden_apple", 2), empty(6)])),
    # treasure chamber
    "premium": table(
        pool((3, 5), [named("golden_carrot", "espora", 5, lo=1, hi=3), named("leather_helmet", "sombrero", 4, levels=(8, 15)),
                      named("spyglass", "lupa", 3), named_potion("remedio", 4, "regeneration"),
                      named_potion("elixir", 3, "night_vision"),
                      item("host_armor_trim_smithing_template", 3), item("shaper_armor_trim_smithing_template", 3),
                      item("flow_armor_trim_smithing_template", 2), item("music_disc_mall", 3),
                      item("music_disc_strad", 3), item("music_disc_far", 2), item("gold_ingot", 6, 2, 6),
                      item("emerald", 6, 3, 8), item("book", 4, ench=(10, 20)), item("golden_apple", 3)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                      item("experience_bottle", 5, 2, 6), item("ghast_tear", 3, 1, 2)], extra=True),
        pool(1, [empty(90), item("diamond_pickaxe", 3, ench=(20, 30)), item("diamond_chestplate", 3, ench=(20, 30)),   # 10 % stronger
                 item("enchanted_golden_apple", 2), item("totem_of_undying", 2)])),
}
