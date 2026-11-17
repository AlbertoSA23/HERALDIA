# Heraldia: compatibilidad con otros mods

[English](COMPATIBILITY.md) · **Español**

Volver al [README](../README.es.md).

## Biomas de otros mods

Cada familia de aldeas y cada estructura única busca sus biomas con una etiqueta propia (`#heraldia:<familia>` y `#heraldia:unicas/<id>`): los biomas vanilla de las tablas de arriba más las etiquetas convencionales de Fabric/NeoForge (`#c:...`) y `#minecraft:is_*` en las que los mods de biomas (Terralith, Biomes O' Plenty...) meten los suyos. Solo se usan las que en vanilla no añaden ningún bioma a la lista, así que **sin mods de biomas todo sale exactamente donde antes**; todas van con `"required": false` (si un mod no está, el paquete carga igual).

| Etiqueta | Además de sus biomas vanilla |
| --- | --- |
| `llanuras`, `unicas/castillo` | `#c:is_plains` |
| `bosque` | `#c:is_birch_forest`, `#c:is_flower_forest` |
| `oscuro` (y la torre de mago) | `#c:is_dark_forest` |
| `nieve`, `unicas/fortaleza_hielo` | `#c:is_snowy_plains` |
| `desierto`, `unicas/acueducto` | `#c:is_desert` |
| `jungla` | `#minecraft:is_jungle`, `#c:is_jungle` |
| `pantano` (y la mansión) | `#c:is_swamp` |
| `badlands` | `#minecraft:is_badlands`, `#c:is_badlands` |
| `costa` | `#minecraft:is_beach`, `#c:is_beach`, `#c:is_stony_shores` |
| `unicas/catedral` | `#c:is_flower_forest` |
| `unicas/santuario` | `#c:is_birch_forest` |
| `unicas/laboratorio_micelio` | `#c:is_mushroom` |
| `unicas/faro` | `#c:is_stony_shores` |
| `unicas/galeon` | `#minecraft:is_beach`, `#c:is_beach` |
| `unicas/atlantida` | `#minecraft:is_ocean`, `#c:is_ocean` |

Taiga, sabana, cerezos y las únicas coliseo, observatorio, pirámide, monasterio, ciudadela, palacio, salón del jarl, mina perdida e isla del corsario se quedan solo con sus biomas vanilla: no hay ninguna etiqueta convencional lo bastante estrecha (por ejemplo, `#c:is_cave` incluye el abismo; `#c:is_taiga` incluye la taiga nevada, de la familia nieve, y `#c:is_savanna` la sabana ventosa, del observatorio). Qué bioma de un mod entra en cada etiqueta lo decide ese mod (con Terralith, por ejemplo, la llanura incluye sus estepas y tierras altas, y el bosque, sus bosques de lavanda y de cerezos). La búsqueda de la Atlántida acepta también los océanos de `#c:is_ocean` y `#c:is_deep_ocean`. Probado con Terralith 2.6.5 (`tools/smoke/terralith_biomas.py`).

## Compatibilidad con otros mods

Probado en un servidor dedicado 26.3 real con las versiones de Modrinth para Minecraft 26.3 + Fabric de la tabla (fijadas con su sha512 en `tools/smoke/modrinth.py`), por grupos de mods que funcionan juntos (`python3 tools/smoke/compat_mods.py --grupo <grupo>`; `--listar` muestra los grupos). En cada grupo: el servidor arranca sin errores de registro ni excepciones que pasen por código de Heraldia, se registran todas las estructuras de Heraldia, `/locate` encuentra una aldea y cuatro estructuras únicas, `/place` coloca la torre de mago con su guardián y se generan (Chunky) tres zonas de 21 × 21 chunks alrededor de la aldea y de dos únicas, midiendo chunks/s y «Can't keep up!». Después se leen los inicios de estructura guardados en las regiones para buscar piezas de Heraldia cruzadas con piezas de estructuras de otros mods.

**Estructuras de otros mods junto a las de Heraldia**: una estructura de otro mod que asoma a la superficie (aldeas de Towns and Towers, ruinas de Structory, tabernas de Dungeons and Taverns...) no nace a menos de `compatibilidad.zona_estructuras_ajenas_bloques` bloques (224 por defecto, 0 lo desactiva) del inicio de una aldea o una única de Heraldia que sale de verdad ahí; Heraldia gana siempre, así que ninguna queda encima de la otra. Antes, la prueba encontró una aldea del bosque de Towns and Towers encima de la catedral y una aldea de playa dentro de una aldea de Heraldia. No cubre: las estructuras subterráneas de otros mods (minas, mazmorras: no se ven, pero pueden cruzar un sótano o la Mina perdida), las vanilla y los mods que sustituyen a las vanilla con su nombre `minecraft:` (las aldeas vanilla conservan su propia zona de exclusión) y estructuras muy grandes cuyas piezas llegan más lejos que esa distancia.

| Mod | Versión probada | Estado | Notas |
| --- | --- | --- | --- |
| Terralith (+ Lithostitched) | 2.6.5+26.3 (2.0.6) | probado | Biomas por las etiquetas convencionales ([Biomas de otros mods](#biomas-de-otros-mods)); sus estructuras propias se apartan de las de Heraldia. 33,8 chunks/s (52,6 sin mods). |
| Tectonic (+ Lithostitched) | 3.1.0+beta2 | con limitaciones | Funciona (27,3 chunks/s), pero Tectonic 3 se declara incompatible con Terralith: con los dos el servidor no arranca («Mod resolution failed»). |
| Biomes O' Plenty (+ GlitchCore, TerraBlender) | 26.3.0.0.16 | probado | 42,6 chunks/s. |
| William Wythers' Overhauled Overworld (+ Cristel Lib, Cloth Config) | 3.0.1 | probado | 15,4 chunks/s: su terreno cuesta más de generar (también sin Heraldia). |
| Oh The Biomes We've Gone | — | no probado: sin versión 26.3 | Última versión para Fabric: 1.21.11. |
| Dungeons and Taverns | 6.1.0 | probado | Con la zona de exclusión, sin solapes. |
| Towns and Towers (+ Cristel Lib) | 1.13.13 | probado | Se solapaba antes de la zona de exclusión; ahora no. |
| Structory, Structory: Towers | 1.3.18, 1.0.19 | probado | |
| Explorify | 1.6.6 | probado | 41,2 chunks/s con todo el grupo de estructuras. |
| YUNG's Better Dungeons, Mineshafts, Strongholds, Ocean Monuments, Desert Temples, Jungle Temples, Witch Huts, Bridges, Extras (YUNG's API) | — | no probado: sin versión 26.3 | Última: 26.1.2. |
| Lithium | 0.26.3 | probado | |
| C2ME | 0.4.2-alpha.0.119 | probado | Generación multihilo: 63,7 chunks/s, sin errores. Los mixins y cachés de Heraldia son seguros entre hilos (revisados, con tests unitarios concurrentes). |
| FerriteCore | 9.0.0 | probado | |
| ScalableLux | 0.3.0-alpha.0.6 | probado | Sustituye a Starlight. |
| ModernFix | — | no probado: sin versión 26.3 | Última: 1.21.1. |
| Starlight | — | no probado: sin versión 26.3 | Abandonado (última 1.20.4); lo sustituye ScalableLux. |
| Noisium | — | no probado: sin versión 26.3 | Tampoco NoisiumForked (última 26.2). |
| Chunky | 1.5.66 | probado | Hace la pregeneración en todos los grupos. |
| Lootr | 1.25.42.124 | probado | Detectado (`/heraldia info`): cada cofre da un botín más modesto, porque cada jugador abre el suyo. |
| Distant Horizons (servidor) | 3.3.4 | con limitaciones | Funciona con Heraldia (zonas generadas con `forceload`), pero junto con Chunky el servidor se queda parado al preparar el spawn, también sin Heraldia: no pregeneres con Chunky mientras esté instalado. |
| Xaero's Minimap, Xaero's World Map | 26.6.2, 1.47.2 | probado (servidor) | Cargan en el servidor; sin probar con un cliente. |
| JourneyMap | 6.0.10 | probado (servidor) | Igual. |

En la CI estas pruebas van en cada push a `develop`, a mano y en los PR que cambian sus ficheros, los mods fijados o el código común de colocación. `python3 tools/smoke/modrinth.py --comprobar` dice si hay versiones 26.3 más nuevas.

## Mapas web (BlueMap, Dynmap y squaremap)

Dependencias opcionales: Heraldia mira al iniciar (`FabricLoader.isModLoaded`) si están `bluemap`, `dynmap` o `squaremap`, y solo entonces carga su adaptador (`mapas/bluemap/`, `mapas/dynmap/`, `mapas/squaremap/`), la única clase que nombra la API de ese mapa. Sin ninguno no se registra ningún evento, no se escribe nada en el mundo y no se carga ninguna clase de los mapas (lo comprueba `MapasWebAisladoTest` en el bytecode). Las API van como `compileOnly` (no entran en el `.jar`): `de.bluecolored:bluemap-api:2.8.2` (repo.bluecolored.de), `xyz.jpenilla:squaremap-api:1.4.3` (Maven Central) y `us.dynmap:DynmapCoreAPI:3.8` (repo.mikeprimm.com; no publica `maven-metadata.xml`, pero la versión fija se resuelve). Si un mapa trae otra versión de su API que no encaja, se avisa en el log y se sigue sin él. Qué sale y las opciones: [Mapas web](CONFIGURACION.md#mapas-web-heraldia-webmap-refresh).

| Mapa | Versión probada | Estado | Notas |
| --- | --- | --- | --- |
| squaremap | 1.4.3 | probado | `tools/smoke/mapas_web.py`: las 5 capas, el marcador de una mediana al descubrirla con un jugador simulado (posición, icono, nombre y descripción en español), `solo_descubiertas`, las capas apagadas y la vuelta tras reiniciar (del fichero del mundo). Una capa (`SimpleLayerProvider`) por clase, con iconos de 24 px. |
| BlueMap | 5.29 (API 2.8.2) | compilado, sin probar en servidor | Un `MarkerSet` por capa en cada mapa del Overworld, con marcadores de punto y los iconos en los recursos del mapa. BlueMap no arranca su API hasta aceptar la descarga de recursos (`accept-download` en su `core.conf`); Heraldia publica en cuanto se activa. |
| Dynmap | — | sin versión 26.3 (última: 1.21.11) | Adaptador escrito contra DynmapCoreAPI 3.8 (conjuntos no persistentes, iconos propios, todo en el hilo del servidor porque su API no es segura entre hilos); el mundo del Overworld se busca por el nombre del nivel. Sin probar. |
