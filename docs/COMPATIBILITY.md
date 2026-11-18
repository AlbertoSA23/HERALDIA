# Heraldia: compatibility with other mods

**English** · [Español](COMPATIBILIDAD.md)

Back to the [README](../README.md).

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

Taiga, savanna, cherry and the coliseum, observatory, pyramid, monastery, citadel, palace, jarl's hall, lost mine and corsair's isle uniques keep only their vanilla biomes: no convention tag is narrow enough (for example, `#c:is_cave` includes the deep dark; `#c:is_taiga` includes snowy taiga, which belongs to the snow family, and `#c:is_savanna` includes windswept savanna, the observatory's). Which biomes of a mod go into each tag is that mod's choice (with Terralith, for example, plains include its steppes and highlands, and forest its lavender and sakura forests). The Atlantis search also accepts the oceans in `#c:is_ocean` and `#c:is_deep_ocean`. Tested with Terralith 2.6.5 (`tools/smoke/terralith_biomes.py`).

## Compatibility with other mods

Tested on a real dedicated 26.3 server with the Modrinth versions for Minecraft 26.3 + Fabric listed below (pinned with their sha512 in `tools/smoke/modrinth.py`), in groups of mods that work together (`python3 tools/smoke/compat_mods.py --group <group>`; `--list-only` shows the groups). In each group: the server starts with no registry errors and no exceptions going through Heraldia code, all Heraldia structures are registered, `/locate` finds a village and four unique structures, `/place` places the wizard tower with its guardian, and three 21 × 21 chunk areas around the village and two uniques are generated (Chunky) measuring chunks/s and "Can't keep up!". Then the structure starts saved in the region files are read to look for Heraldia pieces crossing pieces of other mods' structures.

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

In CI these tests run on every push to `develop`, manually and in pull requests that change their files, the pinned mods or the common placement code. `python3 tools/smoke/modrinth.py --check` checks whether newer 26.3 versions exist.

## Web maps (BlueMap, Dynmap and squaremap)

Optional dependencies: at startup Heraldia checks (`FabricLoader.isModLoaded`) whether `bluemap`, `dynmap` or `squaremap` are present, and only then loads its adapter (`maps/bluemap/`, `maps/dynmap/`, `maps/squaremap/`), the only class that names that map's API. Without any of them no event is registered, nothing is written to the world and no map class is loaded (`WebMapsIsolationTest` checks the bytecode). The APIs are `compileOnly` (they are not in the `.jar`): `de.bluecolored:bluemap-api:2.8.2` (repo.bluecolored.de), `xyz.jpenilla:squaremap-api:1.4.3` (Maven Central) and `us.dynmap:DynmapCoreAPI:3.8` (repo.mikeprimm.com; it publishes no `maven-metadata.xml`, but the fixed version resolves). If a map ships a different API version that does not fit, the log says so and Heraldia carries on without it. What is shown and the options: [Web maps](CONFIGURATION.md#web-maps-heraldia-webmap-refresh).

| Map | Version tested | Status | Notes |
| --- | --- | --- | --- |
| squaremap | 1.4.3 | tested | `tools/smoke/web_maps.py`: the 5 layers, a medium structure's marker on discovering it with a simulated player (position, icon, name and description in Spanish), `solo_descubiertas`, disabled layers and the markers coming back after a restart (from the world file). One layer (`SimpleLayerProvider`) per kind, with 24 px icons. |
| BlueMap | 5.29 (API 2.8.2) | compiled, not tested on a server | One `MarkerSet` per layer in each Overworld map, with point markers and the icons in the map's assets. BlueMap does not start its API until the resource download is accepted (`accept-download` in its `core.conf`); Heraldia publishes as soon as it is enabled. |
| Dynmap | — | no 26.3 version (latest: 1.21.11) | Adapter written against DynmapCoreAPI 3.8 (non-persistent sets, own icons, everything on the server thread because its API is not thread-safe); the Overworld world is looked up by the level name. Not tested. |
