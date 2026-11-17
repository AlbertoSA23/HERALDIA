"""Encargos del tablón y reputación (encargos.py, T38): textos en los 8 idiomas, logros, la página de la Guía, las opciones
y el comando, y que el Java solo use claves que existen."""
import json
import os
import re
import pytest
import comandos
import encargos
import guia
import idiomas
import opciones
from unicas._comun import botin

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
HUECO = re.compile(r"%(?:\d+\$)?[sd]")


def _java(ruta):
    with open(os.path.join(JAVA, ruta), encoding="utf-8") as f:
        return f.read()


def _todas():
    """Claves nuevas de T38 en es_es/en_us: los textos, la Guía y las opciones."""
    out = {"es_es": {}, "en_us": {}}
    for parte in (encargos.lang(), guia.lang(), opciones.lang()):
        for k in parte["es_es"]:
            if "encargos" in k or k.startswith("heraldia.config.reputacion."):
                out["es_es"][k], out["en_us"][k] = parte["es_es"][k], parte["en_us"][k]
    return out


def test_mismas_claves_y_huecos_en_es_y_en():
    lang = encargos.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k, es in lang["es_es"].items():
        assert es.strip() and lang["en_us"][k].strip(), k
        assert HUECO.findall(es) == HUECO.findall(lang["en_us"][k]), k


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_traducidas_en_cada_idioma(codigo):
    with open(idiomas.ruta(codigo), encoding="utf-8") as f:
        t = json.load(f)
    base = _todas()
    assert len(base["en_us"]) >= 60
    for k, en in base["en_us"].items():
        assert k in t, f"{codigo}: falta {k}"
        assert t[k].strip(), f"{codigo}: {k} vacía"
        assert sorted(HUECO.findall(t[k])) == sorted(HUECO.findall(en)), f"{codigo}: {k} con otros huecos"


def test_el_java_solo_usa_claves_que_existen():
    lang = encargos.lang()["es_es"]
    src = _java("encargos/Encargos.java")
    usadas = set(re.findall(r'"(heraldia\.(?:encargos|estado\.encargos)[a-z_.]*)"', src))
    dinamicas = {k for k in usadas if k.endswith(".")}
    for k in usadas - dinamicas:
        assert k in lang, f"el Java usa {k}, que no está en encargos.py"
    # las que se completan en Java: nivel.<nivel>, estado.<estado>, saludo.<nivel>, no_aceptable.<motivo>
    for pre in dinamicas:
        assert any(k.startswith(pre) for k in lang), pre
    for n in encargos.NIVELES:
        assert f"heraldia.encargos.nivel.{n}" in lang
        if n != "desconocido":
            assert f"heraldia.encargos.saludo.{n}" in lang
    for e in ("entregado", "aceptado", "cumplido", "caido", "en_curso", "vencido"):
        assert f"heraldia.encargos.estado.{e}" in lang
    for m in ("hecho", "ya", "lleno", "caido"):
        assert f"heraldia.encargos.no_aceptable.{m}" in lang


def test_niveles_iguales_que_en_java():
    src = _java("encargos/Reputacion.java")
    m = re.search(r"enum Nivel \{\s*(.*?);", src, re.S)
    assert [x.split("(")[0].strip().lower() for x in m.group(1).split(",")] == list(encargos.NIVELES)


def test_logros():
    advs = encargos.logros()
    ids = [lid for lid, *_ in encargos.LOGROS]
    assert list(advs) == [f"encargos/{i}" for i in ids]
    padre = "heraldia:raiz"
    for ruta, a in advs.items():
        assert a["parent"] == padre
        assert a["criteria"] == {"hecho": {"trigger": "minecraft:impossible"}}
        assert a["requirements"] == [["hecho"]]
        assert 0 < a["rewards"]["experience"] <= 150, "recompensa modesta"
        lid = ruta.split("/")[1]
        assert a["display"]["title"]["translate"] in encargos.lang()["es_es"]
        assert a["display"]["description"]["translate"] in encargos.lang()["es_es"]
        padre = f"heraldia:{ruta}"
    src = _java("encargos/Encargos.java")
    for lid in ids:
        assert f'"encargos/{lid}"' in src, f"el Java no concede encargos/{lid}"
    assert '"hecho"' in src


