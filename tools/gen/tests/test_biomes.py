"""biomas.py: biome tags and their check against vanilla (synthetic summary)."""
import json, os
import pytest
import biomes
from conftest import write_json


@pytest.fixture
def clean(monkeypatch, tmp_path):
    monkeypatch.setattr(biomes, "_WRITTEN", {})
    monkeypatch.setattr(biomes, "CONVENTIONAL", {})
    return str(tmp_path / "out")


def structure(out, sid, biome_list):
    write_json(os.path.join(out, "data", "heraldia", "worldgen", "structure", f"{sid}.json"), {"biomes": biome_list})


def test_tag_and_of_unique(clean, monkeypatch):
    monkeypatch.setitem(biomes.CONVENTIONAL, "llanuras", ["c:is_plains"])
    assert biomes.tag(clean, "llanuras", ["plains", "minecraft:sunflower_plains"]) == "#heraldia:llanuras"
    with open(os.path.join(clean, "data", "heraldia", "tags", "worldgen", "biome", "llanuras.json")) as f:
        v = json.load(f)["values"]
    assert v == ["minecraft:plains", "minecraft:sunflower_plains", {"id": "#c:is_plains", "required": False}]
    assert biomes.for_unique(clean, "x", ["forest"]) == "#heraldia:unicas/x"
    assert biomes.for_unique(clean, "y", "#heraldia:llanuras") == "#heraldia:llanuras"      # a tag is left as it is


def test_check_good(clean, mcmeta):
    structure(clean, "a", biomes.tag(clean, "bosque", ["forest"]))
    assert biomes.check(clean, str(mcmeta)) == []


def test_check_conventional_that_adds_of_more(clean, mcmeta, monkeypatch):
    # #minecraft:is_overworld puts plains in a tag that in vanilla only has forest
    monkeypatch.setitem(biomes.CONVENTIONAL, "bosque", ["minecraft:is_overworld"])
    structure(clean, "a", biomes.tag(clean, "bosque", ["forest"]))
    errs = biomes.check(clean, str(mcmeta))
    assert any("#heraldia:bosque en vanilla" in e for e in errs)


def test_check_negatives(clean, mcmeta, monkeypatch):
    monkeypatch.setitem(biomes.CONVENTIONAL, "rara", ["c:no_existe_nunca"])
    biomes.tag(clean, "rara", ["forest"])
    biomes.tag(clean, "falsa", ["minecraft:bioma_falso"])
    structure(clean, "lista", ["minecraft:forest"])                     # without a Heraldia tag
    errs = " | ".join(biomes.check(clean, str(mcmeta)))
    assert "c:no_existe_nunca no existe" in errs and "bioma inexistente minecraft:bioma_falso" in errs
    assert "is not a Heraldia tag" in errs


def test_required_false_mandatory(clean, mcmeta):
    biomes.tag(clean, "bosque", ["forest"])
    p = os.path.join(clean, "data", "heraldia", "tags", "worldgen", "biome", "bosque.json")
    write_json(p, {"values": ["minecraft:forest", {"id": "#minecraft:is_forest"}]})
    assert any("required: false" in e for e in biomes.check(clean, str(mcmeta)))


def test_conventional_real_resolve():
    """The repository's CONVENCIONALES cite tags from the Fabric API copy (etiquetas_c.json) or vanilla."""
    c = biomes.conventional()
    for name, extra in biomes.CONVENTIONAL.items():
        for t in extra:
            assert t.startswith("minecraft:is_") or t[2:] in c, (name, t)
