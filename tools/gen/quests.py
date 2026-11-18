"""Quest board quests and reputation per village (T38): texts and advancements. The logic is in Java (encargos/): each village's
board is rebuilt identically from the seed, the village and the period (Generador), with no data in the datapack.

Keys:
  heraldia.encargos.*          what the board says in chat, /heraldia quest and the notices to the player
  heraldia.estado.encargos*    the lines of /heraldia status
  advancements.heraldia.encargos.<id>.title/.description   advancements (granted by the Java, criterion "hecho")
The arguments (%s) are supplied by the Java (encargos/Encargos): do not change their order without changing it there.
"""
NS = "heraldia"
K = f"{NS}.encargos"
# The reputation levels (Reputacion.Nivel; the thresholds and discounts are in Java and in the Guide).
LEVELS = ("desconocido", "conocido", "amigo", "heroe")
TEXTS = {
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
STATE = {
    "estado.encargos.no": ("Encargos del tablón: desactivados.", "Job board quests: disabled."),
    "estado.encargos": ("Encargos del tablón entregados entre todos: %s", "Job board quests handed in by everyone: %s"),
    "estado.encargos.tuyos": (" - Tuyos: %s; aldeas amigas: %s; héroe en %s",
                              " - Yours: %s; friendly villages: %s; hero in %s"),
    "estado.encargos.tuyos.sin_reputacion": (" - Tuyos: %s", " - Yours: %s"),
}
# Advancements (granted by the Java: encargos/Encargos.logros): (id, icon, frame, experience, (title), (description))
ADVANCEMENTS = [
    ("primero", "minecraft:writable_book", "task", 20, ("Manos a la obra", "Lending a Hand"),
     ("Entrega un encargo del tablón de una aldea de Heraldia", "Hand in a job from the board of a Heraldia village")),
    ("diez", "minecraft:emerald", "goal", 60, ("Recadero de confianza", "Trusted Errand Runner"),
     ("Entrega diez encargos del tablón", "Hand in ten job board quests")),
    ("amigo", "minecraft:poppy", "goal", 60, ("Amigo de la aldea", "Friend of the Village"),
     ("Gánate la amistad de una aldea de Heraldia con sus encargos", "Earn the friendship of a Heraldia village with its jobs")),
    ("heroe", "minecraft:bell", "challenge", 150, ("Héroe de la aldea", "Hero of the Village"),
     ("Llega a ser el héroe de una aldea de Heraldia", "Become the hero of a Heraldia village")),
]


def _advancement_key(lid, part):
    return f"advancements.{NS}.encargos.{lid}.{part}"


def advancements():
    """{path: json} of the quest advancements (criterion "impossible": the Java grants them)."""
    out = {}
    parent = f"{NS}:raiz"
    for lid, emblem, frame, xp, title, desc in ADVANCEMENTS:
        out[f"encargos/{lid}"] = {
            "parent": parent,
            "criteria": {"hecho": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": emblem},
                        "title": {"translate": _advancement_key(lid, "title"), "fallback": title[0]},
                        "description": {"translate": _advancement_key(lid, "description"), "fallback": desc[0]},
                        "frame": frame},
            "requirements": [["hecho"]],
            "rewards": {"experience": xp},
        }
        parent = f"{NS}:encargos/{lid}"
    return out


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    for k, (es, en) in STATE.items():
        out["es_es"][f"{NS}.{k}"], out["en_us"][f"{NS}.{k}"] = es, en
    for lid, _, _, _, title, desc in ADVANCEMENTS:
        for i, language in enumerate(("es_es", "en_us")):
            out[language][_advancement_key(lid, "title")] = title[i]
            out[language][_advancement_key(lid, "description")] = desc[i]
    return out


def write(out, jdump):
    for route, advancement in advancements().items():
        jdump(out, f"data/{NS}/advancement/{route}.json", advancement)
