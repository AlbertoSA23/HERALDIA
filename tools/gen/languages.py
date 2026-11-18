"""Mod languages: es_es and en_us come from the modules ((es, en) tuples and LANG dictionaries); the others from the
translations in tools/gen/languages/<code>.json ({key: text}).

Single source of the keys: the es_es built by the generator (writer.textos). Each translation must have exactly those
keys (not one more or fewer), the same format slots as the English (%s, %1$s, %%: the same arguments, in
the order the sentence needs) and fit in the book pages where it is used (chest_loot.book_lines). If anything fails,
generation stops (writer.write) and the tests say so (tests/test_languages.py).

Clients without the mod (Textos.idioma in Java): heraldia/languages.json says which .jar code corresponds to each Minecraft
language (the part before "_": fr_ca -> fr_fr, pt_pt -> pt_br, es_mx -> es_es); a language without its own translation gets English.

To check a translation by hand (after generating with ./gradlew build): python3 tools/gen/languages.py fr_fr
"""
import json
import os
import re
import sys

BASE = ("es_es", "en_us")
# .jar code -> language name (in its own language). The order is that of the READMEs and of /heraldia info.
TRANSLATIONS = {
    "fr_fr": "Français",
    "de_de": "Deutsch",
    "it_it": "Italiano",
    "pt_br": "Português (Brasil)",
    "ca_es": "Català",
    "gl_es": "Galego",
}
NAMES = {"en_us": "English", "es_es": "Español", **TRANSLATIONS}
# counterpart README of each language in the repository (English is the main one); tests/test_readme.py keeps them
# in sync and with the language selector, in this order.
README = {"en_us": "README.md", "es_es": "README.es.md", "fr_fr": "README.fr.md", "de_de": "README.de.md",
          "it_it": "README.it.md", "pt_br": "README.pt-BR.md", "ca_es": "README.ca.md", "gl_es": "README.gl.md"}
# Minecraft languages whose code does not start with that of their language in the mod: Valencian (val_es) and Andalusian (esan).
ALIAS = {"val": "ca_es", "esan": "es_es"}
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages")
FILL = "X" * 24        # text of a translatable that is not from the mod (e.g. a vanilla item name): worst case

_MARK = re.compile(r"%(?:(\d+)\$)?([a-zA-Z%])")


def everyone():
    """All the mod's language codes, the base ones first."""
    return list(BASE) + list(TRANSLATIONS)


def locale(lang_code):
    return lang_code.split("_", 1)[0]


def mc_locales():
    """{language: .jar code} for heraldia/languages.json (read by Textos.codigo in Java)."""
    out = {locale(c): c for c in everyone()}
    out.update(ALIAS)
    return out


def route(lang_code):
    return os.path.join(FOLDER, f"{lang_code}.json")


def load_data(lang_code):
    """{key: text} of a translation (tools/gen/languages/<code>.json); {} if it does not exist yet."""
    if not os.path.exists(route(lang_code)):
        return {}
    with open(route(lang_code), encoding="utf-8") as f:
        return json.load(f)


def markers(text):
    """Arguments used by a Minecraft format text (TranslatableContents): ([indices 1..n], number of %%) or
    None if it has a placeholder the game does not understand (only %s, %n$s and %%)."""
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
    """Keys missing from or extra in the translation `translated` compared with `base` (the es_es)."""
    e = [f"{lang_code}: falta la clave {k}" for k in base if k not in translated]
    e += [f"{lang_code}: sobra la clave {k}" for k in translated if k not in base]
    e += [f"{lang_code}: {k} está vacía" for k, v in translated.items() if k in base and not str(v).strip()]
    return e


def marker_errors(en, translated, lang_code):
    """Format slots different from those of the English (which are the same as those of the Spanish)."""
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
    """Like TranslatableContents: %s, %n$s and %%."""
    it = iter(range(len(args)))

    def sub(m):
        pos, kind = m.groups()
        if kind == "%":
            return "%"
        i = int(pos) - 1 if pos else next(it, len(args))
        return args[i] if 0 <= i < len(args) else ""
    return _MARK.sub(sub, fmt)


def text(comp, texts):
    """Plain text of a component in the language `texts` (what a client with the mod renders)."""
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
    """[(where, page)] of all the written books (written_book_content) found inside `items` (loot tables,
    trades, block NBT...), with the page as a component."""
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
    """Book pages that do not fit in this language (14 lines of 114 px, like the game)."""
    from uniques._common import chest_loot
    e = []
    for where, p in pages:
        t = text(p, texts)
        if chest_loot.book_lines(t) > chest_loot.BOOK_LINES:
            e.append(f"{lang_code}: la página de libro {where} no cabe ({chest_loot.book_lines(t)} de {chest_loot.BOOK_LINES} "
                     f"líneas): {t[:60]}…")
    return e


SIGN_WIDTH = 90          # SignBlockEntity: maximum width of a sign line, in px


def sign_keys(items):
    """Translatable keys of the sign lines (front_text/back_text) found inside `items` (block NBT):
    {key: bold}. Bold adds 1 px to each character (the font's bold offset)."""
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
    """Sign lines wider than the sign (90 px) in this language, also in es/en: the client (SignRenderer)
    wraps the line by words at 90 px and what is left over is not visible.
    `keys`: those from claves_de_carteles ({key: bold}) or a set of keys (without bold)."""
    e = []
    for k in sorted(keys):
        if k in texts and sign_width(texts[k], isinstance(keys, dict) and keys[k]) > SIGN_WIDTH:
            e.append(f"{lang_code}: la línea de cartel {k} no cabe ({sign_width(texts[k], isinstance(keys, dict) and keys[k])} "
                     f"de {SIGN_WIDTH} px): {texts[k]!r}")
    return e


def sign_width(text, bold=False):
    """Width in px of a sign line: that of chest_loot.width, plus 1 px per bold character."""
    from uniques._common import chest_loot
    return chest_loot.width(text) + (len(text) if bold else 0)


def sort_items(base, translated):
    """The translation with the keys in the order of the es_es (those not in it, at the end)."""
    return {**{k: translated[k] for k in base if k in translated}, **{k: v for k, v in translated.items() if k not in base}}


def complete(base, pages=(), signs=()):
    """{code: texts} of all the languages from the base ones ({"es_es": ..., "en_us": ...}) and the translations.
    `pages`: those of the written books (paginas_de_libros), which must fit in each language; `signs`: keys of
    the sign lines (claves_de_carteles). Raises SystemExit with all the errors if a translation is not
    complete or does not fit."""
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
        raise SystemExit("IDIOMAS:\n" + "\n".join(e[:200]) + (f"\n… and {len(e) - 200} more" if len(e) > 200 else ""))
    return out


def _check(lang_codes):
    """Manual use: compares each translation with the already generated es_es/en_us (build/generated/heraldia)."""
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
    # the books on the template lecterns (board, wizard tower) are not in data/: by their key
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
