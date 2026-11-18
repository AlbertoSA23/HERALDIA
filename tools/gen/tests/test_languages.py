"""idiomas.py and the translations in tools/gen/languages/: complete keys with no extras, format placeholders equal to
those of English, books (Guide, chronicle, hermitage, chronicle copy) and signs that fit in each language, and the map of
languages read by the Java (Textos.codigo).

Without generating the datapack, the texts that the unique structures only fill in when built (e.g. the Atlantis signs)
are not there: here it is checked that each translation has all the others and that all have the same keys; the
exact comparison with the complete es_es is done by the generation (writer.write -> idiomas.completar) and IdiomasTest (JUnit).
"""
import json
import os
import pytest
import roads
import guide
import languages
import advancements
import uniques
import writer
from uniques._common import chest_loot
from mediums import hermitage

MODS = uniques.modules()
LANG_CODES = list(languages.TRANSLATIONS)


class _Template:
    def __init__(self, sid):
        self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{advancements.GUARDIAN_TAG}.{sid}"]})]


class _Registry:
    """Minimal registry: one guardian per unique structure (all have one; the guardian advancements depend on it)."""
    templates = {f"unicas/{sid}/x": _Template(sid) for sid, _ in MODS}


@pytest.fixture(scope="module")
def base():
    return writer.texts(_Registry)


@pytest.fixture(scope="module")
def translated():
    return {c: languages.load_data(c) for c in LANG_CODES}


# ------------------------------------------------------------------ pure logic
def test_markers():
    assert languages.markers("sin huecos") == ([], 0)
    assert languages.markers("%s de %s") == ([1, 2], 0)
    assert languages.markers("%2$s de %1$s") == ([1, 2], 0)
    assert languages.markers("%s %%") == ([1], 1)
    assert languages.markers("%d") is None


def test_format_like_the_game():
    assert languages.format_text("%s/%s", ["1", "2"]) == "1/2"
    assert languages.format_text("%2$s, %1$s", ["a", "b"]) == "b, a"
    assert languages.format_text("%s %%", ["50"]) == "50 %"
    assert languages.format_text("%s %s", ["solo"]) == "solo "


def test_errors_of_keys_and_gaps():
    es = {"a": "uno %s", "b": "dos"}
    en = {"a": "one %s", "b": "two"}
    assert languages.key_errors(es, {"a": "un %s", "b": "deux"}, "fr_fr") == []
    e = languages.key_errors(es, {"a": "un %s", "c": "trois"}, "fr_fr")
    assert any("falta la clave b" in x for x in e) and any("sobra la clave c" in x for x in e)
    assert any("vacía" in x for x in languages.key_errors(es, {"a": " ", "b": "x"}, "fr_fr"))
    assert languages.marker_errors(en, {"a": "un %1$s"}, "fr_fr") == []
    assert languages.marker_errors(en, {"a": "un"}, "fr_fr")
    assert languages.marker_errors(en, {"a": "un %s %s"}, "fr_fr")
    assert any("desconocido" in x for x in languages.marker_errors(en, {"a": "un %d"}, "fr_fr"))


def test_text_of_a_component():
    texts = {"k": "Hola, %s: %s", "n": "Ysolda"}
    comp = {"translate": "k", "with": [{"translate": "n"}, 3]}
    assert languages.text(comp, texts) == "Hola, Ysolda: 3"
    assert languages.text({"translate": "block.minecraft.stone"}, texts) == languages.FILL
    assert languages.text({"text": "a", "extra": [{"text": "b"}]}, texts) == "ab"


def test_pages_and_signs_inside_any_object():
    written_book = chest_loot.written_book([{"translate": "p1"}, {"translate": "p2"}], {"translate": "n"}, "Título", "Autor")
    lectern = {"Book": {"components": {"minecraft:written_book_content": {"pages": [{"raw": {"translate": "p3"}}]}}}}
    pages = languages.book_pages([("botín", {"pools": [{"entries": [written_book]}]}), ("atril", lectern)])
    assert [p["translate"] for _, p in pages] == ["p1", "p2", "p3"]
    sign = {"front_text": {"messages": [{"translate": "c1"}, {"text": ""}]}, "back_text": {"messages": [{"translate": "c2"}]}}
    assert set(languages.sign_keys([sign, {"otra": [sign]}])) == {"c1", "c2"}


