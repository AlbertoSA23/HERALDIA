"""Mapas web (Java: mapas/): sus textos (capas, nombres y descripciones de los marcadores, /heraldia webmap refresh) y
sus opciones (mapas_web.*) en los 8 idiomas, con los mismos huecos; que el Java solo pide claves que existen (una capa
por valor de mapas/Capa.java) y que las opciones de las capas, la del idioma y su sección están en el esquema."""
import json
import os
import re
import pytest
import admin
import languages
import options

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
MAPS = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia", "maps")
LANGUAGES = os.path.join(ROOT, "tools", "gen", "languages")
TRANSLATIONS = ("fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es")


def _java(name):
    with open(os.path.join(MAPS, name), encoding="utf-8") as f:
        return f.read()


def layers():
    """Ids de las capas: los ids guardados del enum Layer."""
    body = re.search(r"enum Layer \{\s*(.*?);", _java("Layer.java"), re.S).group(1)
    return re.findall(r'\b[A-Z]+\("(\w+)"', body)


def java_keys():
    """Claves de texto que piden los mapas web: dos por capa, más las fijas de MapasWeb y Marcadores."""
    out = {f"heraldia.mapas_web.{t}.{c}" for c in layers() for t in ("capa", "descripcion")}
    for f in ("WebMaps.java", "Markers.java"):
        out |= set(re.findall(r'"(heraldia\.mapas_web\.[a-z_.]+)"', _java(f)))
    return out


def option_keys():
    return {k for k in options.lang()["es_es"] if k.startswith("heraldia.config.mapas_web.")} | {
        "heraldia.config.seccion.mapas_web"}


def _translation(code):
    with open(os.path.join(LANGUAGES, code + ".json"), encoding="utf-8") as f:
        return json.load(f)


def test_layers_of_the_java():
    assert layers() == ["unicas", "aldeas", "medianas", "minas", "costa", "arena"]


def test_the_java_only_requests_keys_that_exist():
    es = admin.lang()["es_es"]
    missing = sorted(k for k in java_keys() if k not in es)
    assert not missing, missing
    surplus = sorted(k for k in es if k.startswith("heraldia.mapas_web.") and k not in java_keys())
    assert not surplus, surplus


@pytest.mark.parametrize("code", TRANSLATIONS)
def test_texts_in_each_language(code):
    es, en = admin.lang()["es_es"], admin.lang()["en_us"]
    es_o, en_o = options.lang()["es_es"], options.lang()["en_us"]
    t = _translation(code)
    for k in sorted(java_keys()):
        assert k in en, k
        assert k in t, f"{code}: falta {k}"
        assert languages.markers(t[k]) == languages.markers(es[k]) == languages.markers(en[k]), f"{code}: {k}"
        assert t[k].strip(), k
    for k in sorted(option_keys()):
        assert k in es_o and k in en_o, k
        assert k in t, f"{code}: falta {k}"
    # las descripciones están traducidas (no son copia del español ni del inglés)
    for c in layers():
        k = f"heraldia.mapas_web.descripcion.{c}"
        assert t[k] not in (es[k], en[k]), f"{code}: {k} sin traducir"


def test_options_in_the_schema():
    s = options.schema()
    by_key = {o["clave"]: o for o in s["opciones"]}
    assert by_key["mapas_web.activado"]["defecto"] is True
    assert by_key["mapas_web.solo_descubiertas"]["defecto"] is True
    language = by_key["mapas_web.idioma"]
    assert language["defecto"] == "auto"
    assert set(language["valores"]) == {"auto", "es_es", "en_us"} | set(TRANSLATIONS)
    for c in layers():
        o = by_key[f"mapas_web.capas.{c}"]
        assert o["defecto"] is True and o["seccion"] == "mapas_web"
    assert "mapas_web" in [x["id"] for x in s["secciones"]]


def test_options_reload():
    with open(os.path.join(MAPS, "..", "config", "Reload.java"), encoding="utf-8") as f:
        assert '"mapas_web."' in f.read()
