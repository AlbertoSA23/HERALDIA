# Heraldia: installation, commands and configuration

**English** · [Español](CONFIGURACION.md)

Back to the [README](../README.md).

## Installation

Requirements: Minecraft 26.3, Fabric Loader 0.20.1 or later and Fabric API (tested with 0.166.2+26.3). Optional on the client: Mod Menu (built against 21.0.1), for the [configuration screen](#configuration-screen-client).

1. Build `heraldia-<version>.jar` (see below).
2. Copy it into the server's `mods` folder. On clients it is optional: a vanilla client plays the same (texts it does not know show in Spanish, except the Guide, which arrives in each player's language); with the mod everything shows in its language and the configuration screen is available.
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
- `/heraldia guia` (any player, no permissions needed): gives you an up-to-date copy of the [Herald's Guide](CONTENT.md#heralds-guide) (if you carry one in your inventory, it is replaced by the new one).
- `/heraldia profile` (operators, level 2): the [gameplay profile](#gameplay-profiles) in use (the effective one and the one chosen in the file) and the value it gives to each of its options, marking the ones set by hand in the file that override it.
- `/heraldia info aqui`: which Heraldia structure you are standing in (name and id) and, in a unique structure, whether its guardian is alive (only answered when the whole structure is loaded).

Use the showcase only in a test world: whatever it places stays.

## Admin tools

### Review route: `/heraldia review`

For operators (level 2). A guided route to check all the visual content of the mod in one afternoon, stop by stop: a village of each family, every unique structure (Atlantis and the Corsair's Isle included), each type of medium structure, a mine entrance of each size, the arena (if enabled) and a stretch of road (if there are roads). Whatever is disabled in the configuration is left out.

- `/heraldia review`: goes to the stop you are at (the first one, the first time). At each stop you get an on-screen title, the list of what to check in the chat (translated, like everything else) and buttons to mark it: **Checked**, **+ Note** (checked, with a note) and **Problem** (type what is wrong after the command), plus **Skip**, **Previous**, **Next** and **List**.
- `/heraldia review next`, `previous`, `skip [note]` (marks it as skipped and goes to the next one), `goto <id>` (e.g. `goto unica/castillo`; it autocompletes), `list` (every stop with its status; click one to go there), `reset` (clears your marks) and `status` (the summary: how many are checked, with a problem, skipped and pending, and the list of problems).
- `/heraldia review mark checked [note]` and `/heraldia review mark problem [note]`: what the buttons do.
- The search runs off the server thread, with the same rules as `/heraldia info cerca` (from the world spawn, up to 10,000 blocks; Atlantis, anywhere in the world), and never loads or generates chunks: it prefers a structure that is already generated, even if farther away, to a predicted one. If the nearest one has not been generated yet, it warns you that going there generates new terrain and waits until you click **Go and generate** (`goto <id> generate`).
- The teleport loads the destination without blocking the server and leaves you above ground, with no suffocation: feet and head free, solid ground or water below (floating on the sea at Atlantis or the isle), never in lava, fire, magma, cactus or powder snow, searching in a spiral up to 8 blocks around. If there is no safe spot, you are not moved.
- Progress is per player and saved in `heraldia_revision.json`, in the world folder (it survives restarts). Every change also writes `heraldia_revision.md` in the same folder: per player, every stop with its status, its note and the date, those with a problem first.

### Server status: `/heraldia status [page]`

For any player, translated and paged (8 lines per page, with buttons to turn the page): the Heraldia version, how many structures of each kind some player has discovered out of the total (villages, one of each family; unique structures; medium structures, by type; mines, by size), the guardians defeated, the state of the arena with the server record, whether restocking loot is enabled and whether Lootr is installed. Operators also see the difficulty, the key generation, boss and Guide options, what is still undiscovered of each kind and the other mods loaded. Discoveries come from advancements: those of online players, from memory; the rest, from their files in the world folder (read off the server thread).

### Live reload: `/heraldia reload`

For operators (level 2). Reads `config/heraldia.json` again without restarting the server (and without rewriting it) and applies whatever does not affect generation:

- `dificultad.*`: the health and damage modifiers of the Heraldia mobs already loaded are recalculated (the rest, when they load), keeping the proportion of their current health.
- `jefes.*`, `botin.*`, `guia.*`, `aldeas.vida.tratos_estilo`, `aldeas.vida.asedios` (trades are rolled when a villager levels up) and `unicas.atlantida.cofre_unico_por_jugador`: read every time they are used.
- `perfil` (the [gameplay profile](#gameplay-profiles)): applied whole, with whatever is set by hand on top (all its options are among these).
- `golems.*`: the limits are published again to the golem functions.
- `arena.*` (except `arena.generar_en_mundos_nuevos`, which only counts when a new world starts): increments, maximum alive, experience and whether it is enabled. With a match running they do not change until it ends (reload again then).

Everything else (grids and spacings, villages, families and styles, the job board, roads, unique structures, medium structures, mines, compatibility and the minimum distance) affects generation: if it changed halfway, two neighbouring chunks would be generated with different rules and `/locate` and maps would no longer match what was generated. Those options are not applied: the answer lists them with their value in use and the one in the file, and they apply on restart. A new option of the mod belongs to this group unless it is declared reloadable.

## Configuration

File `config/heraldia.json` on the server (in a single-player world, the one in the game folder). It is created at startup with all default values
and rewritten on every startup with the values in use and a help text (`_ayuda`) in Spanish and English (the options of the [gameplay profile](#gameplay-profiles) only if they were set by hand; the `_perfil` block, informative, shows the effective profile and its values). An invalid value (out of range or of another type)
is reported in the log and replaced by its default; an unknown option is reported and ignored. The `version` field allows migrating the file
when its format changes. It is read when the server starts and affects chunks generated afterwards (not what is already generated); whatever does not affect generation can be applied without restarting with [`/heraldia reload`](#live-reload-heraldia-reload).

| Option | Default | Range | What it does |
| --- | --- | --- | --- |
| `perfil` | `estandar` | `casual`, `estandar`, `hardcore`, `personalizado` | [Gameplay profile](#gameplay-profiles): sets difficulty, reinforcements, restocking loot and the arena in one go; never world generation. |
| `aldeas.separacion_bloques` | 1500 | 1000-10000 | Average spacing between villages; the minimum keeps the 62/94 ratio of the grid. |
| `aldeas.maximo` | 100 | 0-100 | Maximum villages per world: only the grid cells closest to 0,0 count (deterministic, no saved data). |
| `aldeas.porcentaje_grandes` | 25 | 0-100 | Percentage of large villages; the rest are standard. |
| `aldeas.distancia_aldeas_vanilla_bloques` | 160 | 0-256 | Minimum distance to a vanilla village (rounded to chunks); 0 disables it. |
| `aldeas.familias.<family>` | `true` | `true`/`false` | Enables a whole family (its 3 styles). |
| `aldeas.estilos.<style>` | `true` | `true`/`false` | Enables a style (standard and large). If a cell picks a disabled one, another style of its biome is tried. |
| `aldeas.vida.tratos_estilo` | `true` | `true`/`false` | Style trades and the map of the area's unique structure at each family's cartographers ([Village life](CONTENT.md#village-life)). |
| `aldeas.vida.tablon` | `true` | `true`/`false` | Job board and bailiff on the square of new villages. |
| `aldeas.vida.asedios` | `false` | `true`/`false` | The weaponsmith of fortified villages sells an ominous bottle to trigger a raid. |
| `aldeas.caminos.activado` | `true` | `true`/`false` | Roads between nearby villages, with bridges, lamp posts and signs ([Roads between villages](CONTENT.md#roads-between-villages)); new chunks only. When off, the feature is not even added to the biomes. |
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
| `jefes.fases.activado` | `true` | `true`/`false` | Guardian phases below 66 % and 33 % health: effects, particles, sound and an action-bar notice ([Guardian fights](CONTENT.md#guardian-fights)); also for structures already generated. |
| `jefes.refuerzos.activado` | `true` | `true`/`false` | Guardian reinforcements: 2 or 3 mobs of its structure once per phase, at most `jefes.refuerzos.maximo_vivos` alive at once; they do not drop the guardian's loot. Works even with phases off (then without effects and with another notice). |
| `jefes.refuerzos.porcentaje` | 100 | 0-300 | How many reinforcements per phase, as a % of the guardian's own (rounded; above 100 its list repeats): 150 = one or two more. |
| `jefes.refuerzos.maximo_vivos` | 4 | 1-12 | Maximum reinforcements alive at once near a guardian. |
| `jefes.barra.activado` | `true` | `true`/`false` | Boss bar with the guardian's name for players within 32 blocks while the fight lasts. |
| `medianas.activadas` | `true` | `true`/`false` | Enables the [medium structures](CONTENT.md#medium-structures). |
| `medianas.frecuencia_porcentaje` | 100 | 25-400 | Frequency of all medium structures, as a % of the default: 200 = twice as many (each type's spacing is divided by the square root). |
| `medianas.distancia_minima.bloques` | 192 | 64-1024 | Minimum distance between two medium structures of different types (and between two of the same type, at most half a grid cell). |
| `medianas.distancia_aldeas_unicas_bloques` | 256 | 128-1024 | A medium structure does not spawn closer than this to the start of a Heraldia village or unique structure that spawns there. |
| `medianas.<id>.activada` | `true` | `true`/`false` | Enables a type of medium structure (`torre_vigia`, `posada`, `campamento`, `ermita`, `molino`, `pescador`, `cazadores`, `templete`). |
| `medianas.<id>.separacion_bloques` | the type's own (576-832) | 256-4000 | Average spacing between two of that type (at 100 % frequency); each grid cell looks for its candidate inside the type's biomes. |
| `minas.entradas.activado` | `true` | `true`/`false` | Enables the [mine entrances](CONTENT.md#mine-entrances) (new chunks only). |
| `minas.entradas.separacion_bloques` | 768 | 256-4000 | Average spacing between two small mine entrances; medium and large ones keep the ratio (x1.5 and x2.5). |
| `minas.vanilla.multiplicador` | 2.0 | 1-5 | Multiplies how often vanilla abandoned mineshafts appear in new chunks (1 = vanilla; decimals allowed, e.g. 1.5). Does not change chunks already generated or other structures. |
| `guia.entregar_al_entrar` | `true` | `true`/`false` | Gives the [Herald's Guide](CONTENT.md#heralds-guide) to each player the first time they join with each mod version. When off, nobody gets it on joining, but `/heraldia guia` still hands it out. |
| `compatibilidad.zona_estructuras_ajenas_bloques` | 224 | 0-512 | Structures from other mods that show above ground do not spawn closer than this to the start of a Heraldia village or unique structure that spawns there; 0 disables it ([Compatibility with other mods](COMPATIBILITY.md#compatibility-with-other-mods)). |
| `botin.reponer.activado` | `false` | `true`/`false` | [Restocking loot](CONTENT.md#restocking-loot-and-difficulty): Heraldia chests and barrels are refilled on opening after the given days, with no other player nearby and when empty or almost empty; also chests already generated. Nothing with Lootr. |
| `botin.reponer.dias` | 7 | 1-60 | In-game days (24,000 ticks of the world clock) after a looting before a chest is restocked. |
| `dificultad.nivel` | `normal` | `facil`, `normal`, `dificil`, `heroica` | [Difficulty](CONTENT.md#restocking-loot-and-difficulty) of Heraldia guardians and template mobs (health and damage); also those already generated, when they load. `normal` is the previous behaviour. |
| `dificultad.escalar_por_jugadores` | `false` | `true`/`false` | +25 % health per extra player within 32 blocks (up to +100 %), when hit. |
| `dificultad.escalar_botin` | `true` | `true`/`false` | With `facil`, `dificil` or `heroica`, plain stackable items of Heraldia chest loot come in x0.75, x1.25 or x1.5 amounts (nothing changes with `normal`). |
| `arena.activado` | `true` | `true`/`false` | [Wave arena](CONTENT.md#wave-arena) near spawn. When disabled, no matches and no protection (a placed arena stays as it is). |
| `arena.generar_en_mundos_nuevos` | `true` | `true`/`false` | In a new world, the arena is built on its own 200-300 blocks from spawn; in an existing one, never (an operator places it). |
| `arena.oleada.mobs_incremento` | 50 | 10-200 | Extra enemies in each wave, as a % of the first wave's (4, 6, 8, 10... with 50), rounded up. |
| `arena.oleada.stats_incremento` | 10 | 1-100 | Extra health and damage in each wave, in %; if it exceeds `mobs_incremento`, that one is used (enemies grow faster than their strength). |
| `arena.max_mobs_vivos` | 20 | 4-64 | Enemies alive at once in the ring; if a wave brings more, they come in batches. |
| `arena.experiencia_porcentaje` | 15 | 0-100 | Experience of arena enemies, as a % of the normal amount (after the game's own scaling); they drop no items. |

Atlantis has no placement options: there is always exactly one per world.

### Gameplay profiles

The `perfil` option sets a group of gameplay options in one go (never world generation: where and how structures spawn, or the arena that builds itself in a new world, are never touched by a profile). `estandar`, the default, is exactly the previous behaviour.

| Option | `casual` | `estandar` | `hardcore` |
| --- | --- | --- | --- |
| `dificultad.nivel` | `facil` | `normal` | `heroica` |
| `dificultad.escalar_por_jugadores` | `false` | `false` | `true` |
| `dificultad.escalar_botin` | `false` | `true` | `true` |
| `botin.reponer.activado` | `true` | `false` | `false` |
| `botin.reponer.dias` | 3 | 7 | 14 |
| `jefes.fases.activado` | `true` | `true` | `true` |
| `jefes.refuerzos.activado` | `true` | `true` | `true` |
| `jefes.refuerzos.porcentaje` | 50 | 100 | 150 |
| `jefes.refuerzos.maximo_vivos` | 2 | 4 | 6 |
| `arena.oleada.mobs_incremento` | 30 | 50 | 75 |
| `arena.oleada.stats_incremento` | 5 | 10 | 20 |
| `arena.max_mobs_vivos` | 12 | 20 | 28 |
| `arena.experiencia_porcentaje` | 30 | 15 | 5 |

- **An option written in the file overrides the profile** (it is "set by hand"). If its value is not the profile's, the profile becomes **custom** (`personalizado`): the log says so at startup, listing which options differ and what the profile would give, and so do `/heraldia profile` and the `_perfil` block of the file. The other options keep the profile's values.
- The options a profile sets are only written to the file when they are set by hand; that way changing `perfil` in the file actually changes them. To go back to the profile's value, delete the option from the file.
- `personalizado` sets nothing: each option takes its value from the file or, if it is not there, its default.
- Files from 0.1.0 (`version` 1) are migrated without changing anything: the mod used to write every option, so the profile options that had their default are removed (with `estandar` they give the same) and the ones with another value stay as set by hand.
- It is applied whenever the file is read (at startup and with `/heraldia reload`), never in the middle of a chunk; mobs already generated take the difficulty when they load, as before.

### Configuration screen (client)

On the client the file can also be edited from a screen inside the game. With [Mod Menu](https://modrinth.com/mod/modmenu) installed (optional; the mod works the same without it, the screen just has no button) it opens from the configuration button of Heraldia in the mod list. It is built from the same option list as the file, so new options appear on their own:

- Sections: Gameplay profile, Villages, Village families, Village styles, Village life, Roads between villages, Golems, Unique structures, Minimum distance between unique structures, Atlantis, Medium structures, Compatibility with other mods, Loot and Difficulty, with a search box (by name, key, help or section).
- Each option shows its value (on/off button, number box, or a button that cycles through the values of a list option such as `dificultad.nivel`). Its tooltip shows the key, the help text (the same as `_ayuda`) and the default and range. An invalid number turns red, its tooltip says why and **Save** stays disabled until it is fixed.
- Gameplay profile: changing it moves the options that had the previous profile's value to the new one's; the ones with another value (set by hand) stay as they are, with their name in gold, and their tooltip shows the profile's value and that they override it. The tooltip of the profile itself shows the effective profile and which options differ. On saving, only the options whose value is not the profile's are written as set by hand.
- **Save** writes `config/heraldia.json` in the same format as at startup (with `version` and `_ayuda`); **Reset to defaults** puts every option back to its default (nothing is written until you save); **Cancel** discards the changes.
- Changes apply when the world is opened again or the server is restarted, and only to chunks generated afterwards; the screen says so. With no world open they are used from the next world you open (no need to restart the game). With a single-player world open, saving reloads live whatever does not affect generation, the same way as [`/heraldia reload`](#live-reload-heraldia-reload) (the report shows in the chat); the rest, after leaving and re-entering it.
- When connected to a server the screen edits **the client's local file** (your single-player worlds), not the server's: the screen warns about it. The server's configuration is still edited in its own `config/heraldia.json`. Nothing is sent over the network.
