"""Isla del corsario: un islote en mar abierto (océanos templados y cálidos, lejos de la costa y fuera de la
Atlántida) con el fuerte de Roque Salitre en el cerro del norte (muralla, baluarte con cañones, casa del corsario,
cuartel), el puerto del sur (muelle con un bergantín amarrado, la taberna de La Sirena Ahorcada con su escondite, los
almacenes y la horca) y el faro de la punta oeste. Bajo el cerro, las cuevas marinas: la ensenada oculta (se entra en
barca por el acantilado), el cuerpo de guardia, la sala del mapa con el puzle de la rosa de los vientos, la armería con
la santabárbara secreta, los calabozos y, bajo el nivel del mar, la cámara del tesoro con el corsario (diseño en
docs/unicas/isla_corsario.md).

Una sola plantilla que trae su roca, su arena y sus palmeras, colocada por el tipo propio heraldia:isla (Java), que
busca mar abierto con el fondo a una profundidad media; la fila inferior se prolonga hasta el fondo
(HastaElSueloProcessor), así que el islote nunca queda colgando. La auditoría propia es condición para generar.
"""
import functools
from .._comun.botin import lang
from .botin import LOOT, LANG as LANG_OBJETOS  # noqa: F401  (LOOT: contrato del módulo)
from .obra import Obra, K, SID, BASE
from . import auditoria

NOMBRE = {"es_es": "Isla del corsario", "en_us": "Corsair's Isle"}
# Refuerzos del guardián en cada fase (jefes.py): su tripulación.
REFUERZOS = [{"mob": "skeleton", "equipo": {"mainhand": "iron_sword"}}, "skeleton", "drowned"]
TROFEO = {"objeto": "bow", "rareza": "rare",
          "nombre": ("Arco de Roque Salitre", "Roque Salitre's Bow"),
          "lore": [("Disparó la última andanada de la isla.", "It loosed the isle's last broadside."),
                   ("Nunca arrió la bandera negra.", "It never struck the black flag.")],
          "encantamientos": {"minecraft:power": 2, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
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
LOGRO = {"icono": "minecraft:spyglass"}   # logros.py
MAPA = {"decoration": "minecraft:red_x"}
# Océanos templados y cálidos, no los profundos (la Atlántida busca los profundos) ni los fríos o helados. No hay
# etiqueta convencional tan estrecha: #c:is_shallow_ocean incluye los fríos y helados (biomas.py).
BIOMAS = ["minecraft:ocean", "minecraft:lukewarm_ocean", "minecraft:warm_ocean"]
RADIO, MARGEN = 54, 24                   # huella del islote y del bergantín (bloques) y anillo de mar alrededor
FONDO = (-34, -7)                        # fondo admitido en la huella respecto al nivel del mar (bloques)
HASTA_EL_FONDO = ["stone", "andesite", "tuff", "sand", "gravel", "sandstone", "spruce_log"]

TEXTOS = {"guardian": ("Roque Salitre, el corsario", "Roque Salitre, the Corsair")}
LANG = {k: dict(v) for k, v in LANG_OBJETOS.items()}
REPORT = {}


@functools.lru_cache(maxsize=1)
def datos():
    """(plantilla, errores, textos, informe): la obra entera, auditada y normalizada."""
    obra = Obra().build()
    t, errores, rep = auditoria.preparar(obra)
    out = lang(K, TEXTOS)
    for key, lines in obra.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    return t, errores, out, dict(rep, obra=obra)


PROCESADORES = {"processors": [auditoria.PROCESADOR,
                               {"processor_type": "heraldia:acueducto_hasta_el_suelo",
                                "bloques": ["minecraft:" + b for b in HASTA_EL_FONDO], "profundidad_maxima": 24}]}


def _structure():
    return {"type": "heraldia:isla", "biomes": BIOMAS, "step": "surface_structures", "spawn_overrides": {},
            "terrain_adaptation": "none", "start_pool": f"heraldia:unicas/{SID}/inicio", "fila_mar": -BASE,
            "radio": RADIO, "margen": MARGEN, "fondo_min": FONDO[0], "fondo_max": FONDO[1]}


class _Lazy(dict):
    """STRUCTURE con el JSON calculado al leerlo."""
    def get(self, k, default=None):
        if k == "json":
            return _structure()
        return super().get(k, default)

    def __getitem__(self, k):
        return self.get(k) if k == "json" else super().__getitem__(k)


# rejilla heraldia:rejilla con la candidata buscada en sus océanos (el punto de la casilla más metido en ellos)
STRUCTURE = _Lazy(start_pool=f"unicas/{SID}/inicio", size=1, max_distance=1, terrain_adaptation="none",
                  step="surface_structures", spacing=250, separation=190, candidata_en_bioma=True, candidata_y=62)


def build(reg):
    t, errores, textos, rep = datos()
    for k, v in textos.items():           # writer.py lee LANG después de build()
        LANG[k].update(v)
    REPORT.update(rep)
    reg.add(t, f"unica:{SID}")
    reg.pool(f"unicas/{SID}/inicio", [(t.name, 1, "rigid", PROCESADORES)])
    reg.warnings += [f"{SID}: {e}" for e in errores]
