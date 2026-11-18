"""Caravans along the roads between villages (T39): texts and the advancement. The logic is in Java (caravanas/): which stretch of the canonical
route it travels (Tramo), its phases (Viaje), when it departs and what it pays (Reglas); nothing in the datapack except this.

Keys:
  heraldia.caravanas.*          what is said to players near the caravan and /heraldia caravan (operators)
  heraldia.estado.caravanas*    the lines of /heraldia status
  heraldia.viajeros.*           the wayfarers (same engine): names, the action bar line, the attack notice, the command
  heraldia.estado.viajeros*     their line of /heraldia status
  advancements.heraldia.caravanas.<id>.title/.description   the advancement (granted by the Java side, criterion "hecho")
The bandits' names are those of the bandit camp (heraldia.medianas.camp.saqueador/vindicador).
The arguments (%s) are supplied by the Java side (caravanas/Caravanas): do not change their order without changing it there.
"""
NS = "heraldia"
K = f"{NS}.caravanas"
TEXTS = {
    "mercader": ("Mercader de Heraldia", "Heraldia Merchant"),
    "sale": ("Una caravana sale de %s hacia %s por el camino.", "A caravan sets off from %s towards %s along the road."),
    "asalto": ("¡Bandidos! Defiende la caravana que va a %s.", "Bandits! Defend the caravan bound for %s."),
    "superado": ("Los bandidos han caído: la caravana sigue su camino.", "The bandits have fallen: the caravan carries on."),
    "llegada": ("La caravana ha llegado a %s. El mercader te paga %s.", "The caravan has reached %s. The merchant pays you %s."),
    "paga": ("%s esmeraldas", "%s emeralds"),
    "paga.objeto": ("%s esmeraldas y %s × %s", "%s emeralds and %s × %s"),
    "perdida": ("El mercader ha muerto: la caravana hacia %s se ha perdido.", "The merchant is dead: the caravan to %s is lost."),
    "despedida": ("La caravana hacia %s se despide y sigue sola.", "The caravan to %s takes its leave and travels on alone."),
    "desactivadas": ("Las caravanas están desactivadas en este servidor.", "Caravans are disabled on this server."),
    "sin_camino": ("No hay ningún camino de Heraldia a menos de %s bloques con un tramo en chunks cargados.",
                   "There is no Heraldia road within %s blocks with a stretch in loaded chunks."),
    "limite": ("Ya hay %s caravanas en camino (el máximo es %s).", "There are already %s caravans on the road (the maximum is %s)."),
    "buscando": ("Buscando un tramo de camino cerca...", "Looking for a stretch of road nearby..."),
    "creada": ("Caravana %s: de %s a %s, %s bloques.", "Caravan %s: from %s to %s, %s blocks."),
    "lista.titulo": ("Caravanas en camino: %s (máximo %s)", "Caravans on the road: %s (maximum %s)"),
    "lista.linea": (" - %s: de %s a %s, %s, vértice %s de %s, en %s %s %s", " - %s: from %s to %s, %s, waypoint %s of %s, at %s %s %s"),
    "lista.ninguna": ("No hay ninguna caravana en camino.", "There are no caravans on the road."),
    "fase.camino": ("en camino", "travelling"),
    "fase.asalto": ("asaltada", "under attack"),
    "asalto.forzado": ("Asalto a la caravana %s.", "Ambush on caravan %s."),
    "asalto.ninguna": ("No hay ninguna caravana en camino que se pueda asaltar.", "There is no caravan on the road that can be ambushed."),
    "limpiadas": ("Caravanas quitadas: %s (y %s entidades sueltas).", "Caravans removed: %s (and %s stray entities)."),
}
STATE = {
    "estado.caravanas.no": ("Caravanas: desactivadas.", "Caravans: disabled."),
    "estado.caravanas": ("Caravanas en camino: %s (máximo %s; salida %s %%, asalto %s %%); desde el arranque llegaron %s y "
                         "se perdieron %s",
                         "Caravans on the road: %s (maximum %s; departure %s %%, ambush %s %%); since startup %s arrived and "
                         "%s were lost"),
}
# The wayfarers (the same engine, caravanas/Wayfarers and caravanas/Wayfaring): heraldia.viajeros.*. The kind names
# (peregrino...) go inside other texts; <kind>.nombre is the entity's name; <kind>.pasa, the action bar line for the players
# nearby when it sets off (%s = where it goes: the village or, for the pilgrim, the name of its monastery or cathedral).
WAYFARERS = {
    "peregrino": ("peregrino", "pilgrim"),
    "pastor": ("pastor", "shepherd"),
    "mensajero": ("mensajero", "messenger"),
    "guardias": ("pareja de guardias", "pair of guards"),
    "cazador": ("cazador", "hunter"),
    "peregrino.nombre": ("Peregrino", "Pilgrim"),
    "pastor.nombre": ("Pastor", "Shepherd"),
    "mensajero.nombre": ("Mensajero", "Messenger"),
    "guardias.nombre": ("Guardia de %s", "Guard of %s"),
    "cazador.nombre": ("Cazador", "Hunter"),
    "peregrino.pasa": ("Un peregrino camina hacia %s.", "A pilgrim walks towards %s."),
    "pastor.pasa": ("Un pastor lleva su rebaño hacia %s.", "A shepherd drives a flock towards %s."),
    "mensajero.pasa": ("Un mensajero pasa corriendo con una carta para %s.", "A messenger runs past with a letter for %s."),
    "guardias.pasa": ("Una pareja de guardias patrulla el camino hacia %s.", "A pair of guards patrols the road towards %s."),
    "cazador.pasa": ("Un cazador vuelve a %s con su pieza.", "A hunter heads back to %s with the day's catch."),
    "atacado": ("Lo que has hecho se sabrá en %s.", "Word of this will reach %s."),
    "desactivados": ("La gente de paso está desactivada en este servidor.", "Wayfarers are disabled on this server."),
    "tipo_desactivado": ("Ese tipo de viajero (%s) está desactivado en este servidor.",
                         "That kind of wayfarer (%s) is disabled on this server."),
    "limite": ("Ya hay %s viajeros en camino (el máximo es %s).", "There are already %s wayfarers on the road (the maximum is %s)."),
    "ninguno": ("Ningún viajero encaja aquí ahora (la zona, la hora o las opciones).",
                "No wayfarer fits here right now (the area, the time of day or the options)."),
    "sin_santuario": ("No hay ningún monasterio ni catedral a menos de %s bloques por este camino: el peregrino no tiene adónde ir.",
                      "There is no monastery or cathedral within %s blocks along this road: the pilgrim has nowhere to go."),
    "creado": ("Viajero %s (%s): de %s hacia %s, %s bloques.", "Wayfarer %s (%s): from %s towards %s, %s blocks."),
    "lista.titulo": ("Viajeros en camino: %s (máximo %s)", "Wayfarers on the road: %s (maximum %s)"),
    "lista.linea": (" - %s: %s, de %s hacia %s, vértice %s de %s, en %s %s %s",
                    " - %s: %s, from %s towards %s, waypoint %s of %s, at %s %s %s"),
}
WAYFARER_STATE = {
    "estado.viajeros.no": ("Gente de paso: desactivada.", "Wayfarers: disabled."),
    "estado.viajeros": ("Viajeros en camino: %s (máximo %s; frecuencia %s %%); desde el arranque han pasado %s",
                        "Wayfarers on the road: %s (maximum %s; frequency %s %%); since startup %s have passed"),
}
# The advancement (granted by the Java side: caravanas/Caravanas.premiar): (id, icon, frame, experience, (title), (description))
ADVANCEMENTS = [
    ("defensa", "minecraft:lead", "goal", 50, ("Camino seguro", "Safe Passage"),
     ("Defiende una caravana de los bandidos hasta que llegue a su aldea",
      "Defend a caravan from bandits until it reaches its village")),
]


