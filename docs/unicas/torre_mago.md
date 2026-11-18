# Wizard's tower (`heraldia:unicas/torre_mago`)

A slender deepslate tower (diameter 17, about 63 blocks above the ground to the tip of the conical roof)
with an attached turret and two basements. Dark forest and pale garden (`#heraldia:oscuro`), one every ~4,000 blocks
(a 250/190 chunk grid). A single rigid template (`unicas/torre_mago/torre`, 27 × 79 × 25), designed by hand.

Plans with reachable cells: [`torre_mago/plantas.txt`](torre_mago/plantas.txt). Renders: [`exterior.png`](torre_mago/exterior.png)
and [`cortes.png`](torre_mago/cortes.png) (one cut per floor). They are regenerated with `python3 tools/gen/uniques/wizard_tower/blueprints.py`.

## Terrain adaptation
- `start_height` −14 and `terrain_adaptation: none`: the vestibule floor sits flush with the terrain and the basements below
  ground without the beard digging a crater around them (with `beard_thin` a box that goes down sinks the terrain).
- A circular terrace of radius 12 with a 4-block foundation and 5 blocks of air above: it absorbs gentle slopes
  (on a slope it looks like a plinth or a cutting, which makes sense). A low wall with the entrance to the north.

## Floor plans (feet at the given height of the template)
| Level | Use | Contents |
|---|---|---|
| Basement 2 (y 2) | Treasure chamber | A corridor with a trap plate, a chamber with 4 columns, the **premium chest**, the `tesoro` chest, the guardian |
| Basement 1 (y 8) | Failed experiments | Lower vestibule, barred cells, west wing (tripwire trap), east wing (spiders), south wing (crater), an iron door with a puzzle |
| Floor 0 (y 14) | Vestibule | North door, carpet, banners, benches, a lectern with the diary (clues), barrel |
| Floor 1 (y 20) | Lower library | Bookshelves under the gallery, lecterns, a table with chairs, chest |
| Floor 2 (y 26) | Gallery | A perimeter gallery with a railing over the atrium, two walkways, chest, **secret door to the turret's study** |
| Floor 3 (y 32) | Laboratory | A counter with brewing stands, cauldrons (one full), two chests, a scorched floor and a broken window |
| Floor 4 (y 38) | Enchanting | An enchanting table with bookshelves, amethyst, chest, lectern |
| Floor 5 (y 44) | Greenhouse | Large windows, moss beds with rare plants (torchflower, pitcher plant, eyeblossoms, azaleas), hanging spore blossoms |
| Floor 6 (y 50) | Bedroom | A bed against the wall, nightstands, a bookcase, a desk |
| Floor 7 (y 56) | Observatory | A telescope on the pier, a cartography table, chest; an observation slit to the north in the roof |

A continuous spiral staircase around a dark oak pier, from basement 1 to the observatory (6 steps per
floor, a two-cell landing, a railing at the opening of each floor). Basement 2 can only be reached through the iron door.

## Player route
Terrace → vestibule (the diary gives the three clues) → stairs up: library, gallery (incomplete bookshelf →
hidden study), laboratory (water for the cauldron), enchanting, greenhouse, bedroom, observatory. Down:
basement 1 with spawners (a zombie villager in the cells corridor, a cave spider in the east wing), the tripwire trap in the
west wing, a hiding place behind the cobwebs, the cauldron puzzle → a straight flight → the trap plate → treasure chamber and guardian.

## Puzzles, traps and spawners
- **Hidden study (gallery, west)**: in a niche, a chiseled bookshelf with five books and the sixth slot empty.
  Comparator → 6 dust → the block of a redstone torch that powers two extended sticky pistons holding
  two bookshelves (the door). Only slot 6 gives signal 6, which arrives with 1 at the end: the torch turns off and the pistons
  pull back the bookshelves. Any other slot (signal 1-5) does not reach. A sign in the niche: "the sixth too".
- **Iron door (basement 1)**: cauldron → comparator → 3 dust → door. Only the full cauldron (signal 3) opens it.
  Water: the laboratory's full cauldron (with a bucket from any chest or your own).
- **Tripwire trap** (as in the jungle temple): a wire from side to side of the west wing; the hooks power the wall
  and two dispensers with arrows fire at head height.
- **Trap plate** (as in the desert temple): a stone plate in the basement 2 corridor with TNT underneath; the
  cracked slabs around it give a warning.
- Everything is placed in a consistent state (pistons extended with their torch lit, dust at 0, comparators off,
  wires not stepped on): nothing depends on block updates when generated. Checked on a real server (see the PR).
- **Spawners**: a zombie villager (cells corridor) and a cave spider (east wing), in dark areas.
- **Guardian**: "Archmage Malvarius", a persistent evoker with 48 health and 4 armor; it drops a witch's loot
  instead of the totem (it does not give away a totem).

## Chests (richer the more hidden they are)
| Chest | Where | Table |
|---|---|---|
| Barrel | Vestibule | `vestibulo` (food, torches) |
| Chest | Lower library and gallery | `biblioteca` (books, paper; extra: enchanted book) |
| 2 chests | Laboratory | `laboratorio` (ingredients, simple potions) |
| Chest | Enchanting | `encantamientos` (lapis lazuli, books) |
| Barrel | Greenhouse | `invernadero` (rare seeds, moss) |
| Chest | Bedroom | `dormitorio` (personal items) |
| Chest | Observatory | `observatorio` (maps, compasses, amethyst) |
| 2 chests + barrel | Basement 1 | `experimentos` |
| Chest | Hiding place behind cobwebs (basement 1) | `escondite` (gold, emeralds; extra: diamond, disc) |
| Chest | Hidden study | `estudio` (enchanted books, a rare diamond) |
| Chest | Treasure chamber | `tesoro` |
| Chest | Treasure chamber | `premium` |

Premium: one main item, 90 % showy (Malvarius's Staff, a grimoire, a hood, a spyglass, a clock, a dagger, boots with
feather falling, the "vex" trim template, discs *strad* and *far*) and 10 % something stronger (a diamond sword with Sharpness III,
a diamond cuirass with Protection II, an enchanted golden apple); plus gold, emeralds, lapis lazuli, experience, amethyst and
an elixir of regeneration. No netherite or elytra. Each chest has an extra pool marked `solo_sin_lootr`.

## Condition (80-85 % in good condition)
Processor: 12 % of the deepslate bricks cracked, 21 % of the stone bricks with moss or cracks in the basements,
10 % of the deepslate stone with moss on the terrace. Gaps that make sense: the terrace wall fallen to the southwest, tiles
fallen in the southeast of the roof (rubble in the observatory), a broken window and a burnt floor in the laboratory, a crater
in the south wing of the basement, a bar torn out of a cell, cobwebs, vines and pale moss.

## Against the design criteria
- Complete staircases without jumps (audited with the walk); every door with an exit; nothing inaccessible except the
  cells, which can be seen through the bars (one has a bar torn out).
- Furniture against the wall without covering windows (the window fronts are left free); center free (the staircase).
- Lanterns hanging from the floor above, chains with an anchor, water only in cauldrons.
- Symmetry in the vestibule, library and enchanting room; every element with a function (benches, lecterns, beds, telescope).
- No villagers or golems: the tower is abandoned.

## Audit
`lint.py` (a walk from the entrance to every door, chest and staircase; supports; jigsaw) with the secret door
considered open (`lint_open`), and the module's `auditar()`: the state of pistons, torch and dust, the pieces of the puzzles and
traps, the presence of the guardian. Real server test: `tools/gen/uniques/wizard_tower/smoke_redstone.py`.
