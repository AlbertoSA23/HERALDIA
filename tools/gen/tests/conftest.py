"""Pruebas unitarias del generador (pytest). Rápidas y sin generar el datapack: cada prueba construye piezas pequeñas.

Ejecutar: python3 -m pytest tools/gen/tests -q   (o ./gradlew testGen, que va dentro de check)
"""
import os, sys

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if GEN not in sys.path:
    sys.path.insert(0, GEN)

import pytest  # noqa: E402
from core import Template  # noqa: E402


def template(blocks, name="prueba", jigsaws=()):
    """Template a partir de {pos: estado} (sin normalizar) y jigsaws [(pos, orientación, nombre)]."""
    t = Template(name)
    for p, st in blocks.items():
        t.set(*p, st)
    for pos, ori, jname in jigsaws:
        t.jigsaw(*pos, ori, jname, "minecraft:empty", "minecraft:empty", final_state="minecraft:air")
    return t


@pytest.fixture
def tpl():
    return template


def write_json(path, obj):
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


@pytest.fixture
def mcmeta(tmp_path, monkeypatch):
    """Resumen de mcmeta sintético y diminuto (bloques, registros, etiquetas de bioma) cargado en validate, con sus
    registros globales vacíos al empezar (monkeypatch los restaura al terminar)."""
    import validate
    root = tmp_path / "mcmeta"
    write_json(str(root / "blocks" / "data.json"), {
        "stone": [{}, {}], "air": [{}, {}], "dirt": [{}, {}], "chest": [{"facing": ["north", "south", "east", "west"]}, {}],
        "jigsaw": [{"orientation": ["north_up", "south_up"]}, {}],
        "oak_stairs": [{"facing": ["north", "south", "east", "west"], "half": ["top", "bottom"]}, {}]})
    write_json(str(root / "registries" / "data.json"), {
        "item": ["stone", "bread", "iron_axe", "filled_map", "written_book", "compass"], "entity_type": ["zombie", "cat", "hoglin", "villager", "skeleton", "evoker", "guardian"],
        "trigger_type": ["location", "inventory_changed", "player_killed_entity"],
        "entity_sub_predicate_type": ["entity_type", "entity_tags"], "enchantment": ["sharpness", "efficiency"],
        "trim_pattern": ["coast"], "trim_material": ["gold"], "banner_pattern": ["stripe_top"],
        "worldgen/biome": ["plains", "sunflower_plains", "forest", "desert"]})
    write_json(str(root / "data" / "tag" / "worldgen" / "biome" / "data.json"), {
        "is_forest": {"values": ["minecraft:forest"]}, "is_overworld": {"values": ["#minecraft:is_forest", "minecraft:plains"]}})
    for name in ("BLOCKS",):
        monkeypatch.setattr(validate, name, {})
    for name in ("ITEMS", "ENTITIES", "TRIGGERS", "ENTITY_PREDICATES"):
        monkeypatch.setattr(validate, name, set())
    monkeypatch.setattr(validate, "DATA", {k: set() for k in validate.DATA})
    validate.load_registries(str(root))
    return root
