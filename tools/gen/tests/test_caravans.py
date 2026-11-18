"""Caravanas por los caminos (caravanas.py, T39): textos en los 8 idiomas, el logro, la página de la Guía, las opciones
(con el perfil) y el comando, y que el Java solo use claves que existen."""
import json
import os
import re
import pytest
import caravans
import commands
import guide
import languages
import advancements
import options

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
CAVITY = re.compile(r"%(?:\d+\$)?[sd%]")
OPTION_KEYS = ("caravanas.activado", "caravanas.frecuencia", "caravanas.prob_asalto", "caravanas.max_activas")


def _java(route):
    with open(os.path.join(JAVA, route), encoding="utf-8") as f:
        return f.read()


def _all():
    """Claves nuevas de T39 en es_es/en_us: los textos, el logro, la Guía y las opciones."""
    out = {"es_es": {}, "en_us": {}}
    for part in (caravans.lang(), guide.lang(), options.lang()):
        for k in part["es_es"]:
            if "caravanas" in k:
                out["es_es"][k], out["en_us"][k] = part["es_es"][k], part["en_us"][k]
    return out


def test_same_keys_and_gaps_in_es_and_en():
    lang = caravans.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k, es in lang["es_es"].items():
        assert es.strip() and lang["en_us"][k].strip(), k
        assert CAVITY.findall(es) == CAVITY.findall(lang["en_us"][k]), k


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_translated_in_each_language(codigo):
    with open(languages.route(codigo), encoding="utf-8") as f:
        t = json.load(f)
    base = _all()
    assert len(base["en_us"]) >= 35
    for k, en in base["en_us"].items():
        assert k in t, f"{codigo}: falta {k}"
        assert t[k].strip(), f"{codigo}: {k} vacía"
        assert t[k] != base["es_es"][k] or k.endswith((".nombre", ".titulo", "seccion.caravanas")) or codigo in ("gl_es", "pt_br"), \
            f"{codigo}: {k} sin traducir"
        assert sorted(CAVITY.findall(t[k])) == sorted(CAVITY.findall(en)), f"{codigo}: {k} con otros huecos"


def test_the_java_only_uses_keys_that_exist():
    lang = caravans.lang()["es_es"]
    src = _java("caravans/Caravans.java")
    used = set(re.findall(r'"(heraldia\.(?:caravanas|estado\.caravanas)[a-z_.]*)"', src))
    dynamic = {k for k in used if k.endswith(".")}
    assert {"heraldia.caravanas.fase."} == dynamic
    for k in used - dynamic:
        assert k in lang, f"el Java usa {k}, que no está en caravanas.py"
    for phase in ("camino", "asalto"):
        assert f"heraldia.caravanas.fase.{phase}" in lang
    # los nombres de los bandidos son los del campamento de bandidos
    from mediums import camp as camp
    for key in ("saqueador", "vindicador"):
        assert f'"heraldia.medianas.campamento.{key}"' in src and f"heraldia.medianas.campamento.{key}" in camp.LANG["es_es"]


def test_advancement():
    l = caravans.advancements()
    assert set(l) == {"caravanas/defensa"}
    a = l["caravanas/defensa"]
    assert a["criteria"] == {"hecho": {"trigger": "minecraft:impossible"}}
    assert a["parent"] == "heraldia:raiz"
    assert a["display"]["title"]["translate"] in caravans.lang()["es_es"]
    assert '"caravanas/defensa"' in _java("caravans/Caravans.java")
    assert 'award(h, "hecho")' in _java("caravans/Caravans.java")


def test_guide_page_in_each_language():
    ids = [p[0] for p in guide.PAGES]
    assert "caravanas" in ids and ids.index("caravanas") == ids.index("caminos") + 1
    lang = guide.lang()
    assert "heraldia.guia.pagina.caravanas" in lang["es_es"]


def test_options_and_profile():
    fixed_opts = {k: (d, lo, hi) for k, d, lo, hi, *_ in options._FIXED}
    assert fixed_opts["caravanas.activado"] == (True, None, None)
    assert fixed_opts["caravanas.frecuencia"] == (10, 0, 100)
    assert fixed_opts["caravanas.prob_asalto"] == (35, 0, 100)
    assert fixed_opts["caravanas.max_activas"] == (1, 1, 3)
    for k in OPTION_KEYS:
        assert not options.is_generation(k), f"{k} no es de la generación"
    p = options.profiles()
    assert p["casual"]["caravanas.prob_asalto"] < p["estandar"]["caravanas.prob_asalto"] < p["hardcore"]["caravanas.prob_asalto"]
    assert "caravanas.activado" not in p["casual"] and "caravanas.max_activas" not in p["hardcore"]
    # recargables en Java
    assert '"caravanas."' in _java("config/Reload.java")


def test_command_in_english_and_registered():
    for r in ("caravan", "caravan spawn", "caravan spawn raid", "caravan spawn peaceful", "caravan raid", "caravan list", "caravan clear"):
        assert r in commands.CANONICAL
        assert all(re.fullmatch(r"[a-z]+", t) for t in r.split())
    assert "Caravans.node()" in _java("command/HeraldiaCommands.java")
    assert "Caravans.state()" in _java("command/StatusCommand.java")
    assert "Caravans.register()" in _java("Heraldia.java")
    assert "LEVEL_GAMEMASTERS" in _java("caravans/Caravans.java"), "solo para operadores"
