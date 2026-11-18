"""Common loot of the unique structures (vanilla only)."""
from loot import item, empty  # noqa: F401  (re-exported for the modules)


def _rolls(r):
    return r if isinstance(r, int) else {"type": "minecraft:uniform", "min": r[0], "max": r[1]}


def pool(rolls, entries, extra=False):
    """Loot group; extra=True marks it solo_sin_lootr (skipped if the server runs Lootr)."""
    p = {"rolls": _rolls(rolls), "entries": entries}
    if extra:
        p["solo_sin_lootr"] = True
    return p


def table(*pools):
    return {"type": "minecraft:chest", "pools": list(pools)}


def place_chest(base, extra):
    """Typical chest table: (rolls, entries) always and (rolls, entries) extra without Lootr."""
    return table(pool(*base), pool(*extra, extra=True))


def _mods(e):
    old = e.pop("modifier", None)
    return [old] if isinstance(old, dict) else (old or [])


def named(name, w, key, fallback, ench=None, lo=1, hi=1, mods=(), levels=None):
    """Item with a translatable name (item_name), optional fixed enchantments (`ench`) or by levels (`levels`, (min, max))
    and extra modifiers."""
    e = item(name, w, lo, hi, ench=levels)
    m = _mods(e) + [{"type": "minecraft:set_name", "name": {"translate": key, "fallback": fallback}, "target": "item_name"}]
    if ench:
        m.append({"type": "minecraft:set_enchantments", "enchantments": ench})
    e["modifier"] = m + list(mods)
    return e


def book(w, ench):
    """Book with fixed enchantments (converted into an enchanted book)."""
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
    """{key: (es, en)} -> the module's LANG with the keys prefixed."""
    return {"es_es": {prefix + k: v[0] for k, v in names.items()}, "en_us": {prefix + k: v[1] for k, v in names.items()}}


# ------------------------------------------------------------------ guardian trophies
TROPHY_MARK = "heraldia_trofeo"   # custom_data {heraldia_trofeo: "<id>"} common to all trophies (advancement unicas/trofeos)
RARITIES = ("common", "uncommon", "rare", "epic")
FORBIDDEN_ITEMS = ("netherite", "elytra")   # Owner's decisions: no netherite gear and no elytra
MAX_LEVEL = 3                          # encantamientos moderados


def trophy_key(sid):
    return f"heraldia.trofeo.{sid}"


def trophy_table_id(sid):
    """Table with the trophy alone, without conditions (server test, /loot)."""
    return f"heraldia:trofeos/{sid}"


def guardian_table_id(sid, mob):
    """Death table of a unique structure's guardian (its DeathLootTable): normal loot + trophy if a player kills it."""
    return f"heraldia:guardianes/{sid}/{mob.split(':')[-1]}"


def trophy_errors(sid, d):
    """Checks the TROPHY contract of a unicas/ module (see unicas/__init__.py); [] if it is fine."""
    if not d:
        return [f"unicas/{sid}: falta TROFEO (trofeo del guardián, ver unicas/__init__.py)"]
    e = []
    obj = d.get("objeto", "")
    if not obj or any(p in obj for p in FORBIDDEN_ITEMS):
        e.append(f"unicas/{sid}: objeto de trofeo no válido «{obj}»")
    if len(d.get("nombre") or ()) != 2:
        e.append(f"unicas/{sid}: TROFEO.nombre debe ser (es, en)")
    lore = d.get("lore") or ()
    if not 1 <= len(lore) <= 2 or any(len(l) != 2 for l in lore):
        e.append(f"unicas/{sid}: TROFEO.lore debe tener una o dos líneas (es, en)")
    if d.get("rareza", "uncommon") not in RARITIES:
        e.append(f"unicas/{sid}: rareza de trofeo no válida {d.get('rareza')}")
    for ench, lvl in (d.get("encantamientos") or {}).items():
        if not 1 <= lvl <= MAX_LEVEL:
            e.append(f"unicas/{sid}: encantamiento {ench} {lvl} fuera de 1..{MAX_LEVEL}")
    extra = d.get("componentes") or {}
    if any(k in extra for k in ("minecraft:custom_data", "minecraft:item_name", "minecraft:lore", "minecraft:rarity",
                                "minecraft:base_color", "minecraft:custom_name")):
        # base_color: the shield (and the banner) takes the color name and ignores item_name; use the "base" layer
        e.append(f"unicas/{sid}: TROFEO.componentes no puede cambiar nombre, lore, rareza, custom_data ni base_color")
    return e


def trophy_predicate(sid, d):
    """Item predicate that recognizes the trophy (advancement "Collect all the trophies")."""
    return {"items": "minecraft:" + d["objeto"], "predicates": {"minecraft:custom_data": {TROPHY_MARK: sid}}}


