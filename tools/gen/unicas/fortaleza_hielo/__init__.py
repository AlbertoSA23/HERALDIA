"""Fortaleza de hielo: estructura única diseñada a mano (ver docs/unicas/fortaleza_hielo.md)."""
from . import construir, auditoria, botin

STRUCTURE = dict(
    biomes=["minecraft:ice_spikes", "minecraft:snowy_plains", "minecraft:snowy_taiga"],
    start_pool="unicas/fortaleza_hielo/inicio",
    size=1, max_distance=48,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
LOOT = botin.LOOT
LANG = botin.LANG

# Degradación: ladrillo agrietado, almenas bajas caídas y losas de diorita gastadas (el hielo no se toca: un parche de
# bloque de nieve en una cima haría nacer picos de hielo encima).
PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + b, "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + o}
    for b, p, o in (("stone_bricks", 0.2, "cracked_stone_bricks"), ("stone_brick_wall", 0.3, "air"),
                    ("polished_diorite", 0.2, "diorite"))]}]}
assert {r["input_predicate"]["block"][10:]: r["input_predicate"]["probability"]
        for r in PROCESSORS["processors"][0]["rules"]} == auditoria.DECAY

REPORT = {}


def audit(t):
    """Errores de las comprobaciones propias (vacío = todo bien). Rellena REPORT para los planos."""
    errs = auditoria.check_redstone(t)
    lerr, lvl = auditoria.check_light(t)
    errs += lerr
    view, moved = auditoria.opened(t)
    if len(moved) != 4:
        errs.append(("puertas secretas: se esperaban 4 bloques retraídos", tuple(moved)))
    surf, damaged = auditoria.condition(t, construir.RUIN)
    if not 0.15 <= damaged <= 0.20:
        errs.append((f"superficie dañada {damaged:.1%} fuera de 15-20 %", None))
    REPORT.update(view=view, light=lvl, surface=surf, damaged=damaged, moved=moved)
    return errs


def build(reg):
    t = construir.build_template()
    name = reg.add(t, "unica")
    t.lint_view, _ = auditoria.opened(t)            # lint recorre la fortaleza con las puertas secretas abiertas
    for msg, pos in audit(t):
        reg.warnings.append(f"{name}: {msg} {pos}")
    reg.pool("unicas/fortaleza_hielo/inicio", [(name, 1, "rigid", PROCESSORS)])

NOMBRE = {"es_es": "Fortaleza de hielo", "en_us": "Ice Fortress"}
LOGRO = {"icono": "minecraft:blue_ice"}   # logros.py
MAPA = {"decoration": "minecraft:red_x"}
