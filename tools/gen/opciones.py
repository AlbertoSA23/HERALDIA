"""Opciones del fichero de configuración del servidor (config/heraldia.json).

Una sola fuente: el generador escribe el esquema en heraldia/opciones.json (dentro del .jar) y los textos de ayuda
en los idiomas; el Java lo lee al arrancar, valida cada valor contra su rango y avisa en el log si no vale.
"""
from themes import THEMES, FAMILIES
import unicas

VERSION = 1   # súbelo (y añade la migración en HeraldiaConfig.migrate) si cambia el formato del fichero

# Rejilla de las aldeas (heraldia:aldeas): 94 x 16 = 1.504 bloques; la separación mínima guarda la proporción 62/94.
VILLAGE_SPACING, VILLAGE_SEPARATION, VILLAGE_SALT = 94, 62, 261112013
VANILLA_EXCLUSION_CHUNKS = 10

# (clave, por defecto, mínimo, máximo, texto es_es, texto en_us); mínimo y máximo None en las opciones sí/no.
_FIXED = [
    ("aldeas.separacion_bloques", 1500, 1000, 10000,
     "Separación media entre aldeas, en bloques",
     "Average distance between villages, in blocks"),
    ("aldeas.maximo", 100, 0, 100,
     "Máximo de aldeas por mundo: solo valen las casillas de la rejilla más cercanas al 0,0",
     "Maximum villages per world: only the grid cells nearest to 0,0 are used"),
    ("aldeas.porcentaje_grandes", 25, 0, 100,
     "Porcentaje de aldeas grandes (el resto son estándar)",
     "Percentage of large villages (the rest are standard)"),
    ("aldeas.distancia_aldeas_vanilla_bloques", VANILLA_EXCLUSION_CHUNKS * 16, 0, 256,
     "Distancia mínima a las aldeas vanilla, en bloques (0 la desactiva)",
     "Minimum distance to vanilla villages, in blocks (0 disables it)"),
    ("golems.limpieza", True, None, None,
     "Limita los gólems de hierro naturales de las aldeas cargadas",
     "Limits natural iron golems in loaded villages"),
    ("golems.limite_estandar", 8, 1, 64,
     "Con tantos gólems naturales o más, una aldea estándar retira uno cada 30 s",
     "With this many natural golems or more, a standard village removes one every 30 s"),
    ("golems.limite_grande", 9, 1, 64,
     "Con tantos gólems naturales o más, una aldea grande retira uno cada 30 s",
     "With this many natural golems or more, a large village removes one every 30 s"),
]
# Opciones repetidas: (patrón, clave de texto, es_es, en_us); %s es el nombre de la familia, el estilo o la estructura.
_GROUPS = {
    "aldeas.familias.<familia>": ("familia", "Activa la familia de aldeas %s (sus 3 estilos)", "Enables the %s village family (its 3 styles)"),
    "aldeas.estilos.<estilo>": ("estilo", "Activa el estilo de aldea %s", "Enables the %s village style"),
    "unicas.<id>.activada": ("unica.activada", "Activa la estructura única %s", "Enables the %s unique structure"),
    "unicas.<id>.separacion_bloques": ("unica.separacion", "Separación media entre estructuras %s, en bloques",
                                       "Average distance between %s structures, in blocks"),
}
UNIQUE_RANGE = (1000, 10000)


def _key(k):
    return "heraldia.config." + k


def _option(key, default, lo, hi, lang, args=(), pattern=None):
    o = {"clave": key, "defecto": default, "ayuda": lang, "args": list(args)}
    if lo is not None:
        o.update(min=lo, max=hi)
    if pattern:
        o["patron"] = pattern
    return o


def unique_placements():
    """{id: (spacing, separation)} de las estructuras únicas configurables (las que no traen colocación propia)."""
    return {sid: (m.STRUCTURE.get("spacing", unicas.DEFAULT_SPACING), m.STRUCTURE.get("separation", unicas.DEFAULT_SEPARATION))
            for sid, m in unicas.modules() if "placement" not in m.STRUCTURE}


def schema():
    opts = [_option(k, d, lo, hi, _key(k)) for k, d, lo, hi, _, _ in _FIXED]
    g = {p: _key(v[0]) for p, v in _GROUPS.items()}
    for fam in FAMILIES:
        opts.append(_option(f"aldeas.familias.{fam}", True, None, None, g["aldeas.familias.<familia>"], [fam], "aldeas.familias.<familia>"))
    for th in THEMES:
        opts.append(_option(f"aldeas.estilos.{th['id']}", True, None, None, g["aldeas.estilos.<estilo>"], [th["id"]], "aldeas.estilos.<estilo>"))
    unique = unique_placements()
    for sid, (spacing, _) in unique.items():
        opts.append(_option(f"unicas.{sid}.activada", True, None, None, g["unicas.<id>.activada"], [sid], "unicas.<id>.activada"))
        default = min(max(spacing * 16, UNIQUE_RANGE[0]), UNIQUE_RANGE[1])
        opts.append(_option(f"unicas.{sid}.separacion_bloques", default, *UNIQUE_RANGE, g["unicas.<id>.separacion_bloques"], [sid],
                            "unicas.<id>.separacion_bloques"))
    return {
        "version": VERSION,
        "opciones": opts,
        "aldeas": {"spacing": VILLAGE_SPACING, "separation": VILLAGE_SEPARATION,
                   "estilos": {th["id"]: th["family"] for th in THEMES}},
        "unicas": {sid: {"spacing": sp, "separation": se} for sid, (sp, se) in unique.items()},
    }


def lang():
    """Textos de ayuda de cada opción: {"es_es": {...}, "en_us": {...}}."""
    out = {"es_es": {}, "en_us": {}}
    for k, _, _, _, es, en in _FIXED:
        out["es_es"][_key(k)], out["en_us"][_key(k)] = es, en
    for key, es, en in _GROUPS.values():
        out["es_es"][_key(key)], out["en_us"][_key(key)] = es, en
    out["es_es"]["heraldia.config.rango"] = "por defecto %s, de %s a %s"
    out["en_us"]["heraldia.config.rango"] = "default %s, from %s to %s"
    out["es_es"]["heraldia.config.si_no"] = "por defecto %s; true o false"
    out["en_us"]["heraldia.config.si_no"] = "default %s; true or false"
    return out