def trophy(sid, d):
    """Loot table with the unique structure's trophy: vanilla item with a translated name (item_name, rarity color),
    one or two lore lines, rarity, common custom_data and, if any, moderate enchantments and showy components
    (armor trim, banner...). Without enchanting, it still glows (enchantment_glint_override)."""
    k = trophy_key(sid)
    lore = [{"translate": f"{k}.lore{i + 1}", "fallback": es, "color": "gray", "italic": True}
            for i, (es, _) in enumerate(d["lore"])]
    comps = {"minecraft:custom_data": {TROPHY_MARK: sid}, "minecraft:rarity": d.get("rareza", "uncommon"),
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


def guardian_table(sid, original):
    """DeathLootTable of a guardian: its usual loot (`original`, e.g. minecraft:entities/zombie) and the trophy
    only if a player kills it (killed_by_player: with /kill or without a player it does not drop)."""
    return {"type": "minecraft:entity", "pools": [
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": original}]},
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": trophy_table_id(sid)}],
         "condition": {"type": "minecraft:killed_by_player"}}]}


def trophy_lang(sid, d):
    k = trophy_key(sid)
    names = {"": d["nombre"], **{f".lore{i + 1}": l for i, l in enumerate(d["lore"])}}
    return lang(k, names)


# ------------------------------------------------------------------ libros escritos
def written_book(pages, name, title, author, lore=(), components=None, w=1):
    """Loot entry: written book. `pages` and `name` are text components (e.g. {"translate", "fallback"}):
    the game stores the pages as they are and the client translates them to its language when the book is opened (resolving them does not change the
    translate). The book title is an untranslated string (max 32) and, if present, the game uses it as the name: that is
    why the visible name goes in custom_name (no italics) and, for the item on the ground, also in item_name. `lore`:
    lines (components) in gray."""
    if len(title) > 32:
        raise ValueError(f"book title longer than 32 characters: {title}")
    comps = {"minecraft:written_book_content": {"title": {"raw": title}, "author": author, "resolved": True,
                                                 "pages": [{"raw": p} for p in pages]},
             "minecraft:custom_name": dict(name, italic=False),
             "minecraft:item_name": name}   # that of the entity on the ground (ItemEntity.getName does not look at custom_name)
    if lore:
        comps["minecraft:lore"] = [dict(l, color="gray", italic=False) for l in lore]
    comps.update(components or {})
    return {"type": "minecraft:item", "name": "minecraft:written_book", "weight": w,
            "modifier": [{"type": "minecraft:set_components", "components": comps}]}


# ------------------------------------------------------------------ story: the Chronicle of the Heralds (docs/STORY.md)
# Each unique structure keeps a sheet (written book) in one of its own existing chests (STORY["cofre"]). Each sheet tells its part
# and points to the next unique structure in the chain (with the biome and feature hint that THAT structure gives); the chain is computed automatically from
# the registered unique structures: by id, with the final one (Atlantis) at the end, which points back to the first.
STORY_MARK = "heraldia_historia"   # custom_data {heraldia_historia: "<id>"} of each sheet (advancement unicas/cronista)
STORY_TITLE = "Crónica de los Heraldos"
STORY_AUTHOR = "Ysolda"
STORY_MAP = 0.10                   # probability that the sheet comes with the treasure map of the next unique structure
MAX_PAGES_TALE = 2
STORY_TEXTS = {
    "nombre": ("Crónica de los Heraldos: %s", "Chronicle of the Heralds: %s"),
    "lore": ("Pliego %s de %s", "Leaf %s of %s"),
    "siguiente": ("Pliego %s de %s.\n\nEl siguiente pliego lo llevé hasta %s.",
                  "Leaf %s of %s.\n\nThe next leaf I carried to %s."),
    "final": ("Pliego %s de %s.\n\nAquí acaba la crónica y aquí empezó mi viaje. Quien quiera leerla de nuevo, que busque "
              "el primer pliego en %s.",
              "Leaf %s of %s.\n\nHere the chronicle ends, and here my journey began. Whoever would read it again, let them "
              "seek the first leaf in %s."),
}


# Book page: 14 lines of 114 px with the default font (BookViewScreen). Advance of each character in px
# (glyph width + 1); accented letters count as their base letter and anything not in the table counts as 6.
BOOK_LINES, BOOK_WIDTH = 14, 114
_WIDTHS = {**dict.fromkeys(" ", 4), **dict.fromkeys("!',.:;|i", 2), **dict.fromkeys("l`", 3),
           **dict.fromkeys("It[]\"“”", 4), **dict.fromkeys("fk(){}<>*", 5), **dict.fromkeys("@~", 7)}
_BASE = str.maketrans("áéíóúüñÁÉÍÓÚÑ", "aeiouunAEIOUN")


def width(text):
    return sum(_WIDTHS.get(c, 6) for c in text.translate(_BASE))


def book_lines(text):
    """Lines that `text` takes up on a book page: wraps by words like the game (StringSplitter)."""
    n = 0
    for paragraph in text.split("\n"):
        n, line_width = n + 1, 0
        for word in paragraph.split(" "):
            w = width(word)
            if line_width and line_width + width(" ") + w > BOOK_WIDTH:
                n, line_width = n + 1, w
            else:
                line_width += (width(" ") if line_width else 0) + w
    return n


def story_key(sid=None):
    return "heraldia.historia" + (f".{sid}" if sid else "")


