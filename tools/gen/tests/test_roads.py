"""caminos.py: el rasgo heraldia:camino, su colocación, los textos del cartel y las opciones aldeas.caminos.*."""
import roads
import options
import writer


def test_trait_and_placement():
    assert roads.feature() == {"type": "heraldia:camino"}
    # sin modificadores: una vez por chunk, en su esquina (el Java pinta el chunk entero)
    assert roads.placed_feature() == {"feature": "heraldia:camino", "placement": []}


def test_writes_the_two_files(tmp_path):
    written_map = {}
    lang = roads.write(str(tmp_path), lambda out, rel, obj: written_map.__setitem__(rel, obj))
    assert written_map == {"data/heraldia/worldgen/feature/camino.json": roads.feature(),
                        "data/heraldia/worldgen/placed_feature/camino.json": roads.placed_feature()}
    assert lang is roads.LANG


def test_sign_texts_in_both_languages():
    assert roads.LANG["es_es"].keys() == roads.LANG["en_us"].keys()
    for lang in roads.LANG.values():
        for key, text in lang.items():
            assert key.startswith("heraldia.camino.cartel.")
            assert text.count("%s") == 1                      # la distancia
            assert len(text % "1999") <= 15                    # cabe en una línea de cartel
    # el Java usa el texto en español como respaldo (clientes sin el mod)
    assert roads.LANG["es_es"]["heraldia.camino.cartel.derecha"] == "%s bloques →"
    assert roads.LANG["es_es"]["heraldia.camino.cartel.izquierda"] == "← %s bloques"


def test_road_options():
    ops = {o["clave"]: o for o in options.schema()["opciones"]}
    assert ops["aldeas.caminos.activado"]["defecto"] is True
    d = ops["aldeas.caminos.distancia_maxima_bloques"]
    # la separación mínima entre dos aldeas es de 672 bloques (rejilla mínima de 1.000): por debajo no se uniría ninguna
    assert d["defecto"] == 2000 and d["min"] == 500 and d["max"] == 4000
    w = ops["aldeas.caminos.ancho"]
    assert (w["defecto"], w["min"], w["max"]) == (3, 1, 5)
    assert {o["seccion"] for k, o in ops.items() if k.startswith("aldeas.caminos.")} == {"caminos"}
    texts = options.lang()
    for k in ops:
        if k.startswith("aldeas.caminos."):
            assert "heraldia.config." + k in texts["es_es"] and "heraldia.config." + k + ".nombre" in texts["en_us"]


def test_texts_in_the_mod_language():
    # writer junta los textos de caminos con los demás (los mismos en los dos idiomas)
    assert writer.LANG["es_es"].keys() == writer.LANG["en_us"].keys()
