"""Herald's Guide: the written book that explains the mod to players and carries their journal (built by the Java side, comando/Guia).

Here are the texts (keys heraldia.guia.*, in es_es and en_us) and heraldia/guide.json (inside the .jar), which tells the Java side
which fixed pages the book carries and how many entries fit on each page of the journal. Everything is checked with the same
line calculation as the chronicle sheets (chest_loot.book_lines: 14 lines of 114 px): if a page does not fit in a
language, generation fails.

Pages of the book:
  - fixed (PAGES): a bold title and its text, in this order;
  - the arena hall of fame (T41, if enabled): the previous week's champions and the records of each
    mode, on two pages after the journal summary (built by arena/Fama; errores_fama checks the worst case);
  - the journal: the summary (how many unique structures you have discovered out of how many), the list of the discovered ones (their name,
    heraldia.unicas.<id>.nombre) and the hints for the missing ones (the hint from their chronicle sheet,
    heraldia.historia.<id>.pista: biome and trait, no name or coordinates), spread over pages of
    `nombres_por_pagina` and `pistas_por_pagina` entries (computed here with the worst case of each language).
"""
from uniques._common import chest_loot
import advancements
import languages

NS = "heraldia"
KEY = f"{NS}.guia"
TITLE = ("Guía del Heraldo", "The Herald's Guide")   # book title (untranslated string, max TITLE_MAX)
TITLE_MAX = 32                                         # WrittenBookContent.TITLE_MAX_LENGTH
AUTHOR = "Heraldia"
MAX_PAGES = 100                                       # WrittenBookContent: maximum number of pages in a book
MARK = "heraldia_guia_libro"                           # custom_data {heraldia_guia_libro: "<mod version>"}

