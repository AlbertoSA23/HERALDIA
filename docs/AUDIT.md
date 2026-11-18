# Final audit T45: T23-T47 together (18/11/2026)

Auditing session after T23-T47 were merged into `develop` (the last one, T47c, PR #88, `develop` at `2166dbc`). Under the
testing policy of 17-Nov-2026 each session ran only its own new tests and did not wait for CI; this audit runs everything,
reviews what breaks *between* tasks and fixes it. Fixes: PR #89 (branch `claude/heraldia-audit`). `mod_version` stays at
0.1.0; `main` is not touched (`publish.yml` does not exist in the repository: nothing to change).

## Headline

**The `develop` `.jar` did not start.** T47b renamed seven mixin classes (`ArenaCuboMixin` → `ArenaBucketMixin`, ...) without
renaming them in `heraldia.mixins.json`, which is `required`: the mod crashed at startup. `./gradlew build` was green (no
JUnit test loads that file), and every server job of CI had been failing since #87 without anyone looking (the policy
did not wait for CI). Fixed, with `MixinConfigTest` so it cannot happen again. Behind it, several server tests had been
broken by T44 and T47c and were hidden by the crash; all fixed below.

## Battery results

| What | Where | Result |
|---|---|---|
| CI on every push to `develop` since #87 (runs 159, 161) | GitHub | ❌ every server job: the `.jar` did not start (fix 1) |
| `./gradlew build` with `testPesado` (`UniqueSeparationTest`, `MinesDeterminismTest`), `develop` and branch | local, 4 cores | ✅ 6 min 29 s (`testPesado` alone, develop); 8 min 2 s (full build, branch) |
| Generator pytest | local and CI | ✅ 901 on develop, 902 on the branch |
| `tools/changelog.py check` | local and CI | ✅ |
| Renames: generated data of `edf3518` vs head | local | ✅ 5,709 files byte-identical |
| Smoke test (`server_smoke.py`) | local and CI | ❌ on develop (did not start) → ✅ |
| Full CI battery of the PR (`[bateria completa]`: build, JUnit, smoke, cost and 16 groups with the 44 server tests and the 9 `compat_mods` groups) | GitHub, run 165 (`931735f`) | 20 of 21 jobs ✅; ❌ `anchored_guardians` (fixed afterwards, fix 11); final run: @@FINAL@@ |
| Server tests broken and fixed in this audit: `quests` (2 of 2 locally, ✅ CI), `update` (✅), `update_path_b` (new, ✅ local and CI), `admin` (60/60 ✅), `web_maps` (✅), `story` (✅), cathedral `smoke_game` (✅), `anchored_guardians` (✅ local) | local and CI | ✅ |
| Generation cost (`generation_cost.py`, 3 passes) | CI run 165 | ✅ **+2.3 %** (reference +9.3 %, limit +19.7 %); CPU per chunk 75.9 → 77.7 ms (medians); `/locate` village 297-379 ms, unique 279-332 ms, medium 48-64 ms, mine 767-873 ms |

Environment note: in this container Maven Central answered `HEAD` requests with 404 (and some `GET`s at random), so Gradle
could not resolve dependencies; the audit used a local caching mirror (a Gradle init script in `~/.gradle`, nothing in
the repository). Not a problem of the project: CI resolves normally.

## Fixes (PR #89), each with its test

1. **Mixin configuration** with the T47b class names (the mod did not start). `MixinConfigTest`: every listed mixin exists
   and every `*Mixin.java` is listed. Verified: smoke test on a dedicated server.
2. **`/heraldia update undo` left behind the files that `apply` created** (found by the new path-B test): placing a structure
   in a region without a POI (or entities) file created it, and undo only put back the files it had backed up, so the beds
   and workstations of the removed structure stayed registered. `Plan.absent` (`ausentes` in the JSON; an older plan reads
   with nothing to delete) and undo deletes only `r.X.Z.mca` names inside `region/`, `entities/` and `poi/`. `UndoTest`
   and `tools/smoke/update_path_b.py`.
