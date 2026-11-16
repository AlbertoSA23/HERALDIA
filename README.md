# Heraldia

**English** · [Español](README.es.md)

Fabric mod for **Minecraft 26.3** dedicated solely to generating new structures in the Overworld.
All current content is vanilla (blocks, items and loot from the base game).

Development guide (in Spanish): [docs/DESARROLLO.md](docs/DESARROLLO.md).

Contents:

- **Huge villages**: 72 structures (36 biome styles, each in a standard and a large size).
- **Atlantis**: a single sunken city per world (see below).
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

## Installation

Requirements: Minecraft 26.3, Fabric Loader 0.20.1 or later and Fabric API (tested with 0.166.2+26.3). Optional on the client: Mod Menu (built against 21.0.1), for the [configuration screen](#configuration-screen-client).

1. Build `heraldia-<version>.jar` (see below).
2. Copy it into the `mods` folder of the server and of every client.
3. Start the server. `logs/latest.log` should show `Heraldia: 92 estructuras registradas`.

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
- `/heraldia info` (operators, level 2): summary of the configuration in use (villages, enabled unique structures and their spacing, minimum distance, per-player chest, whether Lootr is installed) and how many structures are registered.
- `/heraldia info cerca [radius]`: the nearest unique structure of each type and the nearest Heraldia village, with distance, direction and coordinates (click them to get a `/tp` command). It uses the same check as `/locate`, so it never points to a structure that the minimum distance discards, but it neither loads nor generates chunks: what has not been generated yet is shown as "predicted" (for a predicted village only its family is known). Default radius 3,000 blocks, maximum 10,000; the message says how long the search took.
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
- Four avenues with the special buildings: a church or temple depending on the style (with cemetery and crypt), town hall, market, tavern, smithy, library, farm with windmill and inn. Each special building comes in three variants per style with a different floor plan and silhouette and the same function (for example the church with a front tower, with a transept and bell gable, or with a porch and the tower at the apse; the market open, as a covered hall or as an arcaded square), drawn at random for each village, so two villages of the same style differ in their main buildings. Sheets: [docs/aldeas/variantes.md](docs/aldeas/variantes.md). On the coast there is also a harbor (harbor house and a pier with piles, crane and boats) on the shore nearest to the square, with the pier facing the sea; if there is no shore within about 80 blocks (or the only one would put the pier over a street), the village has no harbor.
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

## Treasure maps

Every unique structure has its own treasure map, which marks the nearest one with an X (or another mark specific to the structure) and carries its translated name:

- In village epic chests: 5 % of the chests hold one (for a random unique structure).
- For sale from master cartographers (level 5) **in Heraldia villages** (not vanilla ones): 24 emeralds and a compass, 2 per restock. Villagers in villages generated before this version do not offer it.
- The search covers about 10,000 blocks and does not load already explored chunks (so it does not stall the server). If no structure of that type is within reach, no map appears (the chest leaves it empty and the cartographer does not offer that trade).
- To test: `/loot give @s loot heraldia:mapas/<id>` gives the map for structure `heraldia:unicas/<id>` from where you stand.

On slopes, building foundations (and the piles of the stilted styles) reach down to the ground in the style's material, up to 16 blocks.

Known limitations: on slopes the streets follow the terrain with one-block steps and, on a cliff higher than 16 blocks, a foundation may be left hanging; sometimes the harbor does not fit (the nearby shore is taken by the square or a special building) and the village has no harbor; overlap with structures from other mods has not been checked (biomes from other mods have, see [Biomes from other mods](#biomes-from-other-mods)).

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

## Advancements

A **Heraldia** advancement tab (82 advancements), with texts in Spanish and English. They only give experience, except the two job-board deeds:

- **Heraldia** (root): enter any Heraldia village or unique structure.
- A village of each family (12 advancements, 20 experience) and the **Heraldia Globetrotter** challenge: all 12 families (250).
- For each unique structure: discover it (50), defeat its named guardian (100) and open its treasure chest (50).
- Atlantis also has its three seals (open the seal chest or hold its key, 30 each); its guardian is the Warden of Poseidon and the treasure counts when you take one of the named items from the unique chest.
- [Job board](#village-life) jobs: **Night Watch** (slay a threat inside a Heraldia village: 3 emeralds and 30 experience) and **Village Defender** (become the hero of a Heraldia village after a raid: 8 emeralds, the Defender's Horn and 100 experience).
- Final challenge **Cartographer of Legends**: discover every unique structure (500).
- **Hall of Trophies** challenge: collect the [trophy](#guardian-trophies) of every unique structure's guardian (500); it counts when you hold it in your inventory.
- **Chronicler** challenge: gather the leaves of the [Chronicle of the Heralds](#chronicle-of-the-heralds), one per unique structure (500); it counts when you hold it in your inventory.

Notes: a structure counts when you step inside its pieces; seeing it is not enough. If a family or a structure is disabled in the [configuration](#configuration), its advancement and the related challenge cannot be earned. With Lootr, the treasure advancement depends on Lootr notifying the game when the chest is opened (not checked). The unique-structure advancements are generated from the unique-structure registry, so a new structure brings its own.

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
| `golems.limpieza` | `true` | `true`/`false` | Enables the periodic removal of natural golems. |
| `golems.limite_estandar` | 8 | 1-64 | At this many natural golems or more, a standard village removes one every 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Same for large villages. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Enables a unique structure. There is one entry for each unique structure in the mod. |
| `unicas.<id>.separacion_bloques` | the structure's own (4000) | 1000-10000 | Average spacing between structures of that type (by default, one every 3000-5000 blocks). Each type spreads over its whole grid cell (grid origin shifted per type), and two of the same type are never closer than `unicas.distancia_minima.bloques`. For the Mycologist's Laboratory (mushroom fields, a very rare biome) the candidate of each cell is not random: it is the spot of the cell deepest inside that biome, so it appears on a good share of mushroom islands (at most one per cell). The Lost Mine does the same with lush and dripstone caves, looking at cavern height (y = 26) instead of sea level, and the Corsair's Isle with its oceans (the spot deepest in open sea). |
| `unicas.rejilla_compatible` | `false` | `true`/`false` | **Set it to `true` in a world created with an earlier Heraldia version (0.1.0)**; leave it `false` in a new world. Placement grids of unique structures changed after 0.1.0 (each type's grid origin is now shifted and the internal separation is the minimum distance), so in an old world `/locate`, treasure maps, the Chronicle folios, `/heraldia info cerca` and the minimum distance no longer find the unique structures already generated in explored areas (they are still there). Turned on, the 14 unique structures that existed in 0.1.0 (aqueduct, castle, cathedral, citadel, colosseum, lighthouse, ice fortress, galleon, mansion, monastery, observatory, palace, pyramid, wizard tower) use that version's grid again, bit for bit, for the same seed and configuration, at the same cost. The ones added later (Jarl's Hall, Druidic Sanctuary, Mycologist's Laboratory, Lost Mine, Corsair's Isle) keep the new grid, and the old ones take precedence over them: a new one is discarded if it falls within the minimum distance of an old one that spawns, so it never appears on top of one already generated. Villages and Atlantis are not affected (their placement did not change; Atlantis keeps its saved position). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Keeps two different unique structures (Atlantis included) from spawning closer than the minimum distance. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Minimum distance between the start chunks of two different unique structures. When two candidates are too close, a deterministic draw (seed and position) keeps one; if the winner cannot spawn there (wrong biome or terrain), the other one is kept. `/locate` and treasure maps follow the same rule. |
| `unicas.atlantida.cofre_unico_por_jugador` | `false` | `true`/`false` | Per-player Atlantis premium chest. The first opening turns its contents into a template stored in the chest itself (the chest is left empty, so breaking or emptying it duplicates nothing) and each player opens their own copy: the whole contents the first time, and afterwards whatever they left. The Poseidon key is still needed. It works the same with or without Lootr (Lootr does not convert this chest because it has no loot table). Turning it off later puts the contents back in the chest once (the first time someone uses it), and it behaves as before. |

Atlantis has no placement options: there is always exactly one per world.

### Configuration screen (client)

On the client the file can also be edited from a screen inside the game. With [Mod Menu](https://modrinth.com/mod/modmenu) installed (optional; the mod works the same without it, the screen just has no button) it opens from the configuration button of Heraldia in the mod list. It is built from the same option list as the file, so new options appear on their own:

- Sections: Villages, Village families, Village styles, Village life, Golems, Unique structures, Minimum distance between unique structures and Atlantis, with a search box (by name, key, help or section).
- Each option shows its value (on/off button or number box). Its tooltip shows the key, the help text (the same as `_ayuda`) and the default and range. An invalid number turns red, its tooltip says why and **Save** stays disabled until it is fixed.
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

The second one downloads a real Fabric 26.3 server into `build/smoke`, starts it with the mod and checks that all 92 structures and all 82 advancements are loaded, that `/place structure` places a village with villagers and that the functions exist.

Server tests for each unique structure (same `--jar` argument): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` and `galeon_test.py`, and in `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` and `prueba_servidor.py` of `fortaleza_hielo`, `mansion`, `monasterio`, `piramide`, `salon_jarl`, `santuario`, `laboratorio_micelio`, `mina_perdida` and `isla_corsario`. Atlantis is checked within the smoke test (`atlantida/humo.py`). `tools/smoke/trofeos.py` adds Carpet (pinned version) and, with a simulated player, kills each guardian and checks that it drops its trophy (and that `/kill` does not) and that the trophy challenge is granted with the last one. `tools/smoke/historia.py` (also with Carpet) checks that the Chronicle chain goes through every unique structure, that each one's chest drops its leaf and that the simulated player earns the Chronicler challenge with the last one. `tools/smoke/aldeas_variantes.py` places several villages of the same style, reads the saved regions and identifies, by comparing blocks with the templates in the `.jar`, which variant of each special building came out; it checks that each one matches exactly one variant and that different variants come out, and measures each `/place`. `tools/smoke/guardianes_adultos.py` places 200 times, through the same path as world generation, every zombie-type mob of the templates (zombie, husk, drowned) and checks that none comes out as a baby, with another weapon or on a mount. `tools/smoke/guardianes_anclados.py` (with Carpet) places 30 times, through the same path, every mob of the templates tagged `heraldia_anclado` (the guardians and the drowned of Atlantis) and checks that none can pick up items and that after 200 ticks, and again after unloading and reloading the chunks, all are still where they appeared (a control batch without the tag must wander and pick up items); then that each one attacks the simulated player 8 blocks away, and that each guardian is still in its room 200 ticks after placing its real template in daylight. `tools/smoke/rejilla_compatible.py` turns on `unicas.rejilla_compatible` and checks that `/locate` of several unique structures from 0.1.0 gives exactly the coordinates of the 0.1.0 `.jar` (fixed in the script, with how they were obtained).

All server tests share the helpers in `tools/smoke/server_smoke.py` (`Context`): checks that always answer (`test` refuses an `execute` with `as`/`at` or more than one condition, which can stay silent on the console), waits by condition with a generous limit (`until`, `wait_entity`, which prints where the entities of that type or tag are if it gives up), waits counted in game ticks (`ticks`, with `/time query gametime`) and `pos` (reads `Pos` with `data get entity`). Guardians and other mobs with AI are looked up by their tag, not in a box next to their spot. Each test server picks a free port, so several tests can run at once on the same machine.

Versions are pinned in `gradle.properties`. Generator tools: `tools/gen/sim.py` (simulates jigsaw assembly; `python3 tools/gen/sim.py [style ...]` counts the variants of the special buildings, houses, villagers, golems and beds), `tools/gen/render.py` (isometric renders; `python3 tools/gen/render.py <folder> [style ...]` draws the variant sheets), `tools/gen/lint.py` (design audit).

## License and credits

No license: all rights reserved. The code is visible but no permission is granted to use, copy or redistribute it.
All content uses only Minecraft blocks and items; no third-party assets are included.
