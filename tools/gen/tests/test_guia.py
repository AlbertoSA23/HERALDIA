"""Guía del Heraldo (guia.py): textos completos en los dos idiomas y límites del libro vanilla (páginas de 14 líneas de
114 px, título de 32 caracteres como mucho, 100 páginas como mucho)."""
import re
import types
import pytest
import guia
import opciones
import unicas
from unicas._comun import botin

MODULOS = unicas.modules()


def modulo(nombre=("Algo", "Something"), pista=("el norte", "the north")):
    return types.SimpleNamespace(NOMBRE={"es_es": nombre[0], "en_us": nombre[1]}, HISTORIA={"pista": pista})


def test_las_unicas_reales_caben():
    assert guia.errores(MODULOS) == []


def test_mismas_claves_y_ninguna_vacia():
    lang = guia.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    assert all(v.strip() for textos in lang.values() for v in textos.values())
    assert all(k.startswith("heraldia.guia.") for k in lang["es_es"])


def test_mismos_huecos_en_los_dos_idiomas():
    lang = guia.lang()
    for k, es in lang["es_es"].items():
        assert re.findall(r"%[sd]", es) == re.findall(r"%[sd]", lang["en_us"][k]), k


@pytest.mark.parametrize("pid, titulo, texto", guia.PAGINAS, ids=[p[0] for p in guia.PAGINAS])
def test_cada_pagina_fija_cabe(pid, titulo, texto):
    for i in (0, 1):
        assert guia.lineas_titulo(titulo[i]) == 1, (pid, titulo[i])
        assert guia.lineas_pagina(titulo[i], texto[i]) <= botin.LIBRO_LINEAS, (pid, i)


def test_paginas_fijas_sin_repetir_y_con_el_comando():
    ids = [p[0] for p in guia.PAGINAS]
    assert len(ids) == len(set(ids))
    assert ids[0] == "bienvenida" and ids[-1] == "diario"
    diario = dict((p[0], p[2]) for p in guia.PAGINAS)["diario"]
    assert all("/heraldia guia" in t for t in diario)


def test_titulo_del_libro():
    assert all(1 <= len(t) <= guia.TITULO_MAX for t in guia.TITULO)
    assert guia.TITULO == guia.DIARIO["nombre"]


def test_entradas_por_pagina_con_el_peor_caso():
    d = guia.datos(MODULOS)
    nombres, pistas = guia._entradas(MODULOS)
    for cab, entradas, n in ((guia.DIARIO["descubiertas"], nombres, d["nombres_por_pagina"]),
                             (guia.DIARIO["pistas"], pistas, d["pistas_por_pagina"])):
        assert n >= 1
        for i in (0, 1):
            # las n entradas más largas, una por línea, tras la cabecera: caben; con una más, la peor ya no cabría
            peores = sorted(entradas[i], key=botin.lineas_libro, reverse=True)[:n]
            assert guia.lineas_pagina(cab[i], "\n".join(peores)) <= botin.LIBRO_LINEAS
        peor = max(botin.lineas_libro(e) for e in entradas[0] + entradas[1])
        assert guia.lineas_titulo(cab[0]) + 1 + (n + 1) * peor > botin.LIBRO_LINEAS


def test_resumen_cabe_con_cualquier_cola():
    for i in (0, 1):
        for cola in ("resumen.ninguna", "resumen.faltan", "resumen.todas"):
            texto = guia.DIARIO["resumen"][i] % (20, 20) + "\n\n" + guia.DIARIO[cola][i].replace("%s", "20")
            assert guia.lineas_pagina(guia.DIARIO["resumen.titulo"][i], texto) <= botin.LIBRO_LINEAS


def test_paginas_maximas():
    d = guia.datos(MODULOS)
    n = len(MODULOS)
    esperado = len(guia.PAGINAS) + 1 + max(-(-n // d["nombres_por_pagina"]), -(-n // d["pistas_por_pagina"]))
    assert guia.paginas_max(MODULOS) == esperado <= guia.MAX_PAGINAS


def test_pagina_demasiado_larga_falla(monkeypatch):
    largo = ("palabra " * 80, "word " * 80)
    monkeypatch.setattr(guia, "PAGINAS", guia.PAGINAS + [("larga", ("T", "T"), largo)])
    e = guia.errores(MODULOS)
    assert any("«larga» (es)" in x for x in e) and any("«larga» (en)" in x for x in e)


def test_pista_que_no_cabe_en_una_pagina_falla():
    larga = ("muy " * 120, "very " * 120)
    assert any("no cabe en una página" in x for x in guia.errores([("x", modulo(pista=larga))]))


def test_demasiadas_paginas_falla():
    mods = [(f"u{i}", modulo()) for i in range(1500)]
    assert any("más de 100" in x for x in guia.errores(mods))


def test_datos_para_el_java():
    d = guia.datos(MODULOS)
    assert d["paginas"] == [p[0] for p in guia.PAGINAS]
    assert d["marca"] == guia.MARCA and d["autor"] == guia.AUTOR
    # una entrada de nombre corto ocupa una línea; con nombres cortos caben más por página que con largos
    corto = guia.datos([("x", modulo(nombre=("Uno", "One")))])
    assert corto["nombres_por_pagina"] == botin.LIBRO_LINEAS - 2 >= d["nombres_por_pagina"]


def test_write_escribe_el_indice_y_devuelve_los_textos():
    escrito = {}
    out = guia.write("salida", MODULOS, lambda out, path, obj: escrito.__setitem__(path, obj))
    assert escrito == {"heraldia/guia.json": guia.datos(MODULOS)}
    assert out == guia.lang()


def test_write_falla_si_no_cabe(monkeypatch):
    monkeypatch.setattr(guia, "TITULO", ("x" * 40, "y"))
    with pytest.raises(SystemExit, match="pasa de 32"):
        guia.write("salida", MODULOS, lambda *a: None)


def test_opcion_de_entrega():
    o = {x["clave"]: x for x in opciones.schema()["opciones"]}["guia.entregar_al_entrar"]
    assert o["defecto"] is True and o["seccion"] == "guia" and "min" not in o
    lang = opciones.lang()
    assert "heraldia.config.guia.entregar_al_entrar" in lang["es_es"]
    assert "heraldia.config.guia.entregar_al_entrar.nombre" in lang["en_us"]
