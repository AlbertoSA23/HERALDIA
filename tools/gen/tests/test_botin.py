"""_comun/botin.py: tablas, objetos con nombre, trofeos (contrato TROFEO) y libros."""
import pytest
from unicas._comun import botin


def test_pool_table_cofre():
    p = botin.pool((1, 3), [botin.item("bread", 1)], extra=True)
    assert p["rolls"] == {"type": "minecraft:uniform", "min": 1, "max": 3} and p["solo_sin_lootr"]
    assert "solo_sin_lootr" not in botin.pool(2, [])
    t = botin.cofre((1, [botin.empty(1)]), (2, [botin.empty(1)]))
    assert t["type"] == "minecraft:chest" and [bool(q.get("solo_sin_lootr")) for q in t["pools"]] == [False, True]


def test_named_con_cantidad_y_encantamientos():
    e = botin.named("iron_sword", 3, "k", "Espada", ench={"minecraft:sharpness": 2}, lo=1, hi=2)
    tipos = [m["type"] for m in e["modifier"]]
    assert tipos == ["minecraft:set_count", "minecraft:set_name", "minecraft:set_enchantments"]
    assert e["modifier"][1]["target"] == "item_name" and e["weight"] == 3


def test_book_potion_lang():
    assert botin.book(1, {"minecraft:mending": 1})["modifier"]["type"] == "minecraft:set_enchantments"
    p = botin.potion("healing", 2)
    assert p["modifier"] == {"type": "minecraft:set_potion", "id": "minecraft:healing"}
    p = botin.potion("healing", 2, key="k", fallback="f")
    assert [m["type"] for m in p["modifier"]] == ["minecraft:set_name", "minecraft:set_potion"]
    assert botin.lang("a.", {"x": ("es", "en")}) == {"es_es": {"a.x": "es"}, "en_us": {"a.x": "en"}}


TROFEO = {"objeto": "iron_axe", "nombre": ("Hacha", "Axe"), "lore": [("l", "l")], "rareza": "rare",
          "encantamientos": {"minecraft:efficiency": 2}}


def test_trofeo_valido():
    assert botin.trofeo_errores("x", TROFEO) == []
    t = botin.trofeo("x", TROFEO)
    mods = t["pools"][0]["entries"][0]["modifier"]
    comps = mods[1]["components"]
    assert comps["minecraft:custom_data"] == {botin.TROFEO_MARCA: "x"} and comps["minecraft:max_stack_size"] == 1
    assert "minecraft:enchantment_glint_override" not in comps          # ya brilla por el encantamiento
    sin = botin.trofeo("x", dict(TROFEO, encantamientos=None))
    assert sin["pools"][0]["entries"][0]["modifier"][1]["components"]["minecraft:enchantment_glint_override"]
    assert botin.trofeo_predicado("x", TROFEO)["items"] == "minecraft:iron_axe"


@pytest.mark.parametrize("cambio, msg", [
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
def test_trofeo_casos_negativos(cambio, msg):
    errs = botin.trofeo_errores("x", dict(TROFEO, **cambio))
    assert any(msg in e for e in errs), errs


def test_trofeo_ausente():
    assert "falta TROFEO" in botin.trofeo_errores("x", None)[0]


def test_guardian_tabla_trofeo_solo_con_jugador():
    t = botin.guardian_tabla("x", "minecraft:entities/zombie")
    assert t["pools"][0]["entries"][0]["value"] == "minecraft:entities/zombie"
    assert t["pools"][1]["condition"] == {"type": "minecraft:killed_by_player"}
    assert botin.guardian_tabla_id("x", "minecraft:zombie") == "heraldia:guardianes/x/zombie"
    lang = botin.trofeo_lang("x", TROFEO)
    assert lang["es_es"]["heraldia.trofeo.x"] == "Hacha" and "heraldia.trofeo.x.lore1" in lang["en_us"]


def test_libro_titulo_y_nombres():
    e = botin.libro([{"text": "p"}], {"translate": "k", "fallback": "f"}, "Título", "Autor", lore=[{"text": "l"}])
    c = e["modifier"][0]["components"]
    assert c["minecraft:custom_name"]["italic"] is False and c["minecraft:item_name"] == {"translate": "k", "fallback": "f"}
    assert c["minecraft:written_book_content"]["pages"] == [{"raw": {"text": "p"}}]
    with pytest.raises(ValueError):
        botin.libro([], {"text": "n"}, "x" * 33, "a")


def test_lineas_libro():
    assert botin.lineas_libro("hola") == 1
    assert botin.lineas_libro("a\nb\n\nc") == 4
    # 114 px por línea: «mmmm» ocupa 24 px y el espacio 4, así que caben 4 palabras (108 px) y la quinta salta
    assert botin.lineas_libro(" ".join(["mmmm"] * 4)) == 1
    assert botin.lineas_libro(" ".join(["mmmm"] * 5)) == 2
    assert botin.lineas_libro(" ".join(["mmmm"] * 10)) == 3
    assert botin.ancho("á") == botin.ancho("a") == 6 and botin.ancho("i") == 2
