"""Encargos del tablón y reputación por aldea (T38): textos y logros. La lógica va en Java (encargos/): el tablón de cada
aldea se rehace igual con la semilla, la aldea y el periodo (Generador), sin datos en el datapack.

Claves:
  heraldia.encargos.*          lo que dice el tablón en el chat, /heraldia quest y los avisos al jugador
  heraldia.estado.encargos*    las líneas de /heraldia status
  advancements.heraldia.encargos.<id>.title/.description   logros (los concede el Java, criterio «hecho»)
Los argumentos (%s) los pone el Java (encargos/Encargos): no cambies su orden sin cambiarlo allí.
"""
NS = "heraldia"
K = f"{NS}.encargos"
# Los niveles de reputación (Reputacion.Nivel; los umbrales y descuentos están en Java y en la Guía).
NIVELES = ("desconocido", "conocido", "amigo", "heroe")
TEXTOS = {
    "preparando": ("El alguacil de %s repasa los encargos...", "The bailiff of %s is going over the jobs..."),
    "nivel.desconocido": ("Desconocido", "Stranger"),
    "nivel.conocido": ("Conocido", "Known"),
    "nivel.amigo": ("Amigo", "Friend"),
    "nivel.heroe": ("Héroe de la aldea", "Village hero"),
    "pista": (" (al %s, a unos %s bloques)", " (%s, about %s blocks away)"),
    "desc.traer": ("Trae %s × %s", "Bring %s × %s"),
    "desc.guardian": ("Vence al guardián de «%s»%s", "Defeat the guardian of “%s”%s"),
    "desc.explorar": ("Explora: %s%s", "Explore: %s%s"),
    "desc.viaje": ("Lleva un mensaje a %s por el camino%s", "Carry a message to %s along the road%s"),
    "desc.arena": ("Supera la oleada %s de la arena", "Survive wave %s of the arena"),
    "paga": ("%s esmeraldas, %s de experiencia, +%s de reputación", "%s emeralds, %s experience, +%s reputation"),
    "paga.sin_reputacion": ("%s esmeraldas, %s de experiencia", "%s emeralds, %s experience"),
    "tablon.titulo": ("Tablón de encargos de %s", "Job board of %s"),
    "tablon.reputacion": ("Tu reputación aquí: %s (%s)", "Your reputation here: %s (%s)"),
    "linea": ("[%s] %s: %s.", "[%s] %s: %s."),
    "estado.entregado": ("(entregado)", "(handed in)"),
    "estado.aceptado": ("(aceptado)", "(accepted)"),
    "estado.cumplido": ("cumplido: vuelve a cobrar", "done: go back to be paid"),
    "estado.caido": ("otro ya lo venció: abandónalo", "someone else defeated it: abandon it"),
    "estado.en_curso": ("en curso", "in progress"),
    "estado.vencido": ("(ya vencido)", "(already defeated)"),
    "boton.aceptar": ("[Aceptar]", "[Accept]"),
    "boton.mios": ("[Mis encargos]", "[My jobs]"),
    "boton.entregar": ("[Entregar]", "[Hand in]"),
    "boton.abandonar": ("[Abandonar]", "[Abandon]"),
    "tablon.rota": ("El tablón cambia en %s días de juego. Varios podéis coger el mismo encargo.",
                    "The board changes in %s in-game days. Several of you can take the same job."),
    "desactivados": ("Los encargos del tablón están desactivados en este servidor.",
                     "Job board quests are disabled on this server."),
    "fuera": ("Tienes que estar en una aldea de Heraldia, junto a su tablón.",
              "You have to be in a Heraldia village, by its job board."),
    "mios.titulo": ("Tus encargos (%s de %s); entregados: %s", "Your jobs (%s of %s); handed in: %s"),
    "mio": ("[%s] %s, para %s: %s.", "[%s] %s, for %s: %s."),
    "mios.ninguno": ("No tienes ningún encargo. Míralos en el tablón de la plaza de una aldea.",
                     "You have no jobs. Look for them on the job board of a village square."),
    "mios.reputacion": (" - %s: %s (%s)", " - %s: %s (%s)"),
    "no_existe": ("No hay encargo número %s (hay %s).", "There is no job number %s (there are %s)."),
    "no_aceptable.hecho": ("Ya entregaste ese encargo.", "You already handed in that job."),
    "no_aceptable.ya": ("Ya tienes ese encargo.", "You already have that job."),
    "no_aceptable.caido": ("Ese guardián ya ha caído: el tablón lo quitará cuando cambie.",
                           "That guardian has already fallen: the board will drop it when it changes."),
    "no_aceptable.lleno": ("Ya llevas %s encargos: entrega o abandona alguno.",
                           "You already carry %s jobs: hand in or abandon one."),
    "aceptado": ("Encargo aceptado: %s.", "Job accepted: %s."),
    "abandonado": ("Encargo abandonado: %s.", "Job abandoned: %s."),
    "faltan": ("Llevas %s de %s × %s: aún no basta.", "You carry %s of %s × %s: not enough yet."),
    "entregado": ("Encargo entregado: %s. Recibes %s.", "Job handed in: %s. You receive %s."),
    "sube": ("En %s ahora te tienen por: %s.", "In %s you are now held as: %s."),
    "nada": ("No tienes nada que entregar en esta aldea.", "You have nothing to hand in at this village."),
    "cumplido": ("¡Encargo cumplido! %s. Vuelve a %s a cobrarlo.", "Job done! %s. Go back to %s to be paid."),
    "baja": ("En %s ya no se fían de ti: ahora te tienen por %s.", "In %s they no longer trust you: you are now %s."),
    "saludo.conocido": ("«Hola de nuevo, vecino de %s.»", "“Hello again, neighbour of %s.”"),
    "saludo.amigo": ("«¡Qué alegría verte, amigo de %s!»", "“So glad to see you, friend of %s!”"),
    "saludo.heroe": ("«¡Paso al héroe de %s!»", "“Make way for the hero of %s!”"),
}
ESTADO = {
    "estado.encargos.no": ("Encargos del tablón: desactivados.", "Job board quests: disabled."),
    "estado.encargos": ("Encargos del tablón entregados entre todos: %s", "Job board quests handed in by everyone: %s"),
    "estado.encargos.tuyos": (" - Tuyos: %s; aldeas amigas: %s; héroe en %s",
                              " - Yours: %s; friendly villages: %s; hero in %s"),
    "estado.encargos.tuyos.sin_reputacion": (" - Tuyos: %s", " - Yours: %s"),
}
# Logros (los concede el Java: encargos/Encargos.logros): (id, icono, marco, experiencia, (título), (descripción))
LOGROS = [
    ("primero", "minecraft:writable_book", "task", 20, ("Manos a la obra", "Lending a Hand"),
     ("Entrega un encargo del tablón de una aldea de Heraldia", "Hand in a job from the board of a Heraldia village")),
    ("diez", "minecraft:emerald", "goal", 60, ("Recadero de confianza", "Trusted Errand Runner"),
     ("Entrega diez encargos del tablón", "Hand in ten job board quests")),
    ("amigo", "minecraft:poppy", "goal", 60, ("Amigo de la aldea", "Friend of the Village"),
     ("Gánate la amistad de una aldea de Heraldia con sus encargos", "Earn the friendship of a Heraldia village with its jobs")),
    ("heroe", "minecraft:bell", "challenge", 150, ("Héroe de la aldea", "Hero of the Village"),
     ("Llega a ser el héroe de una aldea de Heraldia", "Become the hero of a Heraldia village")),
]


