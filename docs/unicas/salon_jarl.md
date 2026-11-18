# Jarl's Hall (`heraldia:unicas/salon_jarl`)

A fortified Norse settlement in a taiga clearing: a log palisade with a wall-walk and four towers
encloses the longhouse of jarl Ulfgrim and the workshops of his people. Under the longhouse is the barrow of the kings of the
hall, where the jarl, who swore never to let go of Ysolda's leaf, still stands: the **Unburied**.

It is an original structure: it does not copy any settlement from another game or mod. It differs from the taiga
family's village (a Norse longhouse style) in that it is a closed, defended compound, with a single very large
longhouse, specialized workshops, ruin and an underground part with puzzles, traps, spawners and a guardian.

## Biome and placement

- Biomes: taiga, old growth pine taiga and old growth spruce taiga (vanilla list, without `#c:` tags: `#c:is_taiga`
  adds the snowy taiga, which belongs to the ice fortress; `biomes.check` checks it).
- Rarity: `spacing` 250 / `separation` 190 chunks (one every ~3,000-5,000 blocks), configurable in
  `config/heraldia.json` like the others (`unicas.salon_jarl.activada`, `unicas.salon_jarl.separacion_bloques`).
- Two rigid pieces joined by a vertical jigsaw under the longhouse (`down_north` → `up_north`, same rotation):
  - `salon` (74 × 18 × 74): the compound, longhouse and workshops; its y = 0 layer is the ground (feet go at y = 1).
  - `tumulo` (49 × 15 × 42): everything below y = 0. **It fills its whole box**: dirt in the top two
    layers, stone below, and a lining of cut stone (cobblestone, stone brick or wood) on every face that faces
    air, so that no springs or lichen appear inside.
- `beard_thin` adaptation: the terrain adjusts to the base of the compound (y = 0) and the barrow stays at its depth, without a
  crater (see "Basements without a crater" in `docs/LESSONS.md`). In the old growth taiga, with slopes and boulders, the
  clearing is leveled under the palisade; inside there is explicit air up to 6 blocks above the yard so that no hillside
  pokes out between the houses.
- The yard's floor: dirt path, gravel and packed mud. There is no grass, dirt, podzol or natural stone in sight
  in the compound, so the taiga's decoration (spruces, ferns, mossy stone boulders) does not spawn inside.
- No shed by the water: the jigsaw does not detect rivers or lakes (it would take Java, like the lighthouse or the galleon). Instead,
  the **shipyard** holds a half-built longship on its slipway, on dry land.

## Surface (feet at y = 1)

Coordinates: x from west to east (0..73), z from north to south (0..73); the gate is to the north (z = 0).

- A **palisade** of spruce logs 6-7 high with alternating points, and a plank **wall-walk** (feet at 5) along
  the inside of the whole perimeter, on uprights.
- **Four towers** of 7 × 7 at the corners: a ground floor with a door to the yard, a room at the height of the wall-walk (with exits to
  both stretches of wall), an open lookout (feet at 10) and a hipped roof; reached by a ladder. Arrow slits on
  the outer faces. The northwest one holds a chest in the lookout; the northeast one has its roof caved in.
- **Gate** (x 32..41): a 4-wide tunnel with log jambs, tapestries and lanterns, and above it the guardroom
  (chest and barrel), with exits to the wall-walk on both sides and a gable roof.
- **Longhouse** (x 28..45, z 22..58): walls of logs laid between posts, a cobblestone plinth and a dark oak
  gable roof (ridge at y = 16) with a smoke hole over the hearth. Inside: two rows of uprights with
  tie beams, a **long hearth** with campfires, two **long tables** with benches (facing outwards) and passages between
  them, beds, a loom, chests and barrels in the side aisles, red and black tapestries, and at the back the **dais** with
  **two high-backed thrones**. A double door to the north and side doors to the shipyard and the warriors' houses.
  In the west aisle, the **staircase to the barrow** (7 steps, with a railing).
- **The jarl's alcove** (hidden room, x 32..41, z 58..63): attached to the south gable, with no door to the outside. It is entered from
  behind the dais's **black tapestry** (to the left of the thrones): a 1 × 2 passage hidden by the tapestry. A bed, the
  `jarl` chest, a lectern, a barrel and a tapestry.
- **Smithy** (northwest): a forge with a lava cauldron, a hood and a chimney, a blast furnace, an anvil, a smithing table,
  a grindstone, a water cauldron, a chest and a barrel. Open to the south.
- **Stables** (northeast): three stalls with hay, water troughs and gates; a chest and a barrel. The roof is partly broken.
- **Shipyard** (west): a long shed open to the yard with a half-built **longship** on its slipway (keel,
  plank hull, tall stem and sternpost, rowing benches and a mast without a sail), the carpenter's bench, a barrel of loot,
  a grindstone, a loom and wool for the sail.
