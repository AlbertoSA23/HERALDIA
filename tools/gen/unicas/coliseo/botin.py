"""Botín del Coliseo: menores modestos, más ricos cuanto más escondidos; premium 90 % vistoso y 10 % algo más fuerte.
Solo vanilla. Cada tabla tiene un grupo extra marcado solo_sin_lootr (con Lootr cada jugador abre el suyo)."""
from loot import item, empty


def pool(rolls, entries, extra=False):
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


def named(name, key, fallback, w=1, ench=None, dmg=None):
    """Objeto con nombre propio (traducible) y encantamientos fijos moderados."""
    mods = [{"type": "minecraft:set_name", "target": "item_name", "name": {"translate": key, "fallback": fallback}}]
    if ench:
        mods.append({"type": "minecraft:set_enchantments", "enchantments": {f"minecraft:{k}": v for k, v in ench.items()}})
    if dmg:
        mods.append({"type": "minecraft:set_damage", "damage": {"type": "minecraft:uniform", "min": dmg[0], "max": dmg[1]}})
    return {"type": "minecraft:item", "name": "minecraft:" + name, "weight": w, "modifier": mods}


FOOD = [item("bread", 10, 1, 3), item("apple", 8, 1, 3), item("baked_potato", 6, 1, 3), item("melon_slice", 5, 2, 5),
        item("honey_bottle", 2), item("cooked_mutton", 4, 1, 2)]
SUNDRY = [item("string", 6, 1, 4), item("stick", 6, 2, 5), item("leather", 4, 1, 3), item("bone", 5, 1, 4),
          item("torch", 5, 2, 5), item("glass_bottle", 3, 1, 2), item("paper", 3, 1, 3), item("iron_nugget", 4, 2, 6)]

LANG_ITEMS = {
    "gladius": ("Gladius del Campeón", "Champion's Gladius"),
    "yelmo": ("Yelmo de la Victoria", "Helm of Victory"),
    "escudo": ("Escudo del Coliseo", "Colosseum Shield"),
    "corona": ("Corona de Laurel", "Laurel Crown"),
    "rudis": ("Rudis de la Libertad", "Rudis of Freedom"),
    "emperador": ("Espada del Emperador", "Emperor's Sword"),
}


def key(k):
    return f"item.heraldia.coliseo.{k}"


def nm(k):
    return LANG_ITEMS[k][0]


