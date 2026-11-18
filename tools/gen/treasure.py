"""Chained treasure hunt (T40): a map fragment leads, step by step, through real Heraldia structures to a
buried chest (assembled by the Java, package tesoro/).

Here go the data and the texts:
  - heraldia:tesoro/fragmento   the first hint: a map fragment (named paper with lore and the custom_data mark
                                {heraldia_busqueda: {v: 1}}); when used (right click) the Java picks the chain and swaps it
                                for a vanilla map with the mark of the first destination.
  - heraldia:tesoro/cofre       the final chest loot: good without breaking progression (no netherite or elytra) and
                                the named keepsake, Ysolda's Compass (custom_data heraldia_recuerdo_tesoro).
  - con_pista(table, family)    adds to a chest table a group with the fragment under the condition heraldia:tesoro_pista
                                (Java: loot/PistaCondition): it comes out with probability treasure.probability % x FACTOR[family],
                                read when the loot is rolled (reloadable with /heraldia reload) and never with treasure.switched_on = false.
  - the advancements tesoro/fragmento and tesoro/cofre (written by advancements.write with the others), the "tesoro" page of the Guide (guide.py) and the texts heraldia.tesoro.*.

Used by: the chest tables of the medium structures, the mine entrances and the unique structures, the reward of the board's
feats and the payment of the board's quests (T38: heraldia:tesoro/encargo, rolled by Tesoro.recompensa in Encargos.pagar).
For another source, it is enough to nest the table heraldia:tesoro/fragmento (or call treasure.Tesoro.fragmento in Java).
"""
from loot import item
from uniques._common import chest_loot

NS = "heraldia"
MARK = "heraldia_busqueda"                 # custom_data of the hints: {heraldia_busqueda: {...}} (tesoro/Cadena in Java)
MEMENTO_MARK = "heraldia_recuerdo_tesoro"
# In SNBT (text), not in JSON: a JSON number in custom_data reaches the game as a double (1 -> 1.0d) and no longer matches
# a {v: 1} predicate (integer); SNBT keeps the type (Cadena.fragmento in Java writes the same integer).
FRAGMENT_MARK = "{%s: {v: 1}}" % MARK
MEMORY_MARK = "{%s: 1b}" % MEMENTO_MARK
FRAGMENT = f"{NS}:tesoro/fragmento"
CHEST_TABLE = f"{NS}:tesoro/cofre"
CONDITION = f"{NS}:tesoro_pista"
# Factor of each table family over treasure.probability: the unique structures have many chests (half per chest); the board
# quests, like one chest; the board feats, few and hard (five times more).
FACTOR = {"medianas": 1.0, "minas": 1.0, "costa": 0.5, "unicas": 0.5, "encargos": 1.0, "hazanas": 5.0}
QUEST = f"{NS}:tesoro/encargo"   # the payment of each delivered board quest (T38, Encargos.pagar -> Tesoro.recompensa)
DEFAULT_PROBABILITY, DEFAULT_RADIUS = 3.0, 1500     # % per chest and blocks (options.py)
LORE_MAX_PX = 250                                    # maximum width of a lore line (the game does not wrap it: it must fit on screen)

