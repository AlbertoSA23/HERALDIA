"""Ice fortress: a hand-designed unique structure (see docs/unicas/ice_fortress.md)."""
from . import construct, audit, chest_loot

STRUCTURE = dict(
    biomes=["minecraft:ice_spikes", "minecraft:snowy_plains", "minecraft:snowy_taiga"],
    start_pool="unicas/fortaleza_hielo/inicio",
    size=1, max_distance=48,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
LOOT = chest_loot.LOOT
LANG = chest_loot.LANG

# Degradation: cracked brick, fallen low merlons and worn diorite slabs (the ice is left alone: a patch of
# snow block on a peak would make ice spikes spawn on top).
PROCESSORS = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + b, "probability": p},
     "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + o}
    for b, p, o in (("stone_bricks", 0.2, "cracked_stone_bricks"), ("stone_brick_wall", 0.3, "air"),
                    ("polished_diorite", 0.2, "diorite"))]}]}
assert {r["input_predicate"]["block"][10:]: r["input_predicate"]["probability"]
        for r in PROCESSORS["processors"][0]["rules"]} == audit.DECAY

REPORT = {}


def run_audit(t):
    """Errors from the specific checks (empty = all good). Fills REPORT for the floor plans."""
    errs = audit.check_redstone(t)
    lerr, lvl = audit.check_light(t)
    errs += lerr
    view, moved = audit.opened(t)
    if len(moved) != 4:
        errs.append(("secret doors: 4 retracted blocks expected", tuple(moved)))
    surf, damaged = audit.condition(t, construct.RUIN)
    if not 0.15 <= damaged <= 0.20:
        errs.append((f"damaged surface {damaged:.1%} outside 15-20 %", None))
    REPORT.update(view=view, light=lvl, surface=surf, damaged=damaged, moved=moved)
    return errs


def build(reg):
    t = construct.build_template()
    name = reg.add(t, "unica")
    t.lint_view, _ = audit.opened(t)            # lint walks the fortress with the secret doors open
    for msg, pos in run_audit(t):
        reg.warnings.append(f"{name}: {msg} {pos}")
    reg.pool("unicas/fortaleza_hielo/inicio", [(name, 1, "rigid", PROCESSORS)])

DISPLAY_NAME = {"es_es": "Fortaleza de hielo", "en_us": "Ice Fortress"}
TROPHY = {"objeto": "golden_helmet", "rareza": "epic",
          "nombre": ("Corona de escarcha", "Frost Crown"),
          "lore": [("Fría al tacto incluso junto al fuego.", "Cold to the touch even beside a fire."),
                   ("La ciñó el Rey Escarcha.", "Once worn by the Frost King.")],
          "encantamientos": {"minecraft:unbreaking": 2},
          "componentes": {"minecraft:trim": {"material": "minecraft:diamond", "pattern": "minecraft:spire"}}}   # guardian trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "galeria",
    "relato": [
        ("Crucé las llanuras nevadas hasta una fortaleza de hielo. Su señor, el Rey Escarcha, llevaba una"
         " corona tan fría que quemaba. Me dijo que el invierno no olvida nada y que en su reino nada se "
         "pudre.",
         "I crossed the snowy plains to a fortress of ice. Its lord, the Frost King, wore a crown so cold"
         " it burned. He told me that winter forgets nothing and that in his realm nothing rots."),
        ("Por eso le confié el pliego: el hielo lo conservaría intacto. Lo dejamos en la galería, bajo la"
         " mirada de sus vigías. Juró que el invierno sería eterno antes que entregarlo. Aún nieva allí.",
         "That is why I entrusted the leaf to him: the ice would keep it whole. We left it in the "
         "gallery, under the gaze of his watchmen. He swore winter would be eternal before he gave it up."
         " It still snows there."),
    ],
    "pista": ("las llanuras nevadas, donde una fortaleza de hielo guarda a su rey helado",
              "the snowy plains, where an ice fortress keeps its frozen king"),
}
ADVANCEMENT = {"icono": "minecraft:blue_ice"}   # advancements.py
MAP = {"decoration": "minecraft:red_x"}
