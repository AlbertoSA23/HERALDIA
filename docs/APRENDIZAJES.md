# Aprendizajes compartidos

Memoria común de las sesiones que diseñan estructuras para Heraldia. Cada viñeta es breve, dice qué se aprendió y cómo se verificó
(servidor de prueba, código de 26.3, auditoría, captura de Alberto). Las lecciones de partida están en `docs/DESARROLLO.md`.

## Comportamiento del juego (26.3)

- Desde 26.x no hay chunks de aparición cargados siempre («Loading 0 persistent chunks»): para `/place structure` desde la consola hay que hacer antes un `forceload` de toda la caja de la estructura. Verificado en un servidor dedicado.
- El servidor dedicado se pausa a los 60 s sin jugadores (`pause-when-empty-seconds`) y deja de cargar chunks. En las pruebas, ponlo a 0. Verificado en un servidor dedicado.
- `ServerLifecycleEvents.SERVER_STARTED` se dispara después del mensaje «Done». Verificado en un servidor dedicado.
- El registro de condiciones de botín (`BuiltInRegistries.LOOT_CONDITION_TYPE`) guarda directamente el `MapCodec`, sin envoltorio de tipo. Verificado al compilar.

- `/locate` no pasa por `isPlacementChunk` de la colocación: usa `getPotentialStructureChunk` y luego `StructureCheck.checkStart`, que solo llama a `applyAdditionalChunkRestrictions` y a `canCreateStructure`. Una colocación propia que limite casillas debe filtrar también en `applyAdditionalChunkRestrictions`, o `/locate` señalará sitios donde no se genera nada. Verificado en el código de 26.3 y con `/locate` en la prueba de humo.
- `ChunkGenerator.findNearestMapStructure` solo sabe buscar en `concentric_rings` y en `random_spread` (con `instanceof`): un tipo de colocación propio debe heredar de `RandomSpreadStructurePlacement` para que `/locate` y los mapas lo encuentren. Su `codec()` tiene que devolver `MapCodec<RandomSpreadStructurePlacement>` (conversión sin comprobar). Verificado al compilar y con `/locate`.
- `BuiltInRegistries.STRUCTURE_PLACEMENT` también guarda directamente el `MapCodec`. Los datapacks de worldgen se leen después de `onInitialize`, así que una configuración leída ahí ya está disponible cuando se decodifica la colocación. Verificado en un servidor dedicado (orden de las líneas en el log).
- En un `structure_set` con varias estructuras, si `tryGenerateStructure` devuelve falso (bioma inválido o un mixin que la rechaza), se quita esa entrada y se sortea otra con la misma semilla de la casilla. Rechazar entradas es la forma limpia de desactivar estilos o fijar el tamaño. Verificado en el código de 26.3.
- Un chunk solo busca inicios de estructura a ±8 chunks (`ChunkGenerator.createReferences`, `range = 8`): una pieza a más de 8 chunks de su chunk de inicio no se coloca nunca, sin error. Un inicio cubre como mucho 17 × 17 chunks (272 bloques); para algo mayor hacen falta varios inicios. Verificado en el código de 26.3 (Atlántida).
- Zonas secas bajo el agua: con `liquid_settings: ignore_waterlogging` en la estructura, el aire de la plantilla queda seco y los bloques anegables conservan su estado; con el valor por defecto (`apply_waterlogging`) los bloques anegables colocados donde había agua quedan anegados e inundan la sala. Una puerta cerrada retiene el agua y una «piscina lunar» (agua bajo aire) no sube. El agua que se quiera debe ir en la plantilla. Verificado en un servidor dedicado con generación natural en océano profundo, leyendo los bloques a los 30 s y a los 2 min (Atlántida).
- Romper un bloque del muro de una sala seca sumergida la inunda en segundos (vanilla). Verificado en el mismo servidor con `setblock`.
- En la consola, `execute as @e[...] at @s if block ...` escribe una línea «Test passed» por entidad: para contar en una prueba automática, suma en un marcador con un nombre único por comprobación y léelo con `scoreboard players get`. Verificado en un servidor dedicado (la primera versión de la prueba leía resultados desincronizados).

## Diseño de estructuras

## Generador y auditoría

- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
