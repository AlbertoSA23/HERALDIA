"""Guía del Heraldo (guia.py): textos completos en los dos idiomas y límites del libro vanilla (páginas de 14 líneas de
114 px, título de 32 caracteres como mucho, 100 páginas como mucho)."""
import re
import types
import pytest
import guide
import options
import uniques
from uniques._common import chest_loot

MODULES = uniques.modules()


def module(name=("Algo", "Something"), clue=("el norte", "the north")):
    return types.SimpleNamespace(DISPLAY_NAME={"es_es": name[0], "en_us": name[1]}, STORY={"pista": clue})


def test_real_uniques_fit():
    assert guide.errors(MODULES) == []


def test_same_keys_and_none_empty():
    lang = guide.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    assert all(v.strip() for texts in lang.values() for v in texts.values())
    assert all(k.startswith("heraldia.guia.") for k in lang["es_es"])


def test_same_gaps_in_both_languages():
    lang = guide.lang()
    for k, es in lang["es_es"].items():
        assert re.findall(r"%[sd]", es) == re.findall(r"%[sd]", lang["en_us"][k]), k


@pytest.mark.parametrize("pid, title, text", guide.PAGES, ids=[p[0] for p in guide.PAGES])
def test_each_page_fixed_fits(pid, title, text):
    for i in (0, 1):
        assert guide.title_lines(title[i]) == 1, (pid, title[i])
        assert guide.page_lines(title[i], text[i]) <= chest_loot.BOOK_LINES, (pid, i)


def test_fixed_pages_without_repeating_and_with_the_command():
    ids = [p[0] for p in guide.PAGES]
    assert len(ids) == len(set(ids))
    assert ids[0] == "bienvenida" and ids[-1] == "diario"
    journal = dict((p[0], p[2]) for p in guide.PAGES)["diario"]
    assert all("/heraldia guide" in t for t in journal)


def test_book_title():
    assert all(1 <= len(t) <= guide.TITLE_MAX for t in guide.TITLE)
    assert guide.TITLE == guide.JOURNAL["nombre"]


def test_entries_by_page_with_the_worst_case():
    d = guide.dataset(MODULES)
    names, clues = guide._entries(MODULES)
    for header, entrances, n in ((guide.JOURNAL["descubiertas"], names, d["nombres_por_pagina"]),
                             (guide.JOURNAL["pistas"], clues, d["pistas_por_pagina"])):
        assert n >= 1
        for i in (0, 1):
            # las n entradas más largas, una por línea, tras la cabecera: caben; con una más, la peor ya no cabría
            peores = sorted(entrances[i], key=chest_loot.book_lines, reverse=True)[:n]
            assert guide.page_lines(header[i], "\n".join(peores)) <= chest_loot.BOOK_LINES
        worst = max(chest_loot.book_lines(e) for e in entrances[0] + entrances[1])
        assert guide.title_lines(header[0]) + 1 + (n + 1) * worst > chest_loot.BOOK_LINES


def test_summary_fits_with_any_tail():
    for i in (0, 1):
        for queue in ("resumen.ninguna", "resumen.faltan", "resumen.todas"):
            text = guide.JOURNAL["resumen"][i] % (20, 20) + "\n\n" + guide.JOURNAL[queue][i].replace("%s", "20")
            assert guide.page_lines(guide.JOURNAL["resumen.titulo"][i], text) <= chest_loot.BOOK_LINES


def test_max_pages():
    d = guide.dataset(MODULES)
    n = len(MODULES)
    expected = len(guide.PAGES) + 1 + guide.FAME_PAGES + max(-(-n // d["nombres_por_pagina"]), -(-n // d["pistas_por_pagina"]))
    assert guide.pages_max(MODULES) == expected <= guide.MAX_PAGES


def test_page_too_long_fails(monkeypatch):
    length = ("palabra " * 80, "word " * 80)
    monkeypatch.setattr(guide, "PAGES", guide.PAGES + [("larga", ("T", "T"), length)])
    e = guide.errors(MODULES)
    assert any("«larga» (es)" in x for x in e) and any("«larga» (en)" in x for x in e)


def test_hint_that_does_not_fit_on_a_page_fails():
    long = ("muy " * 120, "very " * 120)
    assert any("no cabe en una página" in x for x in guide.errors([("x", module(clue=long))]))


def test_too_many_pages_fails():
    mods = [(f"u{i}", module()) for i in range(1500)]
    assert any("más de 100" in x for x in guide.errors(mods))


def test_data_for_the_java():
    d = guide.dataset(MODULES)
    assert d["paginas"] == [p[0] for p in guide.PAGES]
    assert d["marca"] == guide.MARK and d["autor"] == guide.AUTHOR
    # una entrada de nombre corto ocupa una línea; con nombres cortos caben más por página que con largos
    brief = guide.dataset([("x", module(name=("Uno", "One")))])
    assert brief["nombres_por_pagina"] == chest_loot.BOOK_LINES - 2 >= d["nombres_por_pagina"]


def test_write_escribe_el_indice_y_devuelve_los_textos():
    written = {}
    out = guide.write("salida", MODULES, lambda out, path, obj: written.__setitem__(path, obj))
    assert written == {"heraldia/guia.json": guide.dataset(MODULES)}
    assert out == guide.lang()


def test_write_falla_si_no_cabe(monkeypatch):
    monkeypatch.setattr(guide, "TITLE", ("x" * 40, "y"))
    with pytest.raises(SystemExit, match="pasa de 32"):
        guide.write("salida", MODULES, lambda *a: None)


def test_delivery_option():
    o = {x["clave"]: x for x in options.schema()["opciones"]}["guia.entregar_al_entrar"]
    assert o["defecto"] is True and o["seccion"] == "guia" and "min" not in o
    lang = options.lang()
    assert "heraldia.config.guia.entregar_al_entrar" in lang["es_es"]
    assert "heraldia.config.guia.entregar_al_entrar.nombre" in lang["en_us"]


# --- T41: el salón de la fama de la arena ---

def test_hall_of_fame_fits_in_es_and_en():
    assert guide.fame_errors() == []
    assert guide.FAME_PAGES == 2


def test_hall_of_fame_texts():
    es, en = guide.lang()["es_es"], guide.lang()["en_us"]
    for k in ("fama.titulo", "fama.ninguno", "fama.semana", "fama.entrada", "fama.vacio", "records.titulo", "records.intro"):
        assert guide.key(k) in es and guide.key(k) in en
        assert es[guide.key(k)].count("%s") == en[guide.key(k)].count("%s"), k
    assert es[guide.key("fama.entrada")].count("%s") == 3          # modo, jugador, marca (arena/Fama)
    assert "/heraldia arena leaderboard" in es[guide.key("fama.ninguno")]


def test_hall_of_fame_detects_what_does_not_fit():
    length = {guide.key("records.intro"): "palabra " * 60}
    translated = {"xx_xx": {**guide.lang()["en_us"], **__import__("arena_waves").lang()["en_us"], **length}}
    assert any("records" in e for e in guide.fame_errors(translated))
