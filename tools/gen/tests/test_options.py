"""Opciones de lista (dificultad.nivel) y las de botín y dificultad en el esquema que lee el Java (opciones.py)."""
import pytest

import options


def _by_key():
    return {o["clave"]: o for o in options.schema()["opciones"]}


def test_loot_and_difficulty_options():
    o = _by_key()
    assert o["botin.reponer.activado"]["defecto"] is False          # por defecto no cambia el mundo
    assert (o["botin.reponer.dias"]["defecto"], o["botin.reponer.dias"]["min"], o["botin.reponer.dias"]["max"]) == (7, 1, 60)
    assert o["dificultad.nivel"]["defecto"] == "normal"              # normal = comportamiento de siempre
    assert o["dificultad.escalar_por_jugadores"]["defecto"] is False
    assert o["botin.reponer.activado"]["seccion"] == "botin" and o["dificultad.nivel"]["seccion"] == "dificultad"


def test_list_option():
    n = _by_key()["dificultad.nivel"]
    assert n["valores"] == ["facil", "normal", "dificil", "heroica"]
    assert n["nombres_valores"] == [f"heraldia.config.dificultad.nivel.{v}" for v in n["valores"]]
    assert "min" not in n and "max" not in n
    lang = options.lang()
    for code in ("es_es", "en_us"):
        for k in n["nombres_valores"] + ["heraldia.config.valores", n["nombre"], n["ayuda"]]:
            assert lang[code].get(k), (code, k)
    assert lang["es_es"]["heraldia.config.dificultad.nivel.heroica"] == "Heroica"
    assert lang["en_us"]["heraldia.config.dificultad.nivel.facil"] == "Easy"


def test_only_list_ones_carry_values():
    for o in options.schema()["opciones"]:
        if "valores" in o:
            assert isinstance(o["defecto"], str) and o["defecto"] in o["valores"]
        else:
            assert not isinstance(o["defecto"], str), o["clave"]


def test_default_value_outside_the_list_fails():
    with pytest.raises(AssertionError):
        options._option("dificultad.x", "imposible", ["facil", "normal"], None, "k")


# --- perfiles de juego (T36) ---

def test_profile_is_the_first_list_option_and_default_standard():
    o = _by_key()["perfil"]
    assert options.schema()["opciones"][0]["clave"] == "perfil"
    assert o["valores"] == ["casual", "estandar", "hardcore", "personalizado"]
    assert o["defecto"] == "estandar" and o["seccion"] == "perfil"
    assert "perfil" not in o and "generacion" not in o


def test_standard_es_exactly_what_is_of_always():
    default = {o["clave"]: o["defecto"] for o in options.schema()["opciones"]}
    standard = options.profiles()["estandar"]
    assert standard == {k: default[k] for k in standard}
    assert standard["dificultad.nivel"] == "normal" and standard["botin.reponer.activado"] is False
    assert standard["jefes.refuerzos.porcentaje"] == 100 and standard["jefes.refuerzos.maximo_vivos"] == 4


def test_profiles_set_the_same_game_options():
    p = options.profiles()
    assert set(p) == {"casual", "estandar", "hardcore"}
    keys = set(options.profile_options())
    assert all(set(v) == keys for v in p.values())
    for k in ("dificultad.nivel", "dificultad.escalar_por_jugadores", "botin.reponer.activado", "jefes.refuerzos.activado",
              "jefes.fases.activado", "arena.experiencia_porcentaje", "arena.oleada.mobs_incremento", "arena.oleada.stats_incremento"):
        assert k in keys, k


def test_the_profile_never_touches_the_generation():
    gen = {o["clave"] for o in options.schema()["opciones"] if o.get("generacion")}
    keys = set(options.profile_options())
    assert not keys & gen
    assert all(k.startswith(options.PROFILE_PREFIXES) for k in keys)
    assert "arena.generar_en_mundos_nuevos" in gen and "arena.generar_en_mundos_nuevos" not in keys
    for o in options.schema()["opciones"]:
        if o["clave"].startswith(("aldeas.", "unicas.", "medianas.", "minas.", "compatibilidad.")):
            assert o.get("generacion"), o["clave"]
            assert not o.get("perfil"), o["clave"]


