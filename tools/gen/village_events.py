"""Village events (market day, wedding, funeral, festival): texts only. The logic is in Java (events/): where an event is
laid out in the square (Layout), when it starts and ends (Rules), what is saved (Record) and the game side (VillageEvents).
What the figures say goes through the villagers' line system: pools event.<kind>.* in tools/gen/dialogue/<code>/events.json.

Keys:
  heraldia.eventos.<kind>.nombre     the event's name (in the operator command's replies)
  heraldia.eventos.<kind>.anuncio    told to the players within 160 blocks when it starts (%s = the village's name)
  heraldia.eventos.<kind>.fin        told to those nearby when it ends (%s = the village)
  heraldia.eventos.<kind>.dispersa   told to those nearby when someone hurts one of its figures (%s = the village)
  heraldia.eventos.boda.regalo / funeral.regalo   the hint after a figure asks for a gift (wedding and funeral only)
  heraldia.eventos.figura.<role>     the names floating over the main figures
  heraldia.eventos.*                 /heraldia event (operators)
The arguments (%s) are supplied by the Java side (events/VillageEvents): do not change their order without changing it there.
"""
NS = "heraldia"
K = f"{NS}.eventos"
KINDS = ("market", "wedding", "funeral", "festival")
TEXTS = {
    "market.nombre": ("día de mercado", "market day"),
    "wedding.nombre": ("boda", "wedding"),
    "funeral.nombre": ("funeral", "funeral"),
    "festival.nombre": ("fiesta", "festival"),
    "market.anuncio": ("Hoy es día de mercado en %s: hay puestos en la plaza.",
                       "It is market day in %s: there are stalls in the square."),
    "wedding.anuncio": ("Repican las campanas de %s: hay boda en la plaza.",
                        "The bells of %s are ringing: there is a wedding in the square."),
    "funeral.anuncio": ("La campana de %s dobla despacio: hay un funeral en la plaza.",
                        "The bell of %s tolls slowly: there is a funeral in the square."),
    "festival.anuncio": ("Suena música en %s: hay fiesta en la plaza.",
                         "There is music in %s: a festival is on in the square."),
    "market.fin": ("Los mercaderes de %s recogen sus puestos.", "The traders of %s pack up their stalls."),
    "wedding.fin": ("Los novios y sus invitados se van de la plaza de %s.", "The newlyweds and their guests leave the square of %s."),
    "funeral.fin": ("El cortejo deja la plaza de %s en silencio.", "The mourners leave the square of %s in silence."),
    "festival.fin": ("La fiesta de %s se acaba: la música calla.", "The festival in %s is over: the music falls silent."),
    "market.dispersa": ("¡Han atacado a un mercader! El mercado de %s se deshace.",
                        "Someone has attacked a trader! The market in %s breaks up."),
    "wedding.dispersa": ("¡Han atacado a un invitado! La boda de %s se deshace entre gritos.",
                         "Someone has attacked a guest! The wedding in %s breaks up in uproar."),
    "funeral.dispersa": ("¡Han atacado a un doliente! El funeral de %s se deshace.",
                         "Someone has attacked a mourner! The funeral in %s breaks up."),
    "festival.dispersa": ("¡Han atacado a alguien en la fiesta! La gente de %s se va corriendo.",
                          "Someone has been attacked at the festival! The people of %s run off."),
    "wedding.regalo": ("Un regalo para los novios (unas flores, una tarta, una esmeralda...) sería bien recibido.",
                       "A gift for the couple (flowers, a cake, an emerald...) would be welcome."),
    "funeral.regalo": ("Una flor, una vela o una esmeralda para la familia sería un gesto de respeto.",
                       "A flower, a candle or an emerald for the family would be a mark of respect."),
    "figura.merchant": ("Mercader", "Market trader"),
    "figura.cleric": ("Clérigo", "Cleric"),
    "figura.bride": ("La novia", "The bride"),
    "figura.groom": ("El novio", "The groom"),
    "figura.widow": ("La viuda", "The widow"),
    "figura.musician": ("Músico", "Musician"),
    "figura.host": ("Anfitrión de la fiesta", "Festival host"),
    # /heraldia event (operators)
    "desactivados": ("Los eventos en las aldeas están desactivados en este servidor.", "Village events are disabled on this server."),
    "sin_aldea": ("No estás dentro de una aldea de Heraldia.", "You are not inside a Heraldia village."),
    "sin_plaza": ("Esta aldea no tiene plaza (se quedó sin ella al generarse): no hay sitio para un evento (%s).",
                  "This village has no square (it lost it when it was generated): there is no room for an event (%s)."),
    "sin_cargar": ("La plaza de esta aldea no está cargada del todo: acércate a ella (%s).",
                   "This village's square is not fully loaded: go closer to it (%s)."),
    "cerca": ("Estás demasiado cerca de la plaza (%s).", "You are too close to the square (%s)."),
    "ya_hay": ("Ya hay un evento en esta aldea (%s).", "There is already an event in this village (%s)."),
    "limite": ("No cabe otro evento (%s): ya hay %s en marcha y el máximo es %s.",
               "No room for another event (%s): %s are already running and the maximum is %s."),
    "no_cabe": ("No hay sitio libre en la plaza para el evento «%s»: algo lo ocupa (una construcción, el tablón, una pieza que falta).",
                "There is no free room in the square for the event “%s”: something is in the way (a build, the board, a missing piece)."),
    "creado": ("Empieza el evento «%s» en %s: %s figuras y %s bloques.", "The event “%s” starts in %s: %s figures and %s blocks."),
    "parados": ("Eventos parados: %s.", "Events stopped: %s."),
    "lista.titulo": ("Eventos en marcha: %s (máximo %s); desde el arranque han empezado %s y acabado %s",
                     "Events running: %s (maximum %s); since startup %s have started and %s have ended"),
    "lista.linea": (" - «%s» en %s: %s s de %s, %s figuras, %s bloques, plaza en %s %s %s",
                    " - “%s” in %s: %s s of %s, %s figures, %s blocks, square at %s %s %s"),
    "lista.ninguno": ("No hay ningún evento en marcha.", "No village event is running."),
    "no_figura": ("Eso no es una figura de un evento en marcha.", "That is not a figure of a running event."),
}


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    return out
