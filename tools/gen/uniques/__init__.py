"""Unique structures: each module in this package (unicas/<id>.py or unicas/<id>/) defines one structure.

Contract of each module (the generator discovers them by itself; main.py and writer.py need no changes):
  STRUCTURE = dict(
      biomes=["minecraft:forest", ...] (goes into the tag heraldia:unicas/<id>, with the #c: tags from biomes.CONVENTIONAL)
             or "#heraldia:<familia>" (tag of a village family); also in STRUCTURE["json"]["biomes"],
      start_pool="unicas/<id>/inicio",
      size=1..20, max_distance=1..116,
      terrain_adaptation="beard_thin" | "beard_box" | "bury" | "encapsulate" | "none",
      step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG" (or None),
      spacing=250, separation=190,   # chunks; by default one every ~3,000-5,000 blocks (separation: see below)
  )
  # The grid is heraldia:rejilla: enabled and spacing in blocks are set in config/heraldia.json
  # (unicas.<id>.activada, unicas.<id>.separacion_bloques) without writing code; spacing gives the default value. For the
  # configurable ones the Java code does not use separation: the internal spacing is the minimum distance between unique
  # structures and the grid origin is shifted per type (GridPlacement), so that each type spreads over the whole cell.
  # Optional: STRUCTURE["candidata_en_bioma"] = True for very rare biomes (mushroom fields): the candidate of each
  # cell is not a random chunk, but the site in the cell's window that lies deepest inside its biomes (GridPlacement).
  # Optional: STRUCTURE["placement"] = custom placement (JSON dict); the structure then stops being configurable.
  # Optional: STRUCTURE["json"] = complete dict of the structure (a custom type in Java, for example); replaces the above.
  def build(reg): adds templates (names "unicas/<id>/...") and pools ("unicas/<id>/...") to the registry.
  LOOT = {"premium": table, ...}   -> heraldia:unicas/<id>/<name>
  KEYS = {"<key>": {"tabla": table, "cerradura": lock}}   (optional) keys for chests locked with `lock`: the table
      gives exactly the item the lock asks for; it goes to heraldia:llaves/<id>/<key> and /heraldia key offers it.
  LANG = {"es_es": {...}, "en_us": {...}}   (optional) own translation keys that are added to the mod's language file.
  # Optional (treasure maps, see maps.py): name for the map and its marker on the map.
  DISPLAY_NAME = {"es_es": "Atlántida", "en_us": "Atlantis"}           # by default, the id
  MAP = {"decoration": "minecraft:monument"}                     # by default minecraft:red_x
  # Optional (advancements, see advancements.py): discover, guardian and treasure come out on their own; this only adjusts them.
  ADVANCEMENT = {"icono": "minecraft:trident",       # icon of "discover"; by default minecraft:filled_map
           "tesoro": ["premium"],              # LOOT tables whose chest counts as treasure; by default ["premium"]
           "tesoro_objeto": {item predicate},   # or obtain an item (fixed-content chest, no table)
           "extra": [{"id", "icono", "titulo": (es, en), "descripcion": (es, en), "criterios": {...},
                      "requisitos": [[...]], "padre": "descubrir", "marco": "task", "xp": 30}]}   # own advancements
  # The final guardian is created with _comun/pieces.guardian (tag heraldia_guardian): without it the build fails,
  # and also if there is more than one (each guardian drops a trophy).
  TROPHY = {"objeto": "iron_axe",                       # REQUIRED: trophy the guardian drops (_comun/chest_loot.trophy)
            "nombre": (es, en), "lore": [(es, en)],      # one or two lore lines
            "rareza": "rare",                            # common | uncommon | rare | epic (name color)
            "encantamientos": {"minecraft:efficiency": 2},   # optional, levels 1-3
            "componentes": {"minecraft:trim": {...}}}    # optional: trim, banner pattern... (not name, lore, rarity or custom_data)
  # The trophy (heraldia:trofeos/<id>, custom_data {heraldia_trofeo: "<id>"}) only drops if a player kills the guardian:
  # pack.tag_guardians gives it the DeathLootTable heraldia:guardianes/<id>/<mob> (its usual loot + the trophy).
  # Without TROPHY (or without name, lore..., or with netherite/elytra) the build fails. The advancement unicas/trofeos comes out on its own.
  REINFORCEMENTS = ["husk", {"mob": "husk", "equipo": {"mainhand": "iron_sword"}}]   # optional (bosses.py): 2-3 mobs that the
  # guardian summons in each phase (when dropping below 66 % and 33 %); without it, those of the family of its guardian's type.
  STORY = {"cofre": "biblioteca",                   # REQUIRED: its sheet of the Chronicle of the Heralds (docs/STORY.md)
              # cofre: LOOT table of a minor chest or a hidden room that is already in its templates (preferably just one)
              "relato": [(es, en), (es, en)],              # 1-2 pages (max. chest_loot.MAX_PAGINA characters): its part
              "pista": (es, en),                           # how the previous sheet points to it: biome and feature, no name
              "final": True}                               # only Atlantis: closes the chain
  # The chain is computed automatically (chest_loot.story_chain: by id and the final one at the end, which points to the first): the sheet of
  # each unique structure (heraldia:historia/<id>, custom_data {heraldia_historia: "<id>"}) adds a page with the hint to the
  # next one and, sometimes, its treasure map; the table of its chest nests it. Without STORY (or with a chest that is not
  # in its templates, or pages that are too long) the build fails. The advancement unicas/cronista comes out on its own.
  LANG = {"es_es": {...}, "en_us": {...}}   # optional: own texts (same keys in both languages)
  # Optional in a template: t.lint_open = {pos: state or None}, state with the puzzles solved for the walkthrough.

Loot and Lootr: a group (pool) with "solo_sin_lootr": True is skipped if the server runs Lootr
(condition heraldia:sin_lootr). Use it for the extra per chest, so that with Lootr each player gets the modest loot.
The generator also writes the tag heraldia:unicas/<id> and its structure_set, and the treasure map\n(epic chest of the villages and cartographer master trade; maps.py).
"""
import importlib, pkgutil, zlib