# (id, (title es, en), (text es, en)). The page is "title\n\ntext" with the title in bold.
PAGES = [
    ("bienvenida", ("Guía del Heraldo", "The Herald's Guide"),
     ("Bienvenido, viajero. Este mundo guarda más de lo que parece: aldeas enormes, caminos, ruinas con historia y "
      "tesoros con guardián. Esta guía te cuenta qué buscar y, al final, lleva el diario de lo que has descubierto.",
      "Welcome, traveller. This world holds more than meets the eye: huge villages, roads, ruins with a story and "
      "guarded treasures. This guide tells you what to look for and, at the end, keeps a diary of what you have found.")),
    ("aldeas", ("Las aldeas", "The villages"),
     ("Las aldeas de Heraldia son grandes y de doce familias, cada una con el estilo de su bioma: plaza con fuente y "
      "campana, iglesia, mercado, taberna, herrería, biblioteca, granja y posada, y unas veinte casas o más.",
      "Heraldia villages are large and come in twelve families, each in the style of its biome: a square with a "
      "fountain and a bell, a church, market, tavern, smithy, library, farm and inn, and twenty houses or more.")),
    ("vida", ("Vida en la aldea", "Village life"),
     ("Cada estilo tiene tratos propios. En la plaza hay un tablón de encargos: el alguacil paga cosechas, leña y "
      "limpiar los caminos de monstruos. Y los cartógrafos venden mapas de las únicas.",
      "Each style has trades of its own. On the square stands a job board: the bailiff pays for harvests, firewood "
      "and clearing the roads of monsters. And the cartographers sell maps of the unique structures.")),
    ("encargos", ("Encargos", "Quests"),
     ("En el atril del tablón verás de 2 a 4 encargos, que cambian cada pocos días. Pagan esmeraldas y reputación: "
      "conocido, amigo y héroe abaratan los tratos. No ataques a los vecinos. /heraldia quest.",
      "The job board lectern lists 2 to 4 quests that change every few days. They pay emeralds and reputation: known, "
      "friend and hero make trades cheaper. Do not attack the villagers. /heraldia quest.")),
    ("caminos", ("Los caminos", "The roads"),
     ("Senderos con farolas y puentes de madera unen las aldeas vecinas. Cerca de cada aldea, un cartel dice el nombre "
      "de la de destino y cuántos bloques faltan. Seguirlos es la forma más segura de viajar.",
      "Trails with lamp posts and wooden bridges join neighbouring villages. Near each village, a sign gives the name "
      "of the destination and how many blocks are left. Following them is the safest way to travel.")),
    ("caravanas", ("Caravanas", "Caravans"),
     ("Por los caminos viajan a veces mercaderes con sus llamas. Si los asaltan bandidos, defiéndelos: al llegar a su "
      "aldea te pagan esmeraldas y reputación. Si el mercader muere, la caravana se pierde.",
      "Merchants with their llamas sometimes travel the roads. If bandits ambush them, defend them: when they reach "
      "their village they pay you emeralds and reputation. If the merchant dies, the caravan is lost.")),
    ("medianas", ("Junto al camino", "By the wayside"),
     ("Entre aldea y aldea salen estructuras medianas: torres de vigía, posadas de camino, campamentos de bandidos, "
      "ermitas... Tienen botín modesto y, a veces, un pequeño reto. Cuidado con los bandidos.",
      "Between villages you will come across medium structures: watchtowers, roadside inns, bandit camps, "
      "hermitages... They hold modest loot and, now and then, a small challenge. Beware of the bandits.")),
    ("magos", ("Chozas de mago", "Wizard's huts"),
     ("En bosques, pantanos, taigas, montes, cerezales y desiertos viven magos en chozas con jardín de hierbas. "
      "Venden pociones, frascos y libros. Pero alguno es un mago malvado disfrazado: si se descubre, prepárate.",
      "In forests, swamps, taigas, hills, cherry groves and deserts, wizards live in huts with herb gardens. They "
      "sell potions, flasks and books. But some are evil wizards in disguise: if one unmasks, be ready.")),
    ("minas", ("Las minas", "The mines"),
     ("En las laderas de montes, taigas, desiertos, badlands y picos se abren bocas de mina que bajan a galerías con "
      "vías, cruces y salas. Las mayores tienen torre de extracción y un pozo con escalera. Ojo con las arañas del fondo.",
      "On the slopes of hills, taigas, deserts, badlands and peaks, mine adits lead down to galleries with rails, "
      "crossings and rooms. The largest have a headframe and a shaft with a spiral stair. Beware the spiders below.")),
    ("costa", ("La costa", "The coast"),
     ("En la costa hay faros con la luz siempre encendida, la casa del farero y un embarcadero. En playas y bajíos "
      "yacen galeones partidos: aún queda algo en la bodega y en el camarote del capitán.",
      "Lighthouses stand on the coast with their light always lit, the keeper's house and a jetty. On beaches and "
      "shallows lie broken galleons: their hold and the captain's cabin still hold something.")),
    ("unicas", ("Las únicas", "Unique structures"),
     ("Muy raras, cada una en su bioma: un castillo, una catedral, una ciudadela enana, un galeón varado... Dentro hay "
      "salas ocultas, puzles, trampas, un guardián con nombre y su cámara del tesoro.",
      "Very rare, each in its own biome: a castle, a cathedral, a dwarven citadel, a stranded galleon... Inside are "
      "hidden rooms, puzzles, traps, a named guardian and its treasure chamber.")),
    ("atlantida", ("La Atlántida", "Atlantis"),
     ("Solo hay una en el mundo: una ciudad enorme hundida en el océano profundo, con salas secas, tres sellos con sus "
      "llaves y el Guardián de Poseidón, que custodia el mayor tesoro de Heraldia.",
      "There is only one in the world: a vast city sunk in the deep ocean, with dry halls, three seals with their keys "
      "and the Guardian of Poseidon, who keeps the greatest treasure of Heraldia.")),
    ("isla", ("La isla corsaria", "The corsair's isle"),
     ("En mar abierto, lejos de la costa, un islote esconde el fuerte de Roque Salitre y su puerto. Bajo el cerro, "
      "unas cuevas marinas a las que se entra en barca por el acantilado.",
      "Out at sea, far from the coast, an islet hides the fort of Roque Salitre and its harbour. Beneath the hill lie "
      "sea caves, reached by boat through the cliff.")),
    ("arena", ("La arena", "The arena"),
     ("Cerca del spawn hay una arena de oleadas: entra en el ruedo y toca la campana. Cada oleada trae más monstruos y "
      "más fuertes, y cada cinco, un campeón. Si caes en el ruedo, conservas tu inventario. Búscala con /heraldia arena.",
      "Near spawn stands a wave arena. Step into the ring and ring the bell: each wave brings more and stronger monsters, "
      "and every fifth, a champion. If you fall in the ring, you keep your inventory. Where it is: /heraldia arena.")),
    ("logros", ("Logros", "Advancements"),
     ("La pestaña Heraldia de los logros recoge tus viajes: una aldea de cada familia, cada estructura única, su "
      "guardián y su tesoro. Una estructura cuenta al entrar en ella. Lo que ha hallado todo el servidor: /heraldia status.",
      "The Heraldia advancement tab records your travels: a village of each family, every unique structure, its "
      "guardian and its treasure. A structure counts once you step inside. What the whole server has found: /heraldia status.")),
    ("trofeos", ("Trofeos", "Trophies"),
     ("Cada guardián con nombre suelta su trofeo, un objeto con nombre e historia, si lo derrota un jugador. Reúnelos "
      "todos para completar la Sala de trofeos.",
      "Every named guardian drops its trophy, an item with a name and a story, when a player defeats it. Collect them "
      "all to complete the Hall of Trophies.")),
    ("jefes", ("Combates de jefe", "Boss fights"),
     ("Los guardianes con nombre pelean por fases: al perder vida se enfurecen (más rápidos y fuertes un rato) y llaman "
      "a refuerzos propios de su estructura. Mientras dura el combate verás su barra de jefe.",
      "Named guardians fight in phases: as they lose health they become enraged (faster and stronger for a while) and "
      "call for reinforcements that suit their structure. While the fight lasts you will see their boss bar.")),
    ("mapas", ("Mapas del tesoro", "Treasure maps"),
     ("Cada mapa marca la estructura única más cercana de su tipo. Salen en los cofres épicos de las aldeas y los "
      "venden los cartógrafos de Heraldia.",
      "Each map marks the nearest unique structure of its kind. They turn up in the epic chests of the villages and "
      "Heraldia cartographers sell them.")),
    ("tesoro", ("Caza del tesoro", "Treasure hunt"),
     ("A veces un cofre guarda un fragmento de mapa del tesoro. Úsalo para descifrarlo: se volverá un mapa con una "
      "marca. Ve hasta ella y úsalo otra vez. Cada marca lleva a la siguiente; la última, al cofre que enterró Ysolda.",
      "Now and then a chest holds a treasure map fragment. Use it to decipher it and it becomes a map with a mark. Go "
      "there and use it again: each mark leads to the next, and the last to the chest Ysolda buried.")),
    ("historia", ("La Crónica", "The Chronicle"),
     ("Cada estructura única guarda un pliego de la Crónica de los Heraldos, escrita por Ysolda, la última heraldo de "
      "la Atlántida. Cada pliego señala el siguiente: reúnelos todos y sabrás cómo acaba.",
      "Every unique structure keeps a leaf of the Chronicle of the Heralds, written by Ysolda, the last herald of "
      "Atlantis. Each leaf points to the next: gather them all and you will learn how it ends.")),
    ("diario", ("Tu diario", "Your diary"),
     ("Las páginas que siguen son tuyas: qué estructuras únicas has descubierto y pistas de las que te faltan. Para "
      "tenerlas al día, pide otra copia cuando quieras con /heraldia guide.",
      "The pages that follow are yours: which unique structures you have found and clues to the ones still missing. "
      "To bring them up to date, ask for a new copy whenever you like with /heraldia guide.")),
]

