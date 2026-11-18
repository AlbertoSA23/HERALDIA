# Eastern palace (`heraldia:unicas/palacio`)

An imperial palace of eastern inspiration, walled, with three successive courtyards on a strictly
symmetric north-south axis. A single variant, designed by hand (`tools/gen/unicas/palacio/`), in a single rigid piece of 81 × 123 blocks.

- Biomes: `minecraft:cherry_grove` and `minecraft:bamboo_jungle` (the normal and sparse jungles belong to the pyramid temple).
- Rarity: `spacing` 250 / `separation` 190 chunks (one every ~3,000-5,000 blocks).
- Adaptation: `beard_box`. The whole palace rests on a stone plinth (y=0) and **has no basements below the terrain**:
  the "secret chamber under the throne hall" is inside the three-tier stepped platform (y=1-7),
  above the ground. That way the piece's box starts at the plinth, the terrain is filled underneath and nothing sinks the
  surroundings. The inner volume is filled with air so that a hillside does not poke into the courtyards.
- Difference from the "cherry" villages: there, loose cherry wood houses with pagoda roofs on towers; here a single
  ceremonial compound of red walls, marble terraces (quartz), imperial yellow roofs (bamboo mosaic) on the
  axis and green glazed ones (prismarine) on the secondary buildings, with a pond, a moon gate and a five-story pagoda.

## Floor plans (template coordinates: x east, z south from the gate, y=1 paving, feet at y=2)

| Area | Footprint | Notes |
|---|---|---|
| Steps and wall | z=0-4, a wall 3 thick around the whole perimeter, y=2-10 | stone brick plinth, red body, yellow coping |
| Meridian Gate | x=32-48, z=2-8, block y=1-9 | a 3 × 4 passage, two guardrooms with a ladder to the upper pavilion (y=10) |
| Outer courtyard | z=5-27 | a river of golden water (z=15-17) with three arched bridges, cherry trees, stone lanterns |
| Gate of Harmony | wall z=28-30, hall x=28-52, z=26-32 on a plinth | a central passage with columns; a guardroom (west) and a pantry (east) |
| Throne courtyard | z=31-79 | library (west, x=4-17) and treasury (east, x=63-76), symmetric from outside |
| Throne platform | tiers x=22-58/24-56/26-54, z=36-76/38-74/40-72; feet 4, 6 and 8 | flights of steps on the axis (in front and behind) |
| Throne hall | x=29-51, z=44-66, feet 8, double eaves | a throne on a dais, a screen, a back corridor, a back wall 3 thick |
| Under the hall (inside the platform) | x=28-52, z=42-70, feet 2-5 | antechamber, trap corridor, hall of the warriors, treasure chamber |
| Garden wall | z=80-82 | a moon gate (a circle of radius 3) on the axis and two wickets |
| Garden | z=83-119 | a pond (x=27-53, z=88-102) with a bridge and the lake pavilion; pagoda (x=35-45, z=106-116), four concubines' pavilions (x=4-16 and x=64-76) |

## Player route
1. Steps → Meridian Gate. Guardrooms on both sides of the passage (a `guardia` chest in each); ladders to the gate's pavilion (`torre` barrel).
2. Outer courtyard: bridges over the river; the breach in the northeast corner is the ruined part.
3. Gate of Harmony: guardroom (`guardia` chest) and pantry (`almacen` barrels).
4. Throne courtyard: library (`biblioteca` chest, secret study) and treasury (`tesoreria_menor` barrels, a vault with an iron door and a button, the trapped `tesoreria` chest). Steps up to the throne hall (`salon` chest in the back corridor).
5. Behind the screen, two twin columns with a lever: one opens the secret door, the other fires an arrow. The door leads to a shaft with a ladder that goes down into the platform.
6. Antechamber → trap corridor (two tripwires with facing dispensers) → hall of the terracotta warriors (two spawners, in the dark) → a two-lever lock → **treasure chamber** under the throne: a named guardian, the `premium` chest and two `boveda` chests.
7. Moon gate → garden: the lake pavilion (`jardin` barrel), the four concubines' pavilions (a `pabellon` chest in each; the southeast one in ruins), a five-story pagoda with ladders and the `pagoda` chest at the top.

