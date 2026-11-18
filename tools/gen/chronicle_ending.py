"""The end of the Chronicle of the Heralds (docs/STORY.md, "The end"): what a player gets when every guardian of the main
world's unique structures has fallen to them (built by the Java side, chronicle/ChronicleEnding).

Here are the texts (keys heraldia.cronica.*, in es_es and en_us; the 6 translations in tools/gen/languages/<code>.json), the two
advancements and heraldia/cronica_final.json (inside the .jar), which tells the Java side the pages of the last leaf in order.

  cronica/final      (challenge, granted by the Java, criterion "hecho") every Overworld guardian: the last leaf (a written book by
                     Ysolda), the title "Herald of Atlantis" and the Standard of the Heralds (a banner that can be placed)
  cronica/mas_alla   (challenge, granted by the Java) also the guardians of the Nether and the End: one more page in the last leaf

The last leaf: the fixed pages (PAGES), then the "beyond" page in one of its two forms (CODA: still to go, or done); a page is
"title (bold)\\n\\ntext" when it has a title. Everything is measured with the Chronicle leaves' line calculation
(chest_loot.book_lines: 14 lines of 114 px): if a page does not fit in some language, generation fails.
"""
from uniques._common import chest_loot
import advancements as lg
import guide
import languages

NS = "heraldia"
KEY = f"{NS}.cronica"
MARK = "heraldia_ultimo_pliego"           # custom_data {heraldia_ultimo_pliego: 1} of the last leaf (to swap the copy)
AUTHOR = "Ysolda"
TITLE_MAX = 32                             # WrittenBookContent.TITLE_MAX_LENGTH
LORE_MAX_PX = 250                          # as treasure.LORE_MAX_PX: the game does not wrap lore
FINAL, BEYOND = "cronica/final", "cronica/mas_alla"
XP = {FINAL: 500, BEYOND: 250}

# (id, (title es, en) or None, (text es, en)): the pages of the last leaf, in order.
PAGES = [
    ("juramento", ("El último pliego", "The last leaf"),
     ("Si lees esto, el último juramento se ha roto. No lo escribí en ningún pliego que pudieras encontrar: lo guardé "
      "en la tinta misma, para que apareciera solo ante quien liberase a todos mis guardianes.",
      "If you are reading this, the last oath is broken. I wrote it on no leaf you could find: I kept it in the ink "
      "itself, so that it would appear only before whoever set all my guardians free.")),
    ("dignos", None,
     ("Nunca pedí que los vencieran. Les pedí que esperasen a alguien digno. Aquilio, Aldric, Borin, el capitán "
      "ahogado, el Rey de la Escarcha... Ninguno podía descansar hasta que alguien lo demostrara. Tú lo has demostrado.",
      "I never asked for them to be defeated. I asked them to wait for someone worthy. Aquilius, Aldric, Borin, the "
      "drowned captain, the Frost King... none could rest until someone proved it. You have.")),
    ("camino", None,
     ("El camino de vuelta nunca estuvo en los pliegos, sino en quien los siguiera. Has cruzado el mundo que mi orden "
      "dibujó, de aldea en aldea y de ruina en ruina. Ya no hacen falta mapas: el mapa eres tú.",
      "The way back was never in the leaves, but in whoever followed them. You have crossed the world my order drew, "
      "from village to village and from ruin to ruin. No more maps are needed: you are the map.")),
    ("estandarte", None,
     ("Toma el estandarte de los Heraldos: fue nuestro blasón antes de que el mar se llevara la ciudad. Álzalo donde "
      "quieras; donde ondee, la orden vuelve a existir. Desde hoy eres Heraldo de la Atlántida.\n\n— Ysolda",
      "Take the standard of the Heralds: it was our coat of arms before the sea took the city. Raise it wherever you "
      "will; where it flies, the order lives again. From this day you are a Herald of Atlantis.\n\n— Ysolda")),
]
# The "beyond" page (the Nether and End guardians, optional): while some still keep watch, and once they have all fallen.
CODA = {
    "pendiente": (None,
                  ("Una cosa más. Dos pliegos los llevé más allá del mundo: uno al fuego, tras un heraldo perdido, y otro "
                   "al vacío, más allá del dragón. Sus guardianes aún velan. No hace falta que vayas. Pero, si vas, "
                   "vuelve a leer esto.",
                   "One more thing. Two leaves I carried beyond the world: one into the fire, on the trail of a lost "
                   "herald, the other into the void, beyond the dragon. Their guardians still keep watch. You need not "
                   "go. But if you do, read this again.")),
    "hecho": (("Más allá del mapa", "Beyond the map"),
              ("Has ido más lejos que yo. El mariscal ya no guarda la frontera del fuego y el hierofante, por fin, ha "
               "cerrado los ojos. Ningún heraldo llegó tan lejos: ningún mapa de la orden alcanza adonde tú has estado.",
               "You have gone further than I did. The marshal no longer guards the border of fire, and the hierophant "
               "has at last closed his eyes. No herald ever went so far: no map of the order reaches where you have "
               "been.")),
}