def story_table_id(sid):
    """Table with the unique structure's sheet (and, sometimes, the map of the next one); the table of its chest nests it."""
    return f"heraldia:historia/{sid}"


def story_predicate(sid):
    return {"items": "minecraft:written_book", "predicates": {"minecraft:custom_data": {STORY_MARK: sid}}}


def story_errors(sid, d, loot):
    """Checks the STORY contract of a unicas/ module (see unicas/__init__.py); [] if it is fine. Each page
    must fit on a book page, including the one that this unique structure points with its hint (with two-digit numbers)."""
    if not d:
        return [f"unicas/{sid}: falta HISTORIA (su pliego de la Crónica de los Heraldos, ver unicas/__init__.py)"]
    e = []
    if d.get("cofre") not in loot:
        e.append(f"unicas/{sid}: HISTORIA.cofre «{d.get('cofre')}» no es una tabla de su LOOT")
    pages = []
    tale = d.get("relato") or ()
    if not 1 <= len(tale) <= MAX_PAGES_TALE or any(len(p) != 2 for p in tale):
        e.append(f"unicas/{sid}: HISTORIA.relato debe tener 1-{MAX_PAGES_TALE} páginas (es, en)")
    else:
        pages += [(f"página {i + 1}", t) for i, p in enumerate(tale) for t in p]
    clue = d.get("pista") or ()
    if len(clue) != 2:
        e.append(f"unicas/{sid}: HISTORIA.pista debe ser (es, en)")
    else:
        pages += [(f"pista en «{k}»", STORY_TEXTS[k][i] % (99, 99, clue[i]))
                    for k in ("siguiente", "final") for i in (0, 1)]
    e += [f"unicas/{sid}: {which} no cabe en una página de libro ({book_lines(t)} de {BOOK_LINES} líneas): {t[:50]}…"
          for which, t in pages if book_lines(t) > BOOK_LINES]
    return e


def story_chain(modules):
    """[id] in chain order: the unique structures by id and the final one (STORY["final"]) at the end. Each one points to the
    next and the final one to the first: all are joined in a cycle that passes through Atlantis."""
    with_it = [(sid, m.STORY) for sid, m in modules if getattr(m, "STORY", None)]
    return [sid for sid, d in with_it if not d.get("final")] + [sid for sid, d in with_it if d.get("final")]


def story_chain_errors(modules):
    endings = [sid for sid, m in modules if (getattr(m, "STORY", None) or {}).get("final")]
    return [] if len(endings) == 1 else [f"HISTORIA: debe haber una sola única final (la Atlántida), hay {endings}"]


def story_book(sid, d, pos, total, next_unique, next_unique_data, name):
    """Loot entry of the sheet of `sid` (position `pos`, 1..total) that points to the unique structure `next_unique` (with the hint from its
    STORY, `next_unique_data`). `name`: component with the unique structure's name."""
    k = story_key(sid)
    pages = [{"translate": f"{k}.pagina{i + 1}", "fallback": es} for i, (es, _) in enumerate(d["relato"])]
    kind = "final" if d.get("final") else "siguiente"
    clue = {"translate": f"{story_key(next_unique)}.pista", "fallback": next_unique_data["pista"][0]}
    pages.append({"translate": f"{story_key()}.{kind}", "fallback": STORY_TEXTS[kind][0],
                    "with": [pos, total, clue]})
    title = {"translate": f"{story_key()}.nombre", "with": [name],
              "fallback": STORY_TEXTS["nombre"][0] % name.get("fallback", sid)}
    return written_book(pages, title, STORY_TITLE, STORY_AUTHOR,
                 lore=[{"translate": f"{story_key()}.lore", "fallback": STORY_TEXTS["lore"][0] % (pos, total)}],
                 components={"minecraft:custom_data": {STORY_MARK: sid}, "minecraft:rarity": "uncommon"})


def story_table(book_entry, map_input=None):
    """Table heraldia:historia/<id>: the sheet always and, with STORY_MAP, the treasure map of the next unique structure."""
    pools = [{"rolls": 1, "entries": [book_entry]}]
    if map_input:
        empty_weight = round((1 - STORY_MAP) / STORY_MAP)
        pools.append({"rolls": 1, "entries": [dict(map_input, weight=1), {"type": "minecraft:empty", "weight": empty_weight}]})
    return {"type": "minecraft:chest", "pools": pools}


def with_story(tbl, sid):
    """The unique structure's chest table with one more group that nests its sheet (heraldia:historia/<id>). Without the
    solo_sin_lootr mark: with Lootr each player finds their own."""
    return dict(tbl, pools=list(tbl["pools"]) + [
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": story_table_id(sid)}]}])


def story_lang(modules):
    """Chronicle texts: the common ones and, per unique structure, its pages and its hint."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in STORY_TEXTS.items():
        out["es_es"][f"{story_key()}.{k}"], out["en_us"][f"{story_key()}.{k}"] = es, en
    for sid, m in modules:
        d = m.STORY
        names = {f".pagina{i + 1}": p for i, p in enumerate(d["relato"])}
        names[".pista"] = d["pista"]
        for lang_, t in lang(story_key(sid), names).items():
            out[lang_].update(t)
    return out
