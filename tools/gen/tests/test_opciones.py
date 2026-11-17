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


# --- perfiles de juego (T36) ---

def test_perfil_es_la_primera_opcion_de_lista_y_por_defecto_estandar():
    o = _por_clave()["perfil"]
    assert opciones.schema()["opciones"][0]["clave"] == "perfil"
    assert o["valores"] == ["casual", "estandar", "hardcore", "personalizado"]
    assert o["defecto"] == "estandar" and o["seccion"] == "perfil"
    assert "perfil" not in o and "generacion" not in o


def test_estandar_es_exactamente_lo_de_siempre():
    defecto = {o["clave"]: o["defecto"] for o in opciones.schema()["opciones"]}
    estandar = opciones.perfiles()["estandar"]
    assert estandar == {k: defecto[k] for k in estandar}
    assert estandar["dificultad.nivel"] == "normal" and estandar["botin.reponer.activado"] is False
    assert estandar["jefes.refuerzos.porcentaje"] == 100 and estandar["jefes.refuerzos.maximo_vivos"] == 4


def test_los_perfiles_fijan_las_mismas_opciones_de_juego():
    p = opciones.perfiles()
    assert set(p) == {"casual", "estandar", "hardcore"}
    claves = set(opciones.opciones_perfil())
    assert all(set(v) == claves for v in p.values())
    for k in ("dificultad.nivel", "dificultad.escalar_por_jugadores", "botin.reponer.activado", "jefes.refuerzos.activado",
              "jefes.fases.activado", "arena.experiencia_porcentaje", "arena.oleada.mobs_incremento", "arena.oleada.stats_incremento"):
        assert k in claves, k


def test_el_perfil_nunca_toca_la_generacion():
    gen = {o["clave"] for o in opciones.schema()["opciones"] if o.get("generacion")}
    claves = set(opciones.opciones_perfil())
    assert not claves & gen
    assert all(k.startswith(opciones.PERFIL_PREFIJOS) for k in claves)
    assert "arena.generar_en_mundos_nuevos" in gen and "arena.generar_en_mundos_nuevos" not in claves
    for o in opciones.schema()["opciones"]:
        if o["clave"].startswith(("aldeas.", "unicas.", "medianas.", "minas.", "compatibilidad.")):
            assert o.get("generacion"), o["clave"]
            assert not o.get("perfil"), o["clave"]


def test_marcas_del_esquema():
    s = opciones.schema()
    assert s["perfiles"] == opciones.perfiles()
    marcadas = [o["clave"] for o in s["opciones"] if o.get("perfil")]
    assert marcadas == opciones.opciones_perfil()


def test_casual_mas_facil_y_hardcore_mas_dificil():
    p = opciones.perfiles()
    c, e, h = p["casual"], p["estandar"], p["hardcore"]
    orden = ["facil", "normal", "dificil", "heroica"]
    assert orden.index(c["dificultad.nivel"]) < orden.index(e["dificultad.nivel"]) < orden.index(h["dificultad.nivel"])
    assert h["dificultad.nivel"] == "heroica" and c["botin.reponer.activado"] is True
    assert h["jefes.refuerzos.porcentaje"] > e["jefes.refuerzos.porcentaje"] > c["jefes.refuerzos.porcentaje"]
    assert h["jefes.refuerzos.maximo_vivos"] > e["jefes.refuerzos.maximo_vivos"] > c["jefes.refuerzos.maximo_vivos"]
    assert h["arena.experiencia_porcentaje"] < e["arena.experiencia_porcentaje"] < c["arena.experiencia_porcentaje"]
    for v in p.values():   # la arena: los enemigos crecen más que su fuerza
        assert v["arena.oleada.stats_incremento"] <= v["arena.oleada.mobs_incremento"]


def test_un_perfil_que_toca_la_generacion_falla(monkeypatch):
    malo = {k: dict(v) for k, v in opciones.PERFILES.items()}
    for nombre in ("casual", "hardcore"):
        malo[nombre]["minas.entradas.activado"] = False
    monkeypatch.setattr(opciones, "PERFILES", malo)
    with pytest.raises(AssertionError):
        opciones.perfiles()


def test_un_perfil_fuera_de_rango_falla(monkeypatch):
    malo = {k: dict(v) for k, v in opciones.PERFILES.items()}
    malo["hardcore"]["arena.max_mobs_vivos"] = 999
    monkeypatch.setattr(opciones, "PERFILES", malo)
    with pytest.raises(AssertionError):
        opciones.perfiles()


CLAVES_PERFIL = ["heraldia.config.perfil", "heraldia.config.perfil.nombre", "heraldia.config.seccion.perfil",
                 "heraldia.config.perfil.casual", "heraldia.config.perfil.estandar", "heraldia.config.perfil.hardcore",
                 "heraldia.config.perfil.personalizado", "heraldia.config.jefes.refuerzos.porcentaje",
                 "heraldia.config.jefes.refuerzos.porcentaje.nombre", "heraldia.config.jefes.refuerzos.maximo_vivos",
                 "heraldia.config.jefes.refuerzos.maximo_vivos.nombre", "heraldia.config.pantalla.perfil_valor",
                 "heraldia.config.pantalla.fijada", "heraldia.config.pantalla.perfil_efectivo", "heraldia.perfil.titulo",
                 "heraldia.perfil.opcion", "heraldia.perfil.opcion.fijada", "heraldia.perfil.ninguna",
                 "heraldia.perfil.personalizado", "heraldia.config.perfiles"]


def test_textos_del_perfil_en_los_ocho_idiomas():
    import json
    import idiomas
    base = opciones.lang()
    for code in idiomas.todos():
        if code in base:
            textos = base[code]
        else:
            with open(idiomas.ruta(code), encoding="utf-8") as f:
                textos = json.load(f)
        for k in CLAVES_PERFIL:
            assert textos.get(k), (code, k)
        # mismos huecos de formato que el inglés
        for k in CLAVES_PERFIL:
            assert textos[k].count("%s") == base["en_us"][k].count("%s"), (code, k)
    assert len(idiomas.todos()) == 8
