"""Catedral gótica (estructura única): fachada con dos torres y rosetón, nave con colaterales y triforio,
arbotantes, crucero con aguja, coro con girola y capillas, sacristía, biblioteca, claustro; bajo tierra,
cripta, osarios y cámara del tesoro. Diseño y recorrido en docs/unicas/catedral.md."""
from .._comun.piezas import open_stairwells
from core import Template
from .botin import LOOT, LANG
from .modelo import Catedral
from . import interior, cripta
from .._comun import piezas

STRUCTURE = dict(biomes=["minecraft:forest", "minecraft:flower_forest"], start_pool="unicas/catedral/inicio",
                 size=2, max_distance=80, terrain_adaptation="beard_thin", step="surface_structures",
                 start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG", spacing=250, separation=190)
NOMBRE = {"es_es": "Catedral gótica", "en_us": "Gothic cathedral"}
TROFEO = {"objeto": "recovery_compass", "rareza": "uncommon",
          "nombre": ("Brújula de ánimas de Fray Osmundo", "Friar Osmund's Soul Compass"),
          "lore": [("Señala siempre el lugar de tu última caída.", "It always points to where you last fell.")]}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
    "cofre": "biblioteca",
    "relato": [
        ("Entre los árboles del bosque se alza una catedral de agujas altísimas. Fray Osmundo, su "
         "custodio, me enseñó la biblioteca y la cripta. «Tres virtudes abren», me dijo, «y la codicia "
         "castiga». No lo entendí hasta después.",
         "Among the trees of the forest rises a cathedral of soaring spires. Friar Osmund, its keeper, "
         "showed me the library and the crypt. “Three virtues open,” he told me, “and greed is punished.”"
         " I only understood later."),
        ("Le confié el pliego porque no quiso saber qué contenía: le bastaba la fe. Lo guardó entre los "
         "libros de la biblioteca. Si lo has encontrado sin ceder a la codicia, eres quien yo esperaba.",
         "I entrusted him with the leaf because he did not wish to know what it held: faith was enough. "
         "He kept it among the books of the library. If you found it without yielding to greed, you are "
         "the one I awaited."),
    ],
    "pista": ("el bosque, donde una catedral gótica alza sus agujas entre los árboles",
              "the forest, where a gothic cathedral raises its spires among the trees"),
}
LOGRO = {"icono": "minecraft:bell"}   # logros.py
JIG = (65, 0, 30)             # jigsaw de la cripta (bajo el crucero)

# degradación: 80-85 % en buen estado (ver docs/unicas/catedral.md)
def _rule(block, out, p):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block, "probability": p},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    _rule("stone_bricks", "cracked_stone_bricks", 0.11), _rule("stone_bricks", "mossy_stone_bricks", 0.08),
    _rule("deepslate_tiles", "cracked_deepslate_tiles", 0.10), _rule("polished_andesite", "andesite", 0.04)]}]}


def model():
    c = Catedral()
    c.build_symmetric()
    interior.furnish_symmetric(c)
    interior.mirror(c)
    interior.annex(c)
    interior.cloister(c)
    cripta.belfry(c)
    cripta.south_tower_ruin(c)
    cripta.spire(c)
    cripta.crypt(c)
    cripta.library_door(c)
    cripta.ruin_details(c)
    piezas.connect(c.t)
    return c


def pieces(c):
    """Divide el modelo en la pieza de superficie (y >= 0) y la cripta (y < 0), unidas por un jigsaw vertical."""
    top, low = Template("unicas/catedral/catedral"), Template("unicas/catedral/cripta")
    for (x, y, z), (st, nbt) in c.t.blocks.items():
        (top if y >= 0 else low).set(x, y, z, st, nbt)
    for (x, y, z, n) in c.entities:
        (top if y >= 0 else low).entity(x, y, z, n)
    x, y, z = JIG
    top.jigsaw(x, 0, z, "down_south", "heraldia:unicas/catedral/sobre", "heraldia:unicas/catedral/bajo",
               "heraldia:unicas/catedral/cripta", final_state=c.t.get(x, 0, z))
    low.jigsaw(x, -1, z, "up_south", "heraldia:unicas/catedral/bajo", "heraldia:unicas/catedral/sobre",
               "minecraft:empty", final_state=c.t.get(x, -1, z))
    return top, low


def build(reg):
    from .auditoria import audit
    c = model()
    problems = audit(c)
    if problems:
        reg.warnings.extend(f"catedral: {p}" for p in problems[:30])
    top, low = pieces(c)
    open_stairwells(top)
    open_stairwells(low)   # huecos de escalera cortos
    a = reg.add(top, "unica:catedral")
    b = reg.add(low, "unica:catedral")
    reg.pool("unicas/catedral/inicio", [(a, 1, "rigid", PROCESSORS)])
    reg.pool("unicas/catedral/cripta", [(b, 1, "rigid", PROCESSORS)])
