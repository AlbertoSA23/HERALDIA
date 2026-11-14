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

- Circuitos de redstone en plantillas: una antorcha encendida alimenta con fuerza el bloque de encima, y un polvo vecino de ese bloque recibe potencia. Una antorcha NO cuyo soporte se alimenta con polvo puesto *encima del soporte* forma así un reloj y se funde (queda apagada). Lleva el último polvo por el lado del soporte (bajando un escalón si hace falta). Verificado en un servidor dedicado con `tools/smoke/observatorio_smoke.py`.
- Las plantillas se colocan sin actualizaciones de bloque: el estado de reposo del circuito (polvo con su `power`, antorchas `lit`) debe escribirse coherente. Calcularlo con una simulación y comparar en el servidor con `/execute if block` funciona. Para simular una palanca desde la consola, pon un bloque de redstone en su soporte (`setblock` de una palanca con `powered=true` no actualiza el bloque al que está sujeta). Verificado en servidor.
- Puerta secreta de pistones estable al colocarse: pistones pegajosos extendidos con su cabeza y el sello delante, alimentados por una antorcha de redstone (el de arriba directo, el de abajo por casi-conectividad); la palanca apaga la antorcha y los pistones tiran del sello. Verificado en servidor.
- `lint.walk` toma como suelo natural cualquier celda vacía con y < 0: para auditar piezas con sótano en coordenadas negativas, desplaza la plantilla hacia arriba antes del recorrido. Verificado con la auditoría del Observatorio.
- Sótano sin cráter: pieza de subsuelo aparte bajo la de superficie, unida con un jigsaw vertical (`down_north`/`up_north`, `aligned`, así hereda el giro). La adaptación `beard_thin` solo actúa a ±12 bloques de la base de cada pieza. Comprobado que `/place structure` coloca ambas piezas (el guardián del subsuelo aparece).

## Generador y auditoría

- `validate_structures` solo miraba `worldgen/structure/` (no `unicas/`): ahora revisa también las estructuras únicas. Verificado al generar.
- `lint` contaba la linterna marina como farol («farol de pie sin apoyo») y el cable trampa y la palanca como bloques macizos; corregido. Verificado con la auditoría del Observatorio.

- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
