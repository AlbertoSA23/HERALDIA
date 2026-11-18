# Observatory (`heraldia:unicas/observatorio`)

An abandoned astronomical observatory on a windswept summit. A single variant, designed by hand in
`tools/gen/unicas/observatorio.py`. Floor plans and renders in `docs/unicas/observatorio/`.

## Placement
- Biomes: `windswept_hills`, `windswept_gravelly_hills`, `windswept_savanna` (windswept hills, windswept
  gravelly hills and windswept savanna; no other unique structure uses them).
- Default grid: `spacing` 250 / `separation` 190 chunks (one every ~3,000-5,000 blocks).
- Two rigid pieces joined by a vertical jigsaw: **surface** (ground floor, upper floor, roof terrace and
  dome; 41 × 35 × 23) and **underground** (archive and treasure chamber). `beard_thin` adaptation: the terrain
  is leveled around the base of the surface piece. The underground part is a separate piece so that its
  box does not sink the terrain (the `beard_thin` correction only acts within ±12 blocks of the base of each
  piece and at that depth the terrain is solid); its rooms are wrapped in their own rock (two blocks) and
  blocks are only placed where there are rooms, so no stone cube appears on the hillside.

## Coordinates
x grows towards the east, z towards the south, y = 0 is the ground floor slab (you stand at y = 1).
The entrance is to the north (z = 0). A rotunda centered on (20, 20), radius 9.

## Floor plans
### Ground floor (y 1-5)
| Room | Area | Contents |
|---|---|---|
| Path and steps | x 18-22, z 0-5 | Paving, street lamps on pillars |
| Vestibule | x 12-28, z 7-10 | Benches, lanterns; doors to the library, workshop and planetarium |
| Planetarium (rotunda) | r < 8.5 | A mechanical planetarium hanging from the ceiling (a glowstone sun and copper planets on chains), a starry ceiling, cartography tables and lecterns along the wall |
| The astronomers' library | x 2-10, z 7-19 | Bookshelves between windows, lecterns under the windows, a reading table with chairs; **a carpet with a hidden trapdoor** (hidden room 1) |
| Optics workshop | x 30-38, z 7-19 | Stained glass windows, furnaces, a crafting table, a grindstone, a cauldron, glass on display; smaller chest |
| Archive anteroom | x 2-10, z 21-33 | A storeroom with barrels; stairs going down to the archive; smaller chest |
| East staircase | x 30-38, z 21-33 | Flights to the upper floor and the roof terrace |
| South gallery | x 12-28, z 31-33 | Joins the two wings and enters the planetarium from the south |

### Upper floor (y 7-11)
| Room | Area | Contents |
|---|---|---|
| Telescope room | r < 8.5, open to the dome | A large copper telescope on a pedestal pointing at the dome's north slit; smaller chest |
| North gallery | x 12-28, z 7-10 | Spyglasses on tripods next to the windows |
| The astronomers' dormitory | x 2-10, z 7-19 | 4 beds against the west wall (not covering windows), nightstands, smaller chest |
| Dining room | x 2-10, z 21-33 | A table with chairs (facing outwards), smoker, barrels |
| The head astronomer's study | x 30-38, z 7-19 | Desk, bookshelves, cartography table, smaller chest |
| Upper south gallery and landing | x 12-38, z 21-33 | Connects with the east staircase |

### Roof terrace (y 13)
A stone wall parapet, a **sundial** over the west wing (a smooth stone dial, a gnomon and hour
marks with daylight detectors), spyglasses on tripods over the east wing, a weathered copper dome in the
center with an observation slit to the north.

### Archive (underground, y −6 to −2)
| Room | Area | Contents |
|---|---|---|
| Stair landing | x 4-8, z 29-33 | The end of the staircase from the anteroom |
| Wire corridor | x 9-13, z 30-33 | **Trap 1**: a tripwire with two arrow dispensers (like the jungle temple) |
| Archive | x 14-26, z 20-33 | Bookshelves in aisles, **2 spawners** (zombie and spider) in the dark, 2 archive chests, cobwebs. The **phases puzzle** on the east wall. **Hidden room 2** behind the bookshelf of the north wall |
| The librarian's cabinet (hidden room 1) | x 3-9, z 12-17 | Reached only through the trapdoor under the library's carpet; hidden chest |
| Instrument cabinet (hidden room 2) | x 17-23, z 13-16 | A piston door behind the niche's bookshelf; a lever next to the niche; hidden chest |

### Treasure chamber (underground, y −13 to −9)
| Room | Area | Contents |
|---|---|---|
| Staircase | x 28, z 15-21 | Behind the puzzle's iron door |
| Chamber of hours | x 25-31, z 7-14 | Daylight detectors and stone clocks; archive barrel |
| Plates corridor | x 18-24, z 10 | **Trap 2**: pressure plates with arrow dispensers on both sides |
| Guardian's hall | x 8-17, z 5-15 | Columns, **1 spawner** (skeleton) and the **guardian** |
| Treasure chamber | x 2-6, z 8-12 | An iron door with buttons; **premium chest** |

