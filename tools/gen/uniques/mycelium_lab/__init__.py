"""Laboratorio del micólogo: un antiguo jardín botánico de los campos de champiñones construido entre y dentro de tres
champiñones gigantes (la casa del micólogo en el sombrero rojo grande, el dormitorio de los ayudantes en el pequeño y
la biblioteca de esporas en el tallo del pardo, con el secadero en su sombrero), unidos por pasarelas; invernadero de
cristal con cultivos raros, destilería de pociones y el corral de los champiñocas. Bajo el micelio, galerías húmedas y
luminosas con los criaderos, el laboratorio y el cepario secreto, y abajo los experimentos fallidos, la sala de los
reactivos y la cámara de la cepa madre (diseño en docs/unicas/laboratorio_micelio.md).

Dos piezas rígidas: el jardín (y = 0 es el suelo) y las galerías, unidas por un jigsaw vertical, que rellenan toda su
caja (roca donde no hay salas) para que el ajuste del terreno no abra un cráter ni cavidades junto a sus muros. La
auditoría propia (auditoria.py) es condición para generar.
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
                 candidata_en_bioma=True)   # bioma raro: la candidata de cada casilla se busca en él (GridPlacement)
DISPLAY_NAME = {"es_es": "Laboratorio del micólogo", "en_us": "Mycologist's Laboratory"}
# Refuerzos del guardián en cada fase (jefes.py): sus experimentos fallidos.
REINFORCEMENTS = ["bogged", "witch"]
TROPHY = {"objeto": "shears", "rareza": "rare",
          "nombre": ("Tijeras de Maese Ambrosio", "Master Ambrose's Shears"),
          "lore": [("Podaban las cepas de su jardín.", "They pruned the strains of his garden."),
                   ("Las esporas no se dejaron podar.", "The spores would not be pruned.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
STORY = {   # su pliego de la Crónica de los Heraldos (docs/STORY.md, _comun/botin.historia_*)
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
ADVANCEMENT = {"icono": "minecraft:red_mushroom"}   # logros.py
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
    for k, v in _lang(construction).items():        # writer.py lee LANG después de build()
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