def test_page_or_sign_that_does_not_fit_fails():
    length = "palabra " * 60
    assert languages.book_errors([("x", {"translate": "p"})], {"p": length}, "fr_fr")
    assert not languages.book_errors([("x", {"translate": "p"})], {"p": "corta"}, "fr_fr")
    assert languages.sign_errors({"c"}, {"c": "Une ligne beaucoup trop longue"}, "fr_fr")
    assert not languages.sign_errors({"c"}, {"c": "Court"}, "fr_fr")


def test_sign_of_90_px_fits_and_of_91_no():
    exact = "x" * 15                      # 15 × 6 px = 90 px
    assert chest_loot.width(exact) == languages.SIGN_WIDTH
    assert not languages.sign_errors({"c"}, {"c": exact}, "es_es")
    assert languages.sign_errors({"c"}, {"c": exact + "!"}, "es_es")      # 92 px


def test_sign_of_es_en_that_does_not_fit_fails_the_generation(monkeypatch):
    monkeypatch.setattr(languages, "load_data", lambda c: {"c": "Corto"})
    for length in ("es_es", "en_us"):
        base = {"es_es": {"c": "Corto"}, "en_us": {"c": "Short"}}
        base[length]["c"] = "Una línea larguísima de cartel"
        with pytest.raises(SystemExit, match=f"{length}: la línea de cartel c no cabe"):
            languages.complete(base, signs={"c"})


def test_sign_translation_that_does_not_fit_fails_even_if_es_is_wider(monkeypatch):
    # it used to be tolerated if es/en already passed; now the limit is always 90 px
    base = {"es_es": {"c": "Una línea larguísima de cartel"}, "en_us": {"c": "x"}}
    assert languages.sign_errors({"c"}, {"c": "Une ligne trop longue ici"}, "fr_fr")
    monkeypatch.setattr(languages, "load_data", lambda c: {"c": "Une ligne trop longue ici"})
    base["es_es"]["c"] = "Corto"
    with pytest.raises(SystemExit, match="fr_fr: la línea de cartel c no cabe"):
        languages.complete(base, signs={"c"})


def test_complete_fails_with_a_translation_incomplete(monkeypatch):
    base = {"es_es": {"a": "uno %s", "b": "dos"}, "en_us": {"a": "one %s", "b": "two"}}
    monkeypatch.setattr(languages, "load_data", lambda c: {"a": "x %s", "b": "y"})
    out = languages.complete(base)
    assert set(out) == set(languages.everyone()) and out["fr_fr"] == {"a": "x %s", "b": "y"}
    monkeypatch.setattr(languages, "load_data", lambda c: {"a": "x"})
    with pytest.raises(SystemExit, match="falta la clave b"):
        languages.complete(base)


def test_sort_like_spanish():
    assert list(languages.sort_items({"b": 1, "a": 2}, {"a": "x", "b": "y"})) == ["b", "a"]


# ------------------------------------------------------------------ languages and tongues (Textos.codigo in Java)
def test_language_list():
    assert languages.BASE == ("es_es", "en_us")
    assert set(LANG_CODES) >= {"fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es"}
    assert languages.everyone() == list(languages.BASE) + LANG_CODES
    mc_locales = [languages.locale(c) for c in languages.everyone()]
    assert len(mc_locales) == len(set(mc_locales)), "two languages of the same tongue: Textos.codigo would not know which to choose"


def test_language_map():
    m = languages.mc_locales()
    assert m["es"] == "es_es" and m["en"] == "en_us" and m["fr"] == "fr_fr" and m["pt"] == "pt_br"
    assert m["ca"] == m["val"] == "ca_es" and m["gl"] == "gl_es" and m["esan"] == "es_es"
    assert set(m.values()) == set(languages.everyone())


def test_each_translation_exists_and_es_json_blueprint(translated):
    for c in LANG_CODES:
        assert os.path.exists(languages.route(c)), c
        assert translated[c] and all(isinstance(k, str) and isinstance(v, str) for k, v in translated[c].items()), c


# ------------------------------------------------------------------ the real translations
def test_all_translations_have_the_same_keys(translated):
    keys = {c: set(t) for c, t in translated.items()}
    first = keys[LANG_CODES[0]]
    for c in LANG_CODES[1:]:
        assert keys[c] == first, (c, sorted(keys[c] ^ first)[:20])


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_translation_complete(lang_code, base, translated):
    missing = [k for k in base["es_es"] if k not in translated[lang_code]]
    assert missing == [], missing[:20]
    assert all(v.strip() for v in translated[lang_code].values())


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_same_gaps_as_english(lang_code, base, translated):
    assert languages.marker_errors(base["en_us"], translated[lang_code], lang_code) == []