def _advancement_key(lid, part):
    return f"advancements.{NS}.caravanas.{lid}.{part}"


def advancements():
    """{path: json} of the caravan advancement ("impossible" criterion: granted by the Java side)."""
    out = {}
    for lid, emblem, frame, xp, title, desc in ADVANCEMENTS:
        out[f"caravanas/{lid}"] = {
            "parent": f"{NS}:raiz",
            "criteria": {"hecho": {"trigger": "minecraft:impossible"}},
            "display": {"icon": {"id": emblem},
                        "title": {"translate": _advancement_key(lid, "title"), "fallback": title[0]},
                        "description": {"translate": _advancement_key(lid, "description"), "fallback": desc[0]},
                        "frame": frame},
            "requirements": [["hecho"]],
            "rewards": {"experience": xp},
        }
    return out


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    for k, (es, en) in STATE.items():
        out["es_es"][f"{NS}.{k}"], out["en_us"][f"{NS}.{k}"] = es, en
    for k, (es, en) in WAYFARERS.items():
        out["es_es"][f"{NS}.viajeros.{k}"], out["en_us"][f"{NS}.viajeros.{k}"] = es, en
    for k, (es, en) in WAYFARER_STATE.items():
        out["es_es"][f"{NS}.{k}"], out["en_us"][f"{NS}.{k}"] = es, en
    for lid, _, _, _, title, desc in ADVANCEMENTS:
        for i, language in enumerate(("es_es", "en_us")):
            out[language][_advancement_key(lid, "title")] = title[i]
            out[language][_advancement_key(lid, "description")] = desc[i]
    return out


def write(out, jdump):
    for route, advancement in advancements().items():
        jdump(out, f"data/{NS}/advancement/{route}.json", advancement)
