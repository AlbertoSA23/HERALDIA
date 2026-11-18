# Corsair's Isle (`heraldia:unicas/isla_corsario`)

An islet in the open sea with the fort of **Roque Salitre**, the corsair of the black flag. He pulled Ysolda out of the water
with his brigantine, copied her charts and swore never to put to sea again while he kept her leaf: he is still on his island,
in the treasure chamber below sea level, counting his gold.

It is an original structure: it does not recreate any island, fort or ship from another game or mod. It differs from the **Stranded
galleon** (a three-masted galleon run aground on a beach, with its castaways' camp) and from the **Smugglers'
lighthouse** (on the coast, with its cave) in that it is a whole island in the middle of the sea, with its rock, its sand and its
palm trees: a fort on the hill, a harbor with a two-masted brigantine **afloat**, moored to the pier, and the sea
caves under the hill, with a cove that you enter by boat.

## Biome and placement

- Biomes: **ocean, lukewarm ocean and warm ocean** (the non-deep ones). Atlantis looks for the deep ones and in the
  cold and frozen ones a palm tree island does not fit. There is no conventional tag that narrow (`#c:is_shallow_ocean` includes
  the cold and frozen ones), so only the vanilla list is left (`biomas.py`).
- Rarity: `spacing` 250 chunks by default (one every ~3,000-5,000 blocks), configurable like the others
  (`unicas.isla_corsario.activada`, `unicas.isla_corsario.separacion_bloques`).
- **Candidate in the biome** (`candidata_en_bioma`, like the Mycologist's Laboratory): each grid cell's candidate
  is the point of a 128-block mesh deepest in those oceans (`GridPlacement` with `bioma`, at y = 62).
  That way it falls in the open sea, far from the coast, and `/locate`, maps and `UniqueSeparation` work the same.
- **Custom type `heraldia:isla`** (Java, `unicas/isla/IslaStructure`): the jigsaw does not see water. Around the candidate
  chunk (9 points every 16 blocks, from the inside out) it looks for one whose biome is valid across the whole footprint and an outer
  ring (33 samples of the biome noise, cheap) and whose seabed (`OCEAN_FLOOR_WG`, with the `comun/Alturas` cache)
  lies between 34 and 7 blocks below sea level within a 54-block circle (the island and the brigantine) and below the sea
  in the 78-block ring (water all round: no coast nearby). If nothing qualifies, nothing is generated. It places the template with its
  sea-level row (the first layer of air above the water) at y = 63 and a random rotation. With `/place structure`
  (which accepts any biome) it is placed in the chunk as is.
- **Outside Atlantis**: `AtlantisAnchor.excludes` (in `ChunkGeneratorMixin` and `StructureCheckMixin`) already rejects
  every foreign structure whose start falls inside the city's zone, and `UniqueSeparation` separates it from the other
  unique structures, Atlantis included. The server test checks it with `/locate`.
- **Nothing foreign inside the island** (`unicas/isla/IslaZona`, in the same two mixins, without new mixins): a shipwreck,
  an ocean ruin or a ruined portal whose start falls within 7 chunks of the island candidate of its cell
  is rejected if the island really appears there (the same viability as the minimum distance between unique structures). The expensive part is only
  computed next to a candidate (a few chunks per cell) and is memoized; for the rest, a lookup in a
  table and the cell's candidate (already memoized in `GridPlacement`). Strongholds are not excluded (as in
  Atlantis). The server test looks with `/locate` for the shipwreck and the ocean ruin closest to the island.
- **The islet never hangs**: the template goes down up to 18 blocks below sea level (`BASE`) and its bottom row is
  extended down to the seabed when placed (`heraldia:acueducto_hasta_el_suelo`, 24 blocks at most, only with rock,
  sand, gravel, sandstone and the pier's piles). Around the coast, a slope of sand and gravel goes down to that row:
  no crater and no cut coast. The rest of the box is `structure_void` (the sea stays where it is).
- Terrain adaptation `none`; `liquid_settings` `ignore_waterlogging`: the air in the rooms below sea level
  stays dry and the water that is wanted (the cove, the channel, the cistern) is in the template.

## The surface (y = 0 is the first layer above the water)

Design coordinates: x from west to east (0..111), z from north to south (0..109). The islet is a wavy superellipse of
about 84 × 74 blocks: beach at water level, grass one block up and, to the north and east, the fort's **hill** (a plateau at
y = 7) with cliffs to the sea. Palm trees (a leaning jungle trunk, persistent leaves, cocoa as coconuts).

- **Fort** (the hill's plateau, 25 × 22): a stone brick wall with battlements and a wall-walk (ramps up on the west and
  east), a double gate to the south with the fort's sign, a five-sided **bastion** to the north with four **cannons**
  (decorative dispensers, empty) and the powder room (`polvorin` chest). In the cobbled courtyard: the **corsair's house**
  (ground floor with the long table, the fireplace, the cartography table and the `casa` chest; upstairs his alcove with the
  `corsario` chest), the **barracks** (bunks, `cuartel` chest), the cistern, the black flag's mast and the **descent
  tower**, with the stairs to the caves.
- **Harbor** (the southern esplanade, at y = 1): the **Hanged Mermaid tavern** (bar, tables, fireplace, `taberna`
  chest), with its cellar under the floor (ladder, barrels, `bodega` chest) and, behind the cellar's red **tapestry**, the
  innkeeper's **hideout** (`escondite` chest); two **warehouses** (barrels, `almacen` chest); the **gallows** in the
  square; the flight of steps to the fort and the paths (with steps where they climb a block).
- A T-shaped **pier** on piles that reach the seabed and the **brigantine** moored at its head: a dark oak hull, two
  masts with square sails (some torn), a bowsprit, a deck with a hatch to the **hold** (`bergantin` chest),
  an aftercastle with the **captain's cabin** (bed, table, `camarote` chest and the logbook sign with the puzzle's
  clue) and the poop deck with the helm; the anchor chain goes down to the slope.
