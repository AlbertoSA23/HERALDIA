# Registro de cambios

Formato: cada versión es `## [X.Y.Z]` (con ` - AAAA-MM-DD` al publicarla) y lleva dos apartados:
`### Jugadores` (lo que nota quien juega) y `### Técnico` (cambios internos). La versión de arriba
coincide con `mod_version` de `gradle.properties`; `tools/changelog.py` lo comprueba en CI y extrae las notas de publicación.

## [0.1.0]

### Jugadores

- Primera versión del mod: 72 aldeas enormes (36 estilos por bioma, cada uno en tamaño estándar y grande) que aparecen en chunks nuevos del Overworld, una cada 1000-2000 bloques.
- Comandos de prueba `/function heraldia:muestrario` y `/function heraldia:familia/<familia>` para ver los estilos colocados en fila; sus mensajes salen en español o inglés según el idioma del cliente.

### Técnico

- Proyecto Fabric para Minecraft 26.3 (Loom 1.19-SNAPSHOT, Loader 0.20.1, Fabric API 0.166.2+26.3, Java 25), id `heraldia`.
- El generador del datapack "Aldeas enormes" pasa a `tools/gen/` y escribe sus recursos en el `.jar` durante la compilación; namespace `aldeas` cambiado a `heraldia` en estructuras, pools, botín, funciones y etiquetas.
- La ruta de los registros de 26.3 para validar es configurable (`--registries`, `MCMETA_SUMMARY` o `-Pmcmeta_summary`); por defecto se clona `misode/mcmeta` rama `26.3-summary` en `build/` y no se sube al repositorio.
- La validación comprueba sobre los JSON escritos el límite `max_distance_from_center` + 12 <= 128 y `size` <= 20.
- Al arrancar el servidor, el log indica cuántas estructuras `heraldia` hay registradas.
- CI en GitHub: compila el `.jar` (generación, validación y auditoría incluidas), comprueba este registro de cambios y arranca un servidor dedicado 26.3 real con el mod como prueba de humo.
