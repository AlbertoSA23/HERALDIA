"""Idiomas del mod: es_es y en_us salen de los módulos (tuplas (es, en) y diccionarios LANG); los demás, de las
traducciones de tools/gen/languages/<código>.json ({clave: texto}).

Fuente única de las claves: el es_es que arma el generador (writer.textos). Cada traducción debe tener exactamente esas
claves (ni una de más ni de menos), los mismos huecos de formato que el inglés (%s, %1$s, %%: los mismos argumentos, en
el orden que pida la frase) y caber en las páginas de libro donde se usa (botin.lineas_libro). Si algo falla, la
generación se detiene (writer.write) y los tests lo dicen (tests/test_idiomas.py).

Clientes sin el mod (Textos.idioma en Java): heraldia/idiomas.json dice qué código del .jar corresponde a cada lengua de
Minecraft (la parte antes de «_»: fr_ca -> fr_fr, pt_pt -> pt_br, es_mx -> es_es); una lengua sin idioma propio, inglés.

Para comprobar una traducción a mano (tras generar con ./gradlew build): python3 tools/gen/languages.py fr_fr
"""
import json
import os
import re
import sys

BASE = ("es_es", "en_us")
# código del .jar -> nombre del idioma (en su lengua). El orden es el de los README y de /heraldia info.
TRANSLATIONS = {
    "fr_fr": "Français",
    "de_de": "Deutsch",
    "it_it": "Italiano",
    "pt_br": "Português (Brasil)",
    "ca_es": "Català",
    "gl_es": "Galego",
}
NAMES = {"en_us": "English", "es_es": "Español", **TRANSLATIONS}
# README homólogo de cada idioma en el repositorio (el inglés es el principal); tests/test_readme.py los mantiene
# sincronizados y con el selector de idiomas, en este orden.
README = {"en_us": "README.md", "es_es": "README.es.md", "fr_fr": "README.fr.md", "de_de": "README.de.md",
          "it_it": "README.it.md", "pt_br": "README.pt-BR.md", "ca_es": "README.ca.md", "gl_es": "README.gl.md"}
# Lenguas de Minecraft cuyo código no empieza por la de su idioma en el mod: valenciano (val_es) y andaluz (esan).
ALIAS = {"val": "ca_es", "esan": "es_es"}
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages")
FILL = "X" * 24        # texto de un traducible que no es del mod (p. ej. el nombre vanilla de un objeto): peor caso

_MARK = re.compile(r"%(?:(\d+)\$)?([a-zA-Z%])")


def everyone():
    """Todos los códigos de idioma del mod, los base primero."""
    return list(BASE) + list(TRANSLATIONS)


def locale(lang_code):
    return lang_code.split("_", 1)[0]


def mc_locales():
    """{lengua: código del .jar} para heraldia/idiomas.json (lo lee Textos.codigo en Java)."""
    out = {locale(c): c for c in everyone()}
    out.update(ALIAS)
    return out


def route(lang_code):
    return os.path.join(FOLDER, f"{lang_code}.json")


def load_data(lang_code):
    """{clave: texto} de una traducción (tools/gen/languages/<código>.json); {} si aún no existe."""
    if not os.path.exists(route(lang_code)):
        return {}
    with open(route(lang_code), encoding="utf-8") as f:
        return json.load(f)


def markers(text):
    """Argumentos que usa un texto de formato de Minecraft (TranslatableContents): ([índices 1..n], nº de %%) o
    None si tiene un marcador que el juego no entiende (solo %s, %n$s y %%)."""
    indices, literals, following = [], 0, 1
    for m in _MARK.finditer(text):
        pos, kind = m.groups()
        if kind == "%":
            literals += 1
        elif kind != "s":
            return None
        elif pos:
            indices.append(int(pos))
        else:
            indices.append(following)
            following += 1
    return sorted(indices), literals


