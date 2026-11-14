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

- Entidades colgadas (marcos) en una plantilla: sin `block_pos` el juego las descarta al colocar («Block-attached entity at invalid position: null»). Basta con poner `block_pos` (la posición real la recalcula la colocación). Verificado con `/place template` en un servidor dedicado.
- Puerta secreta de pistones enrasada que funciona al generarse: guardar los estados coherentes con la energía (pistones pegajosos `extended=true` con su `piston_head`, antorcha de redstone `lit=true` en la cara oculta del bloque donde va la palanca, palanca apagada). Al encender la palanca la antorcha se apaga y los pistones recogen la puerta; un bloque macizo encima de la antorcha alimenta el segundo pistón. Marco + comparador (orientado hacia el marco) + trampilla de hierro, cable trampa con dispensador encima del bloque del gancho y placa con dispensadores al lado también funcionan. Verificado en un servidor dedicado con `tools/smoke/coliseo_redstone.py`.

## Diseño de estructuras

- Sótanos sin hundir el terreno: pieza principal a ras de suelo (`beard_thin` solo allana alrededor) y el sótano como pieza hija bajo un jigsaw vertical (`down_south` / `up_south`) que rellena **toda** su caja (roca donde no hay salas). El rebaje de `beard_thin` solo actúa hasta 12 bloques por encima de la base de cada pieza, así que queda bajo tierra. Usado en el Coliseo; el alcance de 12 bloques sale del código de `Beardifier` y la colocación se verificó con `/place structure` en la prueba de humo, pero falta ver el terreno en un mundo real.
- Diseñar en un único «mundo» con coordenadas centradas y partirlo en piezas al final (y >= 0 / y < 0) permite que escaleras y pozos crucen de una pieza a otra sin cuentas de desplazamiento. Ver `tools/gen/unicas/coliseo/plano.py`.

## Generador y auditoría

- Recorrido estricto (`tools/gen/unicas/coliseo/auditoria.py`): sin caídas de más de un bloque y comprobando que desde cada celda se vuelve a la entrada (grafo inverso); con los puzles resueltos y sin resolver (lo oculto no debe alcanzarse). Encontró que `lint.walk` deja bajar por una escalera de mano a través de una trampilla cerrada y no ve un peldaño dos bloques más abajo de la celda de los pies.
- Otras comprobaciones reutilizables del Coliseo: bloques sin unión con el suelo de su pieza (la ruina deja fragmentos sueltos), luz de bloque propagada alrededor de los generadores y porcentaje de superficie expuesta dañada frente a la versión sin ruina.
- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