def test_extra_keys_belong_to_uniques(base, translated):
    """Those that do not come out without building are texts of unicas/ modules that are filled in build()."""
    prefixes = tuple(f"heraldia.{sid}." for sid, _ in MODS) + tuple(f"heraldia.unicas.{sid}." for sid, _ in MODS)
    extra = [k for k in translated[LANG_CODES[0]] if k not in base["es_es"]]
    assert all(k.startswith(prefixes) for k in extra), [k for k in extra if not k.startswith(prefixes)][:20]


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_guide_fits(lang_code, translated):
    assert guide.errors(MODS, {lang_code: translated[lang_code]}) == []


def test_guide_counts_entries_with_worst_language(translated):
    only_base, everyone = guide.dataset(MODS), guide.dataset(MODS, translated)
    assert everyone["nombres_por_pagina"] <= only_base["nombres_por_pagina"]
    assert everyone["pistas_por_pagina"] <= only_base["pistas_por_pagina"]
    for c in LANG_CODES:
        assert everyone["pistas_por_pagina"] <= guide.dataset(MODS, {c: translated[c]})["pistas_por_pagina"]


def _books():
    """The loot books that come out without building: the chronicle sheets, the hermitage journal and the copies of the
    trades chronicle (those of the template lecterns are measured by the generation)."""
    items = [(sid, t) for sid, t in writer.history_tables(MODS).items()]
    items += [("ermita", hermitage.LOOT)]
    import trades
    items += [("tratos", trades.items(MODS))]
    return languages.book_pages(items)


def test_there_are_books_to_measure():
    pages = _books()
    assert len(pages) >= 3 * len(MODS)
    assert any(p.get("translate") == "heraldia.historia.final" for _, p in pages)


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_books_fit(lang_code, base, translated):
    assert languages.book_errors(_books(), {**base["en_us"], **translated[lang_code]}, lang_code) == []


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_board_fits(lang_code, translated):
    import board
    for k in board.TEXTS:
        if k.startswith("p"):
            t = languages.format_text(translated[lang_code][f"{board.K}.{k}"], [languages.FILL] * 4)
            assert chest_loot.book_lines(t) <= chest_loot.BOOK_LINES, (k, t)


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_signs_fit(lang_code, base, translated):
    signs = {k for k in translated[lang_code] if ".cartel." in k and k in base["es_es"]}
    assert signs
    assert languages.sign_errors(signs, translated[lang_code], lang_code) == []
    for c in languages.BASE:
        assert languages.sign_errors(signs, base[c], c) == []


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_signs_of_the_roads(lang_code, translated):
    for k in roads.LANG["es_es"]:
        t = translated[lang_code][k]
        assert languages.markers(t) == ([1], 0), (k, t)
        assert len(languages.format_text(t, ["1999"])) <= 15, (k, t)      # fits on a sign line


@pytest.mark.parametrize("lang_code", LANG_CODES)
def test_commands_without_translate(lang_code, base, translated):
    """A command that appears in a text (/heraldia guide, /heraldia arena...) stays the same in the translation."""
    import re
    for k, es in base["es_es"].items():
        for cmd in re.findall(r"/heraldia(?: \w+)?", es):
            assert cmd in translated[lang_code][k], (k, cmd, translated[lang_code][k])


def test_files_of_translation_in_its_format():
    """JSON with indent 2 and without escaping accents, as idiomas writes them (readable diffs)."""
    for c in LANG_CODES:
        with open(languages.route(c), encoding="utf-8") as f:
            text = f.read()
        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n", c


def test_sign_in_bold_adds_a_px_by_character():
    sign = {"front_text": {"messages": [{"translate": "n", "bold": True}, {"translate": "f"}]}}
    keys = languages.sign_keys([sign])
    assert keys == {"n": True, "f": False}
    text = "a" * 14                                   # 84 px; en negrita, 98
    assert not languages.sign_errors(keys, {"f": text}, "es_es")
    assert languages.sign_errors(keys, {"n": text}, "es_es")
    assert languages.sign_width("ab", True) == languages.sign_width("ab") + 2
