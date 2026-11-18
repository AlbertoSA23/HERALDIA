"""Castle loot (vanilla only). Each chest has an extra group marked solo_sin_lootr."""
from .._common.chest_loot import item, empty, pool, table, named

NAMES = {}      # key -> (es, en)


def it(name, w, lo=1, hi=1, ench=None, dmg=None, nm=None):
    """Item with optional enchantment levels or wear; with nm=(key, es, en), with a translatable name."""
    if nm:
        key, es, en = nm
        NAMES[f"heraldia.castillo.objeto.{key}"] = (es, en)
        return named(name, w, f"heraldia.castillo.objeto.{key}", es, lo=lo, hi=hi, levels=ench)
    return item(name, w, lo, hi, ench=ench, dmg=dmg)


FOOD = [it("bread", 12, 1, 3), it("apple", 8, 1, 3), it("carrot", 6, 1, 4), it("baked_potato", 6, 1, 3),
        it("cooked_mutton", 4, 1, 2)]
LOOT = {
    "menor": table(pool((2, 4), FOOD + [it("stick", 8, 2, 6), it("coal", 8, 1, 4), it("torch", 6, 2, 6),
                                        it("string", 5, 1, 3), it("leather", 4, 1, 2), it("flint", 3, 1, 2), empty(8)]),
                   pool(1, [it("iron_nugget", 6, 2, 6), it("emerald", 2), it("arrow", 4, 2, 6), empty(10)], True)),
    "cocina": table(pool((3, 6), [it("bread", 12, 1, 4), it("cooked_beef", 6, 1, 3), it("cooked_porkchop", 6, 1, 3),
                                  it("cooked_chicken", 6, 1, 3), it("apple", 8, 1, 3), it("carrot", 6, 2, 5),
                                  it("potato", 6, 2, 5), it("beetroot", 5, 2, 5), it("sugar", 4, 1, 4), it("egg", 4, 1, 3),
                                  it("pumpkin_pie", 3, 1, 2), it("honey_bottle", 2), it("bowl", 3, 1, 3)]),
                    pool(1, [it("cake", 1), it("golden_carrot", 2, 1, 3), it("bread", 6, 2, 4), empty(8)], True)),
    "armeria": table(pool((2, 4), [it("arrow", 12, 4, 12), it("iron_ingot", 6, 1, 3), it("iron_nugget", 8, 3, 8),
                                   it("shield", 4, dmg=(0.4, 0.8)), it("iron_sword", 3, dmg=(0.3, 0.7)),
                                   it("bow", 4, dmg=(0.4, 0.8)), it("crossbow", 2, dmg=(0.4, 0.8)),
                                   it("chainmail_helmet", 2), it("chainmail_boots", 2), it("leather_chestplate", 3),
                                   it("iron_helmet", 1), it("flint", 4, 1, 3), it("feather", 4, 1, 4)]),
                     pool(1, [it("iron_ingot", 5, 1, 2), it("spectral_arrow", 2, 2, 6), it("arrow", 6, 2, 8), empty(8)], True)),
    "herreria": table(pool((2, 5), [it("iron_ingot", 10, 1, 4), it("iron_nugget", 8, 3, 9), it("coal", 10, 2, 8),
                                    it("charcoal", 4, 1, 4), it("gold_nugget", 4, 2, 6), it("flint", 3, 1, 3),
                                    it("iron_pickaxe", 2, dmg=(0.5, 0.9)), it("iron_shovel", 2, dmg=(0.5, 0.9)),
                                    it("bucket", 3), it("shears", 2), it("chipped_anvil", 1)]),
                      pool(1, [it("iron_ingot", 6, 1, 3), it("gold_ingot", 2), it("coal", 6, 2, 6), empty(8)], True)),
    "establo": table(pool((2, 4), [it("wheat", 12, 2, 8), it("hay_block", 4, 1, 2), it("lead", 5), it("leather", 6, 1, 3),
                                   it("apple", 6, 1, 3), it("carrot", 6, 1, 4), it("saddle", 2), it("golden_carrot", 1, 1, 2),
                                   it("leather_horse_armor", 3), it("iron_horse_armor", 1)]),
                     pool(1, [it("lead", 3), it("saddle", 1), it("wheat", 6, 2, 6), empty(8)], True)),
    "capilla": table(pool((2, 4), [it("candle", 10, 1, 4), it("paper", 8, 2, 5), it("book", 6, 1, 2), it("glass_bottle", 6, 1, 3),
                                   it("lapis_lazuli", 5, 2, 5), it("glowstone_dust", 3, 1, 3), it("bread", 6, 1, 3)]),
                     pool(1, [it("experience_bottle", 5, 1, 3), it("book", 3, ench=(5, 15)), it("golden_apple", 1), empty(8)], True)),
    "aposentos": table(pool((2, 4), [it("gold_ingot", 6, 1, 3), it("emerald", 6, 1, 3), it("book", 6, 1, 2), it("writable_book", 3),
                                     it("clock", 2), it("compass", 2), it("map", 2), it("candle", 5, 1, 3), it("name_tag", 1),
                                     it("golden_carrot", 3, 1, 3), it("white_wool", 4, 1, 3)]),
                       pool(1, [it("gold_ingot", 4, 1, 2), it("emerald", 4, 1, 3), it("book", 2, ench=(5, 15)),
                                it("spyglass", 1), empty(8)], True)),
    "mazmorra": table(pool((2, 5), [it("bone", 12, 1, 4), it("rotten_flesh", 10, 1, 4), it("string", 6, 1, 3), it("arrow", 6, 2, 6),
                                    it("iron_nugget", 6, 2, 6), it("coal", 6, 1, 4), it("gold_nugget", 5, 2, 6),
                                    it("iron_chain", 3, 1, 3), it("torch", 4, 1, 4), it("iron_ingot", 2, 1, 2)]),
                      pool(1, [it("iron_ingot", 5, 1, 2), it("gold_ingot", 3, 1, 2), it("emerald", 3, 1, 2),
                               it("name_tag", 1), empty(8)], True)),
    "oculto": table(pool((2, 4), [it("gold_ingot", 8, 2, 5), it("emerald", 8, 2, 6), it("iron_ingot", 6, 2, 5),
                                  it("diamond", 2, 1, 2), it("book", 4, ench=(10, 20)), it("golden_apple", 3),
                                  it("experience_bottle", 5, 2, 6), it("ender_pearl", 3, 1, 2), it("amethyst_shard", 3, 2, 5)]),
                    pool((1, 2), [it("diamond", 2), it("emerald", 6, 2, 4), it("golden_apple", 2), it("book", 3, ench=(10, 20)),
                                  empty(6)], True)),
    "premium": table(
        pool((3, 4), [it("iron_sword", 6, ench=(15, 25), nm=("espada", "Espada del Castellano", "Castellan's Sword")),
                      it("iron_helmet", 5, ench=(10, 20), nm=("yelmo", "Yelmo de la Guardia", "Helm of the Watch")),
                      it("shield", 5, nm=("escudo", "Escudo de Heraldia", "Shield of Heraldia")),
                      it("bow", 5, ench=(10, 20), nm=("arco", "Arco del Montero", "Huntsman's Bow")),
                      it("tripwire_hook", 3, nm=("llave", "Llave de la Cámara", "Key of the Vault")),
                      it("sentry_armor_trim_smithing_template", 4), it("wild_armor_trim_smithing_template", 3),
                      it("coast_armor_trim_smithing_template", 3), it("host_armor_trim_smithing_template", 3),
                      it("music_disc_13", 2), it("music_disc_cat", 2), it("music_disc_mall", 2), it("music_disc_strad", 2),
                      it("emerald", 6, 4, 9), it("gold_ingot", 6, 4, 8), it("diamond", 3, 1, 2),
                      it("experience_bottle", 5, 4, 8), it("book", 4, ench=(15, 25)), it("golden_horse_armor", 3)]),
        pool(1, [it("golden_helmet", 20, ench=(10, 20), nm=("corona", "Corona del Señor", "Lord's Crown")),
                 it("clock", 15, nm=("reloj", "Reloj de la Torre", "Tower Clock")),
                 it("spyglass", 15, nm=("catalejo", "Catalejo del Vigía", "Lookout's Spyglass")),
                 it("name_tag", 15), it("music_disc_pigstep", 10), it("golden_apple", 15, 1, 2),
                 it("enchanted_golden_apple", 2),
                 it("diamond_sword", 2, ench=(20, 30), nm=("hoja", "Hoja de Aldric", "Aldric's Blade")),
                 it("diamond_chestplate", 2, ench=(20, 30)), it("diamond", 2, 3, 5), it("book", 2, ench=(30, 30))]),
        pool(2, [it("gold_ingot", 6, 2, 5), it("emerald", 6, 3, 6), it("experience_bottle", 5, 2, 5),
                 it("iron_ingot", 5, 3, 6), it("diamond", 2)], True)),
}
