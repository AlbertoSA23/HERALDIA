"""Options of the server configuration file (config/heraldia.json).

A single source: the generator writes the schema to heraldia/options.json (inside the .jar) and the help texts
in the languages; the Java side reads it at startup, validates each value against its range and warns in the log if it is not valid.
"""
from themes import THEMES, FAMILIES
import uniques
import mediums

VERSION = 3   # raise it (and add the migration in HeraldiaConfig.migrate) if the file format changes
# 1 → 2 (T36, profiles): the options a profile sets are only written if they are set by hand (present in the file);
# on migrating, those that had the default value (written by the mod) are removed, and the rest stay set.
# 2 → 3 (light profile): the options of LIGHT_OPTIONS become profile options (written only if set by hand); on
# migrating, those that had the default value are removed (with any other profile they give the same), the rest stay set.

# Village grid (heraldia:aldeas): 94 x 16 = 1,504 blocks; the minimum separation keeps the 62/94 proportion.
VILLAGE_SPACING, VILLAGE_SEPARATION, VILLAGE_SALT = 94, 62, 261112013
VANILLA_EXCLUSION_CHUNKS = 10

# (key, default, minimum, maximum, es_es text, en_us text); minimum and maximum None in yes/no options. In
# list options, "minimum" is the list of values (strings) and "maximum" None; the name of each value goes in _VALUE_NAMES.
_FIXED = [
    ("perfil", "estandar", ["casual", "estandar", "hardcore", "ligero", "personalizado"], None,
     "Perfil de juego: fija de una vez la dificultad, los refuerzos de los guardianes, el botín que se repone, la arena "
     "y los asaltos a las caravanas (casual, más fácil y con el botín que se repone; estándar, lo de siempre; hardcore, heroica, con más refuerzos y "
     "menos experiencia; ligero, el juego de estándar con una generación del mundo más ligera para equipos modestos; "
     "personalizado, cada opción con su valor). Una de esas opciones escrita en el fichero manda sobre "
     "el perfil. Solo ligero cambia la generación del mundo, y en un mundo ya empezado solo en los chunks nuevos",
     "Gameplay profile: sets the difficulty, the guardians' reinforcements, restocking loot, the arena and "
     "caravan ambushes in one go (casual, easier and with restocking loot; standard, as always; hardcore, heroic, with more reinforcements and less "
     "experience; light, the standard game with lighter world generation for modest machines; custom, each option with its own "
     "value). One of those options written in the file overrides the profile. Only light changes world generation, and in "
     "a world already started only in new chunks"),
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
    ("aldeas.vida.rastros", True, None, None,
     "Rastros de trabajo a medias: en algunos solares de la aldea, una casa a medio construir, ropa tendida, una comida a medias, "
     "un taller, un carro cargado, pescado secándose o una hoguera con el puchero (solo bloques, ninguna entidad); solo en aldeas nuevas",
     "Traces of work in progress: on a few plots of the village, a house half built, laundry hanging out, a meal half eaten, a work "
     "yard, a loaded cart, fish drying or a cooking fire with the pot on (blocks only, no entities); new villages only"),
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
    # 100: each type at its own spacing (one medium every ~550 blocks among all of them). The medium-density session
    # lowered it to 60 for a few hours; it measured no generation cost between 100 and 60 (MediumDensityComparisonTest,
    # generation_cost.py --zones medianas: inside the noise), and the owner wants a world full of structures, so it went
    # back to 100 (docs/CONFIGURATION.md, "Medium structures density"). The light profile keeps a lower value.
    ("medianas.frecuencia_porcentaje", 100, 25, 400,
     "Frecuencia de todas las estructuras medianas, en % de la separación propia de cada tipo (100 = la de por "
     "defecto, una cada ~550 bloques entre todas; 200 = el doble; 50 = menos); se aplica sobre la separación de cada tipo",
     "Frequency of all medium structures, as a % of each type's own spacing (100 = the default, one every ~550 blocks "
     "among all of them; 200 = twice as many; 50 = fewer); applied on top of each type's spacing"),
    ("medianas.distancia_minima.bloques", 192, 64, 1024,
     "Distancia mínima entre dos estructuras medianas distintas, en bloques",
     "Minimum distance between two different medium structures, in blocks"),
    ("medianas.distancia_aldeas_unicas_bloques", 256, 128, 1024,
     "Una estructura mediana no sale a menos de esta distancia, en bloques, del inicio de una aldea o una estructura única "
     "de Heraldia (tampoco dentro de la Atlántida)",
     "A medium structure does not spawn closer than this distance, in blocks, to the start of a Heraldia village or unique "
     "structure (nor inside Atlantis)"),
    # Inhabitants of the medium structures (mediums/_inhabitants.py, inhabitants/Inhabitants.java): applied when each one
    # first loads, so only to structures generated (or first loaded) after the change; the light profile turns it off.
    ("medianas.habitantes", True, None, None,
     "Habitantes de las estructuras medianas: el posadero, el molinero, el pescador, los cazadores, el vigía y el ermitaño "
     "viven en su edificio (duermen en su cama y trabajan en su puesto) y la posada tiene sus cerdos. Desactivado, los "
     "nuevos no aparecen y los que ya estaban antes como figuras quietas siguen quietos; solo afecta a los que todavía no "
     "se han cargado nunca",
     "Inhabitants of the medium structures: the innkeeper, the miller, the fisherman, the hunters, the lookout and the "
     "hermit live in their building (they sleep in their bed and work at their workstation) and the inn has its pigs. "
     "Off, the new ones do not appear and those that were already there before as still figures stay still; it only "
     "affects those that have never loaded yet"),
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
    ("faros.activado", True, None, None,
     "Faros en la costa (torre con la luz encendida, casa del farero y embarcadero), en tierra firme junto al mar; solo "
     "en los chunks nuevos",
     "Lighthouses on the coast (a tower with its light lit, the keeper's house and a jetty), on firm ground by the sea; "
     "new chunks only"),
    ("faros.separacion_bloques", 1024, 256, 4000,
     "Separación media entre dos faros, en bloques (solo salen donde hay costa: en la práctica, menos)",
     "Average distance between two lighthouses, in blocks (they only spawn where there is coast: fewer in practice)"),
    ("naufragios.activado", True, None, None,
     "Galeones naufragados de Heraldia (encallados en la playa o semihundidos en aguas poco profundas); solo en los "
     "chunks nuevos",
     "Heraldia wrecked galleons (run aground on the beach or half-sunk in shallow water); new chunks only"),
    ("naufragios.separacion_bloques", 768, 256, 4000,
     "Separación media entre dos galeones naufragados, en bloques (solo salen donde hay costa: en la práctica, menos)",
     "Average distance between two wrecked galleons, in blocks (they only spawn where there is coast: fewer in practice)"),
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
    ("jefes.refuerzos.porcentaje", 100, 0, 300,
     "Cuántos refuerzos llama un guardián en cada fase, en % de los suyos (100: los 2 o 3 de siempre; 150: uno o dos más)",
     "How many reinforcements a guardian calls at each phase, as a % of its own (100: the usual 2 or 3; 150: one or two more)"),
    ("jefes.refuerzos.maximo_vivos", 4, 1, 12,
     "Refuerzos vivos a la vez junto a un guardián como mucho",
     "Maximum reinforcements alive at once near a guardian"),
    ("jefes.barra.activado", True, None, None,
     "Barra de jefe con el nombre del guardián para los jugadores cercanos mientras dura el combate",
     "Boss bar with the guardian's name for nearby players while the fight lasts"),
    ("jefes.apagar_generadores", True, None, None,
     "Al caer el guardián de una estructura única, sus generadores de monstruos se apagan para siempre (la estructura queda "
     "limpia y habitable); desactívalo para que sigan funcionando como antes",
     "When the guardian of a unique structure falls, its monster spawners turn off for good (the structure is left clean "
     "and safe to live in); turn it off to keep them working as before"),
    ("guia.entregar_al_entrar", True, None, None,
     "Guía del Heraldo: da a cada jugador el libro que explica el mod y lleva su diario la primera vez que entra tras "
     "instalar o actualizar Heraldia (una vez por versión; /heraldia guide da otra copia cuando quiera)",
     "Herald's Guide: gives each player the book that explains the mod and keeps their diary the first time they join "
     "after Heraldia is installed or updated (once per version; /heraldia guide gives a new copy at any time)"),
    ("guia.final_cronica", True, None, None,
     "Final de la Crónica de los Heraldos: quien vence (o ve caer cerca) a los guardianes de todas las estructuras únicas "
     "del mundo principal recibe el último pliego, el título de Heraldo de la Atlántida y el estandarte de los Heraldos "
     "(una vez por jugador; cuentan también los guardianes que ya derrotó antes de esta versión)",
     "End of the Chronicle of the Heralds: whoever defeats (or sees fall nearby) the guardians of every unique structure "
     "in the main world gets the last leaf, the title of Herald of Atlantis and the Standard of the Heralds (once per "
     "player; guardians they defeated before this version count too)"),
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
    ("botin.reponer.premium_vencido_modesto", True, None, None,
     "Cofre premium de una única ya vencida: cuando su guardián ha caído, al reponerse solo trae alguna esmeralda de vez en "
     "cuando y, rara vez, un libro encantado modesto (la primera vez que se abre es el premium de siempre); desactívalo para "
     "que se reponga con su premium completo como antes",
     "Premium chest of a cleared unique: once its guardian has fallen, its refills only bring an emerald now and then and, "
     "rarely, a modest enchanted book (the first opening is the usual premium); turn it off to restock it with its full "
     "premium as before"),
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
     "Arena de oleadas cerca del spawn: los operadores la colocan con /heraldia arena place (o se genera sola en un mundo "
     "nuevo); cualquier jugador empieza una partida tocando su campana. Si se desactiva, no hay partidas ni protección",
     "Wave arena near spawn: operators place it with /heraldia arena place (or it is built on its own in a new world); any "
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
    ("arena.modos.cooperativo", True, None, None,
     "Modo cooperativo de la arena (el de siempre): oleadas sin fin con pausa entre ellas; puntúa la oleada superada",
     "Co-op arena mode (the usual one): endless waves with a break in between; the score is the wave cleared"),
    ("arena.modos.contrarreloj", True, None, None,
     "Modo contrarreloj de la arena: un número fijo de oleadas (arena.modos.oleadas_contrarreloj) contra el reloj; "
     "puntúa el tiempo",
     "Time attack arena mode: a fixed number of waves (arena.modos.oleadas_contrarreloj) against the clock; the score "
     "is the time"),
    ("arena.modos.supervivencia", True, None, None,
     "Modo supervivencia de la arena: oleadas sin pausa entre ellas hasta que caen todos; puntúa la oleada más alta",
     "Survival arena mode: waves with no break in between until everyone falls; the score is the highest wave"),
    ("arena.modos.oleadas_contrarreloj", 10, 1, 50,
     "Oleadas del contrarreloj (sus logros piden al menos 10)",
     "Waves in a time attack (its advancements need at least 10)"),
    ("arena.temporada.dia_reinicio", "lunes", ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"], None,
     "Día en que se cierra la semana de la clasificación de la arena (a la hora de arena.temporada.hora_reinicio, hora "
     "del servidor): se anuncian los campeones y empieza otra semana",
     "Day the arena leaderboard week closes (at arena.temporada.hora_reinicio, server time): the champions are "
     "announced and a new week begins"),
    ("arena.temporada.hora_reinicio", 0, 0, 23,
     "Hora (0-23, hora del servidor) a la que se cierra la semana de la arena",
     "Hour (0-23, server time) at which the arena week closes"),
    ("arena.temporada.historico", 8, 1, 52,
     "Semanas cerradas de la clasificación de la arena que se guardan en el mundo (/heraldia arena leaderboard <modo> <semana>)",
     "Closed arena leaderboard weeks kept in the world (/heraldia arena leaderboard <mode> <week>)"),
    ("encargos.activado", True, None, None,
     "Encargos del tablón: el atril del tablón de la plaza de cada aldea de Heraldia (también de las ya generadas) "
     "ofrece de 2 a 4 encargos en el chat (traer objetos, vencer a un guardián, explorar, viajar a una aldea vecina, "
     "la arena) con /heraldia quest; pagan esmeraldas, experiencia y reputación",
     "Job board quests: the job board lectern on the square of every Heraldia village (also those already generated) "
     "offers 2 to 4 quests in chat (bring items, defeat a guardian, explore, travel to a neighbouring village, the "
     "arena) with /heraldia quest; they pay emeralds, experience and reputation"),
    ("encargos.rotacion_dias", 3, 1, 30,
     "Días de juego (24.000 ticks del reloj del mundo) que dura cada tablón antes de cambiar sus encargos (los ya "
     "aceptados se conservan)",
     "In-game days (24,000 ticks of the world clock) each board lasts before its quests change (accepted ones are "
     "kept)"),
    ("reputacion.activado", True, None, None,
     "Reputación por aldea: sube con sus encargos y baja al atacar a sus aldeanos o gólems; con conocido, amigo y "
     "héroe de la aldea, sus aldeanos rebajan los tratos un 10, 20 y 30 % (como Héroe de la aldea, sin acumularse) "
     "y te saludan",
     "Reputation per village: it rises with its quests and falls when you attack its villagers or golems; as known, "
     "friend and village hero, its villagers lower their trades by 10, 20 and 30 % (like Hero of the Village, not "
     "stacking) and greet you"),
    ("dialogos.activado", True, None, None,
     "Conversaciones con los aldeanos: el clic derecho sobre un aldeano de Heraldia dentro de su aldea abre primero una "
     "conversación en el chat (frases según su oficio, la tierra de la aldea, la hora, el tiempo y tu reputación) con "
     "botones para seguir hablando, preguntar qué se cuenta, comerciar o despedirse. Agacharse y hacer clic derecho "
     "abre los tratos directamente; los aldeanos vanilla o de otros mods comercian como siempre",
     "Villager conversations: right-clicking a Heraldia villager inside its village first opens a conversation in "
     "chat (lines by its profession, the village's land, the hour, the weather and your reputation) with buttons to "
     "keep talking, ask for news, trade or say goodbye. Sneak and right-click to open the trades directly; vanilla "
     "villagers and those of other mods trade as always"),
    ("dialogos.espera_segundos", 60, 0, 600,
     "Segundos que descansa cada aldeano entre una conversación y la siguiente (mientras, dice que está ocupado y "
     "ofrece sus tratos); 0: sin espera",
     "Seconds each villager rests between one conversation and the next (meanwhile it says it is busy and offers its "
     "trades); 0: no wait"),
    ("dialogos.viajeros_porcentaje", 10, 0, 100,
     "Porcentaje de aldeanos de Heraldia que han viajado y conocen un sitio: al preguntarles qué se cuenta, una sola "
     "vez en su vida, dicen hacia dónde y a qué distancia aproximada queda una estructura de Heraldia que existe de "
     "verdad (nunca coordenadas); 0: ninguno",
     "Percentage of Heraldia villagers who have travelled and know a place: asked for news, once in their life, they "
     "tell in which direction and roughly how far a Heraldia structure that really exists lies (never coordinates); "
     "0: none"),
    ("dialogos.pista_reputacion", 20, 0, 300,
     "Reputación mínima con la aldea para que un viajero cuente su pista (20: conocido); sin reputación activada, la "
     "cuentan a cualquiera",
     "Minimum reputation with the village for a wayfarer to tell its hint (20: known); with reputation disabled, they "
     "tell anyone"),
    ("dialogos.en_pantalla", True, None, None,
     "Conversaciones y menú de modos de la arena en el centro de la pantalla: un panel con botones (con Heraldia "
     "también en el cliente) o una ventana de cofre cuyas casillas son las opciones (cliente vanilla). Desactivado: "
     "botones en el chat, como antes",
     "Conversations and the arena's mode menu in the middle of the screen: a panel with buttons (with Heraldia also on "
     "the client) or a chest window whose slots are the options (vanilla client). Off: buttons in the chat, as before"),
    ("caravanas.activado", True, None, None,
     "Caravanas: de vez en cuando, con jugadores cerca, un mercader de Heraldia con sus llamas (y a veces un guardia) "
     "recorre un tramo del camino entre dos aldeas vecinas; si la defiendes de los bandidos y llega, paga esmeraldas y "
     "reputación con la aldea de destino. Solo por caminos que existan y en chunks ya cargados",
     "Caravans: now and then, with players nearby, a Heraldia merchant with its llamas (and sometimes a guard) travels "
     "a stretch of the road between two neighbouring villages; defend it from bandits until it arrives and it pays "
     "emeralds and reputation with the destination village. Only along roads that exist and in chunks already loaded"),
    ("caravanas.frecuencia", 10, 0, 100,
     "Probabilidad (%) de que salga una caravana en cada sorteo (uno por minuto, junto a un jugador a menos de 80 "
     "bloques de un camino, 2 min después de la anterior como pronto); 0: solo con /heraldia caravan spawn",
     "Chance (%) of a caravan setting off at each draw (one per minute, next to a player within 80 blocks of a road, "
     "no sooner than 2 min after the previous one); 0: only with /heraldia caravan spawn"),
    ("caravanas.prob_asalto", 35, 0, 100,
     "Probabilidad (%) de que los bandidos asalten una caravana a media ruta (de 2 a 4: saqueadores y un jefe "
     "vindicador)",
     "Chance (%) of bandits ambushing a caravan halfway (2 to 4: pillagers and a vindicator chief)"),
    ("caravanas.max_activas", 1, 1, 3,
     "Caravanas en camino a la vez en todo el servidor, como mucho",
     "Maximum caravans on the road at once on the whole server"),
    ("viajeros.activado", True, None, None,
     "Gente de paso: de vez en cuando, con un jugador cerca, pasa por un camino de Heraldia un peregrino, un pastor con "
     "sus ovejas, un mensajero, una pareja de guardias o un cazador con su perro, según la zona; recorren un tramo y se "
     "van. Solo por caminos que existan y en chunks ya cargados; de 1 a 6 entidades durante uno o dos minutos",
     "Wayfarers: now and then, with a player nearby, a pilgrim, a shepherd with its sheep, a messenger, a pair of guards "
     "or a hunter with its dog passes along a Heraldia road, depending on the area; they walk a stretch and leave. Only "
     "along roads that exist and in chunks already loaded; 1 to 6 entities for a minute or two"),
    ("viajeros.frecuencia", 30, 0, 100,
     "Probabilidad (%) de que pase alguien en cada sorteo (uno por minuto, junto a un jugador a menos de 80 bloques de "
     "un camino, 2 min después del anterior como pronto); 0: solo con /heraldia caravan wayfarer",
     "Chance (%) of someone passing at each draw (one per minute, next to a player within 80 blocks of a road, no "
     "sooner than 2 min after the previous one); 0: only with /heraldia caravan wayfarer"),
    ("viajeros.max_activos", 1, 1, 3,
     "Viajeros en camino a la vez en todo el servidor, como mucho (aparte de las caravanas)",
     "Maximum wayfarers on the road at once on the whole server (besides the caravans)"),
    ("viajeros.peregrino.activado", True, None, None,
     "Peregrino: camina solo hacia el monasterio o la catedral más cercanos (solo si hay uno a menos de 3.000 bloques); "
     "no comercia",
     "Pilgrim: walks alone towards the nearest monastery or cathedral (only if there is one within 3,000 blocks); it "
     "does not trade"),
    ("viajeros.pastor.activado", True, None, None,
     "Pastor: lleva de 3 a 5 ovejas del color de la zona hacia una aldea vecina (no en desierto, badlands, jungla ni "
     "pantano); vende lana y cordero y compra trigo",
     "Shepherd: takes 3 to 5 sheep of the area's colors to a neighbouring village (not in desert, badlands, jungle or "
     "swamp); sells wool and mutton and buys wheat"),
    ("viajeros.mensajero.activado", True, None, None,
     "Mensajero: corre con una carta hacia una aldea vecina sin detenerse; no comercia",
     "Messenger: runs with a letter to a neighbouring village without stopping; it does not trade"),
    ("viajeros.guardias.activado", True, None, None,
     "Pareja de guardias: dos gólems de hierro de una aldea patrullan el camino hacia la vecina, también de noche; se "
     "defienden juntos",
     "Pair of guards: two iron golems of a village patrol the road to the next one, also at night; they defend each other"),
    ("viajeros.cazador.activado", True, None, None,
     "Cazador: vuelve con la pieza de la zona (conejo, jabalí o ave) y su perro, un lobo de la variante del lugar; "
     "vende carne, pieles y flechas",
     "Hunter: comes back with the area's game (rabbit, boar or fowl) and its dog, a wolf of the local variant; sells "
     "meat, hides and arrows"),
    ("chozas_mago.prob_malvado", 20, 0, 100,
     "Probabilidad (%) de que el mago de una choza de mago sea malvado: se decide con la semilla y la choza (siempre "
     "igual para la misma choza) y, si lo es, al acercarse un jugador o al intentar comerciar se revela y se convierte "
     "en el Mago Malvado (un evocador con fases de jefe que invoca vexes); 0: todos comercian",
     "Chance (%) that the wizard of a wizard's hut is evil: decided from the seed and the hut (always the same for the "
     "same hut) and, if so, when a player comes close or tries to trade he reveals himself and becomes the Evil Wizard "
     "(an evoker with boss phases that summons vexes); 0: all of them trade"),
    ("chozas_mago.prob_botin_premium", 30, 0, 100,
     "Probabilidad (%) de que el Mago Malvado suelte además un objeto fuerte que no rompe la progresión (libro de "
     "Reparación, una poción difícil, un tótem de la inmortalidad o un libro de encantamiento alto); se decide por "
     "choza, al revelarse",
     "Chance (%) that the Evil Wizard also drops a strong item that does not break progression (a Mending book, a hard "
     "potion, a totem of undying or a high-level enchanted book); decided per hut, when he reveals himself"),
    ("ambiente.activado", True, None, None,
     "Efectos de ambiente con los sonidos y partículas del juego (nada que descargar): la campana de las aldeas, la "
     "sirena de los faros y los goteos de las minas. Cada uno tiene su opción; con esta desactivada, ninguno suena",
     "Ambient effects with the game's own sounds and particles (nothing to download): the village bell, the lighthouse "
     "siren and the drips in the mines. Each has its own option; with this one off, none of them plays"),
    ("ambiente.campanas", True, None, None,
     "Campana de la aldea: al amanecer y al caer la noche suenan tres campanadas para quien está dentro de una aldea de "
     "Heraldia (como mucho dos veces al día por jugador)",
     "Village bell: at sunrise and at nightfall three strikes ring out for whoever is inside a Heraldia village (at most "
     "twice a day per player)"),
    ("ambiente.sirena_faro", True, None, None,
     "Sirena del faro: con lluvia o tormenta, un faro suena con un cuerno grave que se oye desde el mar, a menos de 160 "
     "bloques y al aire libre (como mucho cada 3 min por jugador)",
     "Lighthouse siren: in rain or a thunderstorm, a lighthouse sounds a deep horn heard from the sea, within 160 blocks "
     "and out in the open (at most every 3 min per player)"),
    ("ambiente.minas", True, None, None,
     "Ecos y goteos en las galerías de las minas de Heraldia: de vez en cuando cae una gota del techo (cada 20-45 s) y, "
     "rara vez, se oye el eco de la cueva (como mucho cada 4 min)",
     "Echoes and drips in the galleries of Heraldia's mines: now and then a drop falls from the ceiling (every 20-45 s) "
     "and, rarely, the cave's echo is heard (at most every 4 min)"),
    ("update_check.activado", True, None, None,
     "Aviso de versión nueva: al arrancar y cada 24 h mira en GitHub Releases si hay una versión más nueva de Heraldia "
     "para este Minecraft y lo dice en la consola y a los operadores al entrar (sin telemetría; se aplica al reiniciar)",
     "New version notice: at startup and every 24 h checks GitHub Releases for a newer Heraldia version for this "
     "Minecraft and says so in the console and to operators when they join (no telemetry; applies on restart)"),
    ("actualizar.margen_bloques", 50, 16, 256,
     "Margen de seguridad, en bloques, alrededor de cualquier construcción de jugador que detecta /heraldia update "
     "analyze: ahí no se regenera ni se coloca nada",
     "Safety margin, in blocks, around any player build that /heraldia update analyze detects: nothing is regenerated "
     "or placed there"),
    ("update_check.prereleases", False, None, None,
     "Avisa también de las pre-publicaciones (alfa, beta, candidatas)",
     "Also announce pre-releases (alpha, beta, release candidates)"),
    ("unicas.atlantida.cofre_unico_por_jugador", False, None, None,
     "Cofre premium de la Atlántida por jugador: cada jugador saca su propia copia del contenido una vez (si no, el primero que llega se lo lleva)",
     "Per-player Atlantis premium chest: each player takes their own copy of its contents once (otherwise the first to arrive takes it all)"),
    ("mapas_web.activado", True, None, None,
     "Marcadores de Heraldia en los mapas web del servidor (BlueMap, Dynmap o squaremap, si alguno está instalado; sin "
     "ellos no hace nada): aldeas, únicas, medianas, entradas de mina y la arena, cada tipo en su capa",
     "Heraldia markers on the server's web maps (BlueMap, Dynmap or squaremap, if one is installed; without them it does "
     "nothing): villages, unique and medium structures, mine entrances and the arena, each kind on its own layer"),
    ("mapas_web.solo_descubiertas", True, None, None,
     "Solo salen en el mapa las de un tipo que algún jugador ya ha descubierto (los mismos logros que cuenta /heraldia "
     "status); si es false, todas las que se han generado en chunks ya cargados",
     "Only those of a kind some player has already discovered are shown (the same advancements /heraldia status "
     "counts); if false, every one generated in chunks already loaded"),
    ("mapas_web.idioma", "auto", ["auto", "es_es", "en_us", "fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es"], None,
     "Idioma de los nombres y descripciones de los marcadores (auto: el del sistema del servidor)",
     "Language of the marker names and descriptions (auto: the server system's)"),
    ("mapas_web.capas.unicas", True, None, None,
     "Capa de las estructuras únicas en los mapas web", "Unique structures layer on the web maps"),
    ("mapas_web.capas.aldeas", True, None, None,
     "Capa de las aldeas de Heraldia en los mapas web", "Heraldia villages layer on the web maps"),
    ("mapas_web.capas.medianas", True, None, None,
     "Capa de las estructuras medianas en los mapas web", "Medium structures layer on the web maps"),
    ("mapas_web.capas.minas", True, None, None,
     "Capa de las entradas de mina en los mapas web", "Mine entrances layer on the web maps"),
    ("mapas_web.capas.costa", True, None, None,
     "Capa de los faros y naufragios en los mapas web", "Lighthouses and wrecks layer on the web maps"),
    ("mapas_web.capas.arena", True, None, None,
     "Capa de la arena de oleadas en los mapas web", "Wave arena layer on the web maps"),
    ("tesoro.activado", True, None, None,
     "Búsqueda del tesoro: a veces sale un fragmento de mapa en los cofres de las medianas, las minas y las únicas (y "
     "como recompensa de las hazañas del tablón); descifrado, lleva por varias estructuras reales hasta un cofre "
     "enterrado. Desactivada, no salen fragmentos y los que haya no hacen nada",
     "Treasure hunt: now and then a map fragment turns up in the chests of medium structures, mines and unique ones (and "
     "as a reward for job-board feats); once deciphered it leads through several real structures to a buried chest. "
     "Disabled, no fragments appear and existing ones do nothing"),
    ("tesoro.probabilidad", 3.0, 0, 100,
     "Probabilidad de que un cofre de una mediana o de una mina lleve un fragmento de mapa del tesoro, en % (admite "
     "decimales; en los de las únicas, la mitad; en las recompensas del tablón, cinco veces más)",
     "Chance that a chest of a medium structure or a mine holds a treasure map fragment, in % (decimals allowed; half "
     "that in unique structures' chests, five times that in job-board rewards)"),
    ("tesoro.radio_max", 1500, 300, 4000,
     "Distancia máxima, en bloques, de cada marca del mapa del tesoro a la anterior (o a donde se descifra el fragmento)",
     "Maximum distance, in blocks, from each mark of the treasure map to the previous one (or to where the fragment is "
     "deciphered)"),    ("reputacion.aldea_visible", True, None, None,
     "La reputación se ve en la aldea: con la mejor reputación que tenga cualquier jugador, flores en la fuente "
     "(conocido); estandartes en las entradas de la plaza, junto al tablón, en las puertas de la muralla y en las "
     "torres (amigo); más flores, faroles en las puertas y una alfombra ante el tablón (héroe); si todos los que la "
     "tratan tienen reputación negativa, las torres cierran sus contraventanas. Solo bloques vanilla y solo donde hay "
     "aire: nunca toca un bloque de un jugador. Desactivada, cada aldea quita lo que puso al cargarse",
     "Reputation shows in the village: with the best reputation any player has there, flowers on the fountain (known); "
     "banners at the square's entrances, by the job board, at the wall gates and on the towers (friend); more flowers, "
     "lanterns on the gates and a carpet before the job board (hero); if everyone who deals with it has negative "
     "reputation, the towers close their shutters. Vanilla blocks only and only on air: it never touches a player's "
     "block. Disabled, each village takes down what it put up when it loads"),
    ("casa_heraldo.activado", True, None, None,
     "La Casa del Heraldo: el pueblo amurallado del spawn (96 × 96 bloques) con su anillo protegido de 50 bloques, donde solo "
     "un operador puede construir o romper y no aparecen monstruos. Desactivada, no se construye ni se protege",
     "The Herald's House: the walled spawn town (96 × 96 blocks) with its 50-block protected ring, where only an operator "
     "can build or break and no monsters spawn. Disabled, it is neither built nor protected"),
    ("casa_heraldo.generar_en_mundos_nuevos", True, None, None,
     "En un mundo nuevo, la Casa del Heraldo se construye sola en el spawn, que pasa a la plaza (en un mundo ya existente, "
     "nunca: la coloca un operador con /heraldia herald place)",
     "In a new world, the Herald's House is built on its own at spawn, and spawn moves to its plaza (never in an existing "
     "world: an operator places it with /heraldia herald place)"),
    ("casa_heraldo.mercado.activado", False, None, None,
     "Puestos del mercado de alquiler: los jugadores pagan una entrada y un alquiler en esmeraldas por un puesto del mercado "
     "de la Casa del Heraldo; quien deja de pagar lo pierde (sus cosas van a un barril de devoluciones)",
     "Market stalls for rent: players pay an entry fee and rent in emeralds for a stall in the Herald's House market; "
     "whoever stops paying loses it (their things go to a return barrel)"),
    ("casa_heraldo.mercado.entrada_esmeraldas", 16, 0, 256,
     "Esmeraldas de entrada para quedarse un puesto libre (se paga una vez, junto con el primer alquiler)",
     "Entry fee in emeralds to take a free stall (paid once, together with the first rent)"),
    ("casa_heraldo.mercado.alquiler_esmeraldas", 4, 0, 256,
     "Esmeraldas de alquiler por periodo (0: el puesto no caduca)",
     "Rent in emeralds per period (0: the stall never runs out)"),
    ("casa_heraldo.mercado.periodo_dias", 7, 1, 60,
     "Duración de cada periodo de alquiler, en días del juego (20 minutos con el servidor en marcha)",
     "Length of each rent period, in game days (20 minutes of the server running)"),
    ("casa_heraldo.mercado.gracia_dias", 3, 0, 30,
     "Días del juego de gracia tras vencer el alquiler antes de perder el puesto (se avisa al inquilino un día antes de "
     "vencer y durante la gracia)",
     "Game days of grace after the rent runs out before the stall is lost (the tenant is warned a day before it is due "
     "and during the grace)"),
    ("casa_heraldo.caminos.activado", True, None, None,
     "Caminos de la Casa del Heraldo: al colocarse el pueblo, de cada puerta sale un camino empedrado e iluminado con "
     "faroles (sin monstruos encima) con chozas de comerciantes humildes; el que más mira a la arena llega hasta ella, con "
     "la choza del guía a la salida. En un mundo cuyo pueblo ya existía, solo con /heraldia herald roads",
     "Herald's House roads: when the town is placed, a road lit with lanterns (no monsters spawn on it) goes out of each "
     "gate, with the huts of humble traders by it; the one that points to the arena reaches it, with the guide's hut at "
     "the town's exit. In a world whose town was already there, only with /heraldia herald roads"),
    ("casa_heraldo.caminos.aldeanos", 5, 0, 8,
     "Aldeanos de las chozas de los caminos, en total (el guía incluido; uno por choza): cada aldeano con su IA cuesta "
     "algo de tiempo de servidor mientras haya un jugador cerca",
     "Villagers in the roadside huts, in all (the guide included; one per hut): each villager with its AI costs some server "
     "time while a player is near"),
    ("casa_heraldo.alrededores.activado", True, None, None,
     "Alrededores de la Casa del Heraldo: al colocarse el pueblo (tras sus caminos), el anillo protegido que lo rodea se "
     "allana en un terreno suave y caminable que se funde con el natural en su borde (sin tajos de más de 10 bloques), con "
     "unos pocos cerezos y casas pequeñas con un cofre de botín (sin aldeanos). En un mundo cuyo pueblo ya existía, solo "
     "con /heraldia herald grounds",
     "Herald's House grounds: when the town is placed (after its roads), the protected ring around it is levelled into "
     "gentle, walkable ground that blends into the natural terrain at its edge (never cut or filled by more than 10 "
     "blocks), with a few cherry trees and small houses with a loot chest (no villagers). In a world whose town was "
     "already there, only with /heraldia herald grounds"),
    ("casa_heraldo.alrededores.casas", 8, 0, 12,
     "Casas pequeñas en los alrededores de la Casa del Heraldo (no se construye ninguna donde el suelo no lo permite)",
     "Small houses in the Herald's House grounds (none is built where the ground does not allow it)"),
    ("eventos.activado", True, None, None,
     "Eventos en las aldeas: de vez en cuando, con un jugador en una aldea de Heraldia, su plaza celebra un día de "
     "mercado, una boda, un funeral o una fiesta durante unos minutos (puestos, un arco, un féretro o una hoguera, y "
     "hasta 15 aldeanos sin IA que hablan, comercian o aceptan regalos); al acabar todo se va. Solo pone bloques sobre "
     "aire y solo quita lo que puso; uno por aldea",
     "Village events: now and then, with a player in a Heraldia village, its square holds a market day, a wedding, a "
     "funeral or a festival for a few minutes (stalls, an arch, a bier or a bonfire, and up to 15 villagers without AI "
     "who speak, trade or take gifts); when it ends everything goes. It only places blocks on air and only removes what "
     "it placed; one per village"),
    ("eventos.frecuencia", 20, 0, 100,
     "Probabilidad (%) de que empiece un evento en cada sorteo (uno cada 30 s por aldea con un jugador dentro, a más de "
     "24 bloques de la plaza); 0: solo con /heraldia event start",
     "Chance (%) of an event starting at each draw (one every 30 s per village with a player inside, more than 24 "
     "blocks from the square); 0: only with /heraldia event start"),
    ("eventos.espera_minutos", 20, 5, 240,
     "Minutos de juego que descansa cada aldea entre un evento y el siguiente (súbelo para que sean más raros)",
     "Minutes of play each village rests between one event and the next (raise it to make them rarer)"),
    ("eventos.max_activos", 2, 1, 4,
     "Eventos a la vez en todo el servidor, como mucho (cada uno, unas 15 entidades durante 3 a 6 minutos)",
     "Maximum events at once on the whole server (each one, about 15 entities for 3 to 6 minutes)"),
]
# Play profiles (option "perfil"): each one sets these gameplay options at once (never world generation ones). "estandar"
# is exactly the usual behavior (the default values); "personalizado" sets nothing (each option with its
# value from the file or, if absent, the default). An option written in the file overrides the profile.
PROFILE = "perfil"
PROFILES = {
    "casual": {
        "dificultad.nivel": "facil", "dificultad.escalar_por_jugadores": False, "dificultad.escalar_botin": False,
        "botin.reponer.activado": True, "botin.reponer.dias": 3,
        "jefes.fases.activado": True, "jefes.refuerzos.activado": True, "jefes.refuerzos.porcentaje": 50,
        "jefes.refuerzos.maximo_vivos": 2,
        "arena.oleada.mobs_incremento": 30, "arena.oleada.stats_incremento": 5, "arena.max_mobs_vivos": 12,
        "arena.experiencia_porcentaje": 30,
        "caravanas.prob_asalto": 15,
        "chozas_mago.prob_malvado": 10,
    },
    "estandar": {},          # filled in with the default values (below): identical to the usual behavior
    "hardcore": {
        "dificultad.nivel": "heroica", "dificultad.escalar_por_jugadores": True, "dificultad.escalar_botin": True,
        "botin.reponer.activado": False, "botin.reponer.dias": 14,
        "jefes.fases.activado": True, "jefes.refuerzos.activado": True, "jefes.refuerzos.porcentaje": 150,
        "jefes.refuerzos.maximo_vivos": 6,
        "arena.oleada.mobs_incremento": 75, "arena.oleada.stats_incremento": 20, "arena.max_mobs_vivos": 28,
        "arena.experiencia_porcentaje": 5,
        "caravanas.prob_asalto": 60,
        "chozas_mago.prob_malvado": 35,
    },
}
CUSTOM = "personalizado"
# The light profile (for modest machines and servers with little RAM): the gameplay of "estandar" plus a lighter world
# generation. It is the only profile that touches generation (GENERATION_PROFILES): the others set the gameplay options
# and leave generation alone (an option of LIGHT written in the file with another profile is just an option, it does not
# make that profile custom). The values come from the measurements of tools/smoke/generation_cost.py (peaks and the
# continuous strip, docs/DEVELOPMENT.md, "Generation cost", and docs/CONFIGURATION.md, "Light profile").
LIGHT = "ligero"
LIGHT_OPTIONS = {
    "aldeas.porcentaje_grandes": 10,             # a large village starts ~2x the pieces of a standard one
    "aldeas.caminos.activado": False,            # the road feature walks its route in every chunk it crosses
    "medianas.frecuencia_porcentaje": 50,        # fewer medium structures than the default 100 (the common kinds thin out)
    "medianas.distancia_minima.bloques": 320,
    "minas.vanilla.multiplicador": 1.0,          # vanilla abandoned mineshafts as in vanilla (the default doubles them)
    "caravanas.activado": False,                 # no caravan entities walking between villages (server ticks)
    "eventos.activado": False,                   # no village events (up to ~15 entities each while one lasts)
    "medianas.habitantes": False,                # no villagers with AI in the medium structures (server ticks)
}
GENERATION_PROFILES = (LIGHT,)
# The only thing the other profiles may touch: gameplay options. World generation (where and how structures appear, the
# arena that builds itself) stays out; GENERATION marks those options in the schema (and the tests check it).
PROFILE_PREFIXES = ("dificultad.", "botin.", "jefes.", "arena.", "caravanas.", "chozas_mago.")
GENERATION = ("aldeas.", "unicas.", "medianas.", "minas.", "faros.", "naufragios.", "compatibilidad.", "arena.generar_en_mundos_nuevos",
              "arena.activado")


