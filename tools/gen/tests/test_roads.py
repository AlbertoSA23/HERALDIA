"""caminos.py: the heraldia:camino feature, its placement, the sign texts and the aldeas.caminos.* options."""
import roads
import options
import writer


def test_trait_and_placement():
    assert roads.feature() == {"type": "heraldia:camino"}
    # without modifiers: once per chunk, at its corner (the Java paints the whole chunk)
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
            assert text.count("%s") == 1                      # the distance
            assert len(text % "1999") <= 15                    # fits on a sign line
    # the Java uses the Spanish text as a fallback (clients without the mod)
    assert roads.LANG["es_es"]["heraldia.camino.cartel.derecha"] == "%s bloques →"
    assert roads.LANG["es_es"]["heraldia.camino.cartel.izquierda"] == "← %s bloques"


def test_road_options():
    ops = {o["clave"]: o for o in options.schema()["opciones"]}
    assert ops["aldeas.caminos.activado"]["defecto"] is True
    d = ops["aldeas.caminos.distancia_maxima_bloques"]
    # the minimum separation between two villages is 672 blocks (minimum grid of 1,000): below that none would be joined
    assert d["defecto"] == 2000 and d["min"] == 500 and d["max"] == 4000
    w = ops["aldeas.caminos.ancho"]
    assert (w["defecto"], w["min"], w["max"]) == (3, 1, 5)
    assert {o["seccion"] for k, o in ops.items() if k.startswith("aldeas.caminos.")} == {"caminos"}
    texts = options.lang()
    for k in ops:
        if k.startswith("aldeas.caminos."):
            assert "heraldia.config." + k in texts["es_es"] and "heraldia.config." + k + ".nombre" in texts["en_us"]


def test_texts_in_the_mod_language():
    # writer merges the road texts with the others (the same in both languages)
    assert writer.LANG["es_es"].keys() == writer.LANG["en_us"].keys()
