"""Caravanas por los caminos (caravanas.py, T39): textos en los 8 idiomas, el logro, la página de la Guía, las opciones
(con el perfil) y el comando, y que el Java solo use claves que existen."""
import json
import os
import re
import pytest
import caravanas
import comandos
import guia
import idiomas
import logros
import opciones

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
HUECO = re.compile(r"%(?:\d+\$)?[sd%]")
CLAVES_OPCIONES = ("caravanas.activado", "caravanas.frecuencia", "caravanas.prob_asalto", "caravanas.max_activas")


def _java(ruta):
    with open(os.path.join(JAVA, ruta), encoding="utf-8") as f:
        return f.read()


def _todas():
    """Claves nuevas de T39 en es_es/en_us: los textos, el logro, la Guía y las opciones."""
    out = {"es_es": {}, "en_us": {}}
    for parte in (caravanas.lang(), guia.lang(), opciones.lang()):
        for k in parte["es_es"]:
            if "caravanas" in k:
                out["es_es"][k], out["en_us"][k] = parte["es_es"][k], parte["en_us"][k]
    return out


def test_mismas_claves_y_huecos_en_es_y_en():
    lang = caravanas.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k, es in lang["es_es"].items():
        assert es.strip() and lang["en_us"][k].strip(), k
        assert HUECO.findall(es) == HUECO.findall(lang["en_us"][k]), k


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_traducidas_en_cada_idioma(codigo):
    with open(idiomas.ruta(codigo), encoding="utf-8") as f:
        t = json.load(f)
    base = _todas()
    assert len(base["en_us"]) >= 35
    for k, en in base["en_us"].items():
        assert k in t, f"{codigo}: falta {k}"
        assert t[k].strip(), f"{codigo}: {k} vacía"
        assert t[k] != base["es_es"][k] or k.endswith((".nombre", ".titulo", "seccion.caravanas")) or codigo in ("gl_es", "pt_br"), \
            f"{codigo}: {k} sin traducir"
        assert sorted(HUECO.findall(t[k])) == sorted(HUECO.findall(en)), f"{codigo}: {k} con otros huecos"


def test_el_java_solo_usa_claves_que_existen():
    lang = caravanas.lang()["es_es"]
    src = _java("caravans/Caravans.java")
    usadas = set(re.findall(r'"(heraldia\.(?:caravanas|estado\.caravanas)[a-z_.]*)"', src))
    dinamicas = {k for k in usadas if k.endswith(".")}
    assert {"heraldia.caravanas.fase."} == dinamicas
    for k in usadas - dinamicas:
        assert k in lang, f"el Java usa {k}, que no está en caravanas.py"
    for fase in ("camino", "asalto"):
        assert f"heraldia.caravanas.fase.{fase}" in lang
    # los nombres de los bandidos son los del campamento de bandidos
    from medianas import campamento as camp
    for clave in ("saqueador", "vindicador"):
        assert f'"heraldia.medianas.campamento.{clave}"' in src and f"heraldia.medianas.campamento.{clave}" in camp.LANG["es_es"]


def test_logro():
    l = caravanas.logros()
    assert set(l) == {"caravanas/defensa"}
    a = l["caravanas/defensa"]
    assert a["criteria"] == {"hecho": {"trigger": "minecraft:impossible"}}
    assert a["parent"] == "heraldia:raiz"
    assert a["display"]["title"]["translate"] in caravanas.lang()["es_es"]
    assert '"caravanas/defensa"' in _java("caravans/Caravans.java")
    assert 'award(h, "hecho")' in _java("caravans/Caravans.java")


def test_pagina_de_la_guia_en_cada_idioma():
    ids = [p[0] for p in guia.PAGINAS]
    assert "caravanas" in ids and ids.index("caravanas") == ids.index("caminos") + 1
    lang = guia.lang()
    assert "heraldia.guia.pagina.caravanas" in lang["es_es"]


def test_opciones_y_perfil():
    fijas = {k: (d, lo, hi) for k, d, lo, hi, *_ in opciones._FIXED}
    assert fijas["caravanas.activado"] == (True, None, None)
    assert fijas["caravanas.frecuencia"] == (10, 0, 100)
    assert fijas["caravanas.prob_asalto"] == (35, 0, 100)
    assert fijas["caravanas.max_activas"] == (1, 1, 3)
    for k in CLAVES_OPCIONES:
        assert not opciones.es_generacion(k), f"{k} no es de la generación"
    p = opciones.perfiles()
    assert p["casual"]["caravanas.prob_asalto"] < p["estandar"]["caravanas.prob_asalto"] < p["hardcore"]["caravanas.prob_asalto"]
    assert "caravanas.activado" not in p["casual"] and "caravanas.max_activas" not in p["hardcore"]
    # recargables en Java
    assert '"caravanas."' in _java("config/Reload.java")


def test_comando_en_ingles_y_registrado():
    for r in ("caravan", "caravan spawn", "caravan spawn raid", "caravan spawn peaceful", "caravan raid", "caravan list", "caravan clear"):
        assert r in comandos.CANONICOS
        assert all(re.fullmatch(r"[a-z]+", t) for t in r.split())
    assert "Caravans.node()" in _java("command/HeraldiaCommands.java")
    assert "Caravans.state()" in _java("command/StatusCommand.java")
    assert "Caravans.register()" in _java("Heraldia.java")
    assert "LEVEL_GAMEMASTERS" in _java("caravans/Caravans.java"), "solo para operadores"
