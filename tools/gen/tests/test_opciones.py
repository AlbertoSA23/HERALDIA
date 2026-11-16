"""Opciones de lista (dificultad.nivel) y las de botín y dificultad en el esquema que lee el Java (opciones.py)."""
import pytest

import opciones


def _por_clave():
    return {o["clave"]: o for o in opciones.schema()["opciones"]}


def test_opciones_de_botin_y_dificultad():
    o = _por_clave()
    assert o["botin.reponer.activado"]["defecto"] is False          # por defecto no cambia el mundo
    assert (o["botin.reponer.dias"]["defecto"], o["botin.reponer.dias"]["min"], o["botin.reponer.dias"]["max"]) == (7, 1, 60)
    assert o["dificultad.nivel"]["defecto"] == "normal"              # normal = comportamiento de siempre
    assert o["dificultad.escalar_por_jugadores"]["defecto"] is False
    assert o["botin.reponer.activado"]["seccion"] == "botin" and o["dificultad.nivel"]["seccion"] == "dificultad"


def test_opcion_de_lista():
    n = _por_clave()["dificultad.nivel"]
    assert n["valores"] == ["facil", "normal", "dificil", "heroica"]
    assert n["nombres_valores"] == [f"heraldia.config.dificultad.nivel.{v}" for v in n["valores"]]
    assert "min" not in n and "max" not in n
    lang = opciones.lang()
    for code in ("es_es", "en_us"):
        for k in n["nombres_valores"] + ["heraldia.config.valores", n["nombre"], n["ayuda"]]:
            assert lang[code].get(k), (code, k)
    assert lang["es_es"]["heraldia.config.dificultad.nivel.heroica"] == "Heroica"
    assert lang["en_us"]["heraldia.config.dificultad.nivel.facil"] == "Easy"


def test_solo_las_de_lista_llevan_valores():
    for o in opciones.schema()["opciones"]:
        if "valores" in o:
            assert isinstance(o["defecto"], str) and o["defecto"] in o["valores"]
        else:
            assert not isinstance(o["defecto"], str), o["clave"]


def test_valor_por_defecto_fuera_de_la_lista_falla():
    with pytest.raises(AssertionError):
        opciones._option("dificultad.x", "imposible", ["facil", "normal"], None, "k")
