"""Estructura única «Palacio oriental» (heraldia:unicas/palacio). Diseño: docs/unicas/palacio.md."""
import copy
from core import nsid
from .plano import construir, W, D, NAME
from .ruinas import arruinar, processors
from . import auditoria
from .botin import LOOT, LANG

STRUCTURE = dict(
    biomes=["minecraft:cherry_grove", "minecraft:bamboo_jungle"],
    start_pool="unicas/palacio/inicio",
    size=1, max_distance=80,
    terrain_adaptation="beard_box",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
NOMBRE = {"es_es": "Palacio oriental", "en_us": "Eastern Palace"}


def fill_air(t):
    """Aire explícito en todo el volumen de la pieza (y >= 1) para que el terreno no asome en patios y salas."""
    x0, y0, z0, x1, y1, z1 = t.bounds()
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(1, y1 + 1):
                if (x, y, z) not in t.blocks:
                    t.blocks[(x, y, z)] = ("minecraft:air", None)


def palacio():
    """Construye la pieza, la arruina y la audita. Devuelve (obra, plantilla en buen estado, errores)."""
    o = construir()
    good = copy.deepcopy(o.t)
    arruinar(o)
    fill_air(o.t)
    # el acceso para la auditoría de recorrido: escalón central de la escalinata
    o.t.jigsaw(40, 0, 0, "north_up", "heraldia:entrance", "heraldia:entrance", "minecraft:empty",
               final_state=o.t.get(40, 0, 0))
    o.t.lint_open = o.lint_open
    from pack import fix_supports
    fix_supports(o.t)
    errs = auditoria.check_redstone(o) + auditoria.check_floating(o) + auditoria.check_ruin(good, o.t)
    werrs, _ = auditoria.check_walk(o)
    return o, good, errs + werrs


def build(reg):
    o, _, errs = palacio()
    reg.warnings += [f"palacio: {e}" for e in errs]
    name = reg.add(o.t, "unica")
    reg.pool("unicas/palacio/inicio", [(name, 1, "rigid", processors())])
