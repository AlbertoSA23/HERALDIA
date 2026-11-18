"""Chozas de mago (T43): lo que no es la plantilla (medianas/choza_mago.py). La lógica va en Java (chozas/): con la
semilla del mundo y el chunk del mago decide si es malvado (chozas_mago.prob_malvado) y si su botín lleva el premio
(chozas_mago.prob_botin_premium); lo revela una sola vez y le pone su tabla de botín. Aquí van sus textos y esas tablas.

Claves:
  heraldia.chozas_mago.*        lo que se dice a los jugadores (revelación, nombre del Mago Malvado y de cada mago),
                                /heraldia wizard (operadores)
  heraldia.estado.chozas_mago*  la línea de /heraldia status
Tablas de botín (mob, no cofre: no se reponen ni llevan la pista del tesoro):
  heraldia:chozas_mago/malvado          la del Mago Malvado: de más nivel que una mediana (MALVADO)
  heraldia:chozas_mago/malvado_premium  la misma más un objeto fuerte (PREMIUM), si sale el premio
El evocador vanilla suelta siempre un tótem de la inmortalidad; el Mago Malvado no (lleva su tabla en vez de la del
evocador): las chozas son frecuentes y un mago de cada cinco es malvado, así que el tótem queda como una de las
opciones del premio (una de cada ~30 chozas malvadas con los valores por defecto), no como botín seguro.
Los argumentos (%s) los pone el Java (chozas/Magos): no cambies su orden sin cambiarlo allí.
"""
from loot import item, empty
from uniques._common import chest_loot

NS = "heraldia"
K = f"{NS}.chozas_mago"
EVIL_TABLE = f"{NS}:chozas_mago/malvado"
PREMIUM_TABLE = f"{NS}:chozas_mago/malvado_premium"
# Nombres de los magos (nombres propios, iguales en todos los idiomas) y sus apodos (traducidos): «Aldric de la Bruma».
NAMES = ["Aldric", "Morwen", "Tobias", "Ysolde", "Bertrand", "Elowen", "Cassius", "Ilsa", "Fenwick", "Odile",
           "Lazlo", "Mirela", "Quillon", "Rhosyn", "Severin", "Tamsin"]
NICKNAMES = [
    ("de la Bruma", "of the Mist"),
    ("de las Setas", "of the Mushrooms"),
    ("de las Estrellas", "of the Stars"),
    ("del Caldero", "of the Cauldron"),
    ("de los Siete Frascos", "of the Seven Flasks"),
    ("del Camino", "of the Road"),
    ("de la Amatista", "of the Amethyst"),
    ("del Bosque Viejo", "of the Old Wood"),
]
TEXTS = {
    "nombre": ("%s %s", "%s %s"),
    "malvado": ("Mago Malvado", "Evil Wizard"),
    "revela": ("¡%s se quita la máscara: era un mago malvado!", "%s throws off the disguise: an evil wizard all along!"),
    "vencido": ("El Mago Malvado ha caído.", "The Evil Wizard has fallen."),
    "reveal.hecho": ("Mago revelado en %s %s %s (malvado a la fuerza).", "Wizard revealed at %s %s %s (forced evil)."),
    "reveal.ninguno": ("No hay ningún mago sin revelar a menos de %s bloques.", "There is no unrevealed wizard within %s blocks."),
    "lista": ("Magos a menos de %s bloques: %s", "Wizards within %s blocks: %s"),
    "lista.linea": (" - %s en %s %s %s: %s", " - %s at %s %s %s: %s"),
    "estado.benigno": ("bondadoso", "benign"),
    "estado.malvado": ("malvado (sin revelar)", "evil (unrevealed)"),
    "estado.sin_decidir": ("aún sin decidir", "not decided yet"),
    "estado.revelado": ("Mago Malvado", "Evil Wizard"),
}
STATE = {
    "estado.chozas_mago": ("Chozas de mago: magos malvados %s %%, botín premium %s %%; vencidos desde el arranque: %s",
                           "Wizard's huts: evil wizards %s %%, premium loot %s %%; defeated since startup: %s"),
}


def _nickname(i):
    return f"{K}.apodo.{i}"


