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
TROPHY_MARK = "heraldia_trofeo"   # custom_data {heraldia_trofeo: "<id>"} común a todos los trofeos (logro unicas/trofeos)
RARITIES = ("common", "uncommon", "rare", "epic")
FORBIDDEN_ITEMS = ("netherite", "elytra")   # Decisiones del dueño: nada de netherita en equipo ni élitros
MAX_LEVEL = 3                          # encantamientos moderados


def trophy_key(sid):
    return f"heraldia.trofeo.{sid}"


def trophy_table_id(sid):
    """Tabla con el trofeo solo, sin condiciones (prueba de servidor, /loot)."""
    return f"heraldia:trofeos/{sid}"


def guardian_table_id(sid, mob):
    """Tabla de muerte de un guardián de la única (su DeathLootTable): botín normal + trofeo si lo mata un jugador."""
    return f"heraldia:guardianes/{sid}/{mob.split(':')[-1]}"


def trophy_errors(sid, d):
    """Comprueba el contrato TROFEO de un módulo de unicas/ (ver unicas/__init__.py); [] si está bien."""
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
        # base_color: el escudo (y el estandarte) toma el nombre del color e ignora item_name; usa la capa «base»
        e.append(f"unicas/{sid}: TROFEO.componentes no puede cambiar nombre, lore, rareza, custom_data ni base_color")
    return e


def trophy_predicate(sid, d):
    """Predicado de objeto que reconoce el trofeo (logro «Colecciona todos los trofeos»)."""
    return {"items": "minecraft:" + d["objeto"], "predicates": {"minecraft:custom_data": {TROPHY_MARK: sid}}}


def trophy(sid, d):
    """Tabla de botín con el trofeo de la única: objeto vanilla con nombre traducido (item_name, color de la rareza),
    una o dos líneas de lore, rareza, custom_data común y, si los hay, encantamientos moderados y componentes
    vistosos (adorno de armadura, estandarte...). Sin encantar, brilla igual (enchantment_glint_override)."""
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
    """DeathLootTable de un guardián: su botín de siempre (`original`, p. ej. minecraft:entities/zombie) y el trofeo
    solo si lo mata un jugador (killed_by_player: con /kill o sin jugador no cae)."""
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
    """Entrada de botín: libro escrito. `paginas` y `nombre` son componentes de texto (p. ej. {"translate", "fallback"}):
    el juego guarda las páginas tal cual y el cliente las traduce a su idioma al abrir el libro (resolverlo no cambia los
    translate). El título del libro es una cadena sin traducir (máx. 32) y, si existe, el juego lo pone como nombre: por
    eso el nombre visible va en custom_name (sin cursiva) y, para el objeto en el suelo, también en item_name. `lore`:
    líneas (componentes) en gris."""
    if len(title) > 32:
        raise ValueError(f"título de libro de más de 32 caracteres: {title}")
    comps = {"minecraft:written_book_content": {"title": {"raw": title}, "author": author, "resolved": True,
                                                 "pages": [{"raw": p} for p in pages]},
             "minecraft:custom_name": dict(name, italic=False),
             "minecraft:item_name": name}   # el de la entidad en el suelo (ItemEntity.getName no mira custom_name)
    if lore:
        comps["minecraft:lore"] = [dict(l, color="gray", italic=False) for l in lore]
    comps.update(components or {})
    return {"type": "minecraft:item", "name": "minecraft:written_book", "weight": w,
            "modifier": [{"type": "minecraft:set_components", "components": comps}]}


# ------------------------------------------------------------------ historia: la Crónica de los Heraldos (docs/STORY.md)
# Cada única guarda un pliego (libro escrito) en un cofre suyo ya existente (HISTORIA["cofre"]). Cada pliego cuenta su parte
# y señala la siguiente única de la cadena (con la pista de bioma y rasgo que da ESA única); la cadena se calcula sola a
# partir de las únicas registradas: por id, con la final (la Atlántida) al cabo, que vuelve a señalar la primera.
STORY_MARK = "heraldia_historia"   # custom_data {heraldia_historia: "<id>"} de cada pliego (logro unicas/cronista)
STORY_TITLE = "Crónica de los Heraldos"
STORY_AUTHOR = "Ysolda"
STORY_MAP = 0.10                   # probabilidad de que el pliego venga con el mapa del tesoro de la siguiente única
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


