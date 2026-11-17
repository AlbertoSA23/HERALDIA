"""Búsqueda del tesoro encadenada (T40): un fragmento de mapa lleva, paso a paso, por estructuras reales de Heraldia hasta
un cofre enterrado (lo arma el Java, paquete tesoro/).

Aquí van los datos y los textos:
  - heraldia:tesoro/fragmento   la primera pista: un fragmento de mapa (papel con nombre, lore y la marca custom_data
                                {heraldia_busqueda: {v: 1}}); al usarlo (clic derecho) el Java elige la cadena y lo cambia
                                por un mapa vanilla con la marca del primer destino.
  - heraldia:tesoro/cofre       el botín del cofre final: bueno sin romper la progresión (nada de netherita ni élitros) y
                                el recuerdo con nombre, la Brújula de Ysolda (custom_data heraldia_recuerdo_tesoro).
  - con_pista(tabla, familia)   añade a una tabla de cofre un grupo con el fragmento bajo la condición heraldia:tesoro_pista
                                (Java: loot/PistaCondition): sale con probabilidad tesoro.probabilidad % x FACTOR[familia],
                                leída al tirar el botín (recargable con /heraldia reload) y nunca con tesoro.activado = false.
  - los logros tesoro/fragmento y tesoro/cofre (los escribe logros.write con los demás), la página «tesoro» de la Guía (guia.py) y los textos heraldia.tesoro.*.

Lo usan: las tablas de cofre de las medianas, de las entradas a mina y de las únicas, la recompensa de las hazañas del
tablón y la paga de los encargos del tablón (T38: heraldia:tesoro/encargo, que tira Tesoro.recompensa en Encargos.pagar).
Para otro origen, basta con anidar la tabla heraldia:tesoro/fragmento (o llamar a tesoro.Tesoro.fragmento en Java).
"""
from loot import item
from unicas._comun import botin

NS = "heraldia"
MARCA = "heraldia_busqueda"                 # custom_data de las pistas: {heraldia_busqueda: {...}} (tesoro/Cadena en Java)
RECUERDO_MARCA = "heraldia_recuerdo_tesoro"
# En SNBT (texto), no en JSON: un número JSON en custom_data llega al juego como double (1 -> 1.0d) y ya no casa con
# un predicado {v: 1} (entero); el SNBT conserva el tipo (Cadena.fragmento en Java escribe el mismo entero).
MARCA_FRAGMENTO = "{%s: {v: 1}}" % MARCA
MARCA_RECUERDO = "{%s: 1b}" % RECUERDO_MARCA
FRAGMENTO = f"{NS}:tesoro/fragmento"
COFRE = f"{NS}:tesoro/cofre"
CONDICION = f"{NS}:tesoro_pista"
# Factor de cada familia de tablas sobre tesoro.probabilidad: las únicas tienen muchos cofres (la mitad por cofre); los
# encargos del tablón, como un cofre; las hazañas del tablón, pocas y difíciles (cinco veces más).
FACTOR = {"medianas": 1.0, "minas": 1.0, "unicas": 0.5, "encargos": 1.0, "hazanas": 5.0}
ENCARGO = f"{NS}:tesoro/encargo"   # la paga de cada encargo entregado del tablón (T38, Encargos.pagar -> Tesoro.recompensa)
PROBABILIDAD_DEFECTO, RADIO_DEFECTO = 3.0, 1500     # % por cofre y bloques (opciones.py)
LORE_MAX_PX = 250                                    # ancho máximo de una línea de lore (el juego no la parte: que quepa en pantalla)

