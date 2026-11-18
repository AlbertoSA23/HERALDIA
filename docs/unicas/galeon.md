# Stranded galleon (`heraldia:unicas/galeon`)

A three-masted galleon (62 blocks long, 17 in the beam, a mainmast 40 m above the keel) run aground on its side on the
shore, with its landward side burst open by the stranding, the castaways' camp on the sand and, behind, a crag with
the cave where they hid the captain's treasure. A single variant, designed by hand (`tools/gen/uniques/galleon/`).

Differences from the vanilla shipwreck: ten times its volume; four habitable decks with 16 furnished rooms;
a camp and a cave; puzzles, traps, spawners and a guardian; loot spread over 18 chests and 3 archaeology blocks.

## Placement on the shore (Java)

The jigsaw does not see water, so the structure uses a custom type, `heraldia:galeon`
(`io.github.albertosa23.heraldia.unicas.galeon`), which reuses `JigsawPlacement` for the piece and decides the spot and the rotation first:

1. A cheap discard: if no point of a 16-block grid (radius 64) falls on a beach, there is no galleon.
2. A grid of candidates every 8 blocks (radius 56) x 4 rotations. For each one the **probes** written by the generator
   in the JSON are measured (template positions, all multiples of 8): the seabed height (`OCEAN_FLOOR_WG`) relative to sea
   level must fall within a range. The hull's sea band: water 2 to 9 deep; open sea: water; the hull's land band,
   the camp and the crag: land between sea level and +4 (+12 for the crag). The hull ones are mandatory; for the rest
   3 failures are allowed. The candidate with the fewest failures and the flattest terrain wins. The heights are cached per column.
3. `JigsawPlacement.addPieces` is called with `maxDepth` 1 (with 0 it does not add even the central piece). The rotation of `JigsawPlacement` is the first roll of `context.random()`. It is passed a copy of the `GenerationContext` with a
   deterministically seeded `WorldgenRandom` whose first roll gives the chosen rotation: the result does not depend on the
   game changing its internal seed.
4. The piece is placed without projection: the template's anchor (waterline amidships) sits at `seaLevel`. The biome is
   validated at the anchor (beach or snowy beach) and not at the center of the box, which falls underground.
5. `/place structure` (a biome predicate that accepts anything): if there is no shore, it is still placed at the center of the chunk
   so that it can be tested.

Terrain adaptation: `none`. Each part brings its own seat: a sand bed on a sandstone base under the hull, a sand floor
4 thick and a 6-high volume of air above the camp (it shaves dunes), and a 2-block rock shell around
every hollow of the cave. That way there is no `beard` to sink the terrain over the basements. Water: all the air below sea level is
surrounded by template blocks (checked), so the sea does not get in through any gap.
`IGNORE_WATERLOGGING` is used: the chests and stairs of the hold are not waterlogged.

Biome: `#minecraft:is_beach` (beach and snowy beach). It does not touch the rocky coast (`stony_shore`), which is left free for the lighthouse.

## Floor plans by level (y = height of the feet; 0 = sea level)

Template axes: X from land (0) to sea; Z from bow (north) to stern. The ship's centerline at X = 64.

| Level | Rooms (from bow to stern) |
|---|---|
| Hold (-4) | fore hold (drowned spawner, chest) · main hold with sand coming in through the breach, stowed cargo and a **hidden store** behind a maze of barrels (chest) · powder store (barrel) · **powder magazine** (chest with a TNT trap) |
| Gun deck (1) | the boatswain's store (barrel) · a battery of 10 cannons, the mess and the **breach** through which you enter from the beach · the surgeon's sick bay (chest, brewing stand) |
| Main deck (5) | forecastle: galley (barrel) and hammocks · waist with hatches, capstan and the fallen topmast · aftercastle: **officers' cabin** (table, chest) |
| Forecastle deck (9) | deck with the bell and the bowsprit |
| Quarterdeck (10) | antechamber · **the captain's cabin** (chest, chart table, lectern) · **the purser's chamber** behind a fake bookshelf (chest) |
| Poop deck (15) | three stern lanterns |
| Crow's nest (23) | the mainmast's crow's nest (chest), by ladder |
| Beach (1) | camp: sailcloth tents, a dead campfire, the lookout's hut (chest), graves, a boat, 3 suspicious sand blocks |
| Cave (1 to -7) | mouth in the crag · a descending gallery with a **tripwire trap** · the bone cave (skeleton spawner) with a **hidden niche** behind cobwebs (chest) · antechamber of the **lanterns puzzle** · **treasure chamber** (premium chest and guardian) |

Plans with the cells reachable on foot: `docs/unicas/galeon/plantas.txt`. Renders: `docs/unicas/galeon/*.png`.

## Player route

Beach → camp (modest chests, archaeology) → the breach leads to the gun deck → stairs to the hold
(spawners, hidden store, powder magazine) and to the main deck → castles, quarterdeck, cabin and secret chamber →
crow's nest. From the camp, the cave: gallery with a trap, bone cave, puzzle and the treasure chamber with the captain.

