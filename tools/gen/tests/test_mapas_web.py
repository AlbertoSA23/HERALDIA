"""Mapas web (Java: mapas/): sus textos (capas, nombres y descripciones de los marcadores, /heraldia webmap refresh) y
sus opciones (mapas_web.*) en los 8 idiomas, con los mismos huecos; que el Java solo pide claves que existen (una capa
por valor de mapas/Capa.java) y que las opciones de las capas, la del idioma y su sección están en el esquema."""
import json
import os
import re
import pytest
import admin
import idiomas
import opciones

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
MAPAS = os.path.join(RAIZ, "src", "main", "java", "io", "github", "albertosa23", "heraldia", "maps")
IDIOMAS = os.path.join(RAIZ, "tools", "gen", "idiomas")
TRADUCCIONES = ("fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es")


def _java(nombre):
    with open(os.path.join(MAPAS, nombre), encoding="utf-8") as f:
        return f.read()


def capas():
    """Ids de las capas: los ids guardados del enum Layer."""
    cuerpo = re.search(r"enum Layer \{\s*(.*?);", _java("Layer.java"), re.S).group(1)
    return re.findall(r'\b[A-Z]+\("(\w+)"', cuerpo)


def claves_java():
    """Claves de texto que piden los mapas web: dos por capa, más las fijas de MapasWeb y Marcadores."""
    out = {f"heraldia.mapas_web.{t}.{c}" for c in capas() for t in ("capa", "descripcion")}
    for f in ("WebMaps.java", "Markers.java"):
        out |= set(re.findall(r'"(heraldia\.mapas_web\.[a-z_.]+)"', _java(f)))
    return out


def claves_opciones():
    return {k for k in opciones.lang()["es_es"] if k.startswith("heraldia.config.mapas_web.")} | {
        "heraldia.config.seccion.mapas_web"}


def _traduccion(code):
    with open(os.path.join(IDIOMAS, code + ".json"), encoding="utf-8") as f:
        return json.load(f)


def test_capas_del_java():
    assert capas() == ["unicas", "aldeas", "medianas", "minas", "costa", "arena"]


def test_el_java_solo_pide_claves_que_existen():
    es = admin.lang()["es_es"]
    faltan = sorted(k for k in claves_java() if k not in es)
    assert not faltan, faltan
    sobran = sorted(k for k in es if k.startswith("heraldia.mapas_web.") and k not in claves_java())
    assert not sobran, sobran


@pytest.mark.parametrize("code", TRADUCCIONES)
def test_textos_en_cada_idioma(code):
    es, en = admin.lang()["es_es"], admin.lang()["en_us"]
    es_o, en_o = opciones.lang()["es_es"], opciones.lang()["en_us"]
    t = _traduccion(code)
    for k in sorted(claves_java()):
        assert k in en, k
        assert k in t, f"{code}: falta {k}"
        assert idiomas.marcadores(t[k]) == idiomas.marcadores(es[k]) == idiomas.marcadores(en[k]), f"{code}: {k}"
        assert t[k].strip(), k
    for k in sorted(claves_opciones()):
        assert k in es_o and k in en_o, k
        assert k in t, f"{code}: falta {k}"
    # las descripciones están traducidas (no son copia del español ni del inglés)
    for c in capas():
        k = f"heraldia.mapas_web.descripcion.{c}"
        assert t[k] not in (es[k], en[k]), f"{code}: {k} sin traducir"


def test_opciones_en_el_esquema():
    s = opciones.schema()
    por_clave = {o["clave"]: o for o in s["opciones"]}
    assert por_clave["mapas_web.activado"]["defecto"] is True
    assert por_clave["mapas_web.solo_descubiertas"]["defecto"] is True
    idioma = por_clave["mapas_web.idioma"]
    assert idioma["defecto"] == "auto"
    assert set(idioma["valores"]) == {"auto", "es_es", "en_us"} | set(TRADUCCIONES)
    for c in capas():
        o = por_clave[f"mapas_web.capas.{c}"]
        assert o["defecto"] is True and o["seccion"] == "mapas_web"
    assert "mapas_web" in [x["id"] for x in s["secciones"]]


def test_las_opciones_se_recargan():
    with open(os.path.join(MAPAS, "..", "config", "Reload.java"), encoding="utf-8") as f:
        assert '"mapas_web."' in f.read()
