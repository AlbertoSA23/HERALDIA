"""Crónica de los Heraldos: contrato HISTORIA (botin.historia_errores) y cadena (botin.historia_cadena, writer)."""
import types
import pytest
from uniques._common import chest_loot

STORY_DATA = {"cofre": "biblioteca", "relato": [("Uno.", "One.")], "pista": ("al norte", "to the north")}


def mod(**story):
    m = types.SimpleNamespace(STORY=dict(STORY_DATA, **story), STRUCTURE={"spacing": 250}, LOOT={"biblioteca": {}})
    return m


def test_story_valid():
    assert chest_loot.story_errors("x", STORY_DATA, {"biblioteca": {}}) == []


@pytest.mark.parametrize("change, msg", [
    (dict(cofre="otro"), "no es una tabla de su LOOT"),
    (dict(relato=[]), "HISTORIA.relato"),
    (dict(relato=[("a", "b")] * 3), "HISTORIA.relato"),
    (dict(pista=("solo",)), "HISTORIA.pista"),
    (dict(relato=[("palabra " * 200, "word")]), "no cabe en una página"),
    (dict(pista=("palabra " * 120, "w")), "no cabe en una página"),
])
def test_story_negative_cases(change, msg):
    errs = chest_loot.story_errors("x", dict(STORY_DATA, **change), {"biblioteca": {}})
    assert any(msg in e for e in errs), errs


def test_story_absent():
    assert "falta HISTORIA" in chest_loot.story_errors("x", None, {})[0]


def test_chain_by_id_with_the_final_to_the_end():
    mods = [("a", mod()), ("b", mod(final=True)), ("c", mod()), ("d", types.SimpleNamespace())]
    assert chest_loot.story_chain(mods) == ["a", "c", "b"]
    assert chest_loot.story_chain_errors(mods) == []
    assert chest_loot.story_chain_errors([("a", mod())])                     # sin final
    assert chest_loot.story_chain_errors([("a", mod(final=True)), ("b", mod(final=True))])   # dos finales


def test_chain_tables_form_a_cycle():
    import writer
    mods = [("a", mod()), ("b", mod(final=True)), ("c", mod())]
    t = writer.history_tables(mods)
    assert list(t) == ["a", "c", "b"]
    next_unique = {}
    for sid, tbl in t.items():
        written_book = tbl["pools"][0]["entries"][0]
        comps = written_book["modifier"][0]["components"]
        assert comps["minecraft:custom_data"] == {chest_loot.STORY_MARK: sid}
        last = comps["minecraft:written_book_content"]["pages"][-1]["raw"]
        pos, total, clue = last["with"]
        assert total == 3
        next_unique[sid] = clue["translate"].split(".")[-2]
        map_obj = tbl["pools"][1]["entries"][0]["modifier"][0]["destination"]
        assert map_obj == f"#heraldia:unicas/{next_unique[sid]}"
        assert last["translate"].endswith(".final" if sid == "b" else ".siguiente")
    assert next_unique == {"a": "c", "c": "b", "b": "a"}                              # la final vuelve a la primera


def test_story_map_and_with_story():
    t = chest_loot.story_table({"type": "minecraft:item", "name": "minecraft:written_book"}, {"type": "minecraft:item"})
    weights = [e.get("weight") for e in t["pools"][1]["entries"]]
    assert weights[0] / sum(weights) == pytest.approx(chest_loot.STORY_MAP)
    c = chest_loot.with_story({"pools": [{"rolls": 1}]}, "x")
    assert c["pools"][-1]["entries"][0]["value"] == "heraldia:historia/x" and "solo_sin_lootr" not in c["pools"][-1]


def test_story_lang():
    lang = chest_loot.story_lang([("a", mod())])
    assert lang["es_es"]["heraldia.historia.a.pagina1"] == "Uno." and lang["en_us"]["heraldia.historia.a.pista"] == "to the north"
    assert set(lang["es_es"]) == set(lang["en_us"])
