"""_comun/botin.py: tables, named items, trophies (TROFEO contract) and books."""
import pytest
from uniques._common import chest_loot


def test_pool_table_chest():
    p = chest_loot.pool((1, 3), [chest_loot.item("bread", 1)], extra=True)
    assert p["rolls"] == {"type": "minecraft:uniform", "min": 1, "max": 3} and p["solo_sin_lootr"]
    assert "solo_sin_lootr" not in chest_loot.pool(2, [])
    t = chest_loot.place_chest((1, [chest_loot.empty(1)]), (2, [chest_loot.empty(1)]))
    assert t["type"] == "minecraft:chest" and [bool(q.get("solo_sin_lootr")) for q in t["pools"]] == [False, True]


def test_named_with_amount_and_enchantments():
    e = chest_loot.named("iron_sword", 3, "k", "Espada", ench={"minecraft:sharpness": 2}, lo=1, hi=2)
    kinds = [m["type"] for m in e["modifier"]]
    assert kinds == ["minecraft:set_count", "minecraft:set_name", "minecraft:set_enchantments"]
    assert e["modifier"][1]["target"] == "item_name" and e["weight"] == 3


def test_book_potion_lang():
    assert chest_loot.book(1, {"minecraft:mending": 1})["modifier"]["type"] == "minecraft:set_enchantments"
    p = chest_loot.potion("healing", 2)
    assert p["modifier"] == {"type": "minecraft:set_potion", "id": "minecraft:healing"}
    p = chest_loot.potion("healing", 2, key="k", fallback="f")
    assert [m["type"] for m in p["modifier"]] == ["minecraft:set_name", "minecraft:set_potion"]
    assert chest_loot.lang("a.", {"x": ("es", "en")}) == {"es_es": {"a.x": "es"}, "en_us": {"a.x": "en"}}


TROPHY = {"objeto": "iron_axe", "nombre": ("Hacha", "Axe"), "lore": [("l", "l")], "rareza": "rare",
          "encantamientos": {"minecraft:efficiency": 2}}


def test_trophy_valid():
    assert chest_loot.trophy_errors("x", TROPHY) == []
    t = chest_loot.trophy("x", TROPHY)
    mods = t["pools"][0]["entries"][0]["modifier"]
    comps = mods[1]["components"]
    assert comps["minecraft:custom_data"] == {chest_loot.TROPHY_MARK: "x"} and comps["minecraft:max_stack_size"] == 1
    assert "minecraft:enchantment_glint_override" not in comps          # already glows from the enchantment
    sin = chest_loot.trophy("x", dict(TROPHY, encantamientos=None))
    assert sin["pools"][0]["entries"][0]["modifier"][1]["components"]["minecraft:enchantment_glint_override"]
    assert chest_loot.trophy_predicate("x", TROPHY)["items"] == "minecraft:iron_axe"


@pytest.mark.parametrize("change, msg", [
    (dict(objeto="netherite_sword"), "objeto de trofeo no válido"),
    (dict(objeto="elytra"), "objeto de trofeo no válido"),
    (dict(nombre=("solo",)), "TROFEO.nombre"),
    (dict(lore=[]), "TROFEO.lore"),
    (dict(lore=[("a", "b")] * 3), "TROFEO.lore"),
    (dict(rareza="legendaria"), "rareza"),
    (dict(encantamientos={"minecraft:sharpness": 5}), "fuera de 1..3"),
    (dict(componentes={"minecraft:base_color": "red"}), "TROFEO.componentes"),
    (dict(componentes={"minecraft:custom_data": {}}), "TROFEO.componentes"),
])
def test_trophy_negative_cases(change, msg):
    errs = chest_loot.trophy_errors("x", dict(TROPHY, **change))
    assert any(msg in e for e in errs), errs


def test_trophy_absent():
    assert "falta TROFEO" in chest_loot.trophy_errors("x", None)[0]


def test_guardian_trophy_table_only_with_player():
    t = chest_loot.guardian_table("x", "minecraft:entities/zombie")
    assert t["pools"][0]["entries"][0]["value"] == "minecraft:entities/zombie"
    assert t["pools"][1]["condition"] == {"type": "minecraft:killed_by_player"}
    assert chest_loot.guardian_table_id("x", "minecraft:zombie") == "heraldia:guardianes/x/zombie"
    lang = chest_loot.trophy_lang("x", TROPHY)
    assert lang["es_es"]["heraldia.trofeo.x"] == "Hacha" and "heraldia.trofeo.x.lore1" in lang["en_us"]


def test_book_title_and_names():
    e = chest_loot.written_book([{"text": "p"}], {"translate": "k", "fallback": "f"}, "Título", "Autor", lore=[{"text": "l"}])
    c = e["modifier"][0]["components"]
    assert c["minecraft:custom_name"]["italic"] is False and c["minecraft:item_name"] == {"translate": "k", "fallback": "f"}
    assert c["minecraft:written_book_content"]["pages"] == [{"raw": {"text": "p"}}]
    with pytest.raises(ValueError):
        chest_loot.written_book([], {"text": "n"}, "x" * 33, "a")


def test_book_lines():
    assert chest_loot.book_lines("hola") == 1
    assert chest_loot.book_lines("a\nb\n\nc") == 4
    # 114 px per line: "mmmm" takes 24 px and the space 4, so 4 words fit (108 px) and the fifth wraps
    assert chest_loot.book_lines(" ".join(["mmmm"] * 4)) == 1
    assert chest_loot.book_lines(" ".join(["mmmm"] * 5)) == 2
    assert chest_loot.book_lines(" ".join(["mmmm"] * 10)) == 3
    assert chest_loot.width("á") == chest_loot.width("a") == 6 and chest_loot.width("i") == 2
