# Dwarven citadel (`heraldia:unicas/ciudadela`)

A city carved inside a mountain. A single variant, designed by hand. Module: `tools/gen/uniques/citadel/`
(geometry in `blueprint.py`, loot in `chest_loot.py`, redstone in `redstone.py`, its own audit in `audit.py`);
placement in Java: `io.github.albertosa23.heraldia.unicas.ciudadela`.

## Placement on the hillside (why Java)
- The jigsaw chooses the rotation at random and does not know which way the hillside goes down; `bury` and `beard_box` bury or empty
  the whole box, including the gate (the ancient city and the trial chambers are entirely underground and have
  no façade). That is why the citadel uses a custom structure type, `heraldia:ciudadela`, with
  `terrain_adaptation: none`.
- The template is a single piece (`PoolElementStructurePiece` from a one-element pool, with its processors).
  Outside the rooms it only has `structure_void`: the natural rock is kept. Each room has its own skin of
  two blocks (deepslate brick inside, stone outside) so that a cave or an aquifer cannot
  cut through it; the outer stone blends with the mountain and admits ores.
- The Java type tries 4 rotations x 25 positions (a 16-block grid around the chunk) and measures the terrain
  with the generation heightmap:
  - in front of the gate (5 points 2 blocks from the portico): almost flat terrain (difference <= 5) and no water;
    the gate is placed at the median height of those points;
  - further out (3 points 10 blocks away): it does not rise more than 3 (the gate does not face a wall);
  - above the city: a grid of ceilings (every 8 blocks, the template's maximum height in that column,
    without the portico) that the generator writes into the JSON; rock is required up to the ceiling minus 1 in 75 % of the
    cells.
  It keeps the best option; if none qualifies, nothing is generated in that grid cell. With `/place`
  (which accepts any biome) it is placed at the best option even if it does not qualify, so it can be tested.
- The point checked against the biome is the center of the city at the height of the gate (under the mountain),
  not the gate, which may fall in the biome at the foot of the hillside.
- Biomes: `stony_peaks` and `jagged_peaks`. Step `underground_structures`. Rarity: `spacing` 250 / `separation`
  190 chunks (one every ~4,000 blocks on the grid; fewer in practice, because it requires the biome and a hillside).

## Levels (design coordinates: x towards the east, z into the mountain; the gate faces north, z=0)
Floor of each level (the player stands at floor+1):

| Level | Floor | Rooms |
|---|---|---|
| L0 | y=30 (throne y=33) | portico, hall of columns, barracks, vestibule, storehouse, throne hall, hidden royal chamber |
| L1 | y=21 | landing, forges, corridor, brewery |
| Cellar | y=15 | the brewer's hidden cellar |
| L2 | y=12 | minecart station, west tunnel, spider den, sunken gallery and the miner's hideout, chasm with a bridge, chasm landing, trap corridor |
| L3 | y=3 | lock antechamber, treasure vault |

### L0
- **Portico** (x 25-45, z 0-7): a carved terrace 14 high with two statues of dwarven guardians and braziers.
  A stone foundation below so that it is not left in the air if the hillside drops.
- **Great gate** (z 8-10): a 5 x 7 arch in a 3-thick façade.
- **Hall of columns** (x 18-52, z 11-44, 12 high): two rows of 5 basalt pillars with capitals,
  a central tiled aisle with gold inlays, lanterns hanging on chains, benches along the walls.
  Ruin: a collapsed pillar with rubble.
- **Barracks** (west): bunks (beds), armor stands, a weapon rack, a table with benches, 2 smaller chests.
  Ruin: a corner of the ceiling caved in with rubble and cobwebs.
- **Vestibule and storehouse** (east): the main staircase to L1. A storehouse with rows of barrels (storehouse loot).
  **Hidden room 1**: behind the last row, a one-block gap next to the wall leads to a room with a hidden chest.
- **Throne hall** (x 24-46, z 46-64, floor 33): three steps up from the hall, a dais with a gold throne,
  a carpet, banners, braziers. The back wall has niches between pilasters.
  **Puzzle 1 (secret piston door)**: two low niches with a lever on each side of the central niche.
  The left one (down) keeps two sticky pistons hidden behind the pilaster extended; when it is raised,
  the pistons pull back the two blocks at the back of the central niche and the way to the
  **royal chamber (hidden room 2)** opens: a bed, a table and the royal chest. The right lever is a decoy.

### L1
- **Staircase** from the vestibule (9 steps) to the landing.
- **Forges** (x 36-64, z 49-70, 9 high): four furnaces with a blackstone hood and a crucible of contained lava
  (lava enclosed on every side), blast furnaces, anvils, smithing tables, grindstones, lava cauldrons,
  2 forge chests. Ruin: a cold crucible (magma) and damaged anvils.
- **Brewery** (x 8-25, z 46-64): giant wooden vats, barrels, water cauldrons, brewing stands,
  a long table with chairs, 2 brewery chests. **Hidden room 3**: a closed trapdoor in a dark corner between
  two vats; a ladder down to the brewer's cellar (hidden chest).
- **Staircase** from the forges (9 steps) to the mine station.

### L2
- **Station** (x 30-46, z 26-39): tracks, minecarts (one with a mine chest), wooden props.
- **West tunnel** with a track and wooden frames every 4 blocks to the **spider den**: a vein with ores,
  cobwebs, a **cave spider spawner** and a minecart with a mine chest.
