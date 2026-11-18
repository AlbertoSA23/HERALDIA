# Gothic cathedral (`heraldia:unicas/catedral`)

A unique structure in the style of Notre-Dame, designed by hand in `tools/gen/uniques/cathedral/` (a single variant).
Biome: forest and flower forest (`minecraft:forest`, `minecraft:flower_forest`). Default rarity: a 250-chunk grid
(separation 190), one every ~3,000-5,000 blocks.

## Size and pieces

- 117 × 84 blocks in plan (x 0..116, z 4..87) and 77 high (y -8..68; the spire reaches 68).
- Two rigid pieces joined by a vertical jigsaw under the crossing (`size` 2, radius 80):
  - **catedral** (y ≥ 0): everything above the ground. Its base is the ground (y = 0), so `beard_thin` settles
    and smooths the terrain around the footprint as in the villages.
  - **cripta** (y -8..-1): crypt, ossuaries and the treasure chamber, under the crossing, the choir and the apse. Being a separate
    piece, its base does not drag the surface one down (lesson from `DEVELOPMENT.md`: a piece that goes down sinks the terrain);
    its beard stays 8 blocks deep, in rock, and it is surrounded by a two-block wall.
- Degradation: a rule processor (cracked stone bricks 11 % and mossy 8 %, cracked slate tiles 10 %,
  polished andesite 4 %) plus explicit damage that makes sense. The audit computes the damaged part of the outer surface:
  **15.8 %** (target 15-20 %, i.e. 80-85 % in good condition).

## Floor plans by level (complete plans in `catedral/planos.txt`)

Axes: x grows from the west façade (x = 6) to the apse; z from north to south; symmetry axis z = 30. Player's feet at y.

| Level (feet) | What is there |
|---|---|
| -7 | Crossing crypt (pillars, bishops' tombs, altar) with two chests; west chamber with a zombie spawner; ossuary (an axis and two loops with skulls in niches); the skeletons' ossuary (spawner); a sunken gallery with cave spiders (spawner, cobwebs); a narrow passage with a trap; the seals antechamber; the treasure chamber; a hidden reliquary under the altar. |
| 1 | Atrium with a flight of steps; three portals (the central one with a trumeau and two in the towers); narthex under the gallery; a 7-bay nave with pews, pulpit and chandeliers; aisles; crossing with north and south portals and the two staircases to the crypt; choir with stalls; high altar on a dais in the apse; ambulatory with three radiating chapels; sacristy (to the north); cloister with a garden, well and tree; chapter house; ruined refectory. |
| 9 | Library above the sacristy (bookshelves, reading table, lecterns) and secret cabinet. |
| 12 | Triforium (galleries) above the aisles, the ambulatory and the choir; high walkways crossing the arms of the crossing; organ gallery above the narthex. |
| 17 | Terraces above the aisles and the ambulatory (accessible roofs), under the flying buttresses; sacristy roof. |
| 28 | Gutter along the nave with a parapet; façade terrace with the gallery of columns; loft above the vaults (nave, crossing, choir and apse). |
| 40 | Bell tower (north tower, two bells on a beam); south tower with its roof caved in. |
| 56 | Tower roof terraces with a crenellated parapet. |

## Player route

1. Atrium and central portal → nave. Along the aisles you reach the crossing and, along the ambulatory, the chapels.
2. Towers: a spiral staircase (slabs, 0.5 blocks per step) in each tower, with exits to the ground floor, the organ
   gallery and the triforium (12), the aisles' terrace (17), the façade terrace (28), the bell tower (40) and the roof terrace (56).
3. From the façade terrace: the nave's gutter and dormers into the loft; the loft joins nave, crossing, choir and apse.
4. Triforium: from the tower to the crossing, along the arm's high walkway, to the triforium of the choir and the ambulatory (a full ring).
5. Sacristy through the north ambulatory door; stairs to the library; a service turret from the sacristy to the
   choir's triforium and to the terrace (sacristy roof).
6. Cloister through the passage from the south aisle; chapter house along the east walk; refectory along the south walk.
7. Crypt down either of the two staircases in the arms of the crossing → ossuary → narrow passage (trap) →
   seals antechamber → (puzzle) → treasure chamber.
8. Secrets: a lever hidden among the library's bookshelves (cabinet); a lever on the dais of the high altar
   (iron trapdoor and a ladder down to the reliquary).

## Chests (19) and loot

| Place | Table | Value |
|---|---|---|
| Radiating chapels (4 barrels) | `capilla` | candles, gold nuggets, paper |
| Cloister, chapter house, refectory | `menor` | bread, candles, coal, nuggets |
| Sacristy (2) | `sacristia` | candles, gold nuggets, wool, books |
| Library | `biblioteca` | books, paper, ink; a random enchanted book in the extra |
| Bell tower | `campanario` | string, chains, lanterns; "Bell of the North Tower" in the extra |
| Crypt (2) | `cripta` | bones, gold, iron; the odd diamond or golden apple |
| Ossuary | `osario` | bones, arrows; a skull, "Saint's Bone" |
| Secret cabinet and reliquary | `oculto` | enchanted book (10-20), gold, emeralds, diamonds, "Illuminated Psalter", discs |
| Treasure chamber (2) | `tesoro` | gold, emeralds, 1-3 diamonds, enchanted iron gear, "Golden Chalice" |
| Treasure chamber, main | `premium` | see below |

Premium: one main item (90 % showy: the gold "Chapter's Sword", the "Helm of the Captain of the Guard", "Bishop
Ermengol's Crozier", "Friar Osmundo's Bow", "Golden Chalice"; 10 % something stronger: the diamond "Martyrs' Breastplate" with Protection III,
a diamond sword with Sharpness IV or an enchanted golden apple), 2-3 showy ones (discs, host/raiser/shaper/wayfinder trim templates,
an enchanted book 15-25, "Psalter"), 3-5 valuables (gold, emeralds, 1-3 diamonds) and an extra. No netherite or elytra.
Each table has its extra pool marked `solo_sin_lootr`.

## Puzzles, traps, spawners and guardian

- **Seals puzzle** (antechamber → treasure): four levers on the wall, each under a sign: Greed, Faith, Hope,
  Charity; a side sign says "3 virtues open / greed punishes". The door is a double block of chiseled stone
  held by two extended sticky pistons in a four-thick wall (levers | torches | door, pistons and dust |
  treasure side). Behind each virtue there is a redstone torch (inverter) next to a continuous line of dust that keeps
  the pistons extended: it only opens with the three virtues on. The greed lever is a trap: it fires an
  arrow from a dispenser hidden behind its sign. The shared simulator (`_common/redstone.py`) tries the 8 combinations.
- **Secret cabinet** (library): the same mechanism with a lever among the bookshelves in the northeast corner; the door is
  a bookshelf that moves back into the wall.
- **Reliquary**: an iron trapdoor on the dais of the high altar, opened by the floor lever next to it; a ladder down to the reliquary.
- **Traps** like in the vanilla temples: a tripwire along the ossuary's axis (two dispensers with arrows right above the
  hooks) and a pressure plate in the narrow passage (two dispensers at floor level).
