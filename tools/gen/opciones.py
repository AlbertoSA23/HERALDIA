"""Opciones del fichero de configuración del servidor (config/heraldia.json).

Una sola fuente: el generador escribe el esquema en heraldia/opciones.json (dentro del .jar) y los textos de ayuda
en los idiomas; el Java lo lee al arrancar, valida cada valor contra su rango y avisa en el log si no vale.
"""
from themes import THEMES, FAMILIES
import unicas
import medianas

VERSION = 1   # súbelo (y añade la migración en HeraldiaConfig.migrate) si cambia el formato del fichero

# Rejilla de las aldeas (heraldia:aldeas): 94 x 16 = 1.504 bloques; la separación mínima guarda la proporción 62/94.
VILLAGE_SPACING, VILLAGE_SEPARATION, VILLAGE_SALT = 94, 62, 261112013
VANILLA_EXCLUSION_CHUNKS = 10

# (clave, por defecto, mínimo, máximo, texto es_es, texto en_us); mínimo y máximo None en las opciones sí/no. En las de
# lista, «mínimo» es la lista de valores (cadenas) y «máximo» None; el nombre de cada valor va en _VALUE_NAMES.
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
    ("aldeas.vida.tratos_estilo", True, None, None,
     "Tratos propios del estilo: algunos oficios de cada estilo de aldea ofrecen uno o dos tratos con su carácter (al subir de nivel)",
     "Style trades: some professions of each village style offer one or two trades with its character (when they level up)"),
    ("aldeas.vida.tablon", True, None, None,
     "Tablón de encargos en la plaza (atril con el libro de encargos y el alguacil que los paga); solo en aldeas nuevas",
     "Job board on the square (lectern with the book of jobs and the bailiff who pays for them); new villages only"),
    ("aldeas.vida.asedios", False, None, None,
     "Asedios: en las aldeas fortificadas el armero vende una botella ominosa para provocar un asalto de saqueadores (cambia el equilibrio)",
     "Sieges: in fortified villages the weaponsmith sells an ominous bottle to provoke a raid (affects balance)"),
    ("aldeas.caminos.activado", True, None, None,
     "Caminos entre aldeas: senderos (tierra, arenisca, grava o adoquín según el terreno) con farolas, puentes de madera y "
     "carteles con el nombre de la aldea de destino; solo en los chunks nuevos",
     "Roads between villages: trails (dirt, sandstone, gravel or cobblestone depending on the terrain) with lamp posts, wooden "
     "bridges and signs naming the destination village; new chunks only"),
    ("aldeas.caminos.distancia_maxima_bloques", 2000, 500, 4000,
     "Solo se unen con un camino las aldeas a menos de esta distancia, en bloques (cada aldea, con sus vecinas más cercanas)",
     "Only villages closer than this distance, in blocks, are joined by a road (each village, with its nearest neighbours)"),
    ("aldeas.caminos.ancho", 3, 1, 5,
     "Ancho de los caminos entre aldeas, en bloques",
     "Width of the roads between villages, in blocks"),
    ("golems.limpieza", True, None, None,
     "Limita los gólems de hierro naturales de las aldeas cargadas",
     "Limits natural iron golems in loaded villages"),
    ("golems.limite_estandar", 8, 1, 64,
     "Con tantos gólems naturales o más, una aldea estándar retira uno cada 30 s",
     "With this many natural golems or more, a standard village removes one every 30 s"),
    ("golems.limite_grande", 9, 1, 64,
     "Con tantos gólems naturales o más, una aldea grande retira uno cada 30 s",
     "With this many natural golems or more, a large village removes one every 30 s"),
    ("unicas.rejilla_compatible", False, None, None,
     "Rejilla antigua de las únicas: ponlo a true en un mundo creado con una versión anterior de Heraldia (antes de las "
     "rejillas desplazadas) para que /locate, los mapas y los pliegos encuentren las únicas que ya se generaron; las "
     "añadidas después siguen con la rejilla nueva sin salir a menos de la distancia mínima de las antiguas. En un mundo "
     "nuevo, false",
     "Old unique-structure grid: set it to true in a world created with an earlier Heraldia version (before the shifted "
     "grids) so /locate, maps and folios find the unique structures already generated; those added later keep the new "
     "grid without spawning closer than the minimum distance to the old ones. In a new world, false"),
    ("unicas.distancia_minima.activada", True, None, None,
     "Impide que dos estructuras únicas distintas salgan a menos de la distancia mínima",
     "Keeps two different unique structures from spawning closer than the minimum distance"),
    ("unicas.distancia_minima.bloques", 1000, 100, 3000,
     "Distancia mínima entre estructuras únicas distintas (también la Atlántida), en bloques",
     "Minimum distance between different unique structures (Atlantis included), in blocks"),
    ("compatibilidad.zona_estructuras_ajenas_bloques", 224, 0, 512,
     "Estructuras de otros mods (que asoman a la superficie) a menos de esta distancia, en bloques, del inicio de una aldea "
     "o una estructura única de Heraldia no se generan, para que no salgan unas encima de otras (0 lo desactiva)",
     "Structures from other mods (those above ground) closer than this distance, in blocks, to the start of a Heraldia "
     "village or unique structure are not generated, so they do not overlap (0 disables it)"),
    ("medianas.activadas", True, None, None,
     "Estructuras medianas (torres de vigía, posadas de camino, campamentos de bandidos, ermitas...) entre las aldeas y "
     "las únicas",
     "Medium structures (watchtowers, roadside inns, bandit camps, hermitages...) between villages and unique structures"),
    ("medianas.frecuencia_porcentaje", 100, 25, 400,
     "Frecuencia de todas las estructuras medianas, en % de la de por defecto (200 = el doble; 50 = la mitad); se suma "
     "a la separación de cada tipo",
     "Frequency of all medium structures, as a % of the default (200 = twice as many; 50 = half); applied on top of "
     "each type's spacing"),
    ("medianas.distancia_minima.bloques", 192, 64, 1024,
     "Distancia mínima entre dos estructuras medianas distintas, en bloques",
     "Minimum distance between two different medium structures, in blocks"),
    ("medianas.distancia_aldeas_unicas_bloques", 256, 128, 1024,
     "Una estructura mediana no sale a menos de esta distancia, en bloques, del inicio de una aldea o una estructura única "
     "de Heraldia (tampoco dentro de la Atlántida)",
     "A medium structure does not spawn closer than this distance, in blocks, to the start of a Heraldia village or unique "
     "structure (nor inside Atlantis)"),
    ("minas.entradas.activado", True, None, None,
     "Entradas a mina en laderas (bocas, campamentos mineros y complejos con torre de extracción) que bajan a una "
     "galería propia; solo en los chunks nuevos",
     "Mine entrances on hillsides (adits, mining camps and complexes with a headframe) leading down to their own "
     "gallery; new chunks only"),
    ("minas.entradas.separacion_bloques", 768, 256, 4000,
     "Separación media entre dos entradas a mina pequeñas, en bloques; las medianas y las grandes guardan la proporción "
     "(x1,5 y x2,5)",
     "Average distance between two small mine entrances, in blocks; medium and large ones keep the ratio (x1.5 and x2.5)"),
    ("minas.vanilla.multiplicador", 2.0, 1, 5,
     "Multiplica la frecuencia de las minas abandonadas vanilla en los chunks nuevos (1 = como en vanilla; admite "
     "decimales, p. ej. 1.5); no cambia los chunks ya generados ni otras estructuras",
     "Multiplies how often vanilla abandoned mineshafts appear in new chunks (1 = as in vanilla; decimals allowed, e.g. "
     "1.5); does not change chunks already generated or other structures"),
    ("jefes.fases.activado", True, None, None,
     "Fases de los guardianes de las estructuras únicas: al bajar del 66 % y del 33 % de vida se enfurecen (velocidad, "
     "resistencia y fuerza breve, con partículas, sonido y aviso a los jugadores cercanos); también los ya generados",
     "Phases of the unique-structure guardians: below 66 % and 33 % health they become enraged (speed, resistance and a "
     "short strength boost, with particles, sound and a notice to nearby players); also those already generated"),
    ("jefes.refuerzos.activado", True, None, None,
     "Refuerzos de los guardianes: en cada fase (una sola vez) llaman a 2 o 3 mobs propios de su estructura, que no "
     "sueltan su botín; nunca más de 4 vivos a la vez",
     "Guardian reinforcements: at each phase (only once) they call 2 or 3 mobs that suit their structure, which do not "
     "drop the guardian's loot; never more than 4 alive at once"),
    ("jefes.barra.activado", True, None, None,
     "Barra de jefe con el nombre del guardián para los jugadores cercanos mientras dura el combate",
     "Boss bar with the guardian's name for nearby players while the fight lasts"),
    ("guia.entregar_al_entrar", True, None, None,
     "Guía del Heraldo: da a cada jugador el libro que explica el mod y lleva su diario la primera vez que entra tras "
     "instalar o actualizar Heraldia (una vez por versión; /heraldia guia da otra copia cuando quiera)",
     "Herald's Guide: gives each player the book that explains the mod and keeps their diary the first time they join "
     "after Heraldia is installed or updated (once per version; /heraldia guia gives a new copy at any time)"),
    ("botin.reponer.activado", False, None, None,
     "Botín que se repone: los cofres y barriles de las aldeas, estructuras medianas y únicas de Heraldia vuelven a llenarse "
     "con su tabla de botín cuando han pasado los días indicados desde que se saquearon, al abrirlos, si no hay otro jugador "
     "cerca y el cofre está vacío o casi vacío (nunca se borra nada; también en los cofres ya generados). Sin efecto con "
     "Lootr (ya da botín por jugador); no afecta a los trofeos ni al cofre premium de la Atlántida",
     "Restocking loot: chests and barrels of Heraldia villages, medium and unique structures are refilled from their loot "
     "table when the given days have passed since they were looted, on opening, if no other player is nearby and the chest "
     "is empty or almost empty (nothing is ever deleted; also in chests already generated). No effect with Lootr (it "
     "already gives per-player loot); trophies and the Atlantis premium chest are not affected"),
    ("botin.reponer.dias", 7, 1, 60,
     "Días de juego (24.000 ticks del reloj del mundo) que tienen que pasar desde que se saqueó un cofre para que se reponga",
     "In-game days (24,000 ticks of the world clock) that must pass after a chest was looted before it is restocked"),
    ("dificultad.nivel", "normal", ["facil", "normal", "dificil", "heroica"], None,
     "Dificultad de los guardianes y los mobs de las plantillas de Heraldia: fácil (vida y daño x0,75), normal (como "
     "siempre), difícil (vida x1,5, daño x1,25) o heroica (vida x2, daño x1,5); también los ya generados, al cargarse",
     "Difficulty of Heraldia's guardians and template mobs: easy (health and damage x0.75), normal (as always), hard "
     "(health x1.5, damage x1.25) or heroic (health x2, damage x1.5); also those already generated, when they load"),
    ("dificultad.escalar_por_jugadores", False, None, None,
     "Más vida para los guardianes y mobs de Heraldia cuantos más jugadores luchen cerca: +25 % por cada jugador de más a "
     "32 bloques (hasta +100 %), al recibir un golpe",
     "More health for Heraldia's guardians and mobs the more players fight nearby: +25 % per extra player within 32 blocks "
     "(up to +100 %), when hit"),
    ("dificultad.escalar_botin", True, None, None,
     "Con la dificultad fácil, difícil o heroica, los objetos sencillos apilables del botín de los cofres de Heraldia salen "
     "en cantidad x0,75, x1,25 o x1,5 (en normal no cambia nada)",
     "With easy, hard or heroic difficulty, plain stackable items in Heraldia chest loot come in x0.75, x1.25 or x1.5 "
     "amounts (normal changes nothing)"),
    ("arena.activado", True, None, None,
     "Arena de oleadas cerca del spawn: los operadores la colocan con /heraldia arena colocar (o se genera sola en un mundo "
     "nuevo); cualquier jugador empieza una partida tocando su campana. Si se desactiva, no hay partidas ni protección",
     "Wave arena near spawn: operators place it with /heraldia arena colocar (or it is built on its own in a new world); any "
     "player starts a match by ringing its bell. When disabled, there are no matches and no protection"),
    ("arena.generar_en_mundos_nuevos", True, None, None,
     "En un mundo nuevo, la arena se construye sola a 200-300 bloques del spawn, en terreno llano (en un mundo ya existente, "
     "nunca: la coloca un operador)",
     "In a new world, the arena is built on its own 200-300 blocks from spawn, on flat ground (never in an existing world: "
     "an operator places it)"),
    ("arena.oleada.mobs_incremento", 50, 10, 200,
     "Enemigos de más en cada oleada, en % de los de la primera (50: 4, 6, 8, 10...)",
     "Extra enemies in each wave, as a % of the first wave's (50: 4, 6, 8, 10...)"),
    ("arena.oleada.stats_incremento", 10, 1, 100,
     "Vida y daño de más de los enemigos en cada oleada, en % (10: x1, x1,1, x1,2...); nunca más que el incremento de "
     "enemigos (los enemigos crecen más que su fuerza)",
     "Extra health and damage of the enemies in each wave, in % (10: x1, x1.1, x1.2...); never more than the enemy "
     "increase (enemies grow faster than their strength)"),
    ("arena.max_mobs_vivos", 20, 4, 64,
     "Enemigos vivos a la vez en el ruedo como mucho: si una oleada trae más, salen en tandas",
     "Maximum enemies alive at once in the ring: if a wave brings more, they come in batches"),
    ("arena.experiencia_porcentaje", 15, 0, 100,
     "Experiencia que dan los enemigos de la arena, en % de la normal (no sueltan objetos)",
     "Experience given by arena enemies, as a % of the normal amount (they drop no items)"),
    ("unicas.atlantida.cofre_unico_por_jugador", False, None, None,
     "Cofre premium de la Atlántida por jugador: cada jugador saca su propia copia del contenido una vez (si no, el primero que llega se lo lleva)",
     "Per-player Atlantis premium chest: each player takes their own copy of its contents once (otherwise the first to arrive takes it all)"),
]
# Opciones repetidas: (patrón, clave de texto, es_es, en_us); %s es el nombre de la familia, el estilo o la estructura.
_GROUPS = {
    "aldeas.familias.<familia>": ("familia", "Activa la familia de aldeas %s (sus 3 estilos)", "Enables the %s village family (its 3 styles)"),
    "aldeas.estilos.<estilo>": ("estilo", "Activa el estilo de aldea %s", "Enables the %s village style"),
    "unicas.<id>.activada": ("unica.activada", "Activa la estructura única %s", "Enables the %s unique structure"),
    "unicas.<id>.separacion_bloques": ("unica.separacion", "Separación media entre estructuras %s, en bloques",
                                       "Average distance between %s structures, in blocks"),
    "medianas.<id>.activada": ("mediana.activada", "Activa la estructura mediana %s", "Enables the %s medium structure"),
    "medianas.<id>.separacion_bloques": ("mediana.separacion", "Separación media entre estructuras %s del mismo tipo, en "
                                         "bloques (con la frecuencia al 100 %%)",
                                         "Average distance between two %s structures, in blocks (at 100 %% frequency)"),
}
UNIQUE_RANGE = (1000, 10000)
MEDIANA_RANGE = medianas.SEPARACION_RANGO

