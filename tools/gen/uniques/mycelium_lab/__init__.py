"""Mycologist's laboratory: a former botanical garden in the mushroom fields built between and inside three
giant mushrooms (the mycologist's house in the large red cap, the assistants' dormitory in the small one and
the spore library in the stem of the brown one, with the drying room in its cap), joined by walkways; a glass
greenhouse with rare crops, a potion distillery and the mooshroom pen. Under the mycelium, damp, luminous
galleries with the nurseries, the laboratory and the secret strain vault, and below them the failed experiments, the reagent
room and the mother strain chamber (design in docs/unicas/mycelium_lab.md).

Two rigid pieces: the garden (y = 0 is the ground) and the galleries, joined by a vertical jigsaw, which fill their whole
box (rock where there are no rooms) so that terrain adjustment does not open a crater or cavities next to their walls. The
own audit (audit.py) is a condition for generating.
"""
from .._common.pieces import open_stairwells
from .._common.chest_loot import lang
from .chest_loot import LOOT, LANG as LANG_OBJECTS
from .construction import Construction, K
from . import audit

STRUCTURE = dict(biomes=["minecraft:mushroom_fields"],
                 start_pool="unicas/laboratorio_micelio/inicio", size=2, max_distance=80,
                 terrain_adaptation="beard_thin", step="surface_structures", start_height={"absolute": 0},
                 project_to="WORLD_SURFACE_WG", spacing=250, separation=190,
                 candidata_en_bioma=True)   # rare biome: each cell's candidate is searched in it (GridPlacement)
DISPLAY_NAME = {"es_es": "Laboratorio del micólogo", "en_us": "Mycologist's Laboratory"}
# Guardian reinforcements in each phase (bosses.py): its failed experiments.
REINFORCEMENTS = ["bogged", "witch"]
TROPHY = {"objeto": "shears", "rareza": "rare",
          "nombre": ("Tijeras de Maese Ambrosio", "Master Ambrose's Shears"),
          "lore": [("Podaban las cepas de su jardín.", "They pruned the strains of his garden."),
                   ("Las esporas no se dejaron podar.", "The spores would not be pruned.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "biblioteca",
    "relato": [
        ("En una isla de champiñones gigantes hallé el jardín de Maese Ambrosio, el micólogo. Vivía en el sombrero"
         " de una seta tan alta como una torre y buscaba en las esporas un remedio para todos los males.",
         "On an island of giant mushrooms I found the garden of Master Ambrose, the mycologist. He lived in the cap"
         " of a mushroom as tall as a tower and sought in the spores a cure for every ill."),
        ("Juró guardar mi pliego entre los frascos de su biblioteca de esporas. Dicen que, al fallarle la última"
         " prueba, la hizo en sí mismo, y que desde entonces las esporas crecen en sus huesos.",
         "He swore to keep my leaf among the jars of his spore library. They say that when his last trial failed,"
         " he tried it on himself, and that since then the spores have grown in his bones."),
    ],
    "pista": ("una isla de champiñones gigantes, donde un sabio cultivaba esporas bajo un sombrero rojo",
              "an island of giant mushrooms, where a sage grew spores beneath a red cap"),
}
ADVANCEMENT = {"icono": "minecraft:red_mushroom"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}

TEXTS = {"guardian": ("Maese Ambrosio, el Esporado", "Master Ambrose the Spore-Ridden")}
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
    reg.add(area, "unica:laboratorio_micelio")
    reg.add(sub, "unica:laboratorio_micelio")
    reg.pool("unicas/laboratorio_micelio/inicio", [(area.name, 1, "rigid", proc)])
    reg.pool("unicas/laboratorio_micelio/galerias", [(sub.name, 1, "rigid", proc)])
    reg.warnings += [f"laboratorio_micelio: {e}" for e in errors]
