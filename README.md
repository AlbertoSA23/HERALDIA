# Heraldia

**English** · [Español](README.es.md)

Fabric mod for **Minecraft 26.3** dedicated solely to generating new structures in the Overworld.
All current content is vanilla (blocks, items and loot from the base game).

Development guide (in Spanish): [docs/DESARROLLO.md](docs/DESARROLLO.md).

Contents:

- **Huge villages**: 72 structures (36 biome styles, each in a standard and a large size).
- **Atlantis**: a single sunken city per world (see below).
- **Wave arena**: a coliseum near spawn to play in waves, with records and rewards (see [Wave arena](#wave-arena)).
- **Unique structures** (one every 3,000-5,000 blocks, each in its own biomes):
  - **Eastern palace** (`heraldia:unicas/palacio`, cherry groves and bamboo jungles): walled compound of 81 × 123 with three courtyards on one axis, a throne room on a three-step platform, a library with a secret study, a treasury with a vault, a garden with a pond, a five-storey pagoda and the concubines' pavilions; beneath the throne, the treasure chamber with its guardian. Secret piston doors, arrow traps and two spawners. Design and plans: [docs/unicas/palacio.md](docs/unicas/palacio.md).
  - **Ice fortress** (`heraldia:unicas/fortaleza_hielo`): ice spikes, snowy plains and snowy taiga. Ice walls and
    towers on a plinth with crypts, two secret piston doors, traps, stray and skeleton spawners, the guardian
    Frost King and 11 chests. Design: [docs/unicas/fortaleza_hielo.md](docs/unicas/fortaleza_hielo.md).
  - **Dwarven citadel** (`heraldia:unicas/ciudadela`): stony and jagged peaks. A city carved into a mountain with
    its gate on the hillside: pillared hall, throne, forges, brewery, mines, a bridge over a chasm and a treasure vault;
    four hidden rooms, two redstone puzzles, two traps, three spawners and the guardian Borin Ironbeard.
    Design: [docs/unicas/ciudadela.md](docs/unicas/ciudadela.md).
  - **Pyramid temple** (`heraldia:unicas/piramide`): jungle and sparse jungle. A stepped Mesoamerican pyramid with a
    temple and roof comb, a ball court, a hidden staircase, an inner cenote with a submerged chamber and the tomb of the
    Jaguar King behind a secret piston door; tripwire, pit and dart traps, 4 spawners and 13 chests.
    Design: [docs/unicas/piramide.md](docs/unicas/piramide.md).
  - **Jarl's Hall** (`heraldia:unicas/salon_jarl`): taiga and old growth taigas. A 74 × 74 fortified Norse settlement with
    a log palisade, four towers and a gatehouse with a guard room, a longhouse with a central hearth, a dais and two
    thrones, a smithy, stables, a shipyard with a half-built longship, warriors' houses, a storehouse and rune stones;
    behind a tapestry, the jarl's hidden bedchamber. Under the longhouse lies the barrow of the kings: a gallery of burial
    niches, an ossuary, the offerings hall, the wall of runes (puzzle) and the chamber of Jarl Ulfgrim the Unburied, with
    the treasure; a secret door to the skald's chamber, tripwire and TNT traps, 3 spawners and 18 chests.
    Design: [docs/unicas/salon_jarl.md](docs/unicas/salon_jarl.md).
  - **Druid Sanctuary** (`heraldia:unicas/santuario`): birch forest and old growth birch forest. A glade ringed by
    standing stones around a huge sacred birch, whose hollow trunk holds a spiral stair up to a platform under the crown
    and down to the roots; round druid huts (behind a tapestry, the archdruid's hidden alcove), a herb garden with
    beehives, a stone pond and an observatory of aligned stones. Under the tree: the root hall, the library with a secret
    bookshelf to the archive, the herbalist's room, an ossuary, the offerings niche, the chamber of the sun (puzzle: light
    the solstices) and the rite chamber of Archdruid Cadoc the Withered, with the treasure; tripwire and pressure-plate
    traps, 3 spawners and 18 chests. Design: [docs/unicas/santuario.md](docs/unicas/santuario.md).
  - **Mycologist's Laboratory** (`heraldia:unicas/laboratorio_micelio`): mushroom fields. An old botanical garden built
    among and inside three giant mushrooms: the mycologist's house in the cap of the big red one (behind a tapestry, his
    hidden alcove), with a spiral stair down its stem; the helpers' dormitory in a small red cap and the spore library in
    the stem of a brown one, with a drying terrace on its cap, all linked by walkways; a glass greenhouse with rare crops
    (nether wart, torchflower, cocoa, chorus), a potion distillery and the mooshroom pen. Under the mycelium, damp
    glowing galleries: the nurseries, the laboratory with a secret stem panel to the strain archive, a tripwire corridor,
    the cocoon room, the failed experiments, the reagent room (puzzle: mix the cure) and the chamber of the mother strain
    with Master Ambrose the Spore-Ridden and the treasure; tripwire and pressure-plate traps, 3 spawners and 22 chests.
    Design: [docs/unicas/laboratorio_micelio.md](docs/unicas/laboratorio_micelio.md).
  - **Lost Mine of Hondavena** (`heraldia:unicas/mina_perdida`): the first **underground** unique, under lush caves and
    dripstone caves (the biome is checked at cavern height, y ≈ 26; one every 3,000-5,000 blocks). Only the timber
    headframe over the master shaft shows at the surface; the shaft (ladder and hoist chain) goes down to a Crown mining
    colony dug into a great cavern at y = 20: shaft station, storehouse, foundry with blast furnaces, miners' houses cut
    into the rock, smithy and carpentry, an underground lake with a landing and a boat, a chasm with a hanging bridge, the
    loading bay with the **switch puzzle** (send the minecart through two track switches to the weighbridge, which opens
    the lode chamber), the old face with exposed ore veins, and a collapsed and flooded sector. The foreman's secret
    office (behind a bookcase), a smugglers' stash behind a tapestry, a tripwire trap and a forgotten blasting charge,
    3 spawners, the guardian Tizon, the Last Foreman, and 21 chests. The colony is carved in solid rock with its own
    hull: no water or lava gets in and nearby vanilla caves only see rough stone. Design:
    [docs/unicas/mina_perdida.md](docs/unicas/mina_perdida.md).
  - **Lighthouse with smugglers' cave** (`heraldia:unicas/faro`, stony shore and beaches): a lighthouse and keeper's house on a headland; a secret passage to a sea-level cave with a dock, storerooms, a dungeon, the captain's office and a treasure chamber. It is always placed on the coastline, with the cave mouth facing the sea. Design: [docs/unicas/faro.md](docs/unicas/faro.md).
  - **Wizard's tower** (`heraldia:unicas/torre_mago`): dark forest and pale garden. An eight-storey tower with a
    double-height library, a laboratory, a greenhouse and an observatory, a study hidden behind a chiseled bookshelf,
    an experiments basement with spawners and traps, the guardian Archmage Malvarius and 16 chests. Design:
    [docs/unicas/torre_mago.md](docs/unicas/torre_mago.md).
  - **Ruined coliseum** (`heraldia:unicas/coliseo`, savanna and savanna plateau): an elliptical amphitheater with stands, boxes and a hypogeum with beast cells, an armory, two redstone puzzles, two traps, four spawners, the Arena Champion and a hidden treasure chamber. Design: [docs/unicas/coliseo.md](docs/unicas/coliseo.md).
  - **Castle** (`heraldia:unicas/castillo`): plains, sunflower plains and meadows. A 100 x 100 fortress with a moat,
    curtain wall, barbican, bailey, keep and a dungeon with cells, traps, three spawners, the guardian
    Sir Aldric and the hidden treasure chamber; 36 chests. Design: [docs/unicas/castillo.md](docs/unicas/castillo.md).
  - **Mountain monastery** (`heraldia:unicas/monasterio`; meadows and groves): terraces on a crag, a church, a cloister and caves with puzzles, traps, a guardian and a premium chest. Design: [docs/unicas/monasterio.md](docs/unicas/monasterio.md).
  - **Observatory** (`heraldia:unicas/observatorio`): windswept hills and windswept savanna plateau. A copper dome with a
    telescope, a planetarium, an optics workshop, a sundial and, beneath the rock, an archive with two hidden rooms, the moon-phase
    puzzle, two traps, three spawners and the guardian Keeper of the Stars. Design: [docs/unicas/observatorio.md](docs/unicas/observatorio.md).
  - **Haunted mansion** (`heraldia:unicas/mansion`): swamp and mangrove swamp. A Victorian estate with a turret, a ruined
    greenhouse and a cemetery with a mausoleum; beneath the house, behind a secret bookshelf, a basement with a laboratory and a treasure
    chamber locked by a lever combination; two traps, three spawners, the guardian Count Malachias and 33 chests.
    Design: [docs/unicas/mansion.md](docs/unicas/mansion.md).
  - **Gothic cathedral** (`heraldia:unicas/catedral`): forests and flower forests. A facade with two towers and a rose window, a nave with
    triforium and flying buttresses, a crossing with a spire, an ambulatory with chapels, a sacristy, a library, a cloister and, underground, a crypt,
    ossuaries and a treasure chamber; two secret doors, a hidden trapdoor, two traps, three spawners, the guardian
    Friar Osmundo and 19 chests. Design: [docs/unicas/catedral.md](docs/unicas/catedral.md).
  - **Ruined aqueduct** (`heraldia:unicas/acueducto`, desert and badlands): a two-tier aqueduct, an abandoned Roman city, a cistern and sewers with the treasure chamber. Design: [docs/unicas/acueducto.md](docs/unicas/acueducto.md).
  - **Stranded galleon** (`heraldia:unicas/galeon`, beaches and snowy beaches): a three-masted galleon run aground on the shore
    (placed by looking for water), with a hold, a cannon deck, castles, a cabin and the treasurer's secret chamber;
    a castaway camp with archaeology and a cave with the lantern puzzle, traps, four spawners and the
    guardian The Drowned Captain; 18 chests. Design: [docs/unicas/galeon.md](docs/unicas/galeon.md).
  - **Corsair's Isle** (`heraldia:unicas/isla_corsario`): temperate and warm oceans, in open sea, far from the coast
    and outside Atlantis (found with the biome noise and the sea floor). Its own islet, about 84 × 74 blocks, with its
    rock, sand and palm trees: on the hill, Roque Salitre's fort (curtain wall with a wall-walk, a bastion with four
    cannons, the corsair's house, barracks and cistern); in the south, the harbour with the pier and a brigantine afloat
    at its moorings, the Hanged Mermaid tavern (with a hideout behind a tapestry in the cellar), the warehouses and the
    gallows, and a small lighthouse on the western point. Beneath the hill, the sea caves: the hidden cove (entered by
    boat through the cliff), the guardroom, the map room with the **compass rose puzzle**, the armoury with the secret
    powder room, the dungeons and, below sea level and dry, the treasure chamber with Roque Salitre, the Corsair;
    tripwire and pressure-plate traps, 3 spawners and 21 chests. Design: [docs/unicas/isla_corsario.md](docs/unicas/isla_corsario.md).
- **Medium structures** (all types together, one every 550-580 blocks, each in its own biomes): watchtowers, roadside
  inns, bandit camps, hermitages, mills, fisher's huts, hunters' lodges and ruined shrines, with a style for each biome. See [Medium structures](#medium-structures).
- **Mine entrances** (on real hillsides of hills, taigas, deserts, badlands and peaks): adits, mining camps and mining
  complexes with a headframe, each leading down to its own gallery; and more vanilla abandoned mineshafts in new chunks
  (x2 by default). See [Mine entrances](#mine-entrances).

## Installation

Requirements: Minecraft 26.3, Fabric Loader 0.20.1 or later and Fabric API (tested with 0.166.2+26.3). Optional on the client: Mod Menu (built against 21.0.1), for the [configuration screen](#configuration-screen-client).

1. Build `heraldia-<version>.jar` (see below).
2. Copy it into the `mods` folder of the server and of every client.
3. Start the server. `logs/latest.log` should show `Heraldia: 142 estructuras registradas`.

In an existing world, structures only appear in chunks that have not been generated yet.
`/reload` does not reload world generation: you must restart the server (or leave and re-enter the world in single player).

## Test commands

- Place a village where you stand: `/place structure heraldia:llanuras_castellana` (or `..._grande`). It works even outside its biome.
- Find the nearest one: `/locate structure heraldia:llanuras_castellana`
- Place a single piece: `/place template heraldia:llanuras_castellana/specials/church`
- `/function heraldia:muestrario`: places all 72 villages in a grid starting where you stand (each row, heading south, is a family; in each row go the 3 styles and then their large versions, heading east, 300 blocks apart). It puts you in spectator mode and takes you from one to the next, one every 8 s (about 10 min). When it finishes you return to creative.
- `/function heraldia:familia/<family>` (`llanuras`, `bosque`, `oscuro`, `taiga`, `nieve`, `desierto`, `sabana`, `jungla`, `pantano`, `cerezos`, `badlands`, `costa`): the same with the 6 villages of one family, in a row heading east.
- `/function heraldia:muestrario/parar`: stops it.
- `/heraldia llave <players> <key>` (operators, level 2): gives the keys of the locked chests of the unique structures, the same item you get in the game. `<key>` autocompletes: `todas` (all), a structure (`atlantida`: its four keys) or a single key (`atlantida.arsenal`, `atlantida.academia`, `atlantida.anfiteatro`, `atlantida.poseidon`). If the inventory is full, the key drops on the ground for that player.
- `/heraldia info` (operators, level 2): summary of the configuration in use (villages, enabled unique structures and their spacing, minimum distance, per-player chest, whether Lootr is installed, medium structures, mine entrances and the vanilla mineshaft multiplier) and how many structures are registered.
- `/heraldia info cerca [radius]`: the nearest unique structure and medium structure of each type, mine entrance of each size and the nearest Heraldia village, with distance, direction and coordinates (click them to get a `/tp` command). It uses the same check as `/locate`, so it never points to a structure that the minimum distance discards, but it neither loads nor generates chunks: what has not been generated yet is shown as "predicted" (for a predicted village only its family is known). Default radius 3,000 blocks, maximum 10,000; the message says how long the search took.
- `/heraldia guia` (any player, no permissions needed): gives you an up-to-date copy of the [Herald's Guide](#heralds-guide) (if you carry one in your inventory, it is replaced by the new one).
- `/heraldia info aqui`: which Heraldia structure you are standing in (name and id) and, in a unique structure, whether its guardian is alive (only answered when the whole structure is loaded).

Use the showcase only in a test world: whatever it places stays.

## Huge villages

By default, one village every 1000-2000 blocks (average spacing 1500), at most 100 per world (the ones closest to 0,0) and never within 10 chunks of a vanilla village. The standard version appears 3 times as often as the large one. All of this can be changed in the [configuration](#configuration).

| Family | Biomes | Styles (ID `heraldia:<style>` and `heraldia:<style>_grande`) |
| --- | --- | --- |
| Plains | plains, sunflower plains, meadow | `llanuras_castellana`, `llanuras_gallega`, `llanuras_entramado` |
| Temperate forest | forest, flower forest, birch forest (and old growth), dappled forest | `bosque_lenadores`, `bosque_elfica`, `bosque_abadia` |
| Dark forest | dark forest, pale garden | `oscuro_gotica`, `oscuro_alquimistas`, `oscuro_fortificada` |
| Taiga | taiga, old growth taigas | `taiga_nordica`, `taiga_eslava`, `taiga_cazadores` |
| Snow | snowy plains and taiga, grove, ice spikes | `nieve_alpina`, `nieve_fortaleza`, `nieve_pastores` |
| Desert | desert | `desierto_andalusi`, `desierto_obelisco`, `desierto_caravanera` |
| Savanna | savanna, savanna plateau | `sabana_paja`, `sabana_terracota`, `sabana_pastores` |
| Jungle | jungle, sparse jungle, bamboo jungle | `jungla_arboles`, `jungla_templos`, `jungla_bambu` |
| Swamp | swamp, mangrove swamp | `pantano_palafitos`, `pantano_brujas`, `pantano_turba` |
| Cherry | cherry grove | `cerezos_japonesa`, `cerezos_templo`, `cerezos_artesanos` |
| Badlands | badlands, eroded and wooded badlands | `badlands_minera`, `badlands_roca`, `badlands_canon` |
| Coast | beach, snowy beach, stony shore | `costa_pescadores`, `costa_mercante`, `costa_mediterranea` |

Each village has:

- A main square with a fountain, benches, trees, a bell and two golems.
- Four avenues with the special buildings: a church or temple depending on the style (with cemetery and crypt), town hall, market, tavern, smithy, library, farm with windmill and inn. Each special building comes in three variants per style with a different floor plan and silhouette and the same function (for example the church with a front tower, with a transept and bell gable, or with a porch and the tower at the apse; the market open, as a covered hall or as an arcaded square), drawn at random for each village, so two villages of the same style differ in their main buildings. Sheets: [docs/aldeas/variantes.md](docs/aldeas/variantes.md). On the coast there is also a harbor (harbor house and a pier with piles, crane and boats) on the free shore nearest to the square, with the pier facing the open sea; every shore within about 96 blocks along the coast is tried, and if only houses, fillers or towers stand in the way, the harbor takes their place. If no shore fits (they are all taken by the square, special buildings or streets reaching the sea, or there is no water nearby), the village has no harbor.
- About 20 houses in the standard size and about 30 in the large one, furnished, with chests in some and loot from common to epic (tables `heraldia:cofres/comun`, `poco_comun`, `raro`, `epico`).
- Watchtowers and wall gates at the ends of the streets; themed decoration between houses.
- Villagers: half the number of houses, over 80 % with a profession. Golems: at least one per 3 villagers.

Population limits: there are about 1.25 beds per initial villager, so the population grows by 25 % at most.
The function `heraldia:golems` checks loaded villages every 30 s and removes one natural golem each time there are 8 or more (standard) or 9 or more (large); it does not touch player-built ones. Limits and cleanup can be changed in the [configuration](#configuration).

## Village life

Heraldia villages have trades with character, a job board and, in the fortified ones, sieges. Everything can be turned off in the [configuration](#configuration) (`aldeas.vida.*`).

- **Style trades** (`aldeas.vida.tratos_estilo`, on): in each style, one profession offers a trade with its character (vanilla items only, with a name, trims or moderate enchantments): the Militia Sword of the Castilian weaponsmith, the Copy of the Chronicle of the Heralds of the abbey librarian, the Dune Breastplate (sand-dyed leather with a gold trim) of the obelisk armorer, the Jarl's Mead of the Norse butcher, the Skipper's Rod of the fishermen... Besides, the cartographer of each family sells at level 3 (16 emeralds and a compass) the map of the unique structure of its area (castle in the plains, Jarl's Hall in the taiga, Stranded Galleon on the coast...). The trades are drawn like the vanilla ones when the villager levels up: a villager of that profession and level offers it with a probability of 1/2 to 2/3 (or always, at levels with a single vanilla trade), so a large village usually has one. Only Heraldia villagers inside a village of that style; also in villages already generated, for villagers that level up from now on.
- **Job board** (`aldeas.vida.tablon`, on): on the square, next to the fountain, a lectern with the book "Job Board" and, behind it, the **bailiff** (a named villager who neither moves nor takes damage) who pays for delivery jobs with his trades: *Harvest for the granary* (32 of the family's crop: wheat, potatoes, berries, cactus, cocoa... for 4 emeralds), *Firewood for winter* (32 logs of the style's wood for 3) and *Clear the roads* (16 rotten flesh and 8 bones for the Watch Cloak, a leather chestplate in the banner colour with Protection II). He has work for a few deliveries (no restocking). Deeds are paid by the village once per player when they get their advancement: *Night watch* (slay a threat inside a Heraldia village: 3 emeralds) and *Defend the village* (become Hero of the Village after a raid on a Heraldia village: 8 emeralds and the Defender's Horn). **New villages only.**
- **Sieges** (`aldeas.vida.asedios`, **off**: it affects balance): in fortified villages (`oscuro_fortificada`, `nieve_fortaleza`, `badlands_canon`) the weaponsmith sells at level 3 the "Siege Challenge", a level I ominous bottle (10 emeralds, once): whoever drinks it and returns to the village triggers a vanilla raid. There is no raider outpost next to the village: raiders attack villagers within 32 blocks even without seeing them, so it would have to sit outside the village, and a large village already reaches almost the 8 chunks from its start, the furthest the game places pieces; they would also be persistent mobs loaded all the time.

Cost: one more entity per village (the bailiff, without AI) and no periodic function; trades and deeds are only evaluated when a villager levels up or a player kills, wins a raid or picks something up (vanilla advancement criteria).

## Roads between villages

Nearby Heraldia villages are joined by trails (`aldeas.caminos.*` in the [configuration](#configuration)):

- **Which villages**: each village with its nearest neighbours closer than `aldeas.caminos.distancia_maxima_bloques` (2000 by default); two villages are joined if no third one is closer to both than they are to each other, so there are no triangles and no roads crossing each other. With the default spacing (1500) almost every village has two or three roads.
- **Route**: it winds gently between the two squares, follows the terrain height and, when it fits, passes about 110 blocks from a unique structure lying halfway (with the grid in use, also the old one of `unicas.rejilla_compatible`). It stops at the pieces of a village or of any surface structure, without crossing them.
- **Surface by terrain**: dirt path (with some coarse dirt and gravel) on grass and dirt, sandstone slabs in deserts and beaches, red sandstone in badlands, gravel and cobblestone on stone and snow, packed mud in mangroves. Width `aldeas.caminos.ancho` (3 by default), with ragged edges.
- **Water**: a river or a short stretch of water (up to about 64 blocks) is crossed by a plank bridge one block above the water, with posts down to the bottom; a shallow marsh (2 blocks), by a boardwalk flush with the water; long and deep water (lakes, sea) cuts the road at the shore. It never goes over lava.
- **Lamp posts and signs**: every 48 blocks or so, on alternating sides, a fence post with a lantern or a torch (depending on the road), in the biome's wood; about 128 blocks from each village, a sign with the name of the destination village (a place name such as "Torre del Roble" or "Vado de la Encina", the same on all its signs) and the blocks left, with an arrow towards it.

Everything comes from the seed and the village grid, chunk by chunk, without loading or waiting for any other chunk: both sides of a chunk border always match. **In an existing world, new chunks only**: what is already generated does not change and the stretches that would fall in explored land do not exist (the road starts at the border). Cost, measured on the test server (`tools/smoke/caminos.py`, about 1,000 chunks): half of the chunks pay less than 32 µs and 90 % less than 128 µs; the only expensive parts are computed once per server start and kept in memory: whether a grid cell has a village (about 1.5 ms; at most 100 cells with a village), each road's waypoint (about 30 ms) and the bottom height at the vertices that fall in water (about 0.4 ms each). The mod writes these figures to the log when the server stops.

## Atlantis

Exactly one per world, always, with no configuration option. It is a walled city of about 770 × 770 blocks, fully submerged, in the deep-ocean basin closest to the origin that is 1,500 blocks or more away and unexplored (in an existing world it only appears in new chunks). The position is computed the first time the world loads and saved in `data/heraldia/atlantida.json`.

- Find it with `/locate structure heraldia:unicas/atlantida` or with its treasure map.
- Flooded streets and squares, and more than 200 houses, towers and rooms that are **dry**, entered through doors or by diving up from below. If a wall is broken, the room floods.
- Eight districts (agora, fish market, baths, arsenal, sunken harbor, coral gardens, academy and amphitheater), a temple in the center, underground galleries and, at the bottom, the final guardian.
- Defenders: guardians, drowned with tridents, 48 spawners, elder guardians in the key districts and the Guardian of Poseidon.
- Three seals with their keys, combination doors, arrow traps, water and TNT.
- 185 chests with advanced loot and a unique chest, hidden and locked with the final guardian's key, holding two legendary tridents. Its contents are fixed: the first group to arrive takes them, unless `unicas.atlantida.cofre_unico_por_jugador` is enabled (see Configuration): then each player opens their own copy.
- No other structures (monuments, shipwrecks, ruins) generate inside the city, except strongholds, which the game needs to reach the End.

Details, plans and what has been verified: [docs/unicas/atlantida.md](docs/unicas/atlantida.md).

## Medium structures

Smaller than a unique structure (15 × 15 to 21 × 21 blocks) and much more common: between villages and unique structures there was a lot of empty land. By default, all types together give **one every 550-580 blocks** (measured, see below), each type only in its own biomes and in a style that matches the biome. Modest loot (no premium chest; with Lootr, each player gets their own), few entities and, in some, a small challenge. Batches 1 and 2:

| Type | Id | Styles (biomes) | Variants |
| --- | --- | --- | --- |
| **Watchtower** | `heraldia:medianas/torre_vigia/<style>` | windswept hills and meadow (stone); taigas (cobblestone and spruce) | three floors and a roofed lookout with a skeleton archer (helmeted, it does not burn), or two floors with a woodshed and no mobs; always a signal fire on top |
| **Roadside inn** | `heraldia:medianas/posada/<style>` | plains (oak); oak, birch and flower forests (birch and dark oak); savannas (acacia and terracotta) | common room with hearth, tables and counter, the innkeeper (a villager without AI who sells bread, cooked pork and a bed, and buys wheat), a room with two beds and a chest; with a hay paddock and trough or with a vegetable garden |
| **Bandit camp** | `heraldia:medianas/campamento/<style>` | forests; taigas; badlands | canvas tents around a campfire with log benches, a barrel with the stolen goods and a banner; two pillagers, or a palisade, three tents, a vindicator chief and a pillager. They are persistent and anchored (they stay in the camp until attacked), never form a patrol and do not respawn |
| **Hermitage** | `heraldia:medianas/ermita/<style>` | groves and snowy slopes (stone bricks); dark forest and pale garden (mossy cobblestone); cherry groves (cherry and white terracotta) | chapel with bell gable and bell, pews, an altar with candles and the hermit's cell (bed, lectern and the chest with his diary, a written book in each player's language); a fenced garden with a water channel and, in one variant, a small graveyard |
| **Mill** | `heraldia:medianas/molino/<style>` | plains (oak and white terracotta); swamps (mangrove and mud bricks) | water mill with its paddle wheel in a race of still water, the millstone and the miller (a villager without AI who buys wheat and sells bread, sugar and cake), or a three-storey windmill with sails and a wheat field with its ditch |
| **Fisher's Hut** | `heraldia:medianas/pescador/<style>` | beaches (birch and sandstone); snowy beaches (spruce and cobblestone); stony shores (oak and stone bricks) | hut with a fish-drying rack and a jetty on piles, with the fisher (buys string and cod, sells cooked cod and a fishing rod) and their cat, or empty, with a smokehouse and a longer jetty with fish traps |
| **Hunters' Lodge** | `heraldia:medianas/cazadores/<style>` | snowy plains and ice spikes (spruce); savannas (acacia) | log cabin with a chimney, bunks and the pelt chest, a drying rack, a chopping block and a hunting stand; with the hunter (buys rabbit hides, sells leather, arrows and a leather tunic) and their wolf, or empty, with a meat smoker |
| **Ruined Shrine** | `heraldia:medianas/templete/<style>` | jungles (mossy stone bricks); desert (sandstone) | colonnaded shrine on a podium, with the side columns broken, their drums fallen and pots with offerings (break them to get them out); with the altar and two keepers (skeletons with helmets in the jungle, husks in the desert, anchored like the bandits), or with a sacred well and nobody |

- They never spawn inside a village, a unique structure, Atlantis or the Corsair's Isle: not within `medianas.distancia_aldeas_unicas_bloques` (256) of the start of a Heraldia village or unique structure that spawns there, nor within `medianas.distancia_minima.bloques` (192) of another medium structure of a different type (a deterministic draw keeps one, the same rule as the minimum distance between unique structures), nor within 128 blocks of a vanilla village candidate. They also give way to structures that show above ground, vanilla or from other mods (pillager outposts, temples, ruined portals, other mods' villages...): one is discarded if such a structure spawns within 80 blocks (vanilla) or 128 (other mods).
- Find them with `/locate structure #heraldia:medianas/<type>` (or `heraldia:medianas/<type>/<style>`) and `/heraldia info cerca`; `/heraldia info` shows their configuration. To test one: `/place structure heraldia:medianas/<type>/<style>`.
- Frequency, measured with `MedianasFrecuenciaTest` (the placement grids on the real 26.3 Overworld biome noise, with villages, unique structures and vanilla structures around them, 3 seeds, 16,000 × 16,000 blocks): see the [changelog](CHANGELOG.md) and the pull request for the figures per type. Each grid looks for its candidate inside the type's biomes (the spot of the cell most inside them), so a type appears wherever its biomes are, at most once per cell.
- Configuration: `medianas.*` options (see [Configuration](#configuration)). Advancements: **By the Wayside**, **Wayfarer** and one of its own for each type of batch 2 (see [Advancements](#advancements)). **In an existing world they only appear in new chunks.**

## Mine entrances

Mine entrances dug into **real hillsides**: the mouth faces downhill, with flat, dry ground in front for the yard and the hill behind, higher than the tunnel; the gallery always lies under rock. Each one leads down **for real** to a Heraldia gallery of its own: 3-wide tunnels with timber frames and lanterns, a rail track from the yard to the end of the main line, crossings, loops and rooms. Three sizes:

| Size | Id | Surface | Underground |
| --- | --- | --- | --- |
| **Mine adit** | `heraldia:minas/pequena/<style>/<variant>` | the mouth with its timber frame, rails, a minecart, lanterns on posts, an ore heap and a barrel | a 14-block descent (rails up the middle, steps on both sides) to a gallery of 3 × 2 crossings with a store room and an ore room |
| **Mining camp** | `heraldia:minas/mediana/<style>/<variant>` | the mouth, the foreman's cabin (bed, table, chest), an ore heap, a loaded chest minecart on its rails and a small smelter (blast furnace, furnace, anvil, a chimney with a smoking campfire) | a 16-block descent to a gallery of 5 × 3 crossings with store room, ore room, canteen and the spiders' room with a small cave spider spawner |
| **Mining complex** | `heraldia:minas/grande/<style>/<variant>` | the mouth, a **headframe** with its pulley wheel over a **vertical shaft with a spiral staircase**, rails with a spur to the loading point, the foreman's office and the smelter | a 20-block descent (and the shaft) to a network of 7 × 4 crossings (store room, powder magazine, canteen, ore room) and, down another ramp, a deep level with the rich vein room and the spiders' room with a **small cave spider spawner** |

- **Styles by biome**, two variants each (the yard mirrored and another gallery): oak and stone on windswept hills, meadows and cherry groves; spruce in taigas, groves and snowy slopes; sandstone (and birch) in the desert; terracotta (and dark oak) in the badlands; deepslate (and spruce) on the peaks. Ore veins show in the gallery walls (more in the ore rooms).
- **Loot**: somewhat better than a vanilla mineshaft chest (more rolls of ingots and raw ore, rails, an emerald now and then, an enchanted iron pickaxe) but moderate: no enchanted golden apples, netherite, elytra or totems, and few diamonds. The rich vein chest of the complex is the best of the mines. With Lootr, each player gets their own (the extra group of each chest is "without Lootr"); all tables live under `heraldia:minas/`.
- **Placement**: one grid per size (`heraldia:minas/<size>`, by default one every 768, 1,152 and 1,920 blocks among those of the same size, scaled by `minas.entradas.separacion_bloques`), looking for its candidate inside the styles' biomes. They follow the medium-structure rules without changing them: never within 256 blocks of a Heraldia village or unique structure, nor within 192 of a medium structure or a mine of another size, nor next to structures that show above ground (vanilla or other mods'); roads skip their pieces. Each entrance is a single piece (no box: what is dug carries its lining and two layers of rock around it, so caves, water and lava do not get in); the hillside search reads the generation heightmap (5 columns to know the slope; on flat land it stops there), measured at 20-70 ms on the test server.
- **More vanilla mineshafts**: `minas.vanilla.multiplicador` (2.0 by default, 1-5, decimals allowed) multiplies how often vanilla abandoned mineshafts appear. Heraldia replaces the placement of the `minecraft:mineshafts` structure set with the same 26.3 values (with 1 it is exactly vanilla); a higher value keeps every mineshaft that would have spawned, in the same place, and adds more. It does not change other structures, and chunks already generated keep what they had (checked on the test server). If another mod also rewrites `minecraft:mineshafts`, only one of the two applies.
- Find them with `/locate structure #heraldia:minas/<size>` and `/heraldia info cerca`; `/heraldia info` shows their configuration. To test one: `/place structure heraldia:minas/<size>/<style>/a` (it is placed even on flat land). Advancements: **Under the Hillside**, **Mining Camp** and **Lord of the Galleries** (one per size, in a chain). **In an existing world they only appear in new chunks.**

## Biomes from other mods

Each village family and each unique structure finds its biomes through its own tag (`#heraldia:<family>` and `#heraldia:unicas/<id>`): the vanilla biomes in the tables above plus the Fabric/NeoForge convention tags (`#c:...`) and `#minecraft:is_*` tags that biome mods (Terralith, Biomes O' Plenty...) add their biomes to. Only tags that add no biome to the list in vanilla are used, so **without biome mods everything generates exactly where it did before**; all of them are `"required": false` (the pack loads fine if a mod is missing).

| Tag | On top of its vanilla biomes |
| --- | --- |
| `llanuras`, `unicas/castillo` | `#c:is_plains` |
| `bosque` | `#c:is_birch_forest`, `#c:is_flower_forest` |
| `oscuro` (and the wizard tower) | `#c:is_dark_forest` |
| `nieve`, `unicas/fortaleza_hielo` | `#c:is_snowy_plains` |
| `desierto`, `unicas/acueducto` | `#c:is_desert` |
| `jungla` | `#minecraft:is_jungle`, `#c:is_jungle` |
| `pantano` (and the mansion) | `#c:is_swamp` |
| `badlands` | `#minecraft:is_badlands`, `#c:is_badlands` |
| `costa` | `#minecraft:is_beach`, `#c:is_beach`, `#c:is_stony_shores` |
| `unicas/catedral` | `#c:is_flower_forest` |
| `unicas/santuario` | `#c:is_birch_forest` |
| `unicas/laboratorio_micelio` | `#c:is_mushroom` |
| `unicas/faro` | `#c:is_stony_shores` |
| `unicas/galeon` | `#minecraft:is_beach`, `#c:is_beach` |
| `unicas/atlantida` | `#minecraft:is_ocean`, `#c:is_ocean` |

Taiga, savanna, cherry and the coliseum, observatory, pyramid, monastery, citadel, palace, jarl's hall, lost mine and corsair's isle uniques keep only their vanilla biomes: no convention tag is narrow enough (for example, `#c:is_cave` includes the deep dark; `#c:is_taiga` includes snowy taiga, which belongs to the snow family, and `#c:is_savanna` includes windswept savanna, the observatory's). Which biomes of a mod go into each tag is that mod's choice (with Terralith, for example, plains include its steppes and highlands, and forest its lavender and sakura forests). The Atlantis search also accepts the oceans in `#c:is_ocean` and `#c:is_deep_ocean`. Tested with Terralith 2.6.5 (`tools/smoke/terralith_biomas.py`).

## Compatibility with other mods

Tested on a real dedicated 26.3 server with the Modrinth versions for Minecraft 26.3 + Fabric listed below (pinned with their sha512 in `tools/smoke/modrinth.py`), in groups of mods that work together (`python3 tools/smoke/compat_mods.py --grupo <group>`; `--listar` shows the groups). In each group: the server starts with no registry errors and no exceptions going through Heraldia code, all Heraldia structures are registered, `/locate` finds a village and four unique structures, `/place` places the wizard tower with its guardian, and three 21 × 21 chunk areas around the village and two uniques are generated (Chunky) measuring chunks/s and "Can't keep up!". Then the structure starts saved in the region files are read to look for Heraldia pieces crossing pieces of other mods' structures.

**Other mods' structures next to Heraldia's**: a structure from another mod that shows above ground (Towns and Towers villages, Structory ruins, Dungeons and Taverns taverns...) does not spawn closer than `compatibilidad.zona_estructuras_ajenas_bloques` blocks (224 by default, 0 disables it) to the start of a Heraldia village or unique structure that really spawns there; Heraldia always wins, so neither appears on top of the other. Before this, the test found a Towns and Towers forest village on top of the cathedral and a beach village inside a Heraldia village. Not covered: underground structures from other mods (mines, dungeons: they are not visible, but may cross a basement or the Lost Mine), vanilla structures and mods that replace vanilla ones under the `minecraft:` name (vanilla villages keep their own exclusion zone), and very large structures whose pieces reach further than that distance.

| Mod | Tested version | Status | Notes |
| --- | --- | --- | --- |
| Terralith (+ Lithostitched) | 2.6.5+26.3 (2.0.6) | tested | Biomes through the convention tags ([Biomes from other mods](#biomes-from-other-mods)); its own structures keep clear of Heraldia's. 33.8 chunks/s (52.6 without mods). |
| Tectonic (+ Lithostitched) | 3.1.0+beta2 | with limitations | Works (27.3 chunks/s), but Tectonic 3 declares itself incompatible with Terralith: the server does not start with both ("Mod resolution failed"). |
| Biomes O' Plenty (+ GlitchCore, TerraBlender) | 26.3.0.0.16 | tested | 42.6 chunks/s. |
| William Wythers' Overhauled Overworld (+ Cristel Lib, Cloth Config) | 3.0.1 | tested | 15.4 chunks/s: its terrain is heavier to generate (without Heraldia too). |
| Oh The Biomes We've Gone | — | not tested: no 26.3 version | Latest Fabric version: 1.21.11. |
| Dungeons and Taverns | 6.1.0 | tested | With the exclusion zone, no overlap. |
| Towns and Towers (+ Cristel Lib) | 1.13.13 | tested | It overlapped before the exclusion zone; now it does not. |
| Structory, Structory: Towers | 1.3.18, 1.0.19 | tested | |
| Explorify | 1.6.6 | tested | 41.2 chunks/s for the whole structure group. |
| YUNG's Better Dungeons, Mineshafts, Strongholds, Ocean Monuments, Desert Temples, Jungle Temples, Witch Huts, Bridges, Extras (YUNG's API) | — | not tested: no 26.3 version | Latest: 26.1.2. |
| Lithium | 0.26.3 | tested | |
| C2ME | 0.4.2-alpha.0.119 | tested | Multithreaded generation: 63.7 chunks/s, no errors. Heraldia's mixins and caches are safe across threads (reviewed, with concurrent unit tests). |
| FerriteCore | 9.0.0 | tested | |
| ScalableLux | 0.3.0-alpha.0.6 | tested | Replaces Starlight. |
| ModernFix | — | not tested: no 26.3 version | Latest: 1.21.1. |
| Starlight | — | not tested: no 26.3 version | Discontinued (latest 1.20.4); ScalableLux replaces it. |
| Noisium | — | not tested: no 26.3 version | Neither NoisiumForked (latest 26.2). |
| Chunky | 1.5.66 | tested | Used for pre-generation in every group. |
| Lootr | 1.25.42.124 | tested | Detected (`/heraldia info`): each chest gives more modest loot, since every player opens their own. |
| Distant Horizons (server) | 3.3.4 | with limitations | Works with Heraldia (areas generated with `forceload`), but together with Chunky the server stays stuck while preparing the spawn, also without Heraldia: do not pre-generate with Chunky while it is installed. |
| Xaero's Minimap, Xaero's World Map | 26.6.2, 1.47.2 | tested (server) | They load on the server; not tested with a client. |
| JourneyMap | 6.0.10 | tested (server) | Same. |

In CI these tests run on every push to `develop`, manually and in pull requests that change their files, the pinned mods or the common placement code. `python3 tools/smoke/modrinth.py --comprobar` checks whether newer 26.3 versions exist.

## Treasure maps

Every unique structure has its own treasure map, which marks the nearest one with an X (or another mark specific to the structure) and carries its translated name:

- In village epic chests: 5 % of the chests hold one (for a random unique structure).
- For sale from master cartographers (level 5) **in Heraldia villages** (not vanilla ones): 24 emeralds and a compass, 2 per restock. Villagers in villages generated before this version do not offer it.
- The search covers about 10,000 blocks and does not load already explored chunks (so it does not stall the server). If no structure of that type is within reach, no map appears (the chest leaves it empty and the cartographer does not offer that trade).
- To test: `/loot give @s loot heraldia:mapas/<id>` gives the map for structure `heraldia:unicas/<id>` from where you stand.

On slopes, building foundations (and the piles of the stilted styles) reach down to the ground in the style's material, up to 16 blocks.

Known limitations: on slopes the streets follow the terrain with one-block steps and, on a cliff higher than 16 blocks, a foundation may be left hanging; a coastal village may still have no harbor when every shore within about 96 blocks is taken by the square, special buildings or streets reaching the sea (with the test seeds, 21 of 21 natural coastal villages got one); overlap with structures from other mods has not been checked (biomes from other mods have, see [Biomes from other mods](#biomes-from-other-mods)).

## Guardian fights

The named guardians of the unique structures (and the Warden of Poseidon) are bosses with **three phases**, including those of structures already generated in an existing world. It all runs on the server: clients do not need the mod.

- A vanilla **boss bar** with the guardian's name for players within 32 blocks while the fight lasts (it starts with the first hit the guardian deals or takes); yellow in phase 1, red in phase 2 and purple in phase 3, with notches at the thirds. It goes away when the guardian dies or nobody is left within 48 blocks.
- **Phase 2** below 66 % health and **phase 3** below 33 %: it becomes enraged (speed I and resistance I for 20 s and strength I for 6 s; in phase 3, speed II and resistance I for 30 s and strength II for 8 s), with smoke, soul flames and a roar, and nearby players see a notice in the action bar ("Sir Aldric, el Castellano Maldito is enraged and calls for reinforcements").
- **Reinforcements**: at each phase, only once, it calls 2 or 3 mobs that suit its structure (the castle garrison with swords and helmets, the colosseum gladiators, the corsair's crew, watchers and a trident-wielding sentinel in Atlantis...; the rest, by their guardian: husks with the centurion, strays with the Frost King, illagers with the illagers...). There are never more than 4 alive at once near the guardian; they drop neither its loot nor its trophy (nor the gear they carry), always spawn as adults and stay put until the fight, like the template mobs, and despawn like any monster if everyone leaves. No reinforcements on peaceful.
- It only changes phase with a player within 48 blocks (if it gets hurt with nobody around, by the sun or lava, the phase comes with the next hit).
- Each phase is recorded in the guardian's own tags (`heraldia_fase.2`, `heraldia_fase.3`): it does not repeat even if the guardian heals, the chunk unloads or the server restarts. Reinforcements carry the `heraldia_refuerzo` tag.
- They can be turned off separately with `jefes.fases.activado`, `jefes.refuerzos.activado` and `jefes.barra.activado` (see [Configuration](#configuration)).

## Guardian trophies

Every named guardian of a unique structure (and Atlantis' Warden of Poseidon) drops its own **trophy** on death: a vanilla item with its own name, one or two lines of lore, a rarity (name colour) and sometimes an armour trim or an emblazoned shield. Most are decorative; a few (the Trident of Poseidon, Borin Ironbeard's Axe) are slightly better than a regular item without breaking progression. It only drops when a player kills the guardian (not with `/kill` or a trap with no player involved), and there is one per guardian: placing the structure again with `/place` creates another guardian and therefore another trophy. Zombie, husk and drowned guardians (and Atlantis' drowned) are always adults, keep their own weapon and never spawn riding a mount.

| Structure | Trophy | Item | Enchantments |
|---|---|---|---|
| Ruined Aqueduct | Lorica of Centurion Aquilius | `iron_chestplate` | protection 1 |
| Atlantis | Trident of Poseidon | `trident` | loyalty 2, impaling 2 |
| Castle | Helm of Sir Aldric | `iron_helmet` | protection 1 |
| Gothic cathedral | Friar Osmund's Soul Compass | `recovery_compass` | — |
| Dwarven Citadel | Borin Ironbeard's Axe | `iron_axe` | efficiency 3, unbreaking 2 |
| Ruined Colosseum | Shield of the Arena Champion | `shield` | unbreaking 2 |
| Smugglers' Lighthouse | Captain Mist's Cutlass | `iron_sword` | sharpness 1, unbreaking 1 |
| Ice Fortress | Frost Crown | `golden_helmet` | unbreaking 2 |
| Stranded Galleon | The Drowned Captain's Spyglass | `spyglass` | — |
| Corsair's Isle | Roque Salitre's Bow | `bow` | power 2, unbreaking 2 |
| Mycologist's Laboratory | Master Ambrose's Shears | `shears` | efficiency 2, unbreaking 2 |
| Haunted Mansion | Count Malachi's Pocket Watch | `clock` | — |
| Lost Mine of Hondavena | Tizon's Pickaxe | `iron_pickaxe` | efficiency 2, unbreaking 2 |
| Mountain Monastery | Tear of the Reliquary | `amethyst_shard` | — |
| Observatory | The Keeper's Astrolabe | `compass` | — |
| Eastern Palace | Ceremonial Sword of the Imperial Guard | `golden_sword` | sharpness 2, unbreaking 3 |
| Pyramid Temple | Breastplate of the Jaguar King | `golden_chestplate` | protection 1 |
| Jarl's Hall | Ulfgrim's Shieldbreaker | `iron_axe` | sharpness 2, unbreaking 2 |
| Druid Sanctuary | Cadoc's Golden Sickle | `golden_hoe` | efficiency 2, unbreaking 2 |
| Wizard Tower | Staff of Archmage Malvarius | `blaze_rod` | — |

All of them carry `custom_data` `{heraldia_trofeo:"<id>"}`. To test: `/loot give @s loot heraldia:trofeos/<id>`. The **Hall of Trophies** challenge (see [Advancements](#advancements)) asks for all of them.

## Chronicle of the Heralds

An optional story thread links the unique structures (full background in [`docs/historia.md`](docs/historia.md)): Ysolda, the last herald of Atlantis, wrote the way back to the sunken city on leaves and entrusted each to the guardian of a structure, who swore to keep it. Every unique structure holds its **leaf**, a written book (“Chronicle of the Heralds: <structure>”) in a chest it already had, which tells its part of the story and ends by pointing to the next structure with a biome-and-feature clue; sometimes (10 %) it comes with that structure's treasure map. The chain goes through all of them, the Wizard Tower's leaf points to Atlantis, and Atlantis' leaf points back to the first.

| Structure | Leaf chest | Points to |
|---|---|---|
| Ruined Aqueduct | cistern | Castle |
| Castle | chapel | Gothic cathedral |
| Gothic cathedral | library | Dwarven Citadel |
| Dwarven Citadel | royal chamber | Ruined Colosseum |
| Ruined Colosseum | lanista's office | Smugglers' Lighthouse |
| Smugglers' Lighthouse | captain's office | Ice Fortress |
| Ice Fortress | gallery | Stranded Galleon |
| Stranded Galleon | captain's cabin | Corsair's Isle |
| Corsair's Isle | map room | Mycologist's Laboratory |
| Mycologist's Laboratory | spore library | Haunted Mansion |
| Haunted Mansion | library | Lost Mine of Hondavena |
| Lost Mine of Hondavena | foreman's hidden office | Mountain Monastery |
| Mountain Monastery | library | Observatory |
| Observatory | hidden room | Eastern Palace |
| Eastern Palace | secret library | Pyramid Temple |
| Pyramid Temple | tomb | Jarl's Hall |
| Jarl's Hall | offerings hall | Druid Sanctuary |
| Druid Sanctuary | library | Wizard Tower |
| Wizard Tower | hideout | Atlantis |
| Atlantis | Academy seal | Ruined Aqueduct |

Pages are shown in each player's language (Spanish if the client does not have the mod). With Lootr every player finds their own leaf. All of them carry `custom_data` `{heraldia_historia:"<id>"}`; to test: `/loot give @s loot heraldia:historia/<id>`. The **Chronicler** challenge (see [Advancements](#advancements)) asks for all of them. **In an existing world they only appear in chests that have not been opened yet.**

## Herald's Guide

A vanilla written book, the **Herald's Guide**, that explains the mod to players and keeps their diary. Every player gets it **once**, the first time they join after Heraldia is installed or updated (players who already existed in the world too; the version they received is stored on the player and kept on death). It is turned off with `guia.entregar_al_entrar` (see [Configuration](#configuration)), and any player can ask for an up-to-date copy with `/heraldia guia`.

- **What it covers** (16 pages): a welcome; the villages and their life (trades, job board, cartographers); the roads; medium structures; the mines; unique structures; Atlantis; the corsair's isle; the wave arena; how advancements, trophies, boss fights (phases, reinforcements and the boss bar), treasure maps and the Chronicle of the Heralds work.
- **Your diary**: how many of this world's unique structures you have discovered (from the "discover" advancements, `heraldia:unicas/<id>/descubrir`) and how many are left, the discovered ones in alphabetical order and, for each missing one, a soft biome-and-feature clue (the same as its Chronicle leaf), **without coordinates** or its name. It counts the unique structures enabled in the configuration plus those you already discovered even if they were disabled later. The diary is a snapshot of the moment it is handed out: ask for a new copy to bring it up to date.
- **Language**: pages are translatable texts whose fallback is in the client's language (Spanish for any Spanish variant; English otherwise), so a player **without the mod** reads it in their language.
- Vanilla book limits: the generator checks that every page fits the 14 lines of a book page (with the same width calculation as the Chronicle leaves), that the title is at most 32 characters and that the book never exceeds 100 pages (with today's 20 unique structures, 21 to 27). It carries `custom_data` `{heraldia_guia_libro:"<version>"}` and the mod edition in its lore.

Cost: it only works when a player without this version's guide joins or when it is asked for (it reads their discovery advancements and builds the book; measured on the test server, see `tools/smoke/guia.py`); nothing per tick.

## Advancements

A **Heraldia** advancement tab (91 advancements), with texts in Spanish and English. They only give experience, except the two job-board deeds:

- **Heraldia** (root): enter any Heraldia village, unique structure, medium structure or mine entrance.
- [Mine entrances](#mine-entrances), a chain: **Under the Hillside** (enter a mine adit, 20), **Mining Camp** (a mining camp, 40) and **Lord of the Galleries** (a mining complex, 80).
- [Medium structures](#medium-structures): **By the Wayside**, find any one (10), and **Wayfarer**, one of each type (150). And, as children of By the Wayside, one for each type of batch 2 (20 each): **Grist for the Mill** (open the sacks of a mill), **Catch of the Day** (the catch barrel of a fisher's hut), **Winter Pelts** (the pelt chest of a hunters' lodge) and **Unguarded** (defeat a keeper of a ruined shrine).
- A village of each family (12 advancements, 20 experience) and the **Heraldia Globetrotter** challenge: all 12 families (250).
- For each unique structure: discover it (50), defeat its named guardian (100) and open its treasure chest (50).
- Atlantis also has its three seals (open the seal chest or hold its key, 30 each); its guardian is the Warden of Poseidon and the treasure counts when you take one of the named items from the unique chest.
- [Job board](#village-life) jobs: **Night Watch** (slay a threat inside a Heraldia village: 3 emeralds and 30 experience) and **Village Defender** (become the hero of a Heraldia village after a raid: 8 emeralds, the Defender's Horn and 100 experience).
- Final challenge **Cartographer of Legends**: discover every unique structure (500).
- **Hall of Trophies** challenge: collect the [trophy](#guardian-trophies) of every unique structure's guardian (500); it counts when you hold it in your inventory.
- **Chronicler** challenge: gather the leaves of the [Chronicle of the Heralds](#chronicle-of-the-heralds), one per unique structure (500); it counts when you hold it in your inventory.

Notes: a structure counts when you step inside its pieces; seeing it is not enough. If a family or a structure is disabled in the [configuration](#configuration), its advancement and the related challenge cannot be earned. With Lootr, the treasure advancement depends on Lootr notifying the game when the chest is opened (not checked). The unique-structure advancements are generated from the unique-structure registry, so a new structure brings its own.

## Restocking loot and difficulty

Two optional server-side features (vanilla clients are enough). Both also work in an **existing world**, on what is already generated.

**Restocking loot** (`botin.reponer.activado`, **off by default**, so turning it on is your decision): chests and barrels of Heraldia villages, medium structures, mine entrances and unique structures are refilled from their loot table again when, **on opening**, all of these are true:

- at least `botin.reponer.dias` in-game days (24,000 ticks of the world clock, the one `/time add` moves; sleeping through the night counts) have passed since it was last looted;
- no other player is within 32 blocks (the one opening it does not count);
- it is empty or almost empty (at most 3 occupied slots out of 27). Nothing is ever deleted: the loot only goes into free slots, so whatever a player stored there stays.

How a chest is recognised: when a Heraldia chest that still has its loot table is opened, the mod stores in the block, as `custom_data` `heraldia_botin: {tabla, saqueado}`, its table and the clock of that looting (nothing else). A chest **already looted before the option was turned on** no longer has its table: the first time it is opened, the mod looks up the Heraldia structure that has a piece there (the chunk's structure references, like `/locate`), and in that piece's template, with its rotation, the loot table it put in that position; from then on it counts as looted at that moment. Lazy: it only works when a player uses a container, never per tick or scanning the world. Not restocked: the Atlantis premium chest (fixed contents, it has its own option `unicas.atlantida.cofre_unico_por_jugador`), trophies, vanilla tables and other mods' tables, and containers of non-template pieces (the Atlantis base) that were looted before turning it on. With **Lootr** installed it does nothing (detected at startup; Lootr already turns loot chests into per-player chests); the log says so if the option is on.

**Difficulty** (`dificultad.nivel`): scales the health and melee damage of the [guardians](#guardian-trophies) and the template mobs of Heraldia (those tagged `heraldia_anclado` or `heraldia_guardian`, and the bosses' reinforcements, `heraldia_refuerzo`; hostile only: cats and wolves are untouched; spawner mobs are not affected).

| Level | Health | Damage | Loot (`dificultad.escalar_botin`) |
| --- | --- | --- | --- |
| `facil` | x0.75 | x0.75 | x0.75 |
| `normal` (default) | as always | as always | as always |
| `dificil` | x1.5 | x1.25 | x1.25 |
| `heroica` | x2 | x1.5 | x1.5 |

- They are attribute modifiers with their own ids (`heraldia:dificultad_vida`, `heraldia:dificultad_dano`, `heraldia:dificultad_jugadores`, `add_multiplied_total`), added on top of whatever else the mob has (the effects of the boss phases, other mods) without touching it. They are set every time the mob loads (also the mobs already generated), so after changing the option and restarting the server they are recomputed; setting them twice changes nothing, and with `normal` they are removed (exactly the previous behaviour). The current health keeps its proportion (a guardian at half health stays at half).
- `dificultad.escalar_por_jugadores` (off): +25 % health per extra player within 32 blocks (up to +100 %), recomputed when the mob takes a hit.
- Loot: only plain stackable items (no name or other components) of Heraldia chest tables change their amount (the fractional part with its probability, never below 1 or above a stack). Skeleton arrows and other ranged damage do not change.

Cost: an event when a block is used (leaves at once if it is not a container with a table, or the option is off), on each entity load and on each hit (leaves at once if the mob has no Heraldia tag); measured with `tools/smoke/botin_reponer.py` and `tools/smoke/dificultad.py`.

## Wave arena

A coliseum near spawn, one per world, to play in waves with your friends. Server-side only (vanilla clients are enough).

**What it looks like.** 57 x 57 blocks: the ring (radius 14) sunk 7 blocks below the ground, with a sandstone floor, sea lanterns and seven spawn points in front of barred cells; the ring wall, topped with glass up to an invisible barrier roof (neither arrows nor mobs reach the stands, nobody climbs out and spiders stay in); four tiers of seats; the outer promenade at ground level, open on all sides, with 16 pillars, arches and lanterns; and to the south the entrance: a ramp from the promenade down to the ring, closed by a barred gate while a match lasts. Next to the entrance, inside the ring, the bell.

**Matches.** Any player steps into the ring and rings the bell: the gate closes and a 5 s countdown with titles starts; whoever is in the ring when it ends plays. Each wave brings more and stronger enemies (4 in the first and +50 % per wave; +10 % health and damage per wave: enemies grow faster than their strength). The types rotate: zombies, skeletons and spiders, a mix with creepers and a hard mix (husks, strays, cave spiders, vindicators and witches), then again. Every 5 waves a named mini-boss also comes (Gorbak the Bonebreaker, Black Arrow, the Arena Executioner and the Last Champion, in turn) with the [phases, bar and reinforcements of the guardians](#guardian-fights). At most `arena.max_mobs_vivos` (20) alive at once: if the wave brings more, they come in batches. 10 s pause between waves. `dificultad.nivel` is respected (the arena's modifiers, `heraldia:arena_*`, add up with those of the difficulty and the bosses). A boss bar shows the wave and the enemies left; the sidebar (objective `heraldia_arena`, only during the match and if nobody uses the sidebar) keeps each player's record and the server's, and breaking the server record is announced in chat. The match ends when every participant has fallen or left the ring (`/heraldia arena salir` takes you out); if the server stops or crashes in the middle of one, the arena is clean next time (no enemies, gate open).

**Loot and death.** Enemies drop no items and give `arena.experiencia_porcentaje` % (15) of the normal experience. Rewards come from waves: every 5 cleared, items for each participant (better at 10, 15 and from 20 on: ingots, diamonds, golden apples, enchanted gear; no netherite or elytra), and advancements for clearing waves 5, 10 and 20. If you fall in the ring during a match, **you keep your inventory and experience** and respawn at the entrance.

**Protection.** Nobody but operators can break, place or use the arena's blocks (except the bell) or use buckets near it, and during a match ender pearls cannot be thrown in the ring. Explosions (creepers, TNT, fireballs), pistons and endermen do not touch it, and fire does not catch on it (all its materials are stone, glass or metal). Only inside its box; outside, everything is normal.

**Placing it** (operators, level 2):

- `/heraldia arena colocar`: finds a flat, dry site with no structures already generated (villages, mine entrances, unique structures, other mods'; underground ones do not count) 200-300 blocks from the world spawn (without loading or generating chunks), gives its coordinates and marks its corners and centre with particle columns for 5 minutes. `/heraldia arena colocar confirmar` builds it: **it clears and levels the ground** (whatever is on top, builds included, is lost), so **make a backup of the world first**. It is built in parts, one chunk per tick (about 3 s).
- `/heraldia arena mover` and `mover confirmar`: the same, removing the old one. `/heraldia arena quitar` and `quitar confirmar`: removes it (the ground stays flat).
- `/heraldia arena empezar` and `/heraldia arena parar`: start or stop a match.
- `/heraldia arena` (anyone): where it is, whether there is a match, and the records.

In a **new world** it is built on its own on the first start (`arena.generar_en_mundos_nuevos`); in an **existing world**, only if an operator places it. Cost: with no match, build or proposal, nothing per tick (three checks); protection, an in-memory AABB per block with an early exit when there is no arena; a match, one check per second of its participants and enemies.

## Configuration

File `config/heraldia.json` on the server (in a single-player world, the one in the game folder). It is created at startup with all default values
and rewritten on every startup with the values in use and a help text (`_ayuda`) in Spanish and English. An invalid value (out of range or of another type)
is reported in the log and replaced by its default; an unknown option is reported and ignored. The `version` field allows migrating the file
when its format changes. It is read only when the server starts and affects chunks generated afterwards (not what is already generated).

| Option | Default | Range | What it does |
| --- | --- | --- | --- |
| `aldeas.separacion_bloques` | 1500 | 1000-10000 | Average spacing between villages; the minimum keeps the 62/94 ratio of the grid. |
| `aldeas.maximo` | 100 | 0-100 | Maximum villages per world: only the grid cells closest to 0,0 count (deterministic, no saved data). |
| `aldeas.porcentaje_grandes` | 25 | 0-100 | Percentage of large villages; the rest are standard. |
| `aldeas.distancia_aldeas_vanilla_bloques` | 160 | 0-256 | Minimum distance to a vanilla village (rounded to chunks); 0 disables it. |
| `aldeas.familias.<family>` | `true` | `true`/`false` | Enables a whole family (its 3 styles). |
| `aldeas.estilos.<style>` | `true` | `true`/`false` | Enables a style (standard and large). If a cell picks a disabled one, another style of its biome is tried. |
| `aldeas.vida.tratos_estilo` | `true` | `true`/`false` | Style trades and the map of the area's unique structure at each family's cartographers ([Village life](#village-life)). |
| `aldeas.vida.tablon` | `true` | `true`/`false` | Job board and bailiff on the square of new villages. |
| `aldeas.vida.asedios` | `false` | `true`/`false` | The weaponsmith of fortified villages sells an ominous bottle to trigger a raid. |
| `aldeas.caminos.activado` | `true` | `true`/`false` | Roads between nearby villages, with bridges, lamp posts and signs ([Roads between villages](#roads-between-villages)); new chunks only. When off, the feature is not even added to the biomes. |
| `aldeas.caminos.distancia_maxima_bloques` | 2000 | 500-4000 | Only villages closer than this are joined. Two villages are never closer than about 670 blocks (with the minimum spacing, 1000), so below that there would be no roads at all. |
| `aldeas.caminos.ancho` | 3 | 1-5 | Road width, in blocks. |
| `golems.limpieza` | `true` | `true`/`false` | Enables the periodic removal of natural golems. |
| `golems.limite_estandar` | 8 | 1-64 | At this many natural golems or more, a standard village removes one every 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Same for large villages. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Enables a unique structure. There is one entry for each unique structure in the mod. |
| `unicas.<id>.separacion_bloques` | the structure's own (4000) | 1000-10000 | Average spacing between structures of that type (by default, one every 3000-5000 blocks). Each type spreads over its whole grid cell (grid origin shifted per type), and two of the same type are never closer than `unicas.distancia_minima.bloques`. For the Mycologist's Laboratory (mushroom fields, a very rare biome) the candidate of each cell is not random: it is the spot of the cell deepest inside that biome, so it appears on a good share of mushroom islands (at most one per cell). The Lost Mine does the same with lush and dripstone caves, looking at cavern height (y = 26) instead of sea level, and the Corsair's Isle with its oceans (the spot deepest in open sea). |
| `unicas.rejilla_compatible` | `false` | `true`/`false` | **Set it to `true` in a world created with an earlier Heraldia version (0.1.0)**; leave it `false` in a new world. Placement grids of unique structures changed after 0.1.0 (each type's grid origin is now shifted and the internal separation is the minimum distance), so in an old world `/locate`, treasure maps, the Chronicle folios, `/heraldia info cerca` and the minimum distance no longer find the unique structures already generated in explored areas (they are still there). Turned on, the 14 unique structures that existed in 0.1.0 (aqueduct, castle, cathedral, citadel, colosseum, lighthouse, ice fortress, galleon, mansion, monastery, observatory, palace, pyramid, wizard tower) use that version's grid again, bit for bit, for the same seed and configuration, at the same cost. The ones added later (Jarl's Hall, Druidic Sanctuary, Mycologist's Laboratory, Lost Mine, Corsair's Isle) keep the new grid, and the old ones take precedence over them: a new one is discarded if it falls within the minimum distance of an old one that spawns, so it never appears on top of one already generated. Villages and Atlantis are not affected (their placement did not change; Atlantis keeps its saved position). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Keeps two different unique structures (Atlantis included) from spawning closer than the minimum distance. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Minimum distance between the start chunks of two different unique structures. When two candidates are too close, a deterministic draw (seed and position) keeps one; if the winner cannot spawn there (wrong biome or terrain), the other one is kept. `/locate` and treasure maps follow the same rule. |
| `unicas.atlantida.cofre_unico_por_jugador` | `false` | `true`/`false` | Per-player Atlantis premium chest. The first opening turns its contents into a template stored in the chest itself (the chest is left empty, so breaking or emptying it duplicates nothing) and each player opens their own copy: the whole contents the first time, and afterwards whatever they left. The Poseidon key is still needed. It works the same with or without Lootr (Lootr does not convert this chest because it has no loot table). Turning it off later puts the contents back in the chest once (the first time someone uses it), and it behaves as before. |
| `jefes.fases.activado` | `true` | `true`/`false` | Guardian phases below 66 % and 33 % health: effects, particles, sound and an action-bar notice ([Guardian fights](#guardian-fights)); also for structures already generated. |
| `jefes.refuerzos.activado` | `true` | `true`/`false` | Guardian reinforcements: 2 or 3 mobs of its structure once per phase, at most 4 alive at once; they do not drop the guardian's loot. Works even with phases off (then without effects and with another notice). |
| `jefes.barra.activado` | `true` | `true`/`false` | Boss bar with the guardian's name for players within 32 blocks while the fight lasts. |
| `medianas.activadas` | `true` | `true`/`false` | Enables the [medium structures](#medium-structures). |
| `medianas.frecuencia_porcentaje` | 100 | 25-400 | Frequency of all medium structures, as a % of the default: 200 = twice as many (each type's spacing is divided by the square root). |
| `medianas.distancia_minima.bloques` | 192 | 64-1024 | Minimum distance between two medium structures of different types (and between two of the same type, at most half a grid cell). |
| `medianas.distancia_aldeas_unicas_bloques` | 256 | 128-1024 | A medium structure does not spawn closer than this to the start of a Heraldia village or unique structure that spawns there. |
| `medianas.<id>.activada` | `true` | `true`/`false` | Enables a type of medium structure (`torre_vigia`, `posada`, `campamento`, `ermita`, `molino`, `pescador`, `cazadores`, `templete`). |
| `medianas.<id>.separacion_bloques` | the type's own (576-832) | 256-4000 | Average spacing between two of that type (at 100 % frequency); each grid cell looks for its candidate inside the type's biomes. |
| `minas.entradas.activado` | `true` | `true`/`false` | Enables the [mine entrances](#mine-entrances) (new chunks only). |
| `minas.entradas.separacion_bloques` | 768 | 256-4000 | Average spacing between two small mine entrances; medium and large ones keep the ratio (x1.5 and x2.5). |
| `minas.vanilla.multiplicador` | 2.0 | 1-5 | Multiplies how often vanilla abandoned mineshafts appear in new chunks (1 = vanilla; decimals allowed, e.g. 1.5). Does not change chunks already generated or other structures. |
| `guia.entregar_al_entrar` | `true` | `true`/`false` | Gives the [Herald's Guide](#heralds-guide) to each player the first time they join with each mod version. When off, nobody gets it on joining, but `/heraldia guia` still hands it out. |
| `compatibilidad.zona_estructuras_ajenas_bloques` | 224 | 0-512 | Structures from other mods that show above ground do not spawn closer than this to the start of a Heraldia village or unique structure that spawns there; 0 disables it ([Compatibility with other mods](#compatibility-with-other-mods)). |
| `botin.reponer.activado` | `false` | `true`/`false` | [Restocking loot](#restocking-loot-and-difficulty): Heraldia chests and barrels are refilled on opening after the given days, with no other player nearby and when empty or almost empty; also chests already generated. Nothing with Lootr. |
| `botin.reponer.dias` | 7 | 1-60 | In-game days (24,000 ticks of the world clock) after a looting before a chest is restocked. |
| `dificultad.nivel` | `normal` | `facil`, `normal`, `dificil`, `heroica` | [Difficulty](#restocking-loot-and-difficulty) of Heraldia guardians and template mobs (health and damage); also those already generated, when they load. `normal` is the previous behaviour. |
| `dificultad.escalar_por_jugadores` | `false` | `true`/`false` | +25 % health per extra player within 32 blocks (up to +100 %), when hit. |
| `dificultad.escalar_botin` | `true` | `true`/`false` | With `facil`, `dificil` or `heroica`, plain stackable items of Heraldia chest loot come in x0.75, x1.25 or x1.5 amounts (nothing changes with `normal`). |
| `arena.activado` | `true` | `true`/`false` | [Wave arena](#wave-arena) near spawn. When disabled, no matches and no protection (a placed arena stays as it is). |
| `arena.generar_en_mundos_nuevos` | `true` | `true`/`false` | In a new world, the arena is built on its own 200-300 blocks from spawn; in an existing one, never (an operator places it). |
| `arena.oleada.mobs_incremento` | 50 | 10-200 | Extra enemies in each wave, as a % of the first wave's (4, 6, 8, 10... with 50), rounded up. |
| `arena.oleada.stats_incremento` | 10 | 1-100 | Extra health and damage in each wave, in %; if it exceeds `mobs_incremento`, that one is used (enemies grow faster than their strength). |
| `arena.max_mobs_vivos` | 20 | 4-64 | Enemies alive at once in the ring; if a wave brings more, they come in batches. |
| `arena.experiencia_porcentaje` | 15 | 0-100 | Experience of arena enemies, as a % of the normal amount (after the game's own scaling); they drop no items. |

Atlantis has no placement options: there is always exactly one per world.

### Configuration screen (client)

On the client the file can also be edited from a screen inside the game. With [Mod Menu](https://modrinth.com/mod/modmenu) installed (optional; the mod works the same without it, the screen just has no button) it opens from the configuration button of Heraldia in the mod list. It is built from the same option list as the file, so new options appear on their own:

- Sections: Villages, Village families, Village styles, Village life, Roads between villages, Golems, Unique structures, Minimum distance between unique structures, Atlantis, Medium structures, Compatibility with other mods, Loot and Difficulty, with a search box (by name, key, help or section).
- Each option shows its value (on/off button, number box, or a button that cycles through the values of a list option such as `dificultad.nivel`). Its tooltip shows the key, the help text (the same as `_ayuda`) and the default and range. An invalid number turns red, its tooltip says why and **Save** stays disabled until it is fixed.
- **Save** writes `config/heraldia.json` in the same format as at startup (with `version` and `_ayuda`); **Reset to defaults** puts every option back to its default (nothing is written until you save); **Cancel** discards the changes.
- Changes apply when the world is opened again or the server is restarted, and only to chunks generated afterwards; the screen says so. With no world open they are used from the next world you open (no need to restart the game); with a single-player world open, after leaving and re-entering it.
- When connected to a server the screen edits **the client's local file** (your single-player worlds), not the server's: the screen warns about it. The server's configuration is still edited in its own `config/heraldia.json`. Nothing is sent over the network.

## Building

Requirements: Java 25, Python 3.11+ and `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

The `.jar` ends up in `build/libs/`. The build runs the generator `tools/gen/main.py`, which creates the structures and the advancements, validates them against the 26.3 registries and audits the structures; a single error or warning fails the build.

The 26.3 registries (summary from [misode/mcmeta](https://github.com/misode/mcmeta), branch `26.3-summary`) are not included in the repository because they are Mojang data. They are cloned automatically into `build/mcmeta-summary`; to use another copy: `-Pmcmeta_summary=<path>` or the `MCMETA_SUMMARY` variable.

`./gradlew build` also runs the unit tests: the generator's (pytest, `tools/gen/tests`, also with `python3 -m pytest tools/gen/tests`, a few seconds), the JUnit tests (`./gradlew test`) and the long JUnit simulations (`./gradlew testPesado`, a few minutes). The generator splits its work across processes (`HERALDIA_PROCESOS=1` runs it serially, with the same output).

`python3 tools/test.py --afectados` runs the unit tests and only the server tests affected by the files changed against `origin/develop` (`--listar` just lists them); `python3 tools/test.py --todo` runs the full battery. The path map is the same one the CI uses (see `docs/DESARROLLO.md`, «Política de pruebas»).

Checks before publishing (the GitHub Actions CI, `.github/workflows/ci.yml`, runs them on every PR against `develop` or `main`, with only the server tests affected by the PR, and all of them on every push to `develop`, when run by hand or on a PR labelled `bateria-completa`):

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

The second one downloads a real Fabric 26.3 server into `build/smoke`, starts it with the mod and checks that all 142 structures and all 91 advancements are loaded, that `/place structure` places a village with villagers and that the functions exist.

Server tests for each unique structure (same `--jar` argument): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` and `galeon_test.py`, and in `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` and `prueba_servidor.py` of `fortaleza_hielo`, `mansion`, `monasterio`, `piramide`, `salon_jarl`, `santuario`, `laboratorio_micelio`, `mina_perdida` and `isla_corsario`. Atlantis is checked within the smoke test (`atlantida/humo.py`). `tools/smoke/trofeos.py` adds Carpet (pinned version) and, with a simulated player, kills each guardian and checks that it drops its trophy (and that `/kill` does not) and that the trophy challenge is granted with the last one. `tools/smoke/jefes_fases.py` (with Carpet) summons guardians with their tags, like one already generated, takes their health down with `/damage` to each threshold and checks the phase tags, the effects, the reinforcements (how many, which type, with their gear and tags, adults, without the guardian's table, not repeated and capped at 4), the boss bar (through the log: on the first hit, when the player leaves and comes back, and on death) and, on a second start with the three options off, that none of that happens. `tools/smoke/historia.py` (also with Carpet) checks that the Chronicle chain goes through every unique structure, that each one's chest drops its leaf and that the simulated player earns the Chronicler challenge with the last one. `tools/smoke/aldeas_variantes.py` places several villages of the same style, reads the saved regions and identifies, by comparing blocks with the templates in the `.jar`, which variant of each special building came out; it checks that each one matches exactly one variant and that different variants come out, and measures each `/place`. `tools/smoke/guardianes_adultos.py` places 200 times, through the same path as world generation, every zombie-type mob of the templates (zombie, husk, drowned) and checks that none comes out as a baby, with another weapon or on a mount. `tools/smoke/guardianes_anclados.py` (with Carpet) places 30 times, through the same path, every mob of the templates tagged `heraldia_anclado` (the guardians and the drowned of Atlantis) and checks that none can pick up items and that after 200 ticks, and again after unloading and reloading the chunks, all are still where they appeared (a control batch without the tag must wander and pick up items); then that each one attacks the simulated player 8 blocks away, and that each guardian is still in its room 200 ticks after placing its real template in daylight. `tools/smoke/rejilla_compatible.py` turns on `unicas.rejilla_compatible` and checks that `/locate` of several unique structures from 0.1.0 gives exactly the coordinates of the 0.1.0 `.jar` (fixed in the script, with how they were obtained). `tools/smoke/coste_generacion.py` measures the world generation cost: it generates the same zones of the same world (fixed seed) with and without Heraldia, three runs of each, and compares the server CPU per chunk with the reference in `tools/smoke/coste_referencia.json` (it fails on a regression; it also reports the steps of each chunk, MSPT, memory and `/locate` times; see `docs/DESARROLLO.md`). Measured in the CI (4 cores): +9.3 % CPU per chunk with Heraldia. With `-Dheraldia.perfil=true` on the server JVM, Heraldia logs on shutdown how long its most expensive generation steps took (placement rules, mine slope search, harbour shore search, roads...); without it, it measures nothing.

All server tests share the helpers in `tools/smoke/server_smoke.py` (`Context`): checks that always answer (`test` refuses an `execute` with `as`/`at` or more than one condition, which can stay silent on the console), waits by condition with a generous limit (`until`, `wait_entity`, which prints where the entities of that type or tag are if it gives up), waits counted in game ticks (`ticks`, with `/time query gametime`) and `pos` (reads `Pos` with `data get entity`). Guardians and other mobs with AI are looked up by their tag, not in a box next to their spot. Each test server picks a free port, so several tests can run at once on the same machine.

Versions are pinned in `gradle.properties`. Generator tools: `tools/gen/sim.py` (simulates jigsaw assembly; `python3 tools/gen/sim.py [style ...]` counts the variants of the special buildings, houses, villagers, golems and beds), `tools/gen/render.py` (isometric renders; `python3 tools/gen/render.py <folder> [style ...]` draws the variant sheets), `tools/gen/lint.py` (design audit).

## License and credits

No license: all rights reserved. The code is visible but no permission is granted to use, copy or redistribute it.
All content uses only Minecraft blocks and items; no third-party assets are included.