def key_errors(base, translated, lang_code):
    """Claves que faltan o sobran en la traducción `trad` frente a `base` (el es_es)."""
    e = [f"{lang_code}: falta la clave {k}" for k in base if k not in translated]
    e += [f"{lang_code}: sobra la clave {k}" for k in translated if k not in base]
    e += [f"{lang_code}: {k} está vacía" for k, v in translated.items() if k in base and not str(v).strip()]
    return e


def marker_errors(en, translated, lang_code):
    """Huecos de formato distintos de los del inglés (que son los mismos que los del español)."""
    e = []
    for k, t in translated.items():
        if k in en:
            m, expected = markers(t), markers(en[k])
            if m is None:
                e.append(f"{lang_code}: {k} tiene un marcador desconocido: {t!r}")
            elif m != expected:
                e.append(f"{lang_code}: {k} usa los huecos {m}, el inglés {expected}: {t!r}")
    return e


def format_text(fmt, args):
    """Como TranslatableContents: %s, %n$s y %%."""
    it = iter(range(len(args)))

    def sub(m):
        pos, kind = m.groups()
        if kind == "%":
            return "%"
        i = int(pos) - 1 if pos else next(it, len(args))
        return args[i] if 0 <= i < len(args) else ""
    return _MARK.sub(sub, fmt)


def text(comp, texts):
    """Texto plano de un componente en el idioma `textos` (lo que pinta un cliente con el mod)."""
    if isinstance(comp, (int, float)):
        return str(comp)
    if isinstance(comp, str):
        return comp
    if isinstance(comp, list):
        return "".join(text(c, texts) for c in comp)
    if "translate" in comp:
        fmt = texts.get(comp["translate"])
        s = FILL if fmt is None else format_text(fmt, [text(a, texts) for a in comp.get("with", [])])
    else:
        s = str(comp.get("text", ""))
    return s + "".join(text(c, texts) for c in comp.get("extra", []))


def book_pages(items):
    """[(dónde, página)] de todos los libros escritos (written_book_content) que haya dentro de `objetos` (tablas de
    botín, tratos, NBT de bloques...), con la página como componente."""
    out = []

    def show(o, where):
        if isinstance(o, dict):
            written_book = o.get("minecraft:written_book_content")
            if isinstance(written_book, dict):
                for i, p in enumerate(written_book.get("pages", [])):
                    out.append((f"{where} p{i + 1}", p.get("raw", p) if isinstance(p, dict) else p))
            for v in o.values():
                show(v, where)
        elif isinstance(o, (list, tuple)):
            for v in o:
                show(v, where)
    for where, o in items:
        show(o, where)
    return out


def book_errors(pages, texts, lang_code):
    """Páginas de libro que no caben en este idioma (14 líneas de 114 px, como el juego)."""
    from uniques._common import chest_loot
    e = []
    for where, p in pages:
        t = text(p, texts)
        if chest_loot.book_lines(t) > chest_loot.BOOK_LINES:
            e.append(f"{lang_code}: la página de libro {where} no cabe ({chest_loot.book_lines(t)} de {chest_loot.BOOK_LINES} "
                     f"líneas): {t[:60]}…")
    return e


SIGN_WIDTH = 90          # SignBlockEntity: ancho máximo de una línea de cartel, en px


