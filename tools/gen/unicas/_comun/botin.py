"""Ayudas de botín comunes (solo vanilla). Cada cofre: grupo base y grupo extra marcado solo_sin_lootr."""
from loot import item


def pool(rolls, entries, extra=False):
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


def chest(base, extra, rolls=(3, 6), extra_rolls=(1, 3)):
    """Cofre típico: base siempre y extra solo sin Lootr (con Lootr cada jugador abre lo modesto)."""
    return table(pool(rolls, base), pool(extra_rolls, extra, extra=True))


def named(name, w, key, fallback, lo=1, hi=1, ench=None, rand_ench=False, enchantments=None):
    """Objeto con nombre traducible. ench: niveles de encantamiento al azar; enchantments: {id: nivel} fijos."""
    e = item(name, w, lo, hi, ench=ench, rand_ench=rand_ench)
    old = e.pop("modifier", None)
    mods = [old] if isinstance(old, dict) else (old or [])
    mods.append({"type": "minecraft:set_name", "target": "item_name", "name": {"translate": key, "fallback": fallback}})
    if enchantments:
        mods.append({"type": "minecraft:set_enchantments", "enchantments": enchantments})
    e["modifier"] = mods
    return e
