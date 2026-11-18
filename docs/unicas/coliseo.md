# Ruined coliseum (`heraldia:unicas/coliseo`)

An elliptical amphitheater of 87 × 73 blocks and 27 high over a two-level hypogeum (14 blocks below the arena).
Biome: savanna and savanna plateau (explicit list `minecraft:savanna`, `minecraft:savanna_plateau`; windswept
savanna is left out because of its relief). The contract's default rarity (`spacing` 250 / `separation` 190 chunks).

Coordinates in this document: `(dx, dz)` relative to the center of the arena (+x east, +z south) and `y` relative to the floor of
the arena (sand at y=0; the player stands at y=1). "Ring r" = a constant distance from the edge of the arena
(concentric ellipses with semi-axes 16.5 + r and 9.5 + r).

## Pieces and terrain adaptation

- `unicas/coliseo/coliseo` (start, rigid, projected to `WORLD_SURFACE_WG`): everything from y=0 upwards.
  Its base is at ground level, so `beard_thin` only levels around it (as in the villages) and a ring of slabs
  (r 25-26) works as an access step.
- `unicas/coliseo/hipogeo` (child, rigid): from y=-14 to y=-1, joined by a vertical jigsaw under the arena.
  The piece fills **all** of its box (rock where there are no rooms), so that the lowering by `beard_thin` under its base does not
  open visible holes: the surrounding terrain stays below y=-2 and out of sight. That way the basement does not sink
  the surface terrain (the problem described in the guide).

## Floor plans by level

| Level | Feet at | Contents |
|---|---|---|
| Attic and upper terrace | y=19 | Terrace r 20-21 behind the attic (windows), the velarium niche with a chest, the velarium masts on the crown. |
| Stands II | y=12-19 | 8 rows of seats (r 12-19), stairs going up from walkway I to the terrace. A collapsed stretch to the northwest. |
| Upper gallery G2 | y=8 | Ring r 19-21 behind the second arcade (with a balustrade). Six vomitoria go up from G2 to walkway I. |
| Walkway I (praecinctio) | y=11 | Ring r 10-11 between the stands, with the mouths of the vomitoria. |
| Stands I and podium | y=5-11 | A marble podium (r 1-3) with the imperial box (south) and the editor's box (north); 6 rows (r 4-9). |
| Ground floor G1 | y=1 | Ring r 19-21 behind 40 arches; east (Triumphal Gate) and west (Libitinarian) tunnels to the arena; north and south passages to the boxes; two taverns; four staircases to G2; a west staircase to the hypogeum. |
| Arena | y=1 | Sand with the lifts' trapdoors and the open central shaft with a ladder. |
| Hypogeum H1 | y=-6 | A central east-west corridor, two side corridors, 8 lifts, 12 beast cells, barracks (west), armory (east). |
| Hypogeum H2 (hidden) | y=-13 | The lanista's office, the plates corridor, the treasure chamber, the lower stretch of Commodus's passage. |

The text plans (reachable cells) and the renders are in [`coliseo/`](coliseo/); they are regenerated with
`python3 tools/gen/uniques/colosseum/audit.py --blueprints`.

## Player route

1. Any arch of the ground floor leads to G1. From G1: taverns, tunnels to the arena, passages to the boxes and stairs to G2.
2. G2 → vomitorium → walkway I → stands → upper terrace (view and the velarium chest).
3. Arena: the central shaft goes down by ladder to the hypogeum's central corridor; you can also go down by the staircase
   that leaves G1 to the west (next to the Libitinarian Gate) and comes out in the barracks' vestibule.
4. H1: barracks (chest, skeleton spawner), beast cells (the tamer's chest, spider and
   zombie spawners), the armory corridor with the tripwire trap, armory (chest).
5. Puzzle 1 in the armory → iron trapdoor → stairs to the lanista's office (H2, rare chest) → corridor with a
   plate trap → treasure chamber.
6. Alternative: puzzle 2 in the imperial box → Commodus's passage (a chapel with a rare chest, a spawner) → the treasure chamber
   from the south.
7. Treasure chamber: the Champion of the Arena and the premium chest on the dais.

## Chests (11)

