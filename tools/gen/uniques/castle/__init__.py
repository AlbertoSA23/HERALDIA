"""Castle: 100 x 100 medieval fortress in plains and meadows, with a dungeon under the keep.
Full design in docs/unicas/castle.md."""
from . import surface, dungeon, audit
from .chest_loot import LOOT, NAMES

STRUCTURE = dict(
    biomes=["minecraft:plains", "minecraft:sunflower_plains", "minecraft:meadow"],
    start_pool="unicas/castillo/inicio", size=3, max_distance=80, terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": -(surface.G + 1)}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190)
DISPLAY_NAME = {"es_es": "Castillo", "en_us": "Castle"}
# Guardian's reinforcements in each phase (bosses.py): the cursed garrison.
REINFORCEMENTS = [{"mob": "zombie", "equipo": {"mainhand": "iron_sword", "head": "chainmail_helmet"}},
             {"mob": "zombie", "equipo": {"mainhand": "iron_sword", "head": "chainmail_helmet"}}, "skeleton"]
TROPHY = {"objeto": "iron_helmet", "rareza": "rare",
          "nombre": ("Yelmo de Sir Aldric", "Helm of Sir Aldric"),
          "lore": [("Abollado por mil asedios, nunca rendido.", "Dented by a thousand sieges, never surrendered.")],
          "encantamientos": {"minecraft:protection": 1},
          "componentes": {"minecraft:trim": {"material": "minecraft:gold", "pattern": "minecraft:sentry"}}}   # guardian's trophy (_comun/chest_loot.trophy)
STORY = {   # its sheet of the Chronicle of the Heralds (docs/STORY.md, _comun/chest_loot.historia_*)
    "cofre": "capilla",
    "relato": [
        ("En las llanuras me abrió la puerta Sir Aldric, castellano de una fortaleza que había resistido "
         "mil asedios. Ninguno lo había rendido. Me pareció el guardián perfecto: nadie le quitaría lo "
         "que él no quisiera dar.",
         "On the plains Sir Aldric opened his gate to me, castellan of a fortress that had withstood a "
         "thousand sieges. None had made him yield. He seemed the perfect guardian: no one would take "
         "from him what he would not give."),
        ("Juró sobre su espada guardar el pliego mientras quedara en pie una almena, y lo dejamos en la "
         "capilla. Hoy dicen que el castellano está maldito. Tal vez su juramento sea la maldición.",
         "He swore on his sword to keep the leaf while a single battlement stood, and we left it in the "
         "chapel. Now they say the castellan is cursed. Perhaps his oath is the curse."),
    ],
    "pista": ("las llanuras abiertas, donde un castillo de altas murallas no se ha rendido nunca",
              "the open plains, where a high-walled castle has never surrendered"),
}
ADVANCEMENT = {"icono": "minecraft:stone_bricks"}   # advancements.py
TEXTS = {"heraldia.castillo.guardian": ("Sir Aldric, el Castellano Maldito", "Sir Aldric, the Cursed Castellan")}
TEXTS.update(NAMES)
LANG = {"es_es": {k: v[0] for k, v in TEXTS.items()}, "en_us": {k: v[1] for k, v in TEXTS.items()}}


def _rule(block, out, p):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block,
                                "probability": p},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


# Decay: moss and cracks (scattered ruin details); the major ruin is placed by hand.
PROC = {"processors": [{"processor_type": "minecraft:rule", "rules": [
    _rule("stone_bricks", "mossy_stone_bricks", 0.15), _rule("stone_bricks", "cracked_stone_bricks", 0.1),
    _rule("cobblestone", "mossy_cobblestone", 0.2)]}]}

LAST = {}


def build(reg):
    t, cmeta = surface.build()
    d, dmeta = dungeon.build(cmeta.pop("below"))
    reg.add(t, "unica")
    reg.add(d, "unica")
    reg.pool("unicas/castillo/inicio", [(t.name, 1, "rigid", PROC)])
    reg.pool("unicas/castillo/mazmorra", [(d.name, 1, "rigid", PROC)])
    errs, res = audit.audit(t, d, cmeta, dmeta)
    reg.warnings += [f"castillo: {e}" for e in errs]
    LAST.update(t=t, d=d, cmeta=cmeta, dmeta=dmeta, res=res)