def test_schema_marks():
    s = options.schema()
    assert s["perfiles"] == options.profiles()
    marked = [o["clave"] for o in s["opciones"] if o.get("perfil")]
    assert marked == options.profile_options()


def test_casual_more_easier_and_hardcore_more_harder():
    p = options.profiles()
    c, e, h = p["casual"], p["estandar"], p["hardcore"]
    order = ["facil", "normal", "dificil", "heroica"]
    assert order.index(c["dificultad.nivel"]) < order.index(e["dificultad.nivel"]) < order.index(h["dificultad.nivel"])
    assert h["dificultad.nivel"] == "heroica" and c["botin.reponer.activado"] is True
    assert h["jefes.refuerzos.porcentaje"] > e["jefes.refuerzos.porcentaje"] > c["jefes.refuerzos.porcentaje"]
    assert h["jefes.refuerzos.maximo_vivos"] > e["jefes.refuerzos.maximo_vivos"] > c["jefes.refuerzos.maximo_vivos"]
    assert h["arena.experiencia_porcentaje"] < e["arena.experiencia_porcentaje"] < c["arena.experiencia_porcentaje"]
    for v in p.values():   # la arena: los enemigos crecen más que su fuerza
        assert v["arena.oleada.stats_incremento"] <= v["arena.oleada.mobs_incremento"]


def test_a_profile_touching_generation_fails(monkeypatch):
    bad = {k: dict(v) for k, v in options.PROFILES.items()}
    for name in ("casual", "hardcore"):
        bad[name]["minas.entradas.activado"] = False
    monkeypatch.setattr(options, "PROFILES", bad)
    with pytest.raises(AssertionError):
        options.profiles()


def test_a_profile_out_of_range_fails(monkeypatch):
    bad = {k: dict(v) for k, v in options.PROFILES.items()}
    bad["hardcore"]["arena.max_mobs_vivos"] = 999
    monkeypatch.setattr(options, "PROFILES", bad)
    with pytest.raises(AssertionError):
        options.profiles()


PROFILE_KEYS = ["heraldia.config.perfil", "heraldia.config.perfil.nombre", "heraldia.config.seccion.perfil",
                 "heraldia.config.perfil.casual", "heraldia.config.perfil.estandar", "heraldia.config.perfil.hardcore",
                 "heraldia.config.perfil.personalizado", "heraldia.config.jefes.refuerzos.porcentaje",
                 "heraldia.config.jefes.refuerzos.porcentaje.nombre", "heraldia.config.jefes.refuerzos.maximo_vivos",
                 "heraldia.config.jefes.refuerzos.maximo_vivos.nombre", "heraldia.config.pantalla.perfil_valor",
                 "heraldia.config.pantalla.fijada", "heraldia.config.pantalla.perfil_efectivo", "heraldia.perfil.titulo",
                 "heraldia.perfil.opcion", "heraldia.perfil.opcion.fijada", "heraldia.perfil.ninguna",
                 "heraldia.perfil.personalizado", "heraldia.config.perfiles"]


def test_profile_texts_in_the_eight_languages():
    import json
    import languages
    base = options.lang()
    for code in languages.everyone():
        if code in base:
            texts = base[code]
        else:
            with open(languages.route(code), encoding="utf-8") as f:
                texts = json.load(f)
        for k in PROFILE_KEYS:
            assert texts.get(k), (code, k)
        # mismos huecos de formato que el inglés
        for k in PROFILE_KEYS:
            assert texts[k].count("%s") == base["en_us"][k].count("%s"), (code, k)
    assert len(languages.everyone()) == 8
