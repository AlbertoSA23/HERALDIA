"""Botín común de las estructuras únicas (solo vanilla)."""
from loot import item, empty  # noqa: F401  (reexportados para los módulos)


def _rolls(r):
    return r if isinstance(r, int) else {"type": "minecraft:uniform", "min": r[0], "max": r[1]}


def pool(rolls, entries, extra=False):
    """Grupo de botín; extra=True lo marca solo_sin_lootr (se omite si el servidor lleva Lootr)."""
    p = {"rolls": _rolls(rolls), "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


def cofre(base, extra):
    """Tabla típica de cofre: (tiradas, entradas) siempre y (tiradas, entradas) extra sin Lootr."""
    return table(pool(*base), pool(*extra, extra=True))


def _mods(e):
    old = e.pop("modifier", None)
    return [old] if isinstance(old, dict) else (old or [])


def named(name, w, key, fallback, ench=None, lo=1, hi=1, mods=(), levels=None):
    """Objeto con nombre traducible (item_name), encantamientos fijos (`ench`) o por niveles (`levels`, (min, max))
    opcionales y modificadores extra."""
    e = item(name, w, lo, hi, ench=levels)
    m = _mods(e) + [{"type": "minecraft:set_name", "name": {"translate": key, "fallback": fallback}, "target": "item_name"}]
    if ench:
        m.append({"type": "minecraft:set_enchantments", "enchantments": ench})
    e["modifier"] = m + list(mods)
    return e


def book(w, ench):
    """Libro con encantamientos fijos (se convierte en libro encantado)."""
    return {"type": "minecraft:item", "name": "minecraft:book", "weight": w,
            "modifier": {"type": "minecraft:set_enchantments", "enchantments": ench}}


def random_ench():
    return {"type": "minecraft:enchant_randomly", "options": "#minecraft:on_random_loot"}


def potion(pid, w, key=None, fallback=None):
    m = [{"type": "minecraft:set_potion", "id": "minecraft:" + pid}]
    if key:
        m.insert(0, {"type": "minecraft:set_name", "name": {"translate": key, "fallback": fallback}, "target": "item_name"})
    e = item("potion", w)
    e["modifier"] = m if len(m) > 1 else m[0]
    return e


def lang(prefix, names):
    """{clave: (es, en)} -> LANG del módulo con las claves prefijadas."""
    return {"es_es": {prefix + k: v[0] for k, v in names.items()}, "en_us": {prefix + k: v[1] for k, v in names.items()}}
