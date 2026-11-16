"""Mina perdida de Hondavena: la primera única subterránea. Una colonia minera de la Corona excavada en una gran caverna
bajo las cuevas exuberantes o de espeleotemas, con su pozo maestro hasta la superficie (el castillete es lo único que se
ve desde fuera), la estación del pozo, el almacén, la fundición, las casas de los mineros en la roca, la herrería, la
carpintería, un lago subterráneo con embarcadero, la sima con su puente colgante, el cargadero de las agujas (puzle de
la vagoneta), el frente viejo, el sector derrumbado e inundado y, tras la compuerta de la báscula, el filón madre con
Tizón, el último capataz (diseño en docs/unicas/mina_perdida.md).

Cuatro plantillas que coloca el tipo propio heraldia:mina (Java): la colonia a una altura fija (PISO), los tramos del
pozo (8 y 1 bloques) hasta el terreno y el castillete encima. La colonia no es una caja: solo lleva lo excavado, su
forro y dos capas de roca maciza alrededor; fuera, structure_void. La auditoría propia es condición para generar.
"""
import functools
from .._comun.botin import lang
from .botin import LOOT, LANG as LANG_OBJETOS
from .obra import Obra, K, SID, PISO, YTOP, EJE, CX, CZ
from . import auditoria
from .superficie import Castillete, pozo, ALTO_POZO, CIMIENTO, HUELLA

NOMBRE = {"es_es": "Mina perdida de Hondavena", "en_us": "Lost Mine of Hondavena"}
# Refuerzos del guardián en cada fase (jefes.py): mineros perdidos y arañas de las galerías.
REFUERZOS = [{"mob": "zombie", "equipo": {"mainhand": "iron_pickaxe"}}, "cave_spider", "cave_spider"]
TROFEO = {"objeto": "iron_pickaxe", "rareza": "rare",
          "nombre": ("Pico de Tizón", "Tizon's Pickaxe"),
          "lore": [("Abrió la última galería de Hondavena.", "It opened the last gallery of Hondavena."),
                   ("Nadie le mandó parar.", "No one told it to stop.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
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
LOGRO = {"icono": "minecraft:iron_pickaxe"}   # logros.py
MAPA = {"decoration": "minecraft:red_x"}
BIOMAS = ["minecraft:lush_caves", "minecraft:dripstone_caves"]
POZO_MAX = 80                 # bloques de pozo como mucho (más, y la escalera se hace eterna): si no, otra casilla

TEXTOS = {"guardian": ("Tizón, el último capataz", "Tizon, the Last Foreman")}
LANG = {k: dict(v) for k, v in LANG_OBJETOS.items()}
REPORT = {}


@functools.lru_cache(maxsize=1)
def datos():
    """Plantillas (colonia, pozo, pozo corto, castillete), metadatos para Java y errores de la auditoría."""
    obra = Obra().build()
    cast = Castillete().build()
    errores, rep = auditoria.preparar(obra, cast)
    out = lang(K, TEXTOS)
    for key, lines in obra.signs + cast.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    col = obra.t
    col.name = f"unicas/{SID}/colonia"
    x0, y0, z0, *_ = col.bounds()
    col.normalize()
    sh = lambda p: (p[0] - x0, p[1] - y0, p[2] - z0)
    eje = sh((EJE[0], YTOP + 1, EJE[1]))
    centro = sh((CX, 6, CZ))
    muestras = [sh(p) for p in ((CX - 20, 6, CZ), (CX + 20, 6, CZ), (CX, 6, CZ - 15), (CX, 6, CZ + 15))]
    c = cast.t
    cx0, cy0, cz0, *_ = c.bounds()
    c.normalize()
    eje_c = (-cx0, -cy0, -cz0)                     # eje del pozo y capa de suelo del castillete
    hx0, hx1, hz0, hz1 = HUELLA
    p8, p1 = pozo(ALTO_POZO, "pozo"), pozo(1, "pozo_corto")
    for t in (col, c, p8, p1):
        t.sin_auditoria_generica = True
    meta = dict(colonia_y=PISO + y0, eje_colonia=list(eje), centro=list(centro), muestras=[list(m) for m in muestras],
                eje_pozo=[3, 0, 3], alto_pozo=ALTO_POZO, eje_castillete=list(eje_c), huella=[hx0, hz0, hx1, hz1],
                pozo_max=POZO_MAX)
    rep = dict(rep, obra=obra, castillete=cast, desplazamiento=(x0, y0, z0), desplazamiento_castillete=(cx0, cy0, cz0))
    return (col, c, p8, p1), meta, errores, out, rep


def _structure():
    _, meta, _, _, _ = datos()
    return dict({"type": "heraldia:mina", "biomes": BIOMAS, "step": "underground_structures", "spawn_overrides": {},
                 "terrain_adaptation": "none", "start_pool": f"heraldia:unicas/{SID}/colonia",
                 "pozo": f"heraldia:unicas/{SID}/pozo", "pozo_corto": f"heraldia:unicas/{SID}/pozo_corto",
                 "castillete": f"heraldia:unicas/{SID}/castillete"}, **meta)


class _Lazy(dict):
    """STRUCTURE con el JSON calculado al leerlo (la obra se construye una sola vez)."""
    def get(self, k, default=None):
        if k == "json":
            return _structure()
        return super().get(k, default)

    def __getitem__(self, k):
        return self.get(k) if k == "json" else super().__getitem__(k)


# rejilla heraldia:rejilla con la candidata buscada en las cuevas a la altura del centro de la caverna
STRUCTURE = _Lazy(start_pool=f"unicas/{SID}/colonia", size=1, max_distance=1, terrain_adaptation="none",
                  step="underground_structures", spacing=250, separation=190, candidata_en_bioma=True,
                  candidata_y=PISO + 6)


def build(reg):
    tpls, meta, errores, textos, rep = datos()
    for k, v in textos.items():           # writer.py lee LANG después de build()
        LANG[k].update(v)
    REPORT.update(rep)
    col, c, p8, p1 = tpls
    reg.add(col, f"unica:{SID}")
    reg.add(c, f"unica:{SID}")
    reg.add(p8, f"unica:{SID}")
    reg.add(p1, f"unica:{SID}")
    reg.pool(f"unicas/{SID}/colonia", [(col.name, 1, "rigid", {"processors": [auditoria.PROCESADOR]})])
    reg.pool(f"unicas/{SID}/castillete", [(c.name, 1, "rigid", {"processors": []})])
    reg.pool(f"unicas/{SID}/pozo", [(p8.name, 1, "rigid", {"processors": []})])
    reg.pool(f"unicas/{SID}/pozo_corto", [(p1.name, 1, "rigid", {"processors": []})])
    reg.warnings += [f"{SID}: {e}" for e in errores]
