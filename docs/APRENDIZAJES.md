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

- Sótanos sin hundir el terreno: poner lo subterráneo en piezas aparte colgadas por jigsaw vertical (`down_south` → `up_south`, `aligned`) y rellenar su caja entera bloque a bloque; la pieza de superficie no baja de y = 0. Diseñar en coordenadas globales y cortar en piezas por cajas permite auditar la estructura completa. Verificado con `place structure` (acueducto) en un servidor dedicado.
- Pilares que llegan al suelo en una pieza rígida: un procesador propio con `finalizeProcessing` puede añadir bloques a la lista (columnas hacia abajo) leyendo el mundo solo dentro de `settings.getBoundingBox()` (el chunk en generación). Se registra en `BuiltInRegistries.STRUCTURE_PROCESSOR` con el `MapCodec` directamente. Verificado en un servidor dedicado: los 52 cimientos del acueducto quedan apoyados.
- Puertas secretas que cierran sin energía externa: pistones pegajosos **extendidos al colocarse** (con su `piston_head`) alimentados por antorchas inversoras; en la generación no hay actualizaciones, así que basta con colocar el estado estable (antorcha `lit=true`, polvo con su `power` calculado). Al cambiar una palanca el circuito reacciona normal. Verificado en un servidor dedicado con `place template`.
- Probar redstone sin jugador: `setblock` de la palanca con `powered=true` solo avisa a sus vecinos; para que reaccione una antorcha a dos bloques hay que cambiar y restaurar un bloque vecino suyo. Las placas se prueban con un mob con `NoAI` (no con dificultad pacífica, que los borra) y las de madera con un objeto `summon item`. Verificado en un servidor dedicado.

## Generador y auditoría

- `lint.walk` toma como suelo cualquier celda con y - 1 < 0 sin bloque debajo: con piezas por debajo de y = 0, el recorrido "camina" por el vacío. Para auditar subsuelos hay que poner tierra explícita bajo lo que no tiene subsuelo (lo hace `unicas/acueducto/auditoria.py`). Verificado con la auditoría del acueducto.
- No existe `cut_sandstone_stairs` (sí `smooth_sandstone_stairs` y `sandstone_stairs`). Verificado con la validación contra los registros.

- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
