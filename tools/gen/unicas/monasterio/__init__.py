"""Monasterio de montaña: una sola plantilla rígida con su propio risco, terrazas, iglesia y cuevas (ver docs/unicas/monasterio.md)."""
from .._comun.piezas import open_stairwells
from . import obra, auditoria
from .botin import LOOT, LANG_ITEMS
from .._comun.botin import lang

ID = obra.ID
STRUCTURE = dict(
    biomes=["minecraft:meadow", "minecraft:grove"],
    start_pool=f"unicas/{ID}/inicio",
    size=1, max_distance=64,
    terrain_adaptation="none",
    step="surface_structures", start_height={"absolute": -25}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
NOMBRE = {"es_es": "Monasterio de montaña", "en_us": "Mountain Monastery"}
LOGRO = {"icono": "minecraft:writable_book"}   # logros.py

_TEXTS = {
    "cripta.1": ("Apagad las luces", "Put out the lights"), "cripta.2": ("de los difuntos", "of the departed"),
    "cripta.3": ("y la lápida", "and the tombstone"), "cripta.4": ("se apartará.", "will move aside."),
    "osario.1": ("Velan el primero", "The first one wakes"), "osario.2": ("y el último;", "and so the last;"),
    "osario.3": ("el del medio", "the one between"), "osario.4": ("duerme.", "sleeps."),
    "guardian": ("Fray Tenebrio, guardián del relicario", "Brother Tenebrio, Warden of the Reliquary"),
}
_TEXTS.update(LANG_ITEMS)
LANG = lang(f"heraldia.unicas.{ID}.", _TEXTS)

# Procesador de envejecimiento (solo cosmético: no abre huecos ni quita apoyos)
AGING = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{out}"}
    for out, p in (("cracked_stone_bricks", 0.08), ("mossy_stone_bricks", 0.087))] + [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:cobblestone", "probability": 0.15},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_cobblestone"}]}]}


def build(reg):
    t = obra.construir()
    errores = auditoria.comprobar(t)
    reg.warnings.extend(f"monasterio: {e}" for e in errores)
    open_stairwells(t)   # huecos de escalera cortos
    name = reg.add(t, f"unica:{ID}")
    reg.templates[name].lint_open = dict(t.abiertos)          # convención común de lint.py: puertas secretas abiertas
    reg.pool(f"unicas/{ID}/inicio", [(name, 1, "rigid", AGING)])