# Marked as generation (so no gameplay profile touches them) and yet applied by /heraldia reload (config/Reload.RELOADABLE):
# the flag only keeps the profiles away, it does not mean "needs a restart". arena.activado is gameplay that profiles must
# not switch (the arena builds itself); the other three fall under a generation prefix (aldeas., unicas.) but act while
# playing. Unmarking them would change the generation fingerprint that worlds have saved (ProfileNotice, the
# generacion_mundo attachment, and the search memory key in SearchCaches), so they stay marked and are listed here;
# test_options checks this list against Reload.java, so a new overlap has to be added here on purpose.
GENERATION_RELOADABLE = ("aldeas.vida.tratos_estilo", "aldeas.vida.asedios", "arena.activado",
                         "unicas.atlantida.cofre_unico_por_jugador")


def is_generation(key):
    return key.startswith(GENERATION)


def gameplay_options():
    """Keys that the gameplay profiles (casual, estandar, hardcore) set, in schema order."""
    keys = set().union(*(set(v) for k, v in PROFILES.items() if k != "estandar"))
    return [k for k, *_ in _FIXED if k in keys]


def profile_options():
    """Keys that some profile sets (the gameplay ones and those of the light profile), in schema order."""
    keys = set(gameplay_options()) | set(LIGHT_OPTIONS)
    return [k for k, *_ in _FIXED if k in keys]