- Everything is placed in a consistent rest state without depending on updates: pistons extended and powered, torches lit,
  dust with its power and its connections written, levers, hooks, wire and dispensers off.
- **Spawners** (only in the crypt, in the dark): zombies (west chamber), skeletons (north ossuary), cave spiders (sunken gallery).
- **Guardian**: "Friar Osmundo, keeper of the treasure", a skeleton in the treasure chamber with 40 health, armor 4, a bow with
  Power II, a chainmail helmet and a gold chestplate, `PersistenceRequired`.
- No villagers or golems: the cathedral is abandoned (partly in ruins) and its treasure guarded.

## Ruin (15-20 % of the surface)

Besides the processor: the south tower with its roof caved in over the bell chamber and a notched parapet; four broken stained-glass windows in the
south clerestory; gaps in the parapet of the south terrace; a hole in the nave's roof (with rubble in the loft); the south walk
of the cloister partly collapsed with two fallen columns; the refectory without a roof, notched walls, rubble and moss;
the crypt's sunken gallery.

## Against the owner's criteria

- Stairs: complete spirals from the ground floor to the roof terrace; straight flights with support; none ends in the void.
- Doors and openings: the audit checks that every door has a way through on both sides and that no room is left without access.
- Furniture against the walls: pews and stalls in rows with a central aisle, bookshelves not covering windows, a table with chairs
  facing outwards.
- Nothing floating: lanterns hanging on chains up to the vault, bells on a beam, flying buttresses and roofs joined by faces
  (the audit looks for groups of blocks that do not reach the ground).
- Symmetry about the nave's axis except what has a function of its own (sacristy to the north, cloister to the south, bell tower).
- Light: no covered walkable cell at the surface is left dark (no monsters spawn inside); the crypt is dark.

## Checks

- The spiral staircase, piston doors, traps, spawners, guardian, signs and loot helpers come from the shared pieces
  in `tools/gen/uniques/_common/` (`pieces.py` and `chest_loot.py`).

- `tools/gen/uniques/cathedral/audit.py` (a condition for generating): a walk from the atrium with the mechanisms
  operated, access to chests, spawners, levers, bells, lecterns, doors and steps; rooms without access; floating
  blocks; light; static consistency of the redstone; ruin ratio. It also runs `lint.py` and the registry validation.
- `tools/gen/uniques/cathedral/smoke_game.py`: a real 26.3 dedicated server; it places the two pieces with `/place template`,
  checks the rest state after the updates, operates each mechanism (a lever simulated with a redstone block on its support)
  and checks traps, spawners, chests and guardian.
- `python3 -m unicas.catedral.planos <folder> render` (from `tools/gen`) regenerates plans and renders.