## Puzzles and traps (no redstone dust; everything in a stable state when placed)

- **Fake bookshelf** (cabin → purser's chamber): two extended sticky pistons in the hidden corner of the bulkhead
  hold two bookshelves. They are powered by a redstone torch in a closed cavity (inverter). A lever in the corner
  of the cabin turns the torch off: the pistons pull the bookshelves back and the way opens.
- **Lanterns puzzle** (cave): three levers under red wool (port), green (starboard) and white (stern) and a sign:
  "Port lit, starboard dark; the stern one, never". The red one opens the first iron door; the green one (on when you
  arrive) turns off a torch that opens the second one; the white one fires an arrow from a dispenser.
- **Powder magazine**: a pressure plate in front of the chest with 4 TNT under the floor (like the desert temple).
- **Tripwire** in the cave gallery: two hooks and two dispensers with arrows at head height.

The generator checks with the shared simulator (`uniques/_common/redstone.py`) that the placed state is stable and that each action
produces its effect (pistons retracted, doors opened, dispensers and TNT triggered). If it fails, nothing is generated.

## Enemies

- Spawners: 2 for drowned in the hold (their own light rules, block and sky 0-7, so they work out of the water),
  1 for skeletons in the bone cave, 1 for zombies in the gallery.
- Guardian: **The Drowned Captain** (a drowned, 50 health, 4 armor, an iron saber, a gold helmet, a nautilus shell
  it always drops; persistent) in the treasure chamber.

No villagers or golems: the camp is abandoned (the graves tell what happened) and the spawners would kill them.

## Condition (80-85 % in good condition)

Hand-made ruin: the breach in the landward side (hull and cannons torn out, sand in the hold), the foremast's topmast
broken and fallen, torn sails, broken stretches of railing, broken stern windows, barnacles (dead coral) on the hull.
Processor: 10 % of the hull's outer planks disappear; 20 % of the cave's cobblestone is covered in moss. The audit
computes the percentage of damaged surface and requires 15-20 % (current result: 15.3 %: 337 hand-made cells —breach, torn-off strakes, torn sails, split planks, barnacles— plus the expected 10 % of the processor over 953 planks, out of 2,833 surface cells).

## Loot (vanilla only; an extra per chest marked `solo_sin_lootr`)

| Table | Where | Contents |
|---|---|---|
| `nafrago` | camp (3) | beach food, string, sticks, coal, a worn fishing rod |
| `arena` | suspicious sand (3) | pottery sherds (angler, shelter, snort), nuggets, emerald |
| `bodega`, `cocina` | hold and galley | provisions, wheat, sugar, bottles, paper |
| `polvora` | powder store | gunpowder, flint, fire charge, 1-2 TNT |
| `cirujano` | sick bay | paper, bottles, healing and regeneration potions |
| `oficiales` | officers' cabin | emeralds, gold, books, compass, map, clock |
| `cofa` | crow's nest | spyglass, map, feathers, string |
| `santabarbara` | powder magazine | gunpowder, iron, arrows, crossbow, emeralds |
| `capitan` | cabin | emeralds, gold, spyglass, enchanted book (low), name tag |
| `contrabando`, `cueva` | hidden rooms | gold, emeralds, diamond (rare), golden apple, enchanted book |
| `tesorero` | secret chamber | more gold and emeralds, 1-2 diamonds, golden apple, coast trim |
| `premium` | treasure chamber | 90 %: named items (saber, spyglass, compass, helmet), moderate enchantments, coast and tide trims, discs; 10 %: a named trident, a heart of the sea or an enchanted golden apple |

No netherite or elytra. The more hidden, the richer: beach < decks < cabin < hidden rooms < treasure.

## Against the design criteria

- Stairs: all the decks are joined by complete flights (or a ladder up to the crow's nest); the audit walks from the
  entrance and requires reaching every door, chest, barrel, lectern, furnace and bell.
- Symmetry: double flights of stairs to port and starboard in both castles, a symmetric battery (except for the breach), stern lanterns.
- Furniture against the bulkheads; tables with chairs facing outwards; lanterns hanging from beams.
- Nothing floating: the audit requires every block to be joined to the ground and the sand to be supported.

## What has been checked

- Generation with the audit (`lint.py` + the module's `audit.py`) without warnings; the simulator detects a misplaced torch or lever (a mutation test done by hand).
- Smoke test on a 26.3 dedicated server: it registers, `/place` places it and the 14 loot tables open.
- `tools/smoke/galleon_test.py` on a dedicated server: `/locate` finds a natural galleon (shore search in 0.5 s), `/place`
  places it at that spot with the sea 20 blocks seaward and sand 24 blocks landward, and the drowned captain and the boat are there.
- Not checked: the look in game (missing a screenshot from the owner), whether the drowned from the spawners appear out of the water, and the
  behavior of the circuits in the game (only simulated).