# Nombre corto de cada opción en la pantalla de configuración del cliente (la ayuda larga va en el tooltip).
_NAMES = {
    "aldeas.separacion_bloques": ("Separación (bloques)", "Spacing (blocks)"),
    "aldeas.maximo": ("Máximo de aldeas", "Maximum villages"),
    "aldeas.porcentaje_grandes": ("Aldeas grandes (%)", "Large villages (%)"),
    "aldeas.distancia_aldeas_vanilla_bloques": ("Distancia a aldeas vanilla (bloques)", "Distance to vanilla villages (blocks)"),
    "aldeas.vida.tratos_estilo": ("Tratos propios del estilo", "Style trades"),
    "aldeas.vida.tablon": ("Tablón de encargos", "Job board"),
    "aldeas.vida.asedios": ("Asedios en aldeas fortificadas", "Sieges in fortified villages"),
    "aldeas.caminos.activado": ("Caminos entre aldeas", "Roads between villages"),
    "aldeas.caminos.distancia_maxima_bloques": ("Distancia máxima entre aldeas unidas (bloques)", "Maximum distance between joined villages (blocks)"),
    "aldeas.caminos.ancho": ("Ancho de los caminos (bloques)", "Road width (blocks)"),
    "golems.limpieza": ("Limpieza de gólems", "Golem cleanup"),
    "golems.limite_estandar": ("Límite en aldea estándar", "Limit in standard village"),
    "golems.limite_grande": ("Límite en aldea grande", "Limit in large village"),
    "unicas.rejilla_compatible": ("Rejilla antigua (mundo de una versión anterior)", "Old grid (world from an earlier version)"),
    "unicas.distancia_minima.activada": ("Distancia mínima activada", "Minimum distance enabled"),
    "unicas.distancia_minima.bloques": ("Distancia mínima (bloques)", "Minimum distance (blocks)"),
    "unicas.atlantida.cofre_unico_por_jugador": ("Cofre premium por jugador", "Per-player premium chest"),
    "arena.activado": ("Arena de oleadas", "Wave arena"),
    "arena.generar_en_mundos_nuevos": ("Generarla en mundos nuevos", "Build it in new worlds"),
    "arena.oleada.mobs_incremento": ("Enemigos de más por oleada (%)", "Extra enemies per wave (%)"),
    "arena.oleada.stats_incremento": ("Vida y daño de más por oleada (%)", "Extra health and damage per wave (%)"),
    "arena.max_mobs_vivos": ("Enemigos vivos a la vez", "Enemies alive at once"),
    "arena.experiencia_porcentaje": ("Experiencia de los enemigos (%)", "Enemy experience (%)"),
    "jefes.fases.activado": ("Fases de los guardianes", "Guardian phases"),
    "jefes.refuerzos.activado": ("Refuerzos de los guardianes", "Guardian reinforcements"),
    "jefes.barra.activado": ("Barra de jefe", "Boss bar"),
    "guia.entregar_al_entrar": ("Dar la guía al entrar", "Give the guide on joining"),
    "botin.reponer.activado": ("Botín que se repone", "Restocking loot"),
    "botin.reponer.dias": ("Días hasta reponerse", "Days until restocked"),
    "dificultad.nivel": ("Nivel de dificultad", "Difficulty level"),
    "dificultad.escalar_por_jugadores": ("Más vida con más jugadores", "More health with more players"),
    "dificultad.escalar_botin": ("Botín según la dificultad", "Loot by difficulty"),
    "medianas.activadas": ("Estructuras medianas", "Medium structures"),
    "medianas.frecuencia_porcentaje": ("Frecuencia (%)", "Frequency (%)"),
    "medianas.distancia_minima.bloques": ("Distancia entre medianas (bloques)", "Distance between medium ones (blocks)"),
    "medianas.distancia_aldeas_unicas_bloques": ("Distancia a aldeas y únicas (bloques)",
                                                 "Distance to villages and unique ones (blocks)"),
    "minas.entradas.activado": ("Entradas a mina", "Mine entrances"),
    "minas.entradas.separacion_bloques": ("Separación de las entradas (bloques)", "Entrance spacing (blocks)"),
    "minas.vanilla.multiplicador": ("Minas vanilla (multiplicador)", "Vanilla mineshafts (multiplier)"),
    "compatibilidad.zona_estructuras_ajenas_bloques": ("Distancia de estructuras de otros mods (bloques)",
                                                       "Distance of other mods' structures (blocks)"),
}
# Nombre de cada valor de las opciones de lista: {clave: {valor: (es_es, en_us)}}.
_VALUE_NAMES = {
    "dificultad.nivel": {"facil": ("Fácil", "Easy"), "normal": ("Normal", "Normal"), "dificil": ("Difícil", "Hard"),
                         "heroica": ("Heroica", "Heroic")},
}
# Grupos: nombre corto (%s = nombre de la familia, el estilo o la estructura) y clave del nombre del argumento
# (None: el id tal cual, como en el README).
_GROUP_NAMES = {
    "aldeas.familias.<familia>": ("%s", "%s", "heraldia.familia.%s"),
    "aldeas.estilos.<estilo>": ("%s", "%s", None),
    "unicas.<id>.activada": ("%s", "%s", "heraldia.unicas.%s.nombre"),
    "unicas.<id>.separacion_bloques": ("%s: separación (bloques)", "%s: spacing (blocks)", "heraldia.unicas.%s.nombre"),
    "medianas.<id>.activada": ("%s", "%s", "heraldia.medianas.%s.nombre"),
    "medianas.<id>.separacion_bloques": ("%s: separación (bloques)", "%s: spacing (blocks)", "heraldia.medianas.%s.nombre"),
}
# Secciones de la pantalla, en orden de aparición: (id, es_es, en_us).
SECTIONS = [
    ("aldeas", "Aldeas", "Villages"),
    ("familias", "Familias de aldeas", "Village families"),
    ("estilos", "Estilos de aldea", "Village styles"),
    ("vida", "Vida de las aldeas", "Village life"),
    ("caminos", "Caminos entre aldeas", "Roads between villages"),
    ("golems", "Gólems", "Golems"),
    ("unicas", "Estructuras únicas", "Unique structures"),
    ("distancia_minima", "Distancia mínima entre únicas", "Minimum distance between unique structures"),
    ("atlantida", "Atlántida", "Atlantis"),
    ("jefes", "Guardianes (jefes)", "Guardians (bosses)"),
    ("medianas", "Estructuras medianas", "Medium structures"),
    ("minas", "Minas", "Mines"),
    ("compatibilidad", "Compatibilidad con otros mods", "Compatibility with other mods"),
    ("botin", "Botín", "Loot"),
    ("dificultad", "Dificultad", "Difficulty"),
    ("guia", "Guía del Heraldo", "Herald's Guide"),
    ("arena", "Arena de oleadas", "Wave arena"),
]
# Prefijo de la clave → sección; gana el primero que encaje, así que una opción nueva cae sola en su sección
# (si no encaja en ninguna, la generación falla).
_SECTION_PREFIXES = [
    ("aldeas.familias.", "familias"), ("aldeas.estilos.", "estilos"), ("aldeas.vida.", "vida"), ("aldeas.caminos.", "caminos"),
    ("aldeas.", "aldeas"), ("golems.", "golems"),
    ("unicas.distancia_minima.", "distancia_minima"), ("unicas.atlantida.", "atlantida"), ("unicas.", "unicas"), ("jefes.", "jefes"),
    ("medianas.", "medianas"), ("minas.", "minas"), ("compatibilidad.", "compatibilidad"), ("guia.", "guia"),
    ("botin.", "botin"), ("dificultad.", "dificultad"), ("arena.", "arena"),
]


