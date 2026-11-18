"""Hondavena's Lost Mine: the first underground unique structure. A Crown mining colony dug into a great cavern
under the lush or dripstone caves, with its master shaft up to the surface (the headframe is the only thing
visible from outside), the shaft station, the warehouse, the smelter, the miners' houses in the rock, the smithy, the
carpentry, an underground lake with a jetty, the chasm with its suspension bridge, the needle loading dock (minecart
puzzle), the old face, the collapsed and flooded sector and, behind the weighbridge hatch, the mother lode with
Tizón, the last foreman (design in docs/unicas/lost_mine.md).

Four templates placed by the custom type heraldia:mina (Java): the colony at a fixed height (FLOOR_Y), the shaft sections
(8 and 1 blocks) up to the terrain and the headframe on top. The colony is not a box: it carries only what was dug, its
lining and two layers of solid rock around it; outside, structure_void. Its own audit is a condition for generating.
"""
import functools
from .._common.chest_loot import lang
from .chest_loot import LOOT, LANG as LANG_OBJECTS
from .construction import Construction, K, SID, FLOOR_Y, YTOP, AXIS, CX, CZ
from . import audit
from .surface import Headframe, well, SHAFT_HEIGHT, FOUNDATION, FOOTPRINT

DISPLAY_NAME = {"es_es": "Mina perdida de Hondavena", "en_us": "Lost Mine of Hondavena"}
# Guardian reinforcements in each phase (bosses.py): lost miners and spiders of the galleries.
REINFORCEMENTS = [{"mob": "zombie", "equipo": {"mainhand": "iron_pickaxe"}}, "cave_spider", "cave_spider"]
TROPHY = {"objeto": "iron_pickaxe", "rareza": "rare",
          "nombre": ("Pico de Tizón", "Tizon's Pickaxe"),
          "lore": [("Abrió la última galería de Hondavena.", "It opened the last gallery of Hondavena."),
                   ("Nadie le mandó parar.", "No one told it to stop.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "despacho",
    "relato": [
        ("Bajé por el pozo maestro de Hondavena, una colonia minera de la Corona bajo las cuevas. Tizón, el"
         " capataz, me enseñó la fundición, el lago y el filón de oro que iba a hacerlos ricos a todos.",
         "I climbed down the master shaft of Hondavena, a Crown mining colony beneath the caves. Tizon, the"
         " foreman, showed me the foundry, the lake and the gold lode that was to make them all rich."),
        ("Guardó mi pliego en su despacho, tras la estantería. Cuando el frente se hundió y la Corona cerró la"
         " mina, los mineros subieron; él se quedó abajo, junto al filón, y sigue picando.",
         "He kept my leaf in his office, behind the bookcase. When the face caved in and the Crown closed the"
         " mine, the miners went up; he stayed below, by the lode, and is digging still."),
    ],
    "pista": ("las cuevas exuberantes o de espeleotemas, bajo un castillete de mina que asoma en la superficie",
              "the lush or dripstone caves, beneath a mine headframe that rises at the surface"),
}
ADVANCEMENT = {"icono": "minecraft:iron_pickaxe"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}
BIOME_MAP = ["minecraft:lush_caves", "minecraft:dripstone_caves"]
WELL_MAX = 80                 # shaft blocks at most (more, and the ladder becomes endless): otherwise, another cell

TEXTS = {"guardian": ("Tizón, el último capataz", "Tizon, the Last Foreman")}
LANG = {k: dict(v) for k, v in LANG_OBJECTS.items()}
REPORT = {}


@functools.lru_cache(maxsize=1)
def dataset():
    """Templates (colony, shaft, short shaft, headframe), Java metadata and audit errors."""
    construction = Construction().build()
    cast = Headframe().build()
    errors, rep = audit.prepare(construction, cast)
    out = lang(K, TEXTS)
    for key, lines in construction.signs + cast.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    col = construction.t
    col.name = f"unicas/{SID}/colonia"
    x0, y0, z0, *_ = col.bounds()
    col.normalize()
    sh = lambda p: (p[0] - x0, p[1] - y0, p[2] - z0)
    axis = sh((AXIS[0], YTOP + 1, AXIS[1]))
    center = sh((CX, 6, CZ))
    samples = [sh(p) for p in ((CX - 20, 6, CZ), (CX + 20, 6, CZ), (CX, 6, CZ - 15), (CX, 6, CZ + 15))]
    c = cast.t
    cx0, cy0, cz0, *_ = c.bounds()
    c.normalize()
    axis_c = (-cx0, -cy0, -cz0)                     # shaft axis and headframe floor layer
    hx0, hx1, hz0, hz1 = FOOTPRINT
    p8, p1 = well(SHAFT_HEIGHT, "pozo"), well(1, "pozo_corto")
    for t in (col, c, p8, p1):
        t.no_generic_audit = True
    meta = dict(colonia_y=FLOOR_Y + y0, eje_colonia=list(axis), centro=list(center), muestras=[list(m) for m in samples],
                eje_pozo=[3, 0, 3], alto_pozo=SHAFT_HEIGHT, eje_castillete=list(axis_c), huella=[hx0, hz0, hx1, hz1],
                pozo_max=WELL_MAX)
    rep = dict(rep, obra=construction, castillete=cast, desplazamiento=(x0, y0, z0), desplazamiento_castillete=(cx0, cy0, cz0))
    return (col, c, p8, p1), meta, errors, out, rep


def _structure():
    _, meta, _, _, _ = dataset()
    return dict({"type": "heraldia:mina", "biomes": BIOME_MAP, "step": "underground_structures", "spawn_overrides": {},
                 "terrain_adaptation": "none", "start_pool": f"heraldia:unicas/{SID}/colonia",
                 "pozo": f"heraldia:unicas/{SID}/pozo", "pozo_corto": f"heraldia:unicas/{SID}/pozo_corto",
                 "castillete": f"heraldia:unicas/{SID}/castillete"}, **meta)


class _Lazy(dict):
    """STRUCTURE with the JSON computed when read (the build is built only once)."""
    def get(self, k, default=None):
        if k == "json":
            return _structure()
        return super().get(k, default)

    def __getitem__(self, k):
        return self.get(k) if k == "json" else super().__getitem__(k)


# heraldia:rejilla grid with the candidate sought in the caves at the height of the cavern's center
STRUCTURE = _Lazy(start_pool=f"unicas/{SID}/colonia", size=1, max_distance=1, terrain_adaptation="none",
                  step="underground_structures", spacing=250, separation=190, candidata_en_bioma=True,
                  candidata_y=FLOOR_Y + 6)


def build(reg):
    tpls, meta, errors, texts, rep = dataset()
    for k, v in texts.items():           # writer.py reads LANG after build()
        LANG[k].update(v)
    REPORT.update(rep)
    col, c, p8, p1 = tpls
    reg.add(col, f"unica:{SID}")
    reg.add(c, f"unica:{SID}")
    reg.add(p8, f"unica:{SID}")
    reg.add(p1, f"unica:{SID}")
    reg.pool(f"unicas/{SID}/colonia", [(col.name, 1, "rigid", {"processors": [audit.PROCESSOR]})])
    reg.pool(f"unicas/{SID}/castillete", [(c.name, 1, "rigid", {"processors": []})])
    reg.pool(f"unicas/{SID}/pozo", [(p8.name, 1, "rigid", {"processors": []})])
    reg.pool(f"unicas/{SID}/pozo_corto", [(p1.name, 1, "rigid", {"processors": []})])
    reg.warnings += [f"{SID}: {e}" for e in errors]