# Texts (heraldia.tesoro.<key>): (es_es, en_us). %s: numbers, names, biomes or directions (heraldia.info.dir.*).
TEXTS = {
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
# Texts that go in the lore of the items (one line each, no wrapping): they are measured with LORE_MAX_PX in each language.
LORE = ("fragmento.lore", "fragmento.uso", "mapa.uso", "pista.mediana", "pista.mina", "pista.tesoro", "pista.prevista",
        "recuerdo.lore")

ADVANCEMENTS = {
    "tesoro/fragmento": {"titulo": ("Un trozo de mapa", "A Scrap of Map"),
                         "descripcion": ("Consigue un fragmento de mapa del tesoro", "Get a treasure map fragment"),
                         "icono": "minecraft:paper", "xp": 20},
    "tesoro/cofre": {"titulo": ("El tesoro de Ysolda", "Ysolda's Treasure"),
                     "descripcion": ("Sigue un mapa del tesoro hasta el final y abre el cofre enterrado",
                                     "Follow a treasure map to the end and open the buried chest"),
                     "icono": "minecraft:chest", "xp": 150, "marco": "goal"},
}


def key(k):
    return f"{NS}.tesoro.{k}"


def comp(k, *args, **style):
    c = {"translate": key(k), "fallback": TEXTS[k][0]}
    if args:
        c["with"] = list(args)
    c.update(style)
    return c


def lang():
    """Texts heraldia.tesoro.* (those of the advancements are in lang_logros: they go with those of advancements.build)."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][key(k)], out["en_us"][key(k)] = es, en
    return out


def lang_advancements():
    out = {"es_es": {}, "en_us": {}}
    for path, d in ADVANCEMENTS.items():
        for part, field in (("title", "titulo"), ("description", "descripcion")):
            k = f"advancements.{NS}.{path.replace('/', '.')}.{part}"
            out["es_es"][k], out["en_us"][k] = d[field]
    return out


def probability(percentage, factor):
    """Probability that a table with con_pista(…, family) gives the fragment: the same as PistaCondition in Java."""
    return max(0.0, min(1.0, percentage / 100.0 * factor))


def fragment():
    """Table heraldia:tesoro/fragmento: the map fragment (named paper with lore and the mark)."""
    comps = {
        "minecraft:item_name": comp("fragmento.nombre"),
        "minecraft:lore": [comp("fragmento.lore", color="gray", italic=False),
                           comp("fragmento.uso", color="dark_aqua", italic=False)],
        "minecraft:rarity": "uncommon",
        "minecraft:enchantment_glint_override": True,
        "minecraft:max_stack_size": 1,
        "minecraft:custom_data": FRAGMENT_MARK,
    }
    return {"type": "minecraft:chest", "pools": [{"rolls": 1, "entries": [
        {"type": "minecraft:item", "name": "minecraft:paper", "modifier": [{"type": "minecraft:set_components", "components": comps}]}]}]}


def memento():
    comps = {
        "minecraft:item_name": comp("recuerdo.nombre"),
        "minecraft:lore": [comp("recuerdo.lore", color="gray", italic=False)],
        "minecraft:rarity": "rare",
        "minecraft:enchantment_glint_override": True,
        "minecraft:custom_data": MEMORY_MARK,
    }
    return {"type": "minecraft:item", "name": "minecraft:compass", "modifier": [{"type": "minecraft:set_components", "components": comps}]}


# Final chest loot: like that of an epic village chest, somewhat more generous and thematic (treasure hunters), without
# netherite, elytra or enchanted apples.
VALUABLE = [item("diamond", 6, 1, 3), item("emerald", 10, 4, 10), item("gold_ingot", 10, 3, 8), item("golden_apple", 5, 1, 2),
           item("book", 6, ench=(20, 30)), item("diamond_sword", 2, ench=(15, 25)), item("iron_chestplate", 3, ench=(15, 25)),
           item("experience_bottle", 6, 4, 10), item("name_tag", 3), item("spyglass", 3), item("heart_of_the_sea", 2),
           item("wayfinder_armor_trim_smithing_template", 3), item("music_disc_wait", 1), item("gold_block", 2)]
SUSTENANCE = [item("bread", 8, 2, 5), item("cooked_cod", 6, 2, 4), item("iron_ingot", 8, 2, 6), item("torch", 6, 4, 10),
            item("map", 2), item("compass", 2)]
FORBIDDEN = ("netherite", "elytra", "enchanted_golden_apple", "totem")


def place_chest():
    """Table heraldia:tesoro/cofre: the keepsake always, 3-5 valuable items and 2-4 of sustenance."""
    return {"type": "minecraft:chest", "pools": [
        {"rolls": 1, "entries": [memento()]},
        {"rolls": {"type": "minecraft:uniform", "min": 3, "max": 5}, "entries": VALUABLE},
        {"rolls": {"type": "minecraft:uniform", "min": 2, "max": 4}, "entries": SUSTENANCE},
    ]}


def clue_pool(family):
    return {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": FRAGMENT}],
            "condition": {"type": CONDITION, "factor": FACTOR[family]}}


def with_hint(tbl, family):
    """The table with one more group: the fragment, with the probability of treasure.probability x FACTOR[family]."""
    return dict(tbl, pools=list(tbl["pools"]) + [clue_pool(family)])


CONTAINERS = ("chest", "barrel", "decorated_pot")   # blocks in which the fragment can appear (not dispensers)


def tables_in_containers(reg):
    """Ids of the tables used by some chest, barrel or jar of the templates (not dispensers or droppers: the
    fragment must not be shot out of a trap)."""
    out = set()
    for t in reg.templates.values():
        for state, nbt in t.blocks.values():
            if nbt and nbt.get("LootTable") and str(state).split("[")[0].removeprefix("minecraft:").endswith(CONTAINERS):
                out.add(str(nbt["LootTable"]))
    return out


def quest():
    """Table heraldia:tesoro/encargo: only the fragment, with the probability of the quests (rolled by Tesoro.recompensa
    when paying each delivered board quest)."""
    return with_hint({"type": "minecraft:chest", "pools": []}, "encargos")


def advancements():
    """{path: advancement} of the treasure hunt (they hang from the root of the Heraldia tab)."""
    import advancements as lg
    out = {}
    criteria = {
        "tesoro/fragmento": {"fragmento": {"trigger": "minecraft:inventory_changed", "conditions": {"items": [
            {"items": "minecraft:paper", "predicates": {"minecraft:custom_data": {MARK: {}}}}]}}},
        "tesoro/cofre": {"cofre": {"trigger": "minecraft:player_generates_container_loot", "conditions": {"loot_tables": CHEST_TABLE}}},
    }
    parent = {"tesoro/fragmento": "raiz", "tesoro/cofre": "tesoro/fragmento"}
    for path, d in ADVANCEMENTS.items():
        out[path] = lg.advancement(parent[path], d["icono"], lg.comp(lg.key(path, "title"), d["titulo"][0]),
                                   lg.comp(lg.key(path, "description"), d["descripcion"][0]), criteria[path],
                                   frame=d.get("marco", "task"), xp=d["xp"])
    return out


def errors(translations=None):
    """[] if everything fits: each lore line within LORE_MAX_PX in each language (with a long biome in the placeholders) and nothing
    forbidden in the chest. `translations`: {code: texts} of the languages other than es/en."""
    e = []
    languages = [("es", {key(k): v[0] for k, v in TEXTS.items()}), ("en", {key(k): v[1] for k, v in TEXTS.items()})]
    languages += list((translations or {}).items())
    for name, t in languages:
        for k in LORE:
            if chest_loot.width(t[key(k)]) > LORE_MAX_PX:
                e.append(f"tesoro: el lore «{k}» ({name}) pasa de {LORE_MAX_PX} px: {t[key(k)]}")
    import json
    text = json.dumps(place_chest())
    e += [f"tesoro: objeto prohibido en el cofre: {p}" for p in FORBIDDEN if p in text]
    return e


def write(out, jdump):
    jdump(out, f"data/{NS}/loot_table/tesoro/fragmento.json", fragment())
    jdump(out, f"data/{NS}/loot_table/tesoro/cofre.json", place_chest())   # the advancements are written by advancements.write with the others
    jdump(out, f"data/{NS}/loot_table/tesoro/encargo.json", quest())
    return lang()
