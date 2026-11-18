# Final audit of 0.1.0 (16-17/11/2026)

Auditing session after merging into `develop`, in this order, T23 docks (#62), T24 medium structures 1 (#61), T25 roads (#63),
T26 medium structures 2 (#64), T27 Guide (#65), T28 bosses with phases (#66), T29 refilling loot and difficulty (#67), T30 mines
(#68), T31 arena (#70), T33 languages and README (#71) and T32 generation cost in CI (#69), on top of T1-T22. Audited base:
`develop` at `a15df3f`. Fixes: PR #72 (branch `claude/heraldia-auditoria`). `mod_version` stays at 0.1.0; neither
`main` nor `publish.yml` is touched.

## Battery results

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
- `mundo_existente.py` (new): first, bugs in the test itself (NBT arrays and the 26.3 palette, the
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

## Cross review (what no session tested together)

| Cross | How it was checked | Result |
|---|---|---|
| Roads versus mines | code (`CaminoFeature.cajas`: pieces of `surface_structures` structures in 3D; mine mouths are, the galleries do not cover the surface) | ✅ the road stops at the mouth and passes over the galleries |
| Roads versus arena | code (`Obras.nivelar`, `Estructuras.ocupado`) | ⚠️ the arena does not know about roads: if it is placed on one it cuts it (risk below) |
| Medium structures versus mines | `entradas_mina.py` (no medium structure closer than `medianas.distancia_minima.bloques` to a mine) and `MinasTest` | ✅ |
| Difficulty and boss phases versus the arena | code (`Juego.crear/preparar`: own modifiers added to the difficulty's; the mini-boss carries `heraldia_guardian`) and `arena.py` (phases and reinforcements of the mini-boss) | ✅ |
| Loot refill versus mines and arena | `ReposicionTest` (every chest table of the templates is refilled; it now also requires the mine ones) | ✅ refill; ❌→✅ the **difficulty** did not scale mine loot (fixed) |
| Guide, all its pages, in the 8 languages | `GuiaTest.libroEnCadaIdioma` (8 languages), generator check (each page fits in each language) and `guia.py` | ✅ |
| `rejilla_compatible` with the new content | `rejilla_compatible.py` (coordinates from main) and `CaminoFeature`/`Caminos` (they use the grid in use) | ✅ |
| Existing world: nothing changes in what is already generated | **new test** `mundo_existente.py`: generates area A with the new content off, stops, starts with the default configuration (file deleted) and then with almost everything changed; compares A (and B) by reading the regions; checks that the new ring does get a road (16 chunks, 159 columns) | ✅ 64 of 64 chunks identical, no entity lost, the arena says "existing world" |
| Overall performance | `coste_generacion.py` locally and on CI | ✅ +3.4 % |
| Mod compatibility | the 9 `compat_mods.py` groups (local and CI) | ✅ |

## Fixes (PR #72), each with its test

1. **Buckets from dispensers next to the arena**: `ArenaCuboMixin` (`BucketItem`/`SolidBucketItem.emptyContents`, early
   exit without an arena) with the pure logic in `Zona.cuboNegado` (`ZonaTest`); in `arena.py`, a dispenser with lava
   next to the arena does not empty it (it drops it as an item) and another one far away does.
2. **Mine loot and difficulty**: `dificultad.escalar_botin` did not touch `heraldia:minas/` (T29 was merged before
   T30). `DificultadMobs.esBotinDeCofre` uses the same list as the refill (`DificultadTest`, `ReposicionTest`).
3. **Signs**: about 110 lines in the 8 languages were wider than 90 px (the "Pending bugs" list was incomplete) and
   the game cuts the words that do not fit. Rewritten without changing keys or blocks; generation now fails with
   any line wider than 90 px in any language, counting bold (+1 px per character) (`test_idiomas.py`).
4. **New test `tools/smoke/mundo_existente.py`** (above), with its pure functions in `test_smoke_descarga.py`.
5. **Test downloads**: `server_smoke.download` retries a cut download and does not leave a broken `.jar` in the cache
   (`test_smoke_descarga.py`).
6. **Jarl's Hall**: diagnostics ("DIAG trampa": entities within 24 blocks of the tripwire and contents of the dispensers) if
   it fails again. The check has not been changed.
7. **Documentation**: the mod on clients is optional (the development guide and `CONFIGURACION`/`CONFIGURATION` said it went
   on every client); warning about the slow mine `/locate` in `CONTENIDO`/`CONTENT`; lessons and status of each
   pending bug in `LESSONS`; `CHANGELOG` (0.1.0 unpublished) with all of the above. The READMEs in the 8 languages
   were already up to date with what had been merged (`test_readme.py`).

## Remaining risks

- `/locate structure #heraldia:minas` stalls the server for ~4 s from a place with no mines nearby (documented; normal play
  does not go through it: there are no mine maps and `/heraldia info cerca` searches off the thread).
- The arena, when placed, only avoids the structures of chunks already saved and does not know about roads: in a new world
  it could step on a structure that is generated during construction, and in any world it cuts a road that passes through its site. In
  the owner's world (already existing) it is only placed by hand with `/heraldia arena colocar`, which shows the site first.
- The intermittent Jarl's Hall failure still has no known cause (only the test; the rest of that test always passes).
- Roads only appear in new chunks: in an existing world, one between an old village and a new one stops at the
  edge of what is already generated. This is expected (documented), but it will be visible.
- The visuals (rewritten signs, the Guide on the client, boss bars, arena) are not accepted without screenshots.

## Recommended options for the owner's world

Back up the world first. With the default values the existing world does not change in what is already generated
(checked by `mundo_existente.py`), and:
- `unicas.rejilla_compatible`: **`true` only if the world already had Heraldia 0.1.0** (the one on `main`); if it never had it,
  `false` (default).
- `arena.*`: default. In an existing world it does not build itself (checked by the "mundo existente" log); if
  wanted, `/heraldia arena colocar` (look at the site before `confirmar`: it clears and levels).
- `botin.reponer.activado`: `false` (default) unless wanted; `dificultad.nivel`: `normal`.
- `guia.entregar_al_entrar`: `true` (default): each player receives the Guide once.
- Everything else, default (roads, medium structures, mines x2, bosses with phases).

## What to test by hand (needs a real client or screenshots)

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
