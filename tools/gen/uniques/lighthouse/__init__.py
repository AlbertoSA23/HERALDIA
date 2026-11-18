"""Faro con cueva de contrabandistas (heraldia:unicas/faro). Diseño en docs/unicas/faro.md.

Se sitúa junto al mar con el tipo de estructura propio heraldia:faro (Java), que busca la línea de costa y gira la
plantilla para que la boca de la cueva mire al agua.
"""
from .._common.pieces import open_stairwells
from loot import item, empty
from uniques._common import chest_loot
import uniques

SID = "faro"
DISPLAY_NAME = {"es_es": "Faro de los contrabandistas", "en_us": "Smugglers' Lighthouse"}
TROPHY = {"objeto": "iron_sword", "rareza": "uncommon",
          "nombre": ("Alfanje del Capitán Bruma", "Captain Mist's Cutlass"),
          "lore": [("Con él se apagaban los faros ajenos.", "With it, rival lighthouses went dark.")],
          "encantamientos": {"minecraft:sharpness": 1, "minecraft:unbreaking": 1}}   # trofeo del guardián (_comun/botin.trofeo)
STORY = {   # su pliego de la Crónica de los Heraldos (docs/STORY.md, _comun/botin.historia_*)
    "cofre": "despacho",
    "relato": [
        ("En la costa rocosa hay un faro que no siempre guía a los barcos. Su dueño, el capitán Bruma, "
         "enciende la luz que le conviene y apaga la de los demás. Una heraldo no elige a sus "
         "anfitriones.",
         "On the rocky shore stands a lighthouse that does not always guide ships. Its master, Captain "
         "Mist, lights the lamp that suits him and puts out everyone else's. A herald does not choose her"
         " hosts."),
        ("Bruma guardó el pliego en su despacho, entre cartas de navegación robadas. No juró por honor "
         "sino por oro: le pagué para que no lo vendiera nunca. Los contrabandistas cumplen lo que se les"
         " paga.",
         "Mist kept the leaf in his office, among stolen sea charts. He swore not by honour but by gold: "
         "I paid him never to sell it. Smugglers keep what they are paid to keep."),
    ],
    "pista": ("la costa rocosa, donde los contrabandistas de un faro encienden la luz que les conviene",
              "the rocky shore, where the smugglers of a lighthouse light whatever lamp suits them"),
}
ADVANCEMENT = {"icono": "minecraft:lantern"}   # logros.py
LANG = {
    "es_es": {
        "heraldia.unicas.faro.guardian": "Capitán Bruma",
        "heraldia.unicas.faro.cartel.bodega1": "El vino",
        "heraldia.unicas.faro.cartel.bodega2": "baja al mar",
        "heraldia.unicas.faro.cartel.despacho1": "Ni proa ni popa:",
        "heraldia.unicas.faro.cartel.despacho2": "manda el centro",
        "heraldia.unicas.faro.objeto.sable": "Sable del capitán Bruma",
        "heraldia.unicas.faro.objeto.catalejo": "Catalejo del farero",
        "heraldia.unicas.faro.objeto.brujula": "Brújula de los contrabandistas",
        "heraldia.unicas.faro.objeto.libro": "Cuaderno de bitácora",
    },
    "en_us": {
        "heraldia.unicas.faro.guardian": "Captain Brume",
        "heraldia.unicas.faro.cartel.bodega1": "The wine",
        "heraldia.unicas.faro.cartel.bodega2": "goes down to sea",
        "heraldia.unicas.faro.cartel.despacho1": "No bow, no stern:",
        "heraldia.unicas.faro.cartel.despacho2": "the middle rules",
        "heraldia.unicas.faro.objeto.sable": "Captain Brume's Cutlass",
        "heraldia.unicas.faro.objeto.catalejo": "Keeper's Spyglass",
        "heraldia.unicas.faro.objeto.brujula": "Smugglers' Compass",
        "heraldia.unicas.faro.objeto.libro": "Logbook",
    },
}

PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": f"minecraft:{a}", "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{b}"}
    for a, b, p in (("stone_bricks", "cracked_stone_bricks", 0.12), ("stone_bricks", "mossy_stone_bricks", 0.10),
                    ("cobblestone", "mossy_cobblestone", 0.25), ("white_terracotta", "light_gray_terracotta", 0.22),
                    ("red_terracotta", "brown_terracotta", 0.20), ("spruce_planks", "stripped_spruce_wood", 0.15),
                    ("glass_pane", "air", 0.10))]}]}

STRUCTURE = dict(spacing=uniques.DEFAULT_SPACING, separation=uniques.DEFAULT_SEPARATION, json={
    "type": "heraldia:faro",
    "biomes": ["minecraft:stony_shore", "minecraft:beach"],
    "step": "surface_structures", "spawn_overrides": {}, "terrain_adaptation": "none",
    "start_pool": "heraldia:unicas/faro/inicio",
    "sea_row": 8,
})


def named(name, w, key, ench=None, rand_ench=False):
    """Objeto con nombre traducible; ench = niveles (mín, máx) de encantamiento al azar."""
    return chest_loot.named(name, w, key, LANG["es_es"][key], levels=ench, mods=(chest_loot.random_ench(),) if rand_ench else ())


def chest(base, extra, rolls=(3, 6), extra_rolls=(1, 3)):
    """Grupo base (siempre) y grupo extra solo_sin_lootr (con Lootr, cada jugador abre el base)."""
    return chest_loot.cofre((rolls, base), (extra_rolls, extra))


FOOD = [item("bread", 10, 1, 3), item("cooked_cod", 8, 1, 3), item("dried_kelp", 8, 2, 6), item("apple", 6, 1, 3),
        item("sweet_berries", 5, 2, 5)]
