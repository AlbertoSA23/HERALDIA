"""Estructuras únicas: cada módulo de este paquete (unicas/<id>.py o unicas/<id>/) define una estructura.

Contrato de cada módulo (el generador lo descubre solo; no hace falta tocar main.py ni writer.py):
  STRUCTURE = dict(
      biomes=["minecraft:forest", ...] (pasa a la etiqueta heraldia:unicas/<id>, con las #c: de biomas.CONVENCIONALES)
             o "#heraldia:<familia>" (etiqueta de una familia de aldeas); también en STRUCTURE["json"]["biomes"],
      start_pool="unicas/<id>/inicio",
      size=1..20, max_distance=1..116,
      terrain_adaptation="beard_thin" | "beard_box" | "bury" | "encapsulate" | "none",
      step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG" (o None),
      spacing=250, separation=190,   # chunks; por defecto una cada ~3.000-5.000 bloques (separation: ver abajo)
  )
  # La rejilla es heraldia:rejilla: activada y separación en bloques se configuran en config/heraldia.json
  # (unicas.<id>.activada, unicas.<id>.separacion_bloques) sin escribir código; spacing da el valor por defecto. En las
  # configurables el Java no usa separation: la separación interna es la distancia mínima entre únicas y el origen de la
  # rejilla se desplaza por tipo (GridPlacement), para que cada tipo se reparta por toda la casilla.
  # Opcional: STRUCTURE["candidata_en_bioma"] = True para biomas muy raros (campos de champiñones): la candidata de cada
  # casilla no es un chunk al azar, sino el sitio de la ventana de la casilla más metido en sus biomas (GridPlacement).
  # Opcional: STRUCTURE["placement"] = colocación propia (dict JSON); la estructura deja entonces de ser configurable.
  # Opcional: STRUCTURE["json"] = dict completo de la estructura (tipo propio en Java, por ejemplo); sustituye al anterior.
  def build(reg): añade plantillas (nombres "unicas/<id>/...") y pools ("unicas/<id>/...") al registro.
  LOOT = {"premium": tabla, ...}   -> heraldia:unicas/<id>/<nombre>
  LLAVES = {"<llave>": {"tabla": tabla, "cerradura": lock}}   (opcional) llaves de cofres cerrados con `lock`: la tabla
      da exactamente el objeto que pide la cerradura; va a heraldia:llaves/<id>/<llave> y la ofrece /heraldia key.
  LANG = {"es_es": {...}, "en_us": {...}}   (opcional) claves de traducción propias que se suman al idioma del mod.
  # Opcional (mapas del tesoro, ver mapas.py): nombre para el mapa y su marca en el mapa.
  NOMBRE = {"es_es": "Atlántida", "en_us": "Atlantis"}           # por defecto, el id
  MAPA = {"decoration": "minecraft:monument"}                     # por defecto minecraft:red_x
  # Opcional (logros, ver logros.py): descubrir, guardián y tesoro salen solos; esto solo los ajusta.
  LOGRO = {"icono": "minecraft:trident",       # icono de «descubrir»; por defecto minecraft:filled_map
           "tesoro": ["premium"],              # tablas de LOOT cuyo cofre cuenta como tesoro; por defecto ["premium"]
           "tesoro_objeto": {predicado de objeto},   # o conseguir un objeto (cofre de contenido fijo, sin tabla)
           "extra": [{"id", "icono", "titulo": (es, en), "descripcion": (es, en), "criterios": {...},
                      "requisitos": [[...]], "padre": "descubrir", "marco": "task", "xp": 30}]}   # logros propios
  # El guardián final se crea con _comun/piezas.guardian (etiqueta heraldia_guardian): sin él la compilación falla,
  # y también si hay más de uno (cada guardián suelta un trofeo).
  TROFEO = {"objeto": "iron_axe",                       # OBLIGATORIO: trofeo que suelta el guardián (_comun/botin.trofeo)
            "nombre": (es, en), "lore": [(es, en)],      # una o dos líneas de lore
            "rareza": "rare",                            # common | uncommon | rare | epic (color del nombre)
            "encantamientos": {"minecraft:efficiency": 2},   # opcional, niveles 1-3
            "componentes": {"minecraft:trim": {...}}}    # opcional: adorno, blasón... (no nombre, lore, rareza ni custom_data)
  # El trofeo (heraldia:trofeos/<id>, custom_data {heraldia_trofeo: "<id>"}) solo cae si mata al guardián un jugador:
  # pack.tag_guardians le pone la DeathLootTable heraldia:guardianes/<id>/<mob> (su botín de siempre + el trofeo).
  # Sin TROFEO (o sin nombre, lore..., o con netherita/élitros) la compilación falla. El logro unicas/trofeos sale solo.
  REFUERZOS = ["husk", {"mob": "husk", "equipo": {"mainhand": "iron_sword"}}]   # opcional (jefes.py): 2-3 mobs que el
  # guardián llama en cada fase (al bajar del 66 % y del 33 %); sin él, los de la familia del tipo de su guardián.
  HISTORIA = {"cofre": "biblioteca",                   # OBLIGATORIO: su pliego de la Crónica de los Heraldos (docs/STORY.md)
              # cofre: tabla de LOOT de un cofre menor o de una sala oculta que ya esté en sus plantillas (mejor uno solo)
              "relato": [(es, en), (es, en)],              # 1-2 páginas (máx. botin.MAX_PAGINA caracteres): su parte
              "pista": (es, en),                           # cómo la señala el pliego anterior: bioma y rasgo, sin nombre
              "final": True}                               # solo la Atlántida: cierra la cadena
  # La cadena se calcula sola (botin.historia_cadena: por id y la final al cabo, que señala la primera): el pliego de
  # cada única (heraldia:historia/<id>, custom_data {heraldia_historia: "<id>"}) añade una página con la pista de la
  # siguiente y, a veces, su mapa del tesoro; la tabla de su cofre lo anida. Sin HISTORIA (o con un cofre que no está
  # en sus plantillas, o páginas demasiado largas) la compilación falla. El logro unicas/cronista sale solo.
  LANG = {"es_es": {...}, "en_us": {...}}   # opcional: textos propios (mismas claves en los dos idiomas)
  # Opcional en una plantilla: t.lint_open = {pos: estado o None}, estado con los puzles resueltos para el recorrido a pie.

Botín y Lootr: un grupo (pool) con "solo_sin_lootr": True se omite si el servidor lleva Lootr
(condición heraldia:sin_lootr). Úsalo para el extra por cofre, de modo que con Lootr cada jugador reciba lo modesto.
El generador escribe además la etiqueta heraldia:unicas/<id> y su structure_set, y el mapa del tesoro\n(cofre épico de las aldeas y trato de maestro cartógrafo; mapas.py).
"""
import importlib, pkgutil, zlib

DEFAULT_SPACING, DEFAULT_SEPARATION = 250, 190
# Únicas que ya estaban en la 0.1.0 (rama main, antes de las rejillas desplazadas): con unicas.rejilla_compatible se
# colocan con la rejilla de entonces para que se encuentren las ya generadas en los mundos de esa versión. No se añade
# ninguna: una única nueva nunca se generó con la rejilla antigua. Las demás llevan siempre la rejilla nueva.
REJILLA_ANTIGUA = frozenset({"acueducto", "castillo", "catedral", "ciudadela", "coliseo", "faro", "fortaleza_hielo", "galeon",
                             "mansion", "monasterio", "observatorio", "palacio", "piramide", "torre_mago"})


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
