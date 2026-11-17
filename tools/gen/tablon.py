"""Tablón de encargos de la plaza de cada aldea (solo datos; el Java solo quita la pieza si está desactivado).

Pieza <estilo>/tablon (pool <estilo>/tablon), colgada de un hueco de la plaza (streets.plaza, SLOT) con un jigsaw
alineado, como los aldeanos: un atril con el libro «Tablón de encargos» y, detrás, el alguacil (aldeano sin IA,
invulnerable, con nombre) que paga los encargos de entrega con sus tratos fijos (Offers en la plantilla):
  - Cosecha para el granero: COSECHA de la familia -> esmeraldas
  - Leña para el invierno: troncos del estilo -> esmeraldas
  - Limpia los caminos: carne podrida y huesos -> «Capa de la ronda» (peto de cuero del color del estandarte)
Los encargos que son hazañas los detecta el juego con logros (sin trabajo por tick) y los paga la recompensa del logro
(una vez por jugador):
  - aldeas/encargos/ronda: matar una amenaza (heraldia:amenazas_aldea) dentro de una aldea Heraldia
  - aldeas/encargos/asedio: ser héroe de la aldea (asalto de saqueadores ganado) en una aldea Heraldia
Coste: una entidad por aldea (el alguacil, sin IA: no piensa ni se mueve) y ninguna función periódica.
Si aldeas.vida.tablon está desactivado, AldeaStructure quita la pieza al crear la aldea (las ya generadas no cambian).
"""
from core import Template, nsid, B, F, NS
from logros import advancement, comp, key as adv_key
from unicas._comun import botin

SLOT = (14, 0, 18)          # hueco en la plaza (23 x 23, centro 11): al sureste de la fuente, entre bancos y árbol
COSECHA = {"llanuras": "wheat", "bosque": "carrot", "oscuro": "brown_mushroom", "taiga": "sweet_berries",
           "nieve": "potato", "desierto": "cactus", "sabana": "wheat", "jungla": "cocoa_beans",
           "pantano": "sugar_cane", "cerezos": "beetroot", "badlands": "cactus", "costa": "kelp"}
BLOQUES = {"brown_mushroom", "cactus", "sugar_cane", "kelp"}   # su nombre es block.minecraft.<id> (objetos de bloque)
# (cantidad pedida, esmeraldas, usos)
GRANERO, LENA = (32, 4, 4), (32, 3, 4)
RONDA_TRATO = ((16, "rotten_flesh"), (8, "bone"), 2)        # pide, también pide, usos
RONDA_LOGRO, ASEDIO_LOGRO = 3, 8                            # esmeraldas de la recompensa de cada logro
AMENAZAS = ["zombie", "husk", "drowned", "zombie_villager", "skeleton", "stray", "bogged", "spider", "cave_spider",
            "creeper", "witch", "pillager", "vindicator", "evoker", "ravager"]
TAG_ALGUACIL = "heraldia_alguacil"
DYE = {"white": 0xF9FFFE, "orange": 0xF9801D, "magenta": 0xC74EBD, "light_blue": 0x3AB3DA, "yellow": 0xFED83D,
       "lime": 0x80C71F, "pink": 0xF38BAA, "gray": 0x474F52, "light_gray": 0x9D9D97, "cyan": 0x169C9C,
       "purple": 0x8932B8, "blue": 0x3C44AA, "brown": 0x835432, "green": 0x5E7C16, "red": 0xB02E26, "black": 0x1D1D21}

