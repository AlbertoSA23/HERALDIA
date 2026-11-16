"""Crónica de los Heraldos: contrato HISTORIA (botin.historia_errores) y cadena (botin.historia_cadena, writer)."""
import types
import pytest
from unicas._comun import botin

HIST = {"cofre": "biblioteca", "relato": [("Uno.", "One.")], "pista": ("al norte", "to the north")}


def mod(**historia):
    m = types.SimpleNamespace(HISTORIA=dict(HIST, **historia), STRUCTURE={"spacing": 250}, LOOT={"biblioteca": {}})
    return m


def test_historia_valida():
    assert botin.historia_errores("x", HIST, {"biblioteca": {}}) == []


@pytest.mark.parametrize("cambio, msg", [
    (dict(cofre="otro"), "no es una tabla de su LOOT"),
    (dict(relato=[]), "HISTORIA.relato"),
    (dict(relato=[("a", "b")] * 3), "HISTORIA.relato"),
    (dict(pista=("solo",)), "HISTORIA.pista"),
    (dict(relato=[("palabra " * 200, "word")]), "no cabe en una página"),
    (dict(pista=("palabra " * 120, "w")), "no cabe en una página"),
])
def test_historia_casos_negativos(cambio, msg):
    errs = botin.historia_errores("x", dict(HIST, **cambio), {"biblioteca": {}})
    assert any(msg in e for e in errs), errs


def test_historia_ausente():
    assert "falta HISTORIA" in botin.historia_errores("x", None, {})[0]


def test_cadena_por_id_con_la_final_al_cabo():
    mods = [("a", mod()), ("b", mod(final=True)), ("c", mod()), ("d", types.SimpleNamespace())]
    assert botin.historia_cadena(mods) == ["a", "c", "b"]
    assert botin.historia_cadena_errores(mods) == []
    assert botin.historia_cadena_errores([("a", mod())])                     # sin final
    assert botin.historia_cadena_errores([("a", mod(final=True)), ("b", mod(final=True))])   # dos finales


def test_tablas_de_la_cadena_forman_un_ciclo():
    import writer
    mods = [("a", mod()), ("b", mod(final=True)), ("c", mod())]
    t = writer.history_tables(mods)
    assert list(t) == ["a", "c", "b"]
    sig = {}
    for sid, tabla in t.items():
        libro = tabla["pools"][0]["entries"][0]
        comps = libro["modifier"][0]["components"]
        assert comps["minecraft:custom_data"] == {botin.HISTORIA_MARCA: sid}
        ultima = comps["minecraft:written_book_content"]["pages"][-1]["raw"]
        pos, total, pista = ultima["with"]
        assert total == 3
        sig[sid] = pista["translate"].split(".")[-2]
        mapa = tabla["pools"][1]["entries"][0]["modifier"][0]["destination"]
        assert mapa == f"#heraldia:unicas/{sig[sid]}"
        assert ultima["translate"].endswith(".final" if sid == "b" else ".siguiente")
    assert sig == {"a": "c", "c": "b", "b": "a"}                              # la final vuelve a la primera


def test_mapa_de_la_historia_y_con_historia():
    t = botin.historia_tabla({"type": "minecraft:item", "name": "minecraft:written_book"}, {"type": "minecraft:item"})
    pesos = [e.get("weight") for e in t["pools"][1]["entries"]]
    assert pesos[0] / sum(pesos) == pytest.approx(botin.HISTORIA_MAPA)
    c = botin.con_historia({"pools": [{"rolls": 1}]}, "x")
    assert c["pools"][-1]["entries"][0]["value"] == "heraldia:historia/x" and "solo_sin_lootr" not in c["pools"][-1]


def test_historia_lang():
    lang = botin.historia_lang([("a", mod())])
    assert lang["es_es"]["heraldia.historia.a.pagina1"] == "Uno." and lang["en_us"]["heraldia.historia.a.pista"] == "to the north"
    assert set(lang["es_es"]) == set(lang["en_us"])