## Puzzles (everything placed in a stable state: nothing waits for a block update)
- **Secret study of the library**: a wall of bookshelves to the north with a two-block door moved by two sticky
  pistons hidden behind a column of bookshelves. Closed = pistons extended and powered by a lever that is
  on, on the face of the column (the column's block strongly powered → the upper piston directly, the lower one by
  quasi-connectivity). Turning the lever off opens it; turning it on closes it.
- **Secret door behind the throne**: the same mechanism in the back wall, hidden behind the left column. The right
  column, its twin, has a decoy lever (off) whose block powers a dispenser with arrows at the foot of the column.
- **Lock of the chamber**: the two-block door is moved by two independent pistons (the lower block towards the
  west and the upper one towards the east), each with its lever; it only opens with both off.

## Traps
- Trap corridor (under the hall): two tripwires; each hook strongly powers the wall it rests on and
  that block activates a dispenser at head height that fires across the wire (as in the jungle temple).
- The treasury vault: a pressure plate in front of the trapped chest, with two dispensers at floor level on
  its sides that fire over the plate.
- The decoy lever of the throne hall (above).

## Enemies
- Hall of the warriors: two spawners (zombie and skeleton), unlit.
- Treasure chamber: the guardian "Commander of the Imperial Guard" (a vindicator with an iron axe and a chainmail
  cuirass, 40 health, `PersistenceRequired`, does not drop its equipment).

## Condition (80-85 % in good condition)
Ruin that makes sense: a breach in the northeast corner of the wall with rubble, coping fallen on the east wall of the
garden, the southeast concubines' pavilion half collapsed (roof and wall open, rubble, moss), a knocked-down stone
lantern and loose tiles on the Gate of Harmony. In addition a processor randomly weathers the stone (cracked
and mossy brick, andesite). The module's audit measures the exposed surface and requires 15-20 % ruin.

## Loot (`heraldia:unicas/palacio/<table>`; each chest's extra pool is marked `solo_sin_lootr`)
| Table | Where | Contents |
|---|---|---|
| `guardia` | 3 chests in guardrooms | food, arrows, torches, iron nuggets; extra: iron ingot, emerald |
| `almacen`, `torre`, `jardin` | barrels | food, string, candles, paper; little value |
| `pabellon` | 4 pavilions | dyes, candles, petals, amethyst shards, gold nuggets, emeralds |
| `biblioteca` | library | paper, books, ink, feathers, map; rare: an enchanted book |
| `tesoreria_menor` | 2 treasury barrels | gold and iron nuggets, copper, the odd emerald |
| `salon` | throne hall corridor | candles, gold, emeralds, golden carrots, spyglass |
| `tesoreria` | the vault's trapped chest | gold ingots, emeralds, raw gold; a diamond unlikely |
| `biblioteca_secreta` | secret study | enchanted books (levels 10-20), bottles o' enchanting, lapis lazuli |
| `pagoda` | top floor of the pagoda | ender pearls, amethyst, enchanted book, golden apple |
| `boveda` | 2 chests in the chamber | diamonds (1-3), gold, emeralds, enchanted iron gear |
| `premium` | the chamber's chest | a jewel: 90 % showy (named gold and iron items with enchantments 15-30) and 10 % strong (enchanted diamond, enchanted golden apple, totem); armor trims, discs, riches |

No netherite gear, netherite upgrade template or elytra.

## Against the design criteria
- Axial symmetry in the wall, gates, courtyards, platform, hall, library/treasury (identical from outside), pavilions and pagoda; the only asymmetries are the hidden mechanisms and the ruin.
- No unfinished staircase: continuous flights of one block per step; ladders always reach a floor.
- Furniture against the walls, centers free; lanterns hanging on chains or standing on stone; water always in closed basins.
- Every room has a recognizable function (guardroom, pantry, library, study, treasury, vault, hall, quarters, pagoda).
- Audit as a condition for generating: `lint.py` (with the mechanisms in the open state) plus the module's checks (redstone, walk with everything closed, nothing floating, ruin percentage).