# Texts of the journal and the item (heraldia.guia.<key>). %s: numbers or components (name, hint).
JOURNAL = {
    "nombre": ("Guía del Heraldo", "The Herald's Guide"),
    "lore": ("Edición de Heraldia %s", "Heraldia edition %s"),
    "resumen.titulo": ("Tu diario", "Your diary"),
    "resumen": ("Has descubierto %s de las %s estructuras únicas de este mundo.",
                "You have discovered %s of the %s unique structures in this world."),
    "resumen.ninguna": ("Aún no has entrado en ninguna. Las pistas de las páginas siguientes te dirán por dónde empezar.",
                        "You have not entered any yet. The clues on the next pages will tell you where to start."),
    "resumen.faltan": ("Te faltan %s. Sigue las pistas de las páginas siguientes.",
                       "%s still to go. Follow the clues on the next pages."),
    "resumen.todas": ("¡Las has descubierto todas! Ahora busca sus trofeos y los pliegos de la crónica.",
                      "You have found them all! Now seek their trophies and the leaves of the chronicle."),
    "descubiertas": ("Descubiertas", "Discovered"),
    "descubierta": ("• %s", "• %s"),
    "pistas": ("Pistas", "Clues"),
    "pista": ("• Busca en %s.", "• Look in %s."),
    "entregada": ("Te damos la Guía del Heraldo: ábrela para saber qué te espera en este mundo.",
                  "Here is the Herald's Guide: open it to learn what awaits you in this world."),
    "copia": ("Aquí tienes una copia al día de la Guía del Heraldo.", "Here is an up-to-date copy of the Herald's Guide."),
    # T41: the arena hall of fame (two pages after the summary, if the arena is enabled; built by arena/Fama)
    "fama.titulo": ("Salón de la fama", "Hall of fame"),
    "fama.ninguno": ("Aún no hay campeones de la arena. Quien acabe esta semana en cabeza de cada modo será el campeón de "
                     "la que viene: /heraldia arena leaderboard.",
                     "There are no arena champions yet. Whoever ends this week on top of each mode will be next week's "
                     "champion: /heraldia arena leaderboard."),
    "fama.semana": ("Campeones de la arena de la semana del %s:", "Arena champions of the week of %s:"),
    "fama.entrada": ("• %s: %s, %s", "• %s: %s, %s"),
    "fama.vacio": ("• %s: nadie", "• %s: nobody"),
    "records.titulo": ("Récords", "Records"),
    "records.intro": ("La mejor marca de siempre en cada modo de la arena:", "The best result ever in each arena mode:"),
}
FAME_PAGES = 2                                         # hall of fame pages (Java: arena/Fama.paginas)