| Chest | Where | Table |
|---|---|---|
| NE tavern / SW tavern | G1, rooms under stands II | `taberna` |
| Velarium | The attic niche on the upper terrace | `velario` |
| Editor's box | North box | `palco_menor` |
| Imperial box | Next to the throne, south box | `palco` |
| Barracks | H1 west | `barracones` |
| Tamer | South-east beast cell | `fieras` |
| Armory | H1 east | `armeria` |
| Commodus's chapel (hidden) | Passage landing, H1 | `cripta` |
| Lanista (hidden) | H2 under the armory | `lanista` |
| Premium | Dais of the treasure chamber | `premium` |

## Puzzles, traps, spawners and guardian

- **Puzzle 1, "the offering"** (armory): a pedestal with an empty item frame; behind it, a comparator reads the frame and powers an
  iron trapdoor in the floor. Any item in the frame opens it. Everything is off when generated (empty frame,
  comparator without signal, trapdoor closed): it does not depend on any update.
- **Puzzle 2, "the emperor's niche"** (imperial box): in the west wall there is a blind niche and, in the same wall,
  a lever. The back wall of the niche is a flush piston door: two extended sticky pistons
  hold it, powered by a redstone torch on the hidden face of the lever's block. When the lever is pulled down the
  torch turns off, the pistons pull in the two blocks and Commodus's passage opens; when it is raised it closes.
  The consistent states are saved (torch lit, pistons extended with their head, lever off), so
  nothing changes when generated. The test `tools/smoke/colosseum_redstone.py` checks it on a real server.
- **Trap 1** (armory corridor): a tripwire from side to side; each hook activates the block it is
  attached to and that one the arrow dispenser above it, which fires at chest height.
- **Trap 2** (plates corridor, H2): three stone plates; each one activates the two wall dispensers
  next to it, at floor level.
- **Spawners**: spiders (north beast cell), zombies (south beast cell), skeletons (barracks), skeletons
  (lower stretch of Commodus's passage). They are far from any light (the audit computes the block light and requires 0 within their
  spawning radius).
- **Guardian**: the Champion of the Arena, a husk (it does not burn in the sun and fits the savanna) with `PersistenceRequired`,
  40 health, gold helmet, iron chestplate and boots, chainmail leggings, iron sword and shield; a low chance of
  dropping its equipment.
- No villagers or golems: it is an abandoned ruin.

## Ruin (target 80-85 % in good condition)

- Collapsed stretch: 5 of the 40 bays to the northwest. The attic and the third order drop to a broken line, stands II
  and the terrace turn into a slope of rubble (cobblestone, sandstone, coarse dirt with dead bushes) that leaves
  the G2 vault in sight.
- Cornices: stretches of the string courses (y=6, 12, 18) and of the upper cornice are missing, and there are notches in the crown.
- Loose seats broken or missing (a few, deterministic).
- Piece processor: smooth and cut sandstone weather to sandstone (6 %); in the hypogeum the stone bricks
  crack (15 %) or grow moss (6 %).
- The audit measures the exposed surface (the top face of each column and the façade) and the damaged percentage.

## Loot

Modest smaller chests, richer the more hidden they are; each chest has an extra `solo_sin_lootr` pool.
Vanilla items only, no netherite gear or elytra.

- `taberna`, `barracones`, `fieras`, `velario`: food, string, leather, bones, iron nuggets, buckets, leads.
- `palco_menor`, `palco`, `armeria`: small amounts of gold and emeralds, worn iron or chainmail gear, a shield,
  arrows, golden carrots.
- `cripta`, `lanista`: ingots, emeralds, a random enchanted book, a golden apple, horse armor, a name tag.
- `premium` (90 % showy): a named trophy (the Champion's Gladius, the Helm of Victory, the Shield of the
  Coliseum or the Laurel Crown) with moderate enchantments, two among armor trims (sentry, wayfinder,
  shaper, host, raiser) and discs, gold, emeralds and the odd diamond; **10 %**: something stronger (the
  Emperor's Sword, an enchanted diamond sword, or an enchanted golden apple).

## Against the owner's criteria

- Stairs: every level change is made with steps or complete ladders; its own audit walks
  without jumps and requires a way back from every reached cell.
- Doors: only doors with an exit; the secret ones are checked open (path) and closed (the chamber cannot be reached).
- Nothing floating: lanterns on a chain or ceiling, chains with an anchor, a check for solid blocks without support after the ruin.
- Symmetry: an elliptical plan symmetric on both axes except for the ruin and the boxes (imperial to the south, editor to the north).
- Every element with a function: arches and galleries for circulation, vomitoria, lifts, cells, barracks, armory.