3. **Nether mediums did not see vanilla fortresses**: `minecraft:fortress` is placed in `UNDERGROUND_DECORATION`, which the
   medium rule takes for "underground". Now it is visible (same 80-block distance as the other vanilla structures).
4. **The Overworld Atlantis blocked Nether and End uniques** within 1,000 blocks of its anchor's X/Z (the "always wins"
   shortcut ran before any dimension check). `UniqueSeparation.Viability.inDimension`; the Overworld is unchanged
   (`UniqueSeparationTest`, `testPesado`).
5. **Enum ids saved in NBT/JSON** (`Layer`, `Shoreline.Mode`, `Revision.Mark`, `Destination.Type`, quests `Type`): the
   `of(...)` parsers T47b added compared case-sensitively where the old `valueOf(s.toUpperCase())` did not; back to
   case-insensitive (a hand-edited file keeps loading).
6. **Intermittent quests failure (`specialPrice` None, CI of #81)**, real cause: `MerchantOffer.CODEC` omits `specialPrice`
   when it is 0, and a plaza villager with AI that walked up to the simulated player could take its `use once`; it then
   traded with the player and followed it, so every retry hit it again and the test villager never opened its trades. The
   test now closes any trade, removes the villagers next to the spot and slows the rest before each use (a missing field
   reads as 0), and the fake player gets water breathing and resistance (it drowned once where `close_out` leaves it).
   Passed 2 of 2 locally. The mod was right.
7. **Server tests broken by T47c** (they translated strings that are the mod's output or its published keys):
   `web_maps.py` wrote `mapas_web.only_discovered`/`layers` (the keys are `solo_descubiertas`/`capas`: the mod
   ignored them, "opción desconocida"); `update.py` looked for `marcas=CAMBIA` in a log that now prints the enum
   `CHANGES`; `admin.py` looked for `Destino`/`generada=` in the `toString` of a record renamed to
   `Destination(pos, generated)`; `uniques/cathedral/smoke_game.py` imported `pieces` (now the `_common.pieces` module,
   the function is `split_pieces`).
8. **Server tests not adapted to T44**: `story.py` required a map on every Chronicle sheet, but the generator (by design)
   gives no map to or from a Nether or End unique (an exploration map only searches its own dimension); the test now
   reads each unique's dimension from the `.jar`. `medium_structures.py` and `mine_entrances.py` required 256 blocks
   to lighthouses and wrecks, which only yield at 192: a legal lighthouse at 192-255 blocks failed them depending on the
   seed. `anchored_guardians.py` had not passed since T44 and hid two real bugs (fix 11).
9. **New tests**: `tools/smoke/update_path_b.py` (path B of `update apply` and `undo` on a dedicated server: a medium
   structure disabled while a zone is generated, then enabled; analyze proposes it, apply places it without touching
   the 50-block margin of a build, the game sees it; undo leaves the files byte-equal to before apply);
   `ConfigPanelTest.everyPanelTextInEachLanguage` (the dialog panel, built in the 8 languages for the 3 profiles and the
   7 menus: every text exists in that language, not only through the Spanish fallback, with the same format arguments);
   `MixinConfigTest`; `UndoTest`.
10. **Documentation**: `docs/DEVELOPMENT.md` refreshed after the renames (every path, class, test and flag checked against
    the tree; what still stays Spanish is listed); `CONFIGURATION`/`CONFIGURACION` (`choza_mago` among the medium
    kinds, spacing range 576-1024, the 25 sections of the client screen, `actualizar.margen_bloques` reloadable, the
    Nether/End uniques in `unicas.rejilla_compatible`), `CONTENT`/`CONTENIDO`, `COMPATIBILITY`/`COMPATIBILIDAD`,
    `BUILDING`/`COMPILAR` (old class and folder names); the 8 READMEs (vanilla clients also get quests, arena, caravans
    and notices in their language); a CHANGELOG bullet T47a had left above `## [0.1.0]`; `LESSONS.md`.
11. **Nether mobs did not stay anchored** (T44): the magma altar's magma cubes hop with their own goal and the piglin
    outpost's brutes walk with a brain; neither looks at `noActionTime`, so `Anchoring` did not hold them (5-11 of 30 left
    their post in 200 ticks). Two narrow mixins, `CubeMobJumpMixin` (the hopping goal does not start while the cube is
    anchored and still) and `PiglinStrollMixin` (an anchored, still piglin forgets its walk target after each brain tick);
    with a target or after a hit they fight as before. In `anchored_guardians.py`, two test bugs: `/place jigsaw` put every
    test mob in a one-block pit (the shulker never saw the player: "does not attack"), and the unanchored control kept the
    `heraldia_adulto` tag and a `heraldia.*` name, so the T46 mob fixes anchored it again.

## Renames (T47b/T47c): nothing the world saves changed

Compared `edf3518` (before T47b) with the audited head:
- **Generated data**: the generator run on both commits gives the same 5,709 files (3,170 templates, 1,251 pools),
  byte-identical, `.nbt` included. `src/main/resources` and `src/client/resources` did not change (apart from the mixin
  list, fixed above). So structure, loot, advancement and tag ids, translation keys and the generated texts are the same.
- **Java string literals**: every literal of `src/main` and `src/client` extracted from both commits and compared: no old
  literal disappeared except the three web-map adapter class names (loaded by reflection, the new classes exist) and the
  GitHub URL (the repository moved). NBT keys, attachment ids, codec field names, command literals and aliases,
  configuration keys, mob tags, `-D` properties and file names are the same.
- **Enums**: those saved or parsed by name (`Capa`, `Destino.Tipo`, `Orilla.Modo`, `Revision.Tipo/Marca`, quests `Tipo`,
  `Reputacion`, `Dificultad`, `Perfil.Tramo`) now carry an explicit id equal to the old lowercase name; the others were
  never serialized by name. **Gson**: `update/Plan` (the only POJO) has `@SerializedName` with the old keys on every
  renamed field; `HeraldiaConfig`, `Revision` and the maps ledger write literal keys.
- What changed and is not saved: log lines that print a renamed enum or record (e.g. `{marcas=CHANGES}`), the Python
  tools' names and flags (`--affected`, `--all`, `--group`, `--ci-matrix`, `--full`), the Java class names.

## Cross review (what no session tested together)

| Cross | How it was checked | Result |
|---|---|---|
| Wizard's huts (T43) yield to mines | code end to end: tag `#heraldia:medianas/ceden_a_minas` generated (`test_mediums.py`), read in `MediumStructures`, applied in generation, `/locate` and `/heraldia info nearby`; `MediumsTest`; `mine_entrances.py` (no medium within 192 blocks of a mine, `/locate` of a medium mine under 9,000 blocks) | ✅ |
| Nether/End (T44) vs the Overworld rules | code: `Dimensions.possible` keeps every grid in its dimension; mines, coast and roads return early outside the Overworld; `UniqueSeparationTest` and `MediumFrequencyTest` skip `heraldia:dimension` | ✅, ❌→✅ fortresses and Atlantis (fixes 3 and 4) |
| Nether/End uniques vs other mods' structures | code (`ForeignZone.active` is Overworld-only) | ⚠️ not handled (risks) |
| Lighthouses/wrecks (T42) vs mediums, mines, villages | `coast.py`; code (`Coast`: 256 to villages and uniques, 192 to mediums and mines, 80/128 to vanilla and other mods) | ✅ (tests fixed, 8) |
| Salts and spacing | all 45 Heraldia structure_sets: distinct salts; separation < spacing in every default and clamped at runtime | ✅ |
| Per-chunk cost of the new rules | code: the hot path stays at map lookups, the expensive parts only at candidates and memoized; `generation_cost.py` | ✅ (+2.3 %) |
| Translations (8 languages) | 1,577 base keys + 194 per structure, same set in all 8; every `heraldia.*` key used in Java exists; every key built at runtime (caravan phases, repair ids, arena modes, panel menus, review stops, quest states, map layers, wizard nicknames, Nether/End names) exists; the panel in 8 languages (new JUnit) | ✅ |
| Command tree | the 17 nodes of `HeraldiaCommands` match `CANONICAL`; `update` registered by `VersionNotice` and `Updater` (Brigadier merges them); old aliases = `commands.OLD`; every `/heraldia ...` in README and docs parses | ✅ |
| Reloadables | every prefix of `Reload.RELOADABLE` is read on use or re-read by `ReloadCommand.apply` | ✅ (`actualizar.margen_bloques` was missing from the docs) |
| Existing worlds | the 12 attachments read safely when absent; fields added later are `optionalFieldOf` with defaults; a missing config key falls back to its default; the 0→1→2 config migration; `existing_world.py` | ✅ |
| Web maps outside the Overworld (T44) | code: `WebMaps` exits for non-Overworld chunks; `Site`/`Ledger` have no dimension | ⚠️ decided: acceptable (below) |

**Web maps and the Nether/End (decision).** The web maps only show the main world. It is acceptable for 0.1.0: the
early exit prevents the real risk (Nether coordinates drawn on the Overworld map), the CHANGELOG already says so, and
Nether/End structures are few. Doing it properly needs a dimension in `Site` and in the ledger (with `Ledger.VERSION`
bumped and old entries defaulting to the Overworld), markers grouped per dimension and each adapter's world id
(squaremap `minecraft:the_nether`, BlueMap per level, Dynmap's names vary by version): about 200 lines plus tests, for a
later version.

## Remaining risks (not fixed, written in LESSONS "Pending bugs")

- Nether/End uniques do not yield to other mods' structures (`ForeignZone` is Overworld-only and its memo is keyed by
  seed alone). With Nether/End structure mods they can overlap.
- In the Nether and the End, the medium rule still computes the Overworld grids' candidates before discarding them
  (memoized and capped; only at candidates).
- `Detector.placeable` (update path B) rejects a placement whose box overlaps any saved structure *in plan view*, ignoring
  height: a mineshaft deep below is enough. In a real world path B will rarely place anything. A 3D test with some
  slack would fix it; not changed (it errs on the safe side).
- With an extreme `medianas.frecuencia_porcentaje` and a large `medianas.distancia_minima.bloques`, `GridPlacement`
  clamps the separation to `spacing / 2` and two mediums of the same kind can be closer than the configured minimum.
- The arena in a **new** world only avoids structures of chunks already saved (known since the previous audit).
- Not verified: in 26.3 `Mob.checkDespawn` may reset `noActionTime` also for persistent mobs with a player within 32
  blocks; if so, anchored mobs could start wandering when a player comes close, before they have a target. The anchoring
  tests have no player near the mobs during the hold phase. To check on the owner's server (below).
- Everything visual still needs the owner's screenshots (list below).

## What to test by hand on the owner's server

Back up the world first (and keep the backup until all of this is checked).
1. **Startup with the real CurseForge modpack**: the log says `Heraldia: 180 estructuras registradas`, no registry or
   mixin errors (this is what failed on `develop` before this audit).
2. **Existing world**: open the owner's world; the log says the version it was generated and opened with
   (`heraldia:version_mundo`); nothing already built changes. Explore new land: roads end at the edge of what was
   generated, lighthouses and huts appear only in new chunks.
3. **`/heraldia update analyze`** on the owner's world: read the report and the PNG map (protected chunks around every
   build, 50-block margin). Only if it looks right: `/heraldia update apply` **with backup** on a copy of the world first,
   then `/heraldia update undo` on that copy, and check the region files are back (and no beds or workstations left
   registered where a structure was removed).