- **Sunken gallery** (north branch): a partial collapse with a one-block passage between rubble and cobwebs.
  **Trap 1 (plate with TNT, like the desert temple)**: a stone plate with TNT two blocks below, away from
  the chests. Behind it, the **miner's hideout (hidden room 4)** with a hidden chest.
- **Chasm** (x 48-58, z 20-56): a 15-deep chasm with lava at the bottom. A 3-wide **bridge** with railings
  and chains to the ceiling. Ruin: a fallen stretch of railing and cracked slabs.
- **Chasm landing**: **skeleton spawner** (dark area).
- **Trap corridor**. **Trap 2 (tripwire with dispensers, like the jungle temple)**: a wire between
  two hooks and four arrow dispensers in the walls.
- **Staircase** of 9 steps down to L3.

### L3
- **Antechamber**: **zombie spawner** (dark). **Puzzle 2 (combination lock)**: four levers on
  the wall, two over gold and two over slate. The vault's iron door only opens with the two gold ones
  up and the two slate ones down (door = A and B and not C and not D, with torch inverters behind the wall).
- **Treasure vault** (x 59-69, z 69-80): a 4-long passage through the thick wall, piles of gold, 2 vault chests
  on the sides and the **premium chest** on a dais at the back. **Guardian**: Borin Ironbeard (a named vindicator,
  60 health, iron axe, iron helmet and chestplate, `PersistenceRequired`).

## Player route
Portico → hall of columns (barracks to the west, storehouse and hidden room 1 to the east, throne and hidden room 2 to the
north) → vestibule → stairs → forges (brewery and hidden room 3 to the west) → stairs → station → west tunnel
(den) and sunken gallery (trap 1, hidden room 4) → bridge over the chasm → landing → trap 2 corridor →
stairs → antechamber (puzzle 2) → vault.

## Chests and loot (`heraldia:unicas/ciudadela/<table>`; each table has an extra `solo_sin_lootr` pool)
| Table | Where | Contents |
|---|---|---|
| `menor` | hall, vestibule, station | food, torches, coal, nuggets, string; extra: iron ingot, gold nuggets, emerald |
| `barracones` | 2 in the barracks | arrows, worn bow and iron sword, shield, chainmail; extra: enchanted helmet (5-10), crossbow |
| `almacen` | storehouse barrels | coal, torches, rails, leather, arrows, nuggets; extra: iron ingots |
| `forja` | 2 in the forges | iron ingots, coal, gold, iron tools, bucket, shield; extra: diamond (rare), enchanted chestplate |
| `cerveceria` | 2 in the brewery | wheat, bread, sugar, honey, bottles, berries, mushrooms; extra: golden carrot, emeralds |
| `mina` | chest minecarts | raw iron and gold, coal, lapis lazuli, redstone, rails, worn pickaxe; extra: diamond (rare), golden apple |
| `oculto` | hidden rooms 1, 3 and 4 | gold ingots, emeralds, diamonds (few), enchanted book, golden apple, bottles o' enchanting; extra: diamonds, book (10-20) |
| `real` | royal chamber | diamonds, emeralds, a crown (named gold helmet, Protection II), book (15-25), disc, trim template; extra: golden apple, gold |
| `boveda` | 2 in the vault | gold ingots and block, raw gold, emeralds, diamonds, golden apple; extra: diamonds, book |
| `premium` | final chamber | 90 %: named items (Borin's axe, the king's helm, the jug of the last beer), discs, trim templates (shaper, host, wayfinder), gold; 10 %: a named diamond pickaxe (Efficiency III, Unbreaking II), a diamond chestplate (Protection II), an enchanted golden apple, a Fortune III book |

No netherite gear or elytra; vanilla items only.

## Spawners, traps and puzzles
- Spawners (3, in unlit areas): cave spiders (den), skeletons (chasm landing), zombies (antechamber).
- A named final guardian in the vault.
- Traps: plate with TNT (sunken gallery), tripwire with 4 arrow dispensers (corridor).
- Puzzles: a piston door with a hidden lever and a decoy (throne); a 4-lever lock (vault).
- All the redstone is placed in a stable state: the audit (`redstone.py`) recomputes like the game the
  connections of each wire and the signal of each torch, piston, door, dispenser and TNT, checks that the
  placed state matches the computed one (nothing depends on an update that does not happen during generation) and
  simulates the solution: the piston door opens when the correct lever is raised and not with the decoy; the
  vault's opens with the correct combination and with none of the other 15.

## Condition
- 80-85 % in good condition: a degradation processor (cracked brick and tile, polished to cobblestone) and
  hand-made ruins that make sense (fallen pillar, caved-in ceiling in the barracks, collapsed gallery, cold crucible,
  fallen railing). The audit measures the share of the visible surface that is degraded and requires 15-20 %.
- No villagers or golems: it is an abandoned city; only the guardian remains.

## Against the owner's criteria
- Complete staircases (9 steps per level, no jumps); no door without an exit: the audit walks
  from the entrance to every door, chest, barrel, lever, spawner and ladder.
- Furniture against the walls; the center of the rooms free except for tables with chairs.
- Nothing floating: lanterns on chains, contained lava, no loose water (only in cauldrons).
- Symmetry in the portico, the hall and the throne; asymmetry only where it has a function (storehouse, mines).
- Plans by level with reachable cells and renders: `docs/unicas/ciudadela/`.