def profiles():
    """{profile: {key: value}} with "estandar" = the default values and "ligero" = estandar plus LIGHT_OPTIONS (checks
    that only the generation profiles touch generation)."""
    default = {k: d for k, d, *_ in _FIXED}
    keys = gameplay_options()
    out = {}
    for name, values in list(PROFILES.items()) + [(LIGHT, None)]:
        if name == "estandar":
            values = {k: default[k] for k in keys}
        elif name == LIGHT:
            values = dict({k: default[k] for k in keys}, **LIGHT_OPTIONS)
        expected = set(keys) | (set(LIGHT_OPTIONS) if name == LIGHT else set())
        assert set(values) == expected, f"profile {name}: must set exactly {sorted(expected)}"
        for k, v in values.items():
            if name in GENERATION_PROFILES and k in LIGHT_OPTIONS:
                assert k in default, f"profile {name}: {k} is not a fixed option"
            else:
                assert k.startswith(PROFILE_PREFIXES) and not is_generation(k), f"profile {name}: {k} is not a gameplay option"
            lo, hi = next((lo, hi) for kk, _, lo, hi, *_ in _FIXED if kk == k)
            assert type(v) is type(default[k]), f"profile {name}: {k}={v!r} is not of the option's type"
            if isinstance(lo, list):
                assert v in lo, f"profile {name}: {k}={v!r} is not one of {lo}"
            elif lo is not None:
                assert lo <= v <= hi, f"profile {name}: {k}={v} outside {lo}-{hi}"
        order = profile_options()
        out[name] = {k: values[k] for k in order if k in values}
    return out


