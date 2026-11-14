# Aprendizajes compartidos

Memoria común de las sesiones que diseñan estructuras para Heraldia. Cada viñeta es breve, dice qué se aprendió y cómo se verificó
(servidor de prueba, código de 26.3, auditoría, captura de Alberto). Las lecciones de partida están en `docs/DESARROLLO.md`.

## Comportamiento del juego (26.3)

- Desde 26.x no hay chunks de aparición cargados siempre («Loading 0 persistent chunks»): para `/place structure` desde la consola hay que hacer antes un `forceload` de toda la caja de la estructura. Verificado en un servidor dedicado.
- El servidor dedicado se pausa a los 60 s sin jugadores (`pause-when-empty-seconds`) y deja de cargar chunks. En las pruebas, ponlo a 0. Verificado en un servidor dedicado.
- `ServerLifecycleEvents.SERVER_STARTED` se dispara después del mensaje «Done». Verificado en un servidor dedicado.
- El registro de condiciones de botín (`BuiltInRegistries.LOOT_CONDITION_TYPE`) guarda directamente el `MapCodec`, sin envoltorio de tipo. Verificado al compilar.
- Los tratos de aldeano son datos: `villager_trade/<oficio>/<nivel>/*.json`, la etiqueta `#minecraft:<oficio>/level_N` (se le suman entradas con `"replace": false`) y `trade_set` (cuántos se sacan de la etiqueta; el cartógrafo de nivel 5 saca 2). `merchant_predicate` filtra por aldeano. Verificado en misode/mcmeta 26.3-data y cargando tratos propios en un servidor dedicado.
- No existen el modificador ni la condición `minecraft:reference`: un `item_modifier` compartido no se puede citar desde el botín ni desde los tratos, hay que escribirlo en línea. Un fichero `item_modifier` debe ser un objeto (una lista da «Not a JSON object»). Las condiciones se escriben `{"type": ...}`, y un grupo de botín lleva una sola `"condition"` (no la lista `conditions`). Verificado con errores de registro en un servidor dedicado.
- `exploration_map` funciona sobre `minecraft:filled_map`. Sin destino, el `filtered` + `discard` deja el objeto vacío («Dropped 0 [Air]»). Con `skip_existing_chunks: false` y 8 anillos (289 celdas) sin ningún bioma válido, la búsqueda responde en menos de 0,1 s. Verificado con `loot spawn` en un servidor dedicado.
- El predicado de entidad `{"nbt": "{Tags:[\"heraldia\"]}"}` sigue funcionando en 26.3 (en el selector `predicate=` y como `merchant_predicate`). Verificado en un servidor dedicado con un aldeano de la aldea y otro vanilla.

- `/locate` no pasa por `isPlacementChunk` de la colocación: usa `getPotentialStructureChunk` y luego `StructureCheck.checkStart`, que solo llama a `applyAdditionalChunkRestrictions` y a `canCreateStructure`. Una colocación propia que limite casillas debe filtrar también en `applyAdditionalChunkRestrictions`, o `/locate` señalará sitios donde no se genera nada. Verificado en el código de 26.3 y con `/locate` en la prueba de humo.
- `ChunkGenerator.findNearestMapStructure` solo sabe buscar en `concentric_rings` y en `random_spread` (con `instanceof`): un tipo de colocación propio debe heredar de `RandomSpreadStructurePlacement` para que `/locate` y los mapas lo encuentren. Su `codec()` tiene que devolver `MapCodec<RandomSpreadStructurePlacement>` (conversión sin comprobar). Verificado al compilar y con `/locate`.
- `BuiltInRegistries.STRUCTURE_PLACEMENT` también guarda directamente el `MapCodec`. Los datapacks de worldgen se leen después de `onInitialize`, así que una configuración leída ahí ya está disponible cuando se decodifica la colocación. Verificado en un servidor dedicado (orden de las líneas en el log).
- En un `structure_set` con varias estructuras, si `tryGenerateStructure` devuelve falso (bioma inválido o un mixin que la rechaza), se quita esa entrada y se sortea otra con la misma semilla de la casilla. Rechazar entradas es la forma limpia de desactivar estilos o fijar el tamaño. Verificado en el código de 26.3.

## Diseño de estructuras

- Redstone en plantillas: una antorcha de redstone en medio de una línea de polvo la corta en tramos; una señal que entra por un tramo no llega a los demás. En la catedral, la palanca «falsa» del puzle no cerraba la puerta hasta ponerla junto al tramo que toca el pistón. Verificado en un servidor dedicado (`prueba_juego.py`: palancas simuladas con un bloque de redstone en su apoyo).
- Puerta secreta que funciona al colocarse sin actualizaciones: dos pistones pegajosos **extendidos** (cabeza `short=false`) sujetan la puerta en la capa central de un muro de tres de grueso, alimentados por una antorcha (inversor) a través de polvo con `power` y conexiones escritas; la palanca apaga la antorcha y los pistones recogen la puerta. El pistón inferior se alimenta por el bloque bajo el polvo. Verificado en un servidor dedicado: tras `/place template` (que sí aplica actualizaciones de forma) el reposo no cambia, abre y vuelve a cerrar.
- Trampas vanilla sin cableado: un dispensador justo encima de un gancho de cable trampa, o al lado de una placa de presión, se activa directamente. Verificado en un servidor dedicado (una criatura sobre el cable o la placa hace disparar flechas).
- Trampilla de hierro abierta encima de una escalera de mano con el mismo `facing` sirve de peldaño; la palanca de suelo en el bloque contiguo la abre. Verificado en un servidor dedicado.
- Estructura con sótano: dividirla en dos piezas rígidas (superficie con base en el suelo y sótano debajo) unidas por un jigsaw vertical `down_<x>`/`up_<x>` con la misma dirección superior; así `beard_thin` asienta la de superficie como una casa normal. Verificado en la prueba de humo (`/place structure`).

## Generador y auditoría

- En 26.3 el `output_state` de una regla de `processor_list` es una cadena (`"minecraft:cracked_stone_bricks"`), no un objeto `{Name: ...}`; con el objeto se rechaza el pool entero («Unbound values in registry ... template_pool»). La validación no lo detecta. Verificado en un servidor dedicado y en misode/mcmeta 26.3-data.
- Las cubiertas escalonadas (2 de subida por columna) solo se tocan por aristas: con 2 bloques de grueso quedan «flotando» para una búsqueda de componentes por caras; con 3 se unen. Detectado con la auditoría de la catedral.
- `Template.fill` ordena los extremos: un intervalo `y2 < y1` que se esperaba vacío rellena al revés. La catedral usa un `fill` que lo ignora. Detectado con la auditoría (aire inesperado dentro de una bóveda).
- Un módulo de estructura única puede declarar `LANG` (textos `es_es`/`en_us`) y `writer.py` los suma a los del mod.

- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