LOOT = {
    "casa": chest(FOOD + [item("candle", 6, 1, 3), item("paper", 6, 1, 4), item("string", 5, 1, 3),
                          item("compass", 1), empty(6)],
                  [item("emerald", 2), item("iron_nugget", 5, 2, 6), empty(8)]),
    "faro": chest([item("spyglass", 3), item("compass", 3), item("map", 4), item("paper", 8, 2, 5),
                   item("glow_ink_sac", 5, 1, 3), item("lantern", 4), item("iron_ingot", 5, 1, 3), empty(6)],
                  [item("emerald", 3, 1, 2), item("glowstone_dust", 4, 2, 5), empty(8)], rolls=(2, 5)),
    "bodega": chest([item("bread", 8, 1, 3), item("apple", 8, 1, 3), item("honey_bottle", 6, 1, 2),
                     item("sweet_berries", 6, 2, 6), item("cod", 6, 1, 4), item("glass_bottle", 5, 1, 3)],
                    [item("sugar", 5, 1, 4), empty(6)], rolls=(2, 4)),
    "almacen": chest([item("leather", 8, 1, 4), item("white_wool", 6, 1, 3), item("string", 8, 2, 5),
                      item("gunpowder", 6, 1, 4), item("sugar", 6, 2, 5), item("iron_ingot", 5, 1, 3),
                      item("gold_nugget", 6, 2, 8), item("cocoa_beans", 4, 1, 4), empty(6)],
                     [item("emerald", 4, 1, 2), item("iron_ingot", 4, 1, 2), empty(8)]),
    "senuelo": chest([item("bone", 10, 1, 4), item("rotten_flesh", 10, 1, 4), item("string", 6, 1, 3),
                      item("gunpowder", 6, 1, 3)], [item("gold_nugget", 4, 1, 4), empty(8)], rolls=(2, 4)),
    "dormitorio": chest(FOOD + [item("gold_nugget", 6, 2, 6), item("leather_chestplate", 3, dmg=(0.3, 0.8)),
                                item("leather_boots", 3, dmg=(0.3, 0.8)), item("book", 4), item("clock", 1), empty(5)],
                        [item("emerald", 3), item("gold_nugget", 4, 1, 4), empty(8)]),
    "calabozo": chest([item("bone", 10, 2, 5), item("iron_nugget", 8, 2, 7), item("iron_chain", 5, 1, 3),
                       item("lead", 4), item("name_tag", 1), item("rotten_flesh", 6, 1, 3), empty(5)],
                      [item("iron_ingot", 3, 1, 2), empty(8)], rolls=(2, 5)),
    "despacho": chest([item("map", 6), item("compass", 4), item("gold_ingot", 6, 1, 3), item("emerald", 6, 2, 5),
                       item("book", 4, rand_ench=True), item("experience_bottle", 4, 2, 5), item("paper", 6, 2, 6),
                       item("writable_book", 3), empty(4)],
                      [item("emerald", 4, 1, 3), item("gold_ingot", 4, 1, 2), item("book", 1, rand_ench=True), empty(6)]),
    "oculto": chest([item("gold_ingot", 8, 2, 5), item("emerald", 8, 2, 6), item("diamond", 3),
                     item("iron_sword", 4, ench=(5, 15)), item("iron_chestplate", 3, ench=(5, 15)),
                     item("golden_apple", 2), item("experience_bottle", 4, 2, 6), empty(4)],
                    [item("emerald", 4, 1, 3), item("gold_ingot", 4, 1, 3), empty(6)]),
    "bote": chest([item("gunpowder", 8, 1, 4), item("emerald", 6, 1, 3), item("salmon", 8, 1, 4),
                   item("nautilus_shell", 4, 1, 2), item("heart_of_the_sea", 1), item("rabbit_hide", 4, 1, 3), empty(6)],
                  [item("gold_nugget", 4, 2, 6), empty(8)], rolls=(2, 5)),
    "tesoro": chest([item("gold_nugget", 10, 3, 10), item("gold_ingot", 8, 1, 4), item("raw_gold", 6, 1, 4),
                     item("emerald", 8, 2, 5)], [item("emerald", 4, 1, 3), item("gold_ingot", 4, 1, 2), empty(4)]),
    # premium: grupo vistoso siempre; 10 % algo más fuerte; extra sin Lootr
    "premium": chest_loot.table(
        chest_loot.pool((3, 4), [
            named("iron_sword", 6, "heraldia.unicas.faro.objeto.sable", ench=(10, 20)),
            named("spyglass", 5, "heraldia.unicas.faro.objeto.catalejo"),
            named("compass", 5, "heraldia.unicas.faro.objeto.brujula"),
            named("book", 3, "heraldia.unicas.faro.objeto.libro", rand_ench=True),
            item("coast_armor_trim_smithing_template", 6), item("music_disc_mellohi", 3), item("music_disc_strad", 3),
            item("golden_apple", 4), item("emerald", 5, 4, 9), item("gold_ingot", 5, 3, 7)]),
        chest_loot.pool(1, [empty(90), item("diamond_sword", 3, ench=(20, 30)), item("trident", 2),
                       item("enchanted_golden_apple", 2), item("diamond", 3, 3, 5)]),
        chest_loot.pool((1, 2), [
            item("emerald", 5, 2, 6), item("gold_ingot", 5, 2, 4), item("coast_armor_trim_smithing_template", 2),
            item("experience_bottle", 4, 3, 8)], extra=True)),
}


def build(reg):
    from uniques.lighthouse import blueprint, checks
    t = blueprint.make()
    open_stairwells(t)   # huecos de escalera cortos
    name = reg.add(t, "unica:faro")
    errs = checks.run(t)
    if errs:
        reg.warnings.extend(f"{name}: {e}" for e in errs)
    reg.pool("unicas/faro/inicio", [(name, 1, "rigid", PROCESSORS)])
