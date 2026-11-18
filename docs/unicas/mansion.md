# Haunted mansion (`heraldia:unicas/mansion`)

A decaying Victorian mansion in the swamp: a 62 × 72 block walled estate with a front garden, a
three-story house with an attic under a steep gable roof, a five-level square turret with a spire at the northwest corner, a ruined glass greenhouse to the east, a family graveyard with a mausoleum
behind and, under the house, a cellar, an ossuary, a hidden laboratory and the treasure chamber.

It differs from the vanilla woodland mansion in everything visible: dark deepslate brick with
spruce trim (not dark oak and birch), a gabled deepslate tile roof with a turret and
chimneys, an open estate with a graveyard, almost no soul light and a basement with mechanisms.

## Biome and placement

- Biome: `#heraldia:pantano` (swamp and mangrove swamp). The swamp is flat: the estate fits without earthworks.
- Rarity: `spacing` 250 / `separation` 190 chunks (one every ~3,000-5,000 blocks, the contract's default value).
- Two rigid pieces joined by a vertical jigsaw: `casa` (estate, house, greenhouse, graveyard; its y=0 layer is the
  ground) and `sotano` (everything below y=0). `size` 2, `max_distance` 48.
- `beard_thin` adaptation: the terrain adjusts to the base of the house (y=0) and the estate sits on a flat island.
  The basement is a separate piece, below the house, that **fills its box completely** with stone and dirt
  (it leaves no undecided terrain gaps), so the `beard` cannot open a pit around it or leave cavities
  next to its walls. The mausoleum has no underground crypt: it sits on a mound and its crypt is inside the mound.

## Heights (coordinates of the `casa` template; the basement uses the same ones)

| Level | Floor (block) | Feet | Rooms |
|---|---|---|---|
| Basement | -6 | -5 | -5..-2 (ceiling -1) |
| Ground floor | 1 | 2 | 2..6 |
| First | 7 | 8 | 8..11 |
| Second | 12 | 13 | 13..16 |
| Attic | 17 | 18 | under the roof (ridge at y=31) |
| Turret lookout | 23 | 24 | 24..26, spire up to y=37 |

## Floor plans

Main house x 12..49, z 14..40 (façade to the north, z=14). Entrance to the estate through the gate at z=0.

**Ground floor**
- A porch with columns and a step; a double door to the **hall** (x 25..36, z 15..29, double height) with a
  **double staircase**: two flights of 6 steps against the east and west walls that climb towards the back to a
  landing-gallery (z 25..29) on the first floor, with a railing. A soul lantern hangs in the center.
- West, front: the **library** (x 13..23, z 15..26) with floor-to-ceiling bookshelves, reading tables and the
  door to the turret. In its south wall, between two projecting bookcases, is the **secret bookshelf**.
- West, back: a hidden strip (z 28..30) with the mechanism and the secret staircase; the **kitchen** (x 13..23, z 32..39)
  with a soul hearth, a pantry, the service stairs to the cellar and the service ladder to the upper floors.
- Center, back: the **dining room** (x 25..36, z 31..39) with a long table and chairs facing outwards; a glazed
  door to the back terrace.
- East: the **ballroom** (x 38..48, z 15..39) with a checkered floor, a fireplace in the south wall and doors to the
  **ruined greenhouse** (x 51..59, z 19..35): broken glass, vines, dry beds and a barrel.

**First floor**: landing; to the west a corridor with the **master bedroom** (with a door to the turret) and the
**guest bedroom**; in the center the **lord's study**; to the east the **portrait gallery** (real vanilla
paintings along 25 blocks).

**Second floor**: a transverse corridor (z 26..28) joining six rooms: two **guest bedrooms**,
the **children's room**, the **sewing room**, the **music room** and the **servants' quarters** (where
the service ladder arrives).

**Attic**: the whole loft with beams, junk, cobwebs, a black cat and a hole in the roof.

**Turret** (x 8..14, z 10..16): a 22-step spiral staircase around a central pier, with a
landing and a door on each floor, the attic and the lookout; a chest in the lookout.

**Basement** (y -5): the cellar under the kitchen (reached by the service stairs); the storeroom under the dining room; and the
hidden part, only through the secret staircase: the **antechamber** under the library → a corridor with a trap → the **ossuary** under
the hall → the **laboratory** under the ballroom → an iron door with a combination → the **treasure chamber**.
From the ossuary, a one-way iron door (button only on the ossuary side) leads to the storeroom to
return through the cellar.

**Exterior**: a gate with pillars and soul lanterns, an entrance drive with dead trees and street lamps, a low
perimeter wall with fallen stretches; behind, a terrace, a fenced **graveyard** with graves (some broken) and the
**mausoleum** on a mound with a chapel and a crypt.

## Player route

Gate → garden → porch → hall. Free: library, kitchen, dining room, ballroom, greenhouse, terrace and
graveyard. Double staircase → first floor. Turret (from the library or the master bedroom) or the service ladder
(kitchen) → second floor and attic; turret → lookout. Service stairs → cellar → storeroom
(a dead end: the iron door does not open from here). Mausoleum → crypt (trap). Secret bookshelf → stairs
→ antechamber → corridor with a tripwire → ossuary → laboratory → combination → final chamber.

## Mechanisms (all at rest and consistent when generated)

