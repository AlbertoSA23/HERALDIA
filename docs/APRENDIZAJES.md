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

- Los mobs de una plantilla pasan por `finalizeSpawn` al colocarse: el esqueleto wither recibe siempre su espada de piedra (se pierde la del NBT), pero conserva armadura, `drop_chances`, atributos, `Tags` y nombre. Verificado con `data get entity` tras `/place structure` en un servidor dedicado (mansión).
- El servidor traduce los `CustomName` traducibles con el `en_us` del mod: el selector `name=` ve el texto inglés, no el `fallback`. Para buscar un mob de una estructura, mejor una etiqueta (`Tags`). Verificado en un servidor dedicado.
- Los cuadros en plantillas funcionan con `variant`, `facing` en código 2D (sur 0, oeste 1, norte 2, este 3) y `block_pos` como `IntArray`; siguen colgados pasados 15 s (16 de 16). Verificado en un servidor dedicado.
- El tipo de marca de mapa de la mansión del bosque es `minecraft:mansion` (no `woodland_mansion`); un nombre inválido en `MAPA` tumba el paquete entero al cargar el trato del cartógrafo. Verificado en un servidor dedicado (Registry loading errors).
- Un circuito de redstone guardado en su estado estable (antorchas encendidas, polvo con potencia y forma, repetidor alimentado, pistones pegajosos extendidos con su cabeza) se genera quieto y funciona al accionarlo: estantería secreta con pistones que tiran hacia un lado (el de abajo por cuasiconectividad) y combinación de 4 palancas con inversores y un bus O. Verificado con `/place template` y forzando la actualización junto a la antorcha (`/setblock` de la palanca no actualiza el bloque que la sostiene).
- `/place template` responde «Loaded template ...» (no «Placed»). Verificado en un servidor dedicado.

## Diseño de estructuras

- Sótanos con `beard_thin`: la casa es una pieza rígida cuya capa y=0 es el suelo y el sótano otra pieza rígida por debajo, unida con un jigsaw vertical (`down_north` → `up_north`, `aligned`). El sótano rellena toda su caja (piedra donde no hay salas) para que el ajuste del terreno no deje cavidades junto a sus muros. Verificado con `/place structure` (mansión).
- Ruina medible: calcular la fracción esperada de bloques cambiados por el procesador sobre la superficie visible (bloques con una cara al aire) y sumar la ruina a mano. Usado en la mansión.

## Generador y auditoría

- Auditoría de varias piezas: unir las piezas en una «obra» en coordenadas comunes, pasar `lint.walk`/`lint.access_issues` a vistas con los mecanismos cerrados y abiertos (zonas ocultas alcanzables solo en la segunda) y partir en piezas después. Simulador de redstone de los mecanismos en `tools/gen/unicas/mansion/redstone.py` (reutilizable). Verificado contrastándolo con el juego (prueba de la mansión).
- `core.to_tag` acepta cualquier etiqueta de `nbtlib` ya construida (necesario para `IntArray`).
- Corregido: `writer.lootr_aware` escribía `"conditions": [{"condition": "heraldia:sin_lootr"}]`, que 26.3 no acepta; ahora escribe `"condition": {"type": "heraldia:sin_lootr"}` (con `all_of` si ya había otra). Verificado con un módulo temporal: `loot spawn` del cofre da el extra sin Lootr.
- Opciones del mod: se definen en `tools/gen/opciones.py` (por defecto, rango y textos en los dos idiomas), que las escribe en `heraldia/opciones.json` dentro del `.jar`. El Java las valida de forma genérica: una opción nueva no necesita código, salvo para usarla. Verificado en la prueba de humo (corrección de un valor fuera de rango).

## Fallos pendientes