4. **Configuration panel** (`/heraldia config`, operator, vanilla client): screenshots of the main dialog and of the 7
   submenus in Spanish and in one more language; sliders, checkboxes and lists show the current values; Save writes
   `config/heraldia.json`; `/heraldia language` changes the player's language.
5. **Nether and End**: screenshots of the four Nether mediums (piglin outpost, magma altar, basalt watchtower, fungus
   shrine), the three End ones, the Ash Citadel and the Void Sanctum; check that none stands on a fortress bridge or a
   bastion; `/heraldia review` to a Nether and an End stop with a player.
6. **Wizard's huts** (decoration, chimney smoke, the evil wizard's reveal and fight: particles, boss bar, vexes),
   **lighthouses and wrecks** (the light at night), **caravans** (merchant, llamas, bandits along a road),
   **treasure maps**, **job board quests** (prices drop with reputation), **arena modes** and the weekly leaderboard.
7. **Web maps** (if the server has BlueMap, Dynmap or squaremap): the layers, the icons and names; only discovered
   structures by default.
8. **Anchored mobs with a player near**: stand 10-20 blocks from a guardian, the magma altar's cubes and the piglin
   outpost's brutes without being seen (sneaking, or invisible) for a minute: they should stay at their post.
9. The items of the previous audit that are still open: rewritten signs in several languages, the Guide on a vanilla
   client, boss bars, mines, docks, the client configuration screen with Mod Menu.