# Textos (heraldia.tesoro.<clave>): (es_es, en_us). %s: números, nombres, biomas o direcciones (heraldia.info.dir.*).
TEXTOS = {
    "fragmento.nombre": ("Fragmento de mapa del tesoro", "Treasure map fragment"),
    "fragmento.lore": ("Una marca borrosa y unas letras de Ysolda", "A faded mark and a few words by Ysolda"),
    "fragmento.uso": ("Clic derecho para descifrarlo", "Right-click to decipher it"),
    "mapa.nombre": ("Mapa del tesoro (%s/%s)", "Treasure map (%s/%s)"),
    "mapa.hecho": ("Mapa del tesoro (desenterrado)", "Treasure map (unearthed)"),
    "mapa.uso": ("Úsalo (clic derecho) al llegar a la marca", "Use it (right-click) at the mark"),
    "pista.mediana": ("Un alto en el camino,", "A stop along the road,"),
    "pista.mina": ("Una boca de mina en la ladera,", "A mine mouth on a hillside,"),
    "pista.tesoro": ("Bajo la tierra, donde cavó Ysolda,", "Under the earth, where Ysolda dug,"),
    "pista.donde": ("en %s, hacia el %s", "in %s, to the %s"),
    "pista.prevista": ("(en tierras aún sin explorar)", "(in lands not yet explored)"),
    "descifrando": ("Descifras el fragmento...", "You decipher the fragment..."),
    "descifrado": ("El fragmento era parte de un mapa del tesoro: %s marcas te llevarán hasta él. Sigue la primera.",
                   "The fragment was part of a treasure map: %s marks will lead you to it. Follow the first one."),
    "sin_destino": ("El fragmento no señala nada a menos de %s bloques de aquí. Prueba a descifrarlo en otro lugar.",
                    "The fragment points to nothing within %s blocks of here. Try deciphering it somewhere else."),
    "desactivado": ("La búsqueda del tesoro está desactivada en este servidor.", "The treasure hunt is disabled on this server."),
    "dimension": ("Este mapa solo sirve en el mundo principal.", "This map only works in the Overworld."),
    "ocupado": ("Ya estás descifrando un fragmento: espera un momento.", "You are already deciphering a fragment: wait a moment."),
    "lejos": ("La marca está a unos %s bloques hacia el %s.", "The mark is about %s blocks to the %s."),
    "paso": ("¡Aquí estaba la siguiente pista! El mapa cambia: marca %s de %s.",
             "The next clue was here! The map changes: mark %s of %s."),
    "cofre": ("¡Es aquí! El cofre de Ysolda está enterrado a %s bloques hacia el %s: cava.",
              "This is the place! Ysolda's chest is buried %s blocks to the %s: dig."),
    "cofre.aqui": ("¡Es aquí! El cofre de Ysolda está enterrado bajo tus pies: cava.",
                   "This is the place! Ysolda's chest is buried right under your feet: dig."),
    "movido": ("Alguien ha construido sobre el sitio del tesoro: la marca se ha movido un poco más allá.",
               "Someone has built over the treasure site: the mark has moved a little further on."),
    "sin_sitio": ("La tierra aquí no deja cavar (agua, roca desnuda o construcciones): acércate más a la marca.",
                  "The ground here cannot be dug (water, bare rock or buildings): get closer to the mark."),
    "hecho": ("Este tesoro ya fue desenterrado.", "This treasure has already been unearthed."),
    "cofre.titulo": ("Cofre de Ysolda", "Ysolda's chest"),
    "recuerdo.nombre": ("Brújula de Ysolda", "Ysolda's Compass"),
    "recuerdo.lore": ("La última heraldo la llevó hasta aquí", "The last herald carried it this far"),
    # /heraldia treasure (operadores)
    "comando.dado": ("Fragmento de mapa del tesoro dado a %s jugadores.", "Treasure map fragment given to %s players."),
    "comando.sin_pista": ("No llevas ninguna pista del tesoro en la mano principal.",
                          "You are not holding a treasure clue in your main hand."),
    "comando.cadena": ("Pista del tesoro: semilla %s, marca %s de %s.", "Treasure clue: seed %s, mark %s of %s."),
    "comando.sin_descifrar": ("Fragmento sin descifrar: úsalo para elegir la cadena.",
                              "Undeciphered fragment: use it to choose the chain."),
    "comando.destino": (" %s. %s en %s, %s (%s)", " %s. %s at %s, %s (%s)"),
    "comando.cofre": (" Cofre colocado en %s %s %s.", " Chest placed at %s %s %s."),
    "tipo.mediana": ("Estructura mediana", "Medium structure"),
    "tipo.mina": ("Entrada a mina", "Mine entrance"),
    "tipo.tesoro": ("Tesoro", "Treasure"),
    "estado.generada": ("generada", "generated"),
    "estado.prevista": ("prevista", "predicted"),
}
# Textos que van en el lore de los objetos (una línea cada uno, sin ajuste): se miden con LORE_MAX_PX en cada idioma.
LORE = ("fragmento.lore", "fragmento.uso", "mapa.uso", "pista.mediana", "pista.mina", "pista.tesoro", "pista.prevista",
        "recuerdo.lore")

