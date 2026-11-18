# Aqueduct with a ruined city (`heraldia:unicas/acueducto`)

An abandoned Roman colony in the desert. A two-tier arched aqueduct crosses the terrain for 86 blocks
to the *castellum* (the water tank), built against the north wall of a 96 x 92 block city. Below,
the forum's cistern and the sewers, where the treasure chamber is hidden.

- Biome: `desert`, `badlands`, `wooded_badlands` (not `eroded_badlands`: its spires break the aqueduct).
  The coliseum goes in the savanna and the pyramid in its own biome; nothing overlaps here.
- Rarity: the contract's (`spacing` 250 / `separation` 190 chunks: one every ~3,000-5,000 blocks).
- Coordinates in this document: x towards the east, z towards the south, y = 0 the city's paving
  (one block above the natural terrain). The whole structure rotates at random as one block.

## Jigsaw pieces and terrain adaptation

A single variant: each pool has a single element, so the assembly is deterministic.

| Piece | Box (x, z, y) | Parent | Notes |
|---|---|---|---|
| `castellum` (start) | 72-86, -12..4, 0..17 | — | center of the structure: everything stays within 116 blocks |
| `acueducto` | 77-81, -98..-13, 0..17 | castellum (north face) | Java processor `heraldia:acueducto_hasta_el_suelo` |
| `ciudad` | 0-95, 5..97, 0..19 | castellum (south face) | weathering processor (cracked sandstone) |
| `cloaca` | 64-92, -5..44, -11..-1 | castellum (floor, vertical) | sewers, traps and treasure chamber |
| `cisterna` | 33-63, 42..60, -9..-1 | ciudad (forum floor, vertical) | vaulted cistern |

- **`beard_box` adaptation.** The surface pieces have their base at y = 0: the game empties the terrain inside their
  box and fills it below (about 12 blocks). That way the dunes do not get into the houses and the paving is supported.
- **Basements without sinking.** The `beard_thin` problem with pieces that go down (the terrain adjusts to the base of the
  box) is solved like this: the underground part goes in **separate pieces** hung by a vertical jigsaw, whose box is entirely
  underground and **filled block by block** (sandstone and stone where there is no room). The emptying of `beard_box` inside
  that box is overwritten by the template and the surface piece does not go below y = 0.
- **Pillars down to the ground.** The aqueduct is rigid (the channel must be horizontal), but the terrain is not.
  Neither `beard_box` nor the `terrain_matching` projection handles a valley of more than ~6 blocks, so there is a
  custom processor (Java, `finalizeProcessing`): each `smooth_sandstone` block of the piece's y = 0 row is
  extended downwards, only within the chunk being generated, until it finds solid ground (not air, not
  fluid, not replaceable, not leaves; at most 64). The foundations of the 13 pillars always reach the ground.

## Player route

1. **Arrival.** The aqueduct is visible from far away (18 high). Its northern end is broken: the last two spans lost
   their upper tier and span 9-10 has collapsed. Following it leads to the castellum, outside the north wall.
2. **City.** Gates to the south (cardo), east and west (decumanus), with a slab ramp. Streets of polished basalt
   (andesite) with sidewalks. Insulae with houses and shops; the governor's villa west of the forum, the baths to the east.
3. **Forum.** A square with porticoes on the sides, a hexastyle temple on a podium to the north, a central fountain, market
   stalls and the fountain house (SW) with the stairs to the **cistern**.
4. **Temple.** In the cella, next to the altar, the inscription with the clue to puzzle 1. Behind the altar, a trapdoor
   in the floor goes down to the **favissa** (a hidden room inside the podium, `oculto` chest).
5. **Baths.** Apodyterium, frigidarium, tepidarium and a caldarium raised over the hypocaust. From the praefurnium
   (furnace) an opening goes down to the **hypocaust** (hidden room, `oculto` chest).
6. **Castellum.** Ground floor with the distribution basin and three levers under the signs AQVA, IGNIS and TERRA; first floor
   with the office of the curator aquarum (`menor` chest); roof terrace with the tank and views.
   **Puzzle 1** opens the secret niche: a hidden staircase going down to the sewers.
7. **Sewers.** Entrance gallery with **trap 1** (tripwire and two arrow dispensers, like the jungle
   temple). Main collector with a water channel. **Spawner room** (two spawners) with a
   `cloaca` chest. A branch blocked by cobwebs leads to the **hidden lararium** (`oculto` chest). A shaft with a
   ladder and an iron grate that opens from below with a lever: a one-way exit to the north street.