# Textos de la propia pantalla (cliente).
PANTALLA_ES = {
    "heraldia.config.pantalla.titulo": "Configuración de Heraldia",
    "heraldia.config.pantalla.buscar": "Buscar opciones…",
    "heraldia.config.pantalla.guardar": "Guardar",
    "heraldia.config.pantalla.restaurar": "Valores por defecto",
    "heraldia.config.pantalla.aviso": "Los cambios se aplican al volver a abrir el mundo o reiniciar el servidor, y solo en los chunks que se generen después.",
    "heraldia.config.pantalla.aviso_mundo": "Tienes un mundo abierto: al guardar se aplica ya lo que no afecta a la generación (como /heraldia reload); lo demás, al salir y volver a entrar, solo en chunks nuevos.",
    "heraldia.config.pantalla.aviso_servidor": "Estás en un servidor: esto edita la configuración local de tu cliente (tus mundos de un jugador), no la del servidor. La del servidor está en su config/heraldia.json.",
    "heraldia.config.pantalla.invalido": "Valor no válido: entero de %s a %s",
    "heraldia.config.pantalla.clave": "Opción: %s",
    "heraldia.config.pantalla.guardado": "Configuración de Heraldia guardada",
    "heraldia.config.pantalla.error": "No se pudo guardar config/heraldia.json: %s",
}
PANTALLA_EN = {
    "heraldia.config.pantalla.titulo": "Heraldia configuration",
    "heraldia.config.pantalla.buscar": "Search options…",
    "heraldia.config.pantalla.guardar": "Save",
    "heraldia.config.pantalla.restaurar": "Reset to defaults",
    "heraldia.config.pantalla.aviso": "Changes apply when you reopen the world or restart the server, and only to chunks generated afterwards.",
    "heraldia.config.pantalla.aviso_mundo": "A world is open: saving applies right away whatever does not affect generation (like /heraldia reload); the rest after you leave and rejoin it, only to new chunks.",
    "heraldia.config.pantalla.aviso_servidor": "You are on a server: this edits your client's local configuration (your single-player worlds), not the server's. The server's is in its config/heraldia.json.",
    "heraldia.config.pantalla.invalido": "Invalid value: whole number from %s to %s",
    "heraldia.config.pantalla.clave": "Option: %s",
    "heraldia.config.pantalla.guardado": "Heraldia configuration saved",
    "heraldia.config.pantalla.error": "Could not save config/heraldia.json: %s",
}