# ---- botín del Mago Malvado (más que una mediana; sin netherita, élitros ni manzanas encantadas)
FORBIDDEN = ("netherite", "elytra", "enchanted_golden_apple")
_PLAYER = {"type": "minecraft:killed_by_player"}


def _pool(rolls, entries):
    p = chest_loot.pool(rolls, entries)
    p["condition"] = _PLAYER           # solo si lo vence un jugador (ni lava ni caídas)
    return p


EVIL = [
    _pool((3, 5), [item("emerald", 10, 3, 8), item("lapis_lazuli", 8, 6, 14), item("experience_bottle", 8, 3, 6),
                   item("ender_pearl", 6, 1, 3), item("glowstone_dust", 5, 3, 8), item("redstone", 5, 4, 10),
                   item("amethyst_shard", 5, 2, 5), item("gold_ingot", 4, 2, 5), item("blaze_powder", 3, 1, 3),
                   item("ghast_tear", 1)]),
    _pool(1, [item("book", 6, ench=(15, 25)), chest_loot.potion("strength", 3), chest_loot.potion("regeneration", 3),
              chest_loot.potion("long_night_vision", 2), item("diamond", 2, 1, 2), item("golden_apple", 2),
              item("iron_sword", 1, ench=(15, 25))]),
]
# el premio: un objeto más fuerte que no rompe la progresión (Decisiones del dueño)
PREMIUM = _pool(1, [
    chest_loot.book(5, {"minecraft:mending": 1}),
    chest_loot.potion("strong_turtle_master", 3), chest_loot.potion("turtle_master", 3), chest_loot.potion("long_slow_falling", 3),
    chest_loot.potion("strong_strength", 3), chest_loot.potion("strong_regeneration", 3),
    item("totem_of_undying", 3),
    chest_loot.book(2, {"minecraft:protection": 4}), chest_loot.book(2, {"minecraft:efficiency": 5}),
    chest_loot.book(2, {"minecraft:sharpness": 5}), chest_loot.book(2, {"minecraft:unbreaking": 3}),
    chest_loot.book(1, {"minecraft:fortune": 3}), chest_loot.book(1, {"minecraft:looting": 3}),
])


def tables():
    """{id corto: tabla} del botín del Mago Malvado (para validate_loot y los tests)."""
    return {"chozas_mago/malvado": {"type": "minecraft:entity", "pools": list(EVIL)},
            "chozas_mago/malvado_premium": {"type": "minecraft:entity", "pools": list(EVIL) + [PREMIUM]}}


def items(tbl):
    """Ids de los objetos de una tabla (con espacio de nombres)."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "minecraft:item":
                out.append(o["name"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(tbl)
    return out


def errors():
    """Reglas del botín (falla la generación): nada prohibido, el premio en la tabla premium y solo en ella."""
    errs = []
    t = tables()
    for name, tbl in t.items():
        for o in items(tbl):
            if any(p in o for p in FORBIDDEN):
                errs.append(f"{name}: {o} rompe la progresión (chozas_mago.PROHIBIDO)")
    if "minecraft:totem_of_undying" in items(t["chozas_mago/malvado"]):
        errs.append("chozas_mago/malvado: el tótem solo puede salir en el premio")
    if len(t["chozas_mago/malvado_premium"]["pools"]) != len(t["chozas_mago/malvado"]["pools"]) + 1:
        errs.append("chozas_mago/malvado_premium: debe ser la normal más el grupo del premio")
    return errs


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    for i, (es, en) in enumerate(NICKNAMES):
        out["es_es"][_nickname(i)], out["en_us"][_nickname(i)] = es, en
    for k, (es, en) in STATE.items():
        out["es_es"][f"{NS}.{k}"], out["en_us"][f"{NS}.{k}"] = es, en
    return out


def schema():
    """heraldia/chozas_mago.json (dentro del .jar): nombres y número de apodos para el Java."""
    return {"nombres": NAMES, "apodos": len(NICKNAMES)}


def write(out, jdump):
    e = errors()
    if e:
        raise SystemExit("\n".join(e))
    for route, tbl in tables().items():
        jdump(out, f"data/{NS}/loot_table/{route}.json", tbl)
    jdump(out, f"{NS}/chozas_mago.json", schema())