When a template is placed there are no block updates, so each circuit is saved in its stable
state: torches lit, dust with its power and shape, repeaters and pistons extended with their head,
just as they would be after updating. Nothing moves until the player operates something. The module's
redstone simulator checks it (see Audit).

1. **Secret bookshelf (library)**: a lever in the bookshelf (x 18) → the torch on the other side turns
   off → the dust and the repeater stop powering two sticky pistons (the lower one by
   quasi-connectivity) → they pull in the two bookshelves of the door (x 22) and a 1 × 2 passage opens. The pistons
   stay hidden behind a projecting bookcase. Pulling the lever down again closes it.
2. **Laboratory combination**: four levers on the south wall. Under each one, a candle: lit under the
   1st and the 4th. The iron door (x 47) only opens with the 1st and 4th up and the 2nd and 3rd down
   (open = A ∧ ¬B ∧ ¬C ∧ D: two inverters, an OR bus of dust and an output inverter).
3. **One-way door**: a button in the ossuary next to the iron door to the storeroom.

## Traps

- A **tripwire** (like the jungle temple) in the antechamber → ossuary corridor: two hooks, the string and two
  dispensers with arrows in the walls, which fire at head height.
- A **pressure plate with TNT** (like the desert temple) in front of the chest in the mausoleum's crypt:
  five blocks of TNT under the floor.

## Enemies

- **Three spawners**, all in the basement: zombie in the cellar, skeleton in the ossuary and spider in the laboratory
  (with cobwebs). The mausoleum's crypt has no spawner: its monsters would step on the TNT plate.
- Final guardian in the treasure chamber: a **wither skeleton, "Count Malaquías"** (`PersistenceRequired`,
  60 health, black-dyed leather armor that it does not drop; the game gives it its stone sword when generated).
- No villagers or golems: the house is abandoned. Only a black cat in the attic.

## Chests (33) and loot

Richer the more hidden they are. Each table has a base pool and an extra pool marked `solo_sin_lootr`.

| Table | Where | Contents |
|---|---|---|
| `jardin` (2) | garden shed, greenhouse | seeds, bone meal, worn tools |
| `cocina` (5) | pantry (2), dining room sideboard, cellar (2) | food, bottles, honey, sugar |
| `menor` (13) | dining room, ballroom, bedrooms (5), children's room, sewing (2), music, servants, storeroom (2) | candles, string, paper, wool, some iron and gold, a few emeralds |
| `biblioteca` (2) | library, study | books, paper, feathers, ink, "The Countess's Diary", sometimes an enchanted book |
| `desvan` (3) | attic (2), turret lookout | junk with something better: spyglass, compass, rare discs 11/13 |
| `oculto` (4) | antechamber, ossuary, treasure chamber (2) | iron, gold, a loose diamond, enchanted book, golden apple |
| `laboratorio` | laboratory (2) | ingredients and potions (healing, night vision, fire resistance), bottles |
| `panteon` | mausoleum crypt | gold, emeralds, a named piece, a trim template |
| `premium` | treasure chamber | see below |

**Premium**: 90 % showy and 10 % somewhat stronger. Always 3-5 showy pieces: "The Count's Pocket Watch"
(a named clock), "Family Portrait" (painting), "The Count's Blade" (iron sword) and "The Family's
Hunting Bow" with level 10-20 enchantments, trim templates (host, raiser,
shaper, wayfinder), discs 11, 13 and mall, gold and emeralds. A separate one-roll pool: 90 % nothing, 10 % a
strong piece (a diamond chestplate or a diamond sword with 20-30 enchantments, an enchanted golden apple or a totem).
No netherite gear or elytra.

## Ruin (15-20 % of the surface)

- The element's processor: deepslate brick → cracked (40 %), polished deepslate → cobbled (20 %), cobblestone and
  stone brick → mossy (35-40 %), glass → nothing (30 %, broken windows), tiles → nothing (4 %, leaks).
  Computed over the house's visible surface: ~12 % of blocks changed, plus the hand-made ruin: ~15-17 %.
- By hand: the greenhouse with half its roof fallen and broken panes, the hole in the attic roof with
  rubble below, stretches of the perimeter wall knocked down, fallen headstones, a fallen chandelier in the ballroom.
- Gaps only where they do not break the route or leave anything hanging.

## Audit (a condition for generating)

`build()` adds to `reg.warnings` (and so the build fails) any failure of:
- `lint.py` on each piece (supports, lanterns, chains, ladders, doors with an exit, jigsaws).
- The walk over the two joined pieces from the gate: every door, chest, barrel, staircase, spawner and
  lever reachable; the hidden areas only with the mechanisms open (and not before).
- Nothing floating: every block connected to the ground.
- Redstone simulator: a consistent rest state; the lever opens the bookshelf; only the correct combination
  opens the chamber; the hook fires both dispensers; the plate primes the TNT; the button opens the door.

Plans by level (`planos.md`) and renders in `docs/unicas/mansion/`; they are regenerated with `python3 -m unicas.mansion.planos`
from `tools/gen`. The server test (`prueba_servidor.py`) operates the bookshelf and the combination in the game.

## Against the design criteria

- Complete staircases without jumps (a spiral with an arrival step at each landing), no door without an exit,
  no inaccessible room (checked by the walk).
- Furniture against the walls without covering windows; center free except for tables with chairs facing outwards.
- Lanterns hanging on chains, no loose water (no water is placed).
- Symmetry in the façade, hall, double staircase, dining room and ballroom; the turret breaks the symmetry on purpose.
