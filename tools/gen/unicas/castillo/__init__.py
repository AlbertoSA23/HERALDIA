"""Castillo: fortaleza medieval de 100 x 100 en llanuras y praderas, con mazmorra bajo la torre del homenaje.
Diseño completo en docs/unicas/castillo.md."""
from . import superficie, mazmorra, auditoria
from .botin import LOOT, NAMES

STRUCTURE = dict(
    biomes=["minecraft:plains", "minecraft:sunflower_plains", "minecraft:meadow"],
    start_pool="unicas/castillo/inicio", size=3, max_distance=80, terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": -(superficie.G + 1)}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190)
NOMBRE = {"es_es": "Castillo", "en_us": "Castle"}
LOGRO = {"icono": "minecraft:stone_bricks"}   # logros.py
TEXTOS = {"heraldia.castillo.guardian": ("Sir Aldric, el Castellano Maldito", "Sir Aldric, the Cursed Castellan")}
TEXTOS.update(NAMES)
LANG = {"es_es": {k: v[0] for k, v in TEXTOS.items()}, "en_us": {k: v[1] for k, v in TEXTOS.items()}}


def _rule(block, out, p):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block,
                                "probability": p},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


# Degradación: musgo y grietas (detalles de ruina repartidos); la ruina mayor está colocada a mano.
PROC = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    _rule("stone_bricks", "mossy_stone_bricks", 0.15), _rule("stone_bricks", "cracked_stone_bricks", 0.1),
    _rule("cobblestone", "mossy_cobblestone", 0.2)]}]}

LAST = {}


def build(reg):
    t, cmeta = superficie.build()
    d, dmeta = mazmorra.build(cmeta.pop("below"))
    reg.add(t, "unica")
    reg.add(d, "unica")
    reg.pool("unicas/castillo/inicio", [(t.name, 1, "rigid", PROC)])
    reg.pool("unicas/castillo/mazmorra", [(d.name, 1, "rigid", PROC)])
    errs, res = auditoria.audit(t, d, cmeta, dmeta)
    reg.warnings += [f"castillo: {e}" for e in errs]
    LAST.update(t=t, d=d, cmeta=cmeta, dmeta=dmeta, res=res)