def test_write(tmp_path):
    escritos = {}
    encargos.write(str(tmp_path), lambda out, ruta, data: escritos.__setitem__(ruta, data))
    assert set(escritos) == {f"data/heraldia/advancement/encargos/{lid}.json" for lid, *_ in encargos.LOGROS}


def test_pagina_de_la_guia():
    pids = [p[0] for p in guia.PAGINAS]
    assert "encargos" in pids
    assert pids.index("encargos") == pids.index("vida") + 1, "justo después de la vida en la aldea"
    _, titulo, texto = guia.PAGINAS[pids.index("encargos")]
    for i in (0, 1):
        assert guia.lineas_pagina(titulo[i], texto[i]) <= botin.LIBRO_LINEAS
        assert "/heraldia quest" in texto[i]
    for codigo in idiomas.TRADUCCIONES:
        with open(idiomas.ruta(codigo), encoding="utf-8") as f:
            t = json.load(f)
        kt, kx = "heraldia.guia.pagina.encargos.titulo", "heraldia.guia.pagina.encargos"
        assert guia.lineas_titulo(t[kt]) == 1, codigo
        assert guia.lineas_pagina(t[kt], t[kx]) <= botin.LIBRO_LINEAS, codigo
        assert "/heraldia quest" in t[kx], codigo


def test_opciones():
    esquema = {o["clave"]: o for o in opciones.schema()["opciones"]}
    assert esquema["encargos.activado"]["defecto"] is True
    assert esquema["reputacion.activado"]["defecto"] is True
    assert esquema["encargos.rotacion_dias"]["defecto"] == 3
    assert (esquema["encargos.rotacion_dias"]["min"], esquema["encargos.rotacion_dias"]["max"]) == (1, 30)
    for k in ("encargos.activado", "encargos.rotacion_dias", "reputacion.activado"):
        assert esquema[k]["seccion"] == "encargos"
        assert not opciones.es_generacion(k), "valor de juego, no de generación"
        assert "generacion" not in esquema[k]
        assert k not in opciones.opciones_perfil(), "el perfil no los toca (no son de dificultad)"
    assert "encargos" in [s for s, *_ in opciones.SECTIONS]
    recarga = _java("config/Recarga.java")
    assert '"encargos."' in recarga and '"reputacion."' in recarga


def test_comando_en_ingles():
    for ruta in ("quest", "quest list", "quest accept", "quest accept <number>", "quest abandon", "quest abandon <number>",
                 "quest turnin"):
        assert ruta in comandos.CANONICOS
        assert re.fullmatch(r"[a-z <>]+", ruta)
    # ningún texto ni botón manda a un nombre antiguo
    assert comandos.errores_textos(_todas()["es_es"]) == []
    assert comandos.errores_textos(_todas()["en_us"]) == []
    src = _java("encargos/Encargos.java")
    for orden in re.findall(r'RunCommand\("([^"]*)', src) + re.findall(r'"(/heraldia quest[^"]*)"', src):
        assert orden.startswith("/heraldia quest"), orden
        assert not comandos.antiguos_en(orden)


def test_prueba_de_servidor_en_el_mapa():
    import importlib.util
    spec = importlib.util.spec_from_file_location("heraldia_test_selector_encargos", os.path.join(ROOT, "tools", "test.py"))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    todas = ["tools/smoke/encargos.py", "tools/smoke/aldeas_vida.py"]
    for ruta in ("src/main/java/io/github/albertosa23/heraldia/encargos/Encargos.java",
                 "src/main/java/io/github/albertosa23/heraldia/mixin/VillagerPreciosMixin.java", "tools/gen/encargos.py",
                 "tools/smoke/encargos.py"):
        assert t.para(ruta, todas) == ["tools/smoke/encargos.py"], ruta
    assert "tools/smoke/encargos.py" in t.DURACION_S
