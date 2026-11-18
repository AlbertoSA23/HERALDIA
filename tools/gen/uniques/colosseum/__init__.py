"""Ruined Colosseum: elliptical amphitheater with a hypogeum (savanna). Design in docs/unicas/colosseum.md."""
from .._common.pieces import open_stairwells
from .chest_loot import LOOT, LANG_ITEMS

STRUCTURE = dict(
    biomes=["minecraft:savanna", "minecraft:savanna_plateau"],
    start_pool="unicas/coliseo/inicio",
    size=2, max_distance=80,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
DISPLAY_NAME = {"es_es": "Coliseo en ruinas", "en_us": "Ruined Colosseum"}
# Guardian's reinforcements in each phase (bosses.py): arena gladiators.
REINFORCEMENTS = [{"mob": "husk", "equipo": {"mainhand": "iron_sword"}},
             {"mob": "husk", "equipo": {"mainhand": "stone_sword", "offhand": "shield"}}]
TROPHY = {"objeto": "shield", "rareza": "rare",
          "nombre": ("Escudo del Campeón de la Arena", "Shield of the Arena Champion"),
          "lore": [("Cien combates y ni una sola derrota.", "A hundred bouts and not a single defeat.")],
          "encantamientos": {"minecraft:unbreaking": 2},
          # without base_color: with it the shield is called "Red Shield" and ignores item_name; the background is the "base" layer
          "componentes": {"minecraft:banner_patterns": [
              {"pattern": "minecraft:base", "color": "red"}, {"pattern": "minecraft:triangles_bottom", "color": "yellow"}, {"pattern": "minecraft:circle", "color": "yellow"},
              {"pattern": "minecraft:border", "color": "black"}]}}   # guardian's trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "lanista",
    "relato": [
        ("En la sabana se levanta un coliseo donde luchaba un campeón con cien combates y ni una sola "
         "derrota. El lanista, su amo, me lo presentó como su mejor inversión.",
         "In the savanna stands a colosseum where a champion fought, with a hundred bouts and not a "
         "single defeat. The lanista, his master, introduced him as his finest investment."),
        ("Al campeón le ofrecí la libertad, pero prefirió el pliego: dijo que guardarlo era una lucha "
         "digna. El lanista lo cerró en su cofre. Para recuperarlo habrá que vencer a quien nunca ha "
         "perdido.",
         "I offered the champion his freedom, but he chose the leaf: he said guarding it was a worthy "
         "fight. The lanista locked it in his chest. To win it back you must defeat one who has never "
         "lost."),
    ],
    "pista": ("la sabana, donde un coliseo en ruinas aún oye el clamor de la arena",
              "the savanna, where a ruined colosseum still hears the roar of the arena"),
}
ADVANCEMENT = {"icono": "minecraft:shield"}   # advancements.py

LANG = {
    "es_es": {"heraldia.coliseo.campeon": "Campeón de la Arena"},
    "en_us": {"heraldia.coliseo.campeon": "Champion of the Arena"},
}
for _k, (_es, _en) in LANG_ITEMS.items():
    LANG["es_es"][f"item.heraldia.coliseo.{_k}"] = _es
    LANG["en_us"][f"item.heraldia.coliseo.{_k}"] = _en


def _rules(*rs):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": [
        {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": f"minecraft:{a}", "probability": p},
         "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{b}"}
        for a, b, p in rs]}]}


PROC_MAIN = _rules(("smooth_sandstone", "sandstone", 0.06), ("cut_sandstone", "sandstone", 0.06))
PROC_HYP = _rules(("stone_bricks", "cracked_stone_bricks", 0.15), ("stone_bricks", "mossy_stone_bricks", 0.07))


def build(reg):
    from . import blueprint, audit
    o, main, hyp, _ = blueprint.construct()
    reg.warnings.extend(f"coliseo: {m}" for m in audit.audit_it(o, main, hyp))
    open_stairwells(main)
    open_stairwells(hyp)   # huecos de escalera cortos
    a = reg.add(main, "unica:coliseo")
    b = reg.add(hyp, "unica:coliseo")
    reg.pool("unicas/coliseo/inicio", [(a, 1, "rigid", PROC_MAIN)])
    reg.pool("unicas/coliseo/hipogeo", [(b, 1, "rigid", PROC_HYP)])
