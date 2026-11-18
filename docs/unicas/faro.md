# Lighthouse with smugglers' cave (`heraldia:unicas/faro`)

A single variant, designed by hand. A white and red lighthouse on a rocky headland on the coast with the keeper's
house; under the headland, at sea level, a smugglers' cave with a hidden dock. It is entered on foot
through the house (secret passage) or by sea, through the mouth of the cave.

## Placement next to the sea (why Java is needed)

The jigsaw does not know where there is water and rotates the piece at random, so it can guarantee neither that there is sea nor that the mouth
of the cave faces it. A custom structure type is registered, `heraldia:faro`
(`io.github.albertosa23.heraldia.unicas.faro.FaroStructure`), which:

1. Looks on a 7 x 7 grid of points (every 8 blocks around the center of the cell) for those that fall in one of the structure's
   biomes (`#heraldia:unicas/faro`: stony shore and beach). If none does, it ends without querying heights:
   inland cells and map and `/locate` searches are cheap.
2. For each candidate and each of the 4 directions it queries the generation heightmaps
   (`OCEAN_FLOOR_WG` and `WORLD_SURFACE_WG`, cached): behind it there must be land between sea level + 4 and + 16;
   in front, 24-40 blocks away, water at least 3 deep; and across the whole footprint nothing higher than the top of the
   headland (so that the terrain does not cover the house).
3. It places the template rotated so the mouth of the cave faces the sea, centered on the chosen point and with the dock's
   water row at sea level (`sea_row`). Terrain adaptation `none`: the headland brings its own rock and
   above it the natural terrain is not touched.
4. With `/place structure` (the biome predicate accepts any) and no coast in sight, it is still placed at the
   center of the chunk, for testing.

Water: the whole inside of the cave is above sea level (the docks' floor is the water
row), so the sea cannot flood it; the channel's water is source blocks placed by the template, at sea level.

## Measurements

A 44 x 52 x 48 template (x, y, z), a single piece. y=8 is the water row (sea level - 1); the top of the
headland (grass) is at y=21 (13 blocks above the sea) and the lighthouse's lightning rod at y=51. The mouth faces +z (the
template's south) and the entrance on foot is at z=0.

## Floor plans by level (player's feet)

**Top, y=22.** A dirt path from the entrance (z=0) to the north door of the keeper's house (15 x 11, walls
of stone and spruce, a gable roof). Inside: bedroom (bed, chest), kitchen (smoker, furnace, a table with two chairs)
and study (bookshelf, lectern, cartography table); **`casa` chest**; a ladder to the cellar. To the south, a
covered corridor to the lighthouse.

**Lighthouse.** A 9 x 9 tower, white and red bands, a solid 5 x 5 core and a 17-step spiral staircase against
the walls, with windows to the sea. Watch room (y=39): lectern, **`faro` chest**, barrel, windows on all four sides.
A ladder to the lantern (y=44): glass all round, two lit copper bulbs (they need no
power), an outer gallery with a railing and corbels.

**Cellar, y=17** (under the house). Wine barrels (**`bodega` barrel**), a sign with the clue and an **iron
trapdoor** in the floor. **Puzzle 1:** the trapdoor opens with the lever hidden among the barrels (the lever
powers the floor block next to the trapdoor). Below, a ladder down to the cave.

**Cave, y=9** (sea level).
- A secret passage (1 wide) from the ladder to the corridor. **Trap 1** (like the jungle temple):
  a tripwire between two hooks; each hook fires the dispenser above it (crossed arrows at
  head height).
- An east-west corridor joining the northern rooms with the great grotto.
- The dock grotto: a 5-wide water channel to the mouth, spruce docks with bollards, crates and a **boat with a
  chest (`bote`)** moored.
- West storeroom: barrels and crates, **`almacen` chest**, a **skeleton spawner** at the back. Behind a stack of
  barrels there is a gap leading to the **stash grotto** (hidden room, **`oculto` chest**).
- East storeroom: **`almacen` chest**, a collapse in one corner, and in a niche a **decoy chest** with a pressure plate
  and TNT underneath (**trap 2**, like the desert temple).
