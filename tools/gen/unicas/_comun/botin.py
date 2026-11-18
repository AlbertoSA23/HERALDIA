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
PROHIBIDOS = ("netherite", "elytra")   # Decisiones del dueño: nada de netherita en equipo ni élitros
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


# ------------------------------------------------------------------ libros escritos
def libro(paginas, nombre, titulo, autor, lore=(), componentes=None, w=1):
    """Entrada de botín: libro escrito. `paginas` y `nombre` son componentes de texto (p. ej. {"translate", "fallback"}):
    el juego guarda las páginas tal cual y el cliente las traduce a su idioma al abrir el libro (resolverlo no cambia los
    translate). El título del libro es una cadena sin traducir (máx. 32) y, si existe, el juego lo pone como nombre: por
    eso el nombre visible va en custom_name (sin cursiva) y, para el objeto en el suelo, también en item_name. `lore`:
    líneas (componentes) en gris."""
    if len(titulo) > 32:
        raise ValueError(f"título de libro de más de 32 caracteres: {titulo}")
    comps = {"minecraft:written_book_content": {"title": {"raw": titulo}, "author": autor, "resolved": True,
                                                 "pages": [{"raw": p} for p in paginas]},
             "minecraft:custom_name": dict(nombre, italic=False),
             "minecraft:item_name": nombre}   # el de la entidad en el suelo (ItemEntity.getName no mira custom_name)
    if lore:
        comps["minecraft:lore"] = [dict(l, color="gray", italic=False) for l in lore]
    comps.update(componentes or {})
    return {"type": "minecraft:item", "name": "minecraft:written_book", "weight": w,
            "modifier": [{"type": "minecraft:set_components", "components": comps}]}