- **Lighthouse** on the western tip: a tower of banded terracotta brick on a rock, a ladder up to the lantern (sea
  lantern) and the `faro` chest.

## The caves (feet at y = 1, under the hill)

All of them lined (stone brick or cobblestone) where they face the rock: no springs or lichen inside.

- **Hidden cove**: a 3-wide mouth in the north cliff, at water level, and a channel that crosses the slope and
  the cliff to a lagoon under the bastion, with stone docks to the south and west, the **rowboat** and the
  `ensenada` chest. Under the water, a **drowned** spawner. The water is source blocks at sea level and all the air stays
  above: it does not flood (a lesson from the lighthouse).
- **Guardroom**: at the foot of the descent from the fort (7 steps); a table, the `guardia` chest and the sign with the exits.
  To the west, the **tripwire** corridor (trap 1: two dispensers at head height).
- **Map room**: a checkered floor with the **compass rose**, a cartography table, a lectern and the `cartas` chest, which
  holds the **Chronicle leaf**. **Compass rose puzzle**: four levers on the north wall with their signs (North,
  East, South, West); only **north and west** open the treasure's piston door (`piezas.combo_door`), and
  east and south close it again (dust straight to the line, as in the sanctuary). The clue is in the logbook in the
  brigantine's cabin: "From the harbor to the treasure: north and west; never east or south".
- **Armory** (west): barrels, the `armeria` chest, a smithing table, a grindstone and a **skeleton** spawner. Next to the
  weapon rack, a lever opens the **powder magazine** (a secret piston door, `piezas.lever_door`): gunpowder, TNT and the
  `santabarbara` chest.
- **Dungeons** (south): a corridor with five barred cells, the `calabozo` chest, a sign and a
  **skeleton** spawner.
- Behind the compass rose door, a descent of 7 steps to feet at -6 (below sea level, dry): the
  **antechamber** with the **plate trap** (trap 2: dispensers at floor level on the sides) and the **treasure
  chamber**: two `tesoro` chests, the `premium` chest between gold blocks and **Roque Salitre, the corsair** (a skeleton with
  a bow, a chainmail helmet, 60 health and 6 armor; a skeleton so that it never comes out as a "baby", see the
  lessons).

## Loot (21 chests)

Modest in the harbor and the fort, better in the brigantine and the caves, more in the hidden rooms (hideout, powder magazine)
and the premium chest in the treasure chamber (90 % showy: a named saber, spyglass, tricorn and compass, ingots,
coast and sentry trims, discs; 10 % something stronger: a trident, a diamond sword, an enchanted apple, a totem or
a diamond chestplate with moderate enchantments). No netherite or elytra. Each table has its extra pool only without
Lootr. Named items: Mermaid's Rum, Silver Real, Letter of Marque, Cannon Fuse, the Brigantine's Logbook...

The guardian's trophy: **Roque Salitre's Bow** (Power 2, Unbreaking 2, rare). Leaf: the `cartas` chest in the map
room, between those of the Stranded galleon and the Mycologist's Laboratory.

## Condition and audit

- 80-85 % in good condition: a rule processor (cracked or mossy stone brick, mossy cobblestone, stripped spruce
  planks, fallen panes) and hand-made ruin (fallen battlements, broken tiles, torn sails). The audit measures the visible
  build without counting the natural islet or the vegetation (`recorrido.superficie_danada`): 16 %.
- `auditoria.py` (a condition for generating): the redstone's rest state, the 16 combinations of the compass rose, the
  powder magazine, the two traps and that the cannons have no signal; the walk (`lint.walk`) with the puzzles closed
  and solved and the strict walk (`recorrido.andar`, without jumps or falls of more than one block, swimming in the sea and the
  cove) with a way back to the entrance from anywhere; hidden rooms only with the puzzles; spawners, levers and the
  21 chests within reach; spawner light (they carry `custom_spawn_rules` up to light 11); nothing floating (everything joined to the
  bottom row); the sea does not get in (all air below the water level has its 6 neighbors in the template) and the
  template's water does not escape; the caves' lining.
- Server test: `isla_corsario/prueba_servidor.py` (natural generation with `/locate`, distance to Atlantis,
  dry treasure chamber, `/place` time, entities, mechanisms and traps).