def sign_keys(items):
    """Claves traducibles de las líneas de cartel (front_text/back_text) que haya dentro de `objetos` (NBT de bloques):
    {clave: en negrita}. La negrita suma 1 px a cada carácter (el desplazamiento de la negrita de la fuente)."""
    out = {}

    def show(o):
        if isinstance(o, dict):
            for side in ("front_text", "back_text"):
                for m in (o.get(side) or {}).get("messages", []) if isinstance(o.get(side), dict) else []:
                    if isinstance(m, dict) and "translate" in m:
                        out[m["translate"]] = out.get(m["translate"], False) or bool(m.get("bold"))
            for v in o.values():
                show(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                show(v)
    for o in items:
        show(o)
    return out


def sign_errors(keys, texts, lang_code):
    """Líneas de cartel más anchas que el cartel (90 px) en este idioma, también en es/en: el cliente (SignRenderer)
    corta la línea por palabras a 90 px y lo que sobra no se ve.
    `claves`: las de claves_de_carteles ({clave: en negrita}) o un conjunto de claves (sin negrita)."""
    e = []
    for k in sorted(keys):
        if k in texts and sign_width(texts[k], isinstance(keys, dict) and keys[k]) > SIGN_WIDTH:
            e.append(f"{lang_code}: la línea de cartel {k} no cabe ({sign_width(texts[k], isinstance(keys, dict) and keys[k])} "
                     f"de {SIGN_WIDTH} px): {texts[k]!r}")
    return e


def sign_width(text, bold=False):
    """Ancho en px de una línea de cartel: el de botin.ancho, más 1 px por carácter en negrita."""
    from uniques._common import chest_loot
    return chest_loot.width(text) + (len(text) if bold else 0)


def sort_items(base, translated):
    """La traducción con las claves en el orden del es_es (las que no están en él, al final)."""
    return {**{k: translated[k] for k in base if k in translated}, **{k: v for k, v in translated.items() if k not in base}}


def complete(base, pages=(), signs=()):
    """{código: textos} de todos los idiomas a partir de los base ({"es_es": ..., "en_us": ...}) y las traducciones.
    `paginas`: las de los libros escritos (paginas_de_libros), que deben caber en cada idioma; `carteles`: claves de
    las líneas de cartel (claves_de_carteles). Lanza SystemExit con todos los errores si una traducción no está
    completa o no cabe."""
    es, en = base["es_es"], base["en_us"]
    out, e = {"es_es": es, "en_us": en}, []
    for lang_code in BASE:
        e += book_errors(pages, base[lang_code], lang_code) + sign_errors(signs, base[lang_code], lang_code)
    for lang_code in TRANSLATIONS:
        translated = load_data(lang_code)
        e += key_errors(es, translated, lang_code) + marker_errors(en, translated, lang_code)
        e += book_errors(pages, {**en, **translated}, lang_code) + sign_errors(signs, translated, lang_code)
        out[lang_code] = sort_items(es, translated)
    if e:
        raise SystemExit("IDIOMAS:\n" + "\n".join(e[:200]) + (f"\n… y {len(e) - 200} más" if len(e) > 200 else ""))
    return out


def _check(lang_codes):
    """Uso a mano: compara cada traducción con el es_es/en_us ya generados (build/generated/heraldia)."""
    root = os.path.join(os.path.dirname(FOLDER), "..", "..", "build", "generated", "heraldia")
    lang = os.path.join(root, "assets", "heraldia", "lang")
    base = {}
    for c in BASE:
        with open(os.path.join(lang, f"{c}.json"), encoding="utf-8") as f:
            base[c] = json.load(f)
    pages = []
    for d, _, fs in os.walk(os.path.join(root, "data")):
        for f in fs:
            if f.endswith(".json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    pages += book_pages([(f, json.load(fh))])
    # los libros de los atriles de las plantillas (tablón, torre del mago) no están en data/: por su clave
    pages += [(k, {"translate": k, "with": [FILL] * 3}) for k in base["es_es"]
                if re.fullmatch(r"heraldia\.(tablon\.p\d+|unicas\.torre_mago\.diario\.\d+)", k)]
    signs = {k for k in base["es_es"] if ".cartel." in k}
    import guide, uniques
    bad_many = 0
    for c in BASE:
        e = sign_errors(signs, base[c], c)
        print("\n".join(e) if e else f"{c}: carteles bien")
        bad_many += len(e)
    for c in lang_codes or TRANSLATIONS:
        translated = load_data(c)
        e = (key_errors(base["es_es"], translated, c) + marker_errors(base["en_us"], translated, c)
             + book_errors(pages, {**base["en_us"], **translated}, c)
             + sign_errors(signs, translated, c))
        if not key_errors(base["es_es"], translated, c):
            e += guide.errors(uniques.modules(), {c: translated})
        print("\n".join(e) if e else f"{c}: bien ({len(translated)} claves)")
        bad_many += len(e)
    return 1 if bad_many else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(_check(sys.argv[1:]))
