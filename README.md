# Heraldia

**English** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Català](README.ca.md) · [Galego](README.gl.md)

A Fabric mod for **Minecraft 26.3** that fills the Overworld with places worth the journey: living villages joined by roads, ruins with a story, guardians with a name and treasure at the end of the map. Everything is built from vanilla blocks and items, so it fits right into your world.

## What you will find in your world

- 🏘️ **Living villages.** 72 hand-designed villages: 36 styles, one for each kind of biome (a Castilian village on the plains, stilt houses in the swamp, a Japanese village among the cherry trees...), each in a standard and a large size, grouped in 12 families. A square with a fountain and a bell, a church, a market, a tavern, a smithy, a library, an inn and twenty or thirty houses. Each style has its own trades, the bailiff's job board pays for harvests, firewood and clearing the roads, and the cartographers sell treasure maps.
- 🛤️ **Roads.** Trails with lamp posts and wooden bridges join neighbouring villages. Near each village a sign tells you the name of the next one and how many blocks are left.
- 🏕️ **By the wayside.** 8 kinds of medium structures between villages: watchtowers, roadside inns, bandit camps, hermitages, mills, fisher's huts, hunters' lodges and ruined shrines, each in the style of its biome, with modest loot and now and then a small challenge.
- 🏰 **19 unique structures**, very rare and each in its own biome: a castle with a moat, a Gothic cathedral, a dwarven citadel carved into the mountain, a stranded galleon, a haunted mansion, an eastern palace, a wizard's tower, a lost mine deep underground, a pirate fort on its own island in open sea... Inside: hidden rooms, redstone puzzles, traps and spawners, and at the end, a **named guardian** guarding the treasure chamber.
- ⚔️ **Guardians that fight in phases.** As they lose health they become enraged and call reinforcements from their own structure, with a boss bar while the fight lasts. Each one drops its own trophy.
- ⛏️ **Mines.** On real hillsides open adits, mining camps and mining complexes with a headframe, in 3 sizes and in the style of each biome, leading down to galleries with rails, crossings and rooms. Vanilla abandoned mineshafts are also more common.
- 🔱 **Atlantis.** Only one per world: a vast city sunk in the deep ocean, with dry halls, three seals with their keys and the Guardian of Poseidon, keeper of the greatest treasure in Heraldia.
- 🏟️ **Wave arena.** A coliseum near spawn: ring the bell and hold out against ever stronger waves, with a champion every fifth wave, records and rewards. If you fall in the ring, you keep your inventory.

## How to play

- 📖 **The Herald's Guide.** Every player gets it on joining: a book that explains what to look for and keeps your diary, with the unique structures you have discovered and clues to the ones still missing. Ask for an up-to-date copy at any time with `/heraldia guia`.
- 📊 **What the server has found.** `/heraldia estado` shows how many villages, unique structures, medium structures and mines the players have discovered, the guardians defeated and the arena record.
- 🏆 **Advancements.** A Heraldia tab with 94 advancements: a village of each family, every unique structure with its guardian and its treasure, the mines, the medium structures, the job board and the arena.
- 🗿 **Trophies.** Each of the 20 guardians drops its trophy, an item with a name and a story. Collect them all to complete the Hall of Trophies.
- 🗺️ **Treasure maps.** Each map marks the nearest unique structure of its kind. They turn up in the villages' epic chests and the cartographers sell them.
- 📜 **The Chronicle of the Heralds.** Each unique structure keeps a leaf of the chronicle written by Ysolda, the last herald of Atlantis. Each leaf points to the next: gather all 20 and you will learn how it ends.

The texts of the mod are in 8 languages: English, Spanish, French, German, Italian, Brazilian Portuguese, Catalan and Galician.

## Installation

1. You need **Minecraft 26.3**, **Fabric Loader** 0.20.1 or later and **Fabric API**.
2. Put `heraldia-<version>.jar` in the `mods` folder of the **server** and restart it.
3. **Players do not need the mod**: they can join with a vanilla client. Texts the client does not know show in Spanish, except the Herald's Guide, which arrives in each player's language. If they install the mod as well, they see everything in their own language and get the configuration screen (with Mod Menu).

**An existing world** works fine: the new structures appear in chunks that have not been generated yet (explore new land). If your world was created with Heraldia **0.1.0**, set `unicas.rejilla_compatible` to `true` before you start the server, so that `/locate`, treasure maps and the Guide keep finding the unique structures you already have.

## Most useful options

The file `config/heraldia.json` is created on the server's first start, with a help text for every option. Changes apply when the server is restarted, in newly generated chunks. Options that do not affect generation (difficulty, bosses, loot, arena, Guide...) can be applied without restarting with `/heraldia recargar`.

| Option | Default | What it does |
| --- | --- | --- |
| `aldeas.separacion_bloques` | 1500 | Average distance between villages (1000-10000). |
| `aldeas.maximo` | 100 | Maximum number of villages in the world. |
| `aldeas.caminos.activado` | `true` | Roads between villages. |
| `unicas.<id>.activada` | `true` | Turns a unique structure on or off. |
| `unicas.rejilla_compatible` | `false` | `true` only for worlds created with Heraldia 0.1.0. |
| `medianas.frecuencia_porcentaje` | 100 | How many medium structures (200 = twice as many). |
| `dificultad.nivel` | `normal` | Guardians and monsters: `facil`, `normal`, `dificil` or `heroica`. |
| `botin.reponer.activado` | `false` | Heraldia chests are restocked after a few days. |
| `arena.activado` | `true` | The wave arena near spawn. |
| `guia.entregar_al_entrar` | `true` | Gives the Herald's Guide to each player on joining. |

## Learn more

- [Full reference of the content](docs/CONTENT.md): every village style, unique structure, medium structure and mine, the guardian fights, advancements, arena and more.
- [Installation, commands and configuration](docs/CONFIGURATION.md): test and admin commands (`/heraldia info`, `/heraldia revisar`, `/heraldia estado`, `/heraldia recargar`, `/heraldia llave`...), every option and the in-game configuration screen.
- [Compatibility with other mods](docs/COMPATIBILITY.md): biome mods, structure mods, Lootr and the rest.
- [Building and testing](docs/BUILDING.md), [development guide (Spanish)](docs/DESARROLLO.md) and [changelog](CHANGELOG.md).

## License and credits

No license: all rights reserved. The code is visible but no permission is granted to use, copy or redistribute it.
All content uses only Minecraft blocks and items; no third-party assets are included.