def key(k):
    return f"{KEY}.{k}"


def lang():
    """{"es_es": {...}, "en_us": {...}} with the fixed pages and the journal texts."""
    out = {"es_es": {}, "en_us": {}}
    for pid, title, text in PAGES:
        for i, language in enumerate(out):
            out[language][key(f"pagina.{pid}.titulo")] = title[i]
            out[language][key(f"pagina.{pid}")] = text[i]
    for k, texts in JOURNAL.items():
        for i, language in enumerate(out):
            out[language][key(k)] = texts[i]
    return out


def title_lines(title):
    """Lines of a bold title (each character, 1 px wider)."""
    return 1 if chest_loot.width(title) + len(title) <= chest_loot.BOOK_WIDTH else 2


def page_lines(title, text):
    """Lines of a page "title (bold)\\n\\ntext"."""
    return title_lines(title) + 1 + chest_loot.book_lines(text)


def _entries(modules, translations=None):
    """Per language (0 = es, 1 = en and then each translation, {code: texts}): [(name of each unique structure)], [(hint of each unique
    structure)] with the format of its entry."""
    names = [[JOURNAL["descubierta"][i] % advancements.unique_name(sid, m)[i] for sid, m in modules] for i in (0, 1)]
    clues = [[JOURNAL["pista"][i] % m.STORY["pista"][i] for sid, m in modules] for i in (0, 1)]
    for t in (translations or {}).values():
        names.append([languages.format_text(t[key("descubierta")], [t[advancements.name_key(sid)]]) for sid, _ in modules])
        clues.append([languages.format_text(t[key("pista")], [t[chest_loot.story_key(sid) + ".pista"]]) for sid, _ in modules])
    return names, clues


def _header(k, translations):
    """The title of a journal page in all languages."""
    return list(JOURNAL[k]) + [t[key(k)] for t in (translations or {}).values()]


def per_page(header, entrances):
    """Entries per page: those that fit after the header (in bold and a blank line) with the longest of all."""
    free_cells = chest_loot.BOOK_LINES - max(title_lines(c) for c in header) - 1
    worst = max(chest_loot.book_lines(e) for e in entrances)
    return free_cells // worst


def dataset(modules, translations=None):
    """What the Java side reads (heraldia/guide.json): fixed pages in order and entries per journal page (with the worst case
    of all languages: the base ones and the translations, {code: texts})."""
    names, clues = _entries(modules, translations)
    return {
        "paginas": [pid for pid, _, _ in PAGES],
        "nombres_por_pagina": per_page(_header("descubiertas", translations), sum(names, [])),
        "pistas_por_pagina": per_page(_header("pistas", translations), sum(clues, [])),
        "marca": MARK,
        "autor": AUTHOR,
    }