## Player route
Entrance → vestibule → library, workshop and planetarium (smaller chests in sight) → east staircase →
upper floor (dormitory, dining room, study, telescope) → roof terrace (sundial, the puzzle's clue) →
back down, anteroom → archive (wire trap, spawners) → hidden rooms → phases puzzle →
chamber of hours → plates corridor (trap) → guardian → premium chest.
The audit checks the complete route on foot in the "solved" state (lever and puzzle operated,
trapdoor open).

## Phases puzzle
Four levers on the east wall of the archive, each under a moon phase glyph: new moon (coal
block), waxing, full (pearlescent froglight) and waning. The iron door only opens with **new moon and
full moon** up and the two crescents down. Clue: the planetarium's floor and the sundial's dial
mark those two phases with the same blocks.
Circuit (everything at rest and consistent when placed, without depending on updates):
- "Good" phase levers → block → redstone torch (NOT) → OR line.
- "Bad" levers → block → dust → OR line.
- OR line → (the last dust comes in from the side of the support) → block → output torch (NOT) next to the door's upper
  leaf. If the dust went on top of that block, the lit torch would power the block above and
  that one the dust: a redstone clock and a burnt-out torch (a real bug found in the server test).
- At rest the OR line is powered by the two lit torches, with the power computed on
  each dust; the output torch is off and the door closed. The audit simulates the circuit
  for the 16 combinations and requires only one to open.

## Hidden room 2: piston door
Two extended sticky pistons (powered by a redstone torch and quasi-connectivity)
hold two bookshelves at the back of a niche. The lever next to the niche turns off the torch: the pistons
retract, pull the bookshelves and open the way. The audit checks the circuit's geometry.

## Traps
1. A tripwire in the archive corridor: the hooks power the block they are attached to and that one
   activates an arrow dispenser above each hook, at chest height.
2. Stone pressure plates in the plates corridor: each plate activates the dispensers it has
   on each side.

## Enemies
- Spawners: zombie and spider in the archive, skeleton in the guardian's hall (unlit areas).
- Guardian: a skeleton, "Keeper of the Stars" (`PersistenceRequired`), 40 health, a bow with Power II,
  a gold helmet and chainmail; a low chance of dropping its equipment.
- No villagers or golems: the observatory is abandoned and infested.

## Loot (vanilla only; `solo_sin_lootr` in each chest's extra pool)
| Table | Chests | Contents |
|---|---|---|
| `menor` | 7 at the surface | Paper, books, candles, food, coal, copper, glass, amethyst shards; sometimes a compass, clock or spyglass |
| `archivo` | 3 underground | Books, maps, lapis lazuli, gold, bottles o' enchanting, a random enchanted book, name tag |
| `oculto` | 2 hidden rooms | Emeralds, diamond (1-2), enchanted book (10-20), golden apple, spyglass, globe banner |
| `premium` | 1, final chamber | 90 % showy: a named spyglass, clock and compass, a named iron helmet with a moderate enchantment, *wayfinder* and *shaper* trims, the *far* or *mall* disc, a globe banner, gold and amethyst. 10 %: diamonds, an enchanted book 25-30 or a diamond chestplate enchanted 15-25. No netherite or elytra |

## Condition (80-85 % in good condition)
- Processor on the surface piece: stone brick → cracked (14 %) or, of the rest, mossy (9 %). Underground: cracked deepslate brick and tile and some andesite in the rock.
- Ruin designed to make sense: copper panels fallen in the southeast of the dome (with rubble on the
  telescope floor, not hanging), the northeast corner of the parapet collapsed with debris on the roof terrace,
  broken windows on the west and east façades, a fallen stretch of the south parapet, cobwebs underground.
- The audit computes the damaged fraction of the outer envelope (blocks visible from outside) and requires
  it to be between 15 and 20 % (result: 84.0 % in good condition over 2,976 visible blocks).

## Against the owner's criteria
- Complete staircases without jumps; every door with an exit; no inaccessible room (walk audit).
- Furniture against the wall, not covering windows; center free except for tables with chairs facing outwards.
- Lanterns hanging on chains up to the ceiling; the mechanical planetarium hangs from chains; rubble on the floor.
- Symmetry in the façade, the rotunda and the wings; every element has a function (telescope, sundial,
  spyglasses, workshop stained glass, archive).

## Checks
- Built with `_comun/piezas.py` (doors, spawners, guardian, tripwire and plate traps, connections),
  loot with `_comun/botin.py`, the circuit with `_comun/redstone.py` and the walk with a basement with `_comun/recorrido.py`.
- `build(reg)` audits the complete template before splitting it and any warning stops generation: supports
  (`lint.support_issues`), the walk in the solved state (doors, chests, barrels, levers, buttons,
  ladders and every step of the flights), hidden rooms unreachable without solving, circuit simulation
  with `redstone.check_static` and `check_puzzle` (16 combinations; the placed state stable), the piston door,
  nothing floating (every block joined to the rest) and the exterior condition between 80 and 85 %.
- `tools/smoke/observatorio_smoke.py`: on a 26.3 dedicated server it places the underground part and checks the rest state, puzzle,
  pistons, traps, treasure chamber and guardian, and that `/place structure` also places the underground part.
- Not checked: the look in game (missing screenshots from the owner) or the natural placement in the biomes.
