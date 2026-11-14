"""Ayudas de botín para estructuras únicas (sobre loot.py): tabla base + extra sin Lootr, objetos con nombre, pociones."""


def rolls(r):
    return r if isinstance(r, int) else {"type": "minecraft:uniform", "min": r[0], "max": r[1]}


def tabla(base, extra, *mas):
    """base y extra: (tiradas, entradas). El extra se marca solo_sin_lootr (con Lootr cada jugador recibe lo base).
    `mas`: grupos adicionales (tiradas, entradas) que se dan siempre."""
    pools = [{"rolls": rolls(base[0]), "entries": base[1]}] + [{"rolls": rolls(r), "entries": e} for r, e in mas]
    pools.append({"rolls": rolls(extra[0]), "entries": extra[1], "solo_sin_lootr": True})
    return {"type": "minecraft:chest", "pools": pools}


def con_nombre(item, key, fallback, w, ench=None, count=1):
    """Objeto con nombre traducible (target item_name) y, si se pide, encantamientos de nivel ench=(min, max)."""
    mods = [{"type": "minecraft:set_name", "target": "item_name", "name": {"translate": key, "fallback": fallback}}]
    if ench:
        mods.append({"type": "minecraft:enchant_with_levels", "levels": {"type": "minecraft:uniform", "min": ench[0], "max": ench[1]},
                     "options": "#minecraft:on_random_loot"})
    if count > 1:
        mods.append({"type": "minecraft:set_count", "count": count})
    return {"type": "minecraft:item", "name": "minecraft:" + item, "weight": w, "modifier": mods}


def pocion(pid, w):
    return {"type": "minecraft:item", "name": "minecraft:potion", "weight": w,
            "modifier": {"type": "minecraft:set_potion", "id": "minecraft:" + pid}}
