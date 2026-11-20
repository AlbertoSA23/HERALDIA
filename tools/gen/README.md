# Heraldia structure generator

Python scripts that generate the mod's data resources (NBT templates, jigsaw pools, structures, loot, functions and texts). Gradle runs it when compiling; there is no need to launch it by hand.

Requirements: Python 3.11+, `pip install -r requirements.txt`.

- `python3 main.py --out <folder> --registries <mcmeta 26.3 summary>` → generates, validates and audits; it writes nothing if there are errors or warnings.
- `themes.py` → the 36 styles (materials, roofs, church type, decoration).
- `houses.py`, `specials.py`, `streets.py`, `fillers.py` → piece builders.
- `pack.py` → pools and weights (including the proportion of villagers and beds).
- `writer.py` → village size, frequency and the structures' JSON.
- `advancements.py` → the "Heraldia" advancements tab (villages by family and, for each unique structure in the registry, discover, guardian and treasure; the trophy and chronicle challenges).
- Guardian trophies: the `TROPHY` of each unique structure → `uniques/_common/chest_loot.trophy` (`heraldia:trofeos/<id>`) and `guardian_tabla` (`heraldia:guardianes/<id>/<mob>`, the DeathLootTable set by `pack.tag_guardians`).
- Chronicle of the Heralds (`docs/STORY.md`): the `STORY` of each unique structure → `unicas/_comun/botin.historia_*` (`heraldia:historia/<id>`, which nests its chest's table; chain in `historia_cadena`) and `writer.history_tables`; the `unicas/cronista` challenge in `advancements.py`.
- `medianas/` → medium structures (watchtower, inn, camp, hermitage): contract in `mediums/__init__.py`, one module per type; `medianas.write` writes their structures, grids, tags and loot.
- `trades.py` → all villager trades (`trato`, `predicado`): the master cartographers' maps (`maps.trade`), each style's characteristic trades (`STYLES`), the map of each family's local unique structure and the siege bottle of the fortified villages; it writes the `#minecraft:<oficio>/level_N` tags.
- `board.py` → the square's quest board (lectern with book and sheriff with his fixed trades) and the feat advancements with their reward.
- `roads.py` → the `heraldia:camino` feature (roads between villages; the layout and placement are Java, package `caminos`) and the texts for the distance on its signs.
- `filler_loot.py` → the filler loot: every container without a table of its own gets a poor `heraldia:relleno/<name>` table by template rule when the template is saved; a container with no table, no rule and no empty-on-purpose mark fails the generation.
- `sim.py` → jigsaw assembly simulator to count houses, villagers and golems without opening the game.
- `validate.py` → checks blocks, properties, items and entities against the 26.3 registries (needs the misode/mcmeta summary, branch `26.3-summary`) and, over the written JSON, the radius and size limit of jigsaw structures.
