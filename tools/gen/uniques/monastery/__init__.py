"""Mountain monastery: a single rigid template with its own crag, terraces, church and caves (see docs/unicas/monastery.md)."""
from .._common.pieces import open_stairwells
from . import construction, audit
from .chest_loot import LOOT, LANG_ITEMS
from .._common.chest_loot import lang

ID = construction.ID
STRUCTURE = dict(
    biomes=["minecraft:meadow", "minecraft:grove"],
    start_pool=f"unicas/{ID}/inicio",
    size=1, max_distance=64,
    terrain_adaptation="none",
    step="surface_structures", start_height={"absolute": -25}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
DISPLAY_NAME = {"es_es": "Monasterio de montaña", "en_us": "Mountain Monastery"}
TROPHY = {"objeto": "amethyst_shard", "rareza": "rare",
          "nombre": ("Lágrima del relicario", "Tear of the Reliquary"),
          "lore": [("Dicen que lloró cuando cayó el último monje.", "They say it wept when the last monk fell."),
                   ("La custodiaba Fray Tenebrio.", "Guarded by Friar Tenebrius.")]}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "biblioteca",
    "relato": [
        ("En las praderas de la montaña, un monasterio cuelga del risco. Los monjes copiaban libros a la "
         "luz de las velas y no hacían preguntas. Fray Tenebrio, guardián del relicario, me ofreció una "
         "celda y silencio.",
         "In the mountain meadows, a monastery clings to the crag. The monks copied books by candlelight "
         "and asked no questions. Friar Tenebrius, guardian of the reliquary, offered me a cell and "
         "silence."),
        ("El pliego quedó en la biblioteca, entre códices que nadie más leería. Tenebrio juró custodiarlo"
         " junto al relicario hasta que cayera el último monje. Dicen que la reliquia lloró aquel día.",
         "The leaf stayed in the library, among codices no one else would read. Tenebrius swore to keep "
         "it beside the reliquary until the last monk fell. They say the relic wept that day."),
    ],
    "pista": ("las praderas de la montaña, donde un monasterio cuelga del risco",
              "the mountain meadows, where a monastery clings to the crag"),
}
ADVANCEMENT = {"icono": "minecraft:writable_book"}   # advancements.py

_TEXTS = {
    "cripta.1": ("Apagad las luces", "Put out the lights"), "cripta.2": ("de los difuntos", "of the departed"),
    "cripta.3": ("y la lápida", "and the stone"), "cripta.4": ("se apartará.", "will move aside."),
    "osario.1": ("Velan el primero", "The first wakes"), "osario.2": ("y el último;", "and so the last;"),
    "osario.3": ("el del medio", "the one between"), "osario.4": ("duerme.", "sleeps."),
    "guardian": ("Fray Tenebrio, guardián del relicario", "Brother Tenebrio, Warden of the Reliquary"),
}
_TEXTS.update(LANG_ITEMS)
LANG = lang(f"heraldia.unicas.{ID}.", _TEXTS)

# Ageing processor (cosmetic only: it opens no gaps and removes no supports)
AGING = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{out}"}
    for out, p in (("cracked_stone_bricks", 0.08), ("mossy_stone_bricks", 0.087))] + [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:cobblestone", "probability": 0.15},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:mossy_cobblestone"}]}]}


def build(reg):
    t = construction.construct()
    errors = audit.check(t)
    reg.warnings.extend(f"monasterio: {e}" for e in errors)
    open_stairwells(t)   # huecos de escalera cortos
    name = reg.add(t, f"unica:{ID}")
    reg.templates[name].lint_open = dict(t.open_items)          # common lint.py convention: secret doors open
    reg.pool(f"unicas/{ID}/inicio", [(name, 1, "rigid", AGING)])
