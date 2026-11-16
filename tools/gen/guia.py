"""Guía del Heraldo: el libro escrito que explica el mod a los jugadores y lleva su diario (lo arma el Java, comando/Guia).

Aquí van los textos (claves heraldia.guia.*, en es_es y en_us) y heraldia/guia.json (dentro del .jar), que dice al Java
qué páginas fijas lleva el libro y cuántas entradas caben en cada página del diario. Todo se comprueba con el mismo
cálculo de líneas que los pliegos de la crónica (botin.lineas_libro: 14 líneas de 114 px): si una página no cabe en un
idioma, la generación falla.

Páginas del libro:
  - fijas (PAGINAS): un título en negrita y su texto, en este orden;
  - el diario: el resumen (cuántas únicas has descubierto de cuántas), la lista de las descubiertas (su nombre,
    heraldia.unicas.<id>.nombre) y las pistas de las que faltan (la pista de su pliego de la crónica,
    heraldia.historia.<id>.pista: bioma y rasgo, sin nombre ni coordenadas), repartidas en páginas de
    `nombres_por_pagina` y `pistas_por_pagina` entradas (calculadas aquí con el peor caso de cada idioma).
"""
from unicas._comun import botin
import logros
import idiomas

NS = "heraldia"
CLAVE = f"{NS}.guia"
TITULO = ("Guía del Heraldo", "The Herald's Guide")   # título del libro (cadena sin traducir, máx. TITULO_MAX)
TITULO_MAX = 32                                         # WrittenBookContent.TITLE_MAX_LENGTH
AUTOR = "Heraldia"
MAX_PAGINAS = 100                                       # WrittenBookContent: máximo de páginas de un libro
MARCA = "heraldia_guia_libro"                           # custom_data {heraldia_guia_libro: "<versión del mod>"}

# (id, (título es, en), (texto es, en)). La página es «título\n\ntexto» con el título en negrita.
PAGINAS = [
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
    ("caminos", ("Los caminos", "The roads"),
     ("Senderos con farolas y puentes de madera unen las aldeas vecinas. Cerca de cada aldea, un cartel dice el nombre "
      "de la de destino y cuántos bloques faltan. Seguirlos es la forma más segura de viajar.",
      "Trails with lamp posts and wooden bridges join neighbouring villages. Near each village, a sign gives the name "
      "of the destination and how many blocks are left. Following them is the safest way to travel.")),
    ("medianas", ("Junto al camino", "By the wayside"),
     ("Entre aldea y aldea salen estructuras medianas: torres de vigía, posadas de camino, campamentos de bandidos, "
      "ermitas... Tienen botín modesto y, a veces, un pequeño reto. Cuidado con los bandidos.",
      "Between villages you will come across medium structures: watchtowers, roadside inns, bandit camps, "
      "hermitages... They hold modest loot and, now and then, a small challenge. Beware of the bandits.")),
    ("minas", ("Las minas", "The mines"),
     ("En las laderas de montes, taigas, desiertos, badlands y picos se abren bocas de mina que bajan a galerías con "
      "vías, cruces y salas. Las mayores tienen torre de extracción y un pozo con escalera. Ojo con las arañas del fondo.",
      "On the slopes of hills, taigas, deserts, badlands and peaks, mine adits lead down to galleries with rails, "
      "crossings and rooms. The largest have a headframe and a shaft with a spiral stair. Beware the spiders below.")),
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
      "guardián y su tesoro. Una estructura cuenta al entrar en ella: no basta con verla de lejos.",
      "The Heraldia advancement tab records your travels: a village of each family, every unique structure, its "
      "guardian and its treasure. A structure counts once you step inside: seeing it from afar is not enough.")),
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
    ("historia", ("La Crónica", "The Chronicle"),
     ("Cada estructura única guarda un pliego de la Crónica de los Heraldos, escrita por Ysolda, la última heraldo de "
      "la Atlántida. Cada pliego señala el siguiente: reúnelos todos y sabrás cómo acaba.",
      "Every unique structure keeps a leaf of the Chronicle of the Heralds, written by Ysolda, the last herald of "
      "Atlantis. Each leaf points to the next: gather them all and you will learn how it ends.")),
    ("diario", ("Tu diario", "Your diary"),
     ("Las páginas que siguen son tuyas: qué estructuras únicas has descubierto y pistas de las que te faltan. Para "
      "tenerlas al día, pide otra copia cuando quieras con /heraldia guia.",
      "The pages that follow are yours: which unique structures you have found and clues to the ones still missing. "
      "To bring them up to date, ask for a new copy whenever you like with /heraldia guia.")),
]

# Textos del diario y del objeto (heraldia.guia.<clave>). %s: números o componentes (nombre, pista).
DIARIO = {
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
}


def clave(k):
    return f"{CLAVE}.{k}"


def lang():
    """{"es_es": {...}, "en_us": {...}} con las páginas fijas y los textos del diario."""
    out = {"es_es": {}, "en_us": {}}
    for pid, titulo, texto in PAGINAS:
        for i, idioma in enumerate(out):
            out[idioma][clave(f"pagina.{pid}.titulo")] = titulo[i]
            out[idioma][clave(f"pagina.{pid}")] = texto[i]
    for k, textos in DIARIO.items():
        for i, idioma in enumerate(out):
            out[idioma][clave(k)] = textos[i]
    return out


def lineas_titulo(titulo):
    """Líneas de un título en negrita (cada carácter, 1 px más ancho)."""
    return 1 if botin.ancho(titulo) + len(titulo) <= botin.LIBRO_ANCHO else 2