# Repeated options: (pattern, text key, es_es, en_us); %s is the name of the family, the style or the structure.
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
MEDIUM_RANGE = mediums.SEPARATION_RANGE

# Short name of each option on the client's configuration screen (the long help goes in the tooltip).
_NAMES = {
    "perfil": ("Perfil de juego", "Gameplay profile"),
    "aldeas.separacion_bloques": ("Separación (bloques)", "Spacing (blocks)"),
    "aldeas.maximo": ("Máximo de aldeas", "Maximum villages"),
    "aldeas.porcentaje_grandes": ("Aldeas grandes (%)", "Large villages (%)"),
    "aldeas.distancia_aldeas_vanilla_bloques": ("Distancia a aldeas vanilla (bloques)", "Distance to vanilla villages (blocks)"),
    "aldeas.vida.tratos_estilo": ("Tratos propios del estilo", "Style trades"),
    "aldeas.vida.tablon": ("Tablón de encargos", "Job board"),
    "aldeas.vida.rastros": ("Rastros de trabajo a medias", "Traces of work in progress"),
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
    "arena.modos.cooperativo": ("Modo cooperativo", "Co-op mode"),
    "arena.modos.contrarreloj": ("Modo contrarreloj", "Time attack mode"),
    "arena.modos.supervivencia": ("Modo supervivencia", "Survival mode"),
    "arena.modos.oleadas_contrarreloj": ("Oleadas del contrarreloj", "Time attack waves"),
    "arena.temporada.dia_reinicio": ("Día de cierre de la semana", "Week closing day"),
    "arena.temporada.hora_reinicio": ("Hora de cierre de la semana", "Week closing hour"),
    "arena.temporada.historico": ("Semanas guardadas", "Weeks kept"),
    "jefes.fases.activado": ("Fases de los guardianes", "Guardian phases"),
    "jefes.refuerzos.activado": ("Refuerzos de los guardianes", "Guardian reinforcements"),
    "jefes.refuerzos.porcentaje": ("Refuerzos por fase (%)", "Reinforcements per phase (%)"),
    "jefes.refuerzos.maximo_vivos": ("Refuerzos vivos a la vez", "Reinforcements alive at once"),
    "jefes.barra.activado": ("Barra de jefe", "Boss bar"),
    "jefes.apagar_generadores": ("Apagar generadores al vencer", "Turn off spawners on victory"),
    "guia.entregar_al_entrar": ("Dar la guía al entrar", "Give the guide on joining"),
    "guia.final_cronica": ("Final de la Crónica", "End of the Chronicle"),
    "botin.reponer.activado": ("Botín que se repone", "Restocking loot"),
    "botin.reponer.dias": ("Días hasta reponerse", "Days until restocked"),
    "botin.reponer.premium_vencido_modesto": ("Premium modesto en únicas vencidas", "Modest premium in cleared uniques"),
    "dificultad.nivel": ("Nivel de dificultad", "Difficulty level"),
    "dificultad.escalar_por_jugadores": ("Más vida con más jugadores", "More health with more players"),
    "dificultad.escalar_botin": ("Botín según la dificultad", "Loot by difficulty"),
    "medianas.activadas": ("Estructuras medianas", "Medium structures"),
    "medianas.frecuencia_porcentaje": ("Frecuencia (%)", "Frequency (%)"),
    "medianas.distancia_minima.bloques": ("Distancia entre medianas (bloques)", "Distance between medium ones (blocks)"),
    "medianas.distancia_aldeas_unicas_bloques": ("Distancia a aldeas y únicas (bloques)",
                                                 "Distance to villages and unique ones (blocks)"),
    "medianas.habitantes": ("Habitantes de las medianas", "Medium structure inhabitants"),
    "minas.entradas.activado": ("Entradas a mina", "Mine entrances"),
    "minas.entradas.separacion_bloques": ("Separación de las entradas (bloques)", "Entrance spacing (blocks)"),
    "minas.vanilla.multiplicador": ("Minas vanilla (multiplicador)", "Vanilla mineshafts (multiplier)"),
    "faros.activado": ("Faros", "Lighthouses"),
    "faros.separacion_bloques": ("Separación de los faros (bloques)", "Lighthouse spacing (blocks)"),
    "naufragios.activado": ("Galeones naufragados", "Wrecked galleons"),
    "naufragios.separacion_bloques": ("Separación de los naufragios (bloques)", "Wreck spacing (blocks)"),
    "encargos.activado": ("Encargos del tablón", "Job board quests"),
    "encargos.rotacion_dias": ("Días hasta cambiar el tablón", "Days until the board changes"),
    "reputacion.activado": ("Reputación por aldea", "Reputation per village"),
    "caravanas.activado": ("Caravanas", "Caravans"),
    "caravanas.frecuencia": ("Frecuencia de las caravanas (%)", "Caravan frequency (%)"),
    "caravanas.prob_asalto": ("Probabilidad de asalto (%)", "Ambush chance (%)"),
    "caravanas.max_activas": ("Caravanas a la vez", "Caravans at once"),
    "dialogos.activado": ("Conversaciones con los aldeanos", "Villager conversations"),
    "dialogos.espera_segundos": ("Espera entre conversaciones (s)", "Wait between conversations (s)"),
    "dialogos.viajeros_porcentaje": ("Aldeanos que conocen un sitio (%)", "Villagers who know a place (%)"),
    "dialogos.pista_reputacion": ("Reputación para una pista", "Reputation for a hint"),
    "dialogos.en_pantalla": ("Conversaciones en pantalla", "Conversations on screen"),
    "viajeros.activado": ("Gente de paso", "Wayfarers"),
    "viajeros.frecuencia": ("Frecuencia de los viajeros (%)", "Wayfarer frequency (%)"),
    "viajeros.max_activos": ("Viajeros a la vez", "Wayfarers at once"),
    "viajeros.peregrino.activado": ("Peregrinos", "Pilgrims"),
    "viajeros.pastor.activado": ("Pastores", "Shepherds"),
    "viajeros.mensajero.activado": ("Mensajeros", "Messengers"),
    "viajeros.guardias.activado": ("Parejas de guardias", "Pairs of guards"),
    "viajeros.cazador.activado": ("Cazadores", "Hunters"),
    "chozas_mago.prob_malvado": ("Magos malvados (%)", "Evil wizards (%)"),
    "chozas_mago.prob_botin_premium": ("Botín premium del Mago Malvado (%)", "Evil Wizard premium loot (%)"),
    "ambiente.activado": ("Efectos de ambiente", "Ambient effects"),
    "ambiente.campanas": ("Campana de la aldea", "Village bell"),
    "ambiente.sirena_faro": ("Sirena del faro", "Lighthouse siren"),
    "ambiente.minas": ("Ecos y goteos de las minas", "Mine echoes and drips"),
    "update_check.activado": ("Aviso de versión nueva", "New version notice"),
    "update_check.prereleases": ("Avisar de pre-publicaciones", "Announce pre-releases"),
    "actualizar.margen_bloques": ("Margen alrededor de construcciones (bloques)", "Margin around player builds (blocks)"),
    "compatibilidad.zona_estructuras_ajenas_bloques": ("Distancia de estructuras de otros mods (bloques)",
                                                       "Distance of other mods' structures (blocks)"),
    "mapas_web.activado": ("Marcadores en los mapas web", "Web map markers"),
    "mapas_web.solo_descubiertas": ("Solo las descubiertas", "Discovered only"),
    "mapas_web.idioma": ("Idioma de los marcadores", "Marker language"),
    "mapas_web.capas.unicas": ("Capa: estructuras únicas", "Layer: unique structures"),
    "mapas_web.capas.aldeas": ("Capa: aldeas", "Layer: villages"),
    "mapas_web.capas.medianas": ("Capa: estructuras medianas", "Layer: medium structures"),
    "mapas_web.capas.minas": ("Capa: entradas de mina", "Layer: mine entrances"),
    "mapas_web.capas.costa": ("Capa: faros y naufragios", "Layer: lighthouses and wrecks"),
    "mapas_web.capas.arena": ("Capa: arena", "Layer: arena"),
    "tesoro.activado": ("Búsqueda del tesoro", "Treasure hunt"),
    "tesoro.probabilidad": ("Fragmentos por cofre (%)", "Fragments per chest (%)"),
    "tesoro.radio_max": ("Distancia máxima entre marcas (bloques)", "Maximum distance between marks (blocks)"),
    "reputacion.aldea_visible": ("La reputación se ve en la aldea", "Reputation shows in the village"),
    "casa_heraldo.activado": ("Casa del Heraldo", "Herald's House"),
    "casa_heraldo.generar_en_mundos_nuevos": ("Construirla en mundos nuevos", "Build it in new worlds"),
    "casa_heraldo.caminos.activado": ("Caminos y chozas", "Roads and huts"),
    "casa_heraldo.caminos.aldeanos": ("Aldeanos de las chozas", "Hut villagers"),
    "casa_heraldo.alrededores.activado": ("Alrededores allanados", "Levelled grounds"),
    "casa_heraldo.alrededores.casas": ("Casas de los alrededores", "Houses around the town"),
    "casa_heraldo.mercado.activado": ("Puestos de alquiler", "Stalls for rent"),
    "casa_heraldo.mercado.entrada_esmeraldas": ("Entrada (esmeraldas)", "Entry fee (emeralds)"),
    "casa_heraldo.mercado.alquiler_esmeraldas": ("Alquiler (esmeraldas)", "Rent (emeralds)"),
    "casa_heraldo.mercado.periodo_dias": ("Periodo de alquiler (días)", "Rent period (days)"),
    "casa_heraldo.mercado.gracia_dias": ("Días de gracia", "Days of grace"),
    "eventos.activado": ("Eventos en las aldeas", "Village events"),
    "eventos.frecuencia": ("Frecuencia de los eventos (%)", "Event frequency (%)"),
    "eventos.espera_minutos": ("Descanso entre eventos (min)", "Rest between events (min)"),
    "eventos.max_activos": ("Eventos a la vez", "Events at once"),
}
# Name of each value of the list options: {key: {value: (es_es, en_us)}}.
_VALUE_NAMES = {
    "perfil": {"casual": ("Casual", "Casual"), "estandar": ("Estándar", "Standard"), "hardcore": ("Hardcore", "Hardcore"),
               "ligero": ("Ligero", "Light"), "personalizado": ("Personalizado", "Custom")},
    "dificultad.nivel": {"facil": ("Fácil", "Easy"), "normal": ("Normal", "Normal"), "dificil": ("Difícil", "Hard"),
                         "heroica": ("Heroica", "Heroic")},
    "arena.temporada.dia_reinicio": {"lunes": ("Lunes", "Monday"), "martes": ("Martes", "Tuesday"),
                                     "miercoles": ("Miércoles", "Wednesday"), "jueves": ("Jueves", "Thursday"),
                                     "viernes": ("Viernes", "Friday"), "sabado": ("Sábado", "Saturday"),
                                     "domingo": ("Domingo", "Sunday")},
    "mapas_web.idioma": {"auto": ("Automático (el del sistema)", "Automatic (the system's)"),
                         "es_es": ("Español", "Español"), "en_us": ("English", "English"), "fr_fr": ("Français", "Français"),
                         "de_de": ("Deutsch", "Deutsch"), "it_it": ("Italiano", "Italiano"),
                         "pt_br": ("Português (Brasil)", "Português (Brasil)"), "ca_es": ("Català", "Català"),
                         "gl_es": ("Galego", "Galego")},
}
# Groups: short name (%s = name of the family, the style or the structure) and key of the argument's name
# (None: the id as is, as in the README).
_GROUP_NAMES = {
    "aldeas.familias.<familia>": ("%s", "%s", "heraldia.familia.%s"),
    "aldeas.estilos.<estilo>": ("%s", "%s", None),
    "unicas.<id>.activada": ("%s", "%s", "heraldia.unicas.%s.nombre"),
    "unicas.<id>.separacion_bloques": ("%s: separación (bloques)", "%s: spacing (blocks)", "heraldia.unicas.%s.nombre"),
    "medianas.<id>.activada": ("%s", "%s", "heraldia.medianas.%s.nombre"),
    "medianas.<id>.separacion_bloques": ("%s: separación (bloques)", "%s: spacing (blocks)", "heraldia.medianas.%s.nombre"),
}
# Screen sections, in order of appearance: (id, es_es, en_us).
SECTIONS = [
    ("perfil", "Perfil de juego", "Gameplay profile"),
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
    ("costa", "Faros y naufragios", "Lighthouses and wrecks"),
    ("compatibilidad", "Compatibilidad con otros mods", "Compatibility with other mods"),
    ("botin", "Botín", "Loot"),
    ("dificultad", "Dificultad", "Difficulty"),
    ("guia", "Guía del Heraldo", "Herald's Guide"),
    ("arena", "Arena de oleadas", "Wave arena"),
    ("encargos", "Encargos y reputación", "Quests and reputation"),
    ("dialogos", "Conversaciones", "Conversations"),
    ("caravanas", "Caravanas", "Caravans"),
    ("viajeros", "Gente de paso", "Wayfarers"),
    ("chozas_mago", "Chozas de mago", "Wizard's huts"),
    ("ambiente", "Ambiente", "Ambience"),
    ("actualizaciones", "Actualizaciones", "Updates"),
    ("mapas_web", "Mapas web", "Web maps"),
    ("tesoro", "Búsqueda del tesoro", "Treasure hunt"),
    ("casa_heraldo", "Casa del Heraldo", "Herald's House"),
    ("eventos", "Eventos en las aldeas", "Village events"),
]
# Key prefix -> section; the first one that fits wins, so a new option falls into its section on its own
# (if it fits in none, generation fails).
_SECTION_PREFIXES = [
    ("perfil", "perfil"),
    ("aldeas.familias.", "familias"), ("aldeas.estilos.", "estilos"), ("aldeas.vida.", "vida"), ("aldeas.caminos.", "caminos"),
    ("aldeas.", "aldeas"), ("golems.", "golems"),
    ("unicas.distancia_minima.", "distancia_minima"), ("unicas.atlantida.", "atlantida"), ("unicas.", "unicas"), ("jefes.", "jefes"),
    ("medianas.", "medianas"), ("minas.", "minas"), ("faros.", "costa"), ("naufragios.", "costa"),
    ("compatibilidad.", "compatibilidad"), ("guia.", "guia"),
    ("botin.", "botin"), ("dificultad.", "dificultad"), ("arena.", "arena"), ("encargos.", "encargos"), ("reputacion.", "encargos"), ("dialogos.", "dialogos"),
    ("caravanas.", "caravanas"), ("viajeros.", "viajeros"), ("chozas_mago.", "chozas_mago"), ("ambiente.", "ambiente"),
    ("update_check.", "actualizaciones"), ("actualizar.", "actualizaciones"), ("mapas_web.", "mapas_web"), ("tesoro.", "tesoro"),
    ("casa_heraldo.", "casa_heraldo"),
    ("eventos.", "eventos"),
]