# Other texts (heraldia.cronica.<key>). %s: a player's name, numbers or components (structure names, a command button).
TEXTS = {
    "libro": ("Crónica: el último pliego", "Chronicle: the last leaf"),      # book title (plain string, <= TITLE_MAX)
    "libro.lore": ("Escrito con la tinta que el agua no borra", "Written in the ink that water cannot wash away"),
    "titulo": ("Heraldo de la Atlántida", "Herald of Atlantis"),             # the player's title
    "titulo.subtitulo": ("La Crónica de los Heraldos se cierra", "The Chronicle of the Heralds is closed"),
    "anuncio": ("El último juramento se ha roto. Ysolda te deja su último pliego y el estandarte de los Heraldos.",
                "The last oath is broken. Ysolda leaves you her last leaf and the standard of the Heralds."),
    "mas_alla": ("Más allá del mapa: tu último pliego tiene una página nueva.",
                 "Beyond the map: your last leaf has a new page."),
    "estandarte": ("Estandarte de los Heraldos", "Standard of the Heralds"),
    "estandarte.lore": ("Blasón de la orden de la Atlántida", "Arms of the Order of Atlantis"),
    "estandarte.alzado": ("Alzado por %s", "Raised by %s"),
    # /heraldia journal: the Chronicle line of the summary and its detail (/heraldia journal chronicle)
    "diario.linea": ("Crónica: guardianes vencidos", "Chronicle: guardians defeated"),
    "diario.titulo_jugador": ("✦ %s, Heraldo de la Atlántida", "✦ %s, Herald of Atlantis"),
    "diario.vencidos": ("Vencidos (%s):", "Defeated (%s):"),
    "diario.quedan": ("Aún velan (%s):", "Still keeping watch (%s):"),
    "diario.mas_alla": ("Más allá del mapa (opcional): %s/%s", "Beyond the map (optional): %s/%s"),
    "diario.cerrada": ("La Crónica está cerrada: eres Heraldo de la Atlántida.",
                       "The Chronicle is closed: you are a Herald of Atlantis."),
    "diario.abierta": ("Cuando caigan todos, la Crónica se cerrará. Cuenta el guardián que derrotes y el que caiga "
                       "contigo cerca.",
                       "When they have all fallen, the Chronicle will close. A guardian counts when you defeat it or when "
                       "it falls with you nearby."),
    "diario.leer": ("[Leer el último pliego]", "[Read the last leaf]"),
    "copia": ("Aquí tienes una copia del último pliego.", "Here is a copy of the last leaf."),
    "sin_cerrar": ("La Crónica aún no se ha cerrado: te quedan %s guardianes.",
                   "The Chronicle is not closed yet: %s guardians still keep watch."),
    "desactivado": ("El final de la Crónica está desactivado en este servidor.",
                    "The end of the Chronicle is turned off on this server."),
}

