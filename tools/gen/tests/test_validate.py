"""validate.py: casos negativos contra un resumen de registros sintético (fixture mcmeta)."""
import json, os
import pytest
import validate
from core import Template, ADULTO_TAG, ANCLADO_TAG
from unicas._comun import piezas


class Reg:
    def __init__(self, *templates, pools=None):
        self.templates = {t.name: t for t in templates}
        self.pools = pools or {}


def test_load_registries_falla_claro(tmp_path):
    with pytest.raises(SystemExit, match="No encuentro"):
        validate.load_registries(str(tmp_path))


def test_check_state(mcmeta):
    assert validate.check_state("minecraft:stone") is None
    assert validate.check_state("oak_stairs[facing=east,half=top]") is None
    assert "inexistente" in validate.check_state("minecraft:stone_brickz")
    assert "propiedad" in validate.check_state("stone[lit=true]")
    assert "valor" in validate.check_state("oak_stairs[facing=up]")


def test_validate_registry_negativos(mcmeta):
    t = Template("a")
    t.set(0, 0, 0, "stone_brickz")
    t.jigsaw(1, 0, 0, "north_up", "heraldia:x", "heraldia:x", "heraldia:no_existe", final_state="minecraft:glowstonez")
    t.entity(0, 1, 0, {"id": "minecraft:zombie"})                    # sin heraldia_adulto
    t.entity(0, 1, 0, {"id": "minecraft:hoglin"})                    # sin protección contra bebés
    t.entity(0, 1, 0, {"id": "minecraft:dragonz"})
    reg = Reg(t, pools={"heraldia:p": {"fallback": "heraldia:q", "elements": [("heraldia:no", 1, "rigid", None)]}})
    errs = " | ".join(validate.validate_registry(reg))
    for msg in ("bloque inexistente: minecraft:stone_brickz", "final_state bloque inexistente",
                "pool inexistente heraldia:no_existe", f"sin la etiqueta {ADULTO_TAG}", "hoglin en una plantilla",
                "entidad minecraft:dragonz", "fallback inexistente heraldia:q", "plantilla inexistente heraldia:no"):
        assert msg in errs, msg


def test_validate_registry_limpio(mcmeta):
    t = Template("a")
    t.set(0, 0, 0, "stone")
    t.entity(0, 1, 0, {"id": "minecraft:zombie", "Tags": [ADULTO_TAG, ANCLADO_TAG]})
    t.entity(0, 1, 0, piezas.guardian("evoker", "k", "f", 40))
    t.entity(0, 1, 0, {"id": "minecraft:villager"})                  # los aldeanos recogen cosechas: sin anclar
    t.entity(0, 1, 0, {"id": "minecraft:guardian"})                  # los peces guardianes de la Atlántida tampoco
    assert validate.validate_registry(Reg(t)) == {}


@pytest.mark.parametrize("nbt, por", [
    ({"id": "minecraft:zombie", "Tags": [ADULTO_TAG]}, "recogería objetos"),            # zombi sin anclar
    ({"id": "minecraft:skeleton"}, "recogería objetos"),                                 # esqueleto sin anclar
    ({"id": "minecraft:evoker", "Tags": [piezas.GUARDIAN_TAG]}, "guardián"),             # guardián sin anclar
])
def test_validate_registry_sin_anclar(mcmeta, nbt, por):
    t = Template("a")
    t.entity(0, 1, 0, nbt)
    errs = validate.validate_registry(Reg(t))
    assert list(errs) == [f"{nbt['id']} sin la etiqueta {ANCLADO_TAG} ({por}: core.anclado)"]
    assert errs[next(iter(errs))] == ["a"]


def test_validate_loot(mcmeta):
    tablas = {"x": {"pools": [{"entries": [
        {"type": "minecraft:item", "name": "minecraft:breadz"},
        {"type": "minecraft:item", "name": "minecraft:bread",
         "modifier": [{"type": "minecraft:set_enchantments", "enchantments": {"minecraft:sharpnezz": 1}},
                      {"type": "minecraft:set_components", "components": {
                          "minecraft:trim": {"pattern": "minecraft:coastz", "material": "minecraft:gold"},
                          "minecraft:banner_patterns": [{"pattern": "minecraft:stripe_top"}, {"pattern": "x"}]}}]}]}]}}
    errs = validate.validate_loot([tablas])
    assert errs == ["objeto inexistente breadz", "encantamiento inexistente minecraft:sharpnezz",
                    "trim_pattern inexistente minecraft:coastz", "banner_pattern inexistente x"]


def _estructura(out, name, s):
    p = os.path.join(out, "data", "heraldia", "worldgen", "structure", name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(s, f)


def test_validate_structures(tmp_path):
    out = str(tmp_path)
    _estructura(out, "a.json", {"type": "minecraft:jigsaw", "max_distance_from_center": 117, "size": 7})
    _estructura(out, "unicas/b.json", {"type": "minecraft:jigsaw", "max_distance_from_center": 80, "size": 21})
    _estructura(out, "c.json", {"type": "heraldia:aldea", "aldea": {"max_distance_from_center": 116, "size": 0}})
    _estructura(out, "d.json", {"type": "heraldia:isla"})
    errs = validate.validate_structures(out)
    assert len(errs) == 3
    assert any("a.json" in e and "117" in e for e in errs) and any("b.json" in e and "size 21" in e for e in errs)
    assert any("(aldea)" in e and "size 0" in e for e in errs)


def _logro(out, path, a, langs=None):
    p = os.path.join(out, "data", "heraldia", "advancement", path + ".json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(a, f)
    for lang in ("es_es", "en_us"):
        q = os.path.join(out, "assets", "heraldia", "lang", f"{lang}.json")
        os.makedirs(os.path.dirname(q), exist_ok=True)
        with open(q, "w") as f:
            json.dump(langs or {"k.t": "t", "k.d": "d"}, f)


def test_validate_advancements_bueno_y_malos(mcmeta, tmp_path):
    out = str(tmp_path / "out")
    disp = {"icon": {"id": "minecraft:stone"}, "title": {"translate": "k.t"}, "description": {"translate": "k.d"},
            "background": "x"}
    _logro(out, "raiz", {"criteria": {"a": {"trigger": "minecraft:location"}}, "display": disp})
    assert validate.validate_advancements(out) == []
    _logro(out, "malo", {"parent": "heraldia:no", "criteria": {"a": {"trigger": "minecraft:volar"},
                                                               "b": {"trigger": "minecraft:location", "conditions": {
                                                                   "player": {"predicate": {"minecraft:raro": {}}},
                                                                   "loot_tables": "heraldia:no_existe"}}},
                         "requirements": [["a"]], "rewards": {"loot": ["heraldia:x"]}, "extra": 1,
                         "display": dict(disp, icon={"id": "minecraft:nada"}, frame="épico",
                                         title={"translate": "falta"}, description={"text": "sin clave"})})
    errs = " | ".join(validate.validate_advancements(out))
    for msg in ("campos desconocidos ['extra']", "disparador desconocido minecraft:volar", "no cubren exactamente",
                "padre inexistente heraldia:no", "icono inexistente", "marco épico", "falta la clave falta",
                "texto sin clave de traducción", "recompensa no permitida", "predicado de entidad desconocido minecraft:raro",
                "tabla de botín inexistente heraldia:no_existe"):
        assert msg in errs, msg
