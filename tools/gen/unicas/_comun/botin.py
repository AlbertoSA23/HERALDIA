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


# ------------------------------------------------------------------ trofeos de los guardianes
TROFEO_MARCA = "heraldia_trofeo"   # custom_data {heraldia_trofeo: "<id>"} común a todos los trofeos (logro unicas/trofeos)
RAREZAS = ("common", "uncommon", "rare", "epic")
PROHIBIDOS = ("netherite", "elytra")   # Decisiones de Alberto: nada de netherita en equipo ni élitros
MAX_NIVEL = 3                          # encantamientos moderados


def trofeo_clave(sid):
    return f"heraldia.trofeo.{sid}"


def trofeo_tabla_id(sid):
    """Tabla con el trofeo solo, sin condiciones (prueba de servidor, /loot)."""
    return f"heraldia:trofeos/{sid}"


def guardian_tabla_id(sid, mob):
    """Tabla de muerte de un guardián de la única (su DeathLootTable): botín normal + trofeo si lo mata un jugador."""
    return f"heraldia:guardianes/{sid}/{mob.split(':')[-1]}"


def trofeo_errores(sid, d):
    """Comprueba el contrato TROFEO de un módulo de unicas/ (ver unicas/__init__.py); [] si está bien."""
    if not d:
        return [f"unicas/{sid}: falta TROFEO (trofeo del guardián, ver unicas/__init__.py)"]
    e = []
    obj = d.get("objeto", "")
    if not obj or any(p in obj for p in PROHIBIDOS):
        e.append(f"unicas/{sid}: objeto de trofeo no válido «{obj}»")
    if len(d.get("nombre") or ()) != 2:
        e.append(f"unicas/{sid}: TROFEO.nombre debe ser (es, en)")
    lore = d.get("lore") or ()
    if not 1 <= len(lore) <= 2 or any(len(l) != 2 for l in lore):
        e.append(f"unicas/{sid}: TROFEO.lore debe tener una o dos líneas (es, en)")
    if d.get("rareza", "uncommon") not in RAREZAS:
        e.append(f"unicas/{sid}: rareza de trofeo no válida {d.get('rareza')}")
    for ench, lvl in (d.get("encantamientos") or {}).items():
        if not 1 <= lvl <= MAX_NIVEL:
            e.append(f"unicas/{sid}: encantamiento {ench} {lvl} fuera de 1..{MAX_NIVEL}")
    extra = d.get("componentes") or {}
    if any(k in extra for k in ("minecraft:custom_data", "minecraft:item_name", "minecraft:lore", "minecraft:rarity",
                                "minecraft:base_color", "minecraft:custom_name")):
        # base_color: el escudo (y el estandarte) toma el nombre del color e ignora item_name; usa la capa «base»
        e.append(f"unicas/{sid}: TROFEO.componentes no puede cambiar nombre, lore, rareza, custom_data ni base_color")
    return e


def trofeo_predicado(sid, d):
    """Predicado de objeto que reconoce el trofeo (logro «Colecciona todos los trofeos»)."""
    return {"items": "minecraft:" + d["objeto"], "predicates": {"minecraft:custom_data": {TROFEO_MARCA: sid}}}


def trofeo(sid, d):
    """Tabla de botín con el trofeo de la única: objeto vanilla con nombre traducido (item_name, color de la rareza),
    una o dos líneas de lore, rareza, custom_data común y, si los hay, encantamientos moderados y componentes
    vistosos (adorno de armadura, estandarte...). Sin encantar, brilla igual (enchantment_glint_override)."""
    k = trofeo_clave(sid)
    lore = [{"translate": f"{k}.lore{i + 1}", "fallback": es, "color": "gray", "italic": True}
            for i, (es, _) in enumerate(d["lore"])]
    comps = {"minecraft:custom_data": {TROFEO_MARCA: sid}, "minecraft:rarity": d.get("rareza", "uncommon"),
             "minecraft:lore": lore, "minecraft:max_stack_size": 1}
    if not d.get("encantamientos"):
        comps["minecraft:enchantment_glint_override"] = True
    comps.update(d.get("componentes") or {})
    mods = [{"type": "minecraft:set_name", "name": {"translate": k, "fallback": d["nombre"][0]}, "target": "item_name"},
            {"type": "minecraft:set_components", "components": comps}]
    if d.get("encantamientos"):
        mods.append({"type": "minecraft:set_enchantments", "enchantments": dict(d["encantamientos"])})
    return {"pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "minecraft:" + d["objeto"],
                                                "modifier": mods}]}]}


def guardian_tabla(sid, original):
    """DeathLootTable de un guardián: su botín de siempre (`original`, p. ej. minecraft:entities/zombie) y el trofeo
    solo si lo mata un jugador (killed_by_player: con /kill o sin jugador no cae)."""
    return {"type": "minecraft:entity", "pools": [
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": original}]},
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": trofeo_tabla_id(sid)}],
         "condition": {"type": "minecraft:killed_by_player"}}]}


def trofeo_lang(sid, d):
    k = trofeo_clave(sid)
    names = {"": d["nombre"], **{f".lore{i + 1}": l for i, l in enumerate(d["lore"])}}
    return lang(k, names)
