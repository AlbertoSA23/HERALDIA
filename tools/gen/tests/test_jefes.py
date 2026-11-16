"""Contrato de los refuerzos de los guardianes (jefes.py, REFUERZOS de cada única) y el esquema heraldia/jefes.json
que lee el Java (comun/jefes). Sin generar el datapack."""
import types
import pytest
import jefes
import opciones
import unicas
import writer

MODS = unicas.modules()
IDS = [sid for sid, _ in MODS]
# Tipo de mob del guardián final de cada única (lo que pack.tag_guardians deja en reg.guardianes), para el esquema.
GUARDIANES = {sid: {"minecraft:zombie": "minecraft:entities/zombie"} for sid in IDS}


def mod(**kw):
    return types.SimpleNamespace(**kw)


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_refuerzos_de_cada_unica_cumplen(sid, m):
    propios = getattr(m, "REFUERZOS", None)
    if propios is not None:
        assert jefes.errores(sid, propios) == []
    out = jefes.refuerzos(sid, m, GUARDIANES[sid])
    assert jefes.MIN_REFUERZOS <= len(out) <= jefes.MAX_REFUERZOS
    for r in out:
        assert r["mob"].startswith("minecraft:") and r["mob"].split(":")[1] in jefes.REFUERZO_MOBS


def test_familias_cumplen_y_cubren_los_guardianes():
    for fam, specs in jefes.FAMILIAS.items():
        assert jefes.errores(fam, specs) == [], fam
    assert set(jefes.MOB_FAMILIA.values()) <= set(jefes.FAMILIAS)
    assert jefes.GENERICA in jefes.FAMILIAS
    # los tipos de los guardianes de hoy (piezas.guardian y el jefe de la Atlántida) tienen familia propia
    for mob in ("zombie", "husk", "drowned", "skeleton", "stray", "bogged", "wither_skeleton", "evoker",
                "vindicator", "elder_guardian"):
        assert jefes.familia(mob) != jefes.GENERICA, mob
        assert jefes.familia("minecraft:" + mob) == jefes.familia(mob)


def test_familia_desconocida_es_la_generica():
    assert jefes.familia("minecraft:creeper") == jefes.GENERICA
    out = jefes.refuerzos("x", mod(), {"minecraft:creeper": "t"})
    assert out == [jefes.normalizar(s) for s in jefes.FAMILIAS[jefes.GENERICA]]
    assert jefes.refuerzos("x", mod(), {}) == out       # sin guardián conocido, también


def test_sin_refuerzos_propios_usa_la_familia_del_guardian():
    assert jefes.refuerzos("x", mod(), {"minecraft:husk": "t"}) == [{"mob": "minecraft:husk"}] * 2
    assert jefes.refuerzos("x", mod(), {"minecraft:elder_guardian": "t"}) == [{"mob": "minecraft:guardian"}] * 2
    assert [r["mob"] for r in jefes.refuerzos("x", mod(), {"minecraft:evoker": "t"})] == ["minecraft:vindicator",
                                                                                       "minecraft:pillager"]


def test_refuerzos_propios_mandan_sobre_la_familia():
    m = mod(REFUERZOS=["witch", {"mob": "minecraft:vindicator", "equipo": {"mainhand": "iron_axe"}}])
    assert jefes.refuerzos("x", m, {"minecraft:husk": "t"}) == [
        {"mob": "minecraft:witch"}, {"mob": "minecraft:vindicator", "equipo": {"mainhand": "minecraft:iron_axe"}}]


@pytest.mark.parametrize("malo, trozo", [
    (["zombie"], "1 refuerzos"),
    (["zombie"] * 4, "4 refuerzos"),
    (["zombie", "hoglin"], "hoglin no puede"),
    (["zombie", "wither"], "wither no puede"),
    (["zombie", "vex"], "vex no puede"),
    (["zombie", "heraldia:zombie"], "heraldia:zombie no puede"),
    (["zombie", {"mob": "zombie", "equipo": {"mainhand": "netherite_sword"}}], "prohibido"),
    (["zombie", {"mob": "zombie", "equipo": {"chest": "elytra"}}], "prohibido"),
    (["zombie", {"mob": "zombie", "equipo": {"espalda": "stick"}}], "ranura espalda"),
    (["zombie", {"mob": "zombie", "nombre": "x"}], "claves desconocidas"),
    (["zombie", {"equipo": {}}], "ni un id"),
    ("zombie", "debe ser una lista"),
])
def test_errores_del_contrato(malo, trozo):
    errs = jefes.errores("x", malo)
    assert any(trozo in e for e in errs), errs
    if isinstance(malo, list):
        with pytest.raises(ValueError):
            jefes.refuerzos("x", mod(REFUERZOS=malo), {})


def test_normalizar():
    assert jefes.normalizar("husk") == {"mob": "minecraft:husk"}
    assert jefes.normalizar({"mob": "minecraft:husk", "equipo": {}}) == {"mob": "minecraft:husk"}
    assert jefes.normalizar({"mob": "husk", "equipo": {"offhand": "shield"}}) == {
        "mob": "minecraft:husk", "equipo": {"offhand": "minecraft:shield"}}


def test_esquema():
    s = jefes.schema(MODS, GUARDIANES)
    assert s["version"] == jefes.VERSION and s["generica"] == jefes.GENERICA
    assert sorted(s["unicas"]) == IDS
    assert set(s["familias"]) == set(jefes.FAMILIAS)
    assert all(k.startswith("minecraft:") and v in s["familias"] for k, v in s["mob_familia"].items())
    for specs in list(s["unicas"].values()) + list(s["familias"].values()):
        assert all(set(r) <= {"mob", "equipo"} for r in specs)
    # una única con REFUERZOS propios los lleva tal cual, sin mirar su guardián
    con = [sid for sid, m in MODS if hasattr(m, "REFUERZOS")]
    assert con, "ninguna única con REFUERZOS propios"
    for sid in con:
        assert s["unicas"][sid] == [jefes.normalizar(r) for r in dict(MODS)[sid].REFUERZOS]


def test_textos_y_opciones():
    lang = jefes.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for fase in (2, 3):
        for suf in ("", ".refuerzos"):
            k = f"heraldia.jefes.fase.{fase}{suf}"
            assert lang["es_es"][k].count("%s") == 1 and lang["en_us"][k].count("%s") == 1
    assert "heraldia.jefes.refuerzos" in lang["es_es"]
    # en el idioma del mod (y así en el respaldo en español de los clientes sin el mod)
    assert all(writer.LANG["es_es"][k] == v for k, v in lang["es_es"].items())
    claves = {o["clave"]: o for o in opciones.schema()["opciones"]}
    for k in ("jefes.fases.activado", "jefes.refuerzos.activado", "jefes.barra.activado"):
        assert claves[k]["defecto"] is True and claves[k]["seccion"] == "jefes"
