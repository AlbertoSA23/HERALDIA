# Lost Mine of Hondavena (`heraldia:unicas/mina_perdida`)

A Crown mining colony carved into a great cavern under the caves. Tizón, the foreman, found a vein of
gold and promised he would make everyone rich; when the old face collapsed and the Crown closed the mine, the miners went up
the shaft and he stayed below, next to the vein. It is **the first underground unique structure**: from outside only the
wooden headframe over the main shaft can be seen.

It is an original structure: it does not copy any mine or colony from another game or mod. It differs from the Dwarven citadel
(also carved out) in that it is not in a mountain and has no façade: it is a colony of human miners in a cavern,
with the mining trade (shaft and winding gear, minecarts, smelter, timbering, veins) as its theme.

## Biome, height and placement

- Biomes: **lush caves** and **dripstone caves** (`minecraft:lush_caves`, `minecraft:dripstone_caves`),
  measured **at the height of the cavern**, not at the surface. Not the deep dark (`deep_dark`, of the ancient cities) nor
  `#c:is_cave` (which includes it). No conventional tags.
- **Height**: the floor layer of the great cavern is at **y = 20** (`obra.PISO`); the mother lode goes down to y = 9 and the
  bottom of the chasm to y = 4; the top face of the colony is at y = 46. Why:
  - below sea level (63), so even on low terrain there is plenty of rock above the vault;
  - above y ≈ 8, where deepslate, the deep dark and the ancient cities (y ≈ -51) and the trial
    chambers (y -40 to -20) begin; the shell below y = 8 is deepslate so that the change is not noticeable;
  - it is the band where lush and dripstone caves are most abundant;
  - the shaft is 10 to 80 blocks (more, and the ladder would be endless: then it does not appear in that cell).
- **Grid**: `heraldia:rejilla` with `bioma` (the structure's tag) and the new field `bioma_y` = 26 (the center
  of the cavern): each cell's candidate is the point of the 128-block mesh deepest in those caves **at that
  height** (`GridPlacement`; without `bioma_y` it looks at y = 64, like the laboratory). One every 3,000-5,000 blocks by
  default, configurable like all of them (`unicas.mina_perdida.activada`, `unicas.mina_perdida.separacion_bloques`).
- **Custom type `heraldia:mina`** (`unicas/mina/MinaStructure.java`): in the candidate chunk it tries a 5 x 5 mesh of
  points (every 16 blocks) with the center of the cavern in the biome and counts how many of four sample points (15-20
  blocks away) are too (it only reads the biome noise, ~20 µs per point). For the best three it looks at the terrain above
  the shaft and the four corners of the headframe with `OCEAN_FLOOR_WG`/`WORLD_SURFACE_WG` (`comun/Alturas`, 5 columns):
  dry (no sea, river or lake), with less than 5 blocks of drop and a shaft of 0 to 80 blocks. The first that qualifies
  gives the pieces: the **colony** at a fixed y, the **shaft sections** (8 blocks, and 1 for the rest) from the colony's top
  face and the **headframe** with its floor on the terrain. If none qualifies, nothing is generated. `/place structure` (which
  accepts any biome) puts it in the chunk as is.
- Adaptation `none` and step `underground_structures`. The headframe brings its own 6-block cobblestone foundation
  (it absorbs the drop) and explicit air above its whole footprint (14 x 9, up to 12 blocks).

## The colony is not a box: the shell

The colony is a single template (108 x 45 x 82) that **only holds what is excavated** (air and water), its **lining** on each face
facing the excavation and **two layers of solid rock** around it (`obra.forro` and `obra.casco`); outside, nothing (structure_void),
so the terrain is kept. That is why:

