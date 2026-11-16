"""caminos.py: el rasgo heraldia:camino, su colocación, los textos del cartel y las opciones aldeas.caminos.*."""
import caminos
import opciones
import writer


def test_rasgo_y_colocacion():
    assert caminos.feature() == {"type": "heraldia:camino"}
    # sin modificadores: una vez por chunk, en su esquina (el Java pinta el chunk entero)
    assert caminos.placed_feature() == {"feature": "heraldia:camino", "placement": []}


def test_escribe_los_dos_ficheros(tmp_path):
    escritos = {}
    lang = caminos.write(str(tmp_path), lambda out, rel, obj: escritos.__setitem__(rel, obj))
    assert escritos == {"data/heraldia/worldgen/feature/camino.json": caminos.feature(),
                        "data/heraldia/worldgen/placed_feature/camino.json": caminos.placed_feature()}
    assert lang is caminos.LANG


def test_textos_del_cartel_en_los_dos_idiomas():
    assert caminos.LANG["es_es"].keys() == caminos.LANG["en_us"].keys()
    for lang in caminos.LANG.values():
        for key, text in lang.items():
            assert key.startswith("heraldia.camino.cartel.")
            assert text.count("%s") == 1                      # la distancia
            assert len(text % "1999") <= 15                    # cabe en una línea de cartel
    # el Java usa el texto en español como respaldo (clientes sin el mod)
    assert caminos.LANG["es_es"]["heraldia.camino.cartel.derecha"] == "%s bloques →"
    assert caminos.LANG["es_es"]["heraldia.camino.cartel.izquierda"] == "← %s bloques"


def test_opciones_de_los_caminos():
    ops = {o["clave"]: o for o in opciones.schema()["opciones"]}
    assert ops["aldeas.caminos.activado"]["defecto"] is True
    d = ops["aldeas.caminos.distancia_maxima_bloques"]
    # la separación mínima entre dos aldeas es de 672 bloques (rejilla mínima de 1.000): por debajo no se uniría ninguna
    assert d["defecto"] == 2000 and d["min"] == 500 and d["max"] == 4000
    w = ops["aldeas.caminos.ancho"]
    assert (w["defecto"], w["min"], w["max"]) == (3, 1, 5)
    assert {o["seccion"] for k, o in ops.items() if k.startswith("aldeas.caminos.")} == {"caminos"}
    textos = opciones.lang()
    for k in ops:
        if k.startswith("aldeas.caminos."):
            assert "heraldia.config." + k in textos["es_es"] and "heraldia.config." + k + ".nombre" in textos["en_us"]


def test_textos_en_el_idioma_del_mod():
    # writer junta los textos de caminos con los demás (los mismos en los dos idiomas)
    assert writer.LANG["es_es"].keys() == writer.LANG["en_us"].keys()
