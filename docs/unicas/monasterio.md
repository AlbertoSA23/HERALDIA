# Mountain monastery (`heraldia:unicas/monasterio`)

A monastery perched on a crag: three stepped terraces joined by flights of steps, the church at the top
and, carved into the rock, caves with hermitages, an ossuary, a secret archive and the reliquary.

## Adapting to the slope (decision)

The jigsaw does not know which way the hillside rises (the rotation is random) and `beard_thin`/`beard_box` only
fill under the base of each piece or sink the terrain around it. That is why the monastery **brings its own
crag**: a single rigid template of 59 × 88 blocks in plan that includes the rock massif from the
caves (y = 0) up to each terrace, with an irregular skirt of scree around it, and explicit air above the
terraces so that the hillside does not bury them.

- `terrain_adaptation: none`: the template defines its whole volume; outside it the terrain is untouched.
- `start_height: -25` with projection to `WORLD_SURFACE_WG`: the lower terrace (y = 24 of the template)
  sits flush with the terrain at the center of the footprint.
- On flat ground the crag rises over the meadow (12 blocks up to the cloister); on a hillside, uphill
  the template cuts into the mountain like a cutting and downhill it shows the crag's rock.
- Faces of the massif facing a terrace: ashlar with buttresses; outer faces: natural rock
  (stone, andesite, tuff and cobble) with a slope.
- A single piece: the audit's walk covers the whole monastery from the entrance.

Biomes: `meadow` and `grove`. Rarity: `spacing` 250 / `separation` 190 chunks (one every ~3,000-5,000 blocks).

## Levels (template coordinates; the entrance is at z = 0, you climb towards increasing z)

| Level | Floor (y) | z | Contents |
|---|---|---|---|
| Path | 24 | 0-5 | a cobbled path with lanterns; entrance connector |
| T0 Atrium | 24 | 6-27 | gatehouse (porters and alms), atrium, graveyard, ruined guesthouse, steps to T1 |
| T1 Garden/refectory | 30 | 28-49 | a two-bed garden with ditches, a shed, refectory, kitchen; cellar below (y 24) |
| T2 Cloister | 36 | 50-72 | cloister with a well, dormitory with cells, library, chapter house |
| Church | 37-38 | 73-87 | nave with columns, choir, raised presbytery, sacristy at the base of the bell tower |
| Bell tower | 38-70 | 73-79 | an inner ladder, landing, bell |
| Crypt | 30 | 75-85 | under the presbytery: tombs, zombie spawner, puzzle 1 |
| Caves | 13 | 20-86 | the hermits' grotto, 3 hermitages, spider cave, ossuary, archive, catacombs, reliquary (y 5) |

## Player route

1. Path → gatehouse arch → atrium. On the sides: gatehouse (barrel), alms room, graveyard and
   the collapsed guesthouse (a chest among the rubble).
2. A 6-step flight → T1. Garden (shed with a chest), refectory and kitchen (barrel). Stairs
   from the kitchen to the **cellar** (barrel). In a corner of the cellar, behind the vats, a trapdoor and a
   ladder go down to the **cellarer's secret pantry** (hidden room, medium chest).
