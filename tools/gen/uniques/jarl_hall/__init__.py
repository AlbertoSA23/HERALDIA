"""Jarl's Hall: a fortified Norse settlement in a taiga clearing, with its kings' barrow under the longhouse
(design in docs/unicas/jarl_hall.md).

Two rigid pieces: the hall (palisade, towers, longhouse and workshops; y = 0 is the ground) and the barrow, joined by a
vertical jigsaw under the longhouse, which fills its whole box (rock where there are no rooms) so that terrain adjustment
does not open a crater or cavities next to its walls. Its own audit (audit.py) is a condition for generating.
"""
from .._common.pieces import open_stairwells
from .._common.chest_loot import lang
from .chest_loot import LOOT, LANG as LANG_OBJECTS
from .construction import Construction, K
from . import audit

STRUCTURE = dict(biomes=["minecraft:taiga", "minecraft:old_growth_pine_taiga", "minecraft:old_growth_spruce_taiga"],
                 start_pool="unicas/salon_jarl/inicio", size=2, max_distance=80, terrain_adaptation="beard_thin",
                 step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
                 spacing=250, separation=190)
DISPLAY_NAME = {"es_es": "Salón del Jarl", "en_us": "Jarl's Hall"}
# Guardian reinforcements in each phase (bosses.py): its retinue of the unburied.
REINFORCEMENTS = [{"mob": "zombie", "equipo": {"mainhand": "stone_axe"}}, {"mob": "zombie", "equipo": {"mainhand": "stone_axe"}},
             "stray"]
TROPHY = {"objeto": "iron_axe", "rareza": "rare",
          "nombre": ("Rompeescudos de Ulfgrim", "Ulfgrim's Shieldbreaker"),
          "lore": [("Hendió cien escudos en su última incursión.", "It split a hundred shields on its last raid."),
                   ("El jarl no lo soltó ni muerto.", "The jarl would not let go of it even in death.")],
          "encantamientos": {"minecraft:sharpness": 2, "minecraft:unbreaking": 2}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "ofrendas",
    "relato": [
        ("En la taiga encontré un salón tras una empalizada de troncos. El jarl Ulfgrim me sentó junto al"
         " hogar y escuchó mi historia toda la noche. Al alba juró por sus antepasados guardar mi pliego.",
         "In the taiga I found a hall behind a palisade of logs. Jarl Ulfgrim sat me by the hearth and "
         "listened to my tale all night. At dawn he swore by his forefathers to keep my leaf."),
        ("Lo bajamos al túmulo de sus reyes, entre las ofrendas. «Ni la muerte me hará soltarlo», dijo. "
         "Cumplió: dicen que aún ronda la cripta con el hacha en la mano, sin tumba que lo acoja.",
         "We carried it down to the barrow of his kings, among the offerings. “Not even death will make "
         "me let go,” he said. He kept his word: they say he still walks the crypt, axe in hand, with no "
         "grave to take him."),
    ],
    "pista": ("la taiga, donde un jarl insepulto guarda su salón tras una empalizada",
              "the taiga, where an unburied jarl keeps his hall behind a palisade"),
}
ADVANCEMENT = {"icono": "minecraft:goat_horn"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}

TEXTS = {"guardian": ("Jarl Ulfgrim, el Insepulto", "Jarl Ulfgrim the Unburied")}
LANG = {k: dict(v) for k, v in LANG_OBJECTS.items()}
REPORT = {}


def _lang(construction):
    out = lang(K, TEXTS)
    for key, lines in construction.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    return out


def build(reg):
    construction = Construction().build()
    for k, v in _lang(construction).items():        # writer.py reads LANG after build()
        LANG[k].update(v)
    area, tomb, errors, rep = audit.prepare(construction)
    REPORT.update(rep, construction=construction)
    proc = {"processors": [audit.PROCESSOR]}
    open_stairwells(area)
    open_stairwells(tomb)
    reg.add(area, "unica:salon_jarl")
    reg.add(tomb, "unica:salon_jarl")
    reg.pool("unicas/salon_jarl/inicio", [(area.name, 1, "rigid", proc)])
    reg.pool("unicas/salon_jarl/tumulo", [(tomb.name, 1, "rigid", proc)])
    reg.warnings += [f"salon_jarl: {e}" for e in errors]