# Página de libro: 14 líneas de 114 px con la fuente por defecto (BookViewScreen). Avance de cada carácter en px
# (ancho del glifo + 1); las letras acentuadas cuentan como su letra base y lo que no está en la tabla, como 6.
BOOK_LINES, BOOK_WIDTH = 14, 114
_WIDTHS = {**dict.fromkeys(" ", 4), **dict.fromkeys("!',.:;|i", 2), **dict.fromkeys("l`", 3),
           **dict.fromkeys("It[]\"“”", 4), **dict.fromkeys("fk(){}<>*", 5), **dict.fromkeys("@~", 7)}
_BASE = str.maketrans("áéíóúüñÁÉÍÓÚÑ", "aeiouunAEIOUN")


def width(text):
    return sum(_WIDTHS.get(c, 6) for c in text.translate(_BASE))


def book_lines(text):
    """Líneas que ocupa `texto` en una página de libro: corta por palabras como el juego (StringSplitter)."""
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
    """Tabla con el pliego de la única (y, a veces, el mapa de la siguiente); la anida la tabla de su cofre."""
    return f"heraldia:historia/{sid}"


def story_predicate(sid):
    return {"items": "minecraft:written_book", "predicates": {"minecraft:custom_data": {STORY_MARK: sid}}}


def story_errors(sid, d, loot):
    """Comprueba el contrato HISTORIA de un módulo de unicas/ (ver unicas/__init__.py); [] si está bien. Cada página
    debe caber en una página de libro, también la que señala esta única con su pista (con números de dos cifras)."""
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
    """[id] en el orden de la cadena: las únicas por id y la final (HISTORIA["final"]) al cabo. Cada una señala la
    siguiente y la final, la primera: todas quedan unidas en un ciclo que pasa por la Atlántida."""
    with_it = [(sid, m.STORY) for sid, m in modules if getattr(m, "STORY", None)]
    return [sid for sid, d in with_it if not d.get("final")] + [sid for sid, d in with_it if d.get("final")]


def story_chain_errors(modules):
    endings = [sid for sid, m in modules if (getattr(m, "STORY", None) or {}).get("final")]
    return [] if len(endings) == 1 else [f"HISTORIA: debe haber una sola única final (la Atlántida), hay {endings}"]


def story_book(sid, d, pos, total, next_unique, next_unique_data, name):
    """Entrada de botín del pliego de `sid` (posición `pos`, 1..total) que señala la única `sig` (con la pista de su
    HISTORIA, `sig_d`). `nombre`: componente con el nombre de la única."""
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
    """Tabla heraldia:historia/<id>: el pliego siempre y, con HISTORIA_MAPA, el mapa del tesoro de la siguiente única."""
    pools = [{"rolls": 1, "entries": [book_entry]}]
    if map_input:
        empty_weight = round((1 - STORY_MAP) / STORY_MAP)
        pools.append({"rolls": 1, "entries": [dict(map_input, weight=1), {"type": "minecraft:empty", "weight": empty_weight}]})
    return {"type": "minecraft:chest", "pools": pools}


def with_story(tbl, sid):
    """La tabla del cofre de la única con un grupo más que anida su pliego (heraldia:historia/<id>). Sin marca
    solo_sin_lootr: con Lootr cada jugador encuentra el suyo."""
    return dict(tbl, pools=list(tbl["pools"]) + [
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": story_table_id(sid)}]}])


def story_lang(modules):
    """Textos de la crónica: los comunes y, por única, sus páginas y su pista."""
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