# ------------------------------------------------------------------ historia: la Crónica de los Heraldos (docs/STORY.md)
# Cada única guarda un pliego (libro escrito) en un cofre suyo ya existente (HISTORIA["cofre"]). Cada pliego cuenta su parte
# y señala la siguiente única de la cadena (con la pista de bioma y rasgo que da ESA única); la cadena se calcula sola a
# partir de las únicas registradas: por id, con la final (la Atlántida) al cabo, que vuelve a señalar la primera.
HISTORIA_MARCA = "heraldia_historia"   # custom_data {heraldia_historia: "<id>"} de cada pliego (logro unicas/cronista)
HISTORIA_TITULO = "Crónica de los Heraldos"
HISTORIA_AUTOR = "Ysolda"
HISTORIA_MAPA = 0.10                   # probabilidad de que el pliego venga con el mapa del tesoro de la siguiente única
MAX_PAGINAS_RELATO = 2
HISTORIA_TEXTOS = {
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
LIBRO_LINEAS, LIBRO_ANCHO = 14, 114
_ANCHOS = {**dict.fromkeys(" ", 4), **dict.fromkeys("!',.:;|i", 2), **dict.fromkeys("l`", 3),
           **dict.fromkeys("It[]\"“”", 4), **dict.fromkeys("fk(){}<>*", 5), **dict.fromkeys("@~", 7)}
_BASE = str.maketrans("áéíóúüñÁÉÍÓÚÑ", "aeiouunAEIOUN")


def ancho(texto):
    return sum(_ANCHOS.get(c, 6) for c in texto.translate(_BASE))


def lineas_libro(texto):
    """Líneas que ocupa `texto` en una página de libro: corta por palabras como el juego (StringSplitter)."""
    n = 0
    for parrafo in texto.split("\n"):
        n, ancho_linea = n + 1, 0
        for palabra in parrafo.split(" "):
            w = ancho(palabra)
            if ancho_linea and ancho_linea + ancho(" ") + w > LIBRO_ANCHO:
                n, ancho_linea = n + 1, w
            else:
                ancho_linea += (ancho(" ") if ancho_linea else 0) + w
    return n


def historia_clave(sid=None):
    return "heraldia.historia" + (f".{sid}" if sid else "")


def historia_tabla_id(sid):
    """Tabla con el pliego de la única (y, a veces, el mapa de la siguiente); la anida la tabla de su cofre."""
    return f"heraldia:historia/{sid}"


def historia_predicado(sid):
    return {"items": "minecraft:written_book", "predicates": {"minecraft:custom_data": {HISTORIA_MARCA: sid}}}


def historia_errores(sid, d, loot):
    """Comprueba el contrato HISTORIA de un módulo de unicas/ (ver unicas/__init__.py); [] si está bien. Cada página
    debe caber en una página de libro, también la que señala esta única con su pista (con números de dos cifras)."""
    if not d:
        return [f"unicas/{sid}: falta HISTORIA (su pliego de la Crónica de los Heraldos, ver unicas/__init__.py)"]
    e = []
    if d.get("cofre") not in loot:
        e.append(f"unicas/{sid}: HISTORIA.cofre «{d.get('cofre')}» no es una tabla de su LOOT")
    paginas = []
    relato = d.get("relato") or ()
    if not 1 <= len(relato) <= MAX_PAGINAS_RELATO or any(len(p) != 2 for p in relato):
        e.append(f"unicas/{sid}: HISTORIA.relato debe tener 1-{MAX_PAGINAS_RELATO} páginas (es, en)")
    else:
        paginas += [(f"página {i + 1}", t) for i, p in enumerate(relato) for t in p]
    pista = d.get("pista") or ()
    if len(pista) != 2:
        e.append(f"unicas/{sid}: HISTORIA.pista debe ser (es, en)")
    else:
        paginas += [(f"pista en «{k}»", HISTORIA_TEXTOS[k][i] % (99, 99, pista[i]))
                    for k in ("siguiente", "final") for i in (0, 1)]
    e += [f"unicas/{sid}: {cual} no cabe en una página de libro ({lineas_libro(t)} de {LIBRO_LINEAS} líneas): {t[:50]}…"
          for cual, t in paginas if lineas_libro(t) > LIBRO_LINEAS]
    return e


def historia_cadena(modules):
    """[id] en el orden de la cadena: las únicas por id y la final (HISTORIA["final"]) al cabo. Cada una señala la
    siguiente y la final, la primera: todas quedan unidas en un ciclo que pasa por la Atlántida."""
    con = [(sid, m.HISTORIA) for sid, m in modules if getattr(m, "HISTORIA", None)]
    return [sid for sid, d in con if not d.get("final")] + [sid for sid, d in con if d.get("final")]


def historia_cadena_errores(modules):
    finales = [sid for sid, m in modules if (getattr(m, "HISTORIA", None) or {}).get("final")]
    return [] if len(finales) == 1 else [f"HISTORIA: debe haber una sola única final (la Atlántida), hay {finales}"]


def historia_libro(sid, d, pos, total, sig, sig_d, nombre):
    """Entrada de botín del pliego de `sid` (posición `pos`, 1..total) que señala la única `sig` (con la pista de su
    HISTORIA, `sig_d`). `nombre`: componente con el nombre de la única."""
    k = historia_clave(sid)
    paginas = [{"translate": f"{k}.pagina{i + 1}", "fallback": es} for i, (es, _) in enumerate(d["relato"])]
    tipo = "final" if d.get("final") else "siguiente"
    pista = {"translate": f"{historia_clave(sig)}.pista", "fallback": sig_d["pista"][0]}
    paginas.append({"translate": f"{historia_clave()}.{tipo}", "fallback": HISTORIA_TEXTOS[tipo][0],
                    "with": [pos, total, pista]})
    titulo = {"translate": f"{historia_clave()}.nombre", "with": [nombre],
              "fallback": HISTORIA_TEXTOS["nombre"][0] % nombre.get("fallback", sid)}
    return libro(paginas, titulo, HISTORIA_TITULO, HISTORIA_AUTOR,
                 lore=[{"translate": f"{historia_clave()}.lore", "fallback": HISTORIA_TEXTOS["lore"][0] % (pos, total)}],
                 componentes={"minecraft:custom_data": {HISTORIA_MARCA: sid}, "minecraft:rarity": "uncommon"})


def historia_tabla(libro_entrada, mapa_entrada=None):
    """Tabla heraldia:historia/<id>: el pliego siempre y, con HISTORIA_MAPA, el mapa del tesoro de la siguiente única."""
    pools = [{"rolls": 1, "entries": [libro_entrada]}]
    if mapa_entrada:
        vacio = round((1 - HISTORIA_MAPA) / HISTORIA_MAPA)
        pools.append({"rolls": 1, "entries": [dict(mapa_entrada, weight=1), {"type": "minecraft:empty", "weight": vacio}]})
    return {"type": "minecraft:chest", "pools": pools}


def con_historia(tabla, sid):
    """La tabla del cofre de la única con un grupo más que anida su pliego (heraldia:historia/<id>). Sin marca
    solo_sin_lootr: con Lootr cada jugador encuentra el suyo."""
    return dict(tabla, pools=list(tabla["pools"]) + [
        {"rolls": 1, "entries": [{"type": "minecraft:loot_table", "value": historia_tabla_id(sid)}]}])


def historia_lang(modules):
    """Textos de la crónica: los comunes y, por única, sus páginas y su pista."""
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in HISTORIA_TEXTOS.items():
        out["es_es"][f"{historia_clave()}.{k}"], out["en_us"][f"{historia_clave()}.{k}"] = es, en
    for sid, m in modules:
        d = m.HISTORIA
        names = {f".pagina{i + 1}": p for i, p in enumerate(d["relato"])}
        names[".pista"] = d["pista"]
        for lang_, t in lang(historia_clave(sid), names).items():
            out[lang_].update(t)
    return out
