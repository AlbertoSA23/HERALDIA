# Ice fortress (`heraldia:unicas/fortaleza_hielo`)

A fortress of packed ice and blue ice on a snowy stone plinth, in ice spikes, snowy plains and snowy
taiga. Abandoned: it is guarded by strays and its former lord, **the Frost King**. A single rigid
piece designed by hand (51 × 65 blocks in plan, 46 high) and a single variant.

## Terrain adaptation (basements)

The crypts and the treasure chamber do not sink into the terrain: they are **inside a solid 10-block plinth** on
which the fortress rises (y = 0 to 10 of the template). That way the piece's box starts at ground level and `beard_thin` only
fills below, without digging out the neighboring terrain. You climb to the courtyard by an 11-step flight of stairs set between two
parapets (with a half slab for access on the first step, because the rigid piece sits one block above the ground).

## Floor plans by level (template coordinates: x from west to east, z from north to south; "feet" = height of the feet)

| Level | Feet | Contents |
|---|---|---|
| Treasure chamber | 1 | antechamber, the plate trap corridor, the final chamber with the premium chest |
| Crypts | 6 | vestibule, the tripwire corridor, ossuary (stray spawner), offering room (skeleton spawner), the King's crypt (guardian) |
| Courtyard and ground floor | 11 | courtyard with a frozen fountain, fortified gate, barracks, kitchens, kennel, sculpture gallery, great hall with the throne, pantheon, the king's hidden room |
| Wall-walk | 20 | the walk along the four walls, the portcullis room, the middle floors of the towers |
| Lookouts | 26 | the upper room of the four towers, under the spires |

Plans generated with the reachable cells: `docs/unicas/fortaleza_hielo/plantas.txt`; renders: `docs/unicas/fortaleza_hielo/*.png`.

## Player route

1. North flight of stairs → fortified gate (a 5-wide passage under the raised portcullis) → courtyard.
2. Courtyard: to the west the **barracks** (2 chests) and the **gallery of ice sculptures** (knight, wolf, bear, dragon; 1 chest
   behind the last sculpture); to the east the **kitchens** (campfires under the roof's flue, smoker, 1 chest, barrels) and the
   **kennel** (pens with three snow wolves, 1 barrel); to the south the **great hall** with the ice throne.
3. Corner towers with ladders up to the wall-walk and the upper room. The wall-walk joins the four towers and the **portcullis
   room** (1 chest). The northeast lookout holds 1 chest. The southern towers are entered from the gallery and from the pantheon.
4. **The king's hidden room** (puzzle 1): of the two niches flanking the throne, the right one is a piston door. It
   opens by pulling down the lever on the back wall, three blocks away. Inside, the `tesoro_real` chest.
5. **Pantheon** (east of the hall) → stairs to the **crypts**: vestibule → corridor with a **tripwire** (4 dispensers
   with arrows in the walls) → ossuary to the north (**stray spawner**, a powder snow pit, 1 chest) and offering room to the
   south (**skeleton spawner**, a collapse, 1 chest) → **the King's crypt** (named guardian).
6. **Secret door of the crypt** (puzzle 2): in the west wall there are two niches; the southern one is another piston door. The
   lever is hidden between the wall and a pillar (it can only be seen from the side). Behind it, a staircase goes down to the **treasure
   chamber**: antechamber → one-block corridor with a **pressure plate and two dispensers** → the final chamber with the premium chest.

## Mechanisms (all of them work when placed, without block updates)

- Piston doors: two sticky pistons **already extended** hold the two blocks of the niche; the lever is
  **on** from the start and powers the pistons (directly through a cross-shaped dust on top of a block that is weakly
  powered). The whole saved state is consistent (lever on, dust at 15, pistons extended with their head), so
  nothing changes when generated. Turning the lever off retracts the blocks into the wall and the niche becomes
  a passage; turning it on again closes it (the passage stays open from inside if nobody touches the lever).
- Traps: tripwire (`attached` hooks, unpowered) and a stone plate at rest; the dispensers, not fired,
  are next to the block that powers the hook or next to the plate. A one-block-deep powder snow pit next to the spawner.
- The module's audit simulates the redstone: saved states = computed states, pistons extended ⇔ powered, and
  that stepping on the plate or the wire signals the dispensers and turning each lever off opens its door.

## Spawners and guardian

- Ossuary: stray spawner; offering room: skeleton spawner. Both in the dark (computed block light 0).
- **The Frost King**: a stray with `PersistenceRequired`, a translatable name, 40 health, a bow with Power II, an iron helmet and
  a chainmail chestplate (a moderate chance of dropping its equipment).
- No villagers or golems: the fortress is abandoned. The snow wolves in the kennel are the only peaceful life.

## Ice and light

Only packed ice and blue ice are used (they do not melt). The audit computes block light and fails if there is regular ice
or snow layers with light > 11 or if a spawner receives light. No exposed top surface is a snow block
(the biome's ice spikes spawn on snow blocks).

## Condition (80-85 % in good condition)

A degradation processor: cracked stone bricks, fallen battlements and patches of snow on the packed ice. Hand-made
ruins: the fallen tip of the northeast spire, a breach in the east parapet, a hole in the kennel roof with rubble,
the fountain's broken statue and a collapse in the offering room. The audit estimates the share of damaged surface.

## Chests and loot (vanilla only, no netherite gear or elytra)

Each table has an extra `solo_sin_lootr` pool (with Lootr each player receives only the modest part).

| Chest | Where | Loot |
|---|---|---|
| `barracones` ×2 | barracks | bread, arrows, leather, iron nuggets, worn leather armor |
| `cocina` | kitchens | cooked meat, stews, berries, coal |
| `perrera` (barrel) | kennel | bones, leads, leather, the odd name tag |
| `garita` | portcullis room | arrows, a worn crossbow, torches, a rare spyglass |
| `atalaya` | northeast upper room | map, compass, spyglass, emeralds |
| `galeria` | sculpture gallery | packed ice, lapis lazuli, candles, books |
| `cripta` ×2 | ossuary and offerings | bones, gold nuggets, iron, emeralds, a rare enchanted book |
| `tesoro_real` | the king's hidden room | gold, emeralds, diamond, enchanted book, golden apple |
| `premium` | treasure chamber | 90 %: named items with moderate enchantments, armor trims, discs; 10 %: a well-enchanted diamond sword or chestplate, an enchanted apple or a totem |

## Against the design criteria

- Complete staircases without jumps (walk audit); no door without an exit; every room reachable (the hidden ones,
  with their mechanism open).
- Furniture against the walls; centers free except for tables with chairs facing outwards.
- Lanterns hanging from the ceiling or a chain; no water at all.
- Symmetry in the fortified gate, the great hall, the towers and the niches; every element has a function
  (niches = doors or the puzzle's decoy, pillars = where the lever hides).