- a vanilla cave passing nearby sees irregular rock, not the flat faces of a box;
- no hollow of the colony touches the outside: the audit checks that every excavated cell has its 6 neighbors in the
  template (except the shaft's opening, which continues in the section above), so **no natural water or lava gets in** from the
  aquifers or the caves, and the corridors do not open onto them;
- **the linings are never natural blocks** (cobblestone, cobbled deepslate, stone brick, planks, brick,
  deepslate tiles): no water or lava springs appear inside, nor glow lichen (which would give light to the
  spawners), moss or the clay pools of the lush caves (`#base_stone_overworld`, `#moss_replaceable`,
  `#lush_ground_replaceable`). The audit fails if a natural block faces a dry cell (the gravel of the
  rubble and of the lake bed and the sand of the bed are allowed). Vanilla ores can appear in the shell's rock. In
  lush caves, vines with glow berries may hang from the ceiling (they need a solid ceiling, not a natural block).
- The shaft goes through caves and aquifers with 1 block of stone outside the plank lining.
- Vanilla structures of the same step (abandoned mineshafts) that cross it: they are generated first and the colony writes over
  its shell; a vanilla corridor can end against the shell's rock. Deduced from the order of the steps; not seen in a real
  world.

## Route (feet at y = 1 in the cavern)

Coordinates of the build: x from west to east, z from north to south; the shaft goes down at x = 44, z = 7. Plans by level in
[`mina_perdida/planos.txt`](mina_perdida/planos.txt); renders `colonia.png`, `colonia_corte.png` and `castillete.png`.

- **Headframe** (surface): four spruce uprights with beams, braces and a small roof; from the master beam
  hangs the bucket's chain, which goes down to the bottom. A cobblestone curb with the ladder, the **winding
  house** (the winch drum, the `malacate` chest) and the spoil heap. Sign: "Hondavena Mine. Main shaft. Closed
  by royal order".
- **Main shaft**: a 3 x 3 opening with the ladder and the chain, a plank lining with a log frame every 4
  blocks. At the bottom, the bucket (a cauldron) in the **shaft station** (the `estacion` chest, barrels, the shaft sign).
- **The great cavern** (a 55 x 43 superellipse, a vault 5 to 16 blocks high with noise): a cobblestone floor, a square of polished
  andesite around the **master pillar** (the rock the miners left to hold up the vault) with the colony's
  signs; lanterns hanging from the vault and loose rubble along the walls.
- To the north: the **storehouse** (barrels, two `almacen` chests) and the **smelter** (four blast furnaces under a brick
  hood, two lava cauldrons, an anvil, coal and raw ore, the `fundicion` chest).
- To the west, the **miners' houses** carved into the rock, with a straight stone brick façade, a door, windows
  and a porch: three dwellings (`vivienda` chests; the southern one with its roof caved in) and the **foreman's house**.
- To the east, the **smithy** and the **carpentry** (`herreria` and `carpinteria` chests).
- To the south, the **underground lake** (water 3 deep with a bed of gravel and sand) with its plank **landing** on
  piles (the `embarcadero` chest, a moored boat) and, on the south shore, the **boat shed**.
- To the east, the **chasm** (5 x 23, from y = 4 to y = 28) with the **rope bridge**: planks, railings and chains up to the
  ceiling; it is missing planks and railing at the edge. A ladder goes down to the bottom, with the bones of those who fell,
  a **skeleton spawner** and the `sima` chest.
- Beyond the bridge, the loading bay gallery with **trap 1** (a tripwire between the jambs, two arrow
  dispensers above the hooks) and the **loading bay** (the `cargadero` chest), with the **switch puzzle**.
- South of the loading bay, the **old face**: a gallery with track (missing sleepers) and a work room with **veins in
  sight** (coal, iron, copper, gold, redstone and lapis lazuli), rubble, cobwebs, a **zombie spawner** and the
  `frente` chest. Sign: "Old face. Closed because of the collapse".
- To the southwest, the **collapsed sector**: the old gallery with a broken track, a fallen prop and a collapse that leaves a way through
  the middle; **trap 2** (a plate over TNT, "the forgotten charge", with cracked tiles as a warning); the collapse
  chamber (cobwebs, a **cave spider spawner**, the `derrumbe` chest) and a 6-step staircase to the **flooded
  sector**: a gallery flooded 3 deep with a plank walkway (broken in one stretch) and the `inundada` chest at the
  bottom, under the water.
- **Mother lode** (behind the floodgate, feet at y = -10): an 11-step staircase goes down to a slate chamber with gold
  veins, a column of raw gold and amethyst geodes, where **Tizón, the last foreman** waits (the `filon` chest); to the
  west, the **treasure chamber** with the `premium` chest between two gold blocks.

## Puzzles, hidden rooms and traps

1. **The loading bay switches** (`vias.py`). A minecart waits at the start, an unpowered booster rail against the east
   wall; the "Start" lever launches it to the west. Three boosters with a redstone block underneath keep it going
   (an empty minecart brakes a lot). The track goes through two **switches** (T junctions) with their floor lever:
   - without touching anything, switch 1 takes it south, to the **spoil heap**;
   - with switch 1 to the north and switch 2 powered, to the west, to the **smelter's dead-end siding**;
   - only with switch 1 to the north and 2 unpowered (to the east) does it reach, by a ramp and a **1 x 1 gap in the wall**
     (a person does not fit), the **weighbridge**: a detector rail. While the minecart weighs on it, its support block
     turns off the inverting torch that holds the **floodgate** of the mother lode (two extended sticky pistons, like
     `piezas.lever_door`), and the floodgate opens; if the minecart is removed, it closes.
   The clue is in the foreman's office ("To the weighbridge: switch 1, north; switch 2, east"). The switch rule in 26.3
   (`RailState.place`, read in the bytecode): with three neighbors, without a signal the last of NW, NE, SW, SE with its two
   neighbors wins; with a signal, the last of SE, SW, NE, NW. The audit reproduces it (`vias.forma_aguja`), follows the minecart
   along the track in the 4 combinations (`vias.recorrer`) and requires only the correct one to reach the weighbridge; the shared simulator
   (`_comun/redstone`, which now treats the detector rail like a plate) checks the floodgate's rest state, that the
   weighbridge opens it and that no lever in the loading bay touches it. The server test does it with a real minecart.
2. **The foreman's office** (a hidden room with a puzzle): in the west wall of his house (two thick), a brick
   panel slides back to the north inside the wall when the lever in the built-in bookshelf in the corner is pulled down
   (`piezas.lever_door`). Inside, the `despacho` chest with the **Chronicle leaf**, a lectern, bookshelves and the sign with the
   switches clue.
3. **The stash** (a hidden room without a puzzle): behind the blue tapestry at the back of the boat shed, a 1 x 2 passage leads to the
   hideout of the gold smugglers (the `alijo` chest).
4. Traps: the **tripwire** at the mouth of the loading bay and the **forgotten charge** (a plate over TNT) in the collapsed
   sector.

## Enemies and loot

- Three spawners (skeletons at the bottom of the chasm, zombies in the old face, cave spiders in the collapse
  chamber), in the dark: the audit propagates block light and requires 0 in their volume.
- Guardian: **Tizón, the last foreman**, a vindicator (the game gives it the axe when it spawns) with an iron helmet and
  a dyed leather apron, 70 health, armor 6. Trophy: **Tizón's Pickaxe** (Efficiency 2, Unbreaking 2).
- **21 chests** (20 in the colony and one in the headframe), richer and richer: provisions and mining tools at the top;
  raw ores, ingots and tools with moderate enchantments in the galleries; gold, diamonds and named
  items in the hidden rooms and the lode; the **premium chest** (90 % showy: the Crown's Ingot, the Lantern of the Last
  Watch, the Miner's Helmet, the Timberman's Pickaxe, the Well-digger's Compass, armor trims, discs; 10 % something stronger:
  an enchanted diamond pickaxe, shovel or chestplate, an enchanted golden apple or a totem). No netherite or elytra. With Lootr,
  each table loses its extra pool (`solo_sin_lootr`).
- The Chronicle leaf in the `despacho` chest.

## State of conservation

16 % of the visible surface is damaged (audit, `auditoria.estado`: faces facing the excavation, not counting
floors): collapses of gravel and cobblestone, the house with the caved-in roof, the fallen prop, missing planks and railing on
the bridge and the walkway, torn-out sleepers, a fallen track at the bottom of the chasm, and the colony's processor (cracked or mossy
brick, mossy cobblestone). Nothing that holds up a mechanism falls: the processor only changes the look.