ADVANCEMENTS = {
    FINAL: {"icono": "minecraft:blue_banner", "padre": "raiz",
            "titulo": ("Heraldo de la Atlántida", "Herald of Atlantis"),
            "descripcion": ("Derrota a los guardianes de todas las estructuras únicas del mundo principal y cierra la Crónica",
                            "Defeat the guardians of every unique structure in the main world and close the Chronicle")},
    BEYOND: {"icono": "minecraft:ender_eye", "padre": FINAL,
             "titulo": ("Más allá del mapa", "Beyond the Map"),
             "descripcion": ("Derrota también a los guardianes de las estructuras únicas del Nether y del End",
                             "Defeat the guardians of the Nether and End unique structures as well")},
}


def key(k):
    return f"{KEY}.{k}"


def page_key(pid, part=None):
    return key(f"pagina.{pid}" + (f".{part}" if part else ""))


def _pages():
    """[(id, title or None, text)] of every page that can appear (the fixed ones and both codas)."""
    return PAGES + [(f"coda.{k}", t, x) for k, (t, x) in CODA.items()]


def lang():
    """{"es_es": {...}, "en_us": {...}} with the pages, the other texts and the advancements' texts."""
    out = {"es_es": {}, "en_us": {}}
    for i, language in enumerate(out):
        for pid, title, text in _pages():
            if title:
                out[language][page_key(pid, "titulo")] = title[i]
            out[language][page_key(pid)] = text[i]
        for k, texts in TEXTS.items():
            out[language][key(k)] = texts[i]
        for path, d in ADVANCEMENTS.items():
            out[language][lg.key(path, "title")] = d["titulo"][i]
            out[language][lg.key(path, "description")] = d["descripcion"][i]
    return out


def advancements():
    """{path: advancement}: both granted by the Java side (criterion "hecho", trigger impossible)."""
    return {path: lg.advancement(d["padre"], d["icono"], lg.comp(lg.key(path, "title"), d["titulo"][0]),
                                 lg.comp(lg.key(path, "description"), d["descripcion"][0]),
                                 {"hecho": {"trigger": "minecraft:impossible"}}, frame="challenge", xp=XP[path])
            for path, d in ADVANCEMENTS.items()}


def dataset():
    """What the Java side reads (heraldia/cronica_final.json): the fixed pages in order, which of them have a title, the codas
    and the marks."""
    return {
        "paginas": [pid for pid, _, _ in PAGES],
        "con_titulo": [pid for pid, title, _ in _pages() if title],
        "coda": {k: f"coda.{k}" for k in CODA},
        "marca": MARK,
        "autor": AUTHOR,
        "logros": {"final": FINAL, "mas_alla": BEYOND},
    }


def _texts_by_language(translations):
    base = lang()
    return [("es", base["es_es"]), ("en", base["en_us"])] + [(c, t) for c, t in (translations or {}).items()]


def errors(translations=None):
    """[] if everything fits in each language: every page (14 lines, its title on one line), the book title (32 characters)
    and the banner's lore (with the widest player name, 16 "W")."""
    e = []
    for language, t in _texts_by_language(translations):
        for pid, title, _ in _pages():
            body = t[page_key(pid)]
            if title:
                head = t[page_key(pid, "titulo")]
                n = guide.page_lines(head, body)
                if guide.title_lines(head) > 1:
                    e.append(f"crónica: el título de la página «{pid}» ({language}) no cabe en una línea: {head}")
            else:
                n = chest_loot.book_lines(body)
            if n > chest_loot.BOOK_LINES:
                e.append(f"crónica: la página «{pid}» ({language}) no cabe: {n} de {chest_loot.BOOK_LINES} líneas")
        if not 1 <= len(t[key("libro")]) <= TITLE_MAX:
            e.append(f"crónica: el título del libro «{t[key('libro')]}» ({language}) pasa de {TITLE_MAX} caracteres")
        for k, args in (("estandarte.lore", []), ("estandarte.alzado", ["W" * 16]), ("libro.lore", [])):
            if chest_loot.width(languages.format_text(t[key(k)], args)) > LORE_MAX_PX:
                e.append(f"crónica: la línea «{k}» ({language}) es demasiado larga")
    return e


def write(out, jdump):
    """The advancements and heraldia/cronica_final.json."""
    for path, adv in advancements().items():
        jdump(out, f"data/{NS}/advancement/{path}.json", adv)
    jdump(out, f"{NS}/cronica_final.json", dataset())
