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

## Installation

Requirements: Minecraft 26.3, Fabric Loader 0.20.1 or later and Fabric API (tested with 0.166.2+26.3).

1. Build `heraldia-<version>.jar` (see below).
2. Copy it into the `mods` folder of the server and of every client.
3. Start the server. `logs/latest.log` should show `Heraldia: 87 estructuras registradas`.

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

Use the showcase only in a test world: whatever it places stays.

## Huge villages

By default, one village every 1000-2000 blocks (average spacing 1500), at most 100 per world (the ones closest to 0,0) and never within 10 chunks of a vanilla village. The standard version appears 3 times as often as the large one. All of this can be changed in the [configuration](#configuration).

| Family | Biomes | Styles (ID `heraldia:<style>` and `heraldia:<style>_grande`) |
| --- | --- | --- |
| Plains | plains, sunflower plains, meadow | `llanuras_castellana`, `llanuras_gallega`, `llanuras_entramado` |
| Temperate forest | forest, flower forest, birch forest (and old growth), wooded hills | `bosque_lenadores`, `bosque_elfica`, `bosque_abadia` |
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
- Four avenues with the special buildings: a church or temple depending on the style (with cemetery and crypt), town hall, market, tavern, smithy, library, farm with windmill and inn (or a port on the coast).
- About 20 houses in the standard size and about 30 in the large one, furnished, with chests in some and loot from common to epic (tables `heraldia:cofres/comun`, `poco_comun`, `raro`, `epico`).
- Watchtowers and wall gates at the ends of the streets; themed decoration between houses.
- Villagers: half the number of houses, over 80 % with a profession. Golems: at least one per 3 villagers.

Population limits: there are about 1.25 beds per initial villager, so the population grows by 25 % at most.
The function `heraldia:golems` checks loaded villages every 30 s and removes one natural golem each time there are 8 or more (standard) or 9 or more (large); it does not touch player-built ones. Limits and cleanup can be changed in the [configuration](#configuration).

## Atlantis

Exactly one per world, always, with no configuration option. It is a walled city of about 770 × 770 blocks, fully submerged, in the deep-ocean basin closest to the origin that is 1,500 blocks or more away and unexplored (in an existing world it only appears in new chunks). The position is computed the first time the world loads and saved in `data/heraldia/atlantida.json`.

- Find it with `/locate structure heraldia:unicas/atlantida` or with its treasure map.
- Flooded streets and squares, and more than 200 houses, towers and rooms that are **dry**, entered through doors or by diving up from below. If a wall is broken, the room floods.
- Eight districts (agora, fish market, baths, arsenal, sunken harbor, coral gardens, academy and amphitheater), a temple in the center, underground galleries and, at the bottom, the final guardian.
- Defenders: guardians, drowned with tridents, 48 spawners, elder guardians in the key districts and the Guardian of Poseidon.
- Three seals with their keys, combination doors, arrow traps, water and TNT.
- 185 chests with advanced loot and a unique chest, hidden and locked with the final guardian's key, holding two legendary tridents. Its contents are fixed: the first group to arrive takes them.
- No other structures (monuments, shipwrecks, ruins) generate inside the city, except strongholds, which the game needs to reach the End.

Details, plans and what has been verified: [docs/unicas/atlantida.md](docs/unicas/atlantida.md).

## Treasure maps

Every unique structure has its own treasure map, which marks the nearest one with an X (or another mark specific to the structure) and carries its translated name:

- In village epic chests: 5 % of the chests hold one (for a random unique structure).
- For sale from master cartographers (level 5) **in Heraldia villages** (not vanilla ones): 24 emeralds and a compass, 2 per restock. Villagers in villages generated before this version do not offer it.
- The search covers about 10,000 blocks and does not load already explored chunks (so it does not stall the server). If no structure of that type is within reach, no map appears (the chest leaves it empty and the cartographer does not offer that trade).
- To test: `/loot give @s loot heraldia:mapas/<id>` gives the map for structure `heraldia:unicas/<id>` from where you stand.

Known limitations: the port is laid out straight from the street without looking for water; on slopes there may be steps and tall foundations; overlap with structures from other mods has not been checked.

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
| `golems.limpieza` | `true` | `true`/`false` | Enables the periodic removal of natural golems. |
| `golems.limite_estandar` | 8 | 1-64 | At this many natural golems or more, a standard village removes one every 30 s. |
| `golems.limite_grande` | 9 | 1-64 | Same for large villages. |
| `unicas.<id>.activada` | `true` | `true`/`false` | Enables a unique structure. There is one entry for each unique structure in the mod. |
| `unicas.<id>.separacion_bloques` | the structure's own (4000) | 1000-10000 | Average spacing between structures of that type (by default, one every 3000-5000 blocks). |
| `unicas.distancia_minima.activada` | `true` | `true`/`false` | Keeps two different unique structures (Atlantis included) from spawning closer than the minimum distance. |
| `unicas.distancia_minima.bloques` | 1000 | 100-3000 | Minimum distance between the start chunks of two different unique structures. When two candidates are too close, a deterministic draw (seed and position) keeps one; if the winner cannot spawn there (wrong biome or terrain), the other one is kept. `/locate` and treasure maps follow the same rule. |

Atlantis is not listed: there is always exactly one per world.

## Building

Requirements: Java 25, Python 3.11+ and `pip install -r tools/gen/requirements.txt`, git.

```bash
./gradlew build
```

The `.jar` ends up in `build/libs/`. The build runs the generator `tools/gen/main.py`, which creates the structures, validates them against the 26.3 registries and audits them; a single error or warning fails the build.

The 26.3 registries (summary from [misode/mcmeta](https://github.com/misode/mcmeta), branch `26.3-summary`) are not included in the repository because they are Mojang data. They are cloned automatically into `build/mcmeta-summary`; to use another copy: `-Pmcmeta_summary=<path>` or the `MCMETA_SUMMARY` variable.

Checks before publishing:

```bash
python3 tools/changelog.py check
```

```bash
python3 tools/smoke/server_smoke.py --jar build/libs/heraldia-0.1.0.jar
```

The second one downloads a real Fabric 26.3 server into `build/smoke`, starts it with the mod and checks that all 87 structures are registered, that `/place structure` places a village with villagers and that the functions exist.

Server tests for each unique structure (same `--jar` argument): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` and `galeon_test.py`, and in `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` and `prueba_servidor.py` of `fortaleza_hielo`, `mansion`, `monasterio` and `piramide`. Atlantis is checked within the smoke test (`atlantida/humo.py`).

Versions are pinned in `gradle.properties`. Generator tools: `tools/gen/sim.py` (simulates jigsaw assembly), `tools/gen/render.py` (isometric renders), `tools/gen/lint.py` (design audit).

## License and credits

No license: all rights reserved. The code is visible but no permission is granted to use, copy or redistribute it.
All content uses only Minecraft blocks and items; no third-party assets are included.