def _clave_logro(lid, parte):
    return f"advancements.{NS}.encargos.{lid}.{parte}"


def logros():
    """{ruta: json} de los logros de los encargos (criterio «impossible»: los concede el Java)."""
    out = {}
    padre = f"{NS}:raiz"
    for lid, icono, marco, xp, titulo, desc in LOGROS:
        out[f"encargos/{lid}"] = {
            "parent": padre,
            "criteria": {"hecho": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": icono},
                        "title": {"translate": _clave_logro(lid, "title"), "fallback": titulo[0]},
                        "description": {"translate": _clave_logro(lid, "description"), "fallback": desc[0]},
                        "frame": marco},
            "requirements": [["hecho"]],
            "rewards": {"experience": xp},
        }
        padre = f"{NS}:encargos/{lid}"
    return out


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTOS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    for k, (es, en) in ESTADO.items():
        out["es_es"][f"{NS}.{k}"], out["en_us"][f"{NS}.{k}"] = es, en
    for lid, _, _, _, titulo, desc in LOGROS:
        for i, idioma in enumerate(("es_es", "en_us")):
            out[idioma][_clave_logro(lid, "title")] = titulo[i]
            out[idioma][_clave_logro(lid, "description")] = desc[i]
    return out


def write(out, jdump):
    for ruta, logro in logros().items():
        jdump(out, f"data/{NS}/advancement/{ruta}.json", logro)
