"""Ayudantes comunes de botín: grupos (con el extra solo_sin_lootr), tablas y objetos con nombre."""
from loot import item


def pool(rolls, entries, extra=False):
    p = {"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
         "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


def named(name, w, key, fallback, ench=None, lo=1, hi=1, levels=None):
    """Objeto con nombre traducible (item_name, sin cursiva). `ench`: encantamientos fijos {id: nivel};
    `levels`: (mín, máx) para encantar al azar como loot.item(ench=...)."""
    e = item(name, w, lo, hi, ench=levels)
    mods = [{"type": "minecraft:set_name", "name": {"translate": key, "fallback": fallback}, "target": "item_name"}]
    if ench:
        mods.append({"type": "minecraft:set_enchantments", "enchantments": ench})
    old = e.pop("modifier", None)
    e["modifier"] = ([old] if isinstance(old, dict) else (old or [])) + mods
    return e


def book(w, ench):
    return {"type": "minecraft:item", "name": "minecraft:book", "weight": w,
            "modifier": {"type": "minecraft:set_enchantments", "enchantments": ench}}
