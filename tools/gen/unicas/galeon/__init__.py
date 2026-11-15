"""Galeón varado: galeón de tres palos encallado en la playa, campamento de náufragos y cueva del tesoro.

Una sola plantilla (barco + campamento + peñón) colocada por el tipo propio heraldia:galeon, que busca la orilla
en Java (el jigsaw no ve el agua). Diseño: docs/unicas/galeon.md.
"""
from .._comun.piezas import open_stairwells
from core import Template
from .comun import Obra, ANCHOR, ZMIN
from . import barco, tierra
from .auditoria import auditar
from .botin import LOOT
from .textos import LANG

NAME = "unicas/galeon/galeon"
NOMBRE = {"es_es": "Galeón varado", "en_us": "Stranded Galleon"}
LOGRO = {"icono": "minecraft:oak_boat"}   # logros.py
STRUCTURE = dict(spacing=250, separation=190)
PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:dark_oak_planks", "probability": 0.10},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:air"},
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:cobblestone", "probability": 0.2},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_cobblestone"},
]}]}
# Sondas para Java (dx, dz respecto al ancla, en múltiplos de 8; intervalo de la altura del fondo respecto al mar).
PROBES = ([dict(dx=8, dz=dz, min=-9, max=-2, required=True) for dz in (-24, -8, 8, 24)] +
          [dict(dx=-8, dz=dz, min=-3, max=3, required=True) for dz in (-24, -8, 8, 24)] +
          [dict(dx=16, dz=dz, min=-30, max=-2, required=True) for dz in (-16, 16)] +
          [dict(dx=24, dz=dz, min=-40, max=-2, required=False) for dz in (-24, 0, 24)] +
          [dict(dx=dx, dz=dz, min=0, max=4, required=False) for dx in (-16, -32) for dz in (-24, 0, 24)] +
          [dict(dx=dx, dz=dz, min=0, max=12, required=False) for dx in (-48, -56) for dz in (-8, 16, 32)])


def construir():
    t = Template(NAME)
    o = Obra(t)
    o.langs = LANG["es_es"]
    tierra.suelo(o)
    barco.construir(o)
    tierra.campamento(o)
    tierra.cueva(o)
    conexiones(o)
    t.jigsaw(40, 0, ZMIN, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="minecraft:sand")
    return o


def conexiones(o):
    """Vallas y cristales unidos entre sí y a bloques macizos (al generarse no hay actualizaciones que lo hagan)."""
    from lint import top_height, bname
    from .comun import DIRV
    for (x, y, z), (st, nbt) in list(o.t.blocks.items()):
        b = bname(st)
        if not (b.endswith("_fence") or b.endswith("_pane")):
            continue
        props = {}
        for d, (dx, dz) in DIRV.items():
            n = o.t.get(x + dx, y, z + dz)
            nb = bname(n)
            ok = n is not None and (nb == b or (nb.endswith("_fence") and b.endswith("_fence")) or
                                    (top_height(n) == 1.0 and not nb.endswith(("_stairs", "_slab", "_trapdoor"))
                                     and "lantern" not in nb and nb not in ("chest", "barrel", "bookshelf") or nb == "bookshelf"))
            props[d] = "true" if ok else "false"
        o.t.set(x, y, z, b + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + ",waterlogged=false]")


def shift(p, d):
    return (p[0] - d[0], p[1] - d[1], p[2] - d[2])


def build(reg):
    o = construir()
    d = o.t.bounds()[:3]
    open_stairwells(o.t)   # huecos de escalera cortos
    reg.add(o.t, "unica")                       # normaliza a coordenadas >= 0
    o.t.lint_open = {shift(p, d): v for p, v in o.t.lint_open.items()}
    o.ruina = {shift(p, d) for p in o.ruina}
    o.superficie = {shift(p, d) for p in o.superficie}
    o.circuitos = [(n, [(k, shift(p, d)) for k, p in a], [(k, shift(p, d)) for k, p in e]) for n, a, e in o.circuitos]
    sea = -d[1]
    reg.warnings += [f"galeon: {e}" for e in auditar(o, sea)[:20]]
    reg.pool("unicas/galeon/inicio", [(NAME, 1, "rigid", PROCESSORS)])
    anchor = list(shift(ANCHOR, d))
    STRUCTURE["json"] = {
        "type": "heraldia:galeon", "biomes": ["minecraft:beach", "minecraft:snowy_beach"], "step": "surface_structures",
        "spawn_overrides": {}, "terrain_adaptation": "none", "start_pool": "heraldia:unicas/galeon/inicio",
        "anchor": anchor, "probes": sorted(PROBES, key=lambda p: not p["required"]), "max_misses": 3, "search_radius": 56}
    build.obra = o
    return o
