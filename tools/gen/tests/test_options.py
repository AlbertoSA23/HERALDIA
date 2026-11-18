"""List options (dificultad.nivel) and the loot and difficulty ones in the schema read by the Java (opciones.py)."""
import pytest

import options


def _by_key():
    return {o["clave"]: o for o in options.schema()["opciones"]}


def test_loot_and_difficulty_options():
    o = _by_key()
    assert o["botin.reponer.activado"]["defecto"] is False          # by default it does not change the world
    assert (o["botin.reponer.dias"]["defecto"], o["botin.reponer.dias"]["min"], o["botin.reponer.dias"]["max"]) == (7, 1, 60)
    assert o["dificultad.nivel"]["defecto"] == "normal"              # normal = the usual behaviour
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
    assert o["valores"] == ["casual", "estandar", "hardcore", "ligero", "personalizado"]
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
    assert set(p) == {"casual", "estandar", "hardcore", "ligero"}
    keys = set(options.gameplay_options())
    assert all(set(v) == keys for n, v in p.items() if n != "ligero")
    assert set(p["ligero"]) == keys | set(options.LIGHT_OPTIONS)
    assert set(options.profile_options()) == keys | set(options.LIGHT_OPTIONS)
    for k in ("dificultad.nivel", "dificultad.escalar_por_jugadores", "botin.reponer.activado", "jefes.refuerzos.activado",
              "jefes.fases.activado", "arena.experiencia_porcentaje", "arena.oleada.mobs_incremento", "arena.oleada.stats_incremento"):
        assert k in keys, k


def test_the_gameplay_profiles_never_touch_the_generation():
    """casual, estandar and hardcore never touch generation; only the generation profiles (ligero) do, and only with the
    options of LIGHT_OPTIONS (never the grids of villages or unique structures: in an existing world they would move)."""
    s = options.schema()
    gen = {o["clave"] for o in s["opciones"] if o.get("generacion")}
    keys = set(options.gameplay_options())
    assert not keys & gen
    assert all(k.startswith(options.PROFILE_PREFIXES) for k in keys)
    assert "arena.generar_en_mundos_nuevos" in gen and "arena.generar_en_mundos_nuevos" not in options.profile_options()
    assert s["perfiles_generacion"] == ["ligero"] == list(options.GENERATION_PROFILES)
    for name, values in s["perfiles"].items():
        if name not in s["perfiles_generacion"]:
            assert not set(values) & gen, name
    assert set(s["perfiles"]["ligero"]) & gen == {k for k in options.LIGHT_OPTIONS if options.is_generation(k)}
    for k in options.LIGHT_OPTIONS:
        assert not k.startswith(("unicas.", "aldeas.separacion", "aldeas.maximo")), k
    for o in s["opciones"]:
        if o["clave"].startswith(("aldeas.", "unicas.", "medianas.", "minas.", "compatibilidad.")):
            assert o.get("generacion"), o["clave"]
            assert bool(o.get("perfil")) == (o["clave"] in options.LIGHT_OPTIONS), o["clave"]


def test_light_is_the_standard_game_with_lighter_generation():
    p, default = options.profiles(), {o["clave"]: o["defecto"] for o in options.schema()["opciones"]}
    light, standard = p["ligero"], p["estandar"]
    assert {k: v for k, v in light.items() if k in standard} == standard        # the gameplay of estandar
    assert light["aldeas.caminos.activado"] is False and light["caravanas.activado"] is False
    assert light["aldeas.porcentaje_grandes"] < default["aldeas.porcentaje_grandes"]
    assert light["medianas.frecuencia_porcentaje"] < default["medianas.frecuencia_porcentaje"]
    assert light["medianas.distancia_minima.bloques"] > default["medianas.distancia_minima.bloques"]
    assert light["minas.vanilla.multiplicador"] < default["minas.vanilla.multiplicador"]
    assert list(light) == [k for k in options.profile_options() if k in light]   # schema order


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
    for v in p.values():   # the arena: enemies grow more than their strength
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
        # same format placeholders as English
        for k in PROFILE_KEYS:
            assert texts[k].count("%s") == base["en_us"][k].count("%s"), (code, k)
    assert len(languages.everyone()) == 8


def test_generation_options_that_reload_are_listed():
    """options.GENERATION and Reload.RELOADABLE (Java) overlap on purpose only in options.GENERATION_RELOADABLE: the
    "generacion" mark keeps the profiles away from an option, it does not make it wait for a restart. A new overlap
    (a generation option under a reloadable prefix, or a reloadable prefix covering a generation option) must be
    decided and written there; and Reload.STARTUP_ONLY only names real keys."""
    import os, re
    src = open(os.path.join(os.path.dirname(options.__file__), "..", "..", "src", "main", "java", "io", "github",
                            "albertosa23", "heraldia", "config", "Reload.java"), encoding="utf-8").read()

    def java_list(name):
        return re.findall(r'"([^"]+)"', re.search(name + r" = List\.of\((.*?)\);", src, re.S).group(1))
    reloadable, startup_only = java_list("RELOADABLE"), java_list("STARTUP_ONLY")
    assert reloadable and startup_only

    def reloads(k):
        return k not in startup_only and any(k.startswith(p) if p.endswith(".") else k == p for p in reloadable)
    keys = [o["clave"] for o in options.schema()["opciones"]]
    assert set(startup_only) <= set(keys)
    both = {k for k in keys if options.is_generation(k) and reloads(k)}
    assert both == set(options.GENERATION_RELOADABLE)
