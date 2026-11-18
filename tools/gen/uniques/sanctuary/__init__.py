"""Druid sanctuary: a birch forest clearing with a circle of menhirs around an enormous sacred birch
(hollow trunk with stairs up to a platform in the crown), druids' cabins, herb garden with
beehives, pond and an observatory of aligned stones; under the tree, roots and dug-out galleries (design in
docs/unicas/sanctuary.md).

Two rigid pieces: the clearing (y = 0 is the ground) and the roots, joined by a vertical jigsaw, which fill their whole box
(rock where there are no rooms) so that terrain adjustment does not open a crater or cavities next to their walls. The
own audit (audit.py) is a condition for generating.
"""
from .._common.pieces import open_stairwells
from .._common.chest_loot import lang
from .chest_loot import LOOT, LANG as LANG_OBJECTS
from .construction import Construction, K
from . import audit

STRUCTURE = dict(biomes=["minecraft:birch_forest", "minecraft:old_growth_birch_forest"],
                 start_pool="unicas/santuario/inicio", size=2, max_distance=80, terrain_adaptation="beard_thin",
                 step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
                 spacing=250, separation=190)
DISPLAY_NAME = {"es_es": "Santuario druídico", "en_us": "Druid Sanctuary"}
# Guardian reinforcements in each phase (bosses.py): the creatures of the withered forest.
REINFORCEMENTS = ["witch", "spider"]
TROPHY = {"objeto": "golden_hoe", "rareza": "rare",
          "nombre": ("Hoz de oro de Cadoc", "Cadoc's Golden Sickle"),
          "lore": [("Segaba el muérdago del árbol sagrado.", "It reaped the mistletoe of the sacred tree."),
                   ("Al final segó también sus raíces.", "In the end it reaped its roots as well.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "biblioteca",
    "relato": [
        ("En el bosque de abedules hallé un claro rodeado de menhires y, en medio, un abedul tan ancho como una"
         " torre. Los druidas me dieron pan y miel, y el archidruida Cadoc escuchó mi historia bajo sus ramas.",
         "In the birch forest I found a glade ringed with standing stones and, in its midst, a birch as wide as a"
         " tower. The druids gave me bread and honey, and Archdruid Cadoc heard my tale beneath its boughs."),
        ("Juró por las raíces del árbol guardar mi pliego y lo puso entre las cortezas escritas de su biblioteca, bajo"
         " tierra. Dicen que, cuando el árbol empezó a secarse, Cadoc pactó con poderes oscuros para salvarlo.",
         "He swore by the roots of the tree to keep my leaf and placed it among the inscribed barks of his library,"
         " underground. They say that when the tree began to wither, Cadoc bargained with dark powers to save it."),
    ],
    "pista": ("el bosque de abedules, donde un árbol sagrado alza su copa sobre un círculo de piedras",
              "the birch forest, where a sacred tree spreads its crown over a circle of stones"),
}
ADVANCEMENT = {"icono": "minecraft:birch_sapling"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}

TEXTS = {"guardian": ("Archidruida Cadoc, el Marchito", "Archdruid Cadoc the Withered")}
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
    area, sub, errors, rep = audit.prepare(construction)
    REPORT.update(rep, construction=construction)
    proc = {"processors": [audit.PROCESSOR]}
    open_stairwells(area)
    open_stairwells(sub)
    reg.add(area, "unica:santuario")
    reg.add(sub, "unica:santuario")
    reg.pool("unicas/santuario/inicio", [(area.name, 1, "rigid", proc)])
    reg.pool("unicas/santuario/raices", [(sub.name, 1, "rigid", proc)])
    reg.warnings += [f"santuario: {e}" for e in errors]