K = f"{NS}.tablon"
TEXTOS = {
    "alguacil": ("Alguacil", "Bailiff"),
    "libro": ("Tablón de encargos", "Job Board"),
    "capa": ("Capa de la ronda", "Watch Cloak"),
    "capa.lore": ("La lleva quien guarda los caminos", "Worn by those who guard the roads"),
    "cuerno": ("Cuerno del defensor", "Defender's Horn"),
    "cuerno.lore": ("La aldea no olvida a quien la defendió", "The village never forgets who defended it"),
    "p1": ("Tablón de encargos\n\nLa aldea necesita manos. Lleva lo que se pide al alguacil, junto a este atril: "
           "paga en el acto mientras le quede trabajo.\n\nLas hazañas no hace falta contarlas: la aldea se entera y "
           "paga una vez a cada cual.",
           "Job Board\n\nThe village needs hands. Bring what is asked to the bailiff, by this lectern: he pays on "
           "the spot while he has work.\n\nDeeds need not be told: the village hears of them and pays each person "
           "once."),
    "p2": ("Cosecha para el granero\n\nTrae al alguacil %s × %s para el granero.\n\nPaga: %s esmeraldas.",
           "Harvest for the granary\n\nBring the bailiff %s × %s for the granary.\n\nPays: %s emeralds."),
    "p3": ("Leña para el invierno\n\nTrae al alguacil %s × %s para las chimeneas.\n\nPaga: %s esmeraldas.",
           "Firewood for winter\n\nBring the bailiff %s × %s for the hearths.\n\nPays: %s emeralds."),
    "p4": ("Limpia los caminos\n\nTrae al alguacil %s × %s y %s × %s.\n\nPaga: %s.",
           "Clear the roads\n\nBring the bailiff %s × %s and %s × %s.\n\nPays: %s."),
    "p5": ("Ronda nocturna (hazaña)\n\nAcaba con una amenaza dentro de la aldea: zombi, esqueleto, araña, creeper, "
           "bruja o saqueador.\n\nPaga la aldea: %s esmeraldas.",
           "Night watch (deed)\n\nSlay a threat inside the village: zombie, skeleton, spider, creeper, witch or "
           "raider.\n\nThe village pays: %s emeralds."),
    "p6": ("Defiende la aldea (hazaña)\n\nResiste un asedio de saqueadores en una aldea de Heraldia hasta ser héroe "
           "de la aldea.\n\nPaga la aldea: %s esmeraldas y %s.",
           "Defend the village (deed)\n\nWithstand a raid on a Heraldia village until you are its hero.\n\nThe "
           "village pays: %s emeralds and %s."),
}
LOGROS = {
    "ronda": (("Ronda nocturna", "Night Watch"),
              ("Acaba con una amenaza dentro de una aldea Heraldia (encargo del tablón)",
               "Slay a threat inside a Heraldia village (job board)"), "minecraft:iron_sword"),
    "asedio": (("Defensor de la aldea", "Village Defender"),
               ("Sé héroe de una aldea Heraldia tras un asedio (encargo del tablón)",
                "Become the hero of a Heraldia village after a raid (job board)"), "minecraft:goat_horn"),
}


def _t(k):
    return {"translate": f"{K}.{k}", "fallback": TEXTOS[k][0]}


def _nombre(item):
    return {"translate": f"{'block' if item in BLOQUES or item.endswith(('_log', '_block')) else 'item'}.minecraft.{item}"}


def _p(k, *args):
    c = _t(k)
    if args:   # una lista NBT es de un solo tipo: los números van como texto
        c["with"] = [{"text": str(a)} if isinstance(a, int) else a for a in args]
    return c


def capa_componentes(th):
    return {"minecraft:item_name": _t("capa"), "minecraft:dyed_color": DYE[th["banner"]],
            "minecraft:enchantments": {"minecraft:protection": 2},
            "minecraft:lore": [dict(_t("capa.lore"), color="gray", italic=False)]}


def cuerno_componentes():
    return {"minecraft:item_name": _t("cuerno"), "minecraft:instrument": "minecraft:call_goat_horn",
            "minecraft:lore": [dict(_t("cuerno.lore"), color="gray", italic=False)]}