- **Warriors' houses** (east): two 13 × 9 houses with four beds, a table with benches, a chest and a barrel. The southern one
  burned: charred planks, the roof caved in over its east end and a dead campfire among the rubble.
- **Pantry** (southwest): barrels, hay, a composter and a chest and a barrel with provisions; part of the roof fallen.
- **Rune stones**: two on either side of the esplanade before the longhouse (the west one carries the **riddle** of the
  rune wall: "Wake the raven and the wolf; let the serpent and the bear sleep"; the east one, "Here reigns Ulfgrim,
  jarl of the taiga") and two loose ones in the yard.

## The kings' barrow (piece `tumulo`)

Upper level (feet at y = -6, rooms 4 high) and lower level (feet at y = -12). Plans in
[`salon_jarl/planos.txt`](salon_jarl/planos.txt).

1. **Vestibule of the ancestors**: where the stairs arrive; two stone warriors (armor stands with a helm,
   chainmail and a stone axe), tapestries, soul lanterns and a sign: "Here sleep the kings of the hall. Let no one wake
   the jarl".
2. **Gallery of the kings**: 17 blocks with burial niches in both walls (skulls, bones) and the chest of a lesser
   king (`tumba`). A **zombie spawner**. One of the northern niches is sealed: it is the **secret door** (puzzle
   2) to the **skald's chamber** (hidden room: bookshelves, lectern, note block, the `escaldo` chest). Its lever is at
   floor level by the foot of the wall, three blocks further on.
3. **Hall of echoes**: a crossing with cobwebs and a **spider spawner**.
4. **Ossuary** (to the north): piles of bones and skulls, the `osario` chest and a **skeleton spawner**.
5. **Tripwire corridor** (to the south): **trap 1**, a tripwire with two arrow dispensers at head
   height (as in the jungle temple).
6. **Offering room**: pots, candles and tapestries; the `ofrendas` chest holds the **Chronicle leaf**. At the
   west end, on an altar, the chest of **greed**, with two pressure plates in front of it and TNT underneath
   (**trap 2**, as in the desert temple).
7. **Rune room** (puzzle 1): the west wall has four chiseled tuff **rune stones**, each with its
   lever and its name: Ormr, the serpent; Hrafn, the raven; Björn, the bear; Ulfr, the wolf. The stone door opens
   only with **the raven and the wolf awake and the serpent and the bear asleep** (the riddle is on the yard's rune
   stone). The correct levers turn off two inverting torches that power the pistons' line; the fake ones
   power it directly with dust, so with any fake rune awake the door stays closed (or closes
   again).
8. **Narrow staircase** (six steps) to the lower level and the **jarl's chamber**: a wooden burial chamber, like those of
   buried ships, with posts, tapestries, pots and the stone barrow **open and empty**: the **guardian**, the
   **jarl Ulfgrim, the Unburied** (a zombie, 60 health, armor 4, an iron axe, an iron helm and chainmail; no
   reinforcements, does not pick up loot and does not break doors), patrols the room.
9. **Treasure chamber**, north of the jarl's: the **premium** chest, a gold block with candles, a barrel and pots.

## Player route

Gate → yard (free: towers and wall-walk, smithy, stables, shipyard, houses, pantry) → longhouse → the dais tapestry
→ the jarl's alcove. Stairs in the west aisle → vestibule → gallery of the kings (lever → skald's chamber) → hall of
echoes → ossuary (dead end) or the tripwire corridor → offering room → rune room → combination →
stairs → the jarl's chamber → treasure. Everything has a way back to the entrance without jumps (the audit checks it).

## Puzzles and traps (everything at rest and consistent when generated)