8. **Antechamber.** A one-block corridor with **trap 2** (pressure plates flanked by dispensers, like the
   desert temple but without TNT) and a vestibule with the offering fountain: **puzzle 2**.
9. **Treasure chamber.** The guardian *Centurion Aquilio*, the `premium` chest on the altar and two `oculto` chests.
   A button next to the iron door opens it from inside (nobody gets locked in).

## Floor plans by level

The text plans with the reachable cells (`·` = walkable from the entrance; `o` = only with the puzzles
solved) are generated with the audit: `docs/unicas/acueducto/plano_*.txt`.

- **Underground -8 (sewers, feet at y = -8).** Secret staircase (x 73, z -6..3) → entrance gallery (x 72-74, z 4..11,
  trap 1 at z 8) → collector (z 12-14, x 60-90, channel at z 13) → spawner room (x 68-82, z 16-26) → antechamber
  corridor (x 79, z 27-31, trap 2) → vestibule (x 78-80, z 32-33) → iron door (79, z 34) → chamber
  (x 73-85, z 36-43, passage at z 35). Lararium: x 65-69, z 6-10, behind the cobweb passage (x 67, z 11). Exit shaft with a ladder at (79, z 20).
- **Underground -7 (cistern, feet at y = -7).** A 27 x 15 hall with 8 pillars, a perimeter walkway and a central cross, four
  pools 1 deep. A spawner on an islet in the center with the `cisterna` chest.
- **Floor 0 (city).** See the plan. A wall 5 high with battlements, towers at the corners, two collapsed stretches.
- **Castellum.** F0 (feet 1), F1 (feet 8), roof terrace (feet 15).
- **Temple.** Podium (feet 4), favissa inside the podium (feet 1).
- **Caldarium.** Raised floor (feet 4); hypocaust below (feet 1, 2 high).

## Puzzles (redstone; everything works as placed)

**Puzzle 1 — The castellum levers.** Three levers on the west wall of the hall (signs AQVA, IGNIS, TERRA).
Clue in the temple: *"Water and earth raise the city; fire consumes it"*. The niche only opens with
AQVA and TERRA down and IGNIS up.
Mechanism (inside the double wall x 75-76 and the hidden corridor x 73-74): two stacked sticky pistons (75, 1-2, -7)
facing north, **extended when placed** and holding the two blocks of the niche (75, 1-2, -9). They are
powered by a line of dust (x 74, z -5..1) that climbs a step (75, 1, -5) → (75, 2, -6) and reaches both
pistons (the lower one through the block under the dust, the upper one directly). Sources of the line: a redstone torch
behind AQVA, a torch behind TERRA (inverters: lit with the lever up) and the IGNIS lever
directly. The door stays closed while there is any source: open ⇔ AQVA ∧ ¬IGNIS ∧ TERRA. When the
power is removed the pistons retract and drag the blocks one step south: the niche is left open.
The placed state is already the stable one (torches lit, dust with its computed signal level, pistons extended
with their head), so it does not depend on any block update during generation.

**Puzzle 2 — The offering fountain.** Iron door (79, -8..-7, 34). In the wall, next to the upper leaf, a
1 x 1 niche at chest height with a wooden pressure plate (80, -7, 34). Sign: *"OBOLVM AQVIS — Give
your obol to the waters"*. No player fits in the niche: you have to throw an item (or an arrow) onto the plate.
The plate strongly powers the block below it (80, -8, 34), next to the lower leaf, and signals the upper leaf:
the door opens while something is on it. From inside, a button in the passage (79, -7, 35) opens the door.

**Exit from the sewers.** An iron trapdoor in the north street (79, 0, 20) over a shaft with a ladder. The
lever on the ceiling (80, -1, 20) powers the adjacent paving and opens the trapdoor; it cannot be opened from the street.

## Traps

- **Trap 1** (entrance gallery, z 8): a tripwire from side to side (x 72-74) with hooks in niches on both
  walls. Each hook strongly powers the block it is attached to and the dispenser above it (y -7, at
  head height) fires arrows through the niche.
- **Trap 2** (antechamber corridor): two stone pressure plates (z 29 and 31) in a one-block corridor; each
  plate has an arrow dispenser on each side, at foot height.

## Enemies

