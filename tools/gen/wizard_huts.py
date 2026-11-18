"""Wizard huts (T43): everything that is not the template (medianas/wizard_hut.py). The logic is in Java (chozas/): with the
world seed and the wizard's chunk it decides whether he is evil (wizard_huts.prob_malvado) and whether his loot carries the prize
(wizard_huts.prob_botin_premium); it reveals him only once and gives him his loot table. This module holds their texts and those tables.

Keys:
  heraldia.chozas_mago.*        what is said to players (reveal, name of the Evil Wizard and of each wizard),
                                /heraldia wizard (operators)
  heraldia.estado.chozas_mago*  the /heraldia status line
Loot tables (mob, not chest: they are not refilled and carry no treasure hint):
  heraldia:chozas_mago/malvado          the Evil Wizard's: higher level than a medium structure (EVIL)
  heraldia:chozas_mago/malvado_premium  the same plus a strong item (PREMIUM), if the prize drops
The vanilla evoker always drops a totem of undying; the Evil Wizard does not (he carries his own table instead of the
evoker's): huts are frequent and one wizard in five is evil, so the totem remains one of the
prize options (one in ~30 evil huts with the default values), not guaranteed loot.
The arguments (%s) are supplied by the Java code (chozas/Magos): do not change their order without changing it there.
"""
from loot import item, empty
from uniques._common import chest_loot

NS = "heraldia"
K = f"{NS}.chozas_mago"
EVIL_TABLE = f"{NS}:chozas_mago/malvado"
PREMIUM_TABLE = f"{NS}:chozas_mago/malvado_premium"
# Wizard names (proper names, the same in all languages) and their nicknames (translated): "Aldric de la Bruma".
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


# ---- Evil Wizard loot (more than a medium structure; no netherite, elytra or enchanted apples)
FORBIDDEN = ("netherite", "elytra", "enchanted_golden_apple")
_PLAYER = {"type": "minecraft:killed_by_player"}


def _pool(rolls, entries):
    p = chest_loot.pool(rolls, entries)
    p["condition"] = _PLAYER           # only if a player defeats him (not lava or falls)
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
# the prize: a stronger item that does not break progression (Decisiones del dueño)
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
    """{short id: table} of the Evil Wizard's loot (for validate_loot and the tests)."""
    return {"chozas_mago/malvado": {"type": "minecraft:entity", "pools": list(EVIL)},
            "chozas_mago/malvado_premium": {"type": "minecraft:entity", "pools": list(EVIL) + [PREMIUM]}}


def items(tbl):
    """Ids of the items in a table (with namespace)."""
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
    """Loot rules (generation fails): nothing forbidden, the prize in the premium table and only there."""
    errs = []
    t = tables()
    for name, tbl in t.items():
        for o in items(tbl):
            if any(p in o for p in FORBIDDEN):
                errs.append(f"{name}: {o} breaks progression (chozas_mago.PROHIBIDO)")
    if "minecraft:totem_of_undying" in items(t["chozas_mago/malvado"]):
        errs.append("chozas_mago/malvado: the totem can only drop as the prize")
    if len(t["chozas_mago/malvado_premium"]["pools"]) != len(t["chozas_mago/malvado"]["pools"]) + 1:
        errs.append("chozas_mago/malvado_premium: must be the normal one plus the prize group")
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
    """heraldia/wizard_huts.json (inside the .jar): names and number of nicknames for the Java code."""
    return {"nombres": NAMES, "apodos": len(NICKNAMES)}


def write(out, jdump):
    e = errors()
    if e:
        raise SystemExit("\n".join(e))
    for route, tbl in tables().items():
        jdump(out, f"data/{NS}/loot_table/{route}.json", tbl)
    jdump(out, f"{NS}/chozas_mago.json", schema())
