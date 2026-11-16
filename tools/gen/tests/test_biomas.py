"""biomas.py: etiquetas de biomas y su comprobación contra vanilla (resumen sintético)."""
import json, os
import pytest
import biomas
from conftest import escribir_json


@pytest.fixture
def limpio(monkeypatch, tmp_path):
    monkeypatch.setattr(biomas, "_ESCRITAS", {})
    monkeypatch.setattr(biomas, "CONVENCIONALES", {})
    return str(tmp_path / "out")


def estructura(out, sid, biomes):
    escribir_json(os.path.join(out, "data", "heraldia", "worldgen", "structure", f"{sid}.json"), {"biomes": biomes})


def test_etiqueta_y_de_unica(limpio, monkeypatch):
    monkeypatch.setitem(biomas.CONVENCIONALES, "llanuras", ["c:is_plains"])
    assert biomas.etiqueta(limpio, "llanuras", ["plains", "minecraft:sunflower_plains"]) == "#heraldia:llanuras"
    with open(os.path.join(limpio, "data", "heraldia", "tags", "worldgen", "biome", "llanuras.json")) as f:
        v = json.load(f)["values"]
    assert v == ["minecraft:plains", "minecraft:sunflower_plains", {"id": "#c:is_plains", "required": False}]
    assert biomas.de_unica(limpio, "x", ["forest"]) == "#heraldia:unicas/x"
    assert biomas.de_unica(limpio, "y", "#heraldia:llanuras") == "#heraldia:llanuras"      # una etiqueta se deja igual


def test_comprobar_bueno(limpio, mcmeta):
    estructura(limpio, "a", biomas.etiqueta(limpio, "bosque", ["forest"]))
    assert biomas.comprobar(limpio, str(mcmeta)) == []


def test_comprobar_convencional_que_mete_de_mas(limpio, mcmeta, monkeypatch):
    # #minecraft:is_overworld mete llanuras en una etiqueta que en vanilla solo tiene bosque
    monkeypatch.setitem(biomas.CONVENCIONALES, "bosque", ["minecraft:is_overworld"])
    estructura(limpio, "a", biomas.etiqueta(limpio, "bosque", ["forest"]))
    errs = biomas.comprobar(limpio, str(mcmeta))
    assert any("#heraldia:bosque en vanilla" in e for e in errs)


def test_comprobar_negativos(limpio, mcmeta, monkeypatch):
    monkeypatch.setitem(biomas.CONVENCIONALES, "rara", ["c:no_existe_nunca"])
    biomas.etiqueta(limpio, "rara", ["forest"])
    biomas.etiqueta(limpio, "falsa", ["minecraft:bioma_falso"])
    estructura(limpio, "lista", ["minecraft:forest"])                     # sin etiqueta de Heraldia
    errs = " | ".join(biomas.comprobar(limpio, str(mcmeta)))
    assert "c:no_existe_nunca no existe" in errs and "bioma inexistente minecraft:bioma_falso" in errs
    assert "no es una etiqueta de Heraldia" in errs


def test_required_false_obligatorio(limpio, mcmeta):
    biomas.etiqueta(limpio, "bosque", ["forest"])
    p = os.path.join(limpio, "data", "heraldia", "tags", "worldgen", "biome", "bosque.json")
    escribir_json(p, {"values": ["minecraft:forest", {"id": "#minecraft:is_forest"}]})
    assert any("required: false" in e for e in biomas.comprobar(limpio, str(mcmeta)))


def test_convencionales_reales_resuelven():
    """Las CONVENCIONALES del repositorio citan etiquetas de la copia de Fabric API (etiquetas_c.json) o vanilla."""
    c = biomas.convencionales()
    for nombre, extra in biomas.CONVENCIONALES.items():
        for t in extra:
            assert t.startswith("minecraft:is_") or t[2:] in c, (nombre, t)