- Spawners: spider in the cistern; husk and skeleton in the spawner room.
- Final guardian: **Centurion Aquilio** (husk, `PersistenceRequired`): 60 health, 5 attack, 0.4 knockback
  resistance; gold helmet, iron chestplate, chainmail leggings, iron boots, iron sword and shield; the equipment does not
  drop (chance 0). A husk because the desert is its place and it does not burn in the sun if it goes out.
- No villagers or golems: the city has been abandoned for centuries.

## Chests and loot (vanilla only)

Each table has an extra pool with `solo_sin_lootr` (with Lootr each player opens their own chest and gets only the base).

| Table | Where | Contents |
|---|---|---|
| `menor` | houses, shops, castellum F1 (chests and barrels) | bread, dried fish, bones, string, paper, iron and gold nuggets, bricks, the odd emerald |
| `tienda` | tabernae and forum stalls | dye, wool, leather, bowls, emeralds, pots |
| `termas` / `villa` | baths and villa | gold and iron ingots, book, name tag, bottle o' enchanting |
| `cisterna`, `cloaca` | dungeons | bones, rotten flesh, iron, gold, redstone, arrows, healing potion |
| `oculto` | favissa, hypocaust, lararium, chamber (x2) | diamond (1-2), enchanted book, golden apple, *dune* armor trim template, gold amber |
| `premium` | treasure chamber | 90 %: *Prefect's Gladius* (named iron sword, Sharpness II), *Curator's Cup* (named gold block), discs (*relic*, *far*, *mall*), armor trim templates (*dune*, *coast*, *wild*), moderate books, emeralds. 10 %: enchanted diamond sword or chestplate (level 20-30), enchanted golden apple. No netherite or elytra. |

## Ruin (80-85 % in good condition)

The ruin is concentrated in places that make sense: collapsed roofs with rubble (brick slabs, sand,
suspicious sand with the desert temple's archaeology loot) in four houses, one house reduced to low walls,
two fallen stretches of wall, a toppled forum column, span 9-10 of the aqueduct collapsed and the last two
spans without their upper tier. The audit measures the built surface in plan and requires the damaged part to be between
15 and 20 %. The weathering processor only changes textures (cracked sandstone, mossy brick in the sewers).

## Against the owner's design criteria

- Complete staircases, no jumps; doors with an exit; no inaccessible room (the hidden ones have access).
- Furniture against the walls, high windows (y = 3) that nothing covers; center free except for tables.
- Lanterns hanging from the ceiling or on a chain; water always contained (pools with a curb, a closed channel).
- Symmetry in the temple, castellum, baths and forum; each element with its function (distribution basin, hypocaust, porticoes).
- Automatic audit before generation (see below).

## Its own audit (`tools/gen/uniques/aqueduct/audit.py`)

It runs in `build()` and any failure stops generation:
- Walk (`lint.walk`) over the complete structure assembled from the south gate: with the puzzles solved
  every door, chest, barrel, staircase, lever, button and the guardian are reached; with the puzzles
  unsolved the treasure chamber and the sewers are **not** reached (the puzzles really close).
- Nothing floating: every block is joined to the ground (y = 0 or underground) by neighboring blocks.
- Redstone simulator: truth table of puzzle 1 (8 combinations), placed state = stable state, traps,
  puzzle 2, the inner button and the sewer exit.
- Jigsaws intact and on the face of their box; the boxes of the pieces do not overlap and fit within the 116 radius.
- Ruin percentage between 15 and 20 %.

## Verification done

- `./gradlew build`: generates, validates against the 26.3 registries and audits (generic lint + its own audit) without warnings.
- Its own audit: 0 failures; ruin measured at 15.9 % (85 % in good condition).
- Real 26.3 dedicated server (`place template` and `place structure`): puzzle 1 closed when placed, open only with
  AQVA + TERRA, closed when adding IGNIS or with TERRA alone (levers set with `setblock` and a forced update on
  a neighboring block, because there is no player); trap 1 fires both dispensers when an armor stand crosses it;
  trap 2 fires with a zombie on top; an item thrown into the niche opens the iron door; the guardian is in
  the chamber; with the complete structure placed (rotated 180°), the 52 foundations of the 13 pillars have a block below.
- Not verified: the look in game (no screenshots from the owner), the behavior of `beard_box` on specific tall dunes
  and deep valleys, and the exit through the grate (only with the simulator).