def paginas(th):
    crop, wood = COSECHA[th["family"]], th["log"]
    (rn, ri), (bn, bi), _ = RONDA_TRATO
    return [_p("p1"), _p("p2", GRANERO[0], _nombre(crop), GRANERO[1]), _p("p3", LENA[0], _nombre(wood), LENA[1]),
            _p("p4", rn, _nombre(ri), bn, _nombre(bi), _t("capa")), _p("p5", RONDA_LOGRO),
            _p("p6", ASEDIO_LOGRO, _t("cuerno"))]


def libro(th):
    e = botin.libro(paginas(th), _t("libro"), TEXTOS["libro"][0], TEXTOS["alguacil"][0])
    return {"id": "minecraft:written_book", "count": 1, "components": e["modifier"][0]["components"]}


def _oferta(buy, sell, uses, buy_b=None):
    o = {"buy": buy, "sell": sell, "maxUses": uses, "uses": 0, "xp": 0, "rewardExp": B(1),
         "priceMultiplier": F(0.0), "specialPrice": 0, "demand": 0}
    if buy_b:
        o["buyB"] = buy_b
    return o


def ofertas(th):
    crop, wood = COSECHA[th["family"]], th["log"]
    (rn, ri), (bn, bi), ru = RONDA_TRATO
    em = lambda n: {"id": "minecraft:emerald", "count": n}
    return [_oferta({"id": f"minecraft:{crop}", "count": GRANERO[0]}, em(GRANERO[1]), GRANERO[2]),
            _oferta({"id": f"minecraft:{wood}", "count": LENA[0]}, em(LENA[1]), LENA[2]),
            _oferta({"id": f"minecraft:{ri}", "count": rn},
                    {"id": "minecraft:leather_chestplate", "count": 1, "components": capa_componentes(th)}, ru,
                    buy_b={"id": f"minecraft:{bi}", "count": bn})]


def alguacil(th):
    return {"id": "minecraft:villager", "PersistenceRequired": B(1), "NoAI": B(1), "Invulnerable": B(1),
            "Tags": [NS, TAG_ALGUACIL], "CustomName": _t("alguacil"), "CustomNameVisible": B(1),
            "VillagerData": {"profession": "minecraft:weaponsmith", "level": 5, "type": "minecraft:" + th["vtype"]},
            "Xp": 250, "Rotation": [F(180.0), F(0.0)],   # mira al norte, hacia el atril y quien lo lee
            "Offers": {"Recipes": ofertas(th)}}


def pieza(th, name):
    """Atril (mirando al norte: el lector se pone delante) y detrás el alguacil, sobre el jigsaw (que no coloca nada)."""
    t = Template(name)
    t.set(0, 0, 0, "lectern[facing=north,has_book=true,powered=false]", nbt={"id": "minecraft:lectern", "Book": libro(th), "Page": 0})
    t.jigsaw(0, 0, 1, "down_north", "heraldia:bottom", "heraldia:slot", "minecraft:empty",
             final_state="minecraft:structure_void", joint="aligned")
    t.entity(0, 0, 1, alguacil(th))
    t.min_size = (1, 3, 2)
    return t


def slot(t, th):
    """Hueco del tablón en la plaza (jigsaw hacia arriba, alineado: la pieza gira con la plaza)."""
    x, y, z = SLOT
    t.jigsaw(x, y, z, "up_north", "heraldia:slot", "heraldia:bottom", nsid(f"{th['id']}/tablon"),
             final_state=th["path"], joint="aligned")


def build(reg, th):
    name = reg.add(pieza(th, f"{th['id']}/tablon"), "tablon")
    reg.pool(f"{th['id']}/tablon", [(name, 1, "rigid", None)])


def errores(themes):
    e = []
    for th in themes:
        if th["family"] not in COSECHA:
            e.append(f"tablon.COSECHA: falta la familia {th['family']}")
        if th["banner"] not in DYE:
            e.append(f"tablon.DYE: falta el color {th['banner']}")
    largo = "X" * 24   # nombre de objeto largo (p. ej. «Troncos de roble oscuro»)
    for k, (es, en) in TEXTOS.items():
        if k.startswith("p"):
            for txt in (es, en):
                t = txt.replace("%s", largo)
                if botin.lineas_libro(t) > botin.LIBRO_LINEAS:
                    e.append(f"tablon: la página {k} no cabe ({botin.lineas_libro(t)} líneas): {txt[:40]}…")
    return e


