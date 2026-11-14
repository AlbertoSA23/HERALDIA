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
- Pistones pegajosos colocados **extendidos** (con su `piston_head`) en una plantilla y alimentados por una palanca encendida quedan estables; al quitar la potencia se recogen y tiran del bloque. Una puerta secreta «cerrada con potencia» funciona sin depender de actualizaciones al generar. Verificado con `/place template` en un servidor dedicado (monasterio, `prueba_servidor.py`).
- `/setblock` de una palanca no actualiza el polvo que está detrás de su bloque soporte: para simular un jugador desde la consola hay que cambiar después el bloque soporte (a otro y vuelta). `/place template` responde «Loaded template … at x, y, z» y no aplica procesadores. Verificado en un servidor dedicado.
- En las reglas de `processor_list`, `output_state` se escribe como cadena (`"minecraft:mossy_cobblestone"`), igual que en las listas vanilla de 26.3. Verificado en misode/mcmeta 26.3-summary.

## Diseño de estructuras
- Laderas sin Java: una sola plantilla rígida que trae su propio macizo de roca (de y = 0 a cada terraza, con talud irregular alrededor) y aire explícito sobre las terrazas, con `terrain_adaptation: none` y `start_height` negativo proyectado a la superficie (la terraza baja queda a ras en el centro). Sirve en cualquier rotación: cuesta arriba corta el monte, cuesta abajo deja ver el risco. Además el recorrido a pie de la auditoría cubre toda la estructura. Aplicado en el monasterio; aspecto en el juego sin confirmar con capturas.
- Generadores de monstruos en zonas con algo de luz: `SpawnData.custom_spawn_rules` (`block_light_limit` 0-11) evita que la regla de luz 0 de los monstruos los deje mudos. Sin verificar todavía en el juego que aparezcan mobs.

## Generador y auditoría

- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).
- Un módulo de `unicas/` puede dar `LANG = {"es_es": {...}, "en_us": {...}}` (lo suma `writer.py`) y la plantilla un `audit_view` (vista con puertas secretas abiertas) que usa `lint.py`; ganchos, cable trampa y palancas cuentan como transitables. Comprobado con la compilación.
- Redstone de plantillas: `unicas/monasterio/auditoria.py` tiene un simulador pequeño (palancas, antorchas de pared, polvo horizontal, bloques conductores, pistones, lámparas, puertas) que exige que el estado colocado sea el estable y prueba todas las combinaciones de palancas de cada puzle. Detectó un fallo real de diseño (una antorcha inversora cortaba la línea de suma). Reutilizable por otras estructuras.

## Fallos pendientes