DEFAULT_SPACING, DEFAULT_SEPARATION = 250, 190
# Unique structures that were already in 0.1.0 (main branch, before the shifted grids): with uniques.rejilla_compatible they are
# placed with the grid of that time so that the ones already generated in worlds of that version are found. None is
# added: a new unique structure was never generated with the old grid. All the others always use the new grid.
OLD_GRID = frozenset({"acueducto", "castillo", "catedral", "ciudadela", "coliseo", "faro", "fortaleza_hielo", "galeon",
                             "mansion", "monasterio", "observatorio", "palacio", "piramide", "torre_mago"})


# Published id of each module whose name is not its id: the id (heraldia:unicas/<id>, its tags, options,
# advancements and translation keys) is already in players' worlds and configurations, so it never changes;
# a new module is published under its own name.
PUBLISHED_IDS = {
    "aqueduct": "acueducto",
    "ash_citadel": "ciudadela_ceniza",
    "atlantis": "atlantida",
    "castle": "castillo",
    "cathedral": "catedral",
    "citadel": "ciudadela",
    "colosseum": "coliseo",
    "corsair_island": "isla_corsario",
    "galleon": "galeon",
    "ice_fortress": "fortaleza_hielo",
    "jarl_hall": "salon_jarl",
    "lighthouse": "faro",
    "lost_mine": "mina_perdida",
    "monastery": "monasterio",
    "mycelium_lab": "laboratorio_micelio",
    "observatory": "observatorio",
    "palace": "palacio",
    "pyramid": "piramide",
    "sanctuary": "santuario",
    "void_sanctum": "sagrario_vacio",
    "wizard_tower": "torre_mago",
}


def published_id(module_name):
    return PUBLISHED_IDS.get(module_name, module_name)


def module_name(sid):
    """Module name of the published id sid (the inverse of published_id)."""
    return next((m for m, i in PUBLISHED_IDS.items() if i == sid), sid)


def modules():
    """[(id, module)] sorted by id, for a deterministic output."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            found.append((published_id(info.name), importlib.import_module(f"{__name__}.{info.name}")))
    return sorted(found)


def salt(sid):
    """Stable salt per structure so that each type has its own placement grid."""
    return zlib.crc32(f"heraldia:unicas/{sid}".encode()) & 0x7FFFFFFF