# Texts of the screen itself (client).
SCREEN_ES = {
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
    "heraldia.config.pantalla.perfil_valor": "Perfil %s: %s",
    "heraldia.config.pantalla.fijada": "Fijada a mano: manda sobre el perfil",
    "heraldia.config.pantalla.perfil_efectivo": "Perfil efectivo: %s. Distintas del perfil: %s",
}
SCREEN_EN = {
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
    "heraldia.config.pantalla.perfil_valor": "%s profile: %s",
    "heraldia.config.pantalla.fijada": "Set by hand: overrides the profile",
    "heraldia.config.pantalla.perfil_efectivo": "Effective profile: %s. Different from the profile: %s",
}
# /heraldia profile (new command, in English) and the file's help.
PROFILE_ES = {
    "heraldia.perfil.titulo": "Perfil de juego: %s (en el fichero: %s)",
    "heraldia.perfil.opcion": " - %s = %s",
    "heraldia.perfil.opcion.fijada": " - %s = %s (fijada a mano; el perfil da %s)",
    "heraldia.perfil.ninguna": "Ninguna opción fijada a mano: manda el perfil.",
    "heraldia.perfil.personalizado": "Con opciones fijadas a mano, el perfil queda como personalizado.",
    "heraldia.config.perfiles": "casual %s, estándar %s, hardcore %s",
    "heraldia.config.perfil_ligero": "ligero %s",
}
PROFILE_EN = {
    "heraldia.perfil.titulo": "Gameplay profile: %s (in the file: %s)",
    "heraldia.perfil.opcion": " - %s = %s",
    "heraldia.perfil.opcion.fijada": " - %s = %s (set by hand; the profile gives %s)",
    "heraldia.perfil.ninguna": "No option set by hand: the profile rules.",
    "heraldia.perfil.personalizado": "With options set by hand, the profile becomes custom.",
    "heraldia.config.perfiles": "casual %s, standard %s, hardcore %s",
    "heraldia.config.perfil_ligero": "light %s",
}