3. Steps → T2. Cloister with galleries and a well; library (chest) with a **gap behind a bookshelf**
   that leads to a ladder up to the **hidden scriptorium** under the roof (medium chest); chapter house;
   dormitory with cells (two cell chests and the prior's).
4. Church: nave, choir, presbytery. Sacristy at the base of the bell tower (chest) and a ladder up to the
   bell (chest on the landing).
5. Stairs from the side aisle to the **crypt** (zombie spawner, dark). **Puzzle 1**: two levers
   that are on, with their lamps, keep a gravestone in a niche closed; the sign says you have to
   put out the lights of the dead. With both off, the pistons pull the gravestone back.
6. A 17-step secret passage down to the **hermits' grotto** (y 13). From the grotto:
   hermitages 1 and 2 (hermitage chests), a corridor to hermitage 3 with **trap 1** (tripwire → two
   arrow dispensers, like the jungle temple), the spider cave (cave spider spawner,
   smaller chest) and the **ossuary** (skeleton spawner).
7. **Puzzle 2** in the ossuary: three levers in three niches and an iron door. The sign: "the first and the
   last keep watch; the middle one sleeps". Only with 1 and 3 up and 2 down does the
   **secret archive** open (two rich chests).
8. From the archive, stairs to the **catacombs** (zombie spawner, a chest in a niche) and the antechamber with
   **trap 2** (pressure plates over dispensers with splash poison potions and arrows,
   like the desert temple's plates but without TNT). At the back, the **reliquary**: a named guardian
   and the premium chest on the altar.

## Redstone (everything stable when placed)

- Puzzle 1 (OR): a lever that is on → a strongly powered block → dust in a hidden chamber in the wall →
  **extended** sticky pistons holding the gravestone. The lamps are next to each
  lever's block. When placed, all the states are consistent (levers `powered=true`, lamps `lit=true`,
  dust with its level, pistons extended with their head): any update leaves them the same.
- Puzzle 2 (AND with negation): levers 1 and 3 → a torch (inverter) that turns off; lever 2 → dust; the
  three outputs add up in a line of dust that powers the block of the final torch, which opens the
  door. Consistent initial state: torches 1 and 3 lit, the line powered, the final torch
  off, the door closed.
- Traps: everything unpowered when placed (hook and wire not triggered, plates not pressed).
- The module's own check recomputes the dust levels and the state of torches, pistons,
  lamps and doors from the levers and requires them to match what is placed.

## Spawners and guardian

- Zombie: crypt and catacombs. Skeleton: ossuary. Cave spider: spider cave.
  All in dark dungeon areas; none on the inhabited surface.
- Guardian: a skeleton, "Friar Tenebrio, guardian of the reliquary", with an iron sword, a gold helmet and
  a chainmail chestplate, 40 health, `PersistenceRequired`, a low chance of dropping its equipment.

## Inhabitants

Three monks (villagers with a fixed profession): a cleric (brewing stand in the sacristy), a librarian
(the library's lectern) and a farmer (the shed's composter). Beds in the cells.

## Condition (80-85 % in good condition)

Ruins that make sense: the guesthouse without a roof with fallen walls, a fallen stretch of the graveyard wall,
the shed with its roof caved in, the northwest corner of the cloister galleries collapsed with rubble,
two dormitory cells without a ceiling, half the chapter house roof fallen, a broken corner of the
bell tower and gaps in the parapets. Processor: cracked stone brick (8 %) and mossy (8 %),
mossy cobble (15 %). The module computes the share of the footprint in ruins (target 15-20 %).

## Loot (vanilla only; the extra pool of each chest has `solo_sin_lootr`)

| Table | Where | Contents |
|---|---|---|
| `menor` | gatehouse, alms room, guesthouse, kitchen, shed, bell tower, spider cave | bread, apples, candles, paper, seeds, iron nuggets, the odd emerald |
| `bodega` | cellar | honey, berries, apples, bottles, sugar, wheat |
| `celda` | cells | candles, book and quill, paper, bread, string |
| `biblioteca` | library | books, paper, ink, feathers, compass, empty map, a rare enchanted book |
| `oculto` | secret pantry, scriptorium, the prior's cell, sacristy | emeralds, gold, enchanted book, a rare golden apple |
| `ermita` | hermitages | emeralds, amethyst, low-level enchanted books, gold ingots |
| `archivo` | secret archive | enchanted books (10-20), emeralds, a rare diamond, name tag, bottles o' enchanting |
| `catacumba` | catacombs | bones, gold, iron, lightly enchanted iron armor, golden apple |
| `premium` | reliquary | 90 % `premium_vistoso` (named items, moderate enchantments, armor trims, discs), 10 % `premium_fuerte` (diamond gear enchanted 20-30 or an enchanted golden apple); plus a pool of valuables and the extra without Lootr |

No netherite gear or elytra. The item names and the guardian's use translation keys
`heraldia.unicas.monasterio.*` with a Spanish fallback.

## Against the owner's criteria

- Complete staircases without jumps: every change of level is made of steps or a ladder; the audit walks it.
- No door without an exit: the audit checks both sides of each door (the secret ones, open).
- Furniture against the wall, chairs facing outwards, lanterns hanging on chains.
- Symmetry in the church, cloister, gatehouse and refectory; each room with its function.
- Nothing floating: its own check for loose blocks (everything must touch the massif).

## Checked

- Its own audit (a condition for generating): consistent redstone states when placed, the 4 and 8 lever combinations of
  the two puzzles (only the solution opens), hooks and plates with their dispenser, nothing floating, ruins at 15.7 %
  of the footprint, chests with an existing table, spawners and guardian. `lint.py` on the view with the secret doors
  open: the walk from the entrance to every door, chest, piece of furniture and ladder; jigsaw intact.
- 26.3 dedicated server (`smoke_server.py`): the template is placed; pistons extended, lamps lit,
  torches and door in their state; spawner and guardian present; puzzle 1 only opens with both levers
  off and puzzle 2 only with 1 and 3 up.
- Not checked in game: that the traps fire when stepped on or crossed, that the spawners produce mobs, the
  fit on real hillsides and the look (missing screenshots from the owner).

## Plans and renders

In `docs/unicas/monasterio/`: text plans by level (`planos.txt`, reachable cells marked) and
isometric renders (`exterior.png`, `cuevas.png`).
