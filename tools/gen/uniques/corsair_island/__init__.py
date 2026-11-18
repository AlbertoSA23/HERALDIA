"""Corsair's island: an islet in open sea (temperate and warm oceans, far from the coast and outside the
Atlantis area) with Roque Salitre's fort on the northern hill (wall, bastion with cannons, corsair's house,
barracks), the southern harbor (pier with a moored brigantine, the tavern of La Sirena Ahorcada with its hideout, the
warehouses and the gallows) and the lighthouse on the west point. Under the hill, the sea caves: the hidden cove (entered
by boat through the cliff), the guardroom, the map room with the compass-rose puzzle, the armory with
the secret powder magazine, the dungeons and, below sea level, the treasure chamber with the corsair (design in
docs/unicas/corsair_island.md).

A single template that brings its own rock, sand and palm trees, placed by the custom type heraldia:isla (Java), which
looks for open sea with the floor at a medium depth; the bottom row is extended down to the floor
(HastaElSueloProcessor), so the islet never ends up hanging. Its own audit is a condition for generating.
"""
import functools
from .._common.chest_loot import lang
from .chest_loot import LOOT, LANG as LANG_OBJECTS  # noqa: F401  (LOOT: module contract)
from .construction import Construction, K, SID, BASE
from . import audit

DISPLAY_NAME = {"es_es": "Isla del corsario", "en_us": "Corsair's Isle"}
# Guardian reinforcements in each phase (bosses.py): its crew.
REINFORCEMENTS = [{"mob": "skeleton", "equipo": {"mainhand": "iron_sword"}}, "skeleton", "drowned"]
TROPHY = {"objeto": "bow", "rareza": "rare",
          "nombre": ("Arco de Roque Salitre", "Roque Salitre's Bow"),
          "lore": [("Disparó la última andanada de la isla.", "It loosed the isle's last broadside."),
                   ("Nunca arrió la bandera negra.", "It never struck the black flag.")],
          "encantamientos": {"minecraft:power": 2, "minecraft:unbreaking": 2}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "cartas",
    "relato": [
        ("Un bergantín de bandera negra me recogió del agua y me llevó a su isla, un cerro con un fuerte en mitad del"
         " mar. Su dueño, el corsario Roque Salitre, quería mis cartas para no perder nunca el rumbo.",
         "A black-flagged brigantine pulled me from the water and took me to its isle, a hill with a fort in the"
         " middle of the sea. Its master, the corsair Roque Salitre, wanted my charts so he would never lose his way."),
        ("Le dejé copiarlas a cambio de guardar mi pliego entre sus cartas, en la sala del mapa, bajo el fuerte."
         " Juró no hacerse a la mar mientras lo tuviera. Sigue en su isla, contando su oro.",
         "I let him copy them in exchange for keeping my leaf among his charts, in the map room beneath the fort."
         " He swore never to put to sea while he held it. He is still on his isle, counting his gold."),
    ],
    "pista": ("un mar templado, donde una isla esconde un fuerte de corsarios y una ensenada en su acantilado",
              "a temperate sea, where an isle hides a corsairs' fort and a cove in its cliff"),
}
ADVANCEMENT = {"icono": "minecraft:spyglass"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}
# Temperate and warm oceans, not the deep ones (Atlantis looks for the deep ones) nor the cold or frozen ones. There is no
# conventional tag that narrow: #c:is_shallow_ocean includes the cold and frozen ones (biomes.py).
BIOME_MAP = ["minecraft:ocean", "minecraft:lukewarm_ocean", "minecraft:warm_ocean"]
RADIUS, MARGIN = 54, 24                   # footprint of the islet and the brigantine (blocks) and ring of sea around it
DEPTH = (-34, -7)                        # floor depth allowed in the footprint relative to sea level (blocks)
TO_THE_BOTTOM = ["stone", "andesite", "tuff", "sand", "gravel", "sandstone", "spruce_log"]

TEXTS = {"guardian": ("Roque Salitre, el corsario", "Roque Salitre, the Corsair")}
LANG = {k: dict(v) for k, v in LANG_OBJECTS.items()}
REPORT = {}


@functools.lru_cache(maxsize=1)
def dataset():
    """(template, errors, texts, report): the whole build, audited and normalized."""
    construction = Construction().build()
    t, errors, rep = audit.prepare(construction)
    out = lang(K, TEXTS)
    for key, lines in construction.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    return t, errors, out, dict(rep, obra=construction)


PROCESSORS = {"processors": [audit.PROCESSOR,
                               {"processor_type": "heraldia:acueducto_hasta_el_suelo",
                                "bloques": ["minecraft:" + b for b in TO_THE_BOTTOM], "profundidad_maxima": 24}]}


def _structure():
    return {"type": "heraldia:isla", "biomes": BIOME_MAP, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "none", "start_pool": f"heraldia:unicas/{SID}/inicio", "fila_mar": -BASE,
            "radio": RADIUS, "margen": MARGIN, "fondo_min": DEPTH[0], "fondo_max": DEPTH[1]}


class _Lazy(dict):
    """STRUCTURE with the JSON computed when read."""
    def get(self, k, default=None):
        if k == "json":
            return _structure()
        return super().get(k, default)

    def __getitem__(self, k):
        return self.get(k) if k == "json" else super().__getitem__(k)


# heraldia:rejilla grid with the candidate sought in its oceans (the point of the cell furthest inside them)
STRUCTURE = _Lazy(start_pool=f"unicas/{SID}/inicio", size=1, max_distance=1, terrain_adaptation="none",
                  step="surface_structures", spacing=250, separation=190, candidata_en_bioma=True, candidata_y=62)


def build(reg):
    t, errors, texts, rep = dataset()
    for k, v in texts.items():           # writer.py reads LANG after build()
        LANG[k].update(v)
    REPORT.update(rep)
    reg.add(t, f"unica:{SID}")
    reg.pool(f"unicas/{SID}/inicio", [(t.name, 1, "rigid", PROCESSORS)])
    reg.warnings += [f"{SID}: {e}" for e in errors]