def _section(key):
    for prefix, sec in _SECTION_PREFIXES:
        if key.startswith(prefix):
            return sec
    raise ValueError(f"opción {key} sin sección en la pantalla de configuración (añádela a opciones._SECTION_PREFIXES)")


def _key(k):
    return "heraldia.config." + k


def _option(key, default, lo, hi, lang, args=(), pattern=None):
    o = {"clave": key, "defecto": default, "ayuda": lang, "args": list(args), "seccion": _section(key),
         "nombre": _key((_GROUPS[pattern][0] if pattern else key) + ".nombre")}
    if isinstance(lo, list):
        assert default in lo and all(isinstance(v, str) for v in lo), f"{key}: valores de lista no válidos"
        o["valores"] = list(lo)
        o["nombres_valores"] = [_key(f"{key}.{v}") for v in lo]
    elif lo is not None:
        o.update(min=lo, max=hi)
    if pattern:
        o["patron"] = pattern
        name_arg = _GROUP_NAMES[pattern][2]
        o["args_nombre"] = [name_arg % a if name_arg else None for a in args]
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
    assert unicas.REJILLA_ANTIGUA <= set(unique), f"rejilla antigua de únicas que no existen: {unicas.REJILLA_ANTIGUA - set(unique)}"
    for sid, (spacing, _) in unique.items():
        opts.append(_option(f"unicas.{sid}.activada", True, None, None, g["unicas.<id>.activada"], [sid], "unicas.<id>.activada"))
        default = min(max(spacing * 16, UNIQUE_RANGE[0]), UNIQUE_RANGE[1])
        opts.append(_option(f"unicas.{sid}.separacion_bloques", default, *UNIQUE_RANGE, g["unicas.<id>.separacion_bloques"], [sid],
                            "unicas.<id>.separacion_bloques"))
    for mid, mod in medianas.modules():
        opts.append(_option(f"medianas.{mid}.activada", True, None, None, g["medianas.<id>.activada"], [mid], "medianas.<id>.activada"))
        opts.append(_option(f"medianas.{mid}.separacion_bloques", mod.SEPARACION, *MEDIANA_RANGE,
                            g["medianas.<id>.separacion_bloques"], [mid], "medianas.<id>.separacion_bloques"))
    assert set(_NAMES) == {k for k, *_ in _FIXED}, "cada opción fija necesita su nombre corto en _NAMES"
    assert {k: list(v) for k, v in _VALUE_NAMES.items()} == {k: lo for k, _, lo, *_ in _FIXED if isinstance(lo, list)}, \
        "cada opción de lista necesita el nombre de cada valor en _VALUE_NAMES"
    return {
        "version": VERSION,
        "secciones": [{"id": sec, "nombre": _key("seccion." + sec)} for sec, _, _ in SECTIONS],
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
    for k, (es, en) in _NAMES.items():
        out["es_es"][_key(k + ".nombre")], out["en_us"][_key(k + ".nombre")] = es, en
    for p, (es, en, _) in _GROUP_NAMES.items():
        out["es_es"][_key(_GROUPS[p][0] + ".nombre")], out["en_us"][_key(_GROUPS[p][0] + ".nombre")] = es, en
    for k, vals in _VALUE_NAMES.items():
        for v, (es, en) in vals.items():
            out["es_es"][_key(f"{k}.{v}")], out["en_us"][_key(f"{k}.{v}")] = es, en
    for sec, es, en in SECTIONS:
        out["es_es"][_key("seccion." + sec)], out["en_us"][_key("seccion." + sec)] = es, en
    out["es_es"].update(PANTALLA_ES)
    out["en_us"].update(PANTALLA_EN)
    out["es_es"]["heraldia.config.rango"] = "por defecto %s, de %s a %s"
    out["en_us"]["heraldia.config.rango"] = "default %s, from %s to %s"
    out["es_es"]["heraldia.config.si_no"] = "por defecto %s; true o false"
    out["en_us"]["heraldia.config.si_no"] = "default %s; true or false"
    out["es_es"]["heraldia.config.valores"] = "por defecto %s; uno de: %s"
    out["en_us"]["heraldia.config.valores"] = "default %s; one of: %s"
    return out
