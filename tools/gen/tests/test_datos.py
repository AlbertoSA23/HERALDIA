"""logros.py, tratos.py, mapas.py y opciones.py: los datos que salen del registro de únicas y de los estilos."""
import pytest
import logros, tratos, mapas, opciones
import unicas
from themes import THEMES, FAMILIES

MODS = unicas.modules()


class RegVacio:
    templates = {}


@pytest.fixture(scope="module")
def arbol():
    return logros.build(RegVacio, MODS)


def test_logros_arbol_coherente(arbol):
    advs, lang = arbol
    assert "raiz" in advs and "display" in advs["raiz"] and advs["raiz"]["display"]["background"]
    for path, a in advs.items():
        if "parent" in a:
            assert a["parent"].split(":", 1)[1] in advs, path
        crit = set(a["criteria"])
        assert {c for g in a["requirements"] for c in g} == crit, path
        for part in ("title", "description"):
            k = a["display"][part]["translate"]
            if not k.startswith(("advancements.minecraft", "item.minecraft")):
                assert k in lang["es_es"] or k.startswith("heraldia.unicas"), (path, k)
        assert set(a.get("rewards", {})) <= {"experience"}
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_logros_por_unica_y_desafios(arbol):
    advs, _ = arbol
    for sid, m in MODS:
        assert f"unicas/{sid}/descubrir" in advs
        assert f"unicas/{sid}/guardian" not in advs          # sin plantillas no hay guardianes
    assert set(advs["unicas/trofeos"]["criteria"]) == {s for s, _ in MODS}
    assert set(advs["unicas/cronista"]["criteria"]) == {s for s, _ in MODS}
    assert set(advs["aldeas/todas"]["criteria"]) == set(FAMILIES)
    assert advs["unicas/todas"]["display"]["frame"] == "challenge"


def test_logro_de_guardian_con_un_registro():
    from core import Template
    from unicas._comun.piezas import GUARDIAN_TAG
    sid, m = MODS[0]
    t = Template(f"unicas/{sid}/x")
    t.entity(0, 0, 0, {"id": "minecraft:zombie", "Tags": [GUARDIAN_TAG, f"{GUARDIAN_TAG}.{sid}"],
                       "CustomName": {"translate": "k", "fallback": "Fb", "color": "red"}})

    class R:
        templates = {t.name: t}
    advs, _ = logros.build(R, [(sid, m)])
    g = advs[f"unicas/{sid}/guardian"]
    assert g["display"]["title"] == {"translate": "k", "fallback": "Fb"}
    pred = g["criteria"]["zombie"]["conditions"]["entity"]["predicate"]
    assert pred["minecraft:entity_tags"] == {"all_of": [f"{GUARDIAN_TAG}.{sid}"]}


def test_structure_tags():
    tags = logros.structure_tags(MODS)
    assert set(tags) == {f"aldeas/{f}" for f in FAMILIES} | {"unicas"}
    assert sum(len(v) for k, v in tags.items() if k != "unicas") == 2 * len(THEMES)


def test_tratos_contrato_y_ids_unicos():
    assert tratos.errores(MODS) == []
    todos = tratos.todos(MODS)
    ids = [i for i, *_ in todos]
    assert len(ids) == len(set(ids))
    for i, prof, lvl, t in todos:
        assert 1 <= lvl <= 5 and t["wants"]["id"] == "minecraft:emerald"
    lang = tratos.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_tratos_negativos(monkeypatch):
    monkeypatch.setitem(tratos.ESTILOS, "estilo_inventado", tratos.ESTILOS[next(iter(tratos.ESTILOS))])
    monkeypatch.setattr(tratos, "FORTIFICADAS", tratos.FORTIFICADAS + ("otro_inventado",))
    errs = " | ".join(tratos.errores(MODS))
    assert "estilo desconocido estilo_inventado" in errs and "FORTIFICADAS: estilo desconocido otro_inventado" in errs


def test_tratos_precio_y_prohibidos(monkeypatch):
    t = tratos.trato(80, {"id": "minecraft:netherite_sword", "components": {"minecraft:enchantments": {"minecraft:sharpness": 5}}})
    monkeypatch.setattr(tratos, "todos", lambda modules: [("heraldia:x", "weaponsmith", 2, t)])
    errs = " | ".join(tratos.errores(MODS))
    assert "precio fuera" in errs and "objeto prohibido" in errs and "pasa del nivel" in errs


def test_predicados_de_tratos():
    assert tratos.villager_predicate()["predicate"] == {"nbt": '{Tags:["heraldia"]}'}
    p = tratos.predicado(["heraldia:x"], "aldeas.tratos")
    assert p["type"] == "minecraft:all_of" and p["terms"][0] == {"type": "heraldia:opcion", "clave": "aldeas.tratos"}
    assert tratos.predicado() == tratos.villager_predicate()


def test_mapas():
    sid, m = MODS[0]
    mods = mapas.item_modifier(sid, m)
    assert mods[0]["destination"] == f"#heraldia:unicas/{sid}" and mods[0]["skip_existing_chunks"] is False
    assert mods[1]["on_fail"] == {"type": "minecraft:discard"}
    assert mapas.MIN_RADIUS <= mapas.search_radius({"spacing": 10 ** 6}) <= mapas.search_radius({"spacing": 1}) <= mapas.MAX_RADIUS
    tabla = mapas.with_maps({"pools": []}, MODS)
    entradas = tabla["pools"][-1]["entries"]
    vacio = entradas[-1]["weight"]
    assert len(entradas) == len(MODS) + 1 and len(MODS) / (len(MODS) + vacio) == pytest.approx(mapas.EPIC_MAP_CHANCE, rel=0.05)
    assert mapas.with_maps({"pools": []}, []) == {"pools": []}
    assert mapas.names("torre_x", object()) == ("Torre x", "Torre x")
    t = mapas.trade(sid, m)
    assert t["additional_wants"] == {"id": "minecraft:compass"} and t["wants"]["count"] == mapas.PRICE_EMERALDS


def test_opciones_esquema():
    s = opciones.schema()
    claves = [o["clave"] for o in s["opciones"]]
    assert len(claves) == len(set(claves)) and s["version"] == opciones.VERSION
    secciones = {x["id"] for x in s["secciones"]}
    for o in s["opciones"]:
        assert o["seccion"] in secciones
        if isinstance(o["defecto"], bool):
            assert "min" not in o
        elif isinstance(o["defecto"], str):        # opción de lista
            assert "min" not in o and o["defecto"] in o["valores"], o["clave"]
        else:
            assert o["min"] <= o["defecto"] <= o["max"], o["clave"]
    configurables = opciones.unique_placements()
    assert set(s["unicas"]) == set(configurables)
    for sid in configurables:
        assert f"unicas.{sid}.activada" in claves and f"unicas.{sid}.separacion_bloques" in claves
    assert {f"aldeas.estilos.{th['id']}" for th in THEMES} <= set(claves)


def test_opciones_textos_completos():
    s, lang = opciones.schema(), opciones.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])
    for o in s["opciones"]:
        assert o["ayuda"] in lang["es_es"] and o["nombre"] in lang["es_es"], o["clave"]


def test_opcion_sin_seccion_falla():
    with pytest.raises(ValueError, match="sin sección"):
        opciones._section("inventada.algo")