- **Puzzle 1, the rune wall** (`pieces.combo_door` with two levers and two fake ones): extended sticky pistons
  holding two polished tuff blocks; the line of dust runs inside the wall (four thick: levers, torches or
  the fake ones' dust, door and pistons with the line, and the face behind). The 16 combinations are tried.
- **Puzzle 2, the skald's secret door** (`pieces.lever_door`): a niche sealed with chiseled brick; the lever turns off the
  inverting torch and the pistons pull in the door. The pistons and the torch stay inside the two-thick wall.
- **Trap 1**: a taut tripwire between two hooks with a dispenser above each hook.
- **Trap 2**: two stone plates in front of the chest of greed with TNT two blocks below.

## Enemies and entities

- **3 spawners**, all in the barrow and in the dark (block light 0 within a radius of 4): zombies (gallery), spiders (hall
  of echoes) and skeletons (ossuary).
- **Guardian**: jarl Ulfgrim (the only one with the `heraldia_guardian` tag; it drops its trophy if a player kills it).
- Two armor stands in the vestibule. No villagers, golems or animals: the hall is abandoned.
- In total, **3 entities** per structure.

## Chests (18) and loot

Richer the more hidden they are; each table has an extra `solo_sin_lootr` pool.

| Table | Where | Contents |
|---|---|---|
| `atalaya` (2) | northwest tower, guardroom | arrows, torches, bread, flint, a worn bow, spyglass |
| `herreria` | smithy | iron, coal, worn tools, chains; extra: the Smith's Hammer, the odd diamond |
| `establo` | stables | leather, wheat, leads, hay, saddle; extra: horse armor |
| `astillero` (barrel) | shipyard | planks, sticks, string, wool, a spruce boat; extra: the Longship's Oar, map, compass |
| `guerreros` (2) | warriors' houses | arrows, leather armor, a stone axe, shield; extra: an enchanted iron axe |
| `despensa` (chest and barrel) | pantry | bread, wheat, fish, berries, honey; extra: cake, golden apple |
| `salon` (2) | longhouse aisles | food, wool, leather, arrows; extra: nuggets, emerald |
| `jarl` | hidden alcove | gold, emeralds, a goat horn, the Ring of the Oath, the Jarl's Mead, enchanted book |
| `tumba` | gallery of the kings | bones, nuggets, a worn sword; extra: an enchanted gold helm |
| `osario` | ossuary | bones, arrows, skull; extra: an enchanted bow, bottles o' enchanting |
| `escaldo` | the skald's hidden chamber | books, paper, feathers, the Saga of Ulfgrim; extra: enchanted book, "far" disc, horn |
| `ofrendas` | offering room | gold, emeralds, amethyst, a Carved Rune Stone **and the Chronicle leaf** |
| `codicia` | altar of greed (trap) | heaps of gold and emeralds; extra: diamonds, gold block |
| `premium` | treasure chamber | 90 %: the Raiding Axe, the Horn of the Assembly, the Shield of the Hall, armor trims (coast, wild, rib), discs, gold, emeralds, enchanted book; 10 %: an enchanted diamond axe or chestplate, an enchanted golden apple or a totem |

No netherite or elytra.

## Trophy and Chronicle

- **Trophy**: *Ulfgrim's Shieldbreaker* (a rare iron axe, Sharpness 2, Unbreaking 2): "It split a hundred shields in his
  last raid. The jarl did not let go of it even in death".
- **Leaf** (`ofrendas` chest): Ysolda reaches the hall, the jarl listens to her by the hearth and swears by his ancestors
  to keep the leaf; they take it down to the barrow of his kings, among the offerings, and he promises that not even death will take it from him.
  The clue with which the Pyramid temple's leaf points to it: "the taiga, where an unburied jarl guards his hall behind a
  palisade". Its own points to the Wizard's tower.

## State of conservation

Visible surface damaged: **16 %** (computed over the hall's blocks with a face to the outside air: the hand-made
ruin plus what is expected from the processor). Hand-made ruin: breaches in the east and south palisade with logs fallen
inwards, fallen points and patches of stripped logs, broken stretches of the wall-walk, the caved-in roof of the northeast
tower, the burnt warriors' house, holes in the roofs of the pantry, the stables and the longhouse (with rubble
below) and patches of moss on the roofs. Processor: cobblestone → mossy (35 %), stone brick → cracked
(12 %) or mossy (8 %) and broken panes (30 %). Nothing that holds up a mechanism changes its solidity.

## Audit (a condition for generating)

`audit.py` fails the build if: the redstone is not in its stable state; any of the 16 combinations of the
rune wall opens without being the correct one (or the correct one does not open); the lever does not open the skald's door; the wire or the
plates do not fire; something hidden (the skald's chamber, the lower staircase, the jarl's chamber, the treasure) can be reached without
solving the puzzles or cannot be reached by solving them; the alcove cannot be reached through the tapestry; there are chests, spawners or
levers out of reach, doors without an exit, stairs without headroom, cells without a way back to the entrance (strict
walk without falls), spawners with light, loose blocks, natural rock in sight in the crypt, the number of chests
falls outside 15-25 or the damaged surface outside 15-20 %. The shared checks also run (`lint.support_issues`,
`access_issues`, `door_pair_issues`, `stair_headroom_issues`) over the whole build.

## Performance

- Generation: two templates (45,400 + 30,900 blocks, fewer than the ice fortress) with a rule processor and without
  custom Java. The `/place structure` time measured on the test server: see the PR (printed by
  `smoke_server.py`).
- Entities: 3 (the guardian and two armor stands). 3 spawners with the vanilla radius and limit. Nothing per tick.

## Tests

- `python3 tools/gen/uniques/jarl_hall/blueprints.py` → plans by level and renders in `docs/unicas/salon_jarl/`.
- `python3 tools/gen/uniques/jarl_hall/smoke_server.py --jar build/libs/heraldia-<version>.jar --work "$PWD/build/smoke"`:
  places the structure (measures the time and counts entities), and the templates unrotated to operate the runes (also
  with a fake rune), the skald's door, the tripwire and the TNT plates. It is in the CI matrix.

## Renders

![Compound](salon_jarl/salon.png)
![Ground floor](salon_jarl/corte_planta_baja.png)
![Barrow](salon_jarl/tumulo_corte_alto.png)
