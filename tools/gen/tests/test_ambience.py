"""Options of the ambient effects (ambience/Ambience.java): one per effect plus one for all, never generation, never a profile."""
import options

KEYS = ("ambiente.activado", "ambiente.campanas", "ambiente.sirena_faro", "ambiente.minas")


def test_one_option_per_effect_and_one_for_all():
    o = {x["clave"]: x for x in options.schema()["opciones"]}
    for k in KEYS:
        assert o[k]["defecto"] is True, k
        assert o[k]["seccion"] == "ambiente", k
        assert not o[k].get("generacion"), f"{k} does not touch world generation"
        assert not o[k].get("perfil"), f"{k} is not set by any profile"
    assert "ambiente" in [s["id"] for s in options.schema()["secciones"]]


def test_texts_in_both_base_languages():
    lang = options.lang()
    for code in ("es_es", "en_us"):
        for k in KEYS:
            assert lang[code][f"heraldia.config.{k}"] and lang[code][f"heraldia.config.{k}.nombre"], (code, k)
        assert lang[code]["heraldia.config.seccion.ambiente"]