## Performance

- Generation: `findGenerationPoint` reads up to 25 + 100 points of the biome noise and, at most, 3 x 5 height columns
  (cached); the grid's candidate already falls in the biome. Templates: the colony, 83,000 blocks written (shell
  included; no solid box), the headframe 2,400, the shaft sections 392 and 49. Entities: the guardian, the puzzle's minecart and
  a boat. Nothing per tick, no new mixins. Times measured in the PR (server test).
- Datapack generation: ~3 s for the whole build with its audit.

## Checks

- Its own audit (`auditoria.py`, a condition for generating): the redstone's rest state; the 4 switch combinations;
  the floodgate, the office and the traps with the shared simulator; a walk with the puzzles closed and solved
  (`lint.walk` and `recorrido.andar`, without falls of more than one block and swimming, with a way back to the entrance from anywhere
  and the climb up the shaft's ladder to the top); supports, doors, stairs (`lint`); spawner light;
  natural blocks in sight; a closed shell; loose blocks; damaged surface; number of chests; the headframe (the chest
  and the shaft's ladder can be reached). Tested with deliberate failures (changed solution, removed torch, panel
  open, a lantern next to a spawner).
- `prueba_servidor.py` (in the CI matrix): `/locate` and natural generation (the guardian in its place, the cavern in
  its cave biome, the shaft's chain from the colony to the headframe and open air above), `/place structure` with its
  time and its entities, and the templates unrotated: chests, spawners, water, the switch puzzle with a real
  minecart at the three exits, the office and the two traps.
- No screenshots from the game: the look is not confirmed.
