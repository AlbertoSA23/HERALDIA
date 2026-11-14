"""Estructuras únicas: cada módulo de este paquete (unicas/<id>.py o unicas/<id>/) define una estructura.

Contrato de cada módulo (el generador lo descubre solo; no hace falta tocar main.py ni writer.py):
  STRUCTURE = dict(
      biomes="#minecraft:is_forest" o "#heraldia:<familia>" (etiqueta de biomas),
      start_pool="unicas/<id>/inicio",
      size=1..20, max_distance=1..116,
      terrain_adaptation="beard_thin" | "beard_box" | "bury" | "encapsulate" | "none",
      step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG" (o None),
      spacing=250, separation=190,   # chunks; por defecto una cada ~3.000-5.000 bloques
  )
  # La rejilla es heraldia:rejilla: activada y separación en bloques se configuran en config/heraldia.json
  # (unicas.<id>.activada, unicas.<id>.separacion_bloques) sin escribir código; spacing/separation dan el valor por defecto.
  # Opcional: STRUCTURE["placement"] = colocación propia (dict JSON); la estructura deja entonces de ser configurable.
  # Opcional: STRUCTURE["json"] = dict completo de la estructura (tipo propio en Java, por ejemplo); sustituye al anterior.
  def build(reg): añade plantillas (nombres "unicas/<id>/...") y pools ("unicas/<id>/...") al registro.
  LOOT = {"premium": tabla, ...}   -> heraldia:unicas/<id>/<nombre>
  LLAVES = {"<llave>": {"tabla": tabla, "cerradura": lock}}   (opcional) llaves de cofres cerrados con `lock`: la tabla
      da exactamente el objeto que pide la cerradura; va a heraldia:llaves/<id>/<llave> y la ofrece /heraldia llave.
  LANG = {"es_es": {...}, "en_us": {...}}   (opcional) claves de traducción propias que se suman al idioma del mod.
  # Opcional (mapas del tesoro, ver mapas.py): nombre para el mapa y su marca en el mapa.
  NOMBRE = {"es_es": "Atlántida", "en_us": "Atlantis"}           # por defecto, el id
  MAPA = {"decoration": "minecraft:monument"}                     # por defecto minecraft:red_x
  LANG = {"es_es": {...}, "en_us": {...}}   # opcional: textos propios (mismas claves en los dos idiomas)
  # Opcional en una plantilla: t.lint_open = {pos: estado o None}, estado con los puzles resueltos para el recorrido a pie.

Botín y Lootr: un grupo (pool) con "solo_sin_lootr": True se omite si el servidor lleva Lootr
(condición heraldia:sin_lootr). Úsalo para el extra por cofre, de modo que con Lootr cada jugador reciba lo modesto.
El generador escribe además la etiqueta heraldia:unicas/<id> y su structure_set, y el mapa del tesoro\n(cofre épico de las aldeas y trato de maestro cartógrafo; mapas.py).
"""
import importlib, pkgutil, zlib

DEFAULT_SPACING, DEFAULT_SEPARATION = 250, 190


def modules():
    """[(id, módulo)] ordenados por id, para una salida determinista."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            found.append((info.name, importlib.import_module(f"{__name__}.{info.name}")))
    return sorted(found)


def salt(sid):
    """Sal estable por estructura para que cada tipo tenga su propia rejilla de colocación."""
    return zlib.crc32(f"heraldia:unicas/{sid}".encode()) & 0x7FFFFFFF
