"""Stranded Galleon: a three-masted galleon run aground on the beach, castaway camp and treasure cave.

A single template (ship + camp + rock) placed by the custom type heraldia:galeon, which looks for the shore
in Java (the jigsaw cannot see water). Design: docs/unicas/galleon.md.
"""
from .._common.pieces import open_stairwells
from core import Template
from .common import Construction, ANCHOR, ZMIN
from . import ship, land
from .audit import audit_it
from .chest_loot import LOOT
from .texts import LANG

NAME = "unicas/galeon/galeon"
DISPLAY_NAME = {"es_es": "Galeón varado", "en_us": "Stranded Galleon"}
TROPHY = {"objeto": "spyglass", "rareza": "uncommon",
          "nombre": ("Catalejo del capitán ahogado", "The Drowned Captain's Spyglass"),
          "lore": [("Aún busca un puerto al que nunca llegó.", "Still searching for a harbour it never reached.")]}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "capitan",
    "relato": [
        ("Embarqué en un galeón para cruzar el mar. Su capitán buscaba un puerto que no salía en ninguna "
         "carta, y yo le prometí que mis mapas lo encontrarían. La tormenta nos lanzó contra una playa.",
         "I boarded a galleon to cross the sea. Its captain sought a harbour that appeared on no chart, "
         "and I promised him my maps would find it. The storm hurled us onto a beach."),
        ("El barco quedó varado en la arena y el capitán se negó a abandonarlo. Guardó el pliego en su "
         "camarote y juró seguir al timón hasta llegar a puerto. Se ahogó con la marea, pero sigue a "
         "bordo.",
         "The ship ran aground on the sand and the captain refused to abandon her. He kept the leaf in "
         "his cabin and swore to stay at the helm until he made port. He drowned with the tide, but he is"
         " still aboard."),
    ],
    "pista": ("una playa, donde un galeón quedó varado con su capitán a bordo",
              "a beach, where a galleon ran aground with her captain still aboard"),
}
ADVANCEMENT = {"icono": "minecraft:oak_boat"}   # advancements.py
STRUCTURE = dict(spacing=250, separation=190)
PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:dark_oak_planks", "probability": 0.10},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:air"},
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:cobblestone", "probability": 0.2},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_cobblestone"},
]}]}
# Probes for Java (dx, dz relative to the anchor, in multiples of 8; range of the floor height relative to the sea).
PROBES = ([dict(dx=8, dz=dz, min=-9, max=-2, required=True) for dz in (-24, -8, 8, 24)] +
          [dict(dx=-8, dz=dz, min=-3, max=3, required=True) for dz in (-24, -8, 8, 24)] +
          [dict(dx=16, dz=dz, min=-30, max=-2, required=True) for dz in (-16, 16)] +
          [dict(dx=24, dz=dz, min=-40, max=-2, required=False) for dz in (-24, 0, 24)] +
          [dict(dx=dx, dz=dz, min=0, max=4, required=False) for dx in (-16, -32) for dz in (-24, 0, 24)] +
          [dict(dx=dx, dz=dz, min=0, max=12, required=False) for dx in (-48, -56) for dz in (-8, 16, 32)])


def construct():
    t = Template(NAME)
    o = Construction(t)
    o.langs = LANG["es_es"]
    land.floor(o)
    ship.construct(o)
    land.camp(o)
    land.cave(o)
    connections(o)
    t.jigsaw(40, 0, ZMIN, "north_up", "heraldia:entrance", "minecraft:empty", "minecraft:empty", final_state="minecraft:sand")
    return o


def connections(o):
    """Fences and glass joined to each other and to solid blocks (when generated there are no updates to do it)."""
    from lint import top_height, bname
    from .common import DIRV
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
    o = construct()
    d = o.t.bounds()[:3]
    open_stairwells(o.t)   # huecos de escalera cortos
    reg.add(o.t, "unica")                       # normaliza a coordenadas >= 0
    o.t.lint_open = {shift(p, d): v for p, v in o.t.lint_open.items()}
    o.ruin_piece = {shift(p, d) for p in o.ruin_piece}
    o.surface = {shift(p, d) for p in o.surface}
    o.circuits = [(n, [(k, shift(p, d)) for k, p in a], [(k, shift(p, d)) for k, p in e]) for n, a, e in o.circuits]
    sea = -d[1]
    reg.warnings += [f"galeon: {e}" for e in audit_it(o, sea)[:20]]
    reg.pool("unicas/galeon/inicio", [(NAME, 1, "rigid", PROCESSORS)])
    anchor = list(shift(ANCHOR, d))
    STRUCTURE["json"] = {
        "type": "heraldia:galeon", "biomes": ["minecraft:beach", "minecraft:snowy_beach"], "step": "surface_structures",
        "spawn_overrides": {}, "terrain_adaptation": "none", "start_pool": "heraldia:unicas/galeon/inicio",
        "anchor": anchor, "probes": sorted(PROBES, key=lambda p: not p["required"]), "max_misses": 3, "search_radius": 56}
    build.construction = o
    return o
