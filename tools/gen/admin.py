"""Textos de las herramientas de administración (Java, comando/): /heraldia review (ruta guiada de revisión),
/heraldia status (resumen del servidor) y /heraldia reload (recarga en caliente de la configuración).

El Java toma el texto de respaldo de es_es (comando/Textos); las traducciones van en idiomas/<código>.json. Los puntos
de la lista de cada tipo de parada son heraldia.revisar.mirar.<tipo>.<n> (cuántos: PUNTOS, el mismo número que
RevisarCommand.PUNTOS) y los propios de una única, heraldia.revisar.mirar.unica.<id> (CON_PUNTO_PROPIO).
"""
NS = "heraldia"

# tipo de parada -> puntos de su lista (RevisarCommand.PUNTOS)
PUNTOS = {"aldea": 4, "unica": 4, "mediana": 3, "mina": 3, "arena": 3, "camino": 3}
# únicas con un punto propio en la lista (RevisarCommand.CON_PUNTO_PROPIO)
CON_PUNTO_PROPIO = ("atlantida", "isla_corsario")
# botones de la ruta (heraldia.revisar.boton.<id> y su ayuda, .ayuda)
BOTONES = ("revisada", "nota", "problema", "saltar", "anterior", "siguiente", "lista", "generar", "ir")