- Dormitory: four bunks, a table, **`dormitorio` chest**.
- Dungeon: cells with bars (one broken), a **zombie spawner**, a **`calabozo` chest** in a cell.
- The captain's office: desk, chairs, lectern, map, **`despacho` chest**, bookshelves. **Puzzle 2:** three
  levers on the north wall and a sign ("Neither bow nor stern: the middle rules"). The iron door of the chamber only
  opens with the middle one up and the other two down. A circuit hidden behind the wall: levers A and C power
  a line of dust; B goes through an inverting torch; the line powers the block of a second torch, which
  is the one that opens the door. At rest (A up, B and C down) the door is closed.
- Treasure chamber (5 high): a **named guardian** ("Captain Bruma", a drowned with an iron sword and chainmail,
  40 health, `PersistenceRequired`, does not drop its equipment), the **premium chest** on a dais and two
  **`tesoro` barrels**.

Route: house → cellar (puzzle 1) → passage (trap 1) → corridor → northern rooms and grotto → storerooms (spawner,
hidden room, trap 2) → office (puzzle 2) → chamber (guardian, premium). By sea you reach the grotto without going through
the house, but the office and the chamber only open with the puzzles.

## Ruin (80-85 % in good condition)

Processor: 10 % of the stone bricks cracked and 8 % mossy; 15 % of the cobblestone mossy. Gaps that make
sense: two broken panes in the house, a gap in the gallery railing on the sea side, a collapse of gravel and
cobblestone in the east storeroom, broken bars in a cell and cobwebs in the dungeon. The audit estimates the percentage
of altered surface and requires it to be between 15 and 20 %.

Villagers or golems: none. The lighthouse is abandoned and the cave taken over by the gang's dead; a villager would only
make sense if the lighthouse were still in use.

## Loot (vanilla only; each chest with its extra `solo_sin_lootr` pool)

| Table | Where | Contents |
|---|---|---|
| `casa` | house | food, candles, paper, string; a rare compass |
| `faro` | watch room | spyglass, compass, empty map, paper, glow ink, lantern, iron ingots |
| `bodega` | cellar | bread, apples, honey bottles, berries, cod |
| `almacen` | storerooms | leather, wool, string, gunpowder, sugar, iron ingots, gold nuggets, a few emeralds |
| `senuelo` | decoy (trap) | bones, rotten flesh, string, gunpowder |
| `dormitorio` | dormitory | food, gold nuggets, worn leather armor, book, a rare clock |
| `calabozo` | dungeon | bones, iron nuggets, chains, lead, a rare name tag |
| `despacho` | office | map, compass, gold ingots, emeralds, enchanted book (20 %), bottles o' enchanting |
| `oculto` | stash grotto | gold, emeralds, diamond (15 %), an enchanted iron piece (5-15), golden apple (10 %) |
| `bote` | chest boat | gunpowder, emeralds, salmon, nautilus shell, heart of the sea (5 %) |
| `tesoro` | chamber | gold nuggets and ingots, raw gold, emeralds |
| `premium` | chamber | 90 %: named items (the captain's saber, spyglass, compass), *coast* trim template, disc, enchanted book, golden apple; 10 %: an enchanted diamond sword (20-30), a trident, an enchanted golden apple or 3-5 diamonds |

No netherite gear or elytra.

## Verified on the server

`/locate structure heraldia:unicas/faro` found one with the test seed and natural generation placed it;
guardian and boat present, water in front of the mouth and air inside the grotto. Puzzle 1 opens the trapdoor; puzzle 2 only
opens the door with (A, B, C) = (down, up, down) among the five combinations tried. Plans and renders:
`docs/unicas/faro/`. The visual look has not been validated with screenshots from the game.

## Against the design criteria

- Complete staircases without jumps: a spiral of steps; the ladders end on a floor (the open trapdoor
  over the ladder counts as a step, just like in the game).
- Doors with an exit and nothing inaccessible: checked by the walk with the puzzles solved.
- Furniture against the walls, center free except for tables with chairs; lanterns hanging from chains or the ceiling.
- Symmetry in the lighthouse and the house; the cave natural and irregular except for the built rooms.
- Every element with a function: bollards, crates on the dock, bunks, cells, the treasure dais.

## The module's own checks

`tools/gen/uniques/lighthouse/checks.py` (they run when building and fail generation):
- Walk with the puzzles solved (the open state declared by the template, which `lint.py` also uses).
- Redstone simulation of the two puzzles and the traps: a rest state consistent with what is placed (nothing depends on
  an update that does not happen during generation) and the door only opens with the correct combination (8 combinations).
- Watertight cave: no air cell of the inside below the top touches the outside except the mouth.
- Percentage of altered surface between 15 and 20 %.