def _section(key):
    for prefix, sec in _SECTION_PREFIXES:
        if key.startswith(prefix):
            return sec
    raise ValueError(f"option {key} has no section on the configuration screen (add it to opciones._SECTION_PREFIXES)")


def _key(k):
    return "heraldia.config." + k


def _option(key, default, lo, hi, lang, args=(), pattern=None):
    o = {"clave": key, "defecto": default, "ayuda": lang, "args": list(args), "seccion": _section(key),
         "nombre": _key((_GROUPS[pattern][0] if pattern else key) + ".nombre")}
    if is_generation(key):
        o["generacion"] = True
    if isinstance(lo, list):
        assert default in lo and all(isinstance(v, str) for v in lo), f"{key}: invalid list values"
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
    """{id: (spacing, separation)} of the configurable unique structures (those without their own placement)."""
    return {sid: (m.STRUCTURE.get("spacing", uniques.DEFAULT_SPACING), m.STRUCTURE.get("separation", uniques.DEFAULT_SEPARATION))
            for sid, m in uniques.modules() if "placement" not in m.STRUCTURE}


def schema():
    opts = [_option(k, d, lo, hi, _key(k)) for k, d, lo, hi, _, _ in _FIXED]
    g = {p: _key(v[0]) for p, v in _GROUPS.items()}
    for fam in FAMILIES:
        opts.append(_option(f"aldeas.familias.{fam}", True, None, None, g["aldeas.familias.<familia>"], [fam], "aldeas.familias.<familia>"))
    for th in THEMES:
        opts.append(_option(f"aldeas.estilos.{th['id']}", True, None, None, g["aldeas.estilos.<estilo>"], [th["id"]], "aldeas.estilos.<estilo>"))
    unique = unique_placements()
    assert uniques.OLD_GRID <= set(unique), f"old grid of unique structures that do not exist: {uniques.OLD_GRID - set(unique)}"
    for sid, (spacing, _) in unique.items():
        opts.append(_option(f"unicas.{sid}.activada", True, None, None, g["unicas.<id>.activada"], [sid], "unicas.<id>.activada"))
        default = min(max(spacing * 16, UNIQUE_RANGE[0]), UNIQUE_RANGE[1])
        opts.append(_option(f"unicas.{sid}.separacion_bloques", default, *UNIQUE_RANGE, g["unicas.<id>.separacion_bloques"], [sid],
                            "unicas.<id>.separacion_bloques"))
    for mid, mod in mediums.modules():
        opts.append(_option(f"medianas.{mid}.activada", True, None, None, g["medianas.<id>.activada"], [mid], "medianas.<id>.activada"))
        opts.append(_option(f"medianas.{mid}.separacion_bloques", mod.SEPARATION, *MEDIUM_RANGE,
                            g["medianas.<id>.separacion_bloques"], [mid], "medianas.<id>.separacion_bloques"))
    assert set(_NAMES) == {k for k, *_ in _FIXED}, "every fixed option needs its short name in _NAMES"
    assert {k: list(v) for k, v in _VALUE_NAMES.items()} == {k: lo for k, _, lo, *_ in _FIXED if isinstance(lo, list)}, \
        "every list option needs the name of each value in _VALUE_NAMES"
    perf = profiles()
    marked = set(profile_options())
    for o in opts:
        if o["clave"] in marked:
            o["perfil"] = True
    return {
        "version": VERSION,
        "secciones": [{"id": sec, "nombre": _key("seccion." + sec)} for sec, _, _ in SECTIONS],
        "opciones": opts,
        "perfiles": perf,
        "perfiles_generacion": list(GENERATION_PROFILES),
        "aldeas": {"spacing": VILLAGE_SPACING, "separation": VILLAGE_SEPARATION,
                   "estilos": {th["id"]: th["family"] for th in THEMES}},
        "unicas": {sid: {"spacing": sp, "separation": se} for sid, (sp, se) in unique.items()},
    }


def lang():
    """Help texts of each option: {"es_es": {...}, "en_us": {...}}."""
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
    out["es_es"].update(SCREEN_ES)
    out["en_us"].update(SCREEN_EN)
    out["es_es"].update(PROFILE_ES)
    out["en_us"].update(PROFILE_EN)
    out["es_es"]["heraldia.config.rango"] = "por defecto %s, de %s a %s"
    out["en_us"]["heraldia.config.rango"] = "default %s, from %s to %s"
    out["es_es"]["heraldia.config.si_no"] = "por defecto %s; true o false"
    out["en_us"]["heraldia.config.si_no"] = "default %s; true or false"
    out["es_es"]["heraldia.config.valores"] = "por defecto %s; uno de: %s"
    out["en_us"]["heraldia.config.valores"] = "default %s; one of: %s"
    return out
