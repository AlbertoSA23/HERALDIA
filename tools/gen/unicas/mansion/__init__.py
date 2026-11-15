"""Mansión encantada: estructura única del pantano (diseño en docs/unicas/mansion.md).

Dos piezas rígidas: la casa (finca, casa, invernadero, cementerio y panteón; y=0 es el suelo) y el sótano, unido por
un jigsaw vertical bajo el comedor. La auditoría propia (auditoria.py) es condición para generar.
"""
from .._comun.piezas import open_stairwells
from loot import item, empty
from .._comun.botin import cofre, table, pool, potion, named as _named
from .obra import Obra
from . import auditoria

STRUCTURE = dict(biomes="#heraldia:pantano", start_pool="unicas/mansion/inicio", size=2, max_distance=48,
                 terrain_adaptation="beard_thin", step="surface_structures", start_height={"absolute": 0},
                 project_to="WORLD_SURFACE_WG", spacing=250, separation=190)
NOMBRE = {"es_es": "Mansión encantada", "en_us": "Haunted Mansion"}
TROFEO = {"objeto": "clock", "rareza": "rare",
          "nombre": ("Reloj del Conde Malaquías", "Count Malachi's Pocket Watch"),
          "lore": [("Se detuvo a medianoche y nunca volvió a andar.", "It stopped at midnight and never ran again.")]}   # trofeo del guardián (_comun/botin.trofeo)
LOGRO = {"icono": "minecraft:jack_o_lantern"}   # logros.py
MAPA = {"decoration": "minecraft:mansion"}

TEXTOS = {   # clave: (es_es, en_us)
    "heraldia.mansion.conde": ("El Conde Malaquías", "Count Malachi"),
    "heraldia.mansion.reloj": ("Reloj de bolsillo del Conde", "The Count's Pocket Watch"),
    "heraldia.mansion.retrato": ("Retrato de familia", "Family Portrait"),
    "heraldia.mansion.llave": ("Llave del panteón", "Mausoleum Key"),
    "heraldia.mansion.espada": ("Hoja del Conde", "The Count's Blade"),
    "heraldia.mansion.arco": ("Arco de caza de la familia", "Family Hunting Bow"),
    "heraldia.mansion.diario": ("Diario de la Condesa", "The Countess's Diary"),
    "heraldia.mansion.vela": ("Vela del velatorio", "Wake Candle"),
    "heraldia.mansion.brujula": ("Brújula que señala a casa", "Compass Pointing Home"),
    "heraldia.mansion.capa": ("Capa de luto", "Mourning Cloak"),
}

LANG = {"es_es": {k: v[0] for k, v in TEXTOS.items()}, "en_us": {k: v[1] for k, v in TEXTOS.items()}}


def named(name, key, w, ench=None, count=1):
    return _named(name, w, key, TEXTOS[key][0], levels=ench)


SEEDS = [item("wheat_seeds", 8, 2, 6), item("pumpkin_seeds", 5, 1, 3), item("melon_seeds", 4, 1, 3), item("bone_meal", 8, 2, 5),
         item("beetroot_seeds", 5, 1, 4), item("spruce_sapling", 3, 1, 2), item("dark_oak_sapling", 2, 1, 2), item("string", 4, 1, 3)]
COMMON = [item("candle", 8, 1, 3), item("string", 8, 1, 4), item("paper", 8, 1, 4), item("white_wool", 5, 1, 2),
          item("stick", 6, 2, 5), item("bone", 8, 1, 4), item("rotten_flesh", 8, 1, 3), item("glass_bottle", 5, 1, 2),
          item("feather", 4, 1, 3), item("leather", 3, 1, 2), item("coal", 6, 1, 4)]