def _recompensa(n, extra=None):
    pools = [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:emerald",
                                       "modifier": [{"type": "minecraft:set_count", "count": n}]}]}]
    if extra:
        pools.append({"rolls": 1, "entries": [{"type": "minecraft:item", "name": extra[0],
                                               "modifier": [{"type": "minecraft:set_components", "components": extra[1]}]}]})
    import tesoro   # a veces, un fragmento de mapa del tesoro (tesoro.FACTOR["encargos"])
    return tesoro.con_pista({"type": "minecraft:advancement_reward", "pools": pools}, "encargos")


def tablas():
    """Tablas de recompensa de las hazañas (heraldia:encargos/<id>)."""
    return {"ronda": _recompensa(RONDA_LOGRO), "asedio": _recompensa(ASEDIO_LOGRO, ("minecraft:goat_horn", cuerno_componentes()))}


def objetos(themes):
    """Lo que pide y da el alguacil de cada estilo, como entradas de botín (para validar ids, adornos y encantamientos)."""
    out = []
    for th in themes:
        for o in ofertas(th):
            for k in ("buy", "buyB", "sell"):
                if k in o:
                    e = {"type": "minecraft:item", "name": o[k]["id"]}
                    if o[k].get("components"):
                        e["modifier"] = [{"type": "minecraft:set_components", "components": o[k]["components"]},
                                         {"type": "minecraft:set_enchantments",
                                          "enchantments": o[k]["components"].get("minecraft:enchantments", {})}]
                    out.append(e)
    return out


def lang():
    """Textos (es_es, en_us) del tablón, del alguacil y de los logros de las hazañas."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTOS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    out["es_es"][f"entity.{NS}.alguacil"], out["en_us"][f"entity.{NS}.alguacil"] = TEXTOS["alguacil"]
    for k, ((tes, ten), (des, den), _) in LOGROS.items():
        for part, es, en in (("title", tes, ten), ("description", des, den)):
            out["es_es"][adv_key(f"aldeas/encargos/{k}", part)], out["en_us"][adv_key(f"aldeas/encargos/{k}", part)] = es, en
    return out


def write(out, jdump):
    """Logros de las hazañas, sus recompensas y la etiqueta de amenazas; devuelve los textos (es_es, en_us)."""
    jdump(out, f"data/{NS}/tags/entity_type/amenazas_aldea.json", {"values": [f"minecraft:{m}" for m in AMENAZAS]})
    aldea = {"minecraft:location": {"structures": f"#{NS}:aldeas"}}
    crit = {
        "ronda": {"amenaza": {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
            "type": "minecraft:entity_properties", "entity": "this",
            "predicate": dict({"minecraft:entity_type": f"#{NS}:amenazas_aldea"}, **aldea)}}}},
        "asedio": {"heroe": {"trigger": "minecraft:hero_of_the_village", "conditions": {"player": {
            "type": "minecraft:entity_properties", "entity": "this", "predicate": aldea}}}},
    }
    rewards = tablas()
    for k, ((tes, _), (des, _), icon) in LOGROS.items():
        path = f"aldeas/encargos/{k}"
        adv = advancement("raiz", icon, comp(adv_key(path, "title"), tes), comp(adv_key(path, "description"), des),
                          crit[k], frame="goal" if k == "asedio" else "task")
        adv["rewards"] = {"loot": [f"{NS}:encargos/{k}"], "experience": 30 if k == "ronda" else 100}
        jdump(out, f"data/{NS}/advancement/{path}.json", adv)
        jdump(out, f"data/{NS}/loot_table/encargos/{k}.json", rewards[k])
    return lang()