LOOT = {
    "taberna": table(pool((2, 4), FOOD + SUNDRY + [empty(8)]),
                     pool(1, [item("emerald", 1), item("gold_nugget", 3, 1, 4), item("bucket", 2), empty(12)], extra=True)),
    "velario": table(pool((2, 4), [item("string", 10, 2, 6), item("white_wool", 6, 1, 4), item("lead", 4), item("stick", 6, 2, 6),
                                   item("ladder", 4, 2, 4), item("bread", 4, 1, 2)]),
                     pool(1, [item("name_tag", 1), item("lead", 3), item("spyglass", 1), empty(10)], extra=True)),
    "barracones": table(pool((2, 4), FOOD + [item("leather", 4, 1, 3), item("iron_nugget", 4, 2, 6), item("arrow", 4, 2, 6),
                                             item("wooden_sword", 2, dmg=(0.3, 0.7)), item("stone_sword", 2, dmg=(0.3, 0.7)),
                                             item("leather_chestplate", 1, dmg=(0.3, 0.7))]),
                        pool(1, [item("iron_ingot", 2), item("emerald", 1), empty(10)], extra=True)),
    "fieras": table(pool((2, 4), [item("bone", 10, 1, 4), item("rotten_flesh", 8, 1, 4), item("leather", 6, 1, 3),
                                  item("lead", 4), item("hay_block", 3, 1, 2), item("string", 4, 1, 3)]),
                    pool(1, [item("saddle", 2), item("name_tag", 1), empty(8)], extra=True)),
    "palco_menor": table(pool((2, 3), FOOD + [item("gold_nugget", 6, 2, 6), item("book", 3), item("paper", 3, 1, 3)]),
                         pool(1, [item("emerald", 3, 1, 2), item("gold_ingot", 2), item("clock", 1), empty(6)], extra=True)),
    "palco": table(pool((2, 4), [item("golden_carrot", 6, 1, 3), item("glistering_melon_slice", 3, 1, 2), item("gold_nugget", 6, 3, 8),
                                 item("emerald", 5, 1, 3), item("gold_ingot", 3, 1, 2), item("book", 2), item("honey_bottle", 3)]),
                   pool(1, [item("emerald", 3, 1, 3), item("golden_apple", 1), item("clock", 1), empty(5)], extra=True)),
    "armeria": table(pool((3, 5), [item("arrow", 8, 4, 10), item("iron_ingot", 5, 1, 3), item("iron_nugget", 5, 3, 8),
                                   item("shield", 3), item("bow", 2, dmg=(0.4, 0.8)), item("iron_sword", 2, dmg=(0.4, 0.8)),
                                   item("chainmail_helmet", 2, dmg=(0.4, 0.8)), item("chainmail_chestplate", 1, dmg=(0.4, 0.8)),
                                   item("iron_helmet", 1, dmg=(0.4, 0.8)), item("leather", 3, 1, 3)]),
                     pool(1, [item("iron_ingot", 3, 1, 3), item("chainmail_leggings", 1, dmg=(0.4, 0.8)), item("crossbow", 1), empty(5)], extra=True)),
    "cripta": table(pool((2, 4), [item("gold_ingot", 6, 1, 4), item("emerald", 6, 2, 5), item("gold_nugget", 4, 4, 10),
                                  item("experience_bottle", 4, 1, 4), item("book", 3, rand_ench=True), item("golden_apple", 2),
                                  item("candle", 3, 1, 3)]),
                    pool(1, [item("emerald", 4, 2, 4), item("golden_apple", 1), item("music_disc_13", 1), empty(4)], extra=True)),
    "lanista": table(pool((3, 5), [item("emerald", 8, 2, 6), item("gold_ingot", 6, 2, 5), item("iron_ingot", 5, 2, 5),
                                   item("diamond", 1), item("name_tag", 3), item("saddle", 3), item("iron_horse_armor", 2),
                                   item("golden_horse_armor", 2), item("book", 3, rand_ench=True), item("writable_book", 2),
                                   item("experience_bottle", 3, 2, 5)]),
                     pool(1, [item("emerald", 4, 2, 5), item("diamond", 1), item("golden_apple", 2), empty(4)], extra=True)),
    "premium": table(
        # trofeo con nombre propio, siempre uno
        pool(1, [named("iron_sword", key("gladius"), nm("gladius"), 4, ench={"sharpness": 3, "unbreaking": 2}),
                 named("golden_helmet", key("yelmo"), nm("yelmo"), 3, ench={"protection": 2, "unbreaking": 3}),
                 named("shield", key("escudo"), nm("escudo"), 3, ench={"unbreaking": 2}),
                 named("golden_helmet", key("corona"), nm("corona"), 2, ench={"respiration": 1}),
                 named("wooden_sword", key("rudis"), nm("rudis"), 2, ench={"knockback": 1, "unbreaking": 3})]),
        # adornos de armadura y discos
        pool(2, [item("sentry_armor_trim_smithing_template", 3), item("wayfinder_armor_trim_smithing_template", 3),
                 item("shaper_armor_trim_smithing_template", 3), item("host_armor_trim_smithing_template", 2),
                 item("raiser_armor_trim_smithing_template", 2), item("music_disc_mall", 2), item("music_disc_far", 2),
                 item("music_disc_strad", 2), item("music_disc_chirp", 2)]),
        pool((2, 4), [item("gold_ingot", 8, 2, 6), item("emerald", 8, 3, 8), item("diamond", 3, 1, 2),
                      item("golden_apple", 3), item("experience_bottle", 5, 3, 8), item("gold_block", 1)]),
        # 10 %: algo más fuerte sin romper la progresión
        pool(1, [empty(18), named("diamond_sword", key("emperador"), nm("emperador"), 1, ench={"sharpness": 3, "looting": 2, "unbreaking": 2}),
                 item("enchanted_golden_apple", 1)]),
        pool(1, [item("emerald", 5, 2, 5), item("gold_ingot", 4, 1, 3), item("diamond", 1)], extra=True)),
}