LOOT = {
    "jardin": cofre(((2, 4), SEEDS + [item("iron_hoe", 2, dmg=(0.3, 0.7)), item("shears", 2, dmg=(0.4, 0.8)), item("flower_pot", 3)]),
                    (1, [item("iron_nugget", 6, 2, 6), item("emerald", 2), empty(8)])),
    "cocina": cofre(((2, 5), [item("bread", 10, 1, 3), item("potato", 8, 1, 4), item("carrot", 6, 1, 3), item("sugar", 6, 1, 4),
                              item("honey_bottle", 4, 1, 2), item("glass_bottle", 6, 1, 3), item("egg", 4, 1, 3),
                              item("cocoa_beans", 3, 1, 3), item("pumpkin_pie", 3), item("rotten_flesh", 6, 1, 3), item("bowl", 4, 1, 2)]),
                    (1, [item("cake", 1), item("golden_carrot", 2, 1, 2), item("emerald", 2), empty(8)])),
    "menor": cofre(((2, 4), COMMON),
                   ((1, 2), [item("iron_ingot", 6, 1, 2), item("gold_nugget", 6, 2, 6), item("emerald", 4, 1, 2),
                             item("lapis_lazuli", 4, 1, 4), item("book", 4), item("name_tag", 1), empty(10)])),
    "biblioteca": cofre(((2, 5), [item("book", 12, 1, 3), item("paper", 10, 2, 6), item("feather", 6, 1, 3), item("ink_sac", 6, 1, 3),
                                  item("writable_book", 3), item("map", 3), item("candle", 5, 1, 2)]),
                        (1, [item("book", 5, rand_ench=True), named("writable_book", "heraldia.mansion.diario", 2),
                             item("experience_bottle", 3, 1, 3), empty(8)])),
    "desvan": cofre(((3, 5), COMMON + [item("cobweb", 4, 1, 3), item("lead", 3), item("saddle", 1), item("clock", 2)]),
                    ((1, 2), [item("spyglass", 3), item("compass", 3), item("gold_ingot", 4, 1, 3), item("iron_ingot", 5, 1, 3),
                              item("music_disc_11", 1), item("music_disc_13", 1), item("name_tag", 2),
                              named("candle", "heraldia.mansion.vela", 2), empty(6)])),
    "oculto": cofre(((2, 4), [item("iron_ingot", 10, 1, 4), item("gold_ingot", 8, 1, 3), item("redstone", 6, 2, 6),
                              item("lapis_lazuli", 6, 2, 6), item("bone", 6, 2, 5), item("emerald", 6, 1, 3),
                              item("experience_bottle", 4, 1, 4)]),
                    ((1, 2), [item("diamond", 3), item("book", 5, rand_ench=True), item("golden_apple", 3),
                              item("iron_sword", 3, ench=(5, 15)), item("iron_chestplate", 2, ench=(5, 15)),
                              named("compass", "heraldia.mansion.brujula", 2), empty(4)])),
    "laboratorio": cofre(((3, 5), [item("glass_bottle", 10, 1, 4), item("spider_eye", 8, 1, 3), item("fermented_spider_eye", 5, 1, 2),
                                   item("glistering_melon_slice", 4, 1, 2), item("redstone", 6, 2, 6), item("glowstone_dust", 5, 1, 4),
                                   item("sugar", 5, 1, 3), item("gunpowder", 5, 1, 3), item("magma_cream", 2), item("phantom_membrane", 2)]),
                         ((1, 2), [potion("healing", 4), potion("night_vision", 4), potion("fire_resistance", 3),
                                   potion("water_breathing", 2), item("experience_bottle", 4, 2, 5), item("blaze_powder", 2), empty(4)])),
    "panteon": cofre(((2, 4), [item("gold_ingot", 10, 1, 4), item("emerald", 8, 1, 4), item("bone", 8, 2, 6), item("candle", 6, 1, 3),
                               item("gold_nugget", 6, 3, 9)]),
                     ((1, 2), [named("tripwire_hook", "heraldia.mansion.llave", 3), named("black_banner", "heraldia.mansion.capa", 2),
                               item("host_armor_trim_smithing_template", 2), item("golden_apple", 3), item("diamond", 2), empty(4)])),
    "premium": table(
        pool((3, 5), [named("clock", "heraldia.mansion.reloj", 6), named("painting", "heraldia.mansion.retrato", 4),
                  named("iron_sword", "heraldia.mansion.espada", 5, ench=(10, 20)),
                  named("bow", "heraldia.mansion.arco", 4, ench=(10, 20)),
                  item("host_armor_trim_smithing_template", 3), item("raiser_armor_trim_smithing_template", 3),
                  item("shaper_armor_trim_smithing_template", 3), item("wayfinder_armor_trim_smithing_template", 3),
                  item("music_disc_11", 3), item("music_disc_13", 3), item("music_disc_mall", 3),
                  item("gold_ingot", 6, 2, 6), item("emerald", 6, 3, 8), item("book", 4, ench=(10, 20)), item("golden_apple", 3)]),
        pool((2, 4), [item("gold_ingot", 6, 1, 4), item("diamond", 3, 1, 2), item("emerald", 6, 2, 5),
                  item("experience_bottle", 5, 2, 6), item("golden_carrot", 4, 1, 3)], extra=True),
        pool(1, [empty(90), item("diamond_chestplate", 3, ench=(20, 30)), item("diamond_sword", 3, ench=(20, 30)),   # 10 % más fuerte
             item("enchanted_golden_apple", 2), item("totem_of_undying", 2)])),
}


def build(reg):
    obra = Obra().build()
    casa, sotano, errores = auditoria.preparar(obra)
    proc = {"processors": [auditoria.DEGRADACION]}
    open_stairwells(casa)
    open_stairwells(sotano)   # huecos de escalera cortos
    reg.add(casa, "unica:mansion")
    reg.add(sotano, "unica:mansion")
    reg.pool("unicas/mansion/inicio", [(casa.name, 1, "rigid", proc)])
    reg.pool("unicas/mansion/sotano", [(sotano.name, 1, "rigid", proc)])
    reg.warnings += [f"mansion: {e}" for e in errores]