def pages_max(modules, translations=None):
    """Pages of the book in the worst case (all discovered or none): fixed + summary + lists."""
    d, n = dataset(modules, translations), len(modules)
    lists = max(-(-n // d["nombres_por_pagina"]), -(-n // d["pistas_por_pagina"]))
    return len(PAGES) + 1 + FAME_PAGES + lists


def fame_errors(translations=None):
    """[] if the hall of fame pages fit in each language in the worst case: the three modes with the widest
    player name (16 "W") and the longest record of each mode."""
    import arena_waves
    a = arena_waves.lang()
    e = []
    worst_name = "W" * 16
    for language, t in _texts_by_language(translations):
        t = {**(a["es_es"] if language == "es" else a["en_us"]), **t}
        modes = [t[f"{NS}.arena.modo.{m}"] for m in arena_waves.MODES]
        points = [languages.format_text(t[f"{NS}.arena.puntos.oleadas"], ["999"]),
                  languages.format_text(t[f"{NS}.arena.puntos.tiempo"], ["59:59", "99"]),
                  languages.format_text(t[f"{NS}.arena.puntos.parcial"], ["99", "99"])]
        entrance = [languages.format_text(t[key("fama.entrada")], [m, worst_name, p]) for m in modes for p in points]
        worst = max(chest_loot.book_lines(x) for x in entrance)
        pages = {
            "fama": (t[key("fama.titulo")], languages.format_text(t[key("fama.semana")], ["99/99/9999"]), 3 * worst),
            "records": (t[key("records.titulo")], t[key("records.intro")], 3 * worst),
        }
        for pid, (title, intro, lines) in pages.items():
            n = title_lines(title) + 1 + chest_loot.book_lines(intro) + lines
            if n > chest_loot.BOOK_LINES or title_lines(title) > 1:
                e.append(f"guía: la página del salón de la fama «{pid}» ({language}) no cabe: {n} de {chest_loot.BOOK_LINES} líneas")
        if page_lines(t[key("fama.titulo")], t[key("fama.ninguno")]) > chest_loot.BOOK_LINES:
            e.append(f"guía: la página del salón de la fama sin campeones ({language}) no cabe")
    return e


def _texts_by_language(translations):
    """[(language name, {key: text} of the guide)] of the base languages and of each translation."""
    base = lang()
    return [("es", base["es_es"]), ("en", base["en_us"])] + [(c, t) for c, t in (translations or {}).items()]


def errors(modules, translations=None):
    """[] if everything fits in each language: each fixed page and the summary (with two-digit numbers and the longest phrase),
    the book title (the guide's name), at least one entry per journal page and the total number of pages.
    `translations`: {code: texts} of the languages other than es/en (languages.complete)."""
    e = []
    for language, t in _texts_by_language(translations):
        for pid, _, _ in PAGES:
            title, text = t[key(f"pagina.{pid}.titulo")], t[key(f"pagina.{pid}")]
            if page_lines(title, text) > chest_loot.BOOK_LINES:
                e.append(f"guía: la página «{pid}» ({language}) no cabe: "
                         f"{page_lines(title, text)} de {chest_loot.BOOK_LINES} líneas")
            if title_lines(title) > 1:
                e.append(f"guía: el título de la página «{pid}» ({language}) no cabe en una línea: {title}")
        for queue in ("resumen.ninguna", "resumen.faltan", "resumen.todas"):
            text = languages.format_text(t[key("resumen")], ["99", "99"]) + "\n\n" + languages.format_text(t[key(queue)], ["99"])
            if page_lines(t[key("resumen.titulo")], text) > chest_loot.BOOK_LINES:
                e.append(f"guía: el resumen con «{queue}» ({language}) no cabe")
        if not 1 <= len(t[key("nombre")]) <= TITLE_MAX:
            e.append(f"guía: el título «{t[key('nombre')]}» ({language}) pasa de {TITLE_MAX} caracteres")
    e += fame_errors(translations)
    import arena_waves
    e += arena_waves.text_errors(translations)          # T41: the lines of the hall of fame signs
    for i in (0, 1):
        if len(TITLE[i]) > TITLE_MAX:
            e.append(f"guía: el título «{TITLE[i]}» pasa de {TITLE_MAX} caracteres")
    d = dataset(modules, translations)
    if d["nombres_por_pagina"] < 1 or d["pistas_por_pagina"] < 1:
        e.append(f"guía: una entrada del diario no cabe en una página ({d})")
    elif pages_max(modules, translations) > MAX_PAGES:
        e.append(f"guía: {pages_max(modules, translations)} páginas, más de {MAX_PAGES}")
    return e


def write(out, modules, jdump, translations=None):
    """Writes heraldia/guide.json and returns its texts; fails if anything does not fit in the book in some language."""
    e = errors(modules, translations)
    if e:
        raise SystemExit("\n".join(e))
    jdump(out, f"{NS}/guia.json", dataset(modules, translations))
    return lang()