# Previous audit: 0.1.0 before T34 (16-17/11/2026)

Auditing session after merging into `develop`, in this order, T23 docks (#62), T24 medium structures 1 (#61), T25 roads (#63),
T26 medium structures 2 (#64), T27 Guide (#65), T28 bosses with phases (#66), T29 refilling loot and difficulty (#67), T30 mines
(#68), T31 arena (#70), T33 languages and README (#71) and T32 generation cost in CI (#69), on top of T1-T22. Audited base:
`develop` at `a15df3f`. Fixes: PR #72 (branch `claude/heraldia-auditoria`). `mod_version` stays at 0.1.0; neither
`main` nor `publish.yml` is touched.

### Battery results

| What | Where | Result |
|---|---|---|
| Full CI of `develop` (a15df3f, push) | GitHub, run 43972960402 | ✅ 16 jobs |
| Full `./gradlew build` (with `testPesado`), develop | local, 4 cores | ✅ 8 min 30 s |
| Full `./gradlew build`, audit branch | local | ✅ 8 min 5 s |
| Generator pytest | local and CI | ✅ 622 on develop; 637 on the branch |
| `tools/changelog.py check` | local and CI | ✅ |
| Full server battery (45 tests: smoke, 43 server tests —with the 9 `compat_mods` groups— and the new `mundo_existente`), develop `.jar` | local, 2 lanes with different `--work` | 43 ✅, 2 ❌ expected (below) |
| Tests affected by the fixes, branch `.jar`: smoke, `arena`, `guia`, `botin_reponer`, `dificultad`, `entradas_mina`, Jarl's Hall, `mundo_existente` | local | ✅ all |
| Generation cost, branch `.jar` (3 passes) | local, on the machine only | ✅ **+3.4 %** (reference +9.3 %, limit +19.7 %) |
| Full CI of the PR (`[bateria completa]`) | GitHub | ✅ 16 jobs at 76f116c (see the final head in the PR) |

Failures seen and why:
- `arena.py` with the develop `.jar`: the two **new** dispenser checks (a dispenser next to the arena
  emptied a lava bucket into it). This is the real bug the PR fixes; with the branch `.jar` it passes (local and CI).
- `existing_world.py` (new): first, bugs in the test itself (NBT arrays and the 26.3 palette, the
  256-chunk limit of `/forceload`), and then 78 differences that **are not the mod's** (lava and water still flowing in the
  caves at the edges, doors opened by villagers, vault `server_data`): with the world frozen
  (`/tick freeze`) on startups 2 and 3, 0 differences. It passes locally and on CI.
- Environment, not the mod: a Fabric API download cut by the network stayed in the cache of a test folder and
  made everything after it fail in 1 s (fixed: see below); and a run I started by mistake with Java 21.
- Jarl's Hall ("tripwire dispensers loaded") **has not been reproduced**: 6 out of 6 locally (one in the
  battery with another server at the same time, four in a row while building and one with the branch `.jar`) and on CI.

Cost (local, median of 3 passes): CPU per chunk 50.8 → 52.5 ms (+3 %), structure steps 5.72 → 6.35 ms per
chunk, max memory after GC 368 → 390 MB, MSPT p99 2.8 → 10.0 ms (during generation with Chunky; max 10.8 ms).
`/locate`: village 259 ms, unique 288 ms, medium 39 ms, **mine 4,277 ms** (documented).

### Cross review (what no session tested together)

| Cross | How it was checked | Result |
|---|---|---|
| Roads versus mines | code (`CaminoFeature.cajas`: pieces of `surface_structures` structures in 3D; mine mouths are, the galleries do not cover the surface) | ✅ the road stops at the mouth and passes over the galleries |
| Roads versus arena | code (`Obras.nivelar`, `Estructuras.ocupado`) | ⚠️ the arena does not know about roads: if it is placed on one it cuts it (risk below) |
| Medium structures versus mines | `mine_entrances.py` (no medium structure closer than `medianas.distancia_minima.bloques` to a mine) and `MinasTest` | ✅ |
| Difficulty and boss phases versus the arena | code (`Juego.crear/preparar`: own modifiers added to the difficulty's; the mini-boss carries `heraldia_guardian`) and `arena.py` (phases and reinforcements of the mini-boss) | ✅ |
| Loot refill versus mines and arena | `ReposicionTest` (every chest table of the templates is refilled; it now also requires the mine ones) | ✅ refill; ❌→✅ the **difficulty** did not scale mine loot (fixed) |
| Guide, all its pages, in the 8 languages | `GuiaTest.libroEnCadaIdioma` (8 languages), generator check (each page fits in each language) and `guide.py` | ✅ |
| `rejilla_compatible` with the new content | `compatible_grid.py` (coordinates from main) and `CaminoFeature`/`Caminos` (they use the grid in use) | ✅ |
| Existing world: nothing changes in what is already generated | **new test** `existing_world.py`: generates area A with the new content off, stops, starts with the default configuration (file deleted) and then with almost everything changed; compares A (and B) by reading the regions; checks that the new ring does get a road (16 chunks, 159 columns) | ✅ 64 of 64 chunks identical, no entity lost, the arena says "existing world" |
| Overall performance | `generation_cost.py` locally and on CI | ✅ +3.4 % |
| Mod compatibility | the 9 `compat_mods.py` groups (local and CI) | ✅ |

### Fixes (PR #72), each with its test

1. **Buckets from dispensers next to the arena**: `ArenaCuboMixin` (`BucketItem`/`SolidBucketItem.emptyContents`, early
   exit without an arena) with the pure logic in `Zona.cuboNegado` (`ZonaTest`); in `arena.py`, a dispenser with lava
   next to the arena does not empty it (it drops it as an item) and another one far away does.
2. **Mine loot and difficulty**: `dificultad.escalar_botin` did not touch `heraldia:minas/` (T29 was merged before
   T30). `DificultadMobs.esBotinDeCofre` uses the same list as the refill (`DificultadTest`, `ReposicionTest`).
3. **Signs**: about 110 lines in the 8 languages were wider than 90 px (the "Pending bugs" list was incomplete) and
   the game cuts the words that do not fit. Rewritten without changing keys or blocks; generation now fails with
   any line wider than 90 px in any language, counting bold (+1 px per character) (`test_languages.py`).
4. **New test `tools/smoke/existing_world.py`** (above), with its pure functions in `test_smoke_descarga.py`.
5. **Test downloads**: `server_smoke.download` retries a cut download and does not leave a broken `.jar` in the cache
   (`test_smoke_descarga.py`).
6. **Jarl's Hall**: diagnostics ("DIAG trampa": entities within 24 blocks of the tripwire and contents of the dispensers) if
   it fails again. The check has not been changed.
7. **Documentation**: the mod on clients is optional (the development guide and `CONFIGURACION`/`CONFIGURATION` said it went
   on every client); warning about the slow mine `/locate` in `CONTENIDO`/`CONTENT`; lessons and status of each
   pending bug in `LESSONS`; `CHANGELOG` (0.1.0 unpublished) with all of the above. The READMEs in the 8 languages
   were already up to date with what had been merged (`test_readme.py`).

### Remaining risks

- `/locate structure #heraldia:minas` stalls the server for ~4 s from a place with no mines nearby (documented; normal play
  does not go through it: there are no mine maps and `/heraldia info cerca` searches off the thread).
- The arena, when placed, only avoids the structures of chunks already saved and does not know about roads: in a new world
  it could step on a structure that is generated during construction, and in any world it cuts a road that passes through its site. In
  the owner's world (already existing) it is only placed by hand with `/heraldia arena colocar`, which shows the site first.
- The intermittent Jarl's Hall failure still has no known cause (only the test; the rest of that test always passes).
- Roads only appear in new chunks: in an existing world, one between an old village and a new one stops at the
  edge of what is already generated. This is expected (documented), but it will be visible.
- The visuals (rewritten signs, the Guide on the client, boss bars, arena) are not accepted without screenshots.

### Recommended options for the owner's world

Back up the world first. With the default values the existing world does not change in what is already generated
(checked by `existing_world.py`), and:
- `unicas.rejilla_compatible`: **`true` only if the world already had Heraldia 0.1.0** (the one on `main`); if it never had it,
  `false` (default).
- `arena.*`: default. In an existing world it does not build itself (checked by the "mundo existente" log); if
  wanted, `/heraldia arena colocar` (look at the site before `confirmar`: it clears and levels).
- `botin.reponer.activado`: `false` (default) unless wanted; `dificultad.nivel`: `normal`.
- `guia.entregar_al_entrar`: `true` (default): each player receives the Guide once.
- Everything else, default (roads, medium structures, mines x2, bosses with phases).

### What to test by hand (needs a real client or screenshots)

1. **Rewritten signs**, with a vanilla client (Spanish text) and with the mod in another language: no line should be
   cut. The longest: the agora and academy of Atlantis, the cathedral seal, the runes and vestibule of Jarl's Hall,
   the lighthouse office, the headframe of the lost mine and the bold title of the Atlantis temple seal.
2. **Herald's Guide** on a vanilla client with the language set to French, German, Catalan...: it arrives in that language,
   the pages do not overflow and the journal is sorted correctly.
3. **Arena**: place it with `/heraldia arena colocar` (visible particles), a game up to wave 5 with the
   mini-boss (boss bar, titles, sidebar scoreboard), die in the ring (respawn at the entrance with the inventory,
   which cannot be done in the test: the simulated player disconnects on death) and a dispenser with lava next to the wall.
4. **Bosses with phases**: the boss bar, the action bar warning, particles and sound on phase change.
5. **Roads and medium structures in an existing world**: explore new land and see how a road ends at the edge of what is
   already generated; street lamps, bridges and the sign with the name of the next village.
6. **Mines**: go down a mouth of each size (rails, crossings, minecart, spiders and spawner).
7. **Docks** of the coastal villages: the dock reaches the water.
8. **Configuration screen** (with Mod Menu, client with the mod): the new sections (arena, difficulty, loot).
9. With the real **CurseForge modpack**: start the server and look at the log (`Heraldia: 142 estructuras
   registradas`, with no registry errors) and the MSPT while exploring.
