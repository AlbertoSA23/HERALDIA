"""logros.py, tratos.py, mapas.py and opciones.py: the data that comes from the registry of unique structures and styles."""
import pytest
import advancements, trades, maps, options
import uniques
from themes import THEMES, FAMILIES

MODS = uniques.modules()


class RegEmpty:
    templates = {}


@pytest.fixture(scope="module")
def tree():
    return advancements.build(RegEmpty, MODS)


def test_advancements_tree_coherent(tree):
    advs, lang = tree
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


def test_advancements_per_unique_and_challenges(tree):
    advs, _ = tree
    for sid, m in MODS:
        assert f"unicas/{sid}/descubrir" in advs
        assert f"unicas/{sid}/guardian" not in advs          # without templates there are no guardians
    assert set(advs["unicas/trofeos"]["criteria"]) == {s for s, _ in MODS}
    assert set(advs["unicas/cronista"]["criteria"]) == {s for s, _ in MODS}
    assert set(advs["aldeas/todas"]["criteria"]) == set(FAMILIES)
    assert advs["unicas/todas"]["display"]["frame"] == "challenge"


def test_guardian_advancement_with_one_registry():
    from core import Template
    from uniques._common.pieces import GUARDIAN_TAG
    sid, m = MODS[0]
    t = Template(f"unicas/{sid}/x")
    t.entity(0, 0, 0, {"id": "minecraft:zombie", "Tags": [GUARDIAN_TAG, f"{GUARDIAN_TAG}.{sid}"],
                       "CustomName": {"translate": "k", "fallback": "Fb", "color": "red"}})

    class R:
        templates = {t.name: t}
    advs, _ = advancements.build(R, [(sid, m)])
    g = advs[f"unicas/{sid}/guardian"]
    assert g["display"]["title"] == {"translate": "k", "fallback": "Fb"}
    pred = g["criteria"]["zombie"]["conditions"]["entity"]["predicate"]
    assert pred["minecraft:entity_tags"] == {"all_of": [f"{GUARDIAN_TAG}.{sid}"]}


def test_structure_tags():
    tags = advancements.structure_tags(MODS)
    assert set(tags) == {f"aldeas/{f}" for f in FAMILIES} | {"unicas"}
    assert sum(len(v) for k, v in tags.items() if k != "unicas") == 2 * len(THEMES)


def test_trades_contract_and_unique_ids():
    assert trades.errors(MODS) == []
    everyone = trades.everyone(MODS)
    ids = [i for i, *_ in everyone]
    assert len(ids) == len(set(ids))
    for i, depth, lvl, t in everyone:
        assert 1 <= lvl <= 5 and t["wants"]["id"] == "minecraft:emerald"
    lang = trades.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])


def test_trades_negative(monkeypatch):
    monkeypatch.setitem(trades.STYLES, "estilo_inventado", trades.STYLES[next(iter(trades.STYLES))])
    monkeypatch.setattr(trades, "FORTIFIED", trades.FORTIFIED + ("otro_inventado",))
    errs = " | ".join(trades.errors(MODS))
    assert "estilo desconocido estilo_inventado" in errs and "FORTIFICADAS: estilo desconocido otro_inventado" in errs


def test_trades_price_and_forbidden(monkeypatch):
    t = trades.trade(80, {"id": "minecraft:netherite_sword", "components": {"minecraft:enchantments": {"minecraft:sharpness": 5}}})
    monkeypatch.setattr(trades, "everyone", lambda modules: [("heraldia:x", "weaponsmith", 2, t)])
    errs = " | ".join(trades.errors(MODS))
    assert "precio fuera" in errs and "objeto prohibido" in errs and "pasa del nivel" in errs


def test_trade_predicates():
    assert trades.villager_predicate()["predicate"] == {"nbt": '{Tags:["heraldia"]}'}
    p = trades.predicate(["heraldia:x"], "aldeas.tratos")
    assert p["type"] == "minecraft:all_of" and p["terms"][0] == {"type": "heraldia:opcion", "clave": "aldeas.tratos"}
    assert trades.predicate() == trades.villager_predicate()


def test_maps():
    sid, m = MODS[0]
    mods = maps.item_modifier(sid, m)
    assert mods[0]["destination"] == f"#heraldia:unicas/{sid}" and mods[0]["skip_existing_chunks"] is False
    assert mods[1]["on_fail"] == {"type": "minecraft:discard"}
    assert maps.MIN_RADIUS <= maps.search_radius({"spacing": 10 ** 6}) <= maps.search_radius({"spacing": 1}) <= maps.MAX_RADIUS
    tbl = maps.with_maps({"pools": []}, MODS)
    entrances = tbl["pools"][-1]["entries"]
    empty = entrances[-1]["weight"]
    assert len(entrances) == len(MODS) + 1 and len(MODS) / (len(MODS) + empty) == pytest.approx(maps.EPIC_MAP_CHANCE, rel=0.05)
    assert maps.with_maps({"pools": []}, []) == {"pools": []}
    assert maps.names("torre_x", object()) == ("Torre x", "Torre x")
    t = maps.trade(sid, m)
    assert t["additional_wants"] == {"id": "minecraft:compass"} and t["wants"]["count"] == maps.PRICE_EMERALDS


def test_options_schema():
    s = options.schema()
    keys = [o["clave"] for o in s["opciones"]]
    assert len(keys) == len(set(keys)) and s["version"] == options.VERSION
    sections_list = {x["id"] for x in s["secciones"]}
    for o in s["opciones"]:
        assert o["seccion"] in sections_list
        if isinstance(o["defecto"], bool):
            assert "min" not in o
        elif isinstance(o["defecto"], str):        # list option
            assert "min" not in o and o["defecto"] in o["valores"], o["clave"]
        else:
            assert o["min"] <= o["defecto"] <= o["max"], o["clave"]
    configurable = options.unique_placements()
    assert set(s["unicas"]) == set(configurable)
    for sid in configurable:
        assert f"unicas.{sid}.activada" in keys and f"unicas.{sid}.separacion_bloques" in keys
    assert {f"aldeas.estilos.{th['id']}" for th in THEMES} <= set(keys)


def test_options_texts_complete():
    s, lang = options.schema(), options.lang()
    assert set(lang["es_es"]) == set(lang["en_us"])
    for o in s["opciones"]:
        assert o["ayuda"] in lang["es_es"] and o["nombre"] in lang["es_es"], o["clave"]


def test_option_without_section_fails():
    with pytest.raises(ValueError, match="has no section"):
        options._section("inventada.algo")
