# Heraldia: building and testing

**English** · [Español](COMPILAR.md)

Back to the [README](../README.md).

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

The second one downloads a real Fabric 26.3 server into `build/smoke`, starts it with the mod and checks that all 174 structures and all 120 advancements are loaded, that `/place structure` places a village with villagers and that the functions exist.

Server tests for each unique structure (same `--jar` argument): `tools/smoke/coliseo_redstone.py`, `observatorio_smoke.py`, `palacio_redstone.py`, `ciudadela_check.py` and `galeon_test.py`, and in `tools/gen/unicas/`: `castillo/prueba_redstone.py`, `torre_mago/prueba_redstone.py`, `catedral/prueba_juego.py` and `prueba_servidor.py` of `fortaleza_hielo`, `mansion`, `monasterio`, `piramide`, `salon_jarl`, `santuario`, `laboratorio_micelio`, `mina_perdida` and `isla_corsario`. Atlantis is checked within the smoke test (`atlantida/humo.py`). `tools/smoke/trofeos.py` adds Carpet (pinned version) and, with a simulated player, kills each guardian and checks that it drops its trophy (and that `/kill` does not) and that the trophy challenge is granted with the last one. `tools/smoke/jefes_fases.py` (with Carpet) summons guardians with their tags, like one already generated, takes their health down with `/damage` to each threshold and checks the phase tags, the effects, the reinforcements (how many, which type, with their gear and tags, adults, without the guardian's table, not repeated and capped at 4), the boss bar (through the log: on the first hit, when the player leaves and comes back, and on death) and, on a second start with the three options off, that none of that happens. `tools/smoke/historia.py` (also with Carpet) checks that the Chronicle chain goes through every unique structure, that each one's chest drops its leaf and that the simulated player earns the Chronicler challenge with the last one. `tools/smoke/aldeas_variantes.py` places several villages of the same style, reads the saved regions and identifies, by comparing blocks with the templates in the `.jar`, which variant of each special building came out; it checks that each one matches exactly one variant and that different variants come out, and measures each `/place`. `tools/smoke/guardianes_adultos.py` places 200 times, through the same path as world generation, every zombie-type mob of the templates (zombie, husk, drowned) and checks that none comes out as a baby, with another weapon or on a mount. `tools/smoke/guardianes_anclados.py` (with Carpet) places 30 times, through the same path, every mob of the templates tagged `heraldia_anclado` (the guardians and the drowned of Atlantis) and checks that none can pick up items and that after 200 ticks, and again after unloading and reloading the chunks, all are still where they appeared (a control batch without the tag must wander and pick up items); then that each one attacks the simulated player 8 blocks away, and that each guardian is still in its room 200 ticks after placing its real template in daylight. `tools/smoke/rejilla_compatible.py` turns on `unicas.rejilla_compatible` and checks that `/locate` of several unique structures from 0.1.0 gives exactly the coordinates of the 0.1.0 `.jar` (fixed in the script, with how they were obtained). `tools/smoke/coste_generacion.py` measures the world generation cost: it generates the same zones of the same world (fixed seed) with and without Heraldia, three runs of each, and compares the server CPU per chunk with the reference in `tools/smoke/coste_referencia.json` (it fails on a regression; it also reports the steps of each chunk, MSPT, memory and `/locate` times; see `DESARROLLO.md`). Measured in the CI (4 cores): +9.3 % CPU per chunk with Heraldia. With `-Dheraldia.perfil=true` on the server JVM, Heraldia logs on shutdown how long its most expensive generation steps took (placement rules, mine slope search, harbour shore search, roads...); without it, it measures nothing.

All server tests share the helpers in `tools/smoke/server_smoke.py` (`Context`): checks that always answer (`test` refuses an `execute` with `as`/`at` or more than one condition, which can stay silent on the console), waits by condition with a generous limit (`until`, `wait_entity`, which prints where the entities of that type or tag are if it gives up), waits counted in game ticks (`ticks`, with `/time query gametime`) and `pos` (reads `Pos` with `data get entity`). Guardians and other mobs with AI are looked up by their tag, not in a box next to their spot. Each test server picks a free port, so several tests can run at once on the same machine.

Versions are pinned in `gradle.properties`. Generator tools: `tools/gen/sim.py` (simulates jigsaw assembly; `python3 tools/gen/sim.py [style ...]` counts the variants of the special buildings, houses, villagers, golems and beds), `tools/gen/render.py` (isometric renders; `python3 tools/gen/render.py <folder> [style ...]` draws the variant sheets), `tools/gen/lint.py` (design audit).