_TEXTOS = {
    # --- /heraldia review ---
    "revisar.parada.arena": ("La arena de oleadas", "The wave arena"),
    "revisar.parada.camino": ("Un tramo de camino", "A stretch of road"),
    "revisar.buscando": ("Buscando %s fuera del hilo del servidor (sin generar nada)...",
                         "Looking for %s off the server thread (without generating anything)..."),
    "revisar.cargando": ("Cargando la zona...", "Loading the area..."),
    "revisar.teletransportado": ("Teletransportado a %s, %s, %s, encima del suelo.", "Teleported to %s, %s, %s, above ground."),
    "revisar.sin_sitio": ("No hay ningún sitio seguro cerca de %s: no te muevo.", "There is no safe spot near %s: you stay where you are."),
    "revisar.no_encontrada": ("%s: no hay ninguna a menos de %s bloques del punto de aparición (o no sale en este mundo).",
                              "%s: none within %s blocks of the world spawn (or it does not appear in this world)."),
    "revisar.sin_arena": ("%s no está colocada: un operador la coloca con /heraldia arena colocar.",
                          "%s has not been placed: an operator places it with /heraldia arena colocar."),
    "revisar.prevista": ("La más cercana está en %s (a %s bloques del punto de aparición) y aún no se ha generado: ir allí "
                         "genera terreno nuevo en ese sitio.",
                         "The nearest one is at %s (%s blocks from the world spawn) and has not been generated yet: going "
                         "there generates new terrain at that spot."),
    "revisar.titulo": ("Revisión %s/%s: %s (%s)", "Review %s/%s: %s (%s)"),
    "revisar.subtitulo": ("Parada %s de %s", "Stop %s of %s"),
    "revisar.mirar": ("Qué mirar:", "What to check:"),
    "revisar.punto": (" • %s", " • %s"),
    "revisar.ya_marcada": ("Ya la marcaste: %s%s", "Already marked: %s%s"),
    "revisar.con_nota": (" («%s»)", " (“%s”)"),
    "revisar.marcada": ("%s (%s): %s%s", "%s (%s): %s%s"),
    "revisar.sin_parada": ("No estás en ninguna parada: has llegado al final de la ruta.",
                           "You are not at any stop: you have reached the end of the route."),
    "revisar.fin": ("Has llegado al final de la ruta. El resumen: /heraldia review status.",
                    "You have reached the end of the route. Summary: /heraldia review status."),
    "revisar.ocupado": ("Ya hay una búsqueda en marcha: espera a que termine.", "A search is already running: wait for it to finish."),
    "revisar.desconocida": ("No hay ninguna parada «%s». Mira /heraldia review list.", "There is no stop “%s”. See /heraldia review list."),
    "revisar.lista.titulo": ("Ruta de revisión (%s paradas; pulsa una para ir):", "Review route (%s stops; click one to go there):"),
    "revisar.lista.linea": ("%s. %s (%s): %s", "%s. %s (%s): %s"),
    "revisar.resumen": ("Revisión de %s: %s de %s revisadas, %s con problema, %s saltadas, %s pendientes",
                        "Review by %s: %s of %s checked, %s with a problem, %s skipped, %s pending"),
    "revisar.resumen.problema": (" ✘ %s (%s): %s", " ✘ %s (%s): %s"),
    "revisar.exportado": ("Notas guardadas en %s", "Notes saved to %s"),
    "revisar.reiniciada": ("Ruta reiniciada: tus marcas se han borrado.", "Route restarted: your marks have been cleared."),
    "revisar.estado.revisada": ("revisada", "checked"),
    "revisar.estado.problema": ("con problema", "with a problem"),
    "revisar.estado.saltada": ("saltada", "skipped"),
    "revisar.estado.pendiente": ("pendiente", "pending"),
    "revisar.boton.revisada": ("[✔ Revisada]", "[✔ Checked]"),
    "revisar.boton.revisada.ayuda": ("Marca esta parada como revisada", "Mark this stop as checked"),
    "revisar.boton.nota": ("[+ Nota]", "[+ Note]"),
    "revisar.boton.nota.ayuda": ("Revisada, con una nota: escríbela detrás de la orden", "Checked, with a note: type it after the command"),
    "revisar.boton.problema": ("[✘ Problema]", "[✘ Problem]"),
    "revisar.boton.problema.ayuda": ("Algo falla: escribe qué detrás de la orden", "Something is wrong: type what after the command"),
    "revisar.boton.saltar": ("[Saltar]", "[Skip]"),
    "revisar.boton.saltar.ayuda": ("La deja para luego y pasa a la siguiente", "Leave it for later and go to the next one"),
    "revisar.boton.anterior": ("[« Anterior]", "[« Previous]"),
    "revisar.boton.anterior.ayuda": ("Vuelve a la parada anterior", "Go back to the previous stop"),
    "revisar.boton.siguiente": ("[Siguiente »]", "[Next »]"),
    "revisar.boton.siguiente.ayuda": ("Pasa a la siguiente parada", "Go to the next stop"),
    "revisar.boton.lista": ("[Lista]", "[List]"),
    "revisar.boton.lista.ayuda": ("Todas las paradas y cómo van", "All the stops and how they are going"),
    "revisar.boton.generar": ("[Ir y generar]", "[Go and generate]"),
    "revisar.boton.generar.ayuda": ("Te lleva allí aunque se genere terreno nuevo", "Takes you there even if new terrain is generated"),
    "revisar.boton.ir": ("[Ir]", "[Go]"),
    "revisar.boton.ir.ayuda": ("Ir a esta parada", "Go to this stop"),
    # qué mirar en cada tipo de parada
    "revisar.mirar.aldea.1": ("Plaza, calles y casas asentadas en el terreno, sin escalones sueltos ni bloques flotando",
                              "Square, streets and houses sit well on the terrain, with no loose steps or floating blocks"),
    "revisar.mirar.aldea.2": ("Interiores con sentido: muebles pegados al muro, sin tapar ventanas ni puertas",
                              "Interiors make sense: furniture against the walls, not blocking windows or doors"),
    "revisar.mirar.aldea.3": ("Aldeanos con oficio, campana, gólems y el tablón de encargos de la plaza",
                              "Villagers with professions, the bell, golems and the job board on the square"),
    "revisar.mirar.aldea.4": ("El estilo encaja con su bioma y con su familia",
                              "The style suits its biome and its family"),
    "revisar.mirar.unica.1": ("Por fuera, en buen estado casi toda, con detalles ruinosos con sentido y bien asentada",
                              "Outside, mostly in good repair, with sensible ruined details, and sitting well on the ground"),
    "revisar.mirar.unica.2": ("Todas las salas: escaleras completas, ninguna puerta sin salida y las salas ocultas",
                              "Every room: complete stairs, no dead-end doors, and the hidden rooms"),
    "revisar.mirar.unica.3": ("Los puzles y trampas de redstone funcionan; generadores en las mazmorras",
                              "Redstone puzzles and traps work; spawners in the dungeons"),
    "revisar.mirar.unica.4": ("El guardián, su barra de jefe y la cámara final con el cofre premium",
                              "The guardian, its boss bar and the final chamber with the premium chest"),
    "revisar.mirar.unica.atlantida": ("Bajo el agua: lleva respiración acuática; mira las salas secas y los tres sellos",
                                      "Underwater: bring water breathing; check the dry halls and the three seals"),
    "revisar.mirar.unica.isla_corsario": ("Entra en barca a las cuevas marinas por el acantilado",
                                          "Take a boat into the sea caves through the cliff"),
    "revisar.mirar.mediana.1": ("Huella pequeña y bien asentada, con la entrada al norte",
                                "Small footprint sitting well on the ground, entrance to the north"),
    "revisar.mirar.mediana.2": ("Cada elemento tiene una función; botín modesto",
                                "Every element has a purpose; modest loot"),
    "revisar.mirar.mediana.3": ("Mobs y aldeanos en su sitio, sin escaparse ni asfixiarse",
                                "Mobs and villagers in place, not wandering off or suffocating"),
    "revisar.mirar.mina.1": ("La boca encaja en la ladera, sin cortes raros en el terreno",
                             "The adit fits the hillside, with no odd cuts in the terrain"),
    "revisar.mirar.mina.2": ("Baja por la galería: vías, cruces y salas completas, sin huecos al vacío",
                             "Go down the gallery: complete rails, crossings and rooms, no holes into the void"),
    "revisar.mirar.mina.3": ("Iluminación, apuntalado y los cofres del fondo",
                             "Lighting, timbering and the chests at the bottom"),
    "revisar.mirar.arena.1": ("Ruedo, gradas y campana completos (y protegidos contra romperlos)",
                              "Ring, stands and bell complete (and protected from breaking)"),
    "revisar.mirar.arena.2": ("Toca la campana: cuenta atrás, oleadas, barra y puerta del ruedo",
                              "Ring the bell: countdown, waves, bar and the ring's gate"),
    "revisar.mirar.arena.3": ("Marcador y récord al superar una oleada",
                              "Scoreboard and record after clearing a wave"),
    "revisar.mirar.camino.1": ("Trazado continuo entre dos aldeas, a ras del terreno (solo en chunks nuevos)",
                               "Continuous route between two villages, flush with the terrain (new chunks only)"),
    "revisar.mirar.camino.2": ("Farolas, puentes y pasarelas sin bloques flotando",
                               "Lamp posts, bridges and walkways with no floating blocks"),
    "revisar.mirar.camino.3": ("Carteles con el nombre de la aldea de destino y su distancia",
                               "Signs with the destination village's name and its distance"),
    # --- /heraldia status ---
    "estado.titulo": ("Heraldia %s: estado del servidor (página %s de %s)", "Heraldia %s: server status (page %s of %s)"),
    "estado.dificultad": ("Dificultad: %s; más vida por jugador: %s; botín escalado: %s",
                          "Difficulty: %s; more health per player: %s; scaled loot: %s"),
    "estado.generacion": ("Generación: aldeas cada %s bloques (máximo %s), medianas %s, minas %s, caminos %s, %s de %s únicas activadas",
                          "Generation: villages every %s blocks (at most %s), medium structures %s, mines %s, roads %s, %s of %s unique structures enabled"),
    "estado.descubiertas": ("Descubiertas por algún jugador (%s jugadores con logros):",
                            "Discovered by some player (%s players with advancements):"),
    "estado.tipo.aldeas": (" - Aldeas (una de cada familia): %s de %s", " - Villages (one of each family): %s of %s"),
    "estado.tipo.unicas": (" - Estructuras únicas: %s de %s", " - Unique structures: %s of %s"),
    "estado.tipo.medianas": (" - Estructuras medianas (por tipo): %s de %s", " - Medium structures (by type): %s of %s"),
    "estado.tipo.minas": (" - Entradas a mina (por tamaño): %s de %s", " - Mine entrances (by size): %s of %s"),
    "estado.faltan": ("   Faltan: %s", "   Missing: %s"),
    "estado.guardianes": ("Guardianes vencidos: %s de %s", "Guardians defeated: %s of %s"),
    "estado.arena": ("Arena: %s; récord del servidor: %s oleadas", "Arena: %s; server record: %s waves"),
    "estado.arena.colocada": ("colocada", "placed"),
    "estado.arena.sin_colocar": ("sin colocar", "not placed"),
    "estado.reponer": ("Botín que se repone: activado (cada %s días de juego)", "Restocking loot: enabled (every %s in-game days)"),
    "estado.reponer.no": ("Botín que se repone: desactivado", "Restocking loot: disabled"),
    "estado.reponer.lootr": ("Botín que se repone: sin efecto (Lootr ya da botín por jugador)",
                             "Restocking loot: no effect (Lootr already gives per-player loot)"),
    "estado.lootr": ("Lootr: %s", "Lootr: %s"),
    "estado.jefes": ("Jefes: fases %s, refuerzos %s, barra %s; Guía al entrar: %s",
                     "Bosses: phases %s, reinforcements %s, bar %s; Guide on join: %s"),
    "estado.mods": ("Otros mods (%s): %s", "Other mods (%s): %s"),
    "estado.anterior": ("[« Página anterior]", "[« Previous page]"),
    "estado.siguiente": ("[Página siguiente »]", "[Next page »]"),
    # --- /heraldia reload ---
    "recargar.titulo": ("Configuración recargada de %s", "Configuration reloaded from %s"),
    "recargar.nada": ("No ha cambiado ninguna opción que se pueda aplicar en caliente.",
                      "No option that can be applied live has changed."),
    "recargar.aplicadas": ("Aplicadas ya (%s):", "Applied now (%s):"),
    "recargar.aplicada": (" ✔ %s = %s", " ✔ %s = %s"),
    "recargar.pendientes": ("Exigen reiniciar el servidor porque afectan a la generación (%s); no se aplican:",
                            "Require a server restart because they affect generation (%s); not applied:"),
    "recargar.pendiente": (" ✘ %s: %s en uso, %s en el fichero", " ✘ %s: %s in use, %s in the file"),
    "recargar.mobs": ("Dificultad recalculada en %s mobs de Heraldia cargados.", "Difficulty recalculated for %s loaded Heraldia mobs."),
    "recargar.arena_partida": ("Hay una partida en la arena: sus opciones no cambian hasta que acabe (vuelve a recargar entonces).",
                               "A match is running in the arena: its options do not change until it ends (reload again then)."),
}


def lang():
    """{"es_es": {...}, "en_us": {...}} con todos los textos de las herramientas de administración."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in _TEXTOS.items():
        out["es_es"][f"{NS}.{k}"] = es
        out["en_us"][f"{NS}.{k}"] = en
    return out


def claves_mirar():
    """Claves de todos los puntos de las listas de qué mirar (las que el Java puede pedir)."""
    out = [f"{NS}.revisar.mirar.{t}.{i}" for t, n in PUNTOS.items() for i in range(1, n + 1)]
    return out + [f"{NS}.revisar.mirar.unica.{u}" for u in CON_PUNTO_PROPIO]