LOGROS = {
    "tesoro/fragmento": {"titulo": ("Un trozo de mapa", "A Scrap of Map"),
                         "descripcion": ("Consigue un fragmento de mapa del tesoro", "Get a treasure map fragment"),
                         "icono": "minecraft:paper", "xp": 20},
    "tesoro/cofre": {"titulo": ("El tesoro de Ysolda", "Ysolda's Treasure"),
                     "descripcion": ("Sigue un mapa del tesoro hasta el final y abre el cofre enterrado",
                                     "Follow a treasure map to the end and open the buried chest"),
                     "icono": "minecraft:chest", "xp": 150, "marco": "goal"},
}


def clave(k):
    return f"{NS}.tesoro.{k}"


def comp(k, *args, **estilo):
    c = {"translate": clave(k), "fallback": TEXTOS[k][0]}
    if args:
        c["with"] = list(args)
    c.update(estilo)
    return c


def lang():
    """Textos heraldia.tesoro.* (los de los logros, en lang_logros: van con los de logros.build)."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTOS.items():
        out["es_es"][clave(k)], out["en_us"][clave(k)] = es, en
    return out


def lang_logros():
    out = {"es_es": {}, "en_us": {}}
    for path, d in LOGROS.items():
        for part, field in (("title", "titulo"), ("description", "descripcion")):
            k = f"advancements.{NS}.{path.replace('/', '.')}.{part}"
            out["es_es"][k], out["en_us"][k] = d[field]
    return out


def probabilidad(porcentaje, factor):
    """Probabilidad de que una tabla con con_pista(…, familia) dé el fragmento: lo mismo que PistaCondition en Java."""
    return max(0.0, min(1.0, porcentaje / 100.0 * factor))


def fragmento():
    """Tabla heraldia:tesoro/fragmento: el fragmento de mapa (papel con nombre, lore y la marca)."""
    comps = {
        "minecraft:item_name": comp("fragmento.nombre"),
        "minecraft:lore": [comp("fragmento.lore", color="gray", italic=False),
                           comp("fragmento.uso", color="dark_aqua", italic=False)],
        "minecraft:rarity": "uncommon",
        "minecraft:enchantment_glint_override": True,
        "minecraft:max_stack_size": 1,
        "minecraft:custom_data": MARCA_FRAGMENTO,
    }
    return {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [
        {"type": "minecraft:item", "name": "minecraft:paper", "modifier": [{"type": "minecraft:set_components", "components": comps}]}]}]}


def recuerdo():
    comps = {
        "minecraft:item_name": comp("recuerdo.nombre"),
        "minecraft:lore": [comp("recuerdo.lore", color="gray", italic=False)],
        "minecraft:rarity": "rare",
        "minecraft:enchantment_glint_override": True,
        "minecraft:custom_data": MARCA_RECUERDO,
    }
    return {"type": "minecraft:item", "name": "minecraft:compass", "modifier": [{"type": "minecraft:set_components", "components": comps}]}


# Botín del cofre final: como el de un cofre épico de aldea, algo más generoso y temático (buscadores de tesoros), sin
# netherita, élitros ni manzanas encantadas.
VALIOSO = [item("diamond", 6, 1, 3), item("emerald", 10, 4, 10), item("gold_ingot", 10, 3, 8), item("golden_apple", 5, 1, 2),
           item("book", 6, ench=(20, 30)), item("diamond_sword", 2, ench=(15, 25)), item("iron_chestplate", 3, ench=(15, 25)),
           item("experience_bottle", 6, 4, 10), item("name_tag", 3), item("spyglass", 3), item("heart_of_the_sea", 2),
           item("wayfinder_armor_trim_smithing_template", 3), item("music_disc_wait", 1), item("gold_block", 2)]
SUSTENTO = [item("bread", 8, 2, 5), item("cooked_cod", 6, 2, 4), item("iron_ingot", 8, 2, 6), item("torch", 6, 4, 10),
            item("map", 2), item("compass", 2)]
PROHIBIDO = ("netherite", "elytra", "enchanted_golden_apple", "totem")


def cofre():
    """Tabla heraldia:tesoro/cofre: el recuerdo siempre, 3-5 objetos valiosos y 2-4 de sustento."""
    return {"type": "minecraft:chest", "pools": [
        {"rolls": 1, "entries": [recuerdo()]},
        {"rolls": {"type": "minecraft:uniform", "min": 3, "max": 5}, "entries": VALIOSO},
        {"rolls": {"type": "minecraft:uniform", "min": 2, "max": 4}, "entries": SUSTENTO},
    ]}


def pool_pista(familia):
    return {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": FRAGMENTO}],
            "condition": {"type": CONDICION, "factor": FACTOR[familia]}}


def con_pista(tabla, familia):
    """La tabla con un grupo más: el fragmento, con la probabilidad de tesoro.probabilidad x FACTOR[familia]."""
    return dict(tabla, pools=list(tabla["pools"]) + [pool_pista(familia)])


CONTENEDORES = ("chest", "barrel", "decorated_pot")   # bloques en los que puede salir el fragmento (no dispensadores)


def tablas_en_contenedores(reg):
    """Ids de las tablas que usa algún cofre, barril o vasija de las plantillas (no dispensadores ni soltadores: el
    fragmento no debe salir disparado de una trampa)."""
    out = set()
    for t in reg.templates.values():
        for estado, nbt in t.blocks.values():
            if nbt and nbt.get("LootTable") and str(estado).split("[")[0].removeprefix("minecraft:").endswith(CONTENEDORES):
                out.add(str(nbt["LootTable"]))
    return out


def encargo():
    """Tabla heraldia:tesoro/encargo: solo el fragmento, con la probabilidad de los encargos (la tira Tesoro.recompensa
    al pagar cada encargo entregado del tablón)."""
    return con_pista({"type": "minecraft:chest", "pools": []}, "encargos")


def logros():
    """{ruta: advancement} de la búsqueda del tesoro (cuelgan de la raíz de la pestaña Heraldia)."""
    import logros as lg
    out = {}
    criterios = {
        "tesoro/fragmento": {"fragmento": {"trigger": "minecraft:inventory_changed", "conditions": {"items": [
            {"items": "minecraft:paper", "predicates": {"minecraft:custom_data": {MARCA: {}}}}]}}},
        "tesoro/cofre": {"cofre": {"trigger": "minecraft:player_generates_container_loot", "conditions": {"loot_tables": COFRE}}},
    }
    padre = {"tesoro/fragmento": "raiz", "tesoro/cofre": "tesoro/fragmento"}
    for path, d in LOGROS.items():
        out[path] = lg.advancement(padre[path], d["icono"], lg.comp(lg.key(path, "title"), d["titulo"][0]),
                                   lg.comp(lg.key(path, "description"), d["descripcion"][0]), criterios[path],
                                   frame=d.get("marco", "task"), xp=d["xp"])
    return out


def errores(traducciones=None):
    """[] si todo cabe: cada línea de lore en LORE_MAX_PX en cada idioma (con un bioma largo en los huecos) y nada
    prohibido en el cofre. `traducciones`: {código: textos} de los idiomas que no son es/en."""
    e = []
    idiomas = [("es", {clave(k): v[0] for k, v in TEXTOS.items()}), ("en", {clave(k): v[1] for k, v in TEXTOS.items()})]
    idiomas += list((traducciones or {}).items())
    for nombre, t in idiomas:
        for k in LORE:
            if botin.ancho(t[clave(k)]) > LORE_MAX_PX:
                e.append(f"tesoro: el lore «{k}» ({nombre}) pasa de {LORE_MAX_PX} px: {t[clave(k)]}")
    import json
    texto = json.dumps(cofre())
    e += [f"tesoro: objeto prohibido en el cofre: {p}" for p in PROHIBIDO if p in texto]
    return e


def write(out, jdump):
    jdump(out, f"data/{NS}/loot_table/tesoro/fragmento.json", fragmento())
    jdump(out, f"data/{NS}/loot_table/tesoro/cofre.json", cofre())   # los logros los escribe logros.write con los demás
    jdump(out, f"data/{NS}/loot_table/tesoro/encargo.json", encargo())
    return lang()