def lineas_pagina(titulo, texto):
    """Líneas de una página «título (negrita)\\n\\ntexto»."""
    return lineas_titulo(titulo) + 1 + botin.lineas_libro(texto)


def _entradas(modules, traducciones=None):
    """Por idioma (0 = es, 1 = en y luego cada traducción, {código: textos}): [(nombre de cada única)], [(pista de cada
    única)] con el formato de su entrada."""
    nombres = [[DIARIO["descubierta"][i] % logros.unique_name(sid, m)[i] for sid, m in modules] for i in (0, 1)]
    pistas = [[DIARIO["pista"][i] % m.HISTORIA["pista"][i] for sid, m in modules] for i in (0, 1)]
    for t in (traducciones or {}).values():
        nombres.append([idiomas.formatear(t[clave("descubierta")], [t[logros.name_key(sid)]]) for sid, _ in modules])
        pistas.append([idiomas.formatear(t[clave("pista")], [t[botin.historia_clave(sid) + ".pista"]]) for sid, _ in modules])
    return nombres, pistas


def _cabecera(k, traducciones):
    """El título de una página del diario en todos los idiomas."""
    return list(DIARIO[k]) + [t[clave(k)] for t in (traducciones or {}).values()]


def por_pagina(cabecera, entradas):
    """Entradas por página: las que caben tras la cabecera (en negrita y una línea en blanco) con la más larga de todas."""
    libres = botin.LIBRO_LINEAS - max(lineas_titulo(c) for c in cabecera) - 1
    peor = max(botin.lineas_libro(e) for e in entradas)
    return libres // peor


def datos(modules, traducciones=None):
    """Lo que lee el Java (heraldia/guia.json): páginas fijas en orden y entradas por página del diario (con el peor caso
    de todos los idiomas: los base y las traducciones, {código: textos})."""
    nombres, pistas = _entradas(modules, traducciones)
    return {
        "paginas": [pid for pid, _, _ in PAGINAS],
        "nombres_por_pagina": por_pagina(_cabecera("descubiertas", traducciones), sum(nombres, [])),
        "pistas_por_pagina": por_pagina(_cabecera("pistas", traducciones), sum(pistas, [])),
        "marca": MARCA,
        "autor": AUTOR,
    }


def paginas_max(modules, traducciones=None):
    """Páginas del libro en el peor caso (todas descubiertas o ninguna): fijas + resumen + listas."""
    d, n = datos(modules, traducciones), len(modules)
    listas = max(-(-n // d["nombres_por_pagina"]), -(-n // d["pistas_por_pagina"]))
    return len(PAGINAS) + 1 + listas


def _textos_por_idioma(traducciones):
    """[(nombre del idioma, {clave: texto} de la guía)] de los base y de cada traducción."""
    base = lang()
    return [("es", base["es_es"]), ("en", base["en_us"])] + [(c, t) for c, t in (traducciones or {}).items()]


def errores(modules, traducciones=None):
    """[] si todo cabe en cada idioma: cada página fija y el resumen (con números de dos cifras y la frase más larga),
    el título del libro (el nombre de la guía), al menos una entrada por página del diario y el total de páginas.
    `traducciones`: {código: textos} de los idiomas que no son es/en (idiomas.completar)."""
    e = []
    for idioma, t in _textos_por_idioma(traducciones):
        for pid, _, _ in PAGINAS:
            titulo, texto = t[clave(f"pagina.{pid}.titulo")], t[clave(f"pagina.{pid}")]
            if lineas_pagina(titulo, texto) > botin.LIBRO_LINEAS:
                e.append(f"guía: la página «{pid}» ({idioma}) no cabe: "
                         f"{lineas_pagina(titulo, texto)} de {botin.LIBRO_LINEAS} líneas")
            if lineas_titulo(titulo) > 1:
                e.append(f"guía: el título de la página «{pid}» ({idioma}) no cabe en una línea: {titulo}")
        for cola in ("resumen.ninguna", "resumen.faltan", "resumen.todas"):
            texto = idiomas.formatear(t[clave("resumen")], ["99", "99"]) + "\n\n" + idiomas.formatear(t[clave(cola)], ["99"])
            if lineas_pagina(t[clave("resumen.titulo")], texto) > botin.LIBRO_LINEAS:
                e.append(f"guía: el resumen con «{cola}» ({idioma}) no cabe")
        if not 1 <= len(t[clave("nombre")]) <= TITULO_MAX:
            e.append(f"guía: el título «{t[clave('nombre')]}» ({idioma}) pasa de {TITULO_MAX} caracteres")
    for i in (0, 1):
        if len(TITULO[i]) > TITULO_MAX:
            e.append(f"guía: el título «{TITULO[i]}» pasa de {TITULO_MAX} caracteres")
    d = datos(modules, traducciones)
    if d["nombres_por_pagina"] < 1 or d["pistas_por_pagina"] < 1:
        e.append(f"guía: una entrada del diario no cabe en una página ({d})")
    elif paginas_max(modules, traducciones) > MAX_PAGINAS:
        e.append(f"guía: {paginas_max(modules, traducciones)} páginas, más de {MAX_PAGINAS}")
    return e


def write(out, modules, jdump, traducciones=None):
    """Escribe heraldia/guia.json y devuelve sus textos; falla si algo no cabe en el libro en algún idioma."""
    e = errores(modules, traducciones)
    if e:
        raise SystemExit("\n".join(e))
    jdump(out, f"{NS}/guia.json", datos(modules, traducciones))
    return lang()
