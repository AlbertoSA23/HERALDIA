# Registro de cambios

Formato: cada versión es `## [X.Y.Z]` (con ` - AAAA-MM-DD` al publicarla) y lleva dos apartados:
`### Jugadores` (lo que nota quien juega) y `### Técnico` (cambios internos). La versión de arriba
coincide con `mod_version` de `gradle.properties`; `tools/changelog.py` lo comprueba y extrae las notas de publicación.

## [0.1.0]

### Jugadores

- Primera versión del mod: 72 aldeas enormes (36 estilos por bioma, cada uno en tamaño estándar y grande) que aparecen en chunks nuevos del Overworld, una cada 1000-2000 bloques.
- Comandos de prueba `/function heraldia:muestrario` y `/function heraldia:familia/<familia>` para ver los estilos colocados en fila; sus mensajes salen en español o inglés según el idioma del cliente.
- Mapas del tesoro hacia cada estructura única: en el 5 % de los cofres épicos de las aldeas y a la venta en los cartógrafos maestros de las aldeas Heraldia (24 esmeraldas y una brújula); con nombre en español o inglés.

### Técnico

- Proyecto Fabric para Minecraft 26.3 (Loom 1.19-SNAPSHOT, Loader 0.20.1, Fabric API 0.166.2+26.3, Java 25), id `heraldia`.
- El generador del datapack "Aldeas enormes" pasa a `tools/gen/` y escribe sus recursos en el `.jar` durante la compilación; namespace `aldeas` cambiado a `heraldia` en estructuras, pools, botín, funciones y etiquetas.
- La ruta de los registros de 26.3 para validar es configurable (`--registries`, `MCMETA_SUMMARY` o `-Pmcmeta_summary`); por defecto se clona `misode/mcmeta` rama `26.3-summary` en `build/` y no se sube al repositorio.
- La validación comprueba sobre los JSON escritos el límite `max_distance_from_center` + 12 <= 128 y `size` <= 20.
- Al arrancar el servidor, el log indica cuántas estructuras `heraldia` hay registradas.
- Comprobaciones locales: `tools/changelog.py check` valida este registro y `tools/smoke/server_smoke.py` arranca un servidor dedicado 26.3 real con el mod como prueba de humo.
- Sin licencia: todos los derechos reservados.
- Base para estructuras únicas: el generador descubre los módulos de `tools/gen/unicas/` y escribe su estructura, su rejilla de colocación, su etiqueta (para mapas) y su botín bajo `heraldia:unicas/<id>`.
- Condición de botín `heraldia:sin_lootr`: los grupos marcados `solo_sin_lootr` se omiten si Lootr está cargado.
- La prueba de humo coloca también cada estructura única y abre todas las tablas de botín.
- `tools/gen/mapas.py`: por cada estructura única escribe `item_modifier` y `loot_table` `heraldia:mapas/<id>` (exploración hacia `#heraldia:unicas/<id>`, radio limitado a ~10.000 bloques y 8 anillos, `skip_existing_chunks` falso, descarte si no hay destino) y el trato `heraldia:cartografo/<id>`, añadido a `#minecraft:cartographer/level_5` con `merchant_predicate` que exige la etiqueta de entidad `heraldia`; los aldeanos de las plantillas la llevan. Contrato de `unicas/` ampliado con `NOMBRE` y `MAPA` opcionales.
- Corregida la condición `heraldia:sin_lootr` en el botín: en 26.3 un grupo lleva `"condition": {"type": ...}`, no la lista `conditions`.
- La prueba de humo mide cada mapa (máximo 30 s, con o sin destino), tira 20 veces el cofre épico y comprueba el filtro de cartógrafos con un aldeano de la aldea y otro vanilla.
