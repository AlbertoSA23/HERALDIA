"""Caravanas por los caminos entre aldeas (T39): textos y el logro. La lógica va en Java (caravanas/): qué tramo de la ruta
canónica recorre (Tramo), sus fases (Viaje), cuándo sale y qué paga (Reglas); nada en el datapack salvo esto.

Claves:
  heraldia.caravanas.*          lo que se dice a los jugadores cerca de la caravana y /heraldia caravan (operadores)
  heraldia.estado.caravanas*    las líneas de /heraldia status
  advancements.heraldia.caravanas.<id>.title/.description   el logro (lo concede el Java, criterio «hecho»)
Los nombres de los bandidos son los del campamento de bandidos (heraldia.medianas.campamento.saqueador/vindicador).
Los argumentos (%s) los pone el Java (caravanas/Caravanas): no cambies su orden sin cambiarlo allí.
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
# El logro (lo concede el Java: caravanas/Caravanas.premiar): (id, icono, marco, experiencia, (título), (descripción))
ADVANCEMENTS = [
    ("defensa", "minecraft:lead", "goal", 50, ("Camino seguro", "Safe Passage"),
     ("Defiende una caravana de los bandidos hasta que llegue a su aldea",
      "Defend a caravan from bandits until it reaches its village")),
]


def _advancement_key(lid, part):
    return f"advancements.{NS}.caravanas.{lid}.{part}"


def advancements():
    """{ruta: json} del logro de las caravanas (criterio «impossible»: lo concede el Java)."""
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
    for lid, _, _, _, title, desc in ADVANCEMENTS:
        for i, language in enumerate(("es_es", "en_us")):
            out[language][_advancement_key(lid, "title")] = title[i]
            out[language][_advancement_key(lid, "description")] = desc[i]
    return out


def write(out, jdump):
    for route, advancement in advancements().items():
        jdump(out, f"data/{NS}/advancement/{route}.json", advancement)
